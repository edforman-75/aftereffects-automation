"""
Module 1.1: Photoshop File Parser

Extracts structured data from PSD files into Python dictionaries.
Uses psd-tools library to read and parse Photoshop documents.
"""

from psd_tools import PSDImage
from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_psd(file_path: str) -> Dict[str, Any]:
    """
    Parse a PSD file and extract structured layer information.

    Args:
        file_path: Path to the PSD file

    Returns:
        Dictionary containing file metadata and layer hierarchy:
        {
            "filename": str,
            "width": int,
            "height": int,
            "layers": List[Dict]  # List of layer information
        }

    Raises:
        FileNotFoundError: If PSD file doesn't exist
        ValueError: If file is not a valid PSD
    """
    try:
        # Validate file exists
        psd_path = Path(file_path)
        if not psd_path.exists():
            raise FileNotFoundError(f"PSD file not found: {file_path}")

        # Open and parse PSD file
        psd = PSDImage.open(file_path)

        # Extract document-level information
        result = {
            "filename": psd_path.name,
            "width": psd.width,
            "height": psd.height,
            "layers": []
        }

        # Recursively extract all layers
        result["layers"] = _extract_layers(psd)

        return result

    except Exception as e:
        if "not a valid PSD" in str(e) or "cannot identify" in str(e):
            raise ValueError(f"Invalid PSD file: {file_path}")
        raise


def _extract_layers(psd_or_group, parent_path: str = "") -> List[Dict[str, Any]]:
    """
    Recursively extract layer information from PSD or layer group.

    Args:
        psd_or_group: PSDImage or Group layer object
        parent_path: Path of parent groups (for nested layers)

    Returns:
        List of layer dictionaries
    """
    layers = []

    for layer in psd_or_group:
        # Determine layer type
        layer_type = _get_layer_type(layer)

        # Build full layer path (including parent groups)
        layer_path = f"{parent_path}/{layer.name}" if parent_path else layer.name

        # Extract bounding box
        bbox = layer.bbox if hasattr(layer, 'bbox') else None

        layer_info = {
            "name": layer.name,
            "type": layer_type,
            "visible": layer.visible,
            "path": layer_path,
        }

        # Add dimensions if available
        if bbox:
            # Handle bbox - can be tuple (x1, y1, x2, y2) or object with attributes
            if isinstance(bbox, tuple) and len(bbox) == 4:
                x1, y1, x2, y2 = bbox
            else:
                x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2

            layer_info["bbox"] = {
                "left": x1,
                "top": y1,
                "right": x2,
                "bottom": y2
            }
            layer_info["width"] = x2 - x1
            layer_info["height"] = y2 - y1

        # Extract text content if it's a text layer
        if layer_type == "text":
            text_data = _extract_text_info(layer)
            if text_data:
                layer_info["text"] = text_data

        # If it's a group, recursively extract child layers
        if layer_type == "group":
            layer_info["children"] = _extract_layers(layer, layer_path)

        layers.append(layer_info)

    return layers


def _extract_text_info(layer) -> Optional[Dict[str, Any]]:
    """
    Extract text content and styling information from a text layer.

    Args:
        layer: Text layer object

    Returns:
        Dictionary with text content, font, size, and color information
    """
    try:
        text_info = {}

        # Extract text content
        if hasattr(layer, 'text'):
            text_info['content'] = layer.text

        # Extract font information from engine_dict
        if hasattr(layer, 'engine_dict'):
            engine_dict = layer.engine_dict

            # Extract style information from StyleRun
            if 'StyleRun' in engine_dict:
                style_run = engine_dict['StyleRun']

                if 'RunArray' in style_run and len(style_run['RunArray']) > 0:
                    run = style_run['RunArray'][0]

                    if 'StyleSheet' in run and 'StyleSheetData' in run['StyleSheet']:
                        style_data = run['StyleSheet']['StyleSheetData']

                        # Font index (actual font name requires font list lookup)
                        if 'Font' in style_data:
                            text_info['font_index'] = int(style_data['Font'])

                        # Font size
                        if 'FontSize' in style_data:
                            text_info['font_size'] = float(style_data['FontSize'])

                        # Font color (ARGB format)
                        if 'FillColor' in style_data and 'Values' in style_data['FillColor']:
                            colors = style_data['FillColor']['Values']
                            if len(colors) >= 4:
                                # Colors are in ARGB order: [alpha, red, green, blue]
                                text_info['color'] = {
                                    'r': int(colors[1] * 255),
                                    'g': int(colors[2] * 255),
                                    'b': int(colors[3] * 255),
                                    'a': int(colors[0] * 255)
                                }

        return text_info if text_info else None

    except Exception as e:
        # If text extraction fails, return None rather than breaking the parser
        return None


def _get_layer_type(layer) -> str:
    """Determine the type of a layer."""
    layer_kind = layer.kind if hasattr(layer, 'kind') else None

    if layer_kind == 'type':
        return 'text'
    elif layer_kind == 'pixel':
        return 'image'
    elif layer_kind == 'shape':
        return 'shape'
    elif layer_kind == 'group':
        return 'group'
    elif layer_kind == 'smartobject':
        return 'smartobject'
    else:
        return 'unknown'
