import test from "node:test";
import assert from "node:assert/strict";

import {
  EXPORT_FILENAME,
  ERROR_CODES,
  ERROR_MESSAGES,
  REVOKE_DELAY_MS,
  ExportError,
  buildExportPayload,
  canExport,
  exportPreferencesJson,
  serializePayload,
} from "./exportPreferences.js";

const PREFS = { email: true, sms: false, push_notification: true };
const FIXED = new Date("2026-10-30T12:34:56.789Z");

/** Fake browser environment recording every interaction. */
function fakeEnv(overrides = {}) {
  const log = { blobs: [], created: [], revoked: [], scheduled: [], appended: [], removed: [], clicks: 0 };
  const body = {
    appendChild(el) {
      log.appended.push(el);
      el.parentNode = body;
    },
    removeChild(el) {
      log.removed.push(el);
      el.parentNode = null;
    },
  };
  class FakeBlob {
    constructor(parts, opts) {
      this.parts = parts;
      this.type = opts.type;
      log.blobs.push(this);
    }
  }
  const env = {
    now: () => FIXED,
    Blob: FakeBlob,
    URL: {
      createObjectURL(blob) {
        log.created.push(blob);
        return "blob:fake-1";
      },
      revokeObjectURL(url) {
        log.revoked.push(url);
      },
    },
    setTimeout(fn, ms) {
      log.scheduled.push({ fn, ms });
    },
    document: {
      body,
      createElement(tag) {
        assert.equal(tag, "a");
        return {
          style: {},
          parentNode: null,
          click() {
            log.clicks += 1;
          },
        };
      },
    },
    ...overrides,
  };
  return { env, log };
}

test("payload has exactly the required keys in documented order", () => {
  const p = buildExportPayload("cust-1", PREFS, FIXED);
  assert.deepEqual(Object.keys(p), ["customerId", "email", "sms", "push_notification", "exportedAt"]);
  assert.equal(p.customerId, "cust-1");
  assert.equal(p.email, true);
  assert.equal(p.sms, false);
  assert.equal(p.push_notification, true);
});

test("exportedAt is an ISO-8601 UTC string and differs between exports", () => {
  const a = buildExportPayload("c", PREFS, new Date("2026-10-30T00:00:00.000Z"));
  const b = buildExportPayload("c", PREFS, new Date("2026-10-30T00:00:01.000Z"));
  assert.match(a.exportedAt, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/);
  assert.notEqual(a.exportedAt, b.exportedAt);
});

test("extra properties on prefs (e.g. tokens) never reach the payload", () => {
  const p = buildExportPayload("c", { ...PREFS, token: "secret", jwt: "x" }, FIXED);
  assert.equal(JSON.stringify(p).includes("secret"), false);
  assert.equal("token" in p, false);
  assert.equal("jwt" in p, false);
});

test("serialized JSON is pretty printed, round-trips and ends with a newline", () => {
  const text = serializePayload(buildExportPayload("c", PREFS, FIXED));
  assert.ok(text.includes('\n  "customerId": "c"'));
  assert.ok(text.endsWith("}\n"));
  assert.deepEqual(JSON.parse(text), buildExportPayload("c", PREFS, FIXED));
});

for (const [name, cid, prefs, code] of [
  ["prefs undefined", "c", undefined, ERROR_CODES.NOT_LOADED],
  ["prefs null", "c", null, ERROR_CODES.NOT_LOADED],
  ["customerId missing", undefined, PREFS, ERROR_CODES.NOT_LOADED],
  ["customerId blank", "   ", PREFS, ERROR_CODES.NOT_LOADED],
  ["non-boolean value", "c", { ...PREFS, sms: "yes" }, ERROR_CODES.INVALID],
  ["missing key", "c", { email: true, sms: false }, ERROR_CODES.INVALID],
  ["prefs not an object", "c", "nope", ERROR_CODES.INVALID],
]) {
  test(`export is blocked and nothing downloads: ${name}`, () => {
    const { env, log } = fakeEnv();
    assert.equal(canExport(cid, prefs), false);
    assert.throws(
      () => exportPreferencesJson(cid, prefs, env),
      (err) => err instanceof ExportError && err.code === code && err.message === ERROR_MESSAGES[code],
    );
    assert.equal(log.blobs.length, 0);
    assert.equal(log.clicks, 0);
  });
}

test("canExport is true when loaded", () => {
  assert.equal(canExport("c", PREFS), true);
});

test("download uses fixed filename, JSON blob, anchor appended/removed, delayed revoke", () => {
  const { env, log } = fakeEnv();
  const payload = exportPreferencesJson("cust-1", PREFS, env);

  assert.equal(log.blobs.length, 1);
  assert.equal(log.blobs[0].type, "application/json");
  assert.deepEqual(JSON.parse(log.blobs[0].parts[0]), payload);
  assert.equal(payload.exportedAt, FIXED.toISOString());

  assert.equal(log.clicks, 1);
  assert.equal(log.appended.length, 1);
  const anchor = log.appended[0];
  assert.equal(anchor.download, EXPORT_FILENAME);
  assert.equal(EXPORT_FILENAME, "notification-preferences.json");
  assert.equal(anchor.href, "blob:fake-1");
  assert.deepEqual(log.removed, [anchor]);

  // URL is not revoked synchronously; it is scheduled.
  assert.deepEqual(log.revoked, []);
  assert.equal(log.scheduled.length, 1);
  assert.equal(log.scheduled[0].ms, REVOKE_DELAY_MS);
  log.scheduled[0].fn();
  assert.deepEqual(log.revoked, ["blob:fake-1"]);
});

test("two exports produce different exportedAt values", () => {
  let t = 0;
  const { env } = fakeEnv({ now: () => new Date(Date.UTC(2026, 9, 30, 0, 0, t++)) });
  const a = exportPreferencesJson("c", PREFS, env);
  const b = exportPreferencesJson("c", PREFS, env);
  assert.notEqual(a.exportedAt, b.exportedAt);
});

test("createObjectURL failure maps to the download error message", () => {
  const { env, log } = fakeEnv();
  env.URL.createObjectURL = () => {
    throw new Error("boom");
  };
  assert.throws(
    () => exportPreferencesJson("c", PREFS, env),
    (err) => err.code === ERROR_CODES.DOWNLOAD_FAILED && err.message === ERROR_MESSAGES[ERROR_CODES.DOWNLOAD_FAILED],
  );
  assert.equal(log.clicks, 0);
});

test("click failure revokes the URL, removes the anchor and reports download error", () => {
  const { env, log } = fakeEnv();
  const origCreate = env.document.createElement;
  env.document.createElement = (tag) => {
    const a = origCreate(tag);
    a.click = () => {
      throw new Error("blocked");
    };
    return a;
  };
  assert.throws(() => exportPreferencesJson("c", PREFS, env), (err) => err.code === ERROR_CODES.DOWNLOAD_FAILED);
  assert.deepEqual(log.revoked, ["blob:fake-1"]);
  assert.equal(log.removed.length, 1);
  assert.equal(log.scheduled.length, 0);
});

test("unsupported browser (no document/URL/Blob) reports download error", () => {
  const env = { now: () => FIXED, document: null, URL: null, Blob: null, setTimeout: () => {} };
  assert.throws(() => exportPreferencesJson("c", PREFS, env), (err) => err.code === ERROR_CODES.DOWNLOAD_FAILED);
});

test("payload values are never logged to the console", () => {
  const seen = [];
  const orig = { log: console.log, error: console.error, warn: console.warn, info: console.info };
  for (const k of Object.keys(orig)) console[k] = (...a) => seen.push(a);
  try {
    const { env } = fakeEnv();
    exportPreferencesJson("secret-customer-id", PREFS, env);
    env.URL.createObjectURL = () => {
      throw new Error("x");
    };
    assert.throws(() => exportPreferencesJson("secret-customer-id", PREFS, env));
  } finally {
    Object.assign(console, orig);
  }
  assert.deepEqual(seen, []);
});

test("error messages are unified and user-friendly", () => {
  assert.equal(ERROR_MESSAGES[ERROR_CODES.NOT_LOADED], "Preferences are not loaded yet. Please refresh and try again.");
  assert.equal(ERROR_MESSAGES[ERROR_CODES.INVALID], ERROR_MESSAGES[ERROR_CODES.NOT_LOADED]);
  assert.match(ERROR_MESSAGES[ERROR_CODES.DOWNLOAD_FAILED], /browser download error/);
});
