#!/usr/bin/env python3
"""
Database Migration: Add Render Frame Path Column
Date: November 4, 2025
Purpose: Add column to store path to extracted render frame for Stage 6 preview
"""

import sqlite3
import sys
import os

def run_migration(db_path):
    """Add stage6_render_frame_path column to jobs table."""
    print(f"\n{'='*70}")
    print(f"DATABASE MIGRATION: Add Render Frame Path")
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

        # Define new column to add
        new_columns = [
            ("stage6_render_frame_path", "VARCHAR(500)", "Path to rendered frame image for display"),
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
