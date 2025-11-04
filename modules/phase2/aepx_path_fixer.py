"""
Module 2.2: AEPX Footage Path Fixer

Fix absolute footage paths in AEPX files to make them portable across machines.
Similar to After Effects' "Collect Files" feature.
"""

import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def find_footage_references(aepx_path: str) -> List[Dict[str, str]]:
    """
    Find all footage file references in AEPX file.

    Args:
        aepx_path: Path to AEPX file

    Returns:
        List of dictionaries with file info:
        [
            {
                'path': '/absolute/path/to/file.png',
                'type': 'image',
                'exists': True/False
            }
        ]
    """
    references = []

    try:
        # Parse AEPX XML
        tree = ET.parse(aepx_path)
        root = tree.getroot()

        # Find all file references
        # AEPX stores file paths in <fldr> tags and fullpath attributes

        # Method 1: Look for fullpath attributes
        for elem in root.iter():
            if 'fullpath' in elem.attrib:
                filepath = elem.attrib['fullpath']
                if filepath and filepath not in ['.', '..']:
                    file_type = _guess_file_type(filepath)
                    references.append({
                        'path': filepath,
                        'type': file_type,
                        'exists': os.path.exists(filepath),
                        'element': elem.tag
                    })

        # Method 2: Look for file paths in text content
        for elem in root.iter():
            if elem.text:
                # Look for absolute paths in text
                paths = _extract_paths_from_text(elem.text)
                for filepath in paths:
                    if _is_valid_file_path(filepath):
                        file_type = _guess_file_type(filepath)
                        references.append({
                            'path': filepath,
                            'type': file_type,
                            'exists': os.path.exists(filepath),
                            'element': elem.tag
                        })

        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_refs = []
        for ref in references:
            if ref['path'] not in seen:
                seen.add(ref['path'])
                unique_refs.append(ref)

        return unique_refs

    except Exception as e:
        print(f"Error finding footage references: {str(e)}")
        return []


def fix_footage_paths(aepx_path: str, output_path: Optional[str] = None,
                      footage_dir: Optional[str] = None) -> Dict:
    """
    Fix absolute footage paths in AEPX file.

    Args:
        aepx_path: Path to source AEPX file
        output_path: Path for fixed AEPX (or None to overwrite)
        footage_dir: Directory where footage should be found
                     (uses relative paths from this directory)

    Returns:
        {
            'success': True/False,
            'fixed_paths': {old_path: new_path, ...},
            'missing_files': [list of files not found],
            'output_path': path to fixed AEPX
        }
    """
    if not output_path:
        output_path = aepx_path.replace('.aepx', '_fixed.aepx')

    fixed_paths = {}
    missing_files = []

    try:
        # Find all references first
        references = find_footage_references(aepx_path)

        if not references:
            return {
                'success': True,
                'fixed_paths': {},
                'missing_files': [],
                'output_path': output_path,
                'message': 'No footage references found'
            }

        # Read AEPX as text (easier for path replacement)
        with open(aepx_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Process each reference
        for ref in references:
            old_path = ref['path']
            new_path = None

            if footage_dir:
                # Try to find file in footage_dir
                filename = os.path.basename(old_path)
                footage_path = os.path.join(footage_dir, filename)

                if os.path.exists(footage_path):
                    # Convert to relative path from AEPX location
                    aepx_dir = os.path.dirname(os.path.abspath(aepx_path))
                    new_path = os.path.relpath(footage_path, aepx_dir)
                else:
                    missing_files.append(filename)
            else:
                # Try to find file relative to AEPX
                filename = os.path.basename(old_path)
                aepx_dir = os.path.dirname(os.path.abspath(aepx_path))

                # Check common locations
                search_paths = [
                    os.path.join(aepx_dir, filename),
                    os.path.join(aepx_dir, 'footage', filename),
                    os.path.join(aepx_dir, 'assets', filename),
                    os.path.join(aepx_dir, '..', 'footage', filename),
                ]

                for search_path in search_paths:
                    if os.path.exists(search_path):
                        new_path = os.path.relpath(search_path, aepx_dir)
                        break

                if not new_path:
                    missing_files.append(filename)

            # Replace path in content
            if new_path:
                # Escape special regex characters in old_path
                old_path_escaped = re.escape(old_path)
                # Replace with forward slashes (AE uses forward slashes)
                new_path_normalized = new_path.replace('\\', '/')
                content = re.sub(old_path_escaped, new_path_normalized, content)
                fixed_paths[old_path] = new_path_normalized

        # Write fixed AEPX
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            'success': True,
            'fixed_paths': fixed_paths,
            'missing_files': list(set(missing_files)),  # Remove duplicates
            'output_path': output_path,
            'message': f'Fixed {len(fixed_paths)} paths, {len(set(missing_files))} files missing'
        }

    except Exception as e:
        return {
            'success': False,
            'fixed_paths': {},
            'missing_files': [],
            'output_path': None,
            'error': str(e)
        }


def collect_footage_files(aepx_path: str, output_dir: str,
                          copy_aepx: bool = True) -> Dict:
    """
    Collect all footage files and create portable AEPX.
    Similar to After Effects' "Collect Files" feature.

    Args:
        aepx_path: Path to source AEPX file
        output_dir: Directory to collect files into
        copy_aepx: Whether to copy AEPX to output_dir

    Returns:
        {
            'success': True/False,
            'collected_files': [list of copied files],
            'missing_files': [list of files not found],
            'aepx_path': path to new AEPX
        }
    """
    collected_files = []
    missing_files = []

    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Create footage subdirectory
        footage_dir = os.path.join(output_dir, 'footage')
        os.makedirs(footage_dir, exist_ok=True)

        # Find all references
        references = find_footage_references(aepx_path)

        # Copy files
        for ref in references:
            src_path = ref['path']

            if os.path.exists(src_path):
                filename = os.path.basename(src_path)
                dst_path = os.path.join(footage_dir, filename)

                # Handle duplicate filenames
                counter = 1
                base, ext = os.path.splitext(filename)
                while os.path.exists(dst_path):
                    filename = f"{base}_{counter}{ext}"
                    dst_path = os.path.join(footage_dir, filename)
                    counter += 1

                shutil.copy2(src_path, dst_path)
                collected_files.append(dst_path)
            else:
                missing_files.append(os.path.basename(src_path))

        # Copy and fix AEPX
        if copy_aepx:
            aepx_filename = os.path.basename(aepx_path)
            new_aepx_path = os.path.join(output_dir, aepx_filename)
        else:
            new_aepx_path = aepx_path.replace('.aepx', '_collected.aepx')

        # Fix paths to use relative paths to footage directory
        result = fix_footage_paths(aepx_path, new_aepx_path, footage_dir)

        return {
            'success': True,
            'collected_files': collected_files,
            'missing_files': list(set(missing_files)),
            'aepx_path': new_aepx_path,
            'footage_dir': footage_dir,
            'message': f'Collected {len(collected_files)} files, {len(set(missing_files))} missing'
        }

    except Exception as e:
        return {
            'success': False,
            'collected_files': [],
            'missing_files': [],
            'aepx_path': None,
            'error': str(e)
        }


# Helper functions

def _guess_file_type(filepath: str) -> str:
    """Guess file type from extension."""
    ext = os.path.splitext(filepath)[1].lower()

    image_exts = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.psd', '.ai', '.svg'}
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    audio_exts = {'.mp3', '.wav', '.aac', '.m4a', '.flac'}

    if ext in image_exts:
        return 'image'
    elif ext in video_exts:
        return 'video'
    elif ext in audio_exts:
        return 'audio'
    else:
        return 'unknown'


def _extract_paths_from_text(text: str) -> List[str]:
    """Extract file paths from text content."""
    paths = []

    # Pattern for absolute paths (macOS/Unix)
    pattern = r'/[\w\s\-\./]+\.\w+'

    matches = re.findall(pattern, text)
    paths.extend(matches)

    return paths


def _is_valid_file_path(filepath: str) -> bool:
    """Check if string looks like a valid file path (macOS/Unix)."""
    # Filter out XML namespaces and URLs
    if filepath.startswith('//') or filepath.startswith('http'):
        return False

    # Filter out namespace-like paths
    if '/vnd.adobe' in filepath or '/dc/elements' in filepath:
        return False

    # Must have an extension
    ext = os.path.splitext(filepath)[1]
    if not ext or len(ext) > 5:  # Extensions shouldn't be too long
        return False

    # Must be absolute path (starting with /)
    return filepath.startswith('/')


if __name__ == '__main__':
    """Test the module."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python aepx_path_fixer.py <aepx_file> [footage_dir]")
        sys.exit(1)

    aepx_file = sys.argv[1]
    footage_dir = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\n{'='*70}")
    print("AEPX FOOTAGE PATH FIXER")
    print(f"{'='*70}\n")

    # Find references
    print("Step 1: Finding footage references...")
    refs = find_footage_references(aepx_file)

    print(f"\nFound {len(refs)} footage references:\n")
    for i, ref in enumerate(refs, 1):
        status = "✅" if ref['exists'] else "❌"
        print(f"{i}. {status} {ref['type']}: {ref['path']}")

    if footage_dir:
        print(f"\n\nStep 2: Fixing paths to use footage directory: {footage_dir}")
        result = fix_footage_paths(aepx_file, footage_dir=footage_dir)

        if result['success']:
            print(f"\n✅ {result['message']}")
            print(f"\nFixed AEPX: {result['output_path']}")

            if result['fixed_paths']:
                print("\nFixed paths:")
                for old, new in result['fixed_paths'].items():
                    print(f"  {os.path.basename(old)} → {new}")

            if result['missing_files']:
                print("\n⚠️  Missing files:")
                for missing in result['missing_files']:
                    print(f"  ❌ {missing}")
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")

    print(f"\n{'='*70}\n")
