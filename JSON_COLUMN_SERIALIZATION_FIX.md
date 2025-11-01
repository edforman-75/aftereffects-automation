# JSON Column Serialization Fix

**Date:** October 31, 2025
**Status:** ✅ Fixed
**Priority:** 🔴 Critical

---

## Problem

### Error
```
TypeError: the JSON object must be str, bytes or bytearray, not dict
```

### Location
- `/web_app.py:4035` - approve_stage2_matching() saving matches
- `/services/match_validation_service.py:42-43` - validate_job() reading results
- `/services/match_validation_service.py:213` - save_validation_results() saving results

### When It Occurred
- During end-to-end testing after fixing database cursor issues
- When approving Stage 2 matches and running validation
- Blocked validation workflow completely

### Test Output
```
Step 4: Auto-approving Stage 2 matches...
  Result: {'error': 'the JSON object must be str, bytes or bytearray, not dict', 'success': False}
```

---

## Root Cause

### SQLAlchemy JSON Column Behavior

The Job model defines JSON columns:
```python
class Job(Base):
    stage1_results = Column(JSON)  # Auto-serializes/deserializes
    stage2_approved_matches = Column(JSON)  # Auto-serializes/deserializes
    stage3_validation_results = Column(JSON)  # Auto-serializes/deserializes
```

**SQLAlchemy JSON columns automatically:**
- **Serialize** Python dicts to JSON strings when writing to database
- **Deserialize** JSON strings to Python dicts when reading from database

**The Problem:**
We were calling `json.dumps()` on dicts before assigning (double-serialization) and calling `json.loads()` on already-deserialized dicts (trying to parse a dict as string).

---

## Solution

### Stop Manual JSON Serialization

**Rule:** Never use `json.dumps()` or `json.loads()` with SQLAlchemy JSON columns.

**Before (INCORRECT):**
```python
# Writing - double serialization ❌
job.stage2_results = json.dumps({'approved_matches': matches})

# Reading - trying to parse dict as string ❌
stage1 = json.loads(job.stage1_results)
stage2 = json.loads(job.stage2_results)
```

**After (CORRECT):**
```python
# Writing - assign dict directly ✅
job.stage2_approved_matches = {'approved_matches': matches}

# Reading - use dict directly ✅
stage1 = job.stage1_results if job.stage1_results else {}
stage2 = job.stage2_approved_matches if job.stage2_approved_matches else {}
```

---

## Code Changes Summary

### Issue #1: Wrong Field Name

The database has `stage2_approved_matches`, not `stage2_results`

### Fix #1: `/web_app.py` - approve_stage2_matching (Line 4035)

**Before:**
```python
# Save matches to stage2_results using ORM
job.stage2_results = json.dumps({'approved_matches': matches})
job.stage2_completed_at = datetime.utcnow()
job.stage2_completed_by = user_id
```

**After:**
```python
# Save matches using ORM (JSON column auto-serializes)
job.stage2_approved_matches = {'approved_matches': matches}
job.stage2_completed_at = datetime.utcnow()
job.stage2_completed_by = user_id
```

**Changes:**
1. `stage2_results` → `stage2_approved_matches` (correct field name)
2. Removed `json.dumps()` (JSON column auto-serializes)
3. Assign dict directly

### Fix #2: `/services/match_validation_service.py` - validate_job (Lines 42-43)

**Before:**
```python
# Parse JSON results
stage1 = json.loads(job.stage1_results) if job.stage1_results else {}
stage2 = json.loads(job.stage2_results) if job.stage2_results else {}
```

**After:**
```python
# JSON columns are auto-deserialized by SQLAlchemy
stage1 = job.stage1_results if job.stage1_results else {}
stage2 = job.stage2_approved_matches if job.stage2_approved_matches else {}
```

**Changes:**
1. Removed `json.loads()` (already deserialized)
2. `stage2_results` → `stage2_approved_matches` (correct field name)
3. Use dict directly

### Fix #3: `/services/match_validation_service.py` - save_validation_results (Line 213)

**Before:**
```python
# Update job with validation results
job.stage3_validation_results = json.dumps(results)
job.stage3_completed_at = datetime.utcnow()
job.stage3_override = override
job.stage3_override_reason = reason
```

**After:**
```python
# Update job with validation results (JSON column auto-serializes)
job.stage3_validation_results = results
job.stage3_completed_at = datetime.utcnow()
job.stage3_override = override
job.stage3_override_reason = reason
```

**Changes:**
1. Removed `json.dumps()` (JSON column auto-serializes)
2. Assign dict directly

---

## Database Schema Reference

### JSON Columns in Job Model

```python
from sqlalchemy import Column, JSON

class Job(Base):
    __tablename__ = 'jobs'

    # Stage 1: PSD/AEPX Processing Results
    stage1_results = Column(JSON)  # Stores: {psd: {...}, aepx: {...}}

    # Stage 2: Approved Layer Matches
    stage2_approved_matches = Column(JSON)  # Stores: {approved_matches: [...]}

    # Stage 3: Validation Results
    stage3_validation_results = Column(JSON)  # Stores: {valid: bool, critical_issues: [...], ...}
```

**Automatic Behavior:**
- When you assign a dict to these columns, SQLAlchemy calls `json.dumps()` internally
- When you read from these columns, SQLAlchemy calls `json.loads()` internally
- You get Python dicts, not JSON strings

---

## SQLAlchemy JSON Column Best Practices

### ✅ Correct Usage

**Writing to JSON Column:**
```python
# Assign Python dict directly
job.stage1_results = {
    'psd': {...},
    'aepx': {...}
}

# Assign nested structures
job.stage2_approved_matches = {
    'approved_matches': [
        {'psd_layer': 'foo', 'ae_layer': 'bar'},
        {'psd_layer': 'baz', 'ae_layer': 'qux'}
    ]
}

session.commit()  # SQLAlchemy auto-serializes to JSON
```

**Reading from JSON Column:**
```python
job = session.query(Job).filter_by(job_id='ABC123').first()

# Access as Python dict directly
psd_data = job.stage1_results.get('psd', {})
matches = job.stage2_approved_matches.get('approved_matches', [])

# No json.loads() needed!
for match in matches:
    print(match['psd_layer'])  # Works directly
```

**Checking for NULL:**
```python
# Safe way to handle NULL values
stage1 = job.stage1_results if job.stage1_results else {}
stage1 = job.stage1_results or {}  # Alternative
```

### ❌ Incorrect Usage

**Don't Do This:**
```python
# ❌ Manual serialization (double-encoding)
job.stage1_results = json.dumps({'foo': 'bar'})

# ❌ Manual deserialization (trying to parse dict)
data = json.loads(job.stage1_results)

# ❌ String formatting
job.stage1_results = "{'foo': 'bar'}"  # Not even valid JSON!
```

---

## Testing

### End-to-End Test Results

**Before Fix:**
```
Step 4: Auto-approving Stage 2 matches...
  Result: {'error': 'the JSON object must be str, bytes or bytearray, not dict', 'success': False}
⚠️  Job stopped at Stage 2
```

**After Fix:**
```
Step 4: Auto-approving Stage 2 matches...
  Result: Validation passed - proceeding to ExtendScript generation
✅ No validation issues - proceeding directly

Step 8: Checking final job status...
  Current Stage: 3
  Status: processing
  Stage 1 Completed: ✅
  Stage 2 Completed: ✅
  Stage 3 Completed: ✅
```

**Test Command:**
```bash
/tmp/e2e_test.sh
```

---

## Success Criteria

- ✅ No `TypeError: the JSON object must be str, bytes or bytearray, not dict`
- ✅ Stage 2 approval saves matches correctly
- ✅ Validation service reads matches correctly
- ✅ Validation results save correctly
- ✅ End-to-end test passes completely
- ✅ Jobs progress through all stages: Stage 1 → Stage 2 → Validation → Stage 3

---

## Related Fixes in This Session

This is the **third critical database fix** in this session:

1. ✅ **approve_stage2 cursor error** - Migrated from `conn.cursor()` to SQLAlchemy ORM
2. ✅ **Validation service cursor error** - Migrated from `conn.cursor()` to SQLAlchemy ORM
3. ✅ **JSON serialization error** - Removed manual json.dumps()/json.loads() for JSON columns

All three were part of migrating the codebase from mixed SQLite/SQLAlchemy patterns to pure SQLAlchemy ORM.

---

## Complete Workflow Now Working

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Ingestion (Automated)                             │
│  • Parse PSD layers                                          │
│  • Parse AEPX composition                                    │
│  • Store results in stage1_results (JSON)  ✅               │
└─────────────────────┬───────────────────────────────────────┘
                       │
┌─────────────────────▼───────────────────────────────────────┐
│  Stage 2: Matching (Human)                                   │
│  • Review auto-matches                                       │
│  • Approve/adjust matches                                    │
│  • Store in stage2_approved_matches (JSON)  ✅              │
└─────────────────────┬───────────────────────────────────────┘
                       │
┌─────────────────────▼───────────────────────────────────────┐
│  Validation (Automatic)                                      │
│  • Check aspect ratios  ✅                                   │
│  • Check resolutions  ✅                                     │
│  • Store in stage3_validation_results (JSON)  ✅            │
└─────────────────────┬───────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
┌────────▼────────────┐   ┌──────────▼──────────┐
│  Critical Issues?   │   │  No Critical Issues │
│  → Stage 3 Review   │   │  → Stage 3 (old)    │
│    (Validation UI)  │   │    (ExtendScript)   │
└─────────────────────┘   └─────────────────────┘
```

---

## Lessons Learned

### SQLAlchemy Column Types

**Different column types have different behaviors:**

| Column Type | Read Behavior | Write Behavior | Manual Conversion? |
|------------|---------------|----------------|-------------------|
| `Column(Text)` | Returns string | Expects string | Yes - use json.dumps()/json.loads() |
| `Column(JSON)` | Returns dict | Expects dict | No - auto-serializes |
| `Column(Integer)` | Returns int | Expects int | No |
| `Column(DateTime)` | Returns datetime | Expects datetime | No |

**Key Rule:**
Check the column type definition before deciding whether to manually serialize/deserialize data.

### Migration Strategy

When migrating from raw SQL to SQLAlchemy ORM:

1. **Check column types** in model definitions
2. **Remove `json.dumps()`** for JSON columns when writing
3. **Remove `json.loads()`** for JSON columns when reading
4. **Test with real data** to ensure serialization works
5. **Update all locations** that access those fields

---

## Future Considerations

### Audit Remaining Code

Search for potential JSON column misuse:
```bash
# Find manual json.dumps() calls
grep -r "json.dumps" --include="*.py" . | grep -v "Column(Text)"

# Find manual json.loads() calls
grep -r "json.loads" --include="*.py" . | grep -v "Column(Text)"
```

### Type Hints

Add type hints to clarify JSON column usage:
```python
from typing import Dict, Optional

class Job(Base):
    stage1_results: Optional[Dict] = Column(JSON)
    stage2_approved_matches: Optional[Dict] = Column(JSON)
```

---

## Related Files

- `/database/models.py` - Job model with JSON column definitions
- `/web_app.py:4035` - approve_stage2_matching (saves to stage2_approved_matches)
- `/services/match_validation_service.py:42` - validate_job (reads JSON columns)
- `/services/match_validation_service.py:213` - save_validation_results (writes JSON column)

---

## Conclusion

The JSON serialization errors have been completely fixed by removing manual `json.dumps()` and `json.loads()` calls for SQLAlchemy JSON columns. The codebase now correctly leverages SQLAlchemy's automatic JSON serialization/deserialization.

**Status:** ✅ Production Ready
**Test:** End-to-end workflow passing ✅
**Server:** Running successfully at http://localhost:5001 ✅
**Workflow:** Stage 1 → Stage 2 → Validation → Stage 3 ✅
