"""
Service for applying conflict resolutions.
"""

from typing import Dict, Any
from PIL import Image
import os
from pathlib import Path
from services.base_service import BaseService, Result


class ConflictResolutionService(BaseService):
    """Handles applying resolution actions to conflicts."""

    def apply_resolution(self, conflict: Dict[str, Any], resolution_id: str,
                        psd_path: str, output_folder: str) -> Result[Dict[str, Any]]:
        """
        Apply a resolution action to a conflict.

        Args:
            conflict: Conflict dictionary with resolution_options
            resolution_id: ID of the resolution to apply
            psd_path: Path to PSD file
            output_folder: Output folder for modified files

        Returns:
            Result containing:
                - modified_path: str (path to modified file if applicable)
                - message: str
                - requires_upload: bool (if user needs to upload new file)
                - min_dimensions: dict (if reupload required)
        """
        self.log_info(f"Applying resolution '{resolution_id}' to conflict '{conflict.get('id')}'")

        # Find the selected resolution option
        resolution = next(
            (r for r in conflict.get('resolution_options', []) if r['id'] == resolution_id),
            None
        )

        if not resolution:
            return Result.failure(f"Resolution '{resolution_id}' not found")

        params = resolution.get('params', {})
        method = params.get('method')

        # Handle different resolution methods
        if method == 'crop':
            return self._crop_image(psd_path, params, output_folder)
        elif method == 'scale_fill':
            return self._scale_fill(psd_path, params, output_folder)
        elif method == 'scale_fit':
            return self._scale_fit(psd_path, params, output_folder)
        elif method in ['accept', 'none']:
            return Result.success({
                'message': 'Accepted as-is, no changes made'
            })
        elif method == 'reupload':
            return Result.success({
                'message': 'Waiting for user to upload new file',
                'requires_upload': True,
                'min_dimensions': {
                    'width': params.get('min_width'),
                    'height': params.get('min_height')
                }
            })
        elif method == 'manual_adjust':
            return Result.success({
                'message': f"Please recreate PSD at {params.get('target_width')}×{params.get('target_height')}",
                'requires_manual_action': True,
                'target_dimensions': {
                    'width': params.get('target_width'),
                    'height': params.get('target_height')
                }
            })
        else:
            return Result.failure(f"Unknown resolution method: {method}")

    def _crop_image(self, image_path: str, params: Dict, output_folder: str) -> Result[Dict]:
        """
        Crop image to target aspect ratio.

        Args:
            image_path: Path to source image
            params: Crop parameters (target_aspect, anchor)
            output_folder: Output folder

        Returns:
            Result with modified_path and message
        """
        try:
            img = Image.open(image_path)
            target_aspect = params['target_aspect']
            anchor = params.get('anchor', 'center')

            current_aspect = img.width / img.height

            if current_aspect > target_aspect:
                # Image is wider - crop width
                new_width = int(img.height * target_aspect)
                left = (img.width - new_width) // 2 if anchor == 'center' else 0
                cropped = img.crop((left, 0, left + new_width, img.height))
            else:
                # Image is taller - crop height
                new_height = int(img.width / target_aspect)
                top = (img.height - new_height) // 2 if anchor == 'center' else 0
                cropped = img.crop((0, top, img.width, top + new_height))

            # Save modified image
            output_path = Path(output_folder) / f"cropped_{Path(image_path).name}"
            cropped.save(output_path)

            self.log_info(f"Cropped image saved to: {output_path}")

            return Result.success({
                'modified_path': str(output_path),
                'message': f'Image cropped to aspect ratio {target_aspect:.2f}',
                'original_size': f'{img.width}×{img.height}',
                'new_size': f'{cropped.width}×{cropped.height}'
            })

        except Exception as e:
            self.log_error(f"Crop failed: {image_path}", exc=e)
            return Result.failure(f'Crop failed: {str(e)}')

    def _scale_fill(self, image_path: str, params: Dict, output_folder: str) -> Result[Dict]:
        """
        Scale image to fill target dimensions.

        Args:
            image_path: Path to source image
            params: Scale parameters (target_width, target_height)
            output_folder: Output folder

        Returns:
            Result with modified_path and message
        """
        try:
            img = Image.open(image_path)
            target_w = params['target_width']
            target_h = params['target_height']

            # Calculate scale to fill (covering entire area, may crop)
            scale_w = target_w / img.width
            scale_h = target_h / img.height
            scale = max(scale_w, scale_h)

            new_w = int(img.width * scale)
            new_h = int(img.height * scale)

            # Resize
            resized = img.resize((new_w, new_h), Image.LANCZOS)

            # Crop to exact dimensions if needed
            if new_w > target_w or new_h > target_h:
                left = (new_w - target_w) // 2
                top = (new_h - target_h) // 2
                resized = resized.crop((left, top, left + target_w, top + target_h))

            # Save modified image
            output_path = Path(output_folder) / f"scaled_fill_{Path(image_path).name}"
            resized.save(output_path)

            self.log_info(f"Scaled image (fill) saved to: {output_path}")

            return Result.success({
                'modified_path': str(output_path),
                'message': f'Image scaled to fill {target_w}×{target_h}',
                'original_size': f'{img.width}×{img.height}',
                'new_size': f'{target_w}×{target_h}'
            })

        except Exception as e:
            self.log_error(f"Scale fill failed: {image_path}", exc=e)
            return Result.failure(f'Scale fill failed: {str(e)}')

    def _scale_fit(self, image_path: str, params: Dict, output_folder: str) -> Result[Dict]:
        """
        Scale image to fit inside target dimensions.

        Args:
            image_path: Path to source image
            params: Scale parameters (target_width, target_height)
            output_folder: Output folder

        Returns:
            Result with modified_path and message
        """
        try:
            img = Image.open(image_path)
            target_w = params['target_width']
            target_h = params['target_height']

            # Calculate scale to fit (entire image visible, may have letterboxing)
            scale_w = target_w / img.width
            scale_h = target_h / img.height
            scale = min(scale_w, scale_h)

            new_w = int(img.width * scale)
            new_h = int(img.height * scale)

            # Resize
            resized = img.resize((new_w, new_h), Image.LANCZOS)

            # Create canvas with target dimensions
            canvas = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))

            # Paste resized image centered
            left = (target_w - new_w) // 2
            top = (target_h - new_h) // 2
            canvas.paste(resized, (left, top))

            # Save modified image
            output_path = Path(output_folder) / f"scaled_fit_{Path(image_path).name}"
            canvas.save(output_path)

            self.log_info(f"Scaled image (fit) saved to: {output_path}")

            return Result.success({
                'modified_path': str(output_path),
                'message': f'Image scaled to fit {target_w}×{target_h} (letterboxed)',
                'original_size': f'{img.width}×{img.height}',
                'new_size': f'{target_w}×{target_h} (content: {new_w}×{new_h})'
            })

        except Exception as e:
            self.log_error(f"Scale fit failed: {image_path}", exc=e)
            return Result.failure(f'Scale fit failed: {str(e)}')
