"""
Tests for Aspect Ratio Transform Applier

Tests the TransformApplier class that applies aspect ratio transformations to AEPX data.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock
import importlib.util

# Import services.base_service directly to avoid circular imports
spec = importlib.util.spec_from_file_location("base_service", "services/base_service.py")
base_service = importlib.util.module_from_spec(spec)
sys.modules['services.base_service'] = base_service
spec.loader.exec_module(base_service)

# Import transform_applier
spec = importlib.util.spec_from_file_location(
    "transform_applier",
    "modules/aspect_ratio/transform_applier.py"
)
transform_applier_module = importlib.util.module_from_spec(spec)
sys.modules['modules.aspect_ratio.transform_applier'] = transform_applier_module
spec.loader.exec_module(transform_applier_module)

TransformApplier = transform_applier_module.TransformApplier
validate_transform_params = transform_applier_module.validate_transform_params


class TestTransformApplier(unittest.TestCase):
    """Test TransformApplier functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.logger = MagicMock()
        self.applier = TransformApplier(self.logger)

        # Sample AEPX data structure
        self.sample_aepx = {
            'compositions': [
                {
                    'name': 'Main Comp',
                    'width': 1920,
                    'height': 1080,
                    'layers': [
                        {
                            'id': 'layer1',
                            'name': 'Content Layer',
                            'type': 'shape',
                            'position': [960, 540],
                            'anchor_point': [100, 50],
                            'scale': [100, 100],
                            'width': 200,
                            'height': 100,
                            'masks': []
                        },
                        {
                            'id': 'layer2',
                            'name': 'Text Layer',
                            'type': 'text',
                            'position': [500, 300],
                            'anchor_point': [0, 0],
                            'scale': [100, 100]
                        },
                        {
                            'id': 'guide1',
                            'name': '_GUIDE_Border',
                            'type': 'shape',
                            'position': [960, 540],
                            'scale': [100, 100]
                        },
                        {
                            'id': 'adj1',
                            'name': 'Color Adjustment',
                            'type': 'adjustment',
                            'position': [960, 540],
                            'scale': [100, 100]
                        },
                        {
                            'id': 'null1',
                            'name': 'Controller',
                            'type': 'null',
                            'position': [960, 540],
                            'scale': [100, 100]
                        }
                    ]
                }
            ]
        }

    def test_validate_transform_params_success(self):
        """Test parameter validation with valid params"""
        params = {
            'scale': 1.2,
            'offset_x': 50,
            'offset_y': 100,
            'method': 'fit'
        }

        result = validate_transform_params(params)
        self.assertTrue(result.is_success())

    def test_validate_transform_params_missing_keys(self):
        """Test parameter validation catches missing keys"""
        params = {
            'scale': 1.0,
            'offset_x': 0
            # Missing offset_y and method
        }

        result = validate_transform_params(params)
        self.assertFalse(result.is_success())
        self.assertIn('Missing required keys', result.get_error())

    def test_validate_transform_params_invalid_scale(self):
        """Test parameter validation catches invalid scale"""
        params = {
            'scale': -1.0,  # Negative scale
            'offset_x': 0,
            'offset_y': 0,
            'method': 'fit'
        }

        result = validate_transform_params(params)
        self.assertFalse(result.is_success())
        self.assertIn('Scale must be a positive number', result.get_error())

    def test_validate_transform_params_invalid_method(self):
        """Test parameter validation catches invalid method"""
        params = {
            'scale': 1.0,
            'offset_x': 0,
            'offset_y': 0,
            'method': 'stretch'  # Invalid method
        }

        result = validate_transform_params(params)
        self.assertFalse(result.is_success())
        self.assertIn('Method must be', result.get_error())

    def test_validate_transform_params_scale_out_of_range(self):
        """Test parameter validation catches unreasonable scale"""
        params = {
            'scale': 15.0,  # Too large
            'offset_x': 0,
            'offset_y': 0,
            'method': 'fit'
        }

        result = validate_transform_params(params)
        self.assertFalse(result.is_success())
        self.assertIn('Scale out of reasonable range', result.get_error())

    def test_find_composition_by_name(self):
        """Test finding composition by name"""
        comp = self.applier._find_composition(self.sample_aepx, 'Main Comp')

        self.assertIsNotNone(comp)
        self.assertEqual(comp['name'], 'Main Comp')
        self.assertEqual(comp['width'], 1920)

    def test_find_composition_main_by_size(self):
        """Test finding main composition by largest area"""
        # Add another smaller composition
        self.sample_aepx['compositions'].append({
            'name': 'Small Comp',
            'width': 1280,
            'height': 720,
            'layers': []
        })

        comp = self.applier._find_composition(self.sample_aepx, None)

        self.assertIsNotNone(comp)
        self.assertEqual(comp['name'], 'Main Comp')  # Largest comp

    def test_find_composition_not_found(self):
        """Test finding non-existent composition"""
        comp = self.applier._find_composition(self.sample_aepx, 'Nonexistent')

        self.assertIsNone(comp)

    def test_should_transform_layer_regular(self):
        """Test regular layers should be transformed"""
        layer = {
            'name': 'Content Layer',
            'type': 'shape'
        }

        should_transform = self.applier._should_transform_layer(layer)
        self.assertTrue(should_transform)

    def test_should_transform_layer_guide(self):
        """Test guide layers should be skipped"""
        layer = {
            'name': '_GUIDE_Border',
            'type': 'shape'
        }

        should_transform = self.applier._should_transform_layer(layer)
        self.assertFalse(should_transform)

    def test_should_transform_layer_adjustment(self):
        """Test adjustment layers should be skipped"""
        layer = {
            'name': 'Color Adjustment',
            'type': 'adjustment'
        }

        should_transform = self.applier._should_transform_layer(layer)
        self.assertFalse(should_transform)

    def test_should_transform_layer_null(self):
        """Test null objects should be skipped"""
        layer = {
            'name': 'Controller',
            'type': 'null'
        }

        should_transform = self.applier._should_transform_layer(layer)
        self.assertFalse(should_transform)

    def test_transform_layer_position(self):
        """Test layer position transformation"""
        layer = {
            'position': [960, 540],
            'anchor_point': [100, 50],
            'scale': [100, 100]
        }

        self.applier._transform_layer(layer, scale=0.5, offset_x=100, offset_y=50)

        # Position should be scaled and offset
        self.assertEqual(layer['position'], [960 * 0.5 + 100, 540 * 0.5 + 50])
        self.assertEqual(layer['position'], [580, 320])

    def test_transform_layer_anchor_point(self):
        """Test layer anchor point transformation"""
        layer = {
            'position': [960, 540],
            'anchor_point': [100, 50],
            'scale': [100, 100]
        }

        self.applier._transform_layer(layer, scale=2.0, offset_x=0, offset_y=0)

        # Anchor point should be scaled
        self.assertEqual(layer['anchor_point'], [200, 100])

    def test_transform_layer_scale_property(self):
        """Test layer scale property transformation"""
        layer = {
            'position': [960, 540],
            'scale': [100, 100]
        }

        self.applier._transform_layer(layer, scale=1.5, offset_x=0, offset_y=0)

        # Scale property should be multiplied
        self.assertEqual(layer['scale'], [150, 150])

    def test_transform_layer_dimensions(self):
        """Test layer width/height transformation"""
        layer = {
            'position': [960, 540],
            'scale': [100, 100],
            'width': 200,
            'height': 100
        }

        self.applier._transform_layer(layer, scale=2.0, offset_x=0, offset_y=0)

        # Dimensions should be scaled
        self.assertEqual(layer['width'], 400)
        self.assertEqual(layer['height'], 200)

    def test_transform_mask_paths(self):
        """Test mask path transformation"""
        mask = {
            'path': [[100, 200], [300, 400], [500, 600]]
        }

        self.applier._transform_mask(mask, scale=0.5, offset_x=50, offset_y=100)

        # All points should be scaled and offset
        expected = [
            [100 * 0.5 + 50, 200 * 0.5 + 100],
            [300 * 0.5 + 50, 400 * 0.5 + 100],
            [500 * 0.5 + 50, 600 * 0.5 + 100]
        ]
        self.assertEqual(mask['path'], expected)

    def test_transform_mask_vertices(self):
        """Test mask vertices transformation"""
        mask = {
            'path': {
                'vertices': [[100, 200], [300, 400]]
            }
        }

        self.applier._transform_mask(mask, scale=2.0, offset_x=0, offset_y=0)

        # Vertices should be scaled
        expected = [[200, 400], [600, 800]]
        self.assertEqual(mask['path']['vertices'], expected)

    def test_add_letterbox_background(self):
        """Test adding letterbox background layer"""
        comp = {
            'width': 1920,
            'height': 1080,
            'layers': []
        }

        self.applier._add_letterbox_background(comp, 'horizontal')

        # Background layer should be added
        self.assertEqual(len(comp['layers']), 1)
        bg = comp['layers'][0]
        self.assertEqual(bg['id'], 'letterbox_background')
        self.assertEqual(bg['name'], 'Letterbox Background')
        self.assertEqual(bg['type'], 'solid')
        self.assertEqual(bg['color'], [0, 0, 0, 1])  # Black
        self.assertEqual(bg['width'], 1920)
        self.assertEqual(bg['height'], 1080)
        self.assertTrue(bg['locked'])

    def test_apply_transform_fit_method(self):
        """Test applying fit transformation with letterbox"""
        transform_params = {
            'scale': 0.9,
            'offset_x': 0,
            'offset_y': 100,
            'method': 'fit',
            'bars': 'horizontal',
            'target_width': 1920,
            'target_height': 1920
        }

        result = self.applier.apply_transform_to_aepx(
            self.sample_aepx,
            transform_params
        )

        # Should succeed
        self.assertTrue(result.is_success())

        # Check result data
        data = result.get_data()
        self.assertEqual(data['scale_applied'], 0.9)
        self.assertEqual(data['offset_applied'], [0, 100])
        self.assertEqual(data['method'], 'fit')

        # Should transform 2 layers (skip guide, adjustment, null)
        self.assertEqual(data['layers_transformed'], 2)

        # Composition dimensions should be updated
        comp = self.sample_aepx['compositions'][0]
        self.assertEqual(comp['width'], 1920)
        self.assertEqual(comp['height'], 1920)

        # Background layer should be added
        # Total layers: 5 original + 1 background = 6
        self.assertEqual(len(comp['layers']), 6)

        # First layer should be background
        bg = comp['layers'][0]
        self.assertEqual(bg['id'], 'letterbox_background')

    def test_apply_transform_fill_method(self):
        """Test applying fill transformation (crop)"""
        transform_params = {
            'scale': 1.2,
            'offset_x': -100,
            'offset_y': -50,
            'method': 'fill',
            'bars': None
        }

        result = self.applier.apply_transform_to_aepx(
            self.sample_aepx,
            transform_params
        )

        # Should succeed
        self.assertTrue(result.is_success())

        # Check result data
        data = result.get_data()
        self.assertEqual(data['scale_applied'], 1.2)
        self.assertEqual(data['offset_applied'], [-100, -50])
        self.assertEqual(data['method'], 'fill')

        # Should transform 2 layers
        self.assertEqual(data['layers_transformed'], 2)

        # Composition dimensions should NOT be updated (fill doesn't change comp size)
        comp = self.sample_aepx['compositions'][0]
        self.assertEqual(comp['width'], 1920)
        self.assertEqual(comp['height'], 1080)

        # Background layer should NOT be added (fill doesn't need letterbox)
        # Total layers: 5 original (no background added)
        self.assertEqual(len(comp['layers']), 5)

    def test_apply_transform_invalid_params(self):
        """Test applying transform with invalid parameters"""
        invalid_params = {
            'scale': -1.0,  # Invalid
            'offset_x': 0,
            'offset_y': 0,
            'method': 'fit'
        }

        result = self.applier.apply_transform_to_aepx(
            self.sample_aepx,
            invalid_params
        )

        # Should fail validation
        self.assertFalse(result.is_success())
        self.assertIn('Scale must be a positive number', result.get_error())

    def test_apply_transform_no_compositions(self):
        """Test applying transform to AEPX with no compositions"""
        empty_aepx = {'compositions': []}

        valid_params = {
            'scale': 1.0,
            'offset_x': 0,
            'offset_y': 0,
            'method': 'fit'
        }

        result = self.applier.apply_transform_to_aepx(empty_aepx, valid_params)

        # Should fail - no composition found
        self.assertFalse(result.is_success())
        self.assertIn('Target composition not found', result.get_error())

    def test_apply_transform_specific_composition(self):
        """Test applying transform to specific composition by name"""
        # Add second composition
        self.sample_aepx['compositions'].append({
            'name': 'Target Comp',
            'width': 1280,
            'height': 720,
            'layers': [
                {
                    'id': 'layer_t1',
                    'name': 'Target Layer',
                    'type': 'shape',
                    'position': [640, 360],
                    'scale': [100, 100]
                }
            ]
        })

        transform_params = {
            'scale': 2.0,
            'offset_x': 0,
            'offset_y': 0,
            'method': 'fill'
        }

        result = self.applier.apply_transform_to_aepx(
            self.sample_aepx,
            transform_params,
            composition_name='Target Comp'
        )

        # Should succeed
        self.assertTrue(result.is_success())

        # Should transform 1 layer (only layer in Target Comp)
        data = result.get_data()
        self.assertEqual(data['layers_transformed'], 1)

        # Target comp should have transformed layer
        target_comp = self.sample_aepx['compositions'][1]
        self.assertEqual(target_comp['name'], 'Target Comp')
        target_layer = target_comp['layers'][0]
        self.assertEqual(target_layer['position'], [1280, 720])  # 640*2, 360*2

    def test_transform_preserves_layer_order(self):
        """Test that transformation preserves layer order"""
        original_layer_ids = [
            layer['id']
            for layer in self.sample_aepx['compositions'][0]['layers']
        ]

        transform_params = {
            'scale': 1.0,
            'offset_x': 0,
            'offset_y': 0,
            'method': 'fill'
        }

        result = self.applier.apply_transform_to_aepx(
            self.sample_aepx,
            transform_params
        )

        self.assertTrue(result.is_success())

        # Layer IDs should be in same order (fill doesn't add background)
        final_layer_ids = [
            layer['id']
            for layer in self.sample_aepx['compositions'][0]['layers']
        ]
        self.assertEqual(original_layer_ids, final_layer_ids)


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Aspect Ratio Transform Applier")
    print("=" * 70)
    print()

    # Run tests
    unittest.main(verbosity=2)
