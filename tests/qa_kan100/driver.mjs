// Test driver (KAN-100 QA): runs the REAL export module under Node with a fake
// browser env + real Blob. stdin: JSON {cases:[{id, customerId, prefs, hasPrefs, now}]}
// stdout: JSON array of {ok, text, filename, mime, code, message}.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const modPath = process.argv[2];
const m = await import(pathToFileURL(modPath).href);
const input = JSON.parse(readFileSync(0, "utf8"));

if (input.meta) {
  console.log(JSON.stringify({
    PREFERENCE_KEYS: m.PREFERENCE_KEYS, EXPORT_FILENAME: m.EXPORT_FILENAME,
    ERROR_CODES: m.ERROR_CODES, ERROR_MESSAGES: m.ERROR_MESSAGES,
    exports: Object.keys(m).sort(),
  }));
} else {
  const out = [];
  for (const c of input.cases) {
    const urls = []; const clicks = [];
    const env = {
      now: () => new Date(c.now ?? "2026-10-30T00:00:00Z"),
      Blob,
      URL: { createObjectURL: (b) => { urls.push(b); return "blob:t/1"; }, revokeObjectURL() {} },
      setTimeout: () => 0,
      document: {
        body: { appendChild(e) { e.parentNode = this; }, removeChild(e) { e.parentNode = null; } },
        createElement: () => ({ style: {}, click() { clicks.push({ download: this.download }); } }),
      },
    };
    const prefs = c.hasPrefs === false ? undefined : c.prefs;
    try {
      m.exportPreferencesJson(c.customerId, prefs, env);
      out.push({ ok: true, text: await urls[0].text(), mime: urls[0].type, filename: clicks[0].download });
    } catch (e) {
      out.push({ ok: false, code: e.code, message: e.message, name: e.name });
    }
  }
  console.log(JSON.stringify(out));
}
