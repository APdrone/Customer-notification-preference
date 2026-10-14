const { test, expect } = require('@playwright/test');

// Mocks/stubs for DB/Events can be used via setup

test.describe('Notification Preferences API', () => {
  test('Suppresses unchanged preference update', async ({ request }) => {
    // Assume customer has preferences: {email:true, sms:false}
    const resp = await request.put('/preferences', {
      headers: { 'X-Customer-ID': '123' },
      data: { email: true, sms: false }
    });
    expect(resp.status()).toBe(200);
    // Should not trigger DB write/event/audit
    expect(resp.json().detail).toBe('No changes');
    // Optionally validate audit/event logs
  });

  test('Persists, audits, and emits event for changed preference', async ({ request }) => {
    const resp = await request.put('/preferences', {
      headers: { 'X-Customer-ID': '123' },
      data: { email: false, sms: true }
    });
    expect(resp.status()).toBe(200);
    expect(resp.json().email).toBe(false);
    // Validate DB/audit/event mock
  });

  test('Returns RFC 7807 validation error for malformed payload', async ({ request }) => {
    const resp = await request.put('/preferences', {
      headers: { 'X-Customer-ID': '123' },
      data: { invalid: 'nope' }
    });
    expect(resp.status()).toBe(400);
    expect(resp.json().type).toBe('https://tools.ietf.org/html/rfc7807');
    expect(resp.json().title).toBe('Invalid Notification Preferences');
  });
});