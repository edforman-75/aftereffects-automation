# Expression System Module

Complete variable definitions and expression system for After Effects parametrized templates.

## Overview

This module provides standardized variable definitions, expression generation, and Hard Card composition management for After Effects automation.

## Components

### 1. Variable Definitions (`variable_definitions.py`)

**Status:** ✅ COMPLETE

Defines all 185 standardized variables used in After Effects Hard Card compositions.

#### Variables Breakdown:
- **Team Variables:** 10 (names, abbreviations, rankings, colors)
- **Score Variables:** 15 (final scores, period scores, additional scores)
- **Event Variables:** 10 (dates, times, venues, locations)
- **Player Variables:** 135 (9 fields × 15 players)
- **Template Control:** 6 (dropdown values, status, game type, network)
- **Media Variables:** 9 (images, logos)

#### Key Features:
- All variable names follow camelCase convention
- Hard Card names prefixed with 'z' (e.g., zhomeTeamName)
- Default values for testing and preview
- Categorized by type and purpose
- Query by name (with/without z prefix), category, or data type

#### Usage Example:
```python
from modules.expression_system.variable_definitions import (
    StandardVariables,
    VariableCategory
)

# Get all variables
all_vars = StandardVariables.get_all_variables()  # 185 total

# Find by name (both forms work)
var = StandardVariables.get_by_name("homeTeamName")
var = StandardVariables.get_by_name("zhomeTeamName")  # same result

# Get by category
team_vars = StandardVariables.get_by_category(VariableCategory.TEAM)

# Get by type
color_vars = StandardVariables.get_variables_by_type('color')

# Check existence
exists = StandardVariables.variable_exists("homeTeamName")

# Get summary
summary = StandardVariables.get_summary()
```

## Variable Naming Conventions

### In Hard Card Composition:
- All variables prefixed with 'z'
- Example: `zhomeTeamName`, `zplayer1FirstName`

### In Layer Names:
- No 'z' prefix
- Example: `homeTeamName`, `player1FirstName`

### Style Guide:
- Use camelCase for simple names: `homeTeamName`, `eventCity`
- Use underscores for complex composite fields: `EventMonth_EventDay_Bar_EventTime`
- Numbers are part of the name: `player1FirstName`, `player15Stats`

## Data Types

- **text**: String values (names, descriptions, status)
- **number**: Numeric values (scores, rankings, jersey numbers)
- **color**: Hex color codes (team colors)
- **image**: Image file paths (featured images)
- **logo**: Logo file paths (team and league logos)

## Variable Categories

### TEAM (10 variables)
Team information for home and away teams:
- Names and abbreviations
- Rankings
- Primary and secondary colors

### SCORE (15 variables)
Scoring information:
- Final scores (home/away)
- Period/quarter scores (1-5)
- Additional scores (sets won, etc.)
- Current period

### EVENT (10 variables)
Event details:
- Date components (month, day, year)
- Times (short and long format)
- Location (city, state, venue)
- Home/away indicator (vs/at)

### PLAYER (135 variables)
Player roster (15 players × 9 fields):
- Names (first, last, full)
- Jersey number
- Position
- Physical stats (height, weight)
- Year/class
- Statistics

### TEMPLATE_CONTROL (6 variables)
Template control values:
- Dropdown selections
- Status text (FINAL, LIVE, etc.)
- Game type
- Broadcast network

### MEDIA (9 variables)
Media assets:
- Featured images (1-3)
- Team logos (full color and single color)
- Opponent and league logos

## Testing

All tests passing ✓

```bash
python3 << 'EOF'
from modules.expression_system.variable_definitions import StandardVariables

# Run comprehensive tests
all_vars = StandardVariables.get_all_variables()
assert len(all_vars) == 185, "Should have 185 variables"

summary = StandardVariables.get_summary()
assert summary['total'] == 185
assert summary['by_category']['team'] == 10
assert summary['by_category']['score'] == 15
assert summary['by_category']['event'] == 10
assert summary['by_category']['player'] == 135
assert summary['by_category']['template_control'] == 6
assert summary['by_category']['media'] == 9

print("All tests passed ✓")
EOF
```

### 2. Expression Generator (`expression_generator.py`)

**Status:** ✅ COMPLETE

Generates After Effects JavaScript expressions for parametrized templates.

#### Expression Types:
- **Simple Text Link:** Direct variable reference
- **Complex Text Concatenation:** Combine multiple variables
- **Conditional Visibility (Text):** Show/hide based on text value
- **Conditional Visibility (Number):** Show/hide based on numeric value
- **Logo Scaling:** Auto-fit logos within dimensions
- **Image Scaling:** Fill or fit composition
- **Hex Color Conversion:** Convert hex codes to RGB
- **Ranking Display:** Show "#15" or blank
- **Number Comparisons:** Compare scores/values

#### Usage Example:
```python
from modules.expression_system import ExpressionGenerator

generator = ExpressionGenerator()

# Simple text link
expr = generator.simple_text_link(variable_name="homeTeamName")
# Result: comp("Hard_Card").layer("zhomeTeamName").text.sourceText

# Complex concatenation
expr = generator.complex_text_concatenation(
    variables=["eventMonth", "eventDayOfTheMonth", "eventYear"],
    separators=[" ", ", "]
)
# Result: Multi-line expression combining date parts

# Conditional visibility
expr = generator.conditional_visibility_text("statusText", "FINAL", True)
# Result: Show layer when statusText == "FINAL"

# Logo scaling
expr = generator.logo_scaling_max_dimensions(500, 500)
# Result: Scale logo to fit within 500x500

# Number comparison
expr = generator.compare_two_numbers_greater("homeTeamScore", "awayTeamScore")
# Result: Show if home score > away score
```

All expressions:
- Are valid After Effects JavaScript
- Include comments explaining purpose
- Validate variable names against StandardVariables
- Support custom configuration (comp name, comparison options)

### 3. Hard Card Generator (`hard_card_generator.py`)

**Status:** ✅ COMPLETE

Generates the Hard_Card composition containing all 185 variable text layers in a grid layout.

#### Features:
- Grid layout system (configurable columns, spacing)
- Dictionary output (Python dict)
- AEPX XML output (valid XML for After Effects)
- Validation (checks names, positions, properties)
- Variable list export (text documentation)

#### Usage:
```python
from modules.expression_system import HardCardGenerator
generator = HardCardGenerator(logger)

# Generate as dictionary
hard_card = generator.generate_hard_card_dict()

# Generate as AEPX XML
xml = generator.generate_hard_card_aepx()

# Validate
result = generator.validate_hard_card(hard_card)

# Export documentation
generator.export_variable_list(hard_card, 'variables.txt')
```

All tests passing ✓

### 4. AEPX Expression Writer (`aepx_expression_writer.py`)

**Status:** ✅ COMPLETE

Modifies AEPX XML files to add expressions to layer properties.

#### Features:
- Parse and modify AEPX project files
- Add expressions to any layer property (text, opacity, scale, position, color, rotation, anchor point)
- Batch add multiple expressions
- Remove expressions from layers
- Validate expression syntax (balanced braces, parentheses, quotes)
- Find all layers with expressions
- Export expressions to JSON for debugging
- Handle XML namespaces correctly
- Save modified projects or export to string

#### Usage Example:
```python
from modules.expression_system import (
    AEPXExpressionWriter,
    ExpressionTarget,
    LayerExpression
)

# Load AEPX file
writer = AEPXExpressionWriter(logger, aepx_path="project.aepx")

# Add expression to layer
result = writer.add_expression_to_layer(
    comp_name="Main_Comp",
    layer_name="homeTeamName",
    target=ExpressionTarget.TEXT_SOURCE,
    expression='comp("Hard_Card").layer("zhomeTeamName").text.sourceText'
)

# Find all layers with expressions
find_result = writer.find_layers_with_expressions()
for layer_info in find_result.get_data()['layers']:
    print(f"{layer_info['comp']}/{layer_info['layer']}: {layer_info['expression']}")

# Save modified project
writer.save_to_file("project_modified.aepx")
```

All tests passing ✓ (31/31 tests)

### 5. Expression Applier Service (`services/expression_applier_service.py`)

**Status:** ✅ COMPLETE

Intelligently analyzes AEPX projects and recommends expressions based on layer name pattern matching, layer types, and confidence scoring.

#### Features:
- **Pattern Matching**: Exact, fuzzy, and regex-based layer name matching
- **Confidence Scoring**: 5-level confidence system (Exact, High, Good, Medium, Low)
- **Layer Type Detection**: Automatically detects text, shape, image, video layers
- **Smart Expression Selection**: Chooses appropriate expressions based on context
- **Batch Analysis**: Analyze entire projects at once
- **Filtering & Grouping**: Filter by confidence, layer type, composition
- **Pattern Types Supported**:
  - Team variables (homeTeamName, awayTeamAbbreviation, etc.)
  - Scores (homeTeamScore, awayTeamScore, period scores)
  - Event data (eventCity, eventDate, eventVenue, etc.)
  - Player sequences (player1FirstName through player15Stats)
  - Status indicators (FINAL, LIVE badges)
  - Logos and images with auto-scaling
  - Color conversions

#### Usage Example:
```python
from services.expression_applier_service import ExpressionApplierService

service = ExpressionApplierService(logger)

# Analyze project and get recommendations
result = service.analyze_project(aepx_path="project.aepx", min_confidence=0.75)
recommendations = result.get_data()['recommendations']

# Review recommendations
for rec in recommendations:
    print(f"{rec.layer_name} -> {rec.variable_name} ({rec.confidence:.0%})")
    print(f"  Reason: {rec.reason}")
    print(f"  Expression: {rec.expression[:60]}...")

# Filter high-confidence recommendations
high_confidence = service.filter_recommendations(
    recommendations,
    min_confidence=0.9
)

# Group by confidence level
groups = service.group_by_confidence(recommendations)
print(f"Exact matches: {len(groups['exact'])}")
print(f"High confidence: {len(groups['high'])}")

# Convert to LayerExpression for AEPX writer
from modules.expression_system import AEPXExpressionWriter

writer = AEPXExpressionWriter(logger, aepx_path="project.aepx")
for rec in high_confidence:
    layer_expr = rec.to_layer_expression()
    writer.add_expression_to_layer(
        comp_name=layer_expr.comp_name,
        layer_name=layer_expr.layer_name,
        target=layer_expr.target,
        expression=layer_expr.expression
    )

writer.save_to_file("project_with_expressions.aepx")
```

#### Matching Strategy:
1. **Exact Match** (confidence: 1.0): Layer name exactly matches variable name
2. **Pattern Match** (confidence: 0.8-1.0): Matches regex patterns for common naming conventions
3. **Fuzzy Match** (confidence: 0.4-0.9): Similar names using character-based similarity

#### Example Matches:
- `homeTeamName` → homeTeamName (exact, 100%)
- `home_team_name` → homeTeamName (pattern, 90%)
- `homeTeamNam` → homeTeamName (fuzzy, 90%)
- `player1FirstName` → player1FirstName (exact, 100%)
- `p1_first_name` → player1FirstName (pattern, 90%)

All tests passing ✓ (33/35 tests, 94%)

## Next Components

### 6. Variable Name Mapper (Planned)
Will map arbitrary PSD layer names to standard variable names.

## Integration

Import from the module:

```python
from modules.expression_system import (
    VariableCategory,
    VariableDefinition,
    StandardVariables
)
```

## File Structure

```
modules/expression_system/
├── __init__.py                    # Module exports
├── variable_definitions.py         # ✅ Variable definitions (COMPLETE)
├── expression_generator.py         # ✅ Expression generation (COMPLETE)
├── hard_card_generator.py          # ✅ Hard Card composition generation (COMPLETE)
├── aepx_expression_writer.py      # ✅ AEPX modification (COMPLETE)
└── README.md                       # This file
```

## License

Part of the After Effects Automation System.
