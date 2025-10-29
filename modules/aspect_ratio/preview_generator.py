"""
Aspect Ratio Preview Generator

Generates visual previews for different aspect ratio transformation options
to help humans make informed decisions.
"""

import os
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
from services.base_service import BaseService, Result


class AspectRatioPreviewGenerator(BaseService):
    """Generate visual previews for aspect ratio transformations"""

    def __init__(self, logger):
        """
        Initialize preview generator

        Args:
            logger: Logger instance
        """
        super().__init__(logger)

    def generate_transformation_previews(
        self,
        psd_path: str,
        aepx_width: int,
        aepx_height: int,
        output_dir: str
    ) -> Result:
        """
        Generate visual previews for different transformation options

        Creates 3 preview images:
        1. fit_preview.jpg - Scale to fit (letterbox/pillarbox)
        2. fill_preview.jpg - Scale to fill (crop edges)
        3. original_preview.jpg - No transformation (for reference)

        Args:
            psd_path: Path to PSD file
            aepx_width: Target AEPX width
            aepx_height: Target AEPX height
            output_dir: Directory to save preview images

        Returns Result with:
        {
            'previews': {
                'fit': 'path/to/fit_preview.jpg',
                'fill': 'path/to/fill_preview.jpg',
                'original': 'path/to/original_preview.jpg'
            },
            'dimensions': {
                'psd': [width, height],
                'aepx': [width, height]
            },
            'transform_info': {
                'fit': {...},
                'fill': {...}
            }
        }
        """
        try:
            self.log_info(f"Generating aspect ratio previews for {psd_path}")

            # Load PSD as flattened image
            psd_image = Image.open(psd_path)
            psd_width, psd_height = psd_image.size

            self.log_info(f"PSD dimensions: {psd_width}×{psd_height}")
            self.log_info(f"Target dimensions: {aepx_width}×{aepx_height}")

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Generate previews
            previews = {}

            # 1. Original (for reference)
            original_path = os.path.join(output_dir, 'original_preview.jpg')
            self._save_preview_with_label(
                psd_image,
                original_path,
                f"Original PSD: {psd_width}×{psd_height}"
            )
            previews['original'] = original_path

            # 2. Fit (letterbox/pillarbox)
            fit_path = os.path.join(output_dir, 'fit_preview.jpg')
            fit_image, fit_info = self._create_fit_preview(
                psd_image,
                aepx_width,
                aepx_height
            )

            fit_label = f"Scale to Fit: {aepx_width}×{aepx_height}"
            if fit_info['bars']:
                fit_label += f" ({fit_info['bars']} bars)"

            self._save_preview_with_label(
                fit_image,
                fit_path,
                fit_label
            )
            previews['fit'] = fit_path

            # 3. Fill (crop)
            fill_path = os.path.join(output_dir, 'fill_preview.jpg')
            fill_image, fill_info = self._create_fill_preview(
                psd_image,
                aepx_width,
                aepx_height
            )

            crop_pct = (1.0 - min(aepx_width / fill_info['scaled_width'],
                                   aepx_height / fill_info['scaled_height'])) * 100

            fill_label = f"Scale to Fill: {aepx_width}×{aepx_height}"
            if crop_pct > 1:
                fill_label += f" (~{crop_pct:.0f}% cropped)"

            self._save_preview_with_label(
                fill_image,
                fill_path,
                fill_label
            )
            previews['fill'] = fill_path

            self.log_info(f"Generated 3 preview images in {output_dir}")

            return Result.success({
                'previews': previews,
                'dimensions': {
                    'psd': [psd_width, psd_height],
                    'aepx': [aepx_width, aepx_height]
                },
                'transform_info': {
                    'fit': fit_info,
                    'fill': fill_info
                }
            })

        except Exception as e:
            self.log_error(f"Preview generation failed: {e}", e)
            return Result.failure(str(e))

    def _create_fit_preview(
        self,
        source_image: Image.Image,
        target_width: int,
        target_height: int
    ) -> tuple[Image.Image, Dict]:
        """
        Create "fit" preview (letterbox/pillarbox)
        Scale image to fit inside target, add bars if needed

        Args:
            source_image: Source PIL Image
            target_width: Target width
            target_height: Target height

        Returns:
            Tuple of (preview image, transform info dict)
        """
        src_w, src_h = source_image.size

        # Calculate scale to fit
        scale = min(target_width / src_w, target_height / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)

        # Resize image
        resized = source_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Create canvas with black bars
        canvas = Image.new('RGB', (target_width, target_height), (0, 0, 0))

        # Center image on canvas
        offset_x = (target_width - new_w) // 2
        offset_y = (target_height - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))

        # Determine bar type
        bars = None
        if abs(new_w - target_width) > 1:
            bars = "vertical"  # Pillarbox
        elif abs(new_h - target_height) > 1:
            bars = "horizontal"  # Letterbox

        transform_info = {
            'scale': scale,
            'scaled_width': new_w,
            'scaled_height': new_h,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'bars': bars,
            'method': 'fit'
        }

        return canvas, transform_info

    def _create_fill_preview(
        self,
        source_image: Image.Image,
        target_width: int,
        target_height: int
    ) -> tuple[Image.Image, Dict]:
        """
        Create "fill" preview (crop edges)
        Scale image to fill entire target, crop overflow

        Args:
            source_image: Source PIL Image
            target_width: Target width
            target_height: Target height

        Returns:
            Tuple of (preview image, transform info dict)
        """
        src_w, src_h = source_image.size

        # Calculate scale to fill
        scale = max(target_width / src_w, target_height / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)

        # Resize image
        resized = source_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Calculate crop box (center crop)
        left = (new_w - target_width) // 2
        top = (new_h - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # Crop to target size
        cropped = resized.crop((left, top, right, bottom))

        transform_info = {
            'scale': scale,
            'scaled_width': new_w,
            'scaled_height': new_h,
            'crop_left': left,
            'crop_top': top,
            'crop_right': right,
            'crop_bottom': bottom,
            'method': 'fill'
        }

        return cropped, transform_info

    def _save_preview_with_label(
        self,
        image: Image.Image,
        output_path: str,
        label: str
    ):
        """
        Save preview image with dimension label overlay

        Args:
            image: PIL Image to save
            output_path: Path to save to
            label: Label text to overlay
        """
        # Create copy to draw on
        preview = image.copy()
        draw = ImageDraw.Draw(preview)

        # Add label at top
        try:
            # Try to use a nice font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            try:
                # Try another common font
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            except:
                # Fallback to default
                font = ImageFont.load_default()

        # Draw label with background
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Background rectangle
        padding = 10
        draw.rectangle(
            [(0, 0), (text_width + padding * 2, text_height + padding * 2)],
            fill=(0, 0, 0)
        )

        # Draw text
        draw.text((padding, padding), label, fill=(255, 255, 255), font=font)

        # Save with high quality
        preview.save(output_path, 'JPEG', quality=90)
        self.log_info(f"Saved preview: {output_path}")

    def generate_thumbnail(
        self,
        preview_path: str,
        output_path: str,
        max_size: int = 400
    ) -> Result:
        """
        Generate small thumbnail from preview for UI display

        Args:
            preview_path: Path to full preview image
            output_path: Path to save thumbnail
            max_size: Maximum dimension in pixels

        Returns Result with thumbnail path and dimensions
        """
        try:
            self.log_info(f"Generating thumbnail for {preview_path}")

            # Load preview
            image = Image.open(preview_path)
            width, height = image.size

            # Calculate thumbnail size (maintain aspect ratio)
            if width > height:
                new_width = min(width, max_size)
                new_height = int(height * (new_width / width))
            else:
                new_height = min(height, max_size)
                new_width = int(width * (new_height / height))

            # Resize
            thumbnail = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save
            thumbnail.save(output_path, 'JPEG', quality=85)

            self.log_info(f"Saved thumbnail: {output_path} ({new_width}×{new_height})")

            return Result.success({
                'thumbnail_path': output_path,
                'dimensions': [new_width, new_height]
            })

        except Exception as e:
            self.log_error(f"Thumbnail generation failed: {e}", e)
            return Result.failure(str(e))

    def generate_side_by_side_comparison(
        self,
        original_path: str,
        fit_path: str,
        fill_path: str,
        output_path: str
    ) -> Result:
        """
        Generate side-by-side comparison image of all three options

        Args:
            original_path: Path to original preview
            fit_path: Path to fit preview
            fill_path: Path to fill preview
            output_path: Path to save comparison image

        Returns Result with comparison image path
        """
        try:
            self.log_info("Generating side-by-side comparison")

            # Load all three images
            original = Image.open(original_path)
            fit = Image.open(fit_path)
            fill = Image.open(fill_path)

            # Get dimensions (should all be same height)
            width = original.width
            height = original.height

            # Create canvas for 3 images side by side with spacing
            spacing = 20
            total_width = width * 3 + spacing * 4
            total_height = height + spacing * 2

            canvas = Image.new('RGB', (total_width, total_height), (255, 255, 255))

            # Paste images
            canvas.paste(original, (spacing, spacing))
            canvas.paste(fit, (spacing * 2 + width, spacing))
            canvas.paste(fill, (spacing * 3 + width * 2, spacing))

            # Add labels
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            except:
                font = ImageFont.load_default()

            labels = ["Original", "Fit (Letterbox)", "Fill (Crop)"]
            positions = [
                spacing + width // 2,
                spacing * 2 + width + width // 2,
                spacing * 3 + width * 2 + width // 2
            ]

            for label, x_pos in zip(labels, positions):
                text_bbox = draw.textbbox((0, 0), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                draw.text(
                    (x_pos - text_width // 2, spacing // 2 - 10),
                    label,
                    fill=(0, 0, 0),
                    font=font
                )

            # Save comparison
            canvas.save(output_path, 'JPEG', quality=90)

            self.log_info(f"Saved comparison: {output_path}")

            return Result.success({
                'comparison_path': output_path,
                'dimensions': [total_width, total_height]
            })

        except Exception as e:
            self.log_error(f"Comparison generation failed: {e}", e)
            return Result.failure(str(e))
