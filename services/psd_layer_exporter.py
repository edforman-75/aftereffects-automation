"""
PSD Layer Exporter Service

Extracts all layers from a PSD file and exports them as individual PNG files.
HEADLESS - No Photoshop required, pure Python processing using psd-tools.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from psd_tools import PSDImage
from PIL import Image


class PSDLayerExporter:
    """Service for exporting PSD layers as individual image files."""

    def __init__(self, logger=None):
        self.logger = logger

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)
        else:
            print(f"ℹ️  {message}")

    def log_error(self, message: str):
        """Log error message."""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"❌ {message}")


    def _convert_psd_version(self, psd_path: str) -> str:
        """
        Convert PSD to version 7 if needed using ImageMagick.
        
        Args:
            psd_path: Path to original PSD file
            
        Returns:
            Path to converted PSD (or original if conversion not needed)
        """
        import subprocess
        import tempfile
        from pathlib import Path
        
        # Create a temporary converted file
        temp_dir = Path(tempfile.gettempdir()) / "psd_conversions"
        temp_dir.mkdir(exist_ok=True)
        
        converted_path = temp_dir / f"converted_{Path(psd_path).name}"
        
        try:
            # Use ImageMagick to convert PSD
            # This will normalize it to a version psd-tools can read
            subprocess.run(
                ['convert', psd_path, '-define', 'psd:preserve-layers=true', str(converted_path)],
                check=True,
                capture_output=True,
                timeout=30
            )
            print(f"  ✅ Converted PSD to compatible version: {converted_path.name}")
            return str(converted_path)
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  ImageMagick conversion failed, using original: {e}")
            return psd_path
        except FileNotFoundError:
            print(f"  ⚠️  ImageMagick not found, using original PSD")
            return psd_path
        except Exception as e:
            print(f"  ⚠️  Conversion error: {e}, using original")
            return psd_path


    def extract_all_layers(self, psd_path: str, output_dir: str,
                          include_groups: bool = False,
                          generate_thumbnails: bool = True) -> Dict[str, Any]:
        """
        Extract all layers from PSD and save as individual PNG files.
        HEADLESS - No Photoshop UI appears, pure Python processing.

        Args:
            psd_path: Path to uploaded PSD file
            output_dir: Directory to save exported layer PNGs
            include_groups: Whether to export group layers (default: False)
            generate_thumbnails: Whether to generate thumbnails (default: True)

        Returns:
            Dictionary with comprehensive processing results:
            {
                'layers': {
                    'Background': {
                        'path': '/path/to/exports/background.png',
                        'thumbnail_path': '/path/to/thumbnails/thumb_background.png',
                        'size': (1200, 1500),
                        'file_size_bytes': 2345678,
                        'type': 'pixel',
                        'bounds': (x, y, width, height)
                    },
                    ...
                },
                'metadata': [...],  # List of all layers with info
                'flattened_preview': '/path/to/psd_flat.png',
                'dimensions': {'width': 1200, 'height': 1500}
            }
        """
        try:
            # Create output directories
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            thumbnails_dir = Path(output_dir) / "thumbnails"
            if generate_thumbnails:
                thumbnails_dir.mkdir(parents=True, exist_ok=True)

            # Open PSD (pure Python, no Photoshop required!)
            # Open PSD with version check and auto-conversion
            try:
                psd = PSDImage.open(psd_path)
            except AssertionError as e:
                if "Invalid version" in str(e):
                    version_match = str(e).split("version ")[-1] if "version" in str(e) else "unknown"
                    print(f"  ⚠️  Detected PSD version {version_match} (unsupported by psd-tools)")
                    print(f"  🔄 Attempting conversion with ImageMagick...")
                    
                    # Try to convert the PSD to a compatible version
                    converted_path = self._convert_psd_version(psd_path)
                    if converted_path != psd_path:
                        # Try opening the converted file
                        try:
                            psd = PSDImage.open(converted_path)
                            print(f"  ✅ Successfully opened converted PSD")
                            # Update psd_path for the rest of the function
                            psd_path = converted_path
                        except Exception as conv_error:
                            self.log_error(f"Conversion failed: {conv_error}")
                            return {
                                "error": "unsupported_version",
                                "message": f"PSD version {version_match} could not be converted.",
                                "layers": {},
                                "metadata": []
                            }
                    else:
                        self.log_error(f"Unsupported PSD version {version_match}. psd-tools supports versions 1-7 only.")
                        return {
                            "error": "unsupported_version",
                            "message": f"PSD version {version_match} is not supported.",
                            "layers": {},
                            "metadata": []
                        }
                else:
                    raise

            # Beautiful header
            print(f"\n{'='*70}")
            print(f"🔄 HEADLESS PSD PROCESSING")
            print(f"{'='*70}")
            print(f"File: {Path(psd_path).name}")
            print(f"Mode: psd-tools (Python)")
            print(f"Dimensions: {psd.width}x{psd.height}")
            print(f"Photoshop UI: Never appears ✨")
            print(f"{'='*70}\n")

            print("Processing layers...\n")

            exported_layers = {}
            metadata = []
            layer_count = 0
            fonts_detected = []  # Track all fonts

            # Process all layers
            for layer in psd:
                layer_count += 1
                result = self._process_layer(
                    layer, output_dir, include_groups,
                    generate_thumbnails, thumbnails_dir, layer_count
                )

                if result:
                    exported_layers[layer.name] = result
                    metadata.append(result)

                    # Track fonts from text layers
                    if result.get('type') == 'text' and result.get('font_info'):
                        font_info = result['font_info'].copy()
                        font_info['layer_name'] = layer.name
                        font_info['is_installed'] = self._check_font_installed(result['font_info'])
                        fonts_detected.append(font_info)

            # Generate flattened preview
            print("\nCreating flattened preview...")
            flattened_path = str(Path(output_dir) / "psd_flat.png")
            composite = psd.composite()
            composite.save(flattened_path, 'PNG')
            flat_size = os.path.getsize(flattened_path) / 1024
            print(f"✅ Flattened preview: psd_flat.png ({flat_size:.1f} KB)\n")

            # Generate font report if fonts were detected
            if fonts_detected:
                self._print_font_report(fonts_detected)

            # Summary
            print(f"{'='*70}")
            print(f"✅ HEADLESS PROCESSING COMPLETE")
            print(f"{'='*70}")
            print(f"  - Layers parsed: {layer_count}")
            image_layers = len([l for l in exported_layers.values() if l.get('type') == 'pixel'])
            text_layers = len([l for l in exported_layers.values() if l.get('type') == 'text'])
            print(f"  - Image layers exported: {image_layers}")
            if generate_thumbnails:
                print(f"  - Thumbnails created: {len([l for l in exported_layers.values() if l.get('thumbnail_path')])}")
            if text_layers > 0:
                print(f"  - Text layers analyzed: {text_layers}")
            if fonts_detected:
                missing_count = len([f for f in fonts_detected if not f['is_installed']])
                print(f"  - Fonts detected: {len(fonts_detected)} ({missing_count} missing)")
            print(f"  - Flattened preview: psd_flat.png")
            print(f"  - Photoshop UI: Never appeared ✨")
            print(f"{'='*70}\n")

            return {
                'layers': exported_layers,
                'metadata': metadata,
                'flattened_preview': flattened_path,
                'dimensions': {
                    'width': psd.width,
                    'height': psd.height
                },
                'fonts': fonts_detected
            }

        except Exception as e:
            self.log_error(f"Failed to extract layers: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _process_layer(self, layer, output_dir: str, include_groups: bool,
                      generate_thumbnails: bool, thumbnails_dir: Path, layer_num: int) -> Optional[Dict]:
        """
        Process a single layer and export if applicable.

        Returns:
            Dict with layer info, or None if layer was skipped
        """
        try:
            layer_name = layer.name
            print(f"├── [{layer_num}] {layer_name}")

            # Skip groups unless explicitly requested
            if layer.is_group():
                print(f"│   ℹ️  Group layer - skipped")
                print("│")
                return None

            # Handle text layers - extract font information
            if layer.kind == 'type':
                print(f"│   ℹ️  Text layer")

                # Extract font information
                font_info = self._extract_font_info(layer)

                if font_info:
                    print(f"│   📝 Font: {font_info['family']} {font_info['style']}")

                    # Check if font is installed
                    is_installed = self._check_font_installed(font_info)
                    if is_installed:
                        print(f"│   ✅ Font installed on system")
                    else:
                        print(f"│   ⚠️  Font NOT FOUND on system")

                print("│")
                return {
                    'name': layer_name,
                    'type': 'text',
                    'text_content': layer.text if hasattr(layer, 'text') else '',
                    'font_info': font_info,
                    'visible': layer.visible,
                    'bounds': layer.bbox if hasattr(layer, 'bbox') else None
                }

            # Export pixel/image layers
            if layer.kind in ['pixel', 'shape', 'smartobject', 'normal']:
                result = self._export_layer_as_png(layer, output_dir, generate_thumbnails, thumbnails_dir)
                print("│")
                return result

            # Other layer types
            print(f"│   ⚠️  Unsupported type: {layer.kind}")
            print("│")
            return None

        except Exception as e:
            print(f"│   ❌ Error: {e}")
            print("│")
            return None

    def _export_layer_as_png(self, layer, output_dir: str,
                            generate_thumbnails: bool, thumbnails_dir: Path) -> Optional[Dict]:
        """
        Export a layer as a PNG file with optional thumbnail.

        Returns:
            Dict with exported file info including thumbnail path
        """
        try:
            layer_name = layer.name

            # Convert layer to PIL Image (pure Python, no Photoshop!)
            layer_image = layer.topil()

            if not layer_image:
                print(f"│   ⚠️  Could not convert to image")
                return None

            # Get dimensions
            width, height = layer_image.size

            # Create safe filename
            safe_name = self._make_safe_filename(layer_name)
            output_path = os.path.join(output_dir, f"{safe_name}.png")

            # Save as PNG
            layer_image.save(output_path, 'PNG')

            # Get file size
            file_size = os.path.getsize(output_path)
            size_kb = file_size / 1024

            print(f"│   ✅ Exported: {safe_name}.png ({size_kb:.1f} KB)")

            result = {
                'name': layer_name,
                'type': 'pixel',
                'path': output_path,
                'size': (width, height),
                'file_size_bytes': file_size,
                'visible': layer.visible,
                'kind': layer.kind,
                'bounds': layer.bbox if hasattr(layer, 'bbox') else None
            }

            # Generate thumbnail if requested
            if generate_thumbnails:
                thumb_path = self._generate_thumbnail(layer_image, thumbnails_dir, safe_name)
                if thumb_path:
                    result['thumbnail_path'] = str(thumb_path)
                    print(f"│   ✅ Thumbnail: thumb_{safe_name}.png")

            return result

        except Exception as e:
            print(f"│   ❌ Export failed: {e}")
            return None

    def _generate_thumbnail(self, pil_image, output_dir: Path, base_name: str,
                           max_size: int = 200) -> Optional[Path]:
        """
        Generate thumbnail from PIL Image.

        Args:
            pil_image: PIL Image object
            output_dir: Directory to save thumbnail
            base_name: Base filename (without extension)
            max_size: Maximum thumbnail dimension (default: 200px)

        Returns:
            Path to thumbnail file, or None if failed
        """
        try:
            # Create copy for thumbnail
            thumb_img = pil_image.copy()

            # Resize to fit in max_size x max_size
            thumb_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Create square canvas with transparent background
            thumb = Image.new('RGBA', (max_size, max_size), (0, 0, 0, 0))

            # Center the resized image
            offset = ((max_size - thumb_img.width) // 2, (max_size - thumb_img.height) // 2)
            thumb.paste(thumb_img, offset)

            # Save thumbnail
            thumb_path = output_dir / f"thumb_{base_name}.png"
            thumb.save(thumb_path, 'PNG')

            return thumb_path

        except Exception as e:
            print(f"│   ⚠️  Thumbnail generation failed: {e}")
            return None

    def _extract_font_info(self, layer) -> Optional[Dict]:
        """
        Extract font information from text layer.

        Returns:
            Dict with font family, style, and PostScript name
        """
        try:
            # Get text data from layer
            if not hasattr(layer, 'text_data'):
                return None

            text_data = layer.text_data

            # Try to get font information
            font_info = {
                'family': 'Unknown',
                'style': 'Regular',
                'postscript_name': None
            }

            # Extract from text data
            if hasattr(text_data, 'font'):
                font_info['postscript_name'] = text_data.font
                # Parse PostScript name to get family and style
                parts = text_data.font.split('-')
                if len(parts) >= 2:
                    font_info['family'] = parts[0]
                    font_info['style'] = parts[1]
                elif len(parts) == 1:
                    font_info['family'] = parts[0]

            # Try alternative attributes
            if hasattr(text_data, 'font_name'):
                font_info['family'] = text_data.font_name

            if hasattr(text_data, 'font_style'):
                font_info['style'] = text_data.font_style

            return font_info

        except Exception as e:
            return None

    def _print_font_report(self, fonts: List[Dict]):
        """
        Print a beautiful font detection report.

        Args:
            fonts: List of font info dicts with is_installed status
        """
        print(f"{'='*70}")
        print(f"🆎 FONT DETECTION REPORT")
        print(f"{'='*70}\n")

        # Categorize fonts
        installed = [f for f in fonts if f['is_installed']]
        missing = [f for f in fonts if not f['is_installed']]

        # Detect custom vs common fonts
        common_fonts = ['Helvetica', 'Arial', 'Times', 'Courier', 'Georgia', 'Verdana']
        custom_installed = [f for f in installed if not any(cf in f['family'] for cf in common_fonts)]
        common_installed = [f for f in installed if any(cf in f['family'] for cf in common_fonts)]

        # Show custom fonts (installed)
        if custom_installed:
            print("✅ Custom Fonts (installed):")
            for font in custom_installed:
                print(f"   - {font['family']} {font['style']}")
            print()

        # Show common fonts (installed)
        if common_installed:
            print("✅ Common Fonts (installed):")
            for font in common_installed:
                print(f"   - {font['family']} {font['style']}")
            print()

        # Show missing fonts with WARNING
        if missing:
            print("⚠️  MISSING FONTS (not installed):")
            for font in missing:
                print(f"   ❌ {font['family']} {font['style']}")
                if font.get('postscript_name'):
                    print(f"      PostScript: {font['postscript_name']}")
            print()
            print("⚠️  ACTION REQUIRED: Install missing fonts before rendering\n")

        # Summary
        print("Summary:")
        print(f"  - Total fonts detected: {len(fonts)}")
        print(f"  - Installed: {len(installed)}")
        print(f"  - Missing: {len(missing)}")
        if missing:
            print(f"  - ⚠️  Warning: Some fonts are missing!")
        else:
            print(f"  - ✅ All fonts available!")

        print(f"\n{'='*70}\n")

    def _check_font_installed(self, font_info: Dict) -> bool:
        """
        Check if font is installed on the system.

        Args:
            font_info: Dict with font family and style

        Returns:
            True if font is installed, False otherwise
        """
        try:
            import subprocess

            # Get PostScript name or construct it
            ps_name = font_info.get('postscript_name')
            if not ps_name:
                # Construct from family and style
                family = font_info.get('family', '')
                style = font_info.get('style', '')
                ps_name = f"{family}-{style}" if style else family

            # Use system font check (macOS)
            result = subprocess.run(
                ['system_profiler', 'SPFontsDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Check if font name appears in output
            if ps_name.lower() in result.stdout.lower():
                return True

            # Also check family name
            family = font_info.get('family', '')
            if family and family.lower() in result.stdout.lower():
                return True

            return False

        except Exception:
            # If check fails, assume not installed
            return False

    def _make_safe_filename(self, layer_name: str) -> str:
        """
        Convert layer name to safe filename.

        Examples:
            'Background' → 'background'
            'Cutout Layer!' → 'cutout_layer'
            'Green/Yellow BG' → 'green_yellow_bg'
        """
        # Convert to lowercase
        safe = layer_name.lower()

        # Replace spaces and special chars with underscores
        safe = ''.join(c if c.isalnum() else '_' for c in safe)

        # Remove multiple consecutive underscores
        while '__' in safe:
            safe = safe.replace('__', '_')

        # Remove leading/trailing underscores
        safe = safe.strip('_')

        return safe

    def get_export_summary(self, exported_layers: Dict[str, Dict]) -> str:
        """
        Generate a human-readable summary of exported layers.

        Returns:
            Multi-line string summarizing the exports
        """
        lines = ["\n" + "="*70]
        lines.append("PSD LAYER EXPORT SUMMARY")
        lines.append("="*70)

        text_layers = []
        image_layers = []

        for layer_name, info in exported_layers.items():
            if info['type'] == 'text':
                text_layers.append(layer_name)
            elif info['type'] == 'pixel':
                image_layers.append({
                    'name': layer_name,
                    'path': info['path'],
                    'size': info['size'],
                    'file_size_mb': info['file_size_bytes'] / (1024 * 1024)
                })

        if image_layers:
            lines.append(f"\n📁 Exported {len(image_layers)} Image Layers:")
            for layer in image_layers:
                lines.append(f"  ✓ {layer['name']}")
                lines.append(f"    → {layer['path']}")
                lines.append(f"    → {layer['size'][0]}x{layer['size'][1]}, {layer['file_size_mb']:.2f} MB")

        if text_layers:
            lines.append(f"\n📝 Detected {len(text_layers)} Text Layers (editable):")
            for layer_name in text_layers:
                lines.append(f"  ✓ {layer_name}")

        lines.append("\n" + "="*70)

        return "\n".join(lines)
