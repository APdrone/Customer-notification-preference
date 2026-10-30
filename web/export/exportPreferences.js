/**
 * Export Notification Preferences to JSON (KAN-100).
 *
 * Client-side only: serializes preferences that the host app has ALREADY loaded
 * and triggers a browser download. It performs no network calls and no backend
 * state changes. Framework-free ES module; browser globals are injectable so the
 * logic is unit-testable under Node.
 *
 * Host app contract:
 *   - customerId: identifier of the authenticated customer. It is expected to
 *     come from the verified session / JWT "sub" claim. This module does not
 *     read, decode or verify any token and never includes one in the export.
 *   - prefs: { email: boolean, sms: boolean, push_notification: boolean }
 */

export const EXPORT_FILENAME = "notification-preferences.json";
export const PREFERENCE_KEYS = Object.freeze(["email", "sms", "push_notification"]);

// Delay before revoking the object URL so the browser can start the download.
export const REVOKE_DELAY_MS = 1000;

export const ERROR_CODES = Object.freeze({
  NOT_LOADED: "PREFERENCES_NOT_LOADED",
  INVALID: "PREFERENCES_INVALID",
  DOWNLOAD_FAILED: "DOWNLOAD_FAILED",
});

// Single source of user-facing wording for the banner/toast.
export const ERROR_MESSAGES = Object.freeze({
  [ERROR_CODES.NOT_LOADED]: "Preferences are not loaded yet. Please refresh and try again.",
  [ERROR_CODES.INVALID]: "Preferences are not loaded yet. Please refresh and try again.",
  [ERROR_CODES.DOWNLOAD_FAILED]:
    "Export failed due to a browser download error. Please try again or use another browser.",
});

export class ExportError extends Error {
  constructor(code) {
    super(ERROR_MESSAGES[code]);
    this.name = "ExportError";
    this.code = code;
  }
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

/** Returns an ERROR_CODES value if the inputs cannot be exported, else null. */
function validationError(customerId, prefs) {
  if (!isNonEmptyString(customerId) || prefs === undefined || prefs === null) {
    return ERROR_CODES.NOT_LOADED;
  }
  if (typeof prefs !== "object" || PREFERENCE_KEYS.some((k) => typeof prefs[k] !== "boolean")) {
    return ERROR_CODES.INVALID;
  }
  return null;
}

/** True when the export action may be offered (use to show/enable the button). */
export function canExport(customerId, prefs) {
  return validationError(customerId, prefs) === null;
}

/**
 * Build the export payload. Only the whitelisted keys are copied, so extra
 * properties on prefs (e.g. tokens) can never leak into the file.
 * The "now" argument is an injectable clock; exportedAt is regenerated per call.
 */
export function buildExportPayload(customerId, prefs, now = new Date()) {
  const code = validationError(customerId, prefs);
  if (code) throw new ExportError(code);
  return {
    customerId,
    email: prefs.email,
    sms: prefs.sms,
    push_notification: prefs.push_notification,
    exportedAt: now.toISOString(), // always UTC ("...Z")
  };
}

/** Pretty-printed JSON text (2-space indent, trailing newline). */
export function serializePayload(payload) {
  return JSON.stringify(payload, null, 2) + "\n";
}

/**
 * Build the payload and trigger the browser download.
 * Throws ExportError (with a user-friendly message) on any failure; callers
 * show error.message in a banner/toast. Never logs the payload.
 * The env argument holds injectable browser APIs (defaults to the globals).
 * Returns the exported payload.
 */
export function exportPreferencesJson(customerId, prefs, env = {}) {
  const doc = env.document ?? globalThis.document;
  const URLApi = env.URL ?? globalThis.URL;
  const BlobApi = env.Blob ?? globalThis.Blob;
  const schedule = env.setTimeout ?? globalThis.setTimeout;
  const now = env.now ? env.now() : new Date();

  const payload = buildExportPayload(customerId, prefs, now);
  const json = serializePayload(payload);

  if (!doc || !URLApi || typeof URLApi.createObjectURL !== "function" || !BlobApi || !schedule) {
    throw new ExportError(ERROR_CODES.DOWNLOAD_FAILED);
  }

  let url = null;
  let anchor = null;
  try {
    const blob = new BlobApi([json], { type: "application/json" });
    url = URLApi.createObjectURL(blob);

    anchor = doc.createElement("a");
    anchor.href = url;
    anchor.download = EXPORT_FILENAME; // fixed name; never user-controlled
    anchor.style.display = "none";
    doc.body.appendChild(anchor); // required by some browsers (e.g. Firefox)
    anchor.click();

    // Revoke later: revoking synchronously can cancel the download.
    const toRevoke = url;
    schedule(() => URLApi.revokeObjectURL(toRevoke), REVOKE_DELAY_MS);
  } catch (_err) {
    if (url) {
      try {
        URLApi.revokeObjectURL(url);
      } catch (_ignored) {
        /* best effort */
      }
    }
    throw new ExportError(ERROR_CODES.DOWNLOAD_FAILED);
  } finally {
    if (anchor && anchor.parentNode) anchor.parentNode.removeChild(anchor);
  }
  return payload;
}
