-- Migration: Add logic for audit suppression when preferences are unchanged
-- No data changes, but add audit trigger suppression for redundant updates

-- Example: Assuming PostgreSQL and audit maintained via triggers
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_name = 'audit_suppress_on_unchanged_preference')
    THEN
        CREATE TRIGGER audit_suppress_on_unchanged_preference
        BEFORE UPDATE ON customer_preferences
        FOR EACH ROW
        EXECUTE FUNCTION suppress_audit_if_unchanged();
    END IF;
END$$;

-- Audit function should be implemented to compare OLD and NEW values
-- and conditionally suppress audit entry
CREATE OR REPLACE FUNCTION suppress_audit_if_unchanged()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.preference_values = NEW.preference_values) THEN
        -- Skip audit
        RETURN NULL;
    END IF;
    -- Normal audit logic
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;