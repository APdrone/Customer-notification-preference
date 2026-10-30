# Export Notification Preferences to JSON (KAN-100)

A client-side "Export Preferences JSON" action. It serializes the notification
preferences the app has already loaded and downloads them as
`notification-preferences.json`. There is **no backend endpoint, no network call
and no server-side state change**.

## Files

| Path | Purpose |
| --- | --- |
| `web/export/exportPreferences.js` | Framework-free ES module (payload, validation, download) |
| `web/export/index.html`, `demo.js` | Demo page with **stub** customer id and preferences |
| `web/export/exportPreferences.test.js` | Unit tests (`cd web && node --test`) |
| `docs/schemas/notification-preferences-export.schema.json` | JSON Schema of the exported file |
| `tests/test_export_contract.py` | Python contract tests (`python -m pytest -q`) |

## Host app integration

```js
import { canExport, exportPreferencesJson, ExportError } from "./exportPreferences.js";

// customerId: from the VERIFIED session / JWT "sub" claim (never from user input).
// prefs: the preferences already loaded into UI state.
button.hidden = !canExport(customerId, prefs);

button.addEventListener("click", () => {
  try {
    exportPreferencesJson(customerId, prefs);
  } catch (err) {
    if (err instanceof ExportError) showBanner(err.message);
  }
});
```

The module never reads, decodes or stores a token. Only whitelisted keys are
copied from `prefs`, so extra properties cannot leak into the file.

## Export file contract

Filename: `notification-preferences.json` (fixed, not user-controlled).
MIME type `application/json`, UTF-8, 2-space indent, trailing newline.

```json
{
  "customerId": "<customerId>",
  "email": true,
  "sms": false,
  "push_notification": true,
  "exportedAt": "2026-10-30T00:00:00.000Z"
}
```

`exportedAt` is the client clock in UTC (ISO-8601, `toISOString()`), regenerated
on every export. It is client-supplied and therefore not tamper-proof. See the
schema file for the formal definition (`additionalProperties: false`).

## Error handling

| Condition | Code | Message |
| --- | --- | --- |
| customerId or preferences not loaded | `PREFERENCES_NOT_LOADED` | Preferences are not loaded yet. Please refresh and try again. |
| Preferences have the wrong shape | `PREFERENCES_INVALID` | Preferences are not loaded yet. Please refresh and try again. |
| Blob / object URL / anchor failure or unsupported browser | `DOWNLOAD_FAILED` | Export failed due to a browser download error. Please try again or use another browser. |

On any error no file is downloaded and the payload is not logged.

## Acceptance criteria (draft, Gherkin)

KAN-100 has no acceptance criteria in Jira. These are proposed for review and
have not been posted anywhere.

```gherkin
Feature: Export notification preferences to JSON

  Background:
    Given I am an authenticated customer or support agent

  Scenario: Export action is available when preferences are loaded
    Given my notification preferences are displayed
    Then I see an "Export Preferences JSON" action

  Scenario: Export action is not offered when preferences are not loaded
    Given my notification preferences have not been loaded
    Then the "Export Preferences JSON" action is not displayed

  Scenario: Download a JSON file of current preferences
    Given my preferences are email=true, sms=false, push_notification=true
    When I click "Export Preferences JSON"
    Then a file named "notification-preferences.json" is downloaded immediately
    And it contains customerId, email, sms, push_notification and exportedAt
    And email is true, sms is false and push_notification is true

  Scenario: Export timestamp is UTC and regenerated per export
    When I export my preferences twice at different times
    Then each file has an ISO-8601 UTC exportedAt ending in "Z"
    And the two exportedAt values differ

  Scenario: Export causes no backend change
    When I click "Export Preferences JSON"
    Then no network request is made
    And no server-side state or audit record is created

  Scenario: Sensitive data is excluded
    When I export my preferences
    Then the file contains no JWT or other token
    And the payload is not written to logs or telemetry

  Scenario: Preferences not loaded
    Given the export is invoked while preferences are not loaded
    Then no file is downloaded
    And I see "Preferences are not loaded yet. Please refresh and try again."

  Scenario: Browser download failure
    Given the browser cannot create or start the download
    When I click "Export Preferences JSON"
    Then no file is downloaded
    And I see "Export failed due to a browser download error. Please try again or use another browser."
```

## Design notes and deviations from the Confluence design

- The pseudocode revoked the object URL immediately after `click()`; this
  implementation delays it (`REVOKE_DELAY_MS`) because an immediate revoke can
  cancel the download in some browsers.
- The anchor is appended to the DOM before the click and removed afterwards
  (needed by some browsers, e.g. Firefox).
- The two error wordings in the design ("load" vs "refresh") are unified to
  "refresh".
- The design refers to `GET/PUT /customers/me/preferences`, JWT auth and
  `PREFERENCE_STORE` in `app/main.py`. None of these exist in this repository, so
  `customerId` and the preference values are inputs supplied by the host app.

## Running

- Python: `python -m pytest -q`
- JS: `cd web && node --test` (Node 20+, no npm dependencies)
- Demo: `cd web && python -m http.server 8000`, then open
  `http://localhost:8000/export/index.html` (ES modules need http, not file://).
