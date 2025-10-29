"""
Module 3.1b: ML-Enhanced Content Matcher

Upgrades content matching with semantic embeddings for better name similarity.
Falls back to rule-based matching if ML is unavailable.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from .content_matcher import match_content_to_slots

# Try to import sentence transformers
_MODEL_CACHE = None
_ML_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    _ML_AVAILABLE = True
except ImportError:
    _ML_AVAILABLE = False
    print("Warning: sentence-transformers not available. Using rule-based matching.")


def _get_model() -> Optional[Any]:
    """Get or load the sentence transformer model."""
    global _MODEL_CACHE, _ML_AVAILABLE
    if not _ML_AVAILABLE:
        return None
    if _MODEL_CACHE is None:
        try:
            _MODEL_CACHE = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Failed to load model: {e}")
            _ML_AVAILABLE = False
            return None
    return _MODEL_CACHE


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
    return float(dot_product / (norm1 * norm2)) if norm1 > 0 and norm2 > 0 else 0.0


def _semantic_similarity(text1: str, text2: str, model: Any) -> float:
    """Calculate semantic similarity between two text strings."""
    try:
        embeddings = model.encode([text1, text2])
        similarity = _cosine_similarity(embeddings[0], embeddings[1])
        return max(0.0, min(1.0, similarity))
    except Exception as e:
        print(f"Warning: Semantic similarity failed: {e}")
        return 0.0


def _calculate_size_score(psd_layer: Dict, target_dimensions: Tuple[int, int]) -> float:
    """Calculate size-based heuristic score."""
    psd_w, psd_h = psd_layer.get('width', 0), psd_layer.get('height', 0)
    target_w, target_h = target_dimensions
    if psd_w == 0 or psd_h == 0 or target_w == 0 or target_h == 0:
        return 0.0
    psd_area, target_area = psd_w * psd_h, target_w * target_h
    area_ratio = min(psd_area, target_area) / max(psd_area, target_area)
    return area_ratio * 0.3


def _calculate_keyword_score(layer_name: str, layer_type: str) -> float:
    """Calculate score based on content-related keywords."""
    name_lower = layer_name.lower()
    content_keywords = ['cutout', 'photo', 'portrait', 'person', 'player', 'subject', 'feature']
    decorative_keywords = ['background', 'bg', 'texture', 'pattern', 'shape']

    for keyword in content_keywords:
        if keyword in name_lower:
            return 0.4
    for keyword in decorative_keywords:
        if keyword in name_lower:
            return -0.2
    if layer_type == 'smartobject':
        return 0.15
    return 0.0


def _ml_match_images(psd_layers: List[Dict], placeholders: List[Dict],
                     comp_dimensions: Tuple[int, int], model: Any) -> List[Dict]:
    """Match image layers using ML semantic similarity."""
    image_layers = [l for l in psd_layers if l['type'] in ('smartobject', 'image')]
    image_placeholders = [p for p in placeholders if p['type'] == 'image']

    if not image_layers or not image_placeholders:
        return []

    layer_names = [layer['name'] for layer in image_layers]
    placeholder_names = [p['name'] for p in image_placeholders]

    try:
        layer_embeddings = model.encode(layer_names)
        placeholder_embeddings = model.encode(placeholder_names)
    except Exception as e:
        print(f"Warning: Failed to generate embeddings: {e}")
        return []

    matches = []
    matched_layers = set()
    matched_placeholders = set()

    for p_idx, placeholder in enumerate(image_placeholders):
        if p_idx in matched_placeholders:
            continue

        best_score, best_layer_idx = 0.0, None

        for l_idx, layer in enumerate(image_layers):
            if l_idx in matched_layers:
                continue

            semantic_score = _cosine_similarity(layer_embeddings[l_idx], placeholder_embeddings[p_idx])
            size_score = _calculate_size_score(layer, comp_dimensions)
            keyword_score = _calculate_keyword_score(layer['name'], layer['type'])
            combined_score = (semantic_score * 0.4) + keyword_score + (size_score * 0.2)

            if combined_score > best_score:
                best_score = combined_score
                best_layer_idx = l_idx

        if best_layer_idx is not None and best_score >= 0.3:
            layer = image_layers[best_layer_idx]
            matches.append({
                'psd_layer': layer['name'],
                'aepx_placeholder': placeholder['name'],
                'type': 'image',
                'confidence': best_score,
                'reason': f'ML semantic match (score: {best_score:.2f})'
            })
            matched_layers.add(best_layer_idx)
            matched_placeholders.add(p_idx)

    return matches


def _match_text_sequential(psd_layers: List[Dict], placeholders: List[Dict],
                           model: Optional[Any]) -> List[Dict]:
    """Match text layers sequentially with optional ML confidence boost."""
    text_layers = [l for l in psd_layers if l['type'] == 'text']
    text_placeholders = [p for p in placeholders if p['type'] == 'text']

    if not text_layers or not text_placeholders:
        return []

    text_layers_sorted = sorted(text_layers, key=lambda l: l.get('y', 0))
    matches = []

    for i, layer in enumerate(text_layers_sorted):
        if i < len(text_placeholders):
            placeholder = text_placeholders[i]
            confidence = 1.0

            if model is not None:
                try:
                    semantic_sim = _semantic_similarity(layer['name'], placeholder['name'], model)
                    if semantic_sim < 0.5:
                        confidence = 0.95
                except:
                    pass

            matches.append({
                'psd_layer': layer['name'],
                'aepx_placeholder': placeholder['name'],
                'type': 'text',
                'confidence': confidence,
                'reason': 'Sequential text match (position-based)'
            })

    return matches


def match_content_to_slots_ml(psd_data: Dict[str, Any], aepx_data: Dict[str, Any],
                               use_ml: bool = True) -> Dict[str, Any]:
    """
    Match PSD layers to AEPX placeholders using ML-enhanced semantic matching.

    Args:
        psd_data: Parsed PSD data from Module 1.1
        aepx_data: Parsed AEPX data from Module 2.1
        use_ml: Whether to use ML enhancement (default: True)

    Returns:
        Dictionary with mappings, unmapped_psd_layers, unfilled_placeholders
    """
    if not use_ml or not _ML_AVAILABLE:
        return match_content_to_slots(psd_data, aepx_data)

    model = _get_model()
    if model is None:
        return match_content_to_slots(psd_data, aepx_data)

    try:
        # Get main composition dimensions
        main_comp = next((c for c in aepx_data['compositions']
                         if c['name'] == aepx_data['composition_name']), None)
        if main_comp is None and aepx_data['compositions']:
            main_comp = aepx_data['compositions'][0]

        comp_dimensions = (
            main_comp.get('width', 1920) if main_comp else 1920,
            main_comp.get('height', 1080) if main_comp else 1080
        )

        placeholders = aepx_data['placeholders']
        text_matches = _match_text_sequential(psd_data['layers'], placeholders, model)
        image_matches = _ml_match_images(psd_data['layers'], placeholders, comp_dimensions, model)
        all_matches = text_matches + image_matches

        mapped_psd_layers = {m['psd_layer'] for m in all_matches}
        filled_placeholders = {m['aepx_placeholder'] for m in all_matches}
        unmapped = [l['name'] for l in psd_data['layers'] if l['name'] not in mapped_psd_layers]
        unfilled = [p['name'] for p in placeholders if p['name'] not in filled_placeholders]

        return {
            'mappings': all_matches,
            'unmapped_psd_layers': unmapped,
            'unfilled_placeholders': unfilled
        }

    except Exception as e:
        print(f"Warning: ML matching failed: {e}")
        print("Falling back to rule-based matcher")
        return match_content_to_slots(psd_data, aepx_data)
