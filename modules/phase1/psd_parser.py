"""
Module 1.1: Photoshop File Parser

Extracts structured data from PSD files into Python dictionaries.
Uses psd-tools library to read and parse Photoshop documents.

Fallback chain:
1. psd-tools (full parsing) - for standard PSD formats
2. Photoshop automation (full parsing) - for newer formats via ExtendScript
3. Pillow (limited parsing) - basic info only, last resort
"""

from psd_tools import PSDImage
from PIL import Image
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


def parse_psd(file_path: str) -> Dict[str, Any]:
    """
    Parse a PSD file and extract structured layer information.

    Uses a three-tier fallback approach:
    1. psd-tools (full parsing) - for standard PSD formats
    2. Photoshop automation (full parsing) - for newer formats via ExtendScript
    3. Pillow (limited parsing) - basic info only, last resort

    Args:
        file_path: Path to the PSD file

    Returns:
        Dictionary containing file metadata and layer hierarchy:
        {
            "filename": str,
            "width": int,
            "height": int,
            "layers": List[Dict],  # List of layer information
            "limited_parse": bool,  # True if Pillow fallback was used
            "parse_method": str  # "psd-tools", "photoshop", or "pillow"
        }

    Raises:
        FileNotFoundError: If PSD file doesn't exist
        ValueError: If file is not a valid PSD
    """
    # Validate file exists
    psd_path = Path(file_path)
    if not psd_path.exists():
        raise FileNotFoundError(f"PSD file not found: {file_path}")

    # Try psd-tools first (full layer parsing)
    try:
        logger.info(f"Attempting to parse PSD with psd-tools: {file_path}")
        psd = PSDImage.open(file_path)

        # Extract document-level information
        result = {
            "filename": psd_path.name,
            "width": psd.width,
            "height": psd.height,
            "layers": [],
            "limited_parse": False,
            "parse_method": "psd-tools"
        }

        # Recursively extract all layers
        result["layers"] = _extract_layers(psd)

        logger.info(f"Successfully parsed PSD with psd-tools: {len(result['layers'])} layers found")
        return result

    except AssertionError as e:
        # Check if it's a version error
        if "Invalid version" in str(e) or "version" in str(e).lower():
            logger.warning(f"psd-tools failed with version error: {e}")

            # Try Photoshop automation fallback (if available and enabled)
            if _should_try_photoshop():
                logger.info(f"Attempting Photoshop automation: {file_path}")
                try:
                    return _parse_psd_with_photoshop(file_path, psd_path)
                except Exception as ps_error:
                    logger.warning(f"Photoshop automation failed: {ps_error}")
                    # Continue to Pillow fallback

            # Fall back to Pillow
            logger.info(f"Falling back to Pillow for basic parsing: {file_path}")
            try:
                return _parse_psd_with_pillow(file_path, psd_path)
            except Exception as pillow_error:
                logger.error(f"Pillow fallback also failed: {pillow_error}")
                raise ValueError(
                    f"Unable to parse PSD file (newer Photoshop format): {file_path}. "
                    f"psd-tools error: {e}, Pillow error: {pillow_error}"
                )
        else:
            # Re-raise if it's not a version error
            raise

    except Exception as e:
        # Check for other common errors
        if "not a valid PSD" in str(e) or "cannot identify" in str(e):
            raise ValueError(f"Invalid PSD file: {file_path}")

        # Try Photoshop automation fallback for other psd-tools errors
        if _should_try_photoshop():
            logger.warning(f"psd-tools failed with error: {e}")
            logger.info(f"Attempting Photoshop automation: {file_path}")
            try:
                return _parse_psd_with_photoshop(file_path, psd_path)
            except Exception as ps_error:
                logger.warning(f"Photoshop automation failed: {ps_error}")
                # Continue to Pillow fallback

        # Try Pillow fallback
        logger.warning(f"Attempting Pillow fallback: {file_path}")
        try:
            return _parse_psd_with_pillow(file_path, psd_path)
        except Exception as pillow_error:
            logger.error(f"Pillow fallback also failed: {pillow_error}")
            raise ValueError(
                f"Unable to parse PSD file: {file_path}. "
                f"psd-tools error: {e}, Pillow error: {pillow_error}"
            )


def _should_try_photoshop() -> bool:
    """
    Check if Photoshop automation should be attempted.

    Checks:
    1. DISABLE_PHOTOSHOP_FALLBACK environment variable
    2. Photoshop is installed (via photoshop_extractor module)

    Returns:
        True if Photoshop automation should be attempted
    """
    # Check if explicitly disabled
    if os.getenv('DISABLE_PHOTOSHOP_FALLBACK', 'false').lower() == 'true':
        logger.debug("Photoshop fallback is disabled via environment variable")
        return False

    # Check if Photoshop is available
    try:
        from modules.phase1.photoshop_extractor import is_photoshop_available
        return is_photoshop_available()
    except ImportError:
        logger.debug("Photoshop extractor module not available")
        return False
    except Exception as e:
        logger.debug(f"Could not check Photoshop availability: {e}")
        return False


def _parse_psd_with_photoshop(file_path: str, psd_path: Path) -> Dict[str, Any]:
    """
    Parse PSD file using Photoshop automation via ExtendScript.

    This provides full layer parsing for newer Photoshop formats that psd-tools
    cannot handle.

    Args:
        file_path: Path to the PSD file
        psd_path: Path object for the PSD file

    Returns:
        Dictionary with complete PSD layer information

    Raises:
        Exception: If Photoshop automation fails
    """
    from modules.phase1.photoshop_extractor import extract_with_photoshop

    logger.info(f"Using Photoshop automation to parse: {file_path}")

    result = extract_with_photoshop(file_path)

    # Ensure parse_method is set
    if 'parse_method' not in result:
        result['parse_method'] = 'photoshop'

    logger.info(
        f"Successfully parsed PSD with Photoshop: {len(result['layers'])} layers, "
        f"{result['width']}x{result['height']}"
    )

    return result


def _parse_psd_with_pillow(file_path: str, psd_path: Path) -> Dict[str, Any]:
    """
    Parse PSD file using Pillow (fallback for newer Photoshop formats).

    Pillow can read PSDs as images and extract basic info even from newer formats
    that psd-tools doesn't support. However, it provides limited layer information.

    Args:
        file_path: Path to the PSD file
        psd_path: Path object for the PSD file

    Returns:
        Dictionary with basic PSD information and limited layer data
    """
    logger.info(f"Parsing PSD with Pillow: {file_path}")

    # Open PSD with Pillow
    with Image.open(file_path) as img:
        # Extract basic document information
        result = {
            "filename": psd_path.name,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "layers": [],
            "limited_parse": True,  # Flag indicating limited parsing
            "parse_method": "pillow"
        }

        # Try to extract layer information from Pillow
        # Pillow provides basic layer names through the layers attribute
        layers = []

        try:
            # Check if the image has layers (PSD specific)
            if hasattr(img, 'layers'):
                # In Pillow, layers is a list of (name, mode) tuples
                for idx, layer_info in enumerate(img.layers):
                    if isinstance(layer_info, tuple) and len(layer_info) >= 2:
                        layer_name = layer_info[0] if layer_info[0] else f"Layer {idx + 1}"
                        layer_mode = layer_info[1] if len(layer_info) > 1 else "unknown"
                    else:
                        layer_name = f"Layer {idx + 1}"
                        layer_mode = "unknown"

                    layers.append({
                        "name": layer_name,
                        "type": "unknown",  # Pillow doesn't provide layer type
                        "visible": True,  # Assume visible (Pillow doesn't track this)
                        "path": layer_name,
                        "mode": layer_mode
                    })

                logger.info(f"Extracted {len(layers)} layer names from Pillow")

            # If no layers found, try extracting from n_frames (for layered images)
            elif hasattr(img, 'n_frames') and img.n_frames > 1:
                logger.info(f"PSD has {img.n_frames} frames, creating layer placeholders")
                for i in range(img.n_frames):
                    layers.append({
                        "name": f"Layer {i + 1}",
                        "type": "unknown",
                        "visible": True,
                        "path": f"Layer {i + 1}"
                    })

            # If still no layers, create at least one placeholder
            if not layers:
                logger.info("No layer information available, creating merged layer placeholder")
                layers.append({
                    "name": "Merged Image",
                    "type": "image",
                    "visible": True,
                    "path": "Merged Image",
                    "width": img.width,
                    "height": img.height
                })

        except Exception as e:
            logger.warning(f"Could not extract layer information from Pillow: {e}")
            # Create at least one placeholder layer
            layers.append({
                "name": "Merged Image",
                "type": "image",
                "visible": True,
                "path": "Merged Image",
                "width": img.width,
                "height": img.height
            })

        result["layers"] = layers

        logger.info(
            f"Successfully parsed PSD with Pillow: {len(layers)} layers, "
            f"{img.width}x{img.height}, mode={img.mode} (LIMITED PARSE)"
        )

        return result


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
