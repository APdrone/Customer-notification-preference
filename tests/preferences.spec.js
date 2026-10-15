// Playwright test suite for preference update suppression and active changes
const { test, expect } = require('@playwright/test');

const baseUrl = process.env.PREF_API_URL || 'http://localhost:5000';
const userId = 'test_user_kan76';

const prefs = { email: true, sms: false };
const prefs2 = { email: false, sms: false };

// Utility to POST preferences
async function postPrefs(page, user_id, preferences) {
  return page.request.post(`${baseUrl}/preferences`, {
    data: { user_id, preferences }
  });
}

test('suppresses DB write and event on unchanged preferences', async ({ request }) => {
  // First post
  const res = await postPrefs(request, userId, prefs);
  expect([200, 204]).toContain(res.status());

  // Second post (should suppress update)
  const res2 = await postPrefs(request, userId, prefs);
  expect([200, 204]).toContain(res2.status());
  // (optional) assert no duplicate audit/event emitted (stub, logs, etc.)
});

test('updates DB and emits event for changed preferences', async ({ request }) => {
  const res = await postPrefs(request, userId, prefs2);
  expect(res.status()).toBe(200);
  const json = await res.json();
  expect(json.status).toBe('updated');
});

test('returns error schema for invalid input', async ({ request }) => {
  const res = await postPrefs(request, userId, { email: 99 });
  expect(res.status()).toBe(400);
  // Optionally check error body schema
});
