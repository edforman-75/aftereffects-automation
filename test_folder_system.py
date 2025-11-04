#!/usr/bin/env python3
"""
Quick test script for folder management system.

Tests:
1. Folder name sanitization
2. Client folder creation
3. Batch folder creation
4. Job folder creation with all subfolders
5. Folder listing
6. Folder info retrieval
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import directly from the modules to avoid full service init
from services.folder_manager import FolderManager
from config.settings import settings

# Create folder manager instance
folder_manager = FolderManager()


def test_folder_system():
    """Test the folder management system"""
    print("\n" + "="*60)
    print("Testing Folder Management System")
    print("="*60 + "\n")

    # Show current settings
    print("Current Settings:")
    print(f"  Use hierarchical folders: {settings.folder_organization.use_hierarchical_folders}")
    print(f"  Base output path: {settings.folder_organization.base_output_path}")
    print(f"  Sanitize folder names: {settings.folder_organization.sanitize_folder_names}")
    print(f"  Create job subfolders: {settings.folder_organization.create_job_subfolders}")
    print()

    # Test 1: Folder name sanitization
    print("Test 1: Folder Name Sanitization")
    test_names = [
        "ACME Corp.",
        "Client #123",
        "Test (2024)!",
        "Normal_Client"
    ]
    for name in test_names:
        sanitized = folder_manager.sanitize_folder_name(name)
        print(f"  '{name}' -> '{sanitized}'")
    print()

    # Test 2: Create client folder
    print("Test 2: Create Client Folder")
    client_name = "Test_Client_Corp"
    client_folder = folder_manager.setup_client_folder(client_name)
    print(f"  Created: {client_folder}")
    print(f"  Exists: {client_folder.exists()}")
    print()

    # Test 3: Create batch folder
    print("Test 3: Create Batch Folder")
    batch_id = "test_batch_001"
    batch_folder = folder_manager.setup_batch_folder(client_name, batch_id)
    print(f"  Created: {batch_folder}")
    print(f"  Exists: {batch_folder.exists()}")
    print()

    # Test 4: Create job folders
    print("Test 4: Create Job Folders")
    job_id = "test_job_001"
    paths = folder_manager.setup_job_folders(client_name, batch_id, job_id)
    print(f"  Root: {paths.root}")
    print(f"  Assets: {paths.assets} (exists: {paths.assets.exists()})")
    print(f"  Previews: {paths.previews} (exists: {paths.previews.exists()})")
    print(f"  Renders: {paths.renders} (exists: {paths.renders.exists()})")
    print(f"  Scripts: {paths.scripts} (exists: {paths.scripts.exists()})")
    print(f"  Logs: {paths.logs} (exists: {paths.logs.exists()})")
    print()

    # Test 5: Create multiple jobs in same batch
    print("Test 5: Create Multiple Jobs in Same Batch")
    for i in range(2, 5):
        job_id = f"test_job_{i:03d}"
        paths = folder_manager.setup_job_folders(client_name, batch_id, job_id)
        print(f"  Created job folder: {paths.root}")
    print()

    # Test 6: List clients
    print("Test 6: List Clients")
    clients = folder_manager.list_clients()
    print(f"  Found {len(clients)} clients:")
    for client in clients:
        print(f"    - {client}")
    print()

    # Test 7: List batches
    print("Test 7: List Batches for Client")
    batches = folder_manager.list_batches(client_name)
    print(f"  Found {len(batches)} batches:")
    for batch in batches:
        print(f"    - {batch}")
    print()

    # Test 8: List jobs
    print("Test 8: List Jobs for Batch")
    jobs = folder_manager.list_jobs(client_name, batch_id)
    print(f"  Found {len(jobs)} jobs:")
    for job in jobs:
        print(f"    - {job}")
    print()

    # Test 9: Get folder info
    print("Test 9: Get Folder Info")
    info = folder_manager.get_folder_info(client_name, batch_id)
    print(f"  Batch folder: {info['path']}")
    print(f"  Exists: {info['exists']}")
    if info['exists']:
        print(f"  Size: {info['size_mb']} MB")
        print(f"  Files: {info['file_count']}")
    print()

    # Test 10: Get paths for existing job (without creating)
    print("Test 10: Get Paths for Existing Job")
    job_id = "test_job_002"
    paths = folder_manager.get_job_paths(client_name, batch_id, job_id)
    print(f"  Root: {paths.root}")
    print(f"  Assets: {paths.assets}")
    print()

    print("="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")


if __name__ == '__main__':
    test_folder_system()
