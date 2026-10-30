// QA helpers for KAN-100 acceptance tests (not a test file; no app code changed).
// The fake environment uses the REAL Node Blob so file content/MIME can be read back.
import { pathToFileURL } from "node:url";

const RealBlob = globalThis.Blob;
export const GOOD_PREFS = Object.freeze({ email: true, sms: false, push_notification: true });
export const MODULE_URL = new URL("../export/exportPreferences.js", import.meta.url);
export const MODULE_PATH = MODULE_URL.pathname.replace(/^\/([A-Za-z]:)/, "$1");
export { pathToFileURL };

export const MSG_NOT_LOADED = "Preferences are not loaded yet. Please refresh and try again.";
export const MSG_DOWNLOAD_FAILED =
  "Export failed due to a browser download error. Please try again or use another browser.";

/**
 * Build an injectable browser env. Options make individual APIs fail:
 *   blobThrows, createUrlThrows, createElementThrows, appendThrows, clickThrows,
 *   noBody, noDocument, noCreateObjectURL, noBlob, noSchedule, now
 */
export function makeEnv(o = {}) {
  const log = {
    blobs: [], urls: [], revoked: [], timers: [], appended: [], removed: [],
    clicks: [], anchors: [], cookieAccess: 0,
  };
  const dom = new Set();
  const body = {
    appendChild(el) {
      if (o.appendThrows) throw new Error("append boom");
      el.parentNode = body;
      dom.add(el);
      log.appended.push(el);
      return el;
    },
    removeChild(el) {
      dom.delete(el);
      el.parentNode = null;
      log.removed.push(el);
      return el;
    },
  };
  const document = {
    body: o.noBody ? null : body,
    get cookie() { log.cookieAccess++; return ""; },
    set cookie(_v) { log.cookieAccess++; },
    createElement(tag) {
      if (o.createElementThrows) throw new Error("createElement boom");
      const a = {
        tagName: String(tag).toUpperCase(), style: {}, parentNode: null,
        click() {
          log.clicks.push({
            href: this.href, download: this.download,
            inDom: dom.has(this), display: this.style.display,
          });
          if (o.clickThrows) throw new Error("click boom");
        },
      };
      log.anchors.push(a);
      return a;
    },
  };
  class RecordingBlob extends RealBlob {
    constructor(parts, opts) {
      if (o.blobThrows) throw new Error("blob boom");
      super(parts, opts);
      log.blobs.push(this);
    }
  }
  let n = 0;
  const URLApi = {
    createObjectURL(blob) {
      if (o.createUrlThrows) throw new Error("createObjectURL boom");
      const url = `blob:qa/${++n}`;
      log.urls.push({ url, blob });
      return url;
    },
    revokeObjectURL(u) { log.revoked.push(u); },
  };
  if (o.noCreateObjectURL) delete URLApi.createObjectURL;
  const env = {
    document: o.noDocument ? undefined : document,
    URL: URLApi,
    Blob: o.noBlob ? undefined : RecordingBlob,
    setTimeout: o.noSchedule ? undefined : (fn, ms) => { log.timers.push({ fn, ms }); return log.timers.length; },
  };
  if (o.now) env.now = typeof o.now === "function" ? o.now : () => o.now;
  // `undefined` values in env fall through (??) to globals, so null-out explicitly.
  if (o.noDocument) env.document = null;
  if (o.noBlob) env.Blob = null;
  if (o.noSchedule) env.setTimeout = null;
  return { env, log, dom };
}

export async function fileText(log, i = 0) {
  return log.urls[i].blob.text();
}

/** Capture/restore console methods so tests can assert nothing is logged. */
export function spyConsole() {
  const names = ["log", "info", "warn", "error", "debug", "trace", "dir", "table"];
  const orig = {}; const calls = [];
  for (const k of names) {
    orig[k] = console[k];
    console[k] = (...args) => { calls.push([k, args]); };
  }
  return { calls, restore() { for (const k of names) console[k] = orig[k]; } };
}

/** Temporarily replace/remove globals (value === undefined removes). Returns restore(). */
export function overrideGlobals(map) {
  const saved = {};
  for (const [k, v] of Object.entries(map)) {
    saved[k] = Object.getOwnPropertyDescriptor(globalThis, k);
    if (v === undefined) delete globalThis[k];
    else Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  }
  return () => {
    for (const [k, d] of Object.entries(saved)) {
      if (d) Object.defineProperty(globalThis, k, d); else delete globalThis[k];
    }
  };
}
