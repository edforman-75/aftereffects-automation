"""
Module 3.1: Content-to-Slot Matcher

Intelligently maps PSD content to AEPX template placeholders.
"""

import re
from typing import Dict, List, Any, Tuple


def match_content_to_slots(psd_data: Dict[str, Any], aepx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Match PSD content layers to AEPX template placeholders.

    Args:
        psd_data: Parsed PSD data from Module 1.1
        aepx_data: Parsed AEPX data from Module 2.1

    Returns:
        Dictionary with mappings, unmapped layers, and unfilled placeholders
    """
    # Extract layers by type from PSD
    psd_text = [l for l in psd_data.get('layers', []) if l.get('type') == 'text']
    psd_text.sort(key=lambda l: l.get('bbox', {}).get('top', 0))  # Sort by position
    
    psd_images = [l for l in psd_data.get('layers', []) 
                  if l.get('type') in ('image', 'smartobject')]
    psd_images.sort(key=lambda l: l.get('width', 0) * l.get('height', 0), reverse=True)

    # Extract placeholders by type from AEPX
    text_ph = [p for p in aepx_data.get('placeholders', []) if p.get('type') == 'text']
    image_ph = [p for p in aepx_data.get('placeholders', []) if p.get('type') == 'image']

    # Perform matching
    mappings = []
    used_psd = set()
    used_ph = set()

    # Match text layers sequentially
    text_mappings, text_used_psd, text_used_ph = _match_text_layers(psd_text, text_ph)
    mappings.extend(text_mappings)
    used_psd.update(text_used_psd)
    used_ph.update(text_used_ph)

    # Match image layers by name similarity
    image_mappings, img_used_psd, img_used_ph = _match_image_layers(psd_images, image_ph)
    mappings.extend(image_mappings)
    used_psd.update(img_used_psd)
    used_ph.update(img_used_ph)

    # Track unmapped/unfilled
    all_psd_names = [l['name'] for l in psd_text + psd_images]
    all_ph_names = [p['name'] for p in text_ph + image_ph]

    return {
        "mappings": mappings,
        "unmapped_psd_layers": [n for n in all_psd_names if n not in used_psd],
        "unfilled_placeholders": [n for n in all_ph_names if n not in used_ph]
    }


def _match_text_layers(psd_layers: List[Dict], placeholders: List[Dict]) -> Tuple[List[Dict], set, set]:
    """Match text layers to text placeholders sequentially."""
    mappings = []
    used_psd = set()
    used_ph = set()
    
    # Sort placeholders by name for consistent ordering
    sorted_ph = sorted(placeholders, key=lambda p: p['name'])
    
    for i, psd_layer in enumerate(psd_layers):
        if i >= len(sorted_ph):
            break
            
        ph = sorted_ph[i]
        psd_name = psd_layer['name']
        ph_name = ph['name']
        
        # Calculate name similarity
        similarity = _name_similarity(psd_name, ph_name)
        
        # Sequential matches get high confidence
        confidence = 1.0 if i < 3 else 0.9
        if similarity > 0.5:
            confidence = min(1.0, confidence + 0.1)
        
        reason = f"Sequential match: {i+1}th text layer → {i+1}th text placeholder"
        if similarity > 0.3:
            reason += f" (name similarity: {similarity:.2f})"
        
        mappings.append({
            "psd_layer": psd_name,
            "aepx_placeholder": ph_name,
            "type": "text",
            "confidence": confidence,
            "reason": reason
        })
        
        used_psd.add(psd_name)
        used_ph.add(ph_name)
    
    return mappings, used_psd, used_ph


def _match_image_layers(psd_layers: List[Dict], placeholders: List[Dict]) -> Tuple[List[Dict], set, set]:
    """Match image/smartobject layers to image placeholders using name similarity."""
    mappings = []
    used_psd = set()
    used_ph = set()
    
    for ph in placeholders:
        ph_name = ph['name']
        best_match = None
        best_score = 0.0
        
        for psd_layer in psd_layers:
            psd_name = psd_layer['name']
            if psd_name in used_psd:
                continue
            
            # Calculate base similarity
            score = _name_similarity(psd_name, ph_name)
            
            # Semantic keyword matching for featured images
            if 'featured' in ph_name.lower() or 'image' in ph_name.lower():
                # Boost for content-focused keywords
                content_keywords = ['cutout', 'photo', 'portrait', 'person', 'player', 'subject']
                if any(kw in psd_name.lower() for kw in content_keywords):
                    score += 0.4
                
                # Smaller boost for smartobject type
                if psd_layer.get('type') == 'smartobject':
                    score += 0.15
                
                # Size boost (but less significant than keyword match)
                area = psd_layer.get('width', 0) * psd_layer.get('height', 0)
                if area > 500000:  # Large image
                    score += 0.05
            
            if score > best_score:
                best_score = score
                best_match = psd_layer
        
        if best_match and best_score > 0.3:
            psd_name = best_match['name']
            confidence = min(1.0, best_score)
            reason = f"Name similarity match (score: {best_score:.2f})"
            if best_match.get('type') == 'smartobject':
                reason += ", smartobject type"
            
            mappings.append({
                "psd_layer": psd_name,
                "aepx_placeholder": ph_name,
                "type": "image",
                "confidence": confidence,
                "reason": reason
            })
            
            used_psd.add(psd_name)
            used_ph.add(ph_name)
    
    return mappings, used_psd, used_ph


def _name_similarity(name1: str, name2: str) -> float:
    """Calculate Jaccard similarity between tokenized names."""
    tokens1 = set(_tokenize(name1.lower()))
    tokens2 = set(_tokenize(name2.lower()))
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    
    return len(intersection) / len(union) if union else 0.0


def _tokenize(name: str) -> List[str]:
    """Split name into tokens."""
    tokens = re.split(r'[\s_\-\.]+', name)
    return [t for t in tokens if t]
