"""
Pytest configuration and shared fixtures.

This file provides fixtures that are available to all test files.
"""

import pytest
import os
import shutil
import tempfile
from pathlib import Path
from PIL import Image
from datetime import datetime


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_psd_path(temp_dir):
    """Path to sample PSD file (does not create actual file)."""
    return os.path.join(temp_dir, 'sample.psd')


@pytest.fixture
def sample_aepx_path(temp_dir):
    """Path to sample AEPX file (does not create actual file)."""
    return os.path.join(temp_dir, 'sample.aepx')


@pytest.fixture
def sample_image(temp_dir):
    """Create a test image file."""
    img = Image.new('RGB', (100, 100), color='red')
    path = os.path.join(temp_dir, 'test_image.png')
    img.save(path)
    return path


@pytest.fixture
def large_image(temp_dir):
    """Create a large test image file."""
    img = Image.new('RGB', (1920, 1080), color='blue')
    path = os.path.join(temp_dir, 'large_image.png')
    img.save(path)
    return path


@pytest.fixture
def mock_psd_data():
    """Mock PSD data structure matching psd_parser output."""
    return {
        'filename': 'sample.psd',
        'width': 1920,
        'height': 1080,
        'layers': [
            {
                'name': 'Text Layer 1',
                'type': 'text',
                'text': {
                    'content': 'Sample Text',
                    'font': 'Arial',
                    'font_size': 48,
                    'color': {'r': 255, 'g': 255, 'b': 255}
                },
                'bbox': {'top': 100, 'left': 100, 'bottom': 200, 'right': 400},
                'width': 300,
                'height': 100,
                'visible': True
            },
            {
                'name': 'Text Layer 2',
                'type': 'text',
                'text': {
                    'content': 'Another Text',
                    'font': 'Helvetica',
                    'font_size': 36,
                    'color': {'r': 0, 'g': 0, 'b': 0}
                },
                'bbox': {'top': 300, 'left': 100, 'bottom': 380, 'right': 500},
                'width': 400,
                'height': 80,
                'visible': True
            },
            {
                'name': 'Image Layer 1',
                'type': 'image',
                'bbox': {'top': 500, 'left': 200, 'bottom': 800, 'right': 700},
                'width': 500,
                'height': 300,
                'visible': True
            },
            {
                'name': 'SmartObject Layer',
                'type': 'smartobject',
                'bbox': {'top': 50, 'left': 1000, 'bottom': 550, 'right': 1500},
                'width': 500,
                'height': 500,
                'visible': True
            }
        ]
    }


@pytest.fixture
def mock_aepx_data():
    """Mock AEPX data structure matching aepx_parser output."""
    return {
        'filename': 'template.aepx',
        'composition_name': 'Main Comp',
        'compositions': [
            {
                'name': 'Main Comp',
                'width': 1920,
                'height': 1080,
                'duration': 10.0,
                'layers': [
                    {
                        'name': 'Title Text',
                        'type': 'text',
                        'is_placeholder': True
                    },
                    {
                        'name': 'Subtitle Text',
                        'type': 'text',
                        'is_placeholder': True
                    },
                    {
                        'name': 'Featured Image',
                        'type': 'image',
                        'is_placeholder': True
                    }
                ]
            }
        ],
        'placeholders': [
            {
                'name': 'Title Text',
                'type': 'text',
                'layer_name': 'Title Text',
                'composition': 'Main Comp'
            },
            {
                'name': 'Subtitle Text',
                'type': 'text',
                'layer_name': 'Subtitle Text',
                'composition': 'Main Comp'
            },
            {
                'name': 'Featured Image',
                'type': 'image',
                'layer_name': 'Featured Image',
                'composition': 'Main Comp'
            }
        ]
    }


@pytest.fixture
def mock_mappings(mock_psd_data, mock_aepx_data):
    """Mock content mappings result."""
    return {
        'mappings': [
            {
                'psd_layer': 'Text Layer 1',
                'aepx_placeholder': 'Title Text',
                'type': 'text',
                'confidence': 0.95,
                'reason': 'Sequential match: 1st text layer → 1st text placeholder'
            },
            {
                'psd_layer': 'Text Layer 2',
                'aepx_placeholder': 'Subtitle Text',
                'type': 'text',
                'confidence': 0.90,
                'reason': 'Sequential match: 2nd text layer → 2nd text placeholder'
            },
            {
                'psd_layer': 'SmartObject Layer',
                'aepx_placeholder': 'Featured Image',
                'type': 'image',
                'confidence': 0.85,
                'reason': 'Name similarity match (score: 0.85), smartobject type'
            }
        ],
        'unmapped_psd_layers': ['Image Layer 1'],
        'unfilled_placeholders': []
    }


@pytest.fixture
def mock_preview_options():
    """Mock preview generation options."""
    return {
        'resolution': 'half',
        'duration': 5,
        'format': 'mp4',
        'quality': 'draft',
        'fps': 15
    }


@pytest.fixture
def invalid_psd_file(temp_dir):
    """Create an invalid PSD file (not actually a PSD)."""
    path = os.path.join(temp_dir, 'invalid.psd')
    with open(path, 'w') as f:
        f.write('This is not a PSD file')
    return path


@pytest.fixture
def invalid_aepx_file(temp_dir):
    """Create an invalid AEPX file (not actually XML)."""
    path = os.path.join(temp_dir, 'invalid.aepx')
    with open(path, 'w') as f:
        f.write('This is not an AEPX file')
    return path


@pytest.fixture
def valid_aepx_file(temp_dir):
    """Create a minimal valid AEPX file."""
    path = os.path.join(temp_dir, 'valid.aepx')
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<AfterEffectsProject xmlns="http://www.adobe.com/products/aftereffects">
    <string>Main Comp</string>
    <Layr>
        <string>Test Layer</string>
    </Layr>
</AfterEffectsProject>'''
    with open(path, 'w') as f:
        f.write(content)
    return path


@pytest.fixture
def empty_psd_data():
    """Mock PSD data with no layers."""
    return {
        'filename': 'empty.psd',
        'width': 1920,
        'height': 1080,
        'layers': []
    }


@pytest.fixture
def empty_aepx_data():
    """Mock AEPX data with no placeholders."""
    return {
        'filename': 'empty.aepx',
        'composition_name': 'Empty Comp',
        'compositions': [
            {
                'name': 'Empty Comp',
                'width': 1920,
                'height': 1080,
                'duration': 10.0,
                'layers': []
            }
        ],
        'placeholders': []
    }


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging between tests to avoid conflicts."""
    import logging
    # Clear all handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    # Reset logging level
    logging.root.setLevel(logging.WARNING)
    yield
