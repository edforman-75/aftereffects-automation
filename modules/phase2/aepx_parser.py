"""
Module 2.1: After Effects Template Parser (AEPX format)

Extracts structured data from AEPX (XML) template files.
Supports After Effects 2025 format.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_aepx(file_path: str) -> Dict[str, Any]:
    """
    Parse an AEPX file and extract structured template information.

    Args:
        file_path: Path to the AEPX file

    Returns:
        Dictionary with filename, composition_name, compositions, and placeholders

    Raises:
        FileNotFoundError: If AEPX file doesn't exist
        ValueError: If file is not valid AEPX
    """
    try:
        # Validate file exists
        aepx_path = Path(file_path)
        if not aepx_path.exists():
            raise FileNotFoundError(f"AEPX file not found: {file_path}")

        # Parse XML
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Try new AE 2025 format first
        compositions = _extract_compositions_ae2025(root)

        # Fallback to old format if no compositions found
        if not compositions:
            namespace = _get_namespace(root)
            compositions = _extract_compositions_legacy(root, namespace)

        # Find main composition (prefer specific names or first one)
        main_comp_name = _find_main_composition(compositions)

        # Extract placeholders
        placeholders = _extract_placeholders(compositions)

        return {
            "filename": aepx_path.name,
            "composition_name": main_comp_name,
            "compositions": compositions,
            "placeholders": placeholders
        }

    except ET.ParseError:
        raise ValueError(f"Invalid AEPX file (XML parse error): {file_path}")
    except Exception as e:
        if "not found" in str(e).lower():
            raise
        raise ValueError(f"Error parsing AEPX file: {e}")


def _extract_compositions_ae2025(root: ET.Element) -> List[Dict[str, Any]]:
    """
    Extract compositions from After Effects 2025 format.

    In AE 2025, the structure is:
    - <string>composition_name</string>
    - Followed by <Layr> blocks for that composition
    - Each <Layr> has <string>layer_name</string> as first child
    """
    compositions = []
    current_comp = None

    # Iterate through all elements in document order
    for elem in root.iter():
        # Strip namespace from tag for comparison
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        # Look for composition markers: <string> elements at specific depth
        # that appear before <Layr> blocks
        if tag == 'string' and elem.text and len(elem.text.strip()) > 0:
            text = elem.text.strip()

            # Check if this string is followed by Layr blocks (composition name)
            # by looking at siblings
            parent = _find_parent_map(root, elem)
            if parent is not None:
                # Get position of current element
                children = list(parent)
                try:
                    idx = children.index(elem)
                    # Look ahead for Layr blocks
                    has_layr_after = False
                    for i in range(idx + 1, min(idx + 20, len(children))):
                        child_tag = children[i].tag.split('}')[-1] if '}' in children[i].tag else children[i].tag
                        if child_tag == 'Layr':
                            has_layr_after = True
                            break

                    # If followed by Layr blocks and not inside a Layr, it's a comp name
                    if has_layr_after and not _is_inside_layr_map(root, elem):
                        # Save previous composition if exists
                        if current_comp is not None:
                            compositions.append(current_comp)

                        # Start new composition
                        current_comp = {
                            'name': text,
                            'width': 1920,  # Default, can't extract from this format
                            'height': 1080,
                            'duration': 10.0,
                            'layers': []
                        }
                except (ValueError, IndexError):
                    pass

        # Extract layers from <Layr> blocks
        elif tag == 'Layr' and current_comp is not None:
            layer = _extract_layer_ae2025(elem)
            if layer:
                current_comp['layers'].append(layer)

    # Add last composition
    if current_comp is not None:
        compositions.append(current_comp)

    return compositions


def _extract_layer_ae2025(layr_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """
    Extract layer information from a <Layr> element in AE 2025 format.

    The first <string> child is the layer name.
    Check for "ADBE Text Properties" to identify text layers.
    """
    # Find first <string> child - that's the layer name
    layer_name = None
    for child in layr_elem:
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if child_tag == 'string' and child.text:
            layer_name = child.text.strip()
            break

    if not layer_name:
        return None

    # Check if it's a text layer by looking for "ADBE Text Properties"
    # In AE 2025, this appears as hex in bdata attribute:
    # "4144424520546578742050726f70657274696573" = "ADBE Text Properties"
    is_text_layer = False
    xml_string = ET.tostring(layr_elem, encoding='unicode')
    if '4144424520546578742050726f70657274696573' in xml_string:
        is_text_layer = True

    # Determine layer type
    layer_type = 'text' if is_text_layer else 'image'

    # Check if it's a placeholder
    is_placeholder = _is_placeholder_name(layer_name)

    return {
        'name': layer_name,
        'type': layer_type,
        'is_placeholder': is_placeholder
    }


# Build parent map once for efficiency
_PARENT_MAP_CACHE = {}


def _build_parent_map(root: ET.Element) -> Dict[ET.Element, ET.Element]:
    """Build a map of element -> parent for efficient parent lookup."""
    parent_map = {}
    for parent in root.iter():
        for child in parent:
            parent_map[child] = parent
    return parent_map


def _find_parent_map(root: ET.Element, elem: ET.Element) -> Optional[ET.Element]:
    """Find parent using cached parent map."""
    # Build map if not cached
    root_id = id(root)
    if root_id not in _PARENT_MAP_CACHE:
        _PARENT_MAP_CACHE[root_id] = _build_parent_map(root)

    return _PARENT_MAP_CACHE[root_id].get(elem)


def _is_inside_layr_map(root: ET.Element, elem: ET.Element) -> bool:
    """Check if an element is inside a <Layr> block using parent map."""
    parent = _find_parent_map(root, elem)
    while parent is not None:
        parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
        if parent_tag == 'Layr':
            return True
        parent = _find_parent_map(root, parent)
    return False


def _find_main_composition(compositions: List[Dict[str, Any]]) -> str:
    """Find the main composition name from the list."""
    if not compositions:
        return 'Unknown'

    # Prefer compositions with specific names
    for comp in compositions:
        name = comp['name'].lower()
        # Look for main-ish names
        if any(keyword in name for keyword in ['main', 'split', 'test-aep']):
            return comp['name']

    # Return first composition
    return compositions[0]['name']


def _extract_compositions_legacy(root: ET.Element, ns: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract compositions from legacy AEPX format (pre-2025)."""
    compositions = []
    comp_path = './/ns:Composition' if ns else './/Composition'

    for comp in root.findall(comp_path, ns):
        comp_data = {
            "name": comp.get('name', 'Untitled'),
            "width": _get_value(comp, 'Width', int, 1920, ns),
            "height": _get_value(comp, 'Height', int, 1080, ns),
            "duration": _get_value(comp, 'Duration', float, 10.0, ns),
            "layers": _extract_layers_legacy(comp, ns)
        }
        compositions.append(comp_data)
    return compositions


def _extract_layers_legacy(comp: ET.Element, ns: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract layers from legacy format composition."""
    layers = []
    layer_path = './/ns:Layer' if ns else './/Layer'
    for layer in comp.findall(layer_path, ns):
        layer_name = _get_value(layer, 'Name', str, 'Unnamed', ns)
        is_placeholder = _get_value(layer, 'IsPlaceholder', bool, False, ns)
        if not is_placeholder:
            is_placeholder = _is_placeholder_name(layer_name)
        layers.append({
            "name": layer_name,
            "type": layer.get('type', 'unknown').lower(),
            "is_placeholder": is_placeholder
        })
    return layers


def _extract_placeholders(compositions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract all placeholder layers from compositions."""
    placeholders = []
    for comp in compositions:
        for layer in comp.get('layers', []):
            if layer.get('is_placeholder', False):
                placeholders.append({
                    "name": layer['name'],
                    "type": layer['type'],
                    "layer_name": layer['name'],
                    "composition": comp['name']
                })
    return placeholders


def _is_placeholder_name(name: str) -> bool:
    """Detect if a layer name suggests it's a placeholder."""
    keywords = ['player', 'name', 'fullname', 'image', 'photo',
                'placeholder', 'featured', 'text', 'title']
    return any(kw in name.lower() for kw in keywords)


def _get_namespace(root: ET.Element) -> Dict[str, str]:
    """Extract namespace from root element."""
    if root.tag.startswith('{'):
        ns_uri = root.tag[1:root.tag.index('}')]
        return {'ns': ns_uri}
    return {}


def _get_value(element: ET.Element, tag: str, value_type: type, default: Any,
               ns: Dict[str, str] = None) -> Any:
    """Get and convert value from XML element."""
    if ns:
        child = element.find(f'ns:{tag}', ns)
    else:
        child = element.find(tag)

    text = child.text if child is not None and child.text else None

    if text is None:
        return default

    try:
        if value_type == bool:
            return text.lower() in ('true', '1', 'yes')
        elif value_type == int:
            return int(float(text))
        elif value_type == float:
            return float(text)
        else:
            return text
    except (ValueError, AttributeError):
        return default
