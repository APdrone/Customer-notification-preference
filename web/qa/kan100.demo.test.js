// KAN-100 QA: demo page logic (web/export/demo.js + index.html) driven through a
// minimal fake DOM. This is NOT a real-browser test.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { overrideGlobals } from "./helpers.js";

const HTML = readFileSync(new URL("../export/index.html", import.meta.url), "utf8");
const DEMO_URL = new URL("../export/demo.js", import.meta.url).href;
const MSG_NOT_LOADED = "Preferences are not loaded yet. Please refresh and try again.";
const MSG_DOWNLOAD_FAILED = "Export failed due to a browser download error. Please try again or use another browser.";

function tagFor(id) {
  const m = HTML.match(new RegExp("<[^>]*[ ]id=\"" + id + "\"[^>]*>"));
  assert.ok(m, `index.html has element #${id}`);
  return m[0];
}

let caseNo = 0;

/** Loads demo.js against a fake DOM seeded from the initial `hidden` attributes in index.html. */
async function bootDemo({ failDownload = false } = {}) {
  const els = {};
  for (const id of ["load", "export", "banner", "prefs"]) {
    const listeners = {};
    els[id] = {
      id,
      hidden: /\bhidden\b/.test(tagFor(id)),
      textContent: "",
      listeners,
      addEventListener(t, fn) { (listeners[t] ??= []).push(fn); },
      click() { if (!this.hidden) (listeners.click ?? []).forEach((fn) => fn({})); },
      fire() { (listeners.click ?? []).forEach((fn) => fn({})); }, // bypass visibility (programmatic call)
    };
  }
  const downloads = [];
  const body = { appendChild(el) { el.parentNode = body; }, removeChild(el) { el.parentNode = null; } };
  const document = {
    body,
    getElementById: (id) => els[id],
    createElement() {
      return {
        style: {}, parentNode: null,
        click() { if (failDownload) throw new Error("boom"); downloads.push({ href: this.href, download: this.download }); },
      };
    },
  };
  const realCreate = URL.createObjectURL;
  const realRevoke = URL.revokeObjectURL;
  let n = 0;
  const blobs = [];
  URL.createObjectURL = (b) => { blobs.push(b); return `blob:demo/${++n}`; };
  URL.revokeObjectURL = () => {};
  const restoreGlobals = overrideGlobals({ document, setTimeout: () => 0 });
  await import(`${DEMO_URL}?case=${++caseNo}`);
  return {
    els, downloads, blobs,
    restore() { URL.createObjectURL = realCreate; URL.revokeObjectURL = realRevoke; restoreGlobals(); },
  };
}

test("index.html: export button is hidden initially, banner is a hidden alert, module script is wired", () => {
  assert.match(tagFor("export"), /\bhidden\b/);
  assert.ok(!/\bdisabled\b/.test(tagFor("export")), "uses hidden (not disabled) per AC2");
  assert.match(tagFor("banner"), /role="alert"/);
  assert.match(tagFor("banner"), /\bhidden\b/);
  assert.match(tagFor("export"), />/);
  assert.ok(/<button[^>]*id="export"[^>]*>\s*Export Preferences JSON\s*<\/button>/.test(HTML), "button label");
  assert.match(HTML, /<script type="module" src="\.\/demo\.js"><\/script>/);
  assert.match(HTML, /<meta charset="utf-8"/i);
});

test("demo AC2: before preferences load the export button is hidden and nothing is shown", async () => {
  const d = await bootDemo();
  try {
    assert.equal(d.els.export.hidden, true);
    assert.equal(d.els.banner.hidden, true);
    assert.equal(d.els.prefs.textContent, "(not loaded)");
  } finally { d.restore(); }
});

test("demo AC1: after load the export button appears and shows the loaded preferences", async () => {
  const d = await bootDemo();
  try {
    d.els.load.click();
    assert.equal(d.els.export.hidden, false);
    assert.deepEqual(JSON.parse(d.els.prefs.textContent), { email: true, sms: false, push_notification: true });
  } finally { d.restore(); }
});

test("demo AC3: clicking export downloads notification-preferences.json with stub values, no banner", async () => {
  const d = await bootDemo();
  try {
    d.els.load.click();
    d.els.export.click();
    assert.equal(d.downloads.length, 1);
    assert.equal(d.downloads[0].download, "notification-preferences.json");
    assert.equal(d.els.banner.hidden, true);
    const o = JSON.parse(await d.blobs[0].text());
    assert.equal(o.customerId, "demo-customer-STUB-001");
    assert.deepEqual([o.email, o.sms, o.push_notification], [true, false, true]);
    assert.equal(d.blobs[0].type, "application/json");
  } finally { d.restore(); }
});

test("demo AC7: export handler invoked while not loaded -> no download, exact banner message", async () => {
  const d = await bootDemo();
  try {
    d.els.export.fire(); // button is hidden, but guard the handler itself
    assert.equal(d.downloads.length, 0);
    assert.equal(d.els.banner.hidden, false);
    assert.equal(d.els.banner.textContent, MSG_NOT_LOADED);
  } finally { d.restore(); }
});

test("demo AC8: browser download failure -> no file, exact banner message; reload clears banner", async () => {
  const d = await bootDemo({ failDownload: true });
  try {
    d.els.load.click();
    d.els.export.click();
    assert.equal(d.downloads.length, 0);
    assert.equal(d.els.banner.hidden, false);
    assert.equal(d.els.banner.textContent, MSG_DOWNLOAD_FAILED);
    d.els.load.click();
    assert.equal(d.els.banner.hidden, true, "banner cleared when preferences are (re)loaded");
  } finally { d.restore(); }
});

test("demo: a successful retry clears a previous error banner; repeated exports each download", async () => {
  const d = await bootDemo();
  try {
    d.els.export.fire();
    assert.equal(d.els.banner.hidden, false);
    d.els.load.click();
    d.els.export.click();
    d.els.export.click();
    d.els.export.click();
    assert.equal(d.downloads.length, 3);
    assert.equal(d.els.banner.hidden, true);
  } finally { d.restore(); }
});

test("demo: export does not change displayed preferences; each Load gives a fresh copy of stub prefs", async () => {
  const d = await bootDemo();
  try {
    d.els.load.click();
    const before = d.els.prefs.textContent;
    d.els.export.click();
    assert.equal(d.els.prefs.textContent, before);
  } finally { d.restore(); }
});

test("demo source: no network/storage/logging and stub data is clearly labelled", () => {
  const src = readFileSync(new URL("../export/demo.js", import.meta.url), "utf8");
  for (const bad of ["fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "console.", "document.cookie", "innerHTML"]) {
    assert.ok(!src.includes(bad), `demo.js must not use ${bad}`);
  }
  assert.match(src, /STUB/);
  assert.match(HTML, /stubs?/i);
});
