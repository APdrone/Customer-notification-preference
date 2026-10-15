-- Migration to add audit suppression trigger and supporting indexes
CREATE INDEX IF NOT EXISTS idx_customer_preferences_user_id ON customer_preferences(user_id);

-- Audit suppression trigger (PostgreSQL example)
CREATE OR REPLACE FUNCTION suppress_duplicate_preference_audit()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.preferences = OLD.preferences THEN
        -- Do not insert an audit log if preferences unchanged
        RETURN NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_suppress_duplicate_preference_audit ON customer_preferences;
CREATE TRIGGER trg_suppress_duplicate_preference_audit
BEFORE UPDATE ON customer_preferences
FOR EACH ROW
EXECUTE FUNCTION suppress_duplicate_preference_audit();
