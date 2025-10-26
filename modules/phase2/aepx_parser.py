"""
Module 2.1: After Effects Template Parser (AEPX format)

Extracts structured data from AEPX (XML) template files.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any


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

        # Detect namespace (if any)
        namespace = _get_namespace(root)

        # Extract compositions
        compositions = _extract_compositions(root, namespace)

        # Find main composition (named "Split Screen" or first one)
        main_comp_name = next(
            (c['name'] for c in compositions if c['name'] == 'Split Screen'),
            compositions[0]['name'] if compositions else 'Unknown'
        )

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

def _extract_compositions(root: ET.Element, ns: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract all compositions from the AEPX file."""
    compositions = []
    comp_path = './/ns:Composition' if ns else './/Composition'

    for comp in root.findall(comp_path, ns):
        comp_data = {
            "name": comp.get('name', 'Untitled'),
            "width": _get_value(comp, 'Width', int, 1920, ns),
            "height": _get_value(comp, 'Height', int, 1080, ns),
            "duration": _get_value(comp, 'Duration', float, 10.0, ns),
            "layers": _extract_layers(comp, ns)
        }
        compositions.append(comp_data)
    return compositions

def _extract_layers(comp: ET.Element, ns: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract all layers from a composition."""
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
