-- Migration: Add audit suppression logic and supporting indexes
-- Block audit triggers on unchanged preferences
CREATE OR REPLACE FUNCTION suppress_unchanged_preference_audit()
RETURNS trigger AS $$
BEGIN
    IF (NEW.preferences = OLD.preferences) THEN
        -- Suppress audit log if unchanged
        RETURN NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS preference_audit_suppression ON customer_preferences;
CREATE TRIGGER preference_audit_suppression
BEFORE UPDATE ON customer_preferences
FOR EACH ROW
EXECUTE PROCEDURE suppress_unchanged_preference_audit();

-- Index to speed up unchanged checks
CREATE INDEX IF NOT EXISTS idx_customer_preferences_pref ON customer_preferences (customer_id, preferences);