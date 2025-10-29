"""
Data Validation Service

Validates PSD and AEPX files before processing to catch issues early.
Provides detailed validation reports with errors and warnings.
"""

import os
import json
import csv
from typing import Dict, List, Optional
from PIL import Image
import xml.etree.ElementTree as ET

from services.base_service import BaseService, Result


class ValidationService(BaseService):
    """
    Service for validating files before processing

    Features:
    - File existence and readability checks
    - File size validation
    - Format validation
    - Dimension validation
    - Structure validation
    - Clear error and warning messages
    """

    def __init__(self, logger, enhanced_logging=None):
        """
        Initialize validation service

        Args:
            logger: Logger instance
            enhanced_logging: EnhancedLoggingService instance (optional)
        """
        super().__init__(logger, enhanced_logging=enhanced_logging)

        # Configurable limits
        self.max_psd_size = 500 * 1024 * 1024  # 500MB
        self.max_aepx_size = 50 * 1024 * 1024  # 50MB
        self.max_batch_rows = 1000  # Maximum rows in batch data
        self.min_dimension = 100  # 100px minimum
        self.max_dimension = 10000  # 10000px maximum

    def validate_psd(self, psd_path: str) -> Result:
        """
        Validate PSD file before processing

        Checks:
        1. File exists and is readable
        2. File size within limits (< 500MB)
        3. File is valid PSD format
        4. Has reasonable dimensions (100-10000px)
        5. Can be opened by PIL/Pillow
        6. Has at least basic structure

        Args:
            psd_path: Path to PSD file

        Returns:
            Result with validation details:
            Success case:
            {
                'valid': True,
                'file_size': int (bytes),
                'dimensions': [width, height],
                'warnings': List[str]  # Non-fatal issues
            }

            Failure case:
            {
                'valid': False,
                'errors': List[str],  # Fatal issues
                'warnings': List[str],
                'file_size': int or None,
                'dimensions': [width, height] or None
            }
        """
        try:
            self.log_info(f"Validating PSD: {psd_path}")

            errors = []
            warnings = []
            file_size = None
            dimensions = None

            # Check 1: File exists
            if not os.path.exists(psd_path):
                errors.append(f"File does not exist: {psd_path}")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': None,
                    'dimensions': None
                })

            # Check 2: File is readable
            if not os.access(psd_path, os.R_OK):
                errors.append("File is not readable (permission denied)")

            # Check 3: File size
            try:
                file_size = os.path.getsize(psd_path)

                if file_size == 0:
                    errors.append("File is empty (0 bytes)")
                elif file_size > self.max_psd_size:
                    errors.append(
                        f"File too large: {file_size / (1024*1024):.1f}MB "
                        f"(max: {self.max_psd_size / (1024*1024):.0f}MB)"
                    )
                elif file_size < 1024:  # Less than 1KB
                    warnings.append(f"File very small ({file_size} bytes) - may be incomplete")

            except OSError as e:
                errors.append(f"Cannot get file size: {e}")

            # Check 4: File extension
            if not psd_path.lower().endswith('.psd'):
                warnings.append("File does not have .psd extension")

            # Check 5: Try to open with PIL
            try:
                with Image.open(psd_path) as img:
                    dimensions = [img.width, img.height]

                    # Check dimensions
                    if img.width < self.min_dimension or img.height < self.min_dimension:
                        errors.append(
                            f"Dimensions too small: {img.width}×{img.height} "
                            f"(min: {self.min_dimension}px)"
                        )

                    if img.width > self.max_dimension or img.height > self.max_dimension:
                        errors.append(
                            f"Dimensions too large: {img.width}×{img.height} "
                            f"(max: {self.max_dimension}px)"
                        )

                    # Check aspect ratio sanity
                    aspect_ratio = img.width / img.height if img.height > 0 else 0
                    if aspect_ratio > 10 or aspect_ratio < 0.1:
                        warnings.append(
                            f"Unusual aspect ratio: {aspect_ratio:.2f} "
                            f"({img.width}×{img.height})"
                        )

                    # Check format
                    if img.format != 'PSD':
                        warnings.append(f"PIL detected format as {img.format}, not PSD")

            except Exception as e:
                errors.append(f"Cannot open file with PIL: {str(e)}")

            # Return result
            if errors:
                self.log_warning(f"PSD validation failed: {len(errors)} errors")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': file_size,
                    'dimensions': dimensions
                })
            else:
                if warnings:
                    self.log_warning(f"PSD validation passed with {len(warnings)} warnings")
                else:
                    self.log_info("PSD validation passed")

                return Result.success({
                    'valid': True,
                    'file_size': file_size,
                    'dimensions': dimensions,
                    'warnings': warnings
                })

        except Exception as e:
            self.log_error(f"PSD validation error: {e}", e)
            return Result.failure({
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'file_size': None,
                'dimensions': None
            })

    def validate_aepx(self, aepx_path: str) -> Result:
        """
        Validate AEPX file before processing

        Checks:
        1. File exists and is readable
        2. File size within limits (< 50MB)
        3. File is valid XML
        4. Has After Effects project structure
        5. Contains at least one composition
        6. Composition dimensions are reasonable

        Args:
            aepx_path: Path to AEPX file

        Returns:
            Result with validation details (same format as validate_psd)
        """
        try:
            self.log_info(f"Validating AEPX: {aepx_path}")

            errors = []
            warnings = []
            file_size = None
            dimensions = None

            # Check 1: File exists
            if not os.path.exists(aepx_path):
                errors.append(f"File does not exist: {aepx_path}")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': None,
                    'dimensions': None
                })

            # Check 2: File is readable
            if not os.access(aepx_path, os.R_OK):
                errors.append("File is not readable (permission denied)")

            # Check 3: File size
            try:
                file_size = os.path.getsize(aepx_path)

                if file_size == 0:
                    errors.append("File is empty (0 bytes)")
                elif file_size > self.max_aepx_size:
                    errors.append(
                        f"File too large: {file_size / (1024*1024):.1f}MB "
                        f"(max: {self.max_aepx_size / (1024*1024):.0f}MB)"
                    )
                elif file_size < 100:  # Less than 100 bytes
                    warnings.append(f"File very small ({file_size} bytes) - may be incomplete")

            except OSError as e:
                errors.append(f"Cannot get file size: {e}")

            # Check 4: File extension
            if not aepx_path.lower().endswith('.aepx'):
                warnings.append("File does not have .aepx extension")

            # Check 5: Try to parse as XML
            try:
                tree = ET.parse(aepx_path)
                root = tree.getroot()

                # Check 6: Has After Effects structure
                if root.tag != 'AfterEffectsProject':
                    errors.append(
                        f"Invalid AEPX structure: root tag is '{root.tag}', "
                        f"expected 'AfterEffectsProject'"
                    )

                # Check 7: Find compositions
                compositions = root.findall('.//Composition') or root.findall('.//comp')

                if not compositions:
                    errors.append("No compositions found in AEPX")
                else:
                    # Check first composition dimensions
                    first_comp = compositions[0]

                    # Try to find width/height (structure may vary)
                    width_elem = (first_comp.find('.//width') or
                                  first_comp.find('.//Width') or
                                  first_comp.get('width'))
                    height_elem = (first_comp.find('.//height') or
                                   first_comp.find('.//Height') or
                                   first_comp.get('height'))

                    if width_elem is not None and height_elem is not None:
                        try:
                            # Handle both element text and attribute
                            width = int(width_elem.text if hasattr(width_elem, 'text')
                                        else width_elem)
                            height = int(height_elem.text if hasattr(height_elem, 'text')
                                         else height_elem)

                            dimensions = [width, height]

                            # Check dimensions
                            if width < self.min_dimension or height < self.min_dimension:
                                errors.append(
                                    f"Composition dimensions too small: {width}×{height} "
                                    f"(min: {self.min_dimension}px)"
                                )

                            if width > self.max_dimension or height > self.max_dimension:
                                errors.append(
                                    f"Composition dimensions too large: {width}×{height} "
                                    f"(max: {self.max_dimension}px)"
                                )

                            # Check aspect ratio
                            aspect_ratio = width / height if height > 0 else 0
                            if aspect_ratio > 10 or aspect_ratio < 0.1:
                                warnings.append(
                                    f"Unusual aspect ratio: {aspect_ratio:.2f} "
                                    f"({width}×{height})"
                                )

                        except (ValueError, TypeError) as e:
                            warnings.append(f"Cannot parse composition dimensions: {e}")

                    else:
                        warnings.append("Composition dimensions not found in expected structure")

                    # Warn if many compositions
                    if len(compositions) > 50:
                        warnings.append(
                            f"Many compositions found ({len(compositions)}) - "
                            f"processing may be slow"
                        )

            except ET.ParseError as e:
                errors.append(f"Invalid XML format: {str(e)}")
            except Exception as e:
                errors.append(f"Cannot parse AEPX: {str(e)}")

            # Return result
            if errors:
                self.log_warning(f"AEPX validation failed: {len(errors)} errors")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': file_size,
                    'dimensions': dimensions
                })
            else:
                if warnings:
                    self.log_warning(f"AEPX validation passed with {len(warnings)} warnings")
                else:
                    self.log_info("AEPX validation passed")

                return Result.success({
                    'valid': True,
                    'file_size': file_size,
                    'dimensions': dimensions,
                    'warnings': warnings
                })

        except Exception as e:
            self.log_error(f"AEPX validation error: {e}", e)
            return Result.failure({
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'file_size': None,
                'dimensions': None
            })

    def validate_project_files(
        self,
        psd_path: Optional[str] = None,
        aepx_path: Optional[str] = None
    ) -> Result:
        """
        Validate both PSD and AEPX files for a project

        Args:
            psd_path: Optional PSD file path
            aepx_path: Optional AEPX file path

        Returns:
            Result with combined validation:
            {
                'valid': bool,  # True only if all provided files are valid
                'psd': {...},   # PSD validation result or None
                'aepx': {...},  # AEPX validation result or None
                'total_errors': int,
                'total_warnings': int
            }
        """
        try:
            self.log_info("Validating project files")

            psd_result = None
            aepx_result = None
            total_errors = 0
            total_warnings = 0

            # Validate PSD if provided
            if psd_path:
                psd_validation = self.validate_psd(psd_path)
                if psd_validation.is_success():
                    psd_result = psd_validation.get_data()
                    total_warnings += len(psd_result.get('warnings', []))
                else:
                    psd_result = psd_validation.get_error()
                    if isinstance(psd_result, dict):
                        total_errors += len(psd_result.get('errors', []))
                        total_warnings += len(psd_result.get('warnings', []))

            # Validate AEPX if provided
            if aepx_path:
                aepx_validation = self.validate_aepx(aepx_path)
                if aepx_validation.is_success():
                    aepx_result = aepx_validation.get_data()
                    total_warnings += len(aepx_result.get('warnings', []))
                else:
                    aepx_result = aepx_validation.get_error()
                    if isinstance(aepx_result, dict):
                        total_errors += len(aepx_result.get('errors', []))
                        total_warnings += len(aepx_result.get('warnings', []))

            # Check if at least one file was provided
            if not psd_path and not aepx_path:
                return Result.failure({
                    'valid': False,
                    'psd': None,
                    'aepx': None,
                    'total_errors': 1,
                    'total_warnings': 0,
                    'error': 'No files provided for validation'
                })

            # Determine overall validity
            all_valid = (
                (psd_result is None or psd_result.get('valid', False))
                and
                (aepx_result is None or aepx_result.get('valid', False))
            )

            result_data = {
                'valid': all_valid,
                'psd': psd_result,
                'aepx': aepx_result,
                'total_errors': total_errors,
                'total_warnings': total_warnings
            }

            if all_valid:
                self.log_info(
                    f"Project validation passed "
                    f"({total_warnings} warnings)"
                )
                return Result.success(result_data)
            else:
                self.log_warning(
                    f"Project validation failed "
                    f"({total_errors} errors, {total_warnings} warnings)"
                )
                return Result.failure(result_data)

        except Exception as e:
            self.log_error(f"Project validation error: {e}", e)
            return Result.failure({
                'valid': False,
                'psd': None,
                'aepx': None,
                'total_errors': 1,
                'total_warnings': 0,
                'error': str(e)
            })

    def get_validation_summary(self, validation_result: Dict) -> str:
        """
        Get human-readable validation summary

        Args:
            validation_result: Validation result dict

        Returns:
            Formatted summary string
        """
        lines = []

        if validation_result.get('valid'):
            lines.append("✅ Validation Passed")
        else:
            lines.append("❌ Validation Failed")

        # PSD summary
        if validation_result.get('psd'):
            psd = validation_result['psd']
            lines.append("\nPSD File:")

            if psd.get('valid'):
                lines.append("  ✅ Valid")
                if psd.get('file_size'):
                    lines.append(f"  Size: {psd['file_size'] / (1024*1024):.1f} MB")
                if psd.get('dimensions'):
                    lines.append(f"  Dimensions: {psd['dimensions'][0]}×{psd['dimensions'][1]}")
            else:
                lines.append("  ❌ Invalid")
                for error in psd.get('errors', []):
                    lines.append(f"    • {error}")

            for warning in psd.get('warnings', []):
                lines.append(f"  ⚠ {warning}")

        # AEPX summary
        if validation_result.get('aepx'):
            aepx = validation_result['aepx']
            lines.append("\nAEPX File:")

            if aepx.get('valid'):
                lines.append("  ✅ Valid")
                if aepx.get('file_size'):
                    lines.append(f"  Size: {aepx['file_size'] / 1024:.1f} KB")
                if aepx.get('dimensions'):
                    lines.append(f"  Dimensions: {aepx['dimensions'][0]}×{aepx['dimensions'][1]}")
            else:
                lines.append("  ❌ Invalid")
                for error in aepx.get('errors', []):
                    lines.append(f"    • {error}")

            for warning in aepx.get('warnings', []):
                lines.append(f"  ⚠ {warning}")

        # Summary stats
        lines.append(f"\nTotal Errors: {validation_result.get('total_errors', 0)}")
        lines.append(f"Total Warnings: {validation_result.get('total_warnings', 0)}")

        return "\n".join(lines)

    def validate_hard_card_json(self, json_path: str) -> Result:
        """
        Validate Hard Card JSON file

        Checks:
        1. File exists and is readable
        2. File is valid JSON
        3. Has required fields
        4. Field values are valid types
        5. Variable names follow conventions

        Args:
            json_path: Path to Hard Card JSON file

        Returns:
            Result with validation details (same format as other validators)
        """
        try:
            self.log_info(f"Validating Hard Card JSON: {json_path}")

            errors = []
            warnings = []
            file_size = None

            # Check 1: File exists
            if not os.path.exists(json_path):
                errors.append(f"File does not exist: {json_path}")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': None
                })

            # Check 2: File is readable
            if not os.access(json_path, os.R_OK):
                errors.append("File is not readable (permission denied)")

            # Check 3: File size
            try:
                file_size = os.path.getsize(json_path)

                if file_size == 0:
                    errors.append("File is empty (0 bytes)")
                elif file_size > 10 * 1024 * 1024:  # 10MB max for JSON
                    errors.append(f"File too large: {file_size / (1024*1024):.1f}MB (max: 10MB)")

            except OSError as e:
                errors.append(f"Cannot get file size: {e}")

            # Check 4: Valid JSON
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check 5: Is a dictionary
                if not isinstance(data, dict):
                    errors.append("JSON root must be an object/dictionary")
                else:
                    # Check 6: Required fields for Hard Card
                    required_fields = ['variables']  # At minimum should have variables

                    for field in required_fields:
                        if field not in data:
                            errors.append(f"Missing required field: '{field}'")

                    # Check 7: Variables structure
                    if 'variables' in data:
                        variables = data['variables']

                        if not isinstance(variables, dict):
                            errors.append("'variables' must be an object/dictionary")
                        else:
                            # Check variable naming and types
                            for var_name, var_value in variables.items():
                                # Check naming convention
                                if not var_name.replace('_', '').isalnum():
                                    warnings.append(
                                        f"Variable name '{var_name}' contains non-alphanumeric characters"
                                    )

                                # Check value type
                                if not isinstance(var_value, (str, int, float, bool, type(None))):
                                    warnings.append(
                                        f"Variable '{var_name}' has complex type (not string/number/bool)"
                                    )

                            # Warn if no variables
                            if len(variables) == 0:
                                warnings.append("No variables defined in Hard Card")
                            elif len(variables) > 100:
                                warnings.append(
                                    f"Many variables defined ({len(variables)}) - may impact performance"
                                )

            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON format: {str(e)}")
            except UnicodeDecodeError as e:
                errors.append(f"File encoding error: {str(e)}")
            except Exception as e:
                errors.append(f"Cannot parse JSON: {str(e)}")

            # Return result
            if errors:
                self.log_warning(f"Hard Card JSON validation failed: {len(errors)} errors")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': file_size
                })
            else:
                if warnings:
                    self.log_warning(f"Hard Card JSON validation passed with {len(warnings)} warnings")
                else:
                    self.log_info("Hard Card JSON validation passed")

                return Result.success({
                    'valid': True,
                    'file_size': file_size,
                    'warnings': warnings
                })

        except Exception as e:
            self.log_error(f"Hard Card JSON validation error: {e}", e)
            return Result.failure({
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'file_size': None
            })

    def validate_batch_data(self, batch_path: str) -> Result:
        """
        Validate batch data file (CSV)

        Checks:
        1. File exists and is readable
        2. File is valid CSV
        3. Has header row
        4. Has required columns
        5. Row count within limits
        6. Data types are reasonable

        Args:
            batch_path: Path to CSV batch file

        Returns:
            Result with validation details:
            Success: {'valid': True, 'file_size': int, 'row_count': int, 'columns': [], 'warnings': []}
            Failure: {'valid': False, 'errors': [], 'warnings': [], 'file_size': int or None}
        """
        try:
            self.log_info(f"Validating batch data: {batch_path}")

            errors = []
            warnings = []
            file_size = None
            row_count = 0
            columns = []

            # Check 1: File exists
            if not os.path.exists(batch_path):
                errors.append(f"File does not exist: {batch_path}")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': None,
                    'row_count': 0,
                    'columns': []
                })

            # Check 2: File is readable
            if not os.access(batch_path, os.R_OK):
                errors.append("File is not readable (permission denied)")

            # Check 3: File size
            try:
                file_size = os.path.getsize(batch_path)

                if file_size == 0:
                    errors.append("File is empty (0 bytes)")
                elif file_size > 50 * 1024 * 1024:  # 50MB max for CSV
                    errors.append(f"File too large: {file_size / (1024*1024):.1f}MB (max: 50MB)")

            except OSError as e:
                errors.append(f"Cannot get file size: {e}")

            # Check 4: File extension
            if not batch_path.lower().endswith('.csv'):
                warnings.append("File does not have .csv extension")

            # Check 5: Parse CSV
            try:
                with open(batch_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)

                    # Get column names
                    columns = reader.fieldnames or []

                    if not columns:
                        errors.append("No header row found in CSV")
                    else:
                        # Check for empty column names
                        empty_cols = [i for i, col in enumerate(columns) if not col or col.strip() == '']
                        if empty_cols:
                            errors.append(f"Empty column names at positions: {empty_cols}")

                        # Count rows
                        for row in reader:
                            row_count += 1

                            # Check row count limit
                            if row_count > self.max_batch_rows:
                                errors.append(
                                    f"Too many rows: {row_count} (max: {self.max_batch_rows})"
                                )
                                break

                        # Check minimum rows
                        if row_count == 0:
                            warnings.append("CSV has header but no data rows")
                        elif row_count < 5:
                            warnings.append(f"Only {row_count} data rows - file may be incomplete")

            except csv.Error as e:
                errors.append(f"Invalid CSV format: {str(e)}")
            except UnicodeDecodeError as e:
                errors.append(f"File encoding error: {str(e)}")
            except Exception as e:
                errors.append(f"Cannot parse CSV: {str(e)}")

            # Return result
            if errors:
                self.log_warning(f"Batch data validation failed: {len(errors)} errors")
                return Result.failure({
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'file_size': file_size,
                    'row_count': row_count,
                    'columns': columns
                })
            else:
                if warnings:
                    self.log_warning(f"Batch data validation passed with {len(warnings)} warnings")
                else:
                    self.log_info(f"Batch data validation passed ({row_count} rows)")

                return Result.success({
                    'valid': True,
                    'file_size': file_size,
                    'row_count': row_count,
                    'columns': columns,
                    'warnings': warnings
                })

        except Exception as e:
            self.log_error(f"Batch data validation error: {e}", e)
            return Result.failure({
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'file_size': None,
                'row_count': 0,
                'columns': []
            })

    def validate_generated_aepx(self, aepx_path: str, expected_expressions: bool = True) -> Result:
        """
        Validate generated AEPX output file before delivery

        Checks:
        1. File exists and is readable
        2. File is valid XML
        3. Has After Effects structure
        4. Contains compositions
        5. If expected_expressions=True, verifies expressions were added
        6. No obvious corruption

        Args:
            aepx_path: Path to generated AEPX file
            expected_expressions: Whether expressions should be present

        Returns:
            Result with validation details (same format as validate_aepx plus expression info)
        """
        try:
            self.log_info(f"Validating generated AEPX: {aepx_path}")

            # Use existing AEPX validation
            base_result = self.validate_aepx(aepx_path)

            if not base_result.is_success():
                # Base validation failed
                return base_result

            # Get base validation data
            validation_data = base_result.get_data()
            errors = []
            warnings = validation_data.get('warnings', [])

            # Additional checks for generated AEPX
            try:
                tree = ET.parse(aepx_path)
                root = tree.getroot()

                # Check for expressions if expected
                if expected_expressions:
                    # Look for expression indicators in XML
                    # (structure may vary, looking for common patterns)
                    expr_elements = (
                        root.findall('.//expression') or
                        root.findall('.//Expression') or
                        root.findall('.//expr')
                    )

                    if not expr_elements:
                        warnings.append(
                            "No expression elements found - expressions may not have been applied"
                        )
                    else:
                        self.log_info(f"Found {len(expr_elements)} expression elements")

                # Check for Hard Card composition
                comps = root.findall('.//Composition') or root.findall('.//comp')
                hard_card_found = False

                for comp in comps:
                    comp_name = (comp.get('name') or
                                comp.find('.//name') or
                                comp.find('.//Name'))

                    if comp_name:
                        name_text = comp_name.text if hasattr(comp_name, 'text') else str(comp_name)
                        if 'hard' in name_text.lower() and 'card' in name_text.lower():
                            hard_card_found = True
                            break

                if expected_expressions and not hard_card_found:
                    warnings.append("Hard Card composition not found - expressions may not work")

            except Exception as e:
                warnings.append(f"Additional validation checks failed: {str(e)}")

            # Update validation data
            validation_data['warnings'] = warnings

            if errors:
                validation_data['valid'] = False
                validation_data['errors'] = errors
                self.log_warning(f"Generated AEPX validation failed: {len(errors)} errors")
                return Result.failure(validation_data)
            else:
                if warnings:
                    self.log_warning(
                        f"Generated AEPX validation passed with {len(warnings)} warnings"
                    )
                else:
                    self.log_info("Generated AEPX validation passed")

                return Result.success(validation_data)

        except Exception as e:
            self.log_error(f"Generated AEPX validation error: {e}", e)
            return Result.failure({
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'file_size': None,
                'dimensions': None
            })
