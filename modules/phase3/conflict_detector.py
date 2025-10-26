"""
Module 3.2: Conflict Detection

Detects potential problems in content mappings before rendering.
"""

from typing import Dict, List, Any


def detect_conflicts(psd_data: Dict[str, Any], aepx_data: Dict[str, Any], 
                     mappings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect potential conflicts in content-to-slot mappings.

    Args:
        psd_data: Parsed PSD data from Module 1.1
        aepx_data: Parsed AEPX data from Module 2.1
        mappings: Mapping results from Module 3.1

    Returns:
        Dictionary with conflicts and summary
    """
    conflicts = []
    
    # Get main composition dimensions
    main_comp = next(
        (c for c in aepx_data['compositions'] if c['name'] == aepx_data['composition_name']),
        aepx_data['compositions'][0] if aepx_data['compositions'] else None
    )
    
    # Check each mapping for conflicts
    for mapping in mappings['mappings']:
        # Find the actual PSD layer
        psd_layer = next(
            (l for l in psd_data['layers'] if l['name'] == mapping['psd_layer']),
            None
        )
        
        if not psd_layer:
            continue
        
        # Check text conflicts
        if mapping['type'] == 'text':
            conflicts.extend(_check_text_conflicts(psd_layer, mapping))
        
        # Check image conflicts
        elif mapping['type'] == 'image':
            conflicts.extend(_check_image_conflicts(psd_layer, mapping, main_comp))
    
    # Check dimension mismatch
    if main_comp:
        dimension_conflicts = _check_dimension_mismatch(psd_data, main_comp)
        conflicts.extend(dimension_conflicts)
    
    # Generate summary
    summary = {
        "total_conflicts": len(conflicts),
        "critical": sum(1 for c in conflicts if c['severity'] == 'critical'),
        "warnings": sum(1 for c in conflicts if c['severity'] == 'warning'),
        "info": sum(1 for c in conflicts if c['severity'] == 'info')
    }
    
    return {
        "conflicts": conflicts,
        "summary": summary
    }


def _check_text_conflicts(psd_layer: Dict[str, Any], mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check for text-related conflicts."""
    conflicts = []
    
    # Get text content if available
    text_content = ""
    if 'text' in psd_layer and 'content' in psd_layer['text']:
        text_content = psd_layer['text']['content']
    
    if not text_content:
        return conflicts
    
    text_length = len(text_content)
    
    # Critical: Text too long (likely overflow)
    if text_length > 100:
        conflicts.append({
            "type": "text_overflow",
            "severity": "critical",
            "mapping": mapping,
            "issue": f"Text is very long ({text_length} chars). Likely to overflow placeholder.",
            "suggestion": f"Consider shortening text to under 100 characters. Current: \"{text_content[:50]}...\""
        })
    
    # Warning: Text moderately long
    elif text_length > 50:
        conflicts.append({
            "type": "text_overflow",
            "severity": "warning",
            "mapping": mapping,
            "issue": f"Text is moderately long ({text_length} chars). May overflow depending on font size.",
            "suggestion": f"Monitor text length. Consider shortening if overflow occurs."
        })
    
    # Check font size if available
    if 'text' in psd_layer and 'font_size' in psd_layer['text']:
        font_size = psd_layer['text']['font_size']
        
        # Warning: Large font size
        if font_size > 72:
            conflicts.append({
                "type": "font_size",
                "severity": "warning",
                "mapping": mapping,
                "issue": f"Large font size ({font_size}pt) may not fit in template placeholder.",
                "suggestion": "Verify placeholder can accommodate large text or reduce font size in PSD."
            })
        
        # Info: Very small font size
        elif font_size < 12:
            conflicts.append({
                "type": "font_size",
                "severity": "info",
                "mapping": mapping,
                "issue": f"Small font size ({font_size}pt) may be hard to read.",
                "suggestion": "Consider increasing font size for better readability."
            })
    
    return conflicts


def _check_image_conflicts(psd_layer: Dict[str, Any], mapping: Dict[str, Any], 
                           main_comp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check for image-related conflicts."""
    conflicts = []
    
    if not main_comp:
        return conflicts
    
    psd_width = psd_layer.get('width', 0)
    psd_height = psd_layer.get('height', 0)
    comp_width = main_comp.get('width', 1920)
    comp_height = main_comp.get('height', 1080)
    
    # Calculate aspect ratios
    psd_aspect = psd_width / psd_height if psd_height > 0 else 0
    comp_aspect = comp_width / comp_height if comp_height > 0 else 0
    
    # Check aspect ratio mismatch
    if psd_aspect > 0 and comp_aspect > 0:
        aspect_diff = abs(psd_aspect - comp_aspect) / comp_aspect
        
        if aspect_diff > 0.2:  # More than 20% difference
            conflicts.append({
                "type": "aspect_ratio",
                "severity": "warning",
                "mapping": mapping,
                "issue": f"Aspect ratio mismatch. PSD: {psd_aspect:.2f}, Template: {comp_aspect:.2f}",
                "suggestion": "Image will be cropped or letterboxed. Adjust PSD dimensions or use object-fit options."
            })
    
    # Check if image is too small (upscaling required)
    if psd_width < comp_width * 0.5 or psd_height < comp_height * 0.5:
        scale_factor = max(comp_width / psd_width, comp_height / psd_height)
        conflicts.append({
            "type": "size_mismatch",
            "severity": "warning",
            "mapping": mapping,
            "issue": f"Image is small ({psd_width}×{psd_height}). Will be upscaled {scale_factor:.1f}x. May look pixelated.",
            "suggestion": f"Use higher resolution image (recommended: at least {comp_width//2}×{comp_height//2})."
        })
    
    # Info: Image is much larger (downscaling)
    elif psd_width > comp_width * 2 or psd_height > comp_height * 2:
        conflicts.append({
            "type": "size_mismatch",
            "severity": "info",
            "mapping": mapping,
            "issue": f"Image is large ({psd_width}×{psd_height}). Will be downscaled from {comp_width}×{comp_height}.",
            "suggestion": "Downscaling is fine. Consider optimizing file size if performance is a concern."
        })
    
    return conflicts


def _check_dimension_mismatch(psd_data: Dict[str, Any], 
                               main_comp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check for PSD to template dimension mismatches."""
    conflicts = []
    
    psd_width = psd_data.get('width', 0)
    psd_height = psd_data.get('height', 0)
    comp_width = main_comp.get('width', 1920)
    comp_height = main_comp.get('height', 1080)
    
    # Calculate aspect ratios
    psd_aspect = psd_width / psd_height if psd_height > 0 else 0
    comp_aspect = comp_width / comp_height if comp_height > 0 else 0
    
    # Check if dimensions don't match
    if psd_width != comp_width or psd_height != comp_height:
        aspect_diff = abs(psd_aspect - comp_aspect) / comp_aspect if comp_aspect > 0 else 0
        
        severity = "warning" if aspect_diff > 0.1 else "info"
        
        conflicts.append({
            "type": "dimension_mismatch",
            "severity": severity,
            "mapping": {"psd_layer": "Document", "aepx_placeholder": "Composition"},
            "issue": f"PSD ({psd_width}×{psd_height}) differs from template ({comp_width}×{comp_height}).",
            "suggestion": "Content will be scaled/repositioned. Verify layout after import."
        })
    
    return conflicts
