# Folder Structure Management

This document explains how to set up and manage the hierarchical folder structure for client > batch > job organization in the After Effects Automation system.

## Overview

The folder management system supports two modes:

1. **Hierarchical Mode** (Recommended): Organizes files in a structured hierarchy
   ```
   projects/
   ├── ACME_Corp/
   │   ├── batch_123/
   │   │   ├── job_001/
   │   │   │   ├── assets/      # PSD, AEPX input files
   │   │   │   ├── previews/    # Generated preview videos and images
   │   │   │   ├── renders/     # Final render outputs
   │   │   │   ├── scripts/     # Generated ExtendScript files
   │   │   │   └── logs/        # Job-specific logs
   │   │   ├── job_002/
   │   │   └── job_003/
   │   └── batch_124/
   └── XYZ_Industries/
   ```

2. **Flat Mode** (Legacy): Uses traditional single-level directories (uploads, previews, etc.)

## Configuration

### Settings Location

Folder organization settings are stored in `config.json` under the `folder_organization` section:

```json
{
  "folder_organization": {
    "use_hierarchical_folders": true,
    "base_output_path": "projects",
    "sanitize_folder_names": true,
    "create_job_subfolders": true,
    "max_folder_name_length": 100,
    "assets_subfolder": "assets",
    "previews_subfolder": "previews",
    "renders_subfolder": "renders",
    "scripts_subfolder": "scripts",
    "logs_subfolder": "logs"
  }
}
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `use_hierarchical_folders` | boolean | `true` | Enable hierarchical folder structure |
| `base_output_path` | string | `"projects"` | Base directory for organized projects |
| `sanitize_folder_names` | boolean | `true` | Remove special characters from folder names |
| `create_job_subfolders` | boolean | `true` | Create subfolders within each job |
| `max_folder_name_length` | integer | `100` | Maximum length for folder names |
| `assets_subfolder` | string | `"assets"` | Name for assets subfolder |
| `previews_subfolder` | string | `"previews"` | Name for previews subfolder |
| `renders_subfolder` | string | `"renders"` | Name for renders subfolder |
| `scripts_subfolder` | string | `"scripts"` | Name for scripts subfolder |
| `logs_subfolder` | string | `"logs"` | Name for logs subfolder |

## API Endpoints

### Setup Folders

#### Create Client Folder

```bash
POST /api/folder/setup/client
Content-Type: application/json

{
  "client_name": "ACME Corp"
}
```

**Response:**
```json
{
  "success": true,
  "client_name": "ACME Corp",
  "folder_path": "projects/ACME_Corp",
  "message": "Client folder created successfully"
}
```

#### Create Batch Folder

```bash
POST /api/folder/setup/batch
Content-Type: application/json

{
  "client_name": "ACME Corp",
  "batch_id": "batch_123"
}
```

**Response:**
```json
{
  "success": true,
  "client_name": "ACME Corp",
  "batch_id": "batch_123",
  "folder_path": "projects/ACME_Corp/batch_123",
  "message": "Batch folder created successfully"
}
```

#### Create Job Folders

```bash
POST /api/folder/setup/job
Content-Type: application/json

{
  "client_name": "ACME Corp",
  "batch_id": "batch_123",
  "job_id": "job_001"
}
```

**Response:**
```json
{
  "success": true,
  "client_name": "ACME Corp",
  "batch_id": "batch_123",
  "job_id": "job_001",
  "paths": {
    "root": "projects/ACME_Corp/batch_123/job_001",
    "assets": "projects/ACME_Corp/batch_123/job_001/assets",
    "previews": "projects/ACME_Corp/batch_123/job_001/previews",
    "renders": "projects/ACME_Corp/batch_123/job_001/renders",
    "scripts": "projects/ACME_Corp/batch_123/job_001/scripts",
    "logs": "projects/ACME_Corp/batch_123/job_001/logs"
  },
  "message": "Job folders created successfully"
}
```

### List Folders

#### List All Clients

```bash
GET /api/folder/list/clients
```

**Response:**
```json
{
  "success": true,
  "clients": ["ACME_Corp", "XYZ_Industries"],
  "count": 2
}
```

#### List Batches for Client

```bash
GET /api/folder/list/batches/ACME_Corp
```

**Response:**
```json
{
  "success": true,
  "client_name": "ACME_Corp",
  "batches": ["batch_123", "batch_124"],
  "count": 2
}
```

#### List Jobs for Batch

```bash
GET /api/folder/list/jobs/ACME_Corp/batch_123
```

**Response:**
```json
{
  "success": true,
  "client_name": "ACME_Corp",
  "batch_id": "batch_123",
  "jobs": ["job_001", "job_002", "job_003"],
  "count": 3
}
```

### Folder Information

#### Get Folder Info

```bash
GET /api/folder/info/ACME_Corp
GET /api/folder/info/ACME_Corp/batch_123
GET /api/folder/info/ACME_Corp/batch_123/job_001
```

**Response:**
```json
{
  "success": true,
  "info": {
    "exists": true,
    "path": "projects/ACME_Corp/batch_123/job_001",
    "size_bytes": 1234567,
    "size_mb": 1.18,
    "file_count": 42
  }
}
```

### Manage Settings

#### Get Current Settings

```bash
GET /api/folder/settings
```

**Response:**
```json
{
  "success": true,
  "settings": {
    "use_hierarchical_folders": true,
    "base_output_path": "projects",
    "sanitize_folder_names": true,
    "create_job_subfolders": true,
    "max_folder_name_length": 100,
    "assets_subfolder": "assets",
    "previews_subfolder": "previews",
    "renders_subfolder": "renders",
    "scripts_subfolder": "scripts",
    "logs_subfolder": "logs"
  }
}
```

#### Update Settings

```bash
PUT /api/folder/settings
Content-Type: application/json

{
  "use_hierarchical_folders": true,
  "base_output_path": "projects"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Folder settings updated successfully"
}
```

## Python Usage

### Using FolderManager Service

```python
from services.folder_manager import folder_manager

# Set up folders for a new job
paths = folder_manager.setup_job_folders(
    client_name="ACME Corp",
    batch_id="batch_123",
    job_id="job_001"
)

# Use the paths
print(f"Save PSD to: {paths.assets}")
print(f"Save preview to: {paths.previews}")
print(f"Save render to: {paths.renders}")

# Get paths for existing job (without creating folders)
paths = folder_manager.get_job_paths("ACME Corp", "batch_123", "job_001")

# List clients
clients = folder_manager.list_clients()

# List batches for a client
batches = folder_manager.list_batches("ACME Corp")

# List jobs for a batch
jobs = folder_manager.list_jobs("ACME Corp", "batch_123")

# Get folder information
info = folder_manager.get_folder_info("ACME Corp", "batch_123", "job_001")
print(f"Folder size: {info['size_mb']} MB")
print(f"File count: {info['file_count']}")
```

### Folder Name Sanitization

The system automatically sanitizes folder names to ensure file system compatibility:

```python
"ACME Corp. (2024)" -> "ACME_Corp_2024"
"Batch #123"        -> "Batch_123"
"Project: Test!"    -> "Project_Test"
```

## Workflow Integration

### Creating a New Client

1. Set up client folder (optional, will be auto-created):
   ```bash
   POST /api/folder/setup/client
   {"client_name": "New Client"}
   ```

### Processing a Batch

1. Upload CSV batch file (existing endpoint):
   ```bash
   POST /api/batch/upload
   ```

2. The system will automatically:
   - Create client folder if it doesn't exist
   - Create batch folder
   - Create job folders for each job in the batch
   - Organize all files in the hierarchical structure

### Accessing Job Files

When hierarchical folders are enabled:

```python
# Get paths for a job
paths = folder_manager.get_job_paths(
    client_name=job.client_name,
    batch_id=job.batch_id,
    job_id=job.job_id
)

# Save files to appropriate locations
psd_path = paths.assets / "input.psd"
preview_path = paths.previews / "preview.mp4"
render_path = paths.renders / "final.mp4"
script_path = paths.scripts / "animation.jsx"
log_path = paths.logs / "processing.log"
```

## Migration from Flat to Hierarchical

To migrate from flat directory structure to hierarchical:

1. Update settings:
   ```bash
   PUT /api/folder/settings
   {"use_hierarchical_folders": true}
   ```

2. The system will:
   - Create new hierarchical structure for new jobs
   - Continue to access old files in flat directories
   - Gradually migrate to the new structure

3. Optional: Manually move existing files to the new structure:
   ```bash
   # Example migration script
   for job in existing_jobs:
       paths = folder_manager.setup_job_folders(
           job.client_name, job.batch_id, job.job_id
       )
       # Move files from flat dirs to new structure
       shutil.move(old_path, paths.assets)
   ```

## Best Practices

1. **Client Names**: Use clear, consistent naming for clients
   - Good: "ACME Corp", "XYZ Industries"
   - Avoid: "ACME-Corp!", "Client #1"

2. **Batch IDs**: Use descriptive, unique identifiers
   - Good: "batch_2024_q1_001", "spring_campaign_batch"
   - Auto-generated: "batch_20240315_143022"

3. **Job IDs**: Ensure uniqueness within a batch
   - Auto-generated format: job database ID or UUID
   - Custom format: "job_001", "video_001"

4. **Folder Organization**:
   - Keep base_output_path at root level ("projects")
   - Use hierarchical mode for better organization
   - Enable subfolder creation for clean separation

5. **Cleanup**:
   - Regularly archive completed projects
   - Monitor folder sizes with `/api/folder/info` endpoint
   - Set up automated archival for old batches

## Troubleshooting

### Folders Not Being Created

1. Check permissions on base_output_path
2. Verify settings with `GET /api/folder/settings`
3. Check logs for folder creation errors

### Special Characters in Names

The system automatically sanitizes folder names, but you can:
- Disable sanitization: Set `sanitize_folder_names: false`
- Adjust max length: Change `max_folder_name_length`

### Flat Mode Not Working

If hierarchical mode is causing issues:
1. Disable it: `PUT /api/folder/settings {"use_hierarchical_folders": false}`
2. System will fall back to flat directories
3. Check existing flat directory paths in DirectorySettings

## File Location Reference

| File Type | Hierarchical Path | Flat Path |
|-----------|-------------------|-----------|
| Input PSD | `projects/{client}/{batch}/{job}/assets/` | `uploads/` |
| Input AEPX | `projects/{client}/{batch}/{job}/assets/` | `uploads/` |
| Preview Video | `projects/{client}/{batch}/{job}/previews/` | `previews/` |
| Preview Image | `projects/{client}/{batch}/{job}/previews/` | `output/previews/` |
| Final Render | `projects/{client}/{batch}/{job}/renders/` | `renders/` |
| ExtendScript | `projects/{client}/{batch}/{job}/scripts/` | `output/` |
| Job Logs | `projects/{client}/{batch}/{job}/logs/` | `logs/` |

## Related Files

- **Service**: `services/folder_manager.py` - Core folder management logic
- **Routes**: `routes/folder_routes.py` - API endpoints
- **Settings**: `config/settings.py` - Configuration dataclass
- **Config**: `config.json` - Persistent configuration
