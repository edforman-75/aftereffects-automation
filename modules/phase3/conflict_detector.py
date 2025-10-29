"""
Module 3.2: Conflict Detection

Detects potential problems in content mappings with configurable thresholds.
"""

from typing import Dict, List, Any, Optional
from .conflict_config import DEFAULT_CONFLICT_CONFIG

# Import font metrics for accurate text width calculation
try:
    from modules.phase1.font_metrics import calculate_text_width, find_system_font
    FONT_METRICS_AVAILABLE = True
except ImportError:
    FONT_METRICS_AVAILABLE = False


def detect_conflicts(psd_data: Dict[str, Any], aepx_data: Dict[str, Any], 
                     mappings: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Detect potential conflicts in content-to-slot mappings.

    Args:
        psd_data: Parsed PSD data from Module 1.1
        aepx_data: Parsed AEPX data from Module 2.1
        mappings: Mapping results from Module 3.1
        config: Optional configuration dict with thresholds

    Returns:
        Dictionary with conflicts and summary
    """
    cfg = config if config is not None else DEFAULT_CONFLICT_CONFIG.copy()
    
    conflicts = []
    conflict_id = 1
    
    # Get main composition dimensions
    main_comp = next(
        (c for c in aepx_data['compositions'] if c['name'] == aepx_data['composition_name']),
        aepx_data['compositions'][0] if aepx_data['compositions'] else None
    )
    
    # Check each mapping
    for mapping in mappings['mappings']:
        psd_layer = next((l for l in psd_data['layers'] if l['name'] == mapping['psd_layer']), None)
        if not psd_layer:
            continue
        
        # Text conflicts
        if mapping['type'] == 'text':
            text_conflicts = _check_text_conflicts(psd_layer, mapping, cfg, conflict_id)
            conflicts.extend(text_conflicts)
            conflict_id += len(text_conflicts)
        
        # Image conflicts
        elif mapping['type'] == 'image':
            image_conflicts = _check_image_conflicts(psd_layer, mapping, main_comp, cfg, conflict_id)
            conflicts.extend(image_conflicts)
            conflict_id += len(image_conflicts)
    
    # Dimension mismatch
    if main_comp:
        dim_conflicts = _check_dimension_mismatch(psd_data, main_comp, cfg, conflict_id)
        conflicts.extend(dim_conflicts)
    
    # Summary
    summary = {
        "total": len(conflicts),
        "critical": sum(1 for c in conflicts if c['severity'] == 'critical'),
        "warning": sum(1 for c in conflicts if c['severity'] == 'warning'),
        "info": sum(1 for c in conflicts if c['severity'] == 'info')
    }
    
    return {"conflicts": conflicts, "summary": summary}


def _check_text_conflicts(psd_layer: Dict, mapping: Dict, cfg: Dict, start_id: int) -> List[Dict]:
    """Check text-related conflicts using actual font metrics when available."""
    conflicts = []
    conflict_id = start_id

    text_content = ""
    if 'text' in psd_layer and 'content' in psd_layer['text']:
        text_content = psd_layer['text']['content']

    if not text_content:
        return conflicts

    text_length = len(text_content)

    # Get font information from PSD layer
    font_name = psd_layer.get('text', {}).get('font_name', 'Arial')
    font_size = psd_layer.get('text', {}).get('font_size', 48.0)

    # Try to calculate actual text width using font metrics
    text_width = None
    font_found = False
    placeholder_width = None

    if FONT_METRICS_AVAILABLE:
        try:
            # Check if we can find the font file
            font_path = find_system_font(font_name)
            font_found = font_path is not None

            # Calculate actual text width
            text_width = calculate_text_width(text_content, font_name, font_size, font_path)

            # Estimate placeholder width (assume 400px default if not specified)
            # In a real implementation, this would come from AEPX placeholder bounds
            placeholder_width = 400.0  # Default placeholder width

            # Check for overflow based on actual metrics
            if text_width and placeholder_width:
                overflow_pixels = text_width - placeholder_width
                overflow_percent = (overflow_pixels / placeholder_width) * 100

                if overflow_pixels > 0:
                    # Text is wider than placeholder
                    if overflow_percent > 20:
                        conflicts.append({
                            "id": f"CONF-{conflict_id}",
                            "type": "TEXT_OVERFLOW",
                            "severity": "critical",
                            "mapping": mapping,
                            "issue": f"Text width ({text_width:.1f}px) exceeds placeholder ({placeholder_width:.0f}px) by {overflow_pixels:.1f}px ({overflow_percent:.1f}%)",
                            "suggestion": "Reduce text length, decrease font size, or increase placeholder width",
                            "auto_fixable": False,
                            "details": {
                                "text_width": round(text_width, 1),
                                "placeholder_width": placeholder_width,
                                "overflow_pixels": round(overflow_pixels, 1),
                                "overflow_percent": round(overflow_percent, 1),
                                "font_name": font_name,
                                "font_size": font_size,
                                "font_found": font_found
                            }
                        })
                        conflict_id += 1
                    elif overflow_percent > 5:
                        conflicts.append({
                            "id": f"CONF-{conflict_id}",
                            "type": "TEXT_OVERFLOW",
                            "severity": "warning",
                            "mapping": mapping,
                            "issue": f"Text width ({text_width:.1f}px) slightly exceeds placeholder ({placeholder_width:.0f}px) by {overflow_pixels:.1f}px",
                            "suggestion": "Consider reducing text or adjusting placeholder",
                            "auto_fixable": False,
                            "details": {
                                "text_width": round(text_width, 1),
                                "placeholder_width": placeholder_width,
                                "overflow_pixels": round(overflow_pixels, 1),
                                "overflow_percent": round(overflow_percent, 1),
                                "font_name": font_name,
                                "font_size": font_size,
                                "font_found": font_found
                            }
                        })
                        conflict_id += 1

                # Warn if font file was not found
                if not font_found:
                    conflicts.append({
                        "id": f"CONF-{conflict_id}",
                        "type": "FONT_FILE_MISSING",
                        "severity": "info",
                        "mapping": mapping,
                        "issue": f"Font file for '{font_name}' not found. Using estimated width.",
                        "suggestion": "Upload font file for more accurate overflow detection",
                        "auto_fixable": False,
                        "details": {
                            "font_name": font_name,
                            "text_width_estimated": round(text_width, 1)
                        }
                    })
                    conflict_id += 1

        except Exception:
            # Fall back to character count if font metrics fail
            pass

    # Fallback: If font metrics not available or failed, use character count
    if text_width is None:
        if text_length > cfg['text_length_critical']:
            conflicts.append({
                "id": f"CONF-{conflict_id}",
                "type": "TEXT_OVERFLOW",
                "severity": "critical",
                "mapping": mapping,
                "issue": f"Text is very long ({text_length} chars). Likely to overflow placeholder.",
                "suggestion": f"Shorten text to under {cfg['text_length_critical']} characters.",
                "auto_fixable": True
            })
            conflict_id += 1
        elif text_length > cfg['text_length_warning']:
            conflicts.append({
                "id": f"CONF-{conflict_id}",
                "type": "TEXT_OVERFLOW",
                "severity": "warning",
                "mapping": mapping,
                "issue": f"Text is moderately long ({text_length} chars). May overflow.",
                "suggestion": "Monitor text length or adjust placeholder size.",
                "auto_fixable": True
            })
            conflict_id += 1
    
    # Font size check
    if 'text' in psd_layer and 'font_size' in psd_layer['text']:
        font_size = psd_layer['text']['font_size']
        
        if font_size > cfg['font_size_large']:
            conflicts.append({
                "id": f"CONF-{conflict_id}",
                "type": "FONT_SIZE",
                "severity": "warning",
                "mapping": mapping,
                "issue": f"Large font size ({font_size}pt) may not fit placeholder.",
                "suggestion": "Reduce font size or increase placeholder size.",
                "auto_fixable": False
            })
            conflict_id += 1
        elif font_size < cfg['font_size_small']:
            conflicts.append({
                "id": f"CONF-{conflict_id}",
                "type": "FONT_SIZE",
                "severity": "info",
                "mapping": mapping,
                "issue": f"Small font size ({font_size}pt) may be hard to read.",
                "suggestion": "Consider increasing font size for readability.",
                "auto_fixable": False
            })
            conflict_id += 1
    
    return conflicts


def _check_image_conflicts(psd_layer: Dict, mapping: Dict, main_comp: Dict, 
                           cfg: Dict, start_id: int) -> List[Dict]:
    """Check image-related conflicts."""
    conflicts = []
    conflict_id = start_id
    
    if not main_comp:
        return conflicts
    
    psd_w, psd_h = psd_layer.get('width', 0), psd_layer.get('height', 0)
    comp_w, comp_h = main_comp.get('width', 1920), main_comp.get('height', 1080)
    
    psd_aspect = psd_w / psd_h if psd_h > 0 else 0
    comp_aspect = comp_w / comp_h if comp_h > 0 else 0
    
    # Aspect ratio mismatch
    if psd_aspect > 0 and comp_aspect > 0:
        aspect_diff = abs(psd_aspect - comp_aspect) / comp_aspect
        
        if aspect_diff > cfg['aspect_ratio_tolerance']:
            conflicts.append({
                "id": f"CONF-{conflict_id}",
                "type": "ASPECT_RATIO_MISMATCH",
                "severity": "info",
                "mapping": mapping,
                "issue": f"Aspect ratio mismatch. Image: {psd_aspect:.2f}, Template: {comp_aspect:.2f}",
                "suggestion": "PSD will be imported as full composition - aspect handled by After Effects.",
                "auto_fixable": False,
                "details": {
                    "psd_width": psd_w,
                    "psd_height": psd_h,
                    "psd_aspect": round(psd_aspect, 2),
                    "comp_width": comp_w,
                    "comp_height": comp_h,
                    "comp_aspect": round(comp_aspect, 2)
                },
                "resolution_options": [
                    {
                        "id": "accept",
                        "label": "Accept - PSD Import Handles This",
                        "description": "The full PSD will be imported as a composition with all layers intact",
                        "is_default": True,
                        "params": {
                            "method": "accept"
                        }
                    }
                ]
            })
            conflict_id += 1
    
    # Resolution warning (upscaling)
    scale_factor = max(comp_w / psd_w, comp_h / psd_h) if psd_w > 0 and psd_h > 0 else 1
    
    if scale_factor > cfg['upscale_warning_factor']:
        conflicts.append({
            "id": f"CONF-{conflict_id}",
            "type": "RESOLUTION_WARNING",
            "severity": "warning",
            "mapping": mapping,
            "issue": f"Image will be upscaled {scale_factor:.1f}x. May look pixelated.",
            "suggestion": f"Use higher resolution (recommend: {comp_w}×{comp_h} or larger).",
            "auto_fixable": False,
            "resolution_options": [
                {
                    "id": "accept_quality_loss",
                    "label": "Accept (May Look Pixelated)",
                    "description": f"Proceed with upscaling - image will be enlarged {scale_factor:.1f}x",
                    "is_default": True,
                    "params": {
                        "method": "accept"
                    }
                },
                {
                    "id": "upload_higher_res",
                    "label": "Upload Higher Resolution",
                    "description": f"Replace with image at least {comp_w}×{comp_h}",
                    "is_default": False,
                    "params": {
                        "method": "reupload",
                        "min_width": comp_w,
                        "min_height": comp_h
                    }
                }
            ]
        })
        conflict_id += 1
    elif psd_w / comp_w < cfg['downscale_info_factor'] or psd_h / comp_h < cfg['downscale_info_factor']:
        conflicts.append({
            "id": f"CONF-{conflict_id}",
            "type": "DIMENSION_INFO",
            "severity": "info",
            "mapping": mapping,
            "issue": f"Image ({psd_w}×{psd_h}) is larger than needed. Will be downscaled.",
            "suggestion": "Downscaling is fine. Consider optimizing file size if needed.",
            "auto_fixable": False
        })
        conflict_id += 1
    
    return conflicts


def _check_dimension_mismatch(psd_data: Dict, main_comp: Dict, cfg: Dict, start_id: int) -> List[Dict]:
    """Check PSD to template dimension mismatches."""
    conflicts = []
    
    psd_w, psd_h = psd_data.get('width', 0), psd_data.get('height', 0)
    comp_w, comp_h = main_comp.get('width', 1920), main_comp.get('height', 1080)
    
    if psd_w == comp_w and psd_h == comp_h:
        return conflicts
    
    psd_aspect = psd_w / psd_h if psd_h > 0 else 0
    comp_aspect = comp_w / comp_h if comp_h > 0 else 0
    aspect_diff = abs(psd_aspect - comp_aspect) / comp_aspect if comp_aspect > 0 else 0
    
    severity = "warning" if aspect_diff > cfg['dimension_tolerance'] else "info"
    
    conflicts.append({
        "id": f"CONF-{start_id}",
        "type": "DIMENSION_INFO",
        "severity": severity,
        "mapping": {"psd_layer": "Document", "aepx_placeholder": "Composition"},
        "issue": f"PSD ({psd_w}×{psd_h}) differs from template ({comp_w}×{comp_h}).",
        "suggestion": "Content will be scaled/repositioned. Verify layout after import.",
        "auto_fixable": False,
        "resolution_options": [
            {
                "id": "accept_scaling",
                "label": "Accept Auto-Scaling",
                "description": "Let After Effects handle scaling/positioning automatically",
                "is_default": True,
                "params": {
                    "method": "accept"
                }
            },
            {
                "id": "adjust_psd",
                "label": "Adjust PSD Dimensions",
                "description": f"Recreate PSD at {comp_w}×{comp_h} for perfect fit",
                "is_default": False,
                "params": {
                    "method": "manual_adjust",
                    "target_width": comp_w,
                    "target_height": comp_h
                }
            }
        ]
    })
    
    return conflicts
