"""
Module 5.1: Video Preview Generator

Generate low-resolution video previews using After Effects command-line rendering.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Default aerender paths for different platforms
AERENDER_PATHS = {
    'darwin': '/Applications/Adobe After Effects 2025/aerender',
    'darwin_2024': '/Applications/Adobe After Effects 2024/aerender',
    'win32': 'C:\\Program Files\\Adobe\\Adobe After Effects 2025\\Support Files\\aerender.exe',
}

DEFAULT_OPTIONS = {
    'resolution': 'half',    # half, third, quarter
    'duration': 5.0,         # seconds (or 'full')
    'format': 'mp4',         # mp4, mov, gif
    'quality': 'draft',      # draft, medium, high
    'fps': 15                # frames per second
}


def make_ae_compatible_png(png_path: str, temp_dir: str) -> str:
    """
    Convert PNG to After Effects compatible format.

    After Effects PNGIO plugin can be picky about PNG formats.
    This re-saves PNGs with basic settings that AE can reliably import.

    Args:
        png_path: Path to PNG file
        temp_dir: Temp directory for output

    Returns:
        Path to converted PNG file
    """
    if not PIL_AVAILABLE:
        # PIL not available, return original path
        return png_path

    try:
        # Open the PNG
        img = Image.open(png_path)

        # Convert to RGBA if not already (ensures consistent format)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Create output path in temp directory
        png_filename = Path(png_path).name
        output_filename = png_filename.replace('.png', '_ae.png')
        output_path = Path(temp_dir) / output_filename

        # Save with basic PNG settings (no optimization, no interlacing)
        # compress_level=6 is a good balance (default is 9)
        # optimize=False avoids extra processing that can cause issues
        img.save(output_path, 'PNG', compress_level=6, optimize=False)

        return str(output_path)

    except Exception as e:
        # If conversion fails, return original path
        print(f"  ⚠️  PNG conversion failed for {Path(png_path).name}: {str(e)}")
        print(f"  (Using original file)")
        return png_path


def check_aerender_available() -> Optional[str]:
    """
    Check if aerender is available on the system.

    Returns:
        Path to aerender if found, None otherwise
    """
    import platform
    system = platform.system().lower()

    # Check common paths
    if system == 'darwin':
        for key in ['darwin', 'darwin_2024']:
            path = AERENDER_PATHS.get(key)
            if path and os.path.exists(path):
                return path
    elif system == 'windows':
        path = AERENDER_PATHS.get('win32')
        if path and os.path.exists(path):
            return path

    # Try finding in PATH
    try:
        result = subprocess.run(['which', 'aerender'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return None


def generate_preview(aepx_path: str, mappings: Dict[str, Any],
                     output_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate video preview of populated After Effects template.

    Args:
        aepx_path: Path to AEPX/AEP template file
        mappings: Content mappings from Module 3
        output_path: Path for output video
        options: Optional rendering options

    Returns:
        Dictionary with preview info (video_path, thumbnail_path, duration, etc.)
    """
    # Merge options with defaults
    opts = DEFAULT_OPTIONS.copy()
    if options:
        opts.update(options)

    print(f"\n{'='*70}")
    print(f"PREVIEW GENERATION STARTING")
    print(f"{'='*70}")
    print(f"AEPX Path: {aepx_path}")
    print(f"Output Path: {output_path}")
    print(f"Options: {opts}")
    print(f"{'='*70}\n")

    # Check aerender availability
    print("Step 1: Checking aerender availability...")
    aerender_path = check_aerender_available()
    if not aerender_path:
        print("❌ aerender not found\n")
        return {
            'success': False,
            'error': 'aerender not found. After Effects must be installed.',
            'video_path': None,
            'thumbnail_path': None
        }
    print(f"✅ aerender found at: {aerender_path}\n")

    # Create temp directory for project preparation
    temp_dir = tempfile.mkdtemp(prefix='ae_preview_')
    print(f"Step 2: Created temp directory: {temp_dir}\n")

    try:
        # Prepare temporary project with mappings
        print("Step 3: Preparing temporary project...")
        temp_project = prepare_temp_project(aepx_path, mappings, temp_dir)
        print(f"✅ Temp project prepared: {temp_project}\n")

        # Determine composition name
        comp_name = mappings.get('composition_name', 'Main Comp')
        print(f"Step 4: Using composition: '{comp_name}'")

        # Verify composition exists in both original and temp project
        print(f"\nStep 4.5: Verifying composition exists...")
        print(f"{'='*70}")

        # Check original file first
        try:
            print(f"  Checking original AEPX file: {aepx_path}")
            original_comps = extract_composition_names(aepx_path)
            print(f"  Original file compositions: {original_comps}")
        except Exception as e:
            print(f"  ⚠️  Error extracting from original: {e}")
            original_comps = []

        # Check temp file
        try:
            print(f"  Checking temp project file: {temp_project}")
            available_comps = extract_composition_names(temp_project)
            print(f"  Temp file compositions: {available_comps}")
        except Exception as e:
            print(f"  ⚠️  Error extracting from temp: {e}")
            available_comps = []

        # If temp file has no compositions but original does, this is a problem
        if not available_comps and original_comps:
            print(f"\n❌ ERROR: Temp project has no compositions!")
            print(f"  Original file had: {original_comps}")
            print(f"  This suggests the temp file copy may be corrupted")
            print(f"  Trying to use original file instead...")
            temp_project = aepx_path
            available_comps = original_comps

        # Use original comps as fallback if temp has none
        if not available_comps:
            available_comps = original_comps

        if comp_name not in available_comps:
            print(f"\n⚠️  WARNING: Composition '{comp_name}' not found!")
            print(f"  Requested: '{comp_name}'")
            print(f"  Available: {available_comps}")

            if available_comps:
                # Try to find a close match (case-insensitive)
                comp_lower = comp_name.lower()
                for available in available_comps:
                    if available.lower() == comp_lower:
                        print(f"  ✓ Found case-insensitive match: '{available}'")
                        comp_name = available
                        break
                else:
                    # No match found, use first available
                    print(f"  ℹ️  Using first available composition: '{available_comps[0]}'")
                    comp_name = available_comps[0]
            else:
                print(f"  ❌ No compositions found in project - rendering will likely fail")
        else:
            print(f"  ✓ Composition '{comp_name}' verified")

        print(f"{'='*70}")
        print(f"✅ Composition verification complete: '{comp_name}'")
        print(f"{'='*70}\n")

        # Render preview
        print("Step 5: Rendering with aerender...")
        success = render_with_aerender(
            temp_project,
            comp_name,
            output_path,
            opts,
            aerender_path
        )

        if not success:
            print("❌ Rendering failed - see aerender output above\n")
            return {
                'success': False,
                'error': 'Rendering failed - check aerender output above for details',
                'video_path': None,
                'thumbnail_path': None
            }

        # Generate thumbnail
        print("Step 6: Generating thumbnail...")
        thumbnail_path = generate_thumbnail(output_path, timestamp=0.5)
        if thumbnail_path:
            print(f"✅ Thumbnail generated: {thumbnail_path}\n")
        else:
            print("⚠️  Thumbnail generation skipped (ffmpeg not available)\n")

        # Get video info
        print("Step 7: Extracting video metadata...")
        video_info = get_video_info(output_path)
        print(f"✅ Video info: {video_info}\n")

        print(f"{'='*70}")
        print(f"✅ PREVIEW GENERATION COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"Video: {output_path}")
        print(f"Thumbnail: {thumbnail_path or 'N/A'}")
        print(f"Duration: {video_info.get('duration', opts['duration'])} seconds")
        print(f"Resolution: {video_info.get('resolution', 'unknown')}")
        print(f"{'='*70}\n")

        return {
            'success': True,
            'video_path': output_path,
            'thumbnail_path': thumbnail_path,
            'duration': video_info.get('duration', opts['duration']),
            'resolution': video_info.get('resolution', 'unknown'),
            'format': opts['format']
        }

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ PREVIEW GENERATION EXCEPTION")
        print(f"{'='*70}")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n")
        return {
            'success': False,
            'error': f'Preview generation failed: {str(e)}',
            'video_path': None,
            'thumbnail_path': None
        }

    finally:
        # Cleanup temp directory (TEMPORARILY DISABLED FOR DEBUGGING)
        print(f"Step 8: NOT cleaning up temp directory for inspection: {temp_dir}")
        print(f"⚠️  Manually inspect: {temp_dir}")
        print(f"⚠️  To re-enable cleanup, uncomment shutil.rmtree() in preview_generator.py\n")
        # try:
        #     shutil.rmtree(temp_dir)
        #     print(f"✅ Temp directory cleaned up\n")
        # except Exception as e:
        #     print(f"⚠️  Failed to cleanup temp directory: {str(e)}\n")


def extract_composition_names(aepx_path: str) -> list:
    """
    Extract composition names from AEPX file.

    Args:
        aepx_path: Path to AEPX file

    Returns:
        List of composition names found in project
    """
    composition_names = []

    # Verify file exists
    if not os.path.exists(aepx_path):
        print(f"    ⚠️  File does not exist: {aepx_path}")
        return []

    file_size = os.path.getsize(aepx_path)
    print(f"    File size: {file_size:,} bytes")

    try:
        import xml.etree.ElementTree as ET

        print(f"    Parsing as XML...")
        # Parse AEPX as XML
        tree = ET.parse(aepx_path)
        root = tree.getroot()
        print(f"    Root tag: {root.tag}")

        # Search for composition elements
        # AEPX format uses various tags, try common ones
        for comp in root.iter():
            # Check for composition name in various possible locations
            if comp.tag in ['Composition', 'Item']:
                # Look for name attribute or child element
                name = comp.get('name') or comp.get('Name')
                if name and name not in composition_names:
                    composition_names.append(name)
                    print(f"    Found (attr): '{name}'")

                # Also check for Name child element
                name_elem = comp.find('Name') or comp.find('name')
                if name_elem is not None and name_elem.text:
                    if name_elem.text not in composition_names:
                        composition_names.append(name_elem.text)
                        print(f"    Found (elem): '{name_elem.text}'")

        print(f"    XML parsing found {len(composition_names)} composition(s)")

        # If no compositions found via XML parsing, try regex search
        if not composition_names:
            print(f"    Trying regex fallback...")
            with open(aepx_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import re
            # Look for composition-like patterns
            patterns = [
                r'<Composition[^>]+name="([^"]+)"',
                r'<Item[^>]+name="([^"]+)"[^>]+type="composition"',
                r'name="([^"]+)"[^>]*>\s*<Composition',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match and match not in composition_names:
                        composition_names.append(match)
                        print(f"    Found (regex): '{match}'")

            print(f"    Regex found {len(composition_names)} composition(s)")

        return composition_names

    except Exception as e:
        print(f"    ❌ Error extracting compositions: {e}")
        import traceback
        traceback.print_exc()
        return []


def search_for_footage_by_filename(filename: str) -> str | None:
    """
    Search for footage file by filename across multiple directories.

    Args:
        filename: Name of the file to find (e.g., "green_yellow_bg.png")

    Returns:
        Absolute path to found file, or None if not found
    """
    # Search locations
    search_dirs = [
        'uploads',
        'footage',
        'sample_files',
        'sample_files/footage',
        'assets',
        'media',
        'static/uploads',
    ]

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue

        # Search in directory and all subdirectories
        for root, dirs, files in os.walk(search_dir):
            if filename in files:
                found_path = os.path.join(root, filename)
                return os.path.abspath(found_path)

    return None


def create_placeholder_image(output_path: str, width: int = 1920, height: int = 1080) -> bool:
    """
    Create a placeholder image for missing footage.

    Args:
        output_path: Where to save placeholder image
        width: Image width
        height: Image height

    Returns:
        True if created successfully
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create solid color image
        img = Image.new('RGB', (width, height), color='#333333')
        draw = ImageDraw.Draw(img)

        # Add text
        filename = os.path.basename(output_path)
        text = f"MISSING FOOTAGE\n{filename}"

        # Draw text in center
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) / 2, (height - text_height) / 2)

        draw.text(position, text, fill='#999999')

        # Save
        img.save(output_path)
        return True

    except Exception as e:
        print(f"    ⚠️  Could not create placeholder: {e}")
        return False


def prepare_temp_project(aepx_path: str, mappings: Dict[str, Any], temp_dir: str) -> str:
    """
    Prepare temporary project file with content mappings.

    Args:
        aepx_path: Path to original AEPX file
        mappings: Content mappings
        temp_dir: Temporary directory

    Returns:
        Path to prepared project file
    """
    # Copy AEPX to temp location
    project_name = Path(aepx_path).name
    temp_project = os.path.join(temp_dir, project_name)
    shutil.copy2(aepx_path, temp_project)

    # Copy footage files to temp directory
    print("Step 3.5: Copying footage files to temp directory...")
    try:
        from modules.phase2.aepx_path_fixer import find_footage_references

        # Get image sources from options (exported PSD layers)
        image_sources = mappings.get('image_sources', {}) if 'image_sources' in mappings else {}

        # Find all footage references
        footage_refs = find_footage_references(aepx_path)

        # Get original AEPX directory
        original_dir = os.path.dirname(os.path.abspath(aepx_path))

        copied_count = 0
        not_found = []
        path_mapping = {}  # Track original path -> new path for AEPX updates

        for ref in footage_refs:
            ref_path = ref['path']
            filename = os.path.basename(ref_path)

            print(f"\n  Looking for: {filename}")

            # Determine if path is absolute or relative
            is_absolute = os.path.isabs(ref_path)

            source_file = None
            search_method = None

            # FIRST: Check if this file is in exported PSD layers (by filename match)
            filename_base = os.path.splitext(filename)[0].lower()  # Remove extension, lowercase
            for layer_name, layer_path in image_sources.items():
                layer_name_safe = layer_name.lower().replace(' ', '_')
                if filename_base == layer_name_safe or filename_base in layer_name_safe:
                    if os.path.exists(layer_path):
                        source_file = Path(layer_path)
                        search_method = "exported PSD layer"
                        print(f"    ✅ Using exported PSD layer: {layer_path}")
                        break

            # If not found in exported layers, continue with regular search
            if not source_file:
                if is_absolute:
                    # For absolute paths, check if exists
                    if os.path.exists(ref_path):
                        source_file = Path(ref_path)
                        search_method = "original path"
                    else:
                        # Absolute path doesn't exist - search by filename
                        print(f"    ❌ Original path not found: {ref_path}")
                        print(f"    🔍 Searching for '{filename}' in project directories...")

                        found_path = search_for_footage_by_filename(filename)
                        if found_path:
                            source_file = Path(found_path)
                            search_method = f"found in {os.path.dirname(found_path)}"
                            print(f"    ✅ Found alternative: {found_path}")
                else:
                    # For relative paths, search multiple locations
                    aepx_dir = Path(original_dir)
                    ref_path_obj = Path(ref_path)

                    # Try multiple search locations
                    search_paths = [
                        aepx_dir / ref_path,                        # Relative to AEPX
                        Path('sample_files') / ref_path,            # In sample_files
                        Path('sample_files') / 'footage' / filename,  # In sample_files/footage/
                        Path('footage') / filename,                 # In root footage/
                        Path('assets') / filename,                  # In root assets/
                        Path('media') / filename,                   # In root media/
                    ]

                    # Find first existing file
                    for search_path in search_paths:
                        if search_path.exists():
                            source_file = search_path
                            search_method = f"found in {search_path.parent}"
                            break

            # Copy if source found, or create placeholder
            dest_file = Path(temp_dir) / filename  # Always use just filename in temp

            if source_file and source_file.exists():
                # Create destination directory if needed
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(str(source_file), str(dest_file))
                print(f"    ✅ Copied to temp directory ({search_method})")

                # Track mapping for AEPX update
                path_mapping[ref_path] = str(dest_file)
                copied_count += 1
            else:
                # File not found anywhere - create placeholder
                print(f"    ⚠️  Not found anywhere - creating placeholder")

                # Create destination directory if needed
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Create placeholder image
                if create_placeholder_image(str(dest_file)):
                    print(f"    ✅ Created placeholder: {dest_file}")
                    path_mapping[ref_path] = str(dest_file)
                else:
                    not_found.append(ref_path)
                    print(f"    ❌ Could not create placeholder")

        # Summary
        if copied_count > 0:
            print(f"✅ Copied {copied_count} footage file(s)")
        if not_found:
            print(f"⚠️  Could not find {len(not_found)} file(s)")
        if copied_count == 0 and not not_found:
            print("  (No footage files referenced)")
        print()

    except Exception as e:
        print(f"⚠️  Warning: Could not copy footage files: {str(e)}\n")

    # Update AEPX to use new footage paths
    print("\nStep 3.6: Updating AEPX footage paths...")
    try:
        # Read AEPX as text for path replacement
        with open(temp_project, 'r', encoding='utf-8') as f:
            aepx_content = f.read()

        updated_count = 0

        # Replace all mapped paths (both absolute and relative)
        for old_path, new_path in path_mapping.items():
            # Replace in AEPX content (escape special regex chars)
            import re
            old_path_escaped = re.escape(old_path)

            # Count matches before replacing
            matches = len(re.findall(old_path_escaped, aepx_content))

            if matches > 0:
                aepx_content = re.sub(old_path_escaped, new_path, aepx_content)
                print(f"  ✓ Updated: {os.path.basename(old_path)} ({matches} reference(s))")
                updated_count += matches

        # Write updated AEPX back
        with open(temp_project, 'w', encoding='utf-8') as f:
            f.write(aepx_content)

        if updated_count > 0:
            print(f"\n✅ Updated {updated_count} footage path(s) in AEPX")
        else:
            print("  (No paths needed updating)")
        print()

    except Exception as e:
        print(f"⚠️  Warning: Could not update AEPX paths: {str(e)}\n")

    # Generate ExtendScript for content population
    script_path = os.path.join(temp_dir, 'populate.jsx')

    # Import extendscript generator
    try:
        from modules.phase4.extendscript_generator import generate_extendscript
        from modules.phase2.aepx_parser import parse_aepx

        # Parse AEPX file
        aepx_data = parse_aepx(aepx_path)

        # Create minimal PSD data from mappings
        # The ExtendScript generator expects text content in PSD layers
        psd_layers = []
        for mapping in mappings.get('mappings', []):
            if mapping.get('type') == 'text':
                # Create a fake PSD layer with the text content from psd_layer
                psd_layers.append({
                    'name': mapping.get('psd_layer', ''),
                    'type': 'text',
                    'text': {
                        'content': mapping.get('psd_layer', ''),  # Use psd_layer as content
                        'font_size': 48,
                        'color': {'r': 255, 'g': 255, 'b': 255}  # White
                    }
                })

        psd_data = {
            'filename': 'preview.psd',
            'width': 1920,
            'height': 1080,
            'layers': psd_layers
        }

        # Build image_sources dict for image layer replacements
        # Map AEPX placeholder layer names to absolute paths of PSD layer preview images
        image_sources = {}
        import glob
        import re

        # Extract session_id from aepx_path
        # Example: "uploads/1761598122_ab371181_aepx_..." -> "1761598122_ab371181"
        session_id = None
        aepx_basename = os.path.basename(aepx_path)

        # Try to extract session_id pattern: timestamp_hash
        match = re.search(r'(\d+_[a-f0-9]+)', aepx_basename)
        if match:
            session_id = match.group(1)

        for mapping in mappings.get('mappings', []):
            if mapping.get('type') == 'image':
                placeholder = mapping.get('aepx_placeholder', '')
                psd_layer_name = mapping.get('psd_layer', '')

                # Sanitize layer name for filename (replace spaces, special chars)
                layer_name_sanitized = re.sub(r'[^\w\-]', '_', psd_layer_name.lower())

                # Look for PSD layer preview file
                # Pattern: previews/psd_layer_{layername}_{sessionid}_{timestamp}.png
                if session_id:
                    preview_pattern = f"previews/psd_layer_{layer_name_sanitized}_{session_id}_*.png"
                else:
                    # Fallback: search without session_id
                    preview_pattern = f"previews/psd_layer_{layer_name_sanitized}_*.png"

                # Find matching preview files (sorted by modification time, most recent first)
                preview_files = sorted(
                    glob.glob(preview_pattern),
                    key=os.path.getmtime,
                    reverse=True
                )

                if preview_files:
                    # Use the most recent preview file
                    preview_file = Path(preview_files[0]).absolute()
                    image_sources[placeholder] = str(preview_file)
                    print(f"  ✓ Found PSD layer preview: {psd_layer_name} -> {os.path.basename(preview_file)}")
                else:
                    # Fallback: try to find in temp directory footage
                    # (for backwards compatibility or if preview not available)
                    from modules.phase2.aepx_path_fixer import find_footage_references
                    footage_refs = find_footage_references(aepx_path)

                    for ref in footage_refs:
                        ref_name = os.path.splitext(os.path.basename(ref['path']))[0]
                        if ref_name.lower() == psd_layer_name.lower():
                            image_file = Path(temp_dir) / ref['path']
                            if image_file.exists():
                                image_sources[placeholder] = str(image_file.absolute())
                                print(f"  ⚠️  Using footage fallback: {psd_layer_name} -> {ref['path']}")
                                break

        # Convert PNG images to AE-compatible format
        if image_sources and PIL_AVAILABLE:
            print("  ✓ Converting PNG images to AE-compatible format...")
            converted_count = 0
            for layer_name, image_path in list(image_sources.items()):
                if image_path.lower().endswith('.png'):
                    converted_path = make_ae_compatible_png(image_path, temp_dir)
                    if converted_path != image_path:  # Conversion successful
                        image_sources[layer_name] = converted_path
                        converted_count += 1

            if converted_count > 0:
                print(f"    ✓ Converted {converted_count} PNG file(s)")

        # Generate script
        generate_extendscript(psd_data, aepx_data, mappings, script_path, {
            'psd_file_path': '',
            'aepx_file_path': temp_project,
            'output_project_path': temp_project,
            'render_output': False,
            'image_sources': image_sources
        })

        # Count replacements
        text_count = len([m for m in mappings.get('mappings', []) if m.get('type') == 'text'])
        image_count = len(image_sources)

        print(f"  ✓ Generated ExtendScript: {os.path.basename(script_path)}")
        if text_count > 0:
            print(f"  ✓ Text replacements: {text_count}")
        if image_count > 0:
            print(f"  ✓ Image replacements: {image_count}")
        if text_count == 0 and image_count == 0:
            print(f"  (No text or image replacements)")

    except Exception as e:
        # If script generation fails, proceed without it
        print(f"  ⚠️  ExtendScript generation failed: {str(e)}")
        print(f"  (Preview will use unpopulated template)")
    print()

    # Step 3.7: Populate template with content using ExtendScript
    print("Step 3.7: Populating template with content...")

    populated_successfully = False

    try:
        if os.path.exists(script_path):
            print(f"  ✓ Generated ExtendScript: {os.path.basename(script_path)}")

            # Run ExtendScript using osascript (AppleScript)
            print("  ✓ Opening project in After Effects...")

            # Convert paths to absolute for AppleScript
            abs_project_path = os.path.abspath(temp_project)
            abs_script_path = os.path.abspath(script_path)

            # Escape paths for AppleScript
            abs_project_path_escaped = abs_project_path.replace('\\', '\\\\').replace('"', '\\"')
            abs_script_path_escaped = abs_script_path.replace('\\', '\\\\').replace('"', '\\"')

            # AppleScript to open project, run script, save, and quit
            # Using 'do script' with file path instead of 'DoScriptFile'
            applescript = f'''
            tell application "Adobe After Effects 2025"
                activate
                delay 1
                open POSIX file "{abs_project_path_escaped}"
                delay 5

                -- Run the ExtendScript
                do script "$.evalFile('{abs_script_path_escaped}');"
                delay 5

                -- Save the project
                save
                delay 2

                -- Quit After Effects
                quit
            end tell
            '''

            print("  ✓ Running population script...")
            print(f"    Project: {abs_project_path}")
            print(f"    Script: {abs_script_path}")

            # Execute AppleScript
            result = subprocess.run(
                ['osascript', '-'],
                input=applescript,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout (increased)
            )

            print(f"  ✓ AppleScript return code: {result.returncode}")
            if result.stdout:
                print(f"    stdout: {result.stdout}")
            if result.stderr:
                print(f"    stderr: {result.stderr}")

            if result.returncode == 0:
                # Wait for AE to fully close and save
                print("  ✓ Waiting for After Effects to close...")
                import time
                time.sleep(3)

                # Verify project was modified (check modification time)
                if os.path.exists(temp_project):
                    mtime = os.path.getmtime(temp_project)
                    import time
                    age_seconds = time.time() - mtime

                    if age_seconds < 120:  # Modified in last 2 minutes
                        print(f"  ✓ Project file updated (age: {age_seconds:.1f}s)")
                        populated_successfully = True
                    else:
                        print(f"  ⚠️  Warning: Project file not recently modified (age: {age_seconds:.1f}s)")
                        print("  (Population may not have succeeded)")

                if populated_successfully:
                    print("✅ Template populated successfully\n")
                else:
                    print("⚠️  Population may have failed - check logs\n")
            else:
                print(f"❌ Script execution failed with return code {result.returncode}")
                if result.stderr:
                    print(f"  Error: {result.stderr}")
                print("  (Will try rendering anyway)\n")

        else:
            print("  ⚠️  No ExtendScript generated - rendering unpopulated template\n")

    except subprocess.TimeoutExpired:
        print("❌ Script execution timed out (>120s)")
        print("  After Effects may still be running")
        print("  (Will try rendering anyway)\n")
    except Exception as e:
        print(f"❌ Population error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("  (Will try rendering anyway)\n")

    # Add a note to the project path about population status
    if not populated_successfully:
        print("⚠️  WARNING: Template may not be populated")
        print("  The preview might show the empty template")
        print("  If this happens frequently, check:")
        print("  - After Effects is installed at the expected path")
        print("  - ExtendScript has no syntax errors")
        print("  - Footage files are accessible\n")

    return temp_project


def render_with_aerender(project_path: str, comp_name: str, output_path: str,
                         options: Dict[str, Any], aerender_path: str) -> bool:
    """
    Render composition using After Effects command-line tool.

    Args:
        project_path: Path to AE project
        comp_name: Composition name to render
        output_path: Output video path
        options: Rendering options
        aerender_path: Path to aerender executable

    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify project file exists
        if not os.path.exists(project_path):
            print(f"❌ Project file not found: {project_path}")
            return False

        project_size = os.path.getsize(project_path)
        print(f"✓ Project file exists: {project_path}")
        print(f"  Size: {project_size:,} bytes")
        print(f"  Composition: {comp_name}")

        # Convert output path to absolute path
        # aerender interprets relative paths relative to AE app directory, not cwd
        abs_output_path = str(Path(output_path).resolve())
        abs_project_path = str(Path(project_path).resolve())

        # Ensure output directory exists
        output_dir = Path(abs_output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Output: {abs_output_path}")

        # Build aerender command
        cmd = [
            aerender_path,
            '-project', abs_project_path,
            '-comp', comp_name,
            '-output', abs_output_path
        ]

        # Add resolution setting
        resolution_map = {
            'full': 1,
            'half': 2,
            'third': 3,
            'quarter': 4
        }
        res_value = resolution_map.get(options.get('resolution', 'half'), 2)
        cmd.extend(['-RStemplate', 'Best Settings'])

        # Note: Removed -OMtemplate parameter
        # After Effects 2025 doesn't have "H.264" template by that name
        # Letting AE use default output module based on file extension (.mp4)
        # The output format will be determined by the file extension in output_path

        # Add duration (if not full)
        duration = options.get('duration')
        if duration and duration != 'full':
            # Calculate end frame
            fps = options.get('fps', 15)
            end_frame = int(duration * fps)
            cmd.extend(['-s', '0', '-e', str(end_frame)])
            print(f"  Duration: {duration}s ({end_frame} frames at {fps} fps)")
        else:
            print(f"  Duration: Full composition")

        # Print the full command for debugging
        cmd_str = ' '.join([f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd])
        print(f"\n{'='*70}")
        print(f"AERENDER COMMAND:")
        print(f"{'='*70}")
        print(f"{cmd_str}")
        print(f"{'='*70}\n")

        print("Starting aerender... (this may take 30-60 seconds)\n")

        # Run aerender
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Print stdout and stderr for debugging
        print(f"\n{'='*70}")
        print(f"aerender stdout:")
        print(f"{'='*70}")
        if result.stdout:
            print(result.stdout)
        else:
            print("(no stdout)")
        print()

        print(f"{'='*70}")
        print(f"aerender stderr:")
        print(f"{'='*70}")
        if result.stderr:
            print(result.stderr)
        else:
            print("(no stderr)")
        print()

        # Check if output file was created
        output_exists = os.path.exists(abs_output_path)
        print(f"{'='*70}")
        print(f"Output file exists: {output_exists}")
        if output_exists:
            file_size = os.path.getsize(abs_output_path)
            print(f"Output file size: {file_size:,} bytes")
        print(f"Output file path: {abs_output_path}")
        print(f"{'='*70}\n")

        # Determine success based on return code AND file existence
        if result.returncode == 0 and output_exists:
            print("✅ aerender completed successfully\n")
            return True
        else:
            print(f"\n{'='*70}")
            print(f"❌ AERENDER FAILED")
            print(f"{'='*70}")

            if result.returncode != 0:
                print(f"Return code: {result.returncode}")

            if not output_exists:
                print(f"Output file was not created: {abs_output_path}")

            # Parse common error messages
            error_text = (result.stdout + result.stderr).lower()

            if 'composition' in error_text and ('not found' in error_text or 'does not exist' in error_text):
                print(f"\n💡 LIKELY CAUSE: Composition '{comp_name}' not found in project")
                print("   Check that the composition name matches exactly (case-sensitive)")
            elif 'footage' in error_text or 'missing' in error_text:
                print(f"\n💡 LIKELY CAUSE: Missing footage files")
                print("   The project references files that couldn't be found")
                print("   This can happen if:")
                print("   - PSD layers weren't extracted as images")
                print("   - Footage paths are incorrect")
                print("   - Population script didn't complete successfully")
            elif 'error' in error_text and '1610153459' in error_text:
                print(f"\n💡 LIKELY CAUSE: Output codec/format issue")
                print("   Try changing the output format or using a different codec")
            elif 'memory' in error_text or 'ram' in error_text:
                print(f"\n💡 LIKELY CAUSE: Insufficient memory")
                print("   After Effects ran out of memory during rendering")
            else:
                print(f"\n💡 Check the aerender output above for specific error messages")

            print(f"\n📋 DEBUGGING STEPS:")
            print(f"   1. Check if project file exists: {abs_project_path}")
            print(f"   2. Open project manually in After Effects")
            print(f"   3. Verify composition '{comp_name}' exists")
            print(f"   4. Check for missing footage warnings")
            print(f"   5. Try rendering manually to see detailed error")
            print(f"{'='*70}\n")

            return False

    except subprocess.TimeoutExpired as e:
        print(f"\n{'='*70}")
        print(f"❌ aerender timeout: Rendering took too long (>5 minutes)")
        print(f"{'='*70}\n")
        return False
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ aerender exception: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n")
        return False


def generate_thumbnail(video_path: str, timestamp: float = 0.5) -> Optional[str]:
    """
    Extract thumbnail frame from video.

    Args:
        video_path: Path to video file
        timestamp: Time in seconds to extract frame

    Returns:
        Path to thumbnail JPEG, or None if failed
    """
    try:
        # Check if ffmpeg is available
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True)
        if result.returncode != 0:
            # ffmpeg not available, skip thumbnail
            return None

        # Generate thumbnail path
        video_path_obj = Path(video_path)
        thumbnail_path = str(video_path_obj.with_suffix('.jpg'))

        # Use ffmpeg to extract frame
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(timestamp),
            '-vframes', '1',
            '-q:v', '2',
            '-y',  # Overwrite
            thumbnail_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and os.path.exists(thumbnail_path):
            return thumbnail_path
        else:
            return None

    except Exception:
        return None


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Get video metadata (duration, resolution, etc.).

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with video info
    """
    info = {
        'duration': None,
        'resolution': None,
        'fps': None
    }

    try:
        # Try using ffprobe
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)

            # Get duration from format
            if 'format' in data and 'duration' in data['format']:
                info['duration'] = float(data['format']['duration'])

            # Get resolution from video stream
            if 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'video':
                        width = stream.get('width')
                        height = stream.get('height')
                        if width and height:
                            info['resolution'] = f"{width}x{height}"

                        fps_str = stream.get('r_frame_rate', '0/1')
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            if int(den) > 0:
                                info['fps'] = int(num) / int(den)
                        break

    except Exception:
        pass

    return info
