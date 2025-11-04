"""
Folder Manager Service

Manages hierarchical folder structure for client > batch > job organization.
Provides utilities for creating and managing folders, with support for both
hierarchical and flat folder structures.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from config.settings import settings


@dataclass
class FolderPaths:
    """Container for all paths related to a job"""
    root: Path  # Root directory for this job
    assets: Path  # PSD, AEPX input files
    previews: Path  # Generated preview videos and images
    renders: Path  # Final render outputs
    scripts: Path  # Generated ExtendScript files
    logs: Path  # Job-specific logs


class FolderManager:
    """
    Manages folder structure for client/batch/job hierarchy.

    Supports two modes:
    1. Hierarchical: projects/client_name/batch_id/job_id/
    2. Flat: Traditional single-level directories (uploads, previews, etc.)

    Usage:
        manager = FolderManager()
        paths = manager.setup_job_folders("ACME Corp", "batch_123", "job_001")
        # Returns FolderPaths with all necessary directories created
    """

    def __init__(self):
        """Initialize folder manager with current settings"""
        self.settings = settings.folder_organization
        self.directories = settings.directories

    def sanitize_folder_name(self, name: str) -> str:
        """
        Sanitize a folder name by removing/replacing invalid characters.

        Args:
            name: Raw folder name (e.g., client name, batch ID)

        Returns:
            Sanitized folder name safe for file system

        Example:
            "ACME Corp. (2024)" -> "ACME_Corp_2024"
            "Batch #123" -> "Batch_123"
        """
        if not self.settings.sanitize_folder_names:
            return name

        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\-_.]', '_', name)

        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')

        # Enforce maximum length
        max_len = self.settings.max_folder_name_length
        if len(sanitized) > max_len:
            sanitized = sanitized[:max_len].rstrip('_')

        return sanitized or 'unnamed'

    def get_client_folder(self, client_name: str) -> Path:
        """
        Get the folder path for a client.

        Args:
            client_name: Name of the client

        Returns:
            Path to client folder

        Example:
            get_client_folder("ACME Corp") -> Path("projects/ACME_Corp")
        """
        if not self.settings.use_hierarchical_folders:
            return Path(self.directories.output_dir)

        base = Path(self.settings.base_output_path)
        client_folder = self.sanitize_folder_name(client_name)
        return base / client_folder

    def get_batch_folder(self, client_name: str, batch_id: str) -> Path:
        """
        Get the folder path for a batch.

        Args:
            client_name: Name of the client
            batch_id: Unique batch identifier

        Returns:
            Path to batch folder

        Example:
            get_batch_folder("ACME Corp", "batch_123") ->
            Path("projects/ACME_Corp/batch_123")
        """
        if not self.settings.use_hierarchical_folders:
            return Path(self.directories.output_dir)

        client_folder = self.get_client_folder(client_name)
        batch_folder = self.sanitize_folder_name(batch_id)
        return client_folder / batch_folder

    def get_job_folder(self, client_name: str, batch_id: str, job_id: str) -> Path:
        """
        Get the folder path for a job.

        Args:
            client_name: Name of the client
            batch_id: Unique batch identifier
            job_id: Unique job identifier

        Returns:
            Path to job folder

        Example:
            get_job_folder("ACME Corp", "batch_123", "job_001") ->
            Path("projects/ACME_Corp/batch_123/job_001")
        """
        if not self.settings.use_hierarchical_folders:
            return Path(self.directories.output_dir)

        batch_folder = self.get_batch_folder(client_name, batch_id)
        job_folder = self.sanitize_folder_name(job_id)
        return batch_folder / job_folder

    def setup_client_folder(self, client_name: str) -> Path:
        """
        Create folder structure for a new client.

        Args:
            client_name: Name of the client

        Returns:
            Path to created client folder

        Raises:
            OSError: If folder creation fails
        """
        client_folder = self.get_client_folder(client_name)

        if self.settings.use_hierarchical_folders:
            client_folder.mkdir(parents=True, exist_ok=True)

        return client_folder

    def setup_batch_folder(self, client_name: str, batch_id: str) -> Path:
        """
        Create folder structure for a new batch.

        Args:
            client_name: Name of the client
            batch_id: Unique batch identifier

        Returns:
            Path to created batch folder

        Raises:
            OSError: If folder creation fails
        """
        batch_folder = self.get_batch_folder(client_name, batch_id)

        if self.settings.use_hierarchical_folders:
            batch_folder.mkdir(parents=True, exist_ok=True)

        return batch_folder

    def setup_job_folders(
        self,
        client_name: str,
        batch_id: str,
        job_id: str
    ) -> FolderPaths:
        """
        Create complete folder structure for a new job.

        Creates the full hierarchy:
        - client_name/batch_id/job_id/
          - assets/      # Input files (PSD, AEPX)
          - previews/    # Generated preview videos and images
          - renders/     # Final render outputs
          - scripts/     # Generated ExtendScript files
          - logs/        # Job-specific logs

        Args:
            client_name: Name of the client
            batch_id: Unique batch identifier
            job_id: Unique job identifier

        Returns:
            FolderPaths object with all created paths

        Raises:
            OSError: If folder creation fails

        Example:
            paths = manager.setup_job_folders("ACME Corp", "batch_123", "job_001")
            # Save PSD to: paths.assets / "input.psd"
            # Save preview to: paths.previews / "preview.mp4"
        """
        job_folder = self.get_job_folder(client_name, batch_id, job_id)

        # Create job root folder
        if self.settings.use_hierarchical_folders:
            job_folder.mkdir(parents=True, exist_ok=True)

        # Create subfolders if enabled
        if self.settings.create_job_subfolders and self.settings.use_hierarchical_folders:
            assets_folder = job_folder / self.settings.assets_subfolder
            previews_folder = job_folder / self.settings.previews_subfolder
            renders_folder = job_folder / self.settings.renders_subfolder
            scripts_folder = job_folder / self.settings.scripts_subfolder
            logs_folder = job_folder / self.settings.logs_subfolder

            # Create all subfolders
            for folder in [assets_folder, previews_folder, renders_folder,
                          scripts_folder, logs_folder]:
                folder.mkdir(parents=True, exist_ok=True)
        else:
            # Use flat directory structure or job root for all files
            assets_folder = Path(self.directories.upload_dir)
            previews_folder = Path(self.directories.preview_dir)
            renders_folder = Path(self.directories.renders_dir)
            scripts_folder = Path(self.directories.output_dir)
            logs_folder = Path(self.directories.logs_dir)

            # Ensure flat directories exist
            for folder in [assets_folder, previews_folder, renders_folder,
                          scripts_folder, logs_folder]:
                folder.mkdir(parents=True, exist_ok=True)

        return FolderPaths(
            root=job_folder,
            assets=assets_folder,
            previews=previews_folder,
            renders=renders_folder,
            scripts=scripts_folder,
            logs=logs_folder
        )

    def get_job_paths(
        self,
        client_name: str,
        batch_id: str,
        job_id: str
    ) -> FolderPaths:
        """
        Get folder paths for an existing job (without creating folders).

        Use this when you need to reference paths for a job that already exists.

        Args:
            client_name: Name of the client
            batch_id: Unique batch identifier
            job_id: Unique job identifier

        Returns:
            FolderPaths object with all paths
        """
        job_folder = self.get_job_folder(client_name, batch_id, job_id)

        if self.settings.create_job_subfolders and self.settings.use_hierarchical_folders:
            assets_folder = job_folder / self.settings.assets_subfolder
            previews_folder = job_folder / self.settings.previews_subfolder
            renders_folder = job_folder / self.settings.renders_subfolder
            scripts_folder = job_folder / self.settings.scripts_subfolder
            logs_folder = job_folder / self.settings.logs_subfolder
        else:
            assets_folder = Path(self.directories.upload_dir)
            previews_folder = Path(self.directories.preview_dir)
            renders_folder = Path(self.directories.renders_dir)
            scripts_folder = Path(self.directories.output_dir)
            logs_folder = Path(self.directories.logs_dir)

        return FolderPaths(
            root=job_folder,
            assets=assets_folder,
            previews=previews_folder,
            renders=renders_folder,
            scripts=scripts_folder,
            logs=logs_folder
        )

    def list_clients(self) -> List[str]:
        """
        List all client folders.

        Returns:
            List of client names (unsanitized if possible, otherwise folder names)
        """
        if not self.settings.use_hierarchical_folders:
            return []

        base = Path(self.settings.base_output_path)
        if not base.exists():
            return []

        return [folder.name for folder in base.iterdir() if folder.is_dir()]

    def list_batches(self, client_name: str) -> List[str]:
        """
        List all batch folders for a client.

        Args:
            client_name: Name of the client

        Returns:
            List of batch IDs
        """
        if not self.settings.use_hierarchical_folders:
            return []

        client_folder = self.get_client_folder(client_name)
        if not client_folder.exists():
            return []

        return [folder.name for folder in client_folder.iterdir() if folder.is_dir()]

    def list_jobs(self, client_name: str, batch_id: str) -> List[str]:
        """
        List all job folders for a batch.

        Args:
            client_name: Name of the client
            batch_id: Unique batch identifier

        Returns:
            List of job IDs
        """
        if not self.settings.use_hierarchical_folders:
            return []

        batch_folder = self.get_batch_folder(client_name, batch_id)
        if not batch_folder.exists():
            return []

        return [folder.name for folder in batch_folder.iterdir() if folder.is_dir()]

    def get_folder_info(self, client_name: str, batch_id: Optional[str] = None,
                       job_id: Optional[str] = None) -> Dict:
        """
        Get information about a folder (size, file count, etc.).

        Args:
            client_name: Name of the client
            batch_id: Optional batch identifier
            job_id: Optional job identifier

        Returns:
            Dictionary with folder information
        """
        if job_id and batch_id:
            folder = self.get_job_folder(client_name, batch_id, job_id)
        elif batch_id:
            folder = self.get_batch_folder(client_name, batch_id)
        else:
            folder = self.get_client_folder(client_name)

        if not folder.exists():
            return {
                'exists': False,
                'path': str(folder)
            }

        # Calculate folder size and file count
        total_size = 0
        file_count = 0
        for item in folder.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1

        return {
            'exists': True,
            'path': str(folder),
            'size_bytes': total_size,
            'size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count
        }


# Singleton instance
folder_manager = FolderManager()
