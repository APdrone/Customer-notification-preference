# Required field indicator (KAN-96 / KAN-97 / KAN-98)

Endpoints (public, read-only):

- `GET /api/v1/forms` - list registered form keys
- `GET /api/v1/forms/{formKey}` - field metadata (400 invalid key, 404 unknown)

Rendering rule: `label = baseLabel + (required ? " *" : "")`.
The API already returns this as `displayLabel`, so clients can render it as-is.
The indicator is visual only and never changes validation.

```jsx
// React reference
const FieldLabel = ({ field }) => (
  <label htmlFor={field.key}>
    {field.label}
    {field.required && <span aria-hidden="true"> {meta.requiredIndicator}</span>}
  </label>
);
```

Making a field required in the UI:

- Derived: mark it required in the Pydantic model (no default).
- Override (UI only): add it to `required_overrides` in `app/forms/registry.py`.

`customer-preferences` currently has no required fields (all have defaults).
