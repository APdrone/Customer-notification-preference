// Demo wiring for the export module. STUB DATA ONLY: a real host app supplies
// customerId (from the verified session / JWT "sub") and the loaded preferences.
import { canExport, exportPreferencesJson, ExportError } from "./exportPreferences.js";

const STUB_CUSTOMER_ID = "demo-customer-STUB-001";
const STUB_PREFERENCES = { email: true, sms: false, push_notification: true };

const state = { customerId: STUB_CUSTOMER_ID, prefs: undefined };

const loadBtn = document.getElementById("load");
const exportBtn = document.getElementById("export");
const banner = document.getElementById("banner");
const view = document.getElementById("prefs");

function showError(message) {
  banner.textContent = message;
  banner.hidden = false;
}

function render() {
  exportBtn.hidden = !canExport(state.customerId, state.prefs);
  view.textContent = state.prefs ? JSON.stringify(state.prefs) : "(not loaded)";
}

loadBtn.addEventListener("click", () => {
  state.prefs = { ...STUB_PREFERENCES }; // simulates a completed load of preferences
  banner.hidden = true;
  render();
});

exportBtn.addEventListener("click", () => {
  banner.hidden = true;
  try {
    exportPreferencesJson(state.customerId, state.prefs);
  } catch (err) {
    showError(err instanceof ExportError ? err.message : "Export failed. Please try again.");
  }
});

render();
