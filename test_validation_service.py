"""
Tests for Data Validation Service

Tests file validation for PSD, AEPX, Hard Card JSON, batch CSV, and generated AEPX files.
"""

import unittest
import tempfile
import json
import csv
import os
from unittest.mock import MagicMock, patch, mock_open

from services.validation_service import ValidationService
from services.base_service import Result


class TestValidationService(unittest.TestCase):
    """Test ValidationService functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.logger = MagicMock()
        self.validation_service = ValidationService(self.logger)

        # Create temp directory for test files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # ==================== PSD Validation Tests ====================

    def test_validate_psd_file_not_found(self):
        """Test PSD validation - file doesn't exist"""
        result = self.validation_service.validate_psd('/nonexistent/file.psd')

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertFalse(error_data['valid'])
        self.assertTrue(any('does not exist' in err for err in error_data['errors']))

    def test_validate_psd_file_too_large(self):
        """Test PSD validation - file exceeds size limit"""
        # Create a temp file
        test_file = os.path.join(self.temp_dir, 'test.psd')
        with open(test_file, 'wb') as f:
            f.write(b'8BPS')  # PSD signature

        # Mock getsize to return large size
        with patch('os.path.getsize', return_value=600 * 1024 * 1024):
            result = self.validation_service.validate_psd(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any('too large' in err.lower() for err in error_data['errors']))

    def test_validate_psd_invalid_signature(self):
        """Test PSD validation - invalid PSD signature"""
        test_file = os.path.join(self.temp_dir, 'test.psd')
        with open(test_file, 'wb') as f:
            f.write(b'NOT_A_PSD_FILE')

        result = self.validation_service.validate_psd(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        # Check for either "Not a valid PSD" or "Cannot open" error
        self.assertTrue(any('Not a valid PSD' in err or 'Cannot open' in err
                           for err in error_data['errors']))

    # ==================== AEPX Validation Tests ====================

    def test_validate_aepx_file_not_found(self):
        """Test AEPX validation - file doesn't exist"""
        result = self.validation_service.validate_aepx('/nonexistent/file.aepx')

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertFalse(error_data['valid'])
        self.assertTrue(any('does not exist' in err for err in error_data['errors']))

    def test_validate_aepx_file_too_large(self):
        """Test AEPX validation - file exceeds size limit"""
        test_file = os.path.join(self.temp_dir, 'test.aepx')
        with open(test_file, 'w') as f:
            f.write('<AfterEffectsProject></AfterEffectsProject>')

        # Mock getsize to return large size
        with patch('os.path.getsize', return_value=60 * 1024 * 1024):
            result = self.validation_service.validate_aepx(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any('too large' in err.lower() for err in error_data['errors']))

    def test_validate_aepx_invalid_xml(self):
        """Test AEPX validation - invalid XML format"""
        test_file = os.path.join(self.temp_dir, 'test.aepx')
        with open(test_file, 'w') as f:
            f.write('NOT VALID XML <<>>')

        result = self.validation_service.validate_aepx(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any('Invalid XML' in err or 'parse' in err.lower()
                           for err in error_data['errors']))

    def test_validate_aepx_no_compositions(self):
        """Test AEPX validation - no compositions found"""
        test_file = os.path.join(self.temp_dir, 'test.aepx')
        with open(test_file, 'w') as f:
            f.write('<AfterEffectsProject></AfterEffectsProject>')

        result = self.validation_service.validate_aepx(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any('No compositions found' in err for err in error_data['errors']))

    def test_validate_aepx_success(self):
        """Test AEPX validation - valid file"""
        test_file = os.path.join(self.temp_dir, 'test.aepx')
        valid_xml = '''<?xml version="1.0"?>
        <AfterEffectsProject>
            <Composition name="Main Comp">
                <width>1920</width>
                <height>1080</height>
            </Composition>
        </AfterEffectsProject>
        '''
        with open(test_file, 'w') as f:
            f.write(valid_xml)

        result = self.validation_service.validate_aepx(test_file)

        self.assertTrue(result.is_success())
        data = result.get_data()
        self.assertTrue(data['valid'])
        # Warnings are okay, just check it's a list
        self.assertIsInstance(data['warnings'], list)

    # ==================== Hard Card JSON Validation Tests ====================

    def test_validate_hard_card_json_file_not_found(self):
        """Test Hard Card JSON validation - file doesn't exist"""
        result = self.validation_service.validate_hard_card_json('/nonexistent/file.json')

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertFalse(error_data['valid'])
        self.assertTrue(any('does not exist' in err for err in error_data['errors']))

    def test_validate_hard_card_json_invalid_format(self):
        """Test Hard Card JSON validation - invalid JSON format"""
        test_file = os.path.join(self.temp_dir, 'test.json')
        with open(test_file, 'w') as f:
            f.write('NOT VALID JSON {{}')

        result = self.validation_service.validate_hard_card_json(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any('Invalid JSON' in err for err in error_data['errors']))

    def test_validate_hard_card_json_missing_variables(self):
        """Test Hard Card JSON validation - missing 'variables' field"""
        test_file = os.path.join(self.temp_dir, 'test.json')
        with open(test_file, 'w') as f:
            json.dump({'other_field': 'value'}, f)

        result = self.validation_service.validate_hard_card_json(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any("Missing required field: 'variables'" in err
                           for err in error_data['errors']))

    def test_validate_hard_card_json_success(self):
        """Test Hard Card JSON validation - valid file"""
        test_file = os.path.join(self.temp_dir, 'test.json')
        with open(test_file, 'w') as f:
            json.dump({
                'variables': {
                    'candidate_name': 'John Doe',
                    'slogan': 'Vote for Change',
                    'district': '12'
                }
            }, f)

        result = self.validation_service.validate_hard_card_json(test_file)

        self.assertTrue(result.is_success())
        data = result.get_data()
        self.assertTrue(data['valid'])
        self.assertEqual(len(data['warnings']), 0)

    def test_validate_hard_card_json_too_many_variables(self):
        """Test Hard Card JSON validation - performance warning for many variables"""
        test_file = os.path.join(self.temp_dir, 'test.json')
        variables = {f'var_{i}': f'value_{i}' for i in range(150)}
        with open(test_file, 'w') as f:
            json.dump({'variables': variables}, f)

        result = self.validation_service.validate_hard_card_json(test_file)

        self.assertTrue(result.is_success())  # Warning, not error
        data = result.get_data()
        self.assertTrue(any('Many variables' in warn for warn in data['warnings']))

    # ==================== Batch Data CSV Validation Tests ====================

    def test_validate_batch_data_file_not_found(self):
        """Test batch data validation - file doesn't exist"""
        result = self.validation_service.validate_batch_data('/nonexistent/file.csv')

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertFalse(error_data['valid'])
        self.assertTrue(any('does not exist' in err for err in error_data['errors']))

    def test_validate_batch_data_empty_file(self):
        """Test batch data validation - empty file"""
        test_file = os.path.join(self.temp_dir, 'test.csv')
        with open(test_file, 'w') as f:
            f.write('')

        result = self.validation_service.validate_batch_data(test_file)

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertTrue(any('No data rows found' in err or 'empty' in err.lower()
                           for err in error_data['errors']))

    def test_validate_batch_data_success(self):
        """Test batch data validation - valid file"""
        test_file = os.path.join(self.temp_dir, 'test.csv')
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'district', 'slogan'])
            writer.writerow(['John Doe', '12', 'Vote for Change'])
            writer.writerow(['Jane Smith', '15', 'Together We Win'])
            writer.writerow(['Bob Johnson', '8', 'For the People'])

        result = self.validation_service.validate_batch_data(test_file)

        self.assertTrue(result.is_success())
        data = result.get_data()
        self.assertTrue(data['valid'])
        self.assertEqual(data['row_count'], 3)
        self.assertEqual(len(data['columns']), 3)

    def test_validate_batch_data_few_rows_warning(self):
        """Test batch data validation - warning for few rows"""
        test_file = os.path.join(self.temp_dir, 'test.csv')
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'district'])
            writer.writerow(['John Doe', '12'])

        result = self.validation_service.validate_batch_data(test_file)

        self.assertTrue(result.is_success())
        data = result.get_data()
        self.assertTrue(any('Only 1' in warn or 'few' in warn.lower()
                           for warn in data['warnings']))

    # ==================== Generated AEPX Validation Tests ====================

    def test_validate_generated_aepx_no_expressions(self):
        """Test generated AEPX validation - missing expressions"""
        test_file = os.path.join(self.temp_dir, 'test.aepx')
        xml_data = '''<?xml version="1.0"?>
        <AfterEffectsProject>
            <Composition name="Main Comp">
                <width>1920</width>
                <height>1080</height>
            </Composition>
        </AfterEffectsProject>
        '''
        with open(test_file, 'w') as f:
            f.write(xml_data)

        result = self.validation_service.validate_generated_aepx(test_file)

        self.assertTrue(result.is_success())  # Warning, not error
        data = result.get_data()
        self.assertTrue(any('No expression elements found' in warn
                           for warn in data['warnings']))

    def test_validate_generated_aepx_success(self):
        """Test generated AEPX validation - valid with expressions and Hard Card"""
        test_file = os.path.join(self.temp_dir, 'test.aepx')
        xml_data = '''<?xml version="1.0"?>
        <AfterEffectsProject>
            <Composition name="Main Comp">
                <width>1920</width>
                <height>1080</height>
                <expression>thisComp.layer("Hard_Card").text.sourceText</expression>
            </Composition>
            <Composition name="Hard_Card">
                <width>1920</width>
                <height>1080</height>
            </Composition>
        </AfterEffectsProject>
        '''
        with open(test_file, 'w') as f:
            f.write(xml_data)

        result = self.validation_service.validate_generated_aepx(test_file)

        self.assertTrue(result.is_success())
        data = result.get_data()
        self.assertTrue(data['valid'])
        # Check that there are no warnings about missing expressions or Hard Card
        self.assertFalse(any('No expression elements found' in w for w in data.get('warnings', [])))

    # ==================== Combined Validation Tests ====================

    def test_validate_project_files_psd_invalid(self):
        """Test combined project validation - PSD invalid"""
        result = self.validation_service.validate_project_files(
            '/nonexistent/file.psd',
            '/nonexistent/file.aepx'
        )

        self.assertFalse(result.is_success())
        error_data = result.get_error()
        self.assertFalse(error_data.get('psd_valid', False))

    # ==================== Validation Summary Tests ====================

    def test_get_validation_summary_all_valid(self):
        """Test validation summary - no errors or warnings"""
        validation_data = {
            'valid': True,
            'warnings': [],
            'file_size': 1024,
            'dimensions': [1920, 1080]
        }

        summary = self.validation_service.get_validation_summary(validation_data)

        self.assertIn('Passed', summary)
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

    def test_get_validation_summary_with_errors(self):
        """Test validation summary - with errors"""
        validation_data = {
            'valid': False,
            'errors': ['File too large', 'Invalid format'],
            'warnings': [],
            'file_size': 1024
        }

        summary = self.validation_service.get_validation_summary(validation_data)

        self.assertIn('Failed', summary)
        self.assertIsInstance(summary, str)

    def test_get_validation_summary_with_warnings(self):
        """Test validation summary - with warnings only"""
        validation_data = {
            'valid': True,
            'warnings': ['Unusual aspect ratio', 'Large file size'],
            'file_size': 1024,
            'dimensions': [1920, 1080]
        }

        summary = self.validation_service.get_validation_summary(validation_data)

        self.assertIn('Passed', summary)
        self.assertIsInstance(summary, str)

    def test_get_validation_summary_combined_project(self):
        """Test validation summary - combined PSD/AEPX validation"""
        validation_data = {
            'valid': True,
            'psd_valid': True,
            'aepx_valid': True,
            'psd': {
                'valid': True,
                'file_size': 10485760,
                'dimensions': [1920, 1080],
                'warnings': []
            },
            'aepx': {
                'valid': True,
                'file_size': 1024,
                'warnings': []
            }
        }

        summary = self.validation_service.get_validation_summary(validation_data)

        self.assertIn('Passed', summary)
        self.assertIn('PSD', summary)
        self.assertIn('AEPX', summary)


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Validation Service")
    print("=" * 70)
    print()

    # Run tests
    unittest.main(verbosity=2)
