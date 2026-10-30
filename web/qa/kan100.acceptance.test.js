// KAN-100 QA acceptance tests (independent of exportPreferences.test.js).
// Run:  cd web && node --test qa/
import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

import {
  EXPORT_FILENAME, ERROR_CODES, ERROR_MESSAGES, REVOKE_DELAY_MS, ExportError,
  buildExportPayload, canExport, exportPreferencesJson, serializePayload,
} from "../export/exportPreferences.js";
import {
  GOOD_PREFS, MODULE_URL, MSG_NOT_LOADED, MSG_DOWNLOAD_FAILED,
  makeEnv, fileText, spyConsole, overrideGlobals,
} from "./helpers.js";

const T1 = new Date("2026-10-30T10:00:00.000Z");
const T2 = new Date("2026-10-30T10:00:05.123Z");

// ---------------------------------------------------------------- AC1 / AC2
test("AC1 export offered when customerId and well-formed preferences are loaded", () => {
  assert.equal(canExport("cust-1", GOOD_PREFS), true);
  for (const e of [true, false]) for (const s of [true, false]) for (const p of [true, false]) {
    assert.equal(canExport("cust-1", { email: e, sms: s, push_notification: p }), true);
  }
});

const NOT_LOADED_CASES = [
  ["prefs undefined", "c", undefined],
  ["prefs null", "c", null],
  ["customerId undefined", undefined, GOOD_PREFS],
  ["customerId null", null, GOOD_PREFS],
  ["customerId empty", "", GOOD_PREFS],
  ["customerId spaces", "   ", GOOD_PREFS],
  ["customerId tab/newline", "\t\n ", GOOD_PREFS],
  ["customerId number", 123, GOOD_PREFS],
  ["customerId zero", 0, GOOD_PREFS],
  ["customerId object", { id: "x" }, GOOD_PREFS],
  ["customerId array", ["x"], GOOD_PREFS],
  ["customerId boolean", true, GOOD_PREFS],
];
const INVALID_CASES = [
  ["empty object", {}],
  ["missing email", { sms: true, push_notification: true }],
  ["missing sms", { email: true, push_notification: true }],
  ["missing push_notification", { email: true, sms: true }],
  ["email string true", { email: "true", sms: false, push_notification: true }],
  ["sms number 1", { email: true, sms: 1, push_notification: true }],
  ["push number 0", { email: true, sms: true, push_notification: 0 }],
  ["email null", { email: null, sms: true, push_notification: true }],
  ["sms undefined", { email: true, sms: undefined, push_notification: true }],
  ["boxed Boolean", { email: new Boolean(true), sms: false, push_notification: true }],
  ["camelCase pushNotification instead of snake_case", { email: true, sms: true, pushNotification: true }],
  ["array", [true, false, true]],
  ["string", "email,sms"],
  ["number", 42],
  ["boolean", true],
  ["function", () => ({})],
];

test("AC2 export not offered for any not-loaded / malformed input", () => {
  for (const [name, id, prefs] of NOT_LOADED_CASES) assert.equal(canExport(id, prefs), false, name);
  for (const [name, prefs] of INVALID_CASES) assert.equal(canExport("c", prefs), false, name);
});

// ---------------------------------------------------------------- AC3
test("AC3 download: fixed filename, application/json, pretty JSON, exact keys and types", async () => {
  const { env, log } = makeEnv({ now: T1 });
  const ret = exportPreferencesJson("cust-42", GOOD_PREFS, env);

  assert.equal(log.clicks.length, 1, "click exactly once (download immediate, single)");
  assert.equal(log.clicks[0].download, "notification-preferences.json");
  assert.equal(EXPORT_FILENAME, "notification-preferences.json");
  assert.equal(log.clicks[0].href, log.urls[0].url, "anchor points at the created object URL");
  assert.equal(log.blobs.length, 1);
  assert.equal(log.blobs[0].type, "application/json");

  const text = await fileText(log);
  const obj = JSON.parse(text);
  assert.deepEqual(Object.keys(obj), ["customerId", "email", "sms", "push_notification", "exportedAt"]);
  assert.equal(obj.customerId, "cust-42");
  assert.strictEqual(obj.email, true);
  assert.strictEqual(obj.sms, false);
  assert.strictEqual(obj.push_notification, true);
  assert.equal(typeof obj.exportedAt, "string");
  assert.deepEqual(obj, ret, "returned payload equals file content");

  // pretty-printed, 2-space indent, LF, trailing newline
  assert.equal(text, JSON.stringify(obj, null, 2) + "\n");
  assert.ok(text.startsWith("{\n  \"customerId\": \"cust-42\",\n"));
  assert.ok(!text.includes("\r"));
  assert.ok(text.endsWith("}\n"));
});

test("AC3 every boolean combination is written exactly (no coercion, no defaults)", async () => {
  for (const e of [true, false]) for (const s of [true, false]) for (const p of [true, false]) {
    const { env, log } = makeEnv({ now: T1 });
    exportPreferencesJson("c", { email: e, sms: s, push_notification: p }, env);
    const o = JSON.parse(await fileText(log));
    assert.deepEqual([o.email, o.sms, o.push_notification], [e, s, p]);
  }
});

test("AC3 anchor is hidden, in the DOM at click time, and removed afterwards", () => {
  const { env, log, dom } = makeEnv({ now: T1 });
  exportPreferencesJson("c", GOOD_PREFS, env);
  assert.equal(log.anchors.length, 1);
  assert.equal(log.anchors[0].tagName, "A");
  assert.equal(log.clicks[0].inDom, true);
  assert.equal(log.clicks[0].display, "none");
  assert.equal(dom.size, 0, "no anchor left in DOM");
  assert.equal(log.removed.length, 1);
});

test("AC3 object URL is revoked later (not synchronously) and only once with the right URL", () => {
  const { env, log } = makeEnv({ now: T1 });
  exportPreferencesJson("c", GOOD_PREFS, env);
  assert.deepEqual(log.revoked, [], "no synchronous revoke (would cancel download)");
  assert.equal(log.timers.length, 1);
  assert.ok(log.timers[0].ms >= 100, `revoke delay should be non-trivial, got ${log.timers[0].ms}`);
  assert.equal(log.timers[0].ms, REVOKE_DELAY_MS);
  log.timers[0].fn();
  assert.deepEqual(log.revoked, [log.urls[0].url]);
});

// ---------------------------------------------------------------- AC4
test("AC4 exportedAt is ISO-8601 UTC with Z, equals injected clock, differs per export", async () => {
  const clocks = [T1, T2];
  let i = 0;
  const { env, log } = makeEnv({ now: () => clocks[i++] });
  exportPreferencesJson("c", GOOD_PREFS, env);
  exportPreferencesJson("c", GOOD_PREFS, env);
  const a = JSON.parse(await fileText(log, 0)).exportedAt;
  const b = JSON.parse(await fileText(log, 1)).exportedAt;
  for (const v of [a, b]) {
    assert.match(v, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/);
    assert.ok(!Number.isNaN(Date.parse(v)));
    assert.equal(new Date(v).toISOString(), v, "round-trips as canonical UTC ISO");
  }
  assert.equal(a, "2026-10-30T10:00:00.000Z");
  assert.equal(b, "2026-10-30T10:00:05.123Z");
  assert.notEqual(a, b);
});

test("AC4 without injected clock the real clock is used (bounded by before/after)", async () => {
  const { env, log } = makeEnv();
  const before = Date.now();
  exportPreferencesJson("c", GOOD_PREFS, env);
  await new Promise((r) => setTimeout(r, 15));
  exportPreferencesJson("c", GOOD_PREFS, env);
  const after = Date.now();
  const a = Date.parse(JSON.parse(await fileText(log, 0)).exportedAt);
  const b = Date.parse(JSON.parse(await fileText(log, 1)).exportedAt);
  assert.ok(a >= before && a <= after);
  assert.ok(b > a, "second export has a later timestamp (regenerated, not cached)");
});

test("AC4 exportedAt is UTC regardless of process time zone", () => {
  const script =
    `import(${JSON.stringify(MODULE_URL.href)}).then(m=>{` +
    `console.log(m.buildExportPayload("c",{email:true,sms:true,push_notification:true},` +
    `new Date("2026-10-30T23:30:00+05:30")).exportedAt)})`;
  for (const tz of ["Asia/Kolkata", "Pacific/Auckland", "America/Los_Angeles", "UTC"]) {
    const r = spawnSync(process.execPath, ["-e", script], { env: { ...process.env, TZ: tz }, encoding: "utf8" });
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stdout.trim(), "2026-10-30T18:00:00.000Z", `TZ=${tz}`);
  }
});

// ---------------------------------------------------------------- AC5
test("AC5 export makes no network call and touches no storage/cookies/beacon", () => {
  const hits = [];
  const trap = (name) => ({
    configurable: true,
    get() { hits.push(name); return () => { hits.push(name + "()"); throw new Error(name + " used"); }; },
  });
  const names = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "localStorage", "sessionStorage", "indexedDB", "caches"];
  const saved = {};
  for (const n of names) {
    saved[n] = Object.getOwnPropertyDescriptor(globalThis, n);
    Object.defineProperty(globalThis, n, trap(n));
  }
  const nav = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  try {
    Object.defineProperty(globalThis, "navigator", {
      configurable: true,
      value: { get sendBeacon() { hits.push("sendBeacon"); return () => {}; } },
    });
    const ok = makeEnv({ now: T1 });
    exportPreferencesJson("c", GOOD_PREFS, ok.env);
    const f = makeEnv({ now: T1, clickThrows: true });
    assert.throws(() => exportPreferencesJson("c", GOOD_PREFS, f.env), ExportError);
    assert.throws(() => exportPreferencesJson("c", undefined, f.env), ExportError);
    assert.equal(ok.log.cookieAccess + f.log.cookieAccess, 0, "document.cookie untouched");
  } finally {
    for (const n of names) {
      if (saved[n]) Object.defineProperty(globalThis, n, saved[n]); else delete globalThis[n];
    }
    if (nav) Object.defineProperty(globalThis, "navigator", nav); else delete globalThis.navigator;
  }
  assert.deepEqual(hits, [], "no network/storage API was touched");
});

test("AC5 module source has no imports and no network/storage/cookie/log APIs", () => {
  const src = readFileSync(MODULE_URL, "utf8");
  const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  assert.ok(!/^\s*import\s/m.test(code), "no static imports");
  assert.ok(!/\bimport\s*\(/.test(code), "no dynamic imports");
  for (const bad of ["fetch", "XMLHttpRequest", "sendBeacon", "WebSocket", "localStorage", "sessionStorage", "indexedDB", "document.cookie", "console."]) {
    assert.ok(!code.includes(bad), `forbidden API in code: ${bad}`);
  }
});

// ---------------------------------------------------------------- AC6
test("AC6 extra / sensitive properties never reach payload or file", async () => {
  const SECRET = "SECRET-xyz-123";
  const prefs = {
    email: true, sms: false, push_notification: true,
    token: SECRET, password: SECRET, jwt: SECRET, accessToken: SECRET, Authorization: `Bearer ${SECRET}`,
    nested: { token: SECRET }, customerId: "attacker-id", exportedAt: "1999-01-01T00:00:00Z",
  };
  Object.defineProperty(prefs, "hidden", { value: SECRET, enumerable: false });
  const { env, log } = makeEnv({ now: T1 });
  const ret = exportPreferencesJson("real-id", prefs, env);
  const text = await fileText(log);
  assert.ok(!text.includes(SECRET));
  assert.ok(!/token|password|jwt|authorization|bearer|nested|hidden/i.test(text));
  assert.deepEqual(Object.keys(JSON.parse(text)), ["customerId", "email", "sms", "push_notification", "exportedAt"]);
  assert.equal(JSON.parse(text).customerId, "real-id", "prefs.customerId cannot override session customerId");
  assert.equal(JSON.parse(text).exportedAt, T1.toISOString(), "prefs.exportedAt cannot override timestamp");
  assert.ok(!JSON.stringify(ret).includes(SECRET));
});

test("AC6 payload / customerId are never logged on success or failure paths", () => {
  const spy = spyConsole();
  try {
    const ok = makeEnv({ now: T1 });
    exportPreferencesJson("PII-CUSTOMER-777", GOOD_PREFS, ok.env);
    for (const o of [{ clickThrows: true }, { blobThrows: true }, { createUrlThrows: true }]) {
      assert.throws(() => exportPreferencesJson("PII-CUSTOMER-777", GOOD_PREFS, makeEnv(o).env), ExportError);
    }
    assert.throws(() => exportPreferencesJson("PII-CUSTOMER-777", {}, ok.env), ExportError);
  } finally { spy.restore(); }
  assert.deepEqual(spy.calls, [], "nothing written to console");
});

test("AC6 ExportError messages/stack do not contain payload values", () => {
  for (const o of [{ clickThrows: true }, { blobThrows: true }, { noBody: true }]) {
    let err;
    try { exportPreferencesJson("PII-CUSTOMER-777", GOOD_PREFS, makeEnv(o).env); } catch (e) { err = e; }
    assert.ok(err instanceof ExportError);
    assert.ok(!err.message.includes("PII-CUSTOMER-777"));
    assert.ok(!String(err.stack).includes("PII-CUSTOMER-777"));
    assert.equal(err.cause, undefined, "no leaked underlying error");
  }
});

// ---------------------------------------------------------------- AC7
test("AC7 not loaded: ExportError with exact wording, no file, no DOM, no URL", () => {
  const all = [
    ...NOT_LOADED_CASES.map(([n, id, p]) => [n, id, p, ERROR_CODES.NOT_LOADED]),
    ...INVALID_CASES.map(([n, p]) => [n, "c", p, ERROR_CODES.INVALID]),
  ];
  for (const [name, id, prefs, code] of all) {
    const { env, log } = makeEnv({ now: T1 });
    let err;
    try { exportPreferencesJson(id, prefs, env); } catch (e) { err = e; }
    assert.ok(err instanceof ExportError, name);
    assert.ok(err instanceof Error, name);
    assert.equal(err.code, code, name);
    assert.equal(err.message, MSG_NOT_LOADED, name);
    assert.equal(log.blobs.length + log.urls.length + log.anchors.length + log.clicks.length + log.timers.length, 0, `${name}: no download side effects`);
  }
});

test("AC7 user-facing strings match the Confluence design literally", () => {
  assert.equal(ERROR_MESSAGES[ERROR_CODES.NOT_LOADED], MSG_NOT_LOADED);
  assert.equal(ERROR_MESSAGES[ERROR_CODES.INVALID], MSG_NOT_LOADED);
  assert.equal(ERROR_MESSAGES[ERROR_CODES.DOWNLOAD_FAILED], MSG_DOWNLOAD_FAILED);
  assert.equal(new ExportError(ERROR_CODES.NOT_LOADED).name, "ExportError");
});

test("AC7 buildExportPayload / serializePayload also reject unloaded input", () => {
  assert.throws(() => buildExportPayload("c", undefined, T1), (e) => e.code === ERROR_CODES.NOT_LOADED);
  assert.throws(() => buildExportPayload("", GOOD_PREFS, T1), (e) => e.code === ERROR_CODES.NOT_LOADED);
  assert.throws(() => buildExportPayload("c", { email: 1, sms: 1, push_notification: 1 }, T1), (e) => e.code === ERROR_CODES.INVALID);
  assert.equal(serializePayload({ a: 1 }), "{\n  \"a\": 1\n}\n");
});

// ---------------------------------------------------------------- AC8
const FAIL_CASES = [
  ["Blob constructor throws", { blobThrows: true }],
  ["createObjectURL throws", { createUrlThrows: true }],
  ["createObjectURL missing (unsupported browser)", { noCreateObjectURL: true }],
  ["document.createElement throws", { createElementThrows: true }],
  ["appendChild throws", { appendThrows: true }],
  ["anchor.click throws", { clickThrows: true }],
  ["document.body is null", { noBody: true }],
];

test("AC8 download failures surface DOWNLOAD_FAILED with exact wording and leave no residue", () => {
  for (const [name, opts] of FAIL_CASES) {
    const { env, log, dom } = makeEnv({ now: T1, ...opts });
    let err;
    try { exportPreferencesJson("c", GOOD_PREFS, env); } catch (e) { err = e; }
    assert.ok(err instanceof ExportError, name);
    assert.equal(err.code, ERROR_CODES.DOWNLOAD_FAILED, name);
    assert.equal(err.message, MSG_DOWNLOAD_FAILED, name);
    assert.equal(dom.size, 0, `${name}: anchor not left in DOM`);
    assert.deepEqual(log.timers, [], `${name}: no revoke timer scheduled after failure`);
    assert.deepEqual(log.revoked, log.urls.map((u) => u.url), `${name}: created URLs revoked`);
  }
});

test("AC8 revokeObjectURL throwing during cleanup is swallowed; DOWNLOAD_FAILED still raised", () => {
  const { env } = makeEnv({ now: T1, clickThrows: true });
  env.URL.revokeObjectURL = () => { throw new Error("revoke boom"); };
  assert.throws(() => exportPreferencesJson("c", GOOD_PREFS, env), (e) => e.code === ERROR_CODES.DOWNLOAD_FAILED);
});

test("AC8 missing browser globals (no document / URL / Blob / setTimeout) -> DOWNLOAD_FAILED, no crash", () => {
  for (const name of ["document", "URL", "Blob", "setTimeout"]) {
    const restore = overrideGlobals({ [name]: undefined });
    try {
      const { env } = makeEnv({ now: T1 });
      env[name] = undefined; // fall through to the (now removed) global
      assert.throws(
        () => exportPreferencesJson("c", GOOD_PREFS, env),
        (e) => e instanceof ExportError && e.code === ERROR_CODES.DOWNLOAD_FAILED && e.message === MSG_DOWNLOAD_FAILED,
        name,
      );
    } finally { restore(); }
  }
});

test("AC8 not-loaded takes precedence over unsupported browser", () => {
  assert.throws(() => exportPreferencesJson("c", undefined, {}), (e) => e.code === ERROR_CODES.NOT_LOADED);
});

// ---------------------------------------------------------------- Robustness
test("export does not mutate the host preferences object or customerId", () => {
  const prefs = Object.freeze({ email: true, sms: false, push_notification: true, extra: Object.freeze({ a: 1 }) });
  const snapshot = JSON.stringify(prefs);
  const { env, log } = makeEnv({ now: T1 });
  const ret = exportPreferencesJson("c", prefs, env);
  assert.equal(JSON.stringify(prefs), snapshot);
  assert.notStrictEqual(ret, prefs);
  ret.email = false; // mutating returned payload must not affect host state
  assert.equal(prefs.email, true);
  assert.equal(log.blobs.length, 1);
});

test("repeated exports: N clicks, N independent URLs, N revokes, no DOM growth, stable content", async () => {
  const { env, log, dom } = makeEnv({ now: T1 });
  for (let i = 0; i < 25; i++) exportPreferencesJson("c", GOOD_PREFS, env);
  assert.equal(log.clicks.length, 25);
  assert.equal(new Set(log.urls.map((u) => u.url)).size, 25);
  assert.equal(log.timers.length, 25);
  log.timers.forEach((t) => t.fn());
  assert.deepEqual(log.revoked, log.urls.map((u) => u.url));
  assert.equal(dom.size, 0);
  const texts = await Promise.all(log.urls.map((u) => u.blob.text()));
  assert.equal(new Set(texts).size, 1);
});

test("export after a failed export works (no sticky state)", () => {
  const bad = makeEnv({ now: T1, clickThrows: true });
  assert.throws(() => exportPreferencesJson("c", GOOD_PREFS, bad.env), ExportError);
  const good = makeEnv({ now: T1 });
  exportPreferencesJson("c", GOOD_PREFS, good.env);
  assert.equal(good.log.clicks.length, 1);
});

test("customerId edge cases are preserved verbatim, JSON-escaped, and never affect the filename", async () => {
  const ids = ["  padded  ", "a\"b\c", "line1\nline2", "</script><b>", "ünïcødé-日本語-😀", "x".repeat(10000), "__proto__", "0", "a/b\..\evil.json"];
  for (const id of ids) {
    const { env, log } = makeEnv({ now: T1 });
    exportPreferencesJson(id, GOOD_PREFS, env);
    assert.equal(JSON.parse(await fileText(log)).customerId, id);
    assert.equal(log.clicks[0].download, EXPORT_FILENAME);
  }
});

test("file bytes are UTF-8 without BOM", async () => {
  const { env, log } = makeEnv({ now: T1 });
  exportPreferencesJson("日本語", GOOD_PREFS, env);
  const bytes = new Uint8Array(await log.urls[0].blob.arrayBuffer());
  assert.notDeepEqual([...bytes.slice(0, 3)], [0xef, 0xbb, 0xbf]);
  assert.equal(bytes[0], 0x7b);
  assert.equal(JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)).customerId, "日本語");
});

test("inherited (prototype) preference values are accepted but extra inherited keys stay out", () => {
  const prefs = Object.create({ email: true, sms: false, push_notification: true, token: "t" });
  assert.equal(canExport("c", prefs), true);
  assert.ok(!("token" in buildExportPayload("c", prefs, T1)));
});
