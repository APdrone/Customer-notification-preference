-- Migration: Add indices and audit tracking for preference suppression

-- Index on preferences for customer_id, channel, and value
CREATE INDEX IF NOT EXISTS idx_preferences_customer_channel_value
    ON preferences (customer_id, channel, value);

-- Add audit table for changes
CREATE TABLE IF NOT EXISTS preference_audit (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    old_preferences JSONB,
    new_preferences JSONB,
    suppressed BOOLEAN DEFAULT FALSE
);

-- Index for efficient audit lookup
CREATE INDEX IF NOT EXISTS idx_preference_audit_customer ON preference_audit (customer_id);
