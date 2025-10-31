"""
Batch Validator Service

Validates CSV batch files before processing (Stage 0).
Ensures all paths exist, formats are correct, and requirements are met.
"""

import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import re

try:
    from psd_tools import PSDImage
except ImportError:
    PSDImage = None

import xml.etree.ElementTree as ET


class BatchValidator:
    """
    Validates CSV batch files and individual job entries.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.required_columns = ['job_id', 'psd_path', 'aepx_path', 'output_name']
        self.optional_columns = ['client_name', 'project_name', 'priority', 'notes']
        self.valid_priorities = ['high', 'medium', 'low']

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)

    def log_error(self, message: str):
        """Log error message."""
        if self.logger:
            self.logger.error(message)

    def validate_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Comprehensive validation of batch CSV file.

        Args:
            csv_path: Path to uploaded CSV file

        Returns:
            {
                'valid': True/False,
                'batch_id': 'BATCH_20251030_143022',
                'total_jobs': 10,
                'valid_jobs': 8,
                'invalid_jobs': 2,
                'errors': [
                    {
                        'job_id': 'JOB003',
                        'row': 3,
                        'errors': ['PSD file not found at path', 'Invalid output name format']
                    }
                ],
                'warnings': [
                    {
                        'job_id': 'JOB005',
                        'row': 5,
                        'warnings': ['Priority not specified, defaulting to medium']
                    }
                ],
                'jobs': [...]  # List of validated job dicts
            }
        """
        print(f"\n{'='*70}")
        print(f"📋 CSV BATCH VALIDATION")
        print(f"{'='*70}")
        print(f"File: {Path(csv_path).name}")
        print(f"{'='*70}\n")

        self.log_info(f"Starting batch validation for {csv_path}")

        result = {
            'valid': True,
            'batch_id': self._generate_batch_id(),
            'total_jobs': 0,
            'valid_jobs': 0,
            'invalid_jobs': 0,
            'errors': [],
            'warnings': [],
            'jobs': []
        }

        # Read and parse CSV
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Validate headers
                header_errors = self._validate_headers(reader.fieldnames)
                if header_errors:
                    result['valid'] = False
                    result['errors'].append({
                        'row': 0,
                        'errors': header_errors
                    })
                    self.log_error(f"CSV header validation failed: {header_errors}")
                    return result

                # Validate each job row
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    result['total_jobs'] += 1

                    job_errors = []
                    job_warnings = []

                    # Validate this job
                    job_errors, job_warnings = self._validate_job_row(row)

                    if job_errors:
                        result['invalid_jobs'] += 1
                        result['errors'].append({
                            'job_id': row.get('job_id', f'Row {row_num}'),
                            'row': row_num,
                            'errors': job_errors
                        })
                        print(f"❌ Row {row_num}: {row.get('job_id', 'UNKNOWN')} - {len(job_errors)} error(s)")
                        for error in job_errors:
                            print(f"   • {error}")
                    else:
                        result['valid_jobs'] += 1
                        result['jobs'].append(self._normalize_job_row(row))
                        print(f"✅ Row {row_num}: {row['job_id']}")

                    if job_warnings:
                        result['warnings'].append({
                            'job_id': row.get('job_id'),
                            'row': row_num,
                            'warnings': job_warnings
                        })
                        for warning in job_warnings:
                            print(f"  ⚠️  {warning}")

        except Exception as e:
            result['valid'] = False
            result['errors'].append({
                'row': 0,
                'errors': [f'Failed to parse CSV: {str(e)}']
            })
            self.log_error(f"CSV parsing failed: {e}")
            return result

        # Final validation
        if result['invalid_jobs'] > 0:
            result['valid'] = False

        # Print summary
        print(f"\n{'='*70}")
        print(f"📊 VALIDATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total jobs: {result['total_jobs']}")
        print(f"✅ Valid: {result['valid_jobs']}")
        print(f"❌ Invalid: {result['invalid_jobs']}")
        print(f"⚠️  Warnings: {len(result['warnings'])}")

        if result['valid']:
            print(f"\n✅ BATCH READY FOR INGESTION")
            self.log_info(f"Batch {result['batch_id']} validated successfully: {result['valid_jobs']} jobs")
        else:
            print(f"\n❌ BATCH VALIDATION FAILED")
            print(f"Fix errors and re-upload CSV")
            self.log_error(f"Batch validation failed: {result['invalid_jobs']} invalid jobs")

        print(f"{'='*70}\n")

        return result

    def _validate_headers(self, headers: List[str]) -> List[str]:
        """Validate CSV headers."""
        errors = []

        if not headers:
            return ['CSV file is empty or has no headers']

        # Check required columns
        missing = [col for col in self.required_columns if col not in headers]
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")

        return errors

    def _validate_job_row(self, row: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """
        Validate individual job row.

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        # Validate job_id
        job_id = row.get('job_id', '').strip()
        if not job_id:
            errors.append("Missing job_id")
        elif not self._is_valid_job_id(job_id):
            errors.append(f"Invalid job_id format: {job_id} (use alphanumeric, underscore, dash only)")

        # Validate PSD path
        psd_path = row.get('psd_path', '').strip()
        if not psd_path:
            errors.append("Missing psd_path")
        else:
            psd_validation = self._validate_psd_path(psd_path)
            if psd_validation:
                errors.append(psd_validation)

        # Validate AEPX path
        aepx_path = row.get('aepx_path', '').strip()
        if not aepx_path:
            errors.append("Missing aepx_path")
        else:
            aepx_validation = self._validate_aepx_path(aepx_path)
            if aepx_validation:
                errors.append(aepx_validation)

        # Validate output_name
        output_name = row.get('output_name', '').strip()
        if not output_name:
            errors.append("Missing output_name")
        elif not self._is_valid_filename(output_name):
            errors.append(f"Invalid output_name: {output_name}")

        # Validate priority (optional)
        priority = row.get('priority', '').strip().lower()
        if priority and priority not in self.valid_priorities:
            warnings.append(f"Invalid priority '{priority}', defaulting to 'medium'")
        elif not priority:
            warnings.append("Priority not specified, defaulting to 'medium'")

        return errors, warnings

    def _is_valid_job_id(self, job_id: str) -> bool:
        """Check if job_id format is valid."""
        return bool(re.match(r'^[A-Za-z0-9_-]+$', job_id))

    def _validate_psd_path(self, psd_path: str) -> str:
        """
        Validate PSD file path.

        Returns:
            Error message if invalid, empty string if valid
        """
        path = Path(psd_path)

        # Check exists
        if not path.exists():
            return f"PSD file not found: {psd_path}"

        # Check readable
        if not path.is_file():
            return f"PSD path is not a file: {psd_path}"

        # Check extension
        if path.suffix.lower() != '.psd':
            return f"File is not a PSD: {psd_path}"

        # Try to open PSD (if psd-tools is available)
        # Note: We're lenient about version errors because newer PSDs may not be supported
        # by psd-tools but can still be processed by our PSD Layer Exporter
        if PSDImage:
            try:
                psd = PSDImage.open(psd_path)
                psd.close()
            except Exception as e:
                error_msg = str(e).lower()
                # Treat version errors as non-critical - allow file to proceed
                if 'version' in error_msg or 'invalid version' in error_msg:
                    # File exists and has .psd extension, let Stage 1 try to process it
                    return ""
                else:
                    # Other errors (corruption, etc.) are critical
                    return f"Invalid or corrupted PSD file: {str(e)}"

        return ""  # Valid

    def _validate_aepx_path(self, aepx_path: str) -> str:
        """
        Validate AEPX/AEP file path.

        Returns:
            Error message if invalid, empty string if valid
        """
        path = Path(aepx_path)

        # Check exists
        if not path.exists():
            return f"AEPX/AEP file not found: {aepx_path}"

        # Check readable
        if not path.is_file():
            return f"AEPX/AEP path is not a file: {aepx_path}"

        # Check extension
        ext = path.suffix.lower()
        if ext not in ['.aepx', '.aep']:
            return f"File is not AEPX/AEP: {aepx_path}"

        # If AEPX, try to parse XML
        if ext == '.aepx':
            try:
                tree = ET.parse(aepx_path)
                root = tree.getroot()
                if 'AfterEffects' not in root.tag:
                    return f"Invalid AEPX file structure"
            except Exception as e:
                return f"Invalid or corrupted AEPX file: {str(e)}"

        # AEP files can't be validated without opening AE
        # Just check it exists and has correct extension

        return ""  # Valid

    def _is_valid_filename(self, filename: str) -> bool:
        """Check if output filename is valid."""
        # Allow alphanumeric, underscore, dash, dot
        # Must end with .aep or .aepx
        pattern = r'^[A-Za-z0-9_-]+\.(aep|aepx)$'
        return bool(re.match(pattern, filename))

    def _normalize_job_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Normalize job row data.

        - Trim whitespace
        - Set defaults
        - Convert types
        """
        return {
            'job_id': row['job_id'].strip(),
            'psd_path': row['psd_path'].strip(),
            'aepx_path': row['aepx_path'].strip(),
            'output_name': row['output_name'].strip(),
            'client_name': row.get('client_name', '').strip() or None,
            'project_name': row.get('project_name', '').strip() or None,
            'priority': row.get('priority', 'medium').strip().lower(),
            'notes': row.get('notes', '').strip() or None
        }

    def _generate_batch_id(self) -> str:
        """Generate unique batch ID."""
        return f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
