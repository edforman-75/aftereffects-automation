# Aspect Ratio Handler

Conservative aspect ratio handling system with human oversight and learning capabilities for PSD → AEPX transformations.

## Overview

The Aspect Ratio Handler addresses aspect ratio mismatches between PSD source files and After Effects templates. It provides:

- **Conservative Classification**: Categorizes compositions as Portrait, Square, or Landscape
- **Safe Auto-Transformations**: Only applies transformations for same-category, low-risk scenarios
- **Human Oversight**: Flags risky transformations for manual review
- **Learning System**: Learns from human decisions to improve recommendations over time

## Key Philosophy

This system is **deliberately conservative**. It will:
- ✅ Auto-apply only when safe (same category, <10% difference)
- ✅ Ask for human guidance when unsure
- ✅ Never attempt "heroic" transformations
- ✅ Learn from human decisions over time

## Quick Start

```python
from modules.aspect_ratio import AspectRatioHandler, TransformationType
import logging

# Setup
logger = logging.getLogger('my_app')
handler = AspectRatioHandler(logger)

# Analyze mismatch
decision = handler.analyze_mismatch(
    psd_width=1920,
    psd_height=1080,
    aepx_width=1920,
    aepx_height=1161
)

# Check if auto-apply is safe
if handler.can_auto_transform(decision):
    # Calculate transformation
    transform = handler.calculate_transform(
        1920, 1080,
        1920, 1161,
        method="fit"  # or "fill"
    )

    print(f"Scale: {transform['scale']}")
    print(f"Offset: ({transform['offset_x']}, {transform['offset_y']})")

else:
    # Present to human for review
    print(f"Reason: {decision.reasoning}")
    print(f"Recommended: {decision.recommended_action}")

    # Get human decision
    human_choice = get_human_input()  # Your UI

    # Record for learning
    handler.record_human_decision(
        (1920, 1080),
        (1920, 1161),
        decision.transformation_type.value,
        human_choice
    )
```

## Classification System

### Aspect Ratio Categories

| Category | Ratio Range | Examples |
|----------|-------------|----------|
| **Portrait** | < 0.9 | Instagram Story (1080×1920), Vertical Video |
| **Square** | 0.9 - 1.1 | Instagram Post (1080×1080), Square Video |
| **Landscape** | > 1.1 | HD Video (1920×1080), YouTube (16:9) |

### Transformation Types

| Type | Difference | Auto-Apply? | Description |
|------|------------|-------------|-------------|
| **NONE** | < 5% | ✅ Yes | Perfect or near-perfect match |
| **MINOR_SCALE** | 5-10% | ✅ Yes | Minor adjustment, safe to auto-apply |
| **MODERATE_ADJUST** | 10-20% | ❌ No | Noticeable change, needs approval |
| **HUMAN_REVIEW** | > 20% or cross-category | ❌ No | Significant difference, requires review |

## Decision Logic

```
┌─────────────────────────────────────────┐
│ Classify PSD & AEPX                     │
│ (Portrait, Square, or Landscape)        │
└────────────┬────────────────────────────┘
             │
             ▼
        ┌─────────┐
        │Same     │ No  ┌──────────────────────┐
        │Category?│────▶│HUMAN_REVIEW          │
        └────┬────┘     │(Cross-category risk) │
             │ Yes      └──────────────────────┘
             ▼
    ┌────────────────┐
    │Calculate       │
    │Ratio Difference│
    └────┬───────────┘
         │
         ├─▶ <5%  ────▶ NONE (auto-apply)
         │
         ├─▶ 5-10% ───▶ MINOR_SCALE (auto-apply)
         │
         ├─▶ 10-20% ──▶ MODERATE_ADJUST (human review)
         │
         └─▶ >20% ────▶ HUMAN_REVIEW (manual review)
```

## API Reference

### AspectRatioClassifier

Static methods for classification and ratio analysis.

#### `classify(width: int, height: int) -> AspectRatioCategory`

Classify composition as portrait, square, or landscape.

```python
from modules.aspect_ratio import AspectRatioClassifier

category = AspectRatioClassifier.classify(1920, 1080)
# Returns: AspectRatioCategory.LANDSCAPE
```

#### `get_ratio_difference(psd_w, psd_h, aepx_w, aepx_h) -> float`

Calculate percentage difference between aspect ratios.

```python
diff = AspectRatioClassifier.get_ratio_difference(
    1920, 1080,  # PSD
    1920, 1161   # AEPX
)
# Returns: 0.070 (7% difference)
```

### AspectRatioHandler

Main handler class for decision-making and transformations.

#### `analyze_mismatch(psd_w, psd_h, aepx_w, aepx_h) -> AspectRatioDecision`

Analyze aspect ratio mismatch and recommend action.

```python
decision = handler.analyze_mismatch(1920, 1080, 1920, 1161)

print(decision.transformation_type)  # TransformationType.MINOR_SCALE
print(decision.can_auto_apply)       # True
print(decision.confidence)            # 0.85
print(decision.reasoning)             # Detailed explanation
```

**Returns**: `AspectRatioDecision` with:
- `psd_category`, `aepx_category`: Aspect ratio categories
- `psd_dimensions`, `aepx_dimensions`: Original dimensions
- `transformation_type`: Type of transformation needed
- `ratio_difference`: Percentage difference (0.0-1.0)
- `recommended_action`: Human-readable recommendation
- `confidence`: Confidence score (0.0-1.0)
- `reasoning`: Detailed explanation
- `can_auto_apply`: Whether safe to auto-apply

#### `can_auto_transform(decision: AspectRatioDecision) -> bool`

Determine if transformation can be applied automatically.

```python
if handler.can_auto_transform(decision):
    # Proceed automatically
    transform = handler.calculate_transform(...)
else:
    # Present to human
    show_review_ui(decision)
```

#### `calculate_transform(psd_w, psd_h, aepx_w, aepx_h, method="fit") -> Dict`

Calculate transformation parameters.

**Methods**:
- `"fit"`: Scale to fit inside (letterbox/pillarbox)
- `"fill"`: Scale to fill completely (crop edges)

```python
transform = handler.calculate_transform(
    1920, 1080,
    1920, 1920,
    method="fit"
)

# Returns:
{
    'scale': 1.0,
    'offset_x': 0.0,
    'offset_y': 420.0,
    'method': 'fit',
    'new_width': 1920.0,
    'new_height': 1080.0,
    'bars': 'horizontal'  # letterbox bars
}
```

#### `record_human_decision(psd_dims, aepx_dims, ai_rec, human_choice)`

Record human decision for learning system.

**Human choices**:
- `"proceed"`: Accept AI recommendation
- `"skip"`: Skip this graphic
- `"manual_fix"`: Will fix manually in AE
- `"different_transform"`: Use different method

```python
handler.record_human_decision(
    psd_dims=(1920, 1080),
    aepx_dims=(1920, 1161),
    ai_recommendation="minor_scale",
    human_choice="proceed"
)
```

#### `get_learning_stats() -> Dict`

Analyze learning data to identify patterns.

```python
stats = handler.get_learning_stats()

print(f"Total decisions: {stats['total_decisions']}")
print(f"Auto-apply accuracy: {stats['auto_apply_accuracy']:.1%}")
print(f"Agreement rate: {stats['agreement_rate']:.1%}")

for category, data in stats['by_category'].items():
    print(f"{category}: {data['accuracy']:.1%} agreement")
```

#### `export_learning_data(filepath: str)`

Export learning data to JSON for analysis.

```python
handler.export_learning_data('learning_data.json')
```

## Usage Examples

### Example 1: Perfect Match (Auto-Apply)

```python
decision = handler.analyze_mismatch(1920, 1080, 3840, 2160)

# Same aspect ratio, different resolution
assert decision.transformation_type == TransformationType.NONE
assert decision.can_auto_apply == True
assert decision.confidence == 1.0

transform = handler.calculate_transform(1920, 1080, 3840, 2160)
# Simple 2x scale up, no letterboxing
```

### Example 2: Minor Difference (Auto-Apply)

```python
decision = handler.analyze_mismatch(1920, 1080, 1920, 1161)

# 7% difference, same category (landscape)
assert decision.transformation_type == TransformationType.MINOR_SCALE
assert decision.can_auto_apply == True
assert decision.confidence == 0.85

transform = handler.calculate_transform(1920, 1080, 1920, 1161, method="fit")
# Minor letterboxing, safe to auto-apply
```

### Example 3: Cross-Category (Human Review Required)

```python
decision = handler.analyze_mismatch(1920, 1080, 1080, 1920)

# Landscape → Portrait (cross-category)
assert decision.transformation_type == TransformationType.HUMAN_REVIEW
assert decision.can_auto_apply == False
assert decision.confidence == 0.0

# Present to user
print(decision.reasoning)
# "Cross-category transformation detected: landscape → portrait.
#  Automatic transformation may cause significant layout issues.
#  Human review required..."
```

### Example 4: Moderate Difference (Needs Approval)

```python
decision = handler.analyze_mismatch(1920, 1080, 1920, 1280)

# 15% difference, same category
assert decision.transformation_type == TransformationType.MODERATE_ADJUST
assert decision.can_auto_apply == False
assert decision.confidence == 0.60

# Show preview to user
preview = generate_preview(decision)
if user_approves(preview):
    transform = handler.calculate_transform(1920, 1080, 1920, 1280)
    handler.record_human_decision(
        (1920, 1080), (1920, 1280),
        "moderate", "proceed"
    )
```

## Integration with Project Workflow

```python
def process_graphic(psd_path, aepx_path):
    """Example integration into project workflow"""

    # Get dimensions
    psd_dims = get_psd_dimensions(psd_path)
    aepx_dims = get_aepx_dimensions(aepx_path)

    # Analyze mismatch
    decision = handler.analyze_mismatch(
        psd_dims[0], psd_dims[1],
        aepx_dims[0], aepx_dims[1]
    )

    # Log decision
    logger.info(
        f"Aspect ratio analysis: {decision.transformation_type.value}, "
        f"confidence: {decision.confidence:.1%}"
    )

    # Handle based on decision
    if handler.can_auto_transform(decision):
        # Auto-apply transformation
        transform = handler.calculate_transform(
            psd_dims[0], psd_dims[1],
            aepx_dims[0], aepx_dims[1],
            method="fit"
        )

        apply_transform_to_aepx(aepx_path, transform)

        return {
            'status': 'auto_transformed',
            'transform': transform,
            'decision': decision
        }

    else:
        # Requires human review
        return {
            'status': 'needs_review',
            'reason': decision.reasoning,
            'recommended_action': decision.recommended_action,
            'decision': decision
        }
```

## Learning System

The handler tracks human decisions to improve recommendations over time.

### Recording Decisions

```python
# After each human decision
handler.record_human_decision(
    psd_dims=(1920, 1080),
    aepx_dims=(1920, 1280),
    ai_recommendation="moderate",
    human_choice="proceed"  # or "skip", "manual_fix", "different_transform"
)
```

### Analyzing Patterns

```python
# Get statistics
stats = handler.get_learning_stats()

print(f"Total decisions recorded: {stats['total_decisions']}")
print(f"Auto-apply accuracy: {stats['auto_apply_accuracy']:.1%}")

# Common overrides (where human disagreed with AI)
for override in stats['common_overrides']:
    print(f"Override: {override['ai_recommendation']} → {override['human_choice']}")
    print(f"  PSD: {override['psd_category']}, AEPX: {override['aepx_category']}")
    print(f"  Difference: {override['ratio_difference']:.1%}")
```

### Exporting Data

```python
# Export for analysis
handler.export_learning_data('learning_data.json')

# JSON structure:
{
    "exported_at": "2025-01-26T10:30:00",
    "total_records": 45,
    "statistics": { ... },
    "decisions": [
        {
            "timestamp": "2025-01-26T10:15:00",
            "psd_dimensions": [1920, 1080],
            "aepx_dimensions": [1920, 1161],
            "psd_category": "landscape",
            "aepx_category": "landscape",
            "ratio_difference": 0.070,
            "ai_recommendation": "minor_scale",
            "human_choice": "proceed",
            "agreed": true
        },
        ...
    ]
}
```

## Testing

Run comprehensive test suite:

```bash
python3 test_aspect_ratio_handler.py
```

Tests cover:
- ✅ Aspect ratio classification (8 cases)
- ✅ Ratio difference calculation (6 cases)
- ✅ Mismatch analysis & decision making (7 cases)
- ✅ Transformation calculations (6 cases)
- ✅ Learning system recording & statistics
- ✅ Edge cases & error handling (5 cases)

## Best Practices

### 1. Always Check Auto-Apply

```python
if handler.can_auto_transform(decision):
    # Safe to proceed
else:
    # Requires human review
```

### 2. Provide Clear Reasoning to Users

```python
if not decision.can_auto_apply:
    show_ui_dialog(
        title="Manual Review Required",
        message=decision.reasoning,
        recommendation=decision.recommended_action,
        confidence=decision.confidence
    )
```

### 3. Record All Decisions

```python
# Even if user skips
handler.record_human_decision(
    psd_dims, aepx_dims,
    decision.transformation_type.value,
    "skip"  # User chose to skip
)
```

### 4. Review Learning Stats Periodically

```python
# Weekly review
stats = handler.get_learning_stats()

if stats['auto_apply_accuracy'] < 0.80:
    # Consider adjusting thresholds
    logger.warning("Auto-apply accuracy below 80%")
```

## Confidence Levels

| Confidence | Meaning | Typical Action |
|------------|---------|----------------|
| **1.0** | Perfect match | Auto-apply with no concerns |
| **0.85** | High confidence | Auto-apply, minor adjustments |
| **0.60** | Moderate | Show preview, get approval |
| **0.30** | Low | Warn user, detailed review needed |
| **0.0** | No confidence | Cross-category, manual handling |

## Common Scenarios

### Scenario: YouTube to Instagram Story
- PSD: 1920×1080 (landscape)
- AEPX: 1080×1920 (portrait)
- Result: **HUMAN_REVIEW** (cross-category)
- Confidence: 0.0

### Scenario: HD to 4K
- PSD: 1920×1080
- AEPX: 3840×2160
- Result: **NONE** (same ratio)
- Confidence: 1.0

### Scenario: 16:9 to 16:10
- PSD: 1920×1080
- AEPX: 1920×1200
- Result: **MODERATE_ADJUST** (10% diff)
- Confidence: 0.60

## Troubleshooting

### Issue: Too Many Human Reviews

**Problem**: System flags too many cases for review.

**Solution**: Review learning data to identify patterns:

```python
stats = handler.get_learning_stats()

# Check override patterns
for override in stats['common_overrides']:
    print(f"Frequent override: {override}")

# Consider adjusting thresholds if humans consistently
# approve certain types of transformations
```

### Issue: Unexpected Classifications

**Problem**: Composition classified incorrectly.

**Solution**: Verify dimensions and check boundary cases:

```python
# Check ratio
ratio = width / height
print(f"Ratio: {ratio}")

# Classification boundaries:
# Portrait: < 0.9
# Square: 0.9 - 1.1
# Landscape: > 1.1

# If ratio is 0.89, it's portrait
# If ratio is 1.09, it's square
```

## License

Part of After Effects Automation system.
