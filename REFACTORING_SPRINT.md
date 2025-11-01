# Refactoring Sprint - Code Cleanup & Organization

## Goal
Clean up technical debt before implementing Stages 5-6. Focus on critical issues that will make future development easier.

---

## Priority 1: Database Access Standardization (CRITICAL)

### Audit all database access patterns

**Task:** Find and fix all instances of incorrect database patterns
```bash
# Find all cursor usage (should be zero)
grep -rn "\.cursor()" services/ web_app.py

# Find all db_session() calls (should use service methods instead)
grep -rn "db_session()" services/ | grep -v "def db_session"

# Find all container.db_manager (old pattern)
grep -rn "container.db_manager" .
```

### Standardize to service methods

**Pattern to use everywhere:**
```python
# ✅ CORRECT
job = job_service.get_job(job_id)
job_service.update_job(job)
batch = batch_service.get_batch(batch_id)

# ❌ AVOID
session = db_session()
job = session.query(Job).filter_by(job_id=job_id).first()
```

**Files to audit:**
- [ ] services/match_validation_service.py
- [ ] services/stage_transition_manager.py
- [ ] services/batch_service.py
- [ ] services/job_service.py
- [ ] web_app.py (all endpoints)

---

## Priority 2: Split web_app.py into Modules

### Current: Monolithic (4200 lines)
```
web_app.py
  ├── App initialization (50 lines)
  ├── Batch routes (300 lines)
  ├── Job routes (500 lines)
  ├── Stage 1 routes (400 lines)
  ├── Stage 2 routes (600 lines)
  ├── Stage 3 routes (400 lines)
  ├── Validation routes (300 lines)
  ├── Settings routes (200 lines)
  └── Utility functions (1450 lines)
```

### Target: Modular Blueprint Structure

**Create new files:**
```python
# routes/__init__.py
from flask import Blueprint

# routes/batch_routes.py
batch_bp = Blueprint('batch', __name__)

@batch_bp.route('/api/batch/upload', methods=['POST'])
def upload_batch():
    """Upload CSV batch file"""
    # Move existing code here

@batch_bp.route('/api/batch/<batch_id>', methods=['GET'])
def get_batch(batch_id):
    """Get batch details"""
    # Move existing code here

# routes/job_routes.py
job_bp = Blueprint('job', __name__)

@job_bp.route('/api/job/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job details"""
    # Move existing code here

# routes/stage2_routes.py
stage2_bp = Blueprint('stage2', __name__)

@stage2_bp.route('/review-matching/<job_id>', methods=['GET'])
def review_matching(job_id):
    """Stage 2 matching review page"""
    # Move existing code here

@stage2_bp.route('/api/job/<job_id>/approve-stage2', methods=['POST'])
def approve_stage2(job_id):
    """Approve Stage 2 matches"""
    # Move existing code here

# routes/stage3_routes.py
stage3_bp = Blueprint('stage3', __name__)

@stage3_bp.route('/validate/<job_id>', methods=['GET'])
def validate_job(job_id):
    """Stage 3 validation review page"""
    # Move existing code here
```

**Simplified web_app.py (target: ~200 lines):**
```python
from flask import Flask
from routes.batch_routes import batch_bp
from routes.job_routes import job_bp
from routes.stage2_routes import stage2_bp
from routes.stage3_routes import stage3_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(batch_bp)
app.register_blueprint(job_bp)
app.register_blueprint(stage2_bp)
app.register_blueprint(stage3_bp)

# Minimal initialization code
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

---

## Priority 3: Centralize Configuration

### Create config module

**File: config/settings.py**
```python
from pathlib import Path

class Config:
    """Base configuration"""
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    
    # Database
    DATABASE_URL = str(DATA_DIR / 'production.db')
    
    # Paths
    UPLOAD_FOLDER = DATA_DIR / 'uploads'
    BATCH_FOLDER = DATA_DIR / 'batches'
    JOB_FOLDER = DATA_DIR / 'jobs'
    
    # Limits
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_BATCH_SIZE = 100  # jobs per batch
    
    # File types
    ALLOWED_EXTENSIONS = {'.psd', '.aepx', '.csv'}
    
    # ImageMagick
    IMAGEMAGICK_PATH = 'magick'
    IMAGEMAGICK_TIMEOUT = 60  # seconds
    
    @classmethod
    def ensure_directories(cls):
        """Create required directories"""
        for path in [cls.DATA_DIR, cls.UPLOAD_FOLDER, 
                     cls.BATCH_FOLDER, cls.JOB_FOLDER]:
            path.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
```

**Usage throughout codebase:**
```python
from config.settings import Config

# Instead of hardcoded paths
job_dir = Config.JOB_FOLDER / job_id
```

---

## Priority 4: Consistent Error Handling

### Create error handling utilities

**File: utils/errors.py**
```python
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base application error"""
    status_code = 500
    
    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code:
            self.status_code = status_code
        self.message = message

class JobNotFoundError(AppError):
    """Job not found"""
    status_code = 404

class ValidationError(AppError):
    """Validation failed"""
    status_code = 400

def handle_error(error):
    """Global error handler"""
    if isinstance(error, AppError):
        logger.warning(f"App error: {error.message}")
        return jsonify({
            'success': False,
            'error': error.message
        }), error.status_code
    
    # Unexpected error
    logger.error(f"Unexpected error: {error}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
```

**Usage in routes:**
```python
@app.route('/api/job/<job_id>')
def get_job(job_id):
    job = job_service.get_job(job_id)
    if not job:
        raise JobNotFoundError(f"Job not found: {job_id}")
    return jsonify({'success': True, 'job': job.to_dict()})

# Register error handler
app.register_error_handler(AppError, handle_error)
```

---

## Priority 5: Clean Up Unused Code

### Find and remove
```bash
# Find TODO comments
grep -rn "TODO" . --exclude-dir=venv

# Find FIXME comments
grep -rn "FIXME" . --exclude-dir=venv

# Find commented-out code blocks
grep -rn "^#.*def " . --exclude-dir=venv

# Find unused imports (use pylint or similar)
pylint web_app.py --disable=all --enable=unused-import
```

---

## Priority 6: Add Type Hints

### Add type annotations to critical functions
```python
# Before
def get_job(job_id):
    session = db_session()
    job = session.query(Job).filter_by(job_id=job_id).first()
    session.close()
    return job

# After
from typing import Optional
from database.models import Job

def get_job(job_id: str) -> Optional[Job]:
    """
    Get job by ID.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job object if found, None otherwise
    """
    session = db_session()
    try:
        return session.query(Job).filter_by(job_id=job_id).first()
    finally:
        session.close()
```

---

## Refactoring Checklist

### Phase 1: Critical (Do Now)
- [ ] Audit all database access patterns
- [ ] Convert to service methods everywhere
- [ ] Remove all cursor() usage
- [ ] Add session cleanup (try/finally) everywhere
- [ ] Test after each change

### Phase 2: Structure (2-3 hours)
- [ ] Create routes/ directory
- [ ] Split web_app.py into blueprints
- [ ] Move batch routes → routes/batch_routes.py
- [ ] Move job routes → routes/job_routes.py
- [ ] Move stage routes → routes/stage2_routes.py, etc.
- [ ] Update web_app.py to register blueprints
- [ ] Test all endpoints still work

### Phase 3: Configuration (1 hour)
- [ ] Create config/settings.py
- [ ] Move all hardcoded paths to config
- [ ] Move all constants to config
- [ ] Update all imports
- [ ] Test configuration loading

### Phase 4: Error Handling (1 hour)
- [ ] Create utils/errors.py
- [ ] Define custom exception classes
- [ ] Add error handler to app
- [ ] Update routes to raise custom exceptions
- [ ] Test error responses

### Phase 5: Cleanup (1 hour)
- [ ] Remove commented code
- [ ] Fix TODOs or document them
- [ ] Remove unused imports
- [ ] Add type hints to public functions
- [ ] Run linter and fix issues

---

## Testing Strategy

After each refactoring phase:

1. **Run E2E test:**
```bash
/tmp/e2e_test.sh
```

2. **Manual smoke test:**
- Upload batch
- Process Stage 1
- Review Stage 2
- Test validation

3. **Check logs for errors:**
```bash
tail -f aftereffects_automation.log | grep ERROR
```

---

## Rollback Plan

If refactoring breaks something:
```bash
# See what changed
git diff

# Undo specific file
git checkout HEAD -- web_app.py

# Undo all changes
git reset --hard HEAD
```

---

## Success Criteria

✅ Zero "cursor()" calls in codebase
✅ All database access through service methods
✅ web_app.py < 300 lines
✅ All routes in separate blueprint files
✅ All configuration centralized
✅ E2E test passes
✅ No new errors in logs

---

## Estimated Time

- Phase 1 (Database): 2 hours
- Phase 2 (Structure): 3 hours
- Phase 3 (Config): 1 hour
- Phase 4 (Errors): 1 hour
- Phase 5 (Cleanup): 1 hour
- **Total: ~8 hours (1 full day)**

---

## Order of Operations

1. **Commit current work** ✅ (about to do)
2. **Database audit** (critical, do first)
3. **Split web_app.py** (big improvement)
4. **Centralize config** (nice to have)
5. **Standardize errors** (polish)
6. **Final cleanup** (polish)

