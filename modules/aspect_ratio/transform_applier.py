"""
Aspect Ratio Transform Applier

Applies calculated aspect ratio transformations to AEPX layer data.
Modifies composition dimensions, layer positions, scales, and adds letterbox backgrounds.
"""

from typing import Dict, Optional, List
from services.base_service import BaseService, Result


class TransformApplier(BaseService):
    """Apply aspect ratio transformations to AEPX data"""

    def __init__(self, logger):
        """
        Initialize transform applier

        Args:
            logger: Logger instance
        """
        super().__init__(logger)

    def apply_transform_to_aepx(
        self,
        aepx_data: Dict,
        transform_params: Dict,
        composition_name: Optional[str] = None
    ) -> Result:
        """
        Apply aspect ratio transformation to AEPX data

        Modifies aepx_data in-place to apply the calculated transformation.
        This includes:
        1. Update composition dimensions if needed
        2. Scale and reposition all layers
        3. Update anchor points
        4. Adjust masks if present
        5. Update composition background color for letterbox bars

        Args:
            aepx_data: Parsed AEPX data dict (from AEPXService)
            transform_params: Transform parameters from AspectRatioHandler.calculate_transform()
                {
                    'scale': float,
                    'offset_x': float,
                    'offset_y': float,
                    'method': 'fit' or 'fill',
                    'new_width': float,
                    'new_height': float,
                    'bars': 'horizontal' or 'vertical' or None
                }
            composition_name: Optional - which composition to transform (default: main comp)

        Returns Result with:
        {
            'layers_transformed': int,
            'compositions_updated': int,
            'scale_applied': float,
            'offset_applied': [x, y]
        }
        """
        try:
            self.log_info("Applying aspect ratio transformation to AEPX")

            # Validate transform parameters
            validation = validate_transform_params(transform_params)
            if not validation.is_success():
                return validation

            # Find target composition
            comp_data = self._find_composition(aepx_data, composition_name)
            if not comp_data:
                return Result.failure("Target composition not found")

            # Extract transform parameters
            scale = transform_params['scale']
            offset_x = transform_params['offset_x']
            offset_y = transform_params['offset_y']
            method = transform_params['method']
            new_width = transform_params.get('new_width')
            new_height = transform_params.get('new_height')
            bars = transform_params.get('bars')

            self.log_info(
                f"Transform params: scale={scale:.3f}, "
                f"offset=({offset_x:.1f}, {offset_y:.1f}), method={method}"
            )

            # Store original dimensions
            original_width = comp_data.get('width', 1920)
            original_height = comp_data.get('height', 1080)

            # Update composition dimensions if using 'fit' method with bars
            if method == 'fit' and bars:
                target_width = int(transform_params.get('target_width', new_width or original_width))
                target_height = int(transform_params.get('target_height', new_height or original_height))
                comp_data['width'] = target_width
                comp_data['height'] = target_height
                self.log_info(f"Updated comp dimensions: {target_width}×{target_height}")

            # Apply transformation to all layers
            layers_transformed = 0
            layers = comp_data.get('layers', [])

            for layer in layers:
                if self._should_transform_layer(layer):
                    self._transform_layer(layer, scale, offset_x, offset_y)
                    layers_transformed += 1

            self.log_info(f"Transformed {layers_transformed} layers")

            # Add background solid for letterbox bars if needed
            if method == 'fit' and bars:
                self._add_letterbox_background(comp_data, bars)

            return Result.success({
                'layers_transformed': layers_transformed,
                'compositions_updated': 1,
                'scale_applied': scale,
                'offset_applied': [offset_x, offset_y],
                'method': method,
                'original_dimensions': [original_width, original_height],
                'new_dimensions': [comp_data['width'], comp_data['height']]
            })

        except Exception as e:
            self.log_error(f"Transform application failed: {e}", e)
            return Result.failure(str(e))

    def _find_composition(
        self,
        aepx_data: Dict,
        comp_name: Optional[str]
    ) -> Optional[Dict]:
        """
        Find target composition in AEPX data

        If comp_name not specified, returns the main composition
        (first non-precomp or largest composition)

        Args:
            aepx_data: AEPX data dict
            comp_name: Optional composition name

        Returns:
            Composition dict or None
        """
        compositions = aepx_data.get('compositions', [])

        if not compositions:
            self.log_warning("No compositions found in AEPX data")
            return None

        if comp_name:
            # Find by name
            for comp in compositions:
                if comp.get('name') == comp_name:
                    self.log_info(f"Found composition by name: {comp_name}")
                    return comp
            self.log_warning(f"Composition '{comp_name}' not found")
            return None

        # Return main comp (heuristic: largest by area)
        main_comp = max(compositions, key=lambda c: c.get('width', 0) * c.get('height', 0))
        self.log_info(f"Using main composition: {main_comp.get('name', 'Unnamed')}")
        return main_comp

    def _should_transform_layer(self, layer: Dict) -> bool:
        """
        Determine if layer should be transformed

        Skip transformation for:
        - Adjustment layers
        - Guide layers
        - Layers with specific naming conventions (e.g., "_GUIDE_")
        - Null objects (usually controllers)

        Args:
            layer: Layer dict

        Returns:
            True if layer should be transformed
        """
        layer_name = layer.get('name', '').lower()

        # Skip guide layers
        if '_guide_' in layer_name or layer_name.startswith('guide'):
            self.log_info(f"Skipping guide layer: {layer.get('name')}")
            return False

        # Skip adjustment layers
        if layer.get('type') == 'adjustment':
            self.log_info(f"Skipping adjustment layer: {layer.get('name')}")
            return False

        # Skip null objects
        if layer.get('type') == 'null':
            self.log_info(f"Skipping null object: {layer.get('name')}")
            return False

        # Skip layers marked as guides
        if layer.get('is_guide', False):
            self.log_info(f"Skipping guide-marked layer: {layer.get('name')}")
            return False

        return True

    def _transform_layer(
        self,
        layer: Dict,
        scale: float,
        offset_x: float,
        offset_y: float
    ):
        """
        Apply transformation to a single layer

        Modifies layer dict in-place:
        - Scale position by scale factor
        - Add offsets
        - Scale anchor point
        - Update scale property

        Args:
            layer: Layer dict to transform
            scale: Scale factor
            offset_x: X offset in pixels
            offset_y: Y offset in pixels
        """
        # Get current position
        position = layer.get('position', [0, 0])

        # Apply scale and offset
        new_x = (position[0] * scale) + offset_x
        new_y = (position[1] * scale) + offset_y

        layer['position'] = [new_x, new_y]

        # Update anchor point if present
        if 'anchor_point' in layer:
            anchor = layer['anchor_point']
            if isinstance(anchor, list) and len(anchor) >= 2:
                layer['anchor_point'] = [
                    anchor[0] * scale,
                    anchor[1] * scale
                ]

        # Update scale property
        current_scale = layer.get('scale', [100, 100])
        if isinstance(current_scale, list) and len(current_scale) >= 2:
            layer['scale'] = [
                current_scale[0] * scale,
                current_scale[1] * scale
            ]

        # Update width/height for shape layers
        if 'width' in layer:
            layer['width'] = layer['width'] * scale
        if 'height' in layer:
            layer['height'] = layer['height'] * scale

        # Transform mask paths if present
        if 'masks' in layer and isinstance(layer['masks'], list):
            for mask in layer['masks']:
                self._transform_mask(mask, scale, offset_x, offset_y)

    def _transform_mask(
        self,
        mask: Dict,
        scale: float,
        offset_x: float,
        offset_y: float
    ):
        """
        Transform mask path coordinates

        Args:
            mask: Mask dict
            scale: Scale factor
            offset_x: X offset
            offset_y: Y offset
        """
        if 'path' in mask:
            path_data = mask['path']
            if isinstance(path_data, list):
                for point in path_data:
                    if isinstance(point, list) and len(point) >= 2:
                        point[0] = (point[0] * scale) + offset_x
                        point[1] = (point[1] * scale) + offset_y

            # Also check for vertices in path data
            elif isinstance(path_data, dict):
                if 'vertices' in path_data:
                    vertices = path_data['vertices']
                    if isinstance(vertices, list):
                        for vertex in vertices:
                            if isinstance(vertex, list) and len(vertex) >= 2:
                                vertex[0] = (vertex[0] * scale) + offset_x
                                vertex[1] = (vertex[1] * scale) + offset_y

    def _add_letterbox_background(
        self,
        comp_data: Dict,
        bars_direction: str
    ):
        """
        Add black solid background layer for letterbox bars

        Inserts at bottom of layer stack

        Args:
            comp_data: Composition dict
            bars_direction: 'horizontal' or 'vertical'
        """
        width = comp_data.get('width', 1920)
        height = comp_data.get('height', 1080)

        background_layer = {
            'id': 'letterbox_background',
            'name': 'Letterbox Background',
            'type': 'solid',
            'color': [0, 0, 0, 1],  # Black
            'position': [width / 2, height / 2],
            'anchor_point': [width / 2, height / 2],
            'width': width,
            'height': height,
            'scale': [100, 100],
            'opacity': 100,
            'enabled': True,
            'locked': True,
            'solo': False,
            'shy': False
        }

        # Insert at beginning (bottom layer in AE)
        layers = comp_data.get('layers', [])
        layers.insert(0, background_layer)
        comp_data['layers'] = layers

        self.log_info(f"Added letterbox background ({bars_direction} bars)")


def validate_transform_params(transform_params: Dict) -> Result:
    """
    Validate transform parameters before applying

    Checks:
    - Required keys present
    - Scale is positive
    - Method is valid
    - Dimensions are reasonable

    Args:
        transform_params: Transform parameters dict

    Returns:
        Result with validation errors or success
    """
    required_keys = ['scale', 'offset_x', 'offset_y', 'method']
    missing = [k for k in required_keys if k not in transform_params]

    if missing:
        return Result.failure(f"Missing required keys: {missing}")

    scale = transform_params.get('scale')
    if not isinstance(scale, (int, float)) or scale <= 0:
        return Result.failure("Scale must be a positive number")

    method = transform_params.get('method')
    if method not in ['fit', 'fill']:
        return Result.failure("Method must be 'fit' or 'fill'")

    # Validate offsets are numeric
    offset_x = transform_params.get('offset_x')
    offset_y = transform_params.get('offset_y')
    if not isinstance(offset_x, (int, float)):
        return Result.failure("offset_x must be numeric")
    if not isinstance(offset_y, (int, float)):
        return Result.failure("offset_y must be numeric")

    # Check for reasonable scale values
    if scale < 0.1 or scale > 10:
        return Result.failure(f"Scale out of reasonable range: {scale} (should be 0.1-10)")

    return Result.success({})
