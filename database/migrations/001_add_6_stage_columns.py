#!/usr/bin/env python3
"""
Database Migration: Add 6-Stage Pipeline Columns
Date: October 31, 2025
Purpose: Add Stage 3-6 columns to support 6-stage pipeline restructuring
"""

import sqlite3
import sys
import os

def run_migration(db_path):
    """Add new columns for 6-stage pipeline."""
    print(f"\n{'='*70}")
    print(f"DATABASE MIGRATION: 6-Stage Pipeline")
    print(f"{'='*70}")
    print(f"Database: {db_path}")

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(jobs)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"\n📋 Found {len(existing_columns)} existing columns in jobs table")

        # Define new columns to add
        new_columns = [
            # Stage 3: Validation columns
            ("stage3_validation_results", "TEXT", "Stage 3 validation report (JSON)"),

            # Stage 4: Validation Review columns
            ("stage4_override", "INTEGER DEFAULT 0", "Whether validation was overridden"),
            ("stage4_override_reason", "TEXT", "Override justification"),

            # Stage 5: ExtendScript Generation columns
            ("stage5_started_at", "TIMESTAMP", "Stage 5 start time"),
            ("stage5_completed_at", "TIMESTAMP", "Stage 5 completion time"),
            ("stage5_completed_by", "VARCHAR(100) DEFAULT 'system'", "Who completed Stage 5"),
            ("stage5_extendscript", "TEXT", "Generated ExtendScript"),

            # Stage 6: Download columns
            ("stage6_started_at", "TIMESTAMP", "Stage 6 start time"),
            ("stage6_completed_at", "TIMESTAMP", "Stage 6 completion time"),
            ("stage6_completed_by", "VARCHAR(100)", "Who completed Stage 6"),
            ("stage6_downloaded_at", "TIMESTAMP", "When user downloaded"),
        ]

        # Add missing columns
        added_count = 0
        skipped_count = 0

        for column_name, column_type, description in new_columns:
            if column_name in existing_columns:
                print(f"  ⏭️  Skipping {column_name} (already exists)")
                skipped_count += 1
            else:
                sql = f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                print(f"  ✅ Added {column_name}: {description}")
                added_count += 1

        # Commit changes
        conn.commit()

        print(f"\n{'='*70}")
        print(f"✅ Migration Complete")
        print(f"   Added: {added_count} columns")
        print(f"   Skipped: {skipped_count} columns (already exist)")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    # Default to production database
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data',
        'production.db'
    )

    # Allow override via command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    success = run_migration(db_path)
    sys.exit(0 if success else 1)
