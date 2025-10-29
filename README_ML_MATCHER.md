# Module 3.1b: ML-Enhanced Content Matcher

## Overview

Upgrades the rule-based content matcher with semantic embeddings for better name similarity matching using the `sentence-transformers` library.

## Features

- **Semantic Understanding**: Uses 'all-MiniLM-L6-v2' model for semantic similarity
- **Hybrid Scoring**: Combines ML embeddings with keyword and size heuristics
- **Automatic Fallback**: Falls back to rule-based matcher if ML unavailable
- **Same Interface**: Drop-in replacement for `match_content_to_slots()`

## Installation

```bash
pip install sentence-transformers
```

## Usage

```python
from modules.phase3.ml_content_matcher import match_content_to_slots_ml

# ML-enhanced matching (default)
result = match_content_to_slots_ml(psd_data, aepx_data)

# Disable ML (use rule-based)
result = match_content_to_slots_ml(psd_data, aepx_data, use_ml=False)
```

## How It Works

### Text Layer Matching
- **Primary**: Sequential matching (top to bottom) - unchanged
- **Enhancement**: Semantic validation adjusts confidence
  - If semantic similarity < 0.5: confidence = 0.95
  - Otherwise: confidence = 1.0

### Image Layer Matching
- **Semantic Score** (40%): Cosine similarity of embeddings
- **Keyword Score** (40%): Boosts for content keywords
  - Content keywords: cutout, photo, portrait, person (+0.4)
  - Decorative keywords: background, bg, texture (-0.2)
  - Smartobjects: +0.15
- **Size Score** (20%): Area ratio similarity

**Final Score** = (Semantic × 0.4) + Keyword + (Size × 0.2)

**Threshold**: Minimum 0.3 to create match

## Comparison: Rule-Based vs ML-Enhanced

| Layer       | Placeholder      | Rule-Based | ML-Enhanced |
|-------------|------------------|------------|-------------|
| BEN FORMAN  | player1fullname  | 100%       | 95%         |
| ELOISE GRACE| player2fullname  | 100%       | 95%         |
| EMMA LOUISE | player3fullname  | 100%       | 95%         |
| cutout      | featuredimage1   | 60%        | 53%         |

## Key Insights

- ML provides semantic understanding of layer/placeholder names
- Content-focused layers are boosted over decorative ones
- Maintains same high-quality matches as rule-based
- Slightly more conservative confidence scores
- Automatically handles edge cases with fallback

## Testing

```bash
# Run ML matcher tests
python tests/test_ml_matcher.py

# Run demonstration
python demo_ml_matcher.py
```

## Performance

- **Model Size**: ~90MB (first download)
- **Model Load Time**: ~1-2 seconds (cached after first load)
- **Inference Time**: ~50-100ms per batch
- **Memory**: +200MB when model loaded

## Files

- `modules/phase3/ml_content_matcher.py` (229 lines)
- `tests/test_ml_matcher.py` (151 lines)
- `demo_ml_matcher.py` (134 lines)

## Model Details

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Type**: Sentence Transformer
- **Base**: MiniLM (Microsoft)
- **Embedding Size**: 384 dimensions
- **Performance**: Fast, lightweight, high quality
- **Use Case**: Semantic search and similarity
