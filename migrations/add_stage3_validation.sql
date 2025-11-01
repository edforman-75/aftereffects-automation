-- Migration: Add Stage 3 Validation columns to jobs table
-- Purpose: Store validation results, timestamps, and override decisions
-- Date: 2025-10-31

-- Add stage3 validation result columns
ALTER TABLE jobs ADD COLUMN stage3_validation_results TEXT;
ALTER TABLE jobs ADD COLUMN stage3_completed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN stage3_override BOOLEAN DEFAULT 0;
ALTER TABLE jobs ADD COLUMN stage3_override_reason TEXT;

-- Note: SQLite uses 0/1 for boolean instead of TRUE/FALSE
-- stage3_validation_results will store JSON with format:
-- {
--   "valid": true/false,
--   "critical_issues": [...],
--   "warnings": [...],
--   "info": [...]
-- }
