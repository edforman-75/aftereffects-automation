"""
Expression Generator

Generates JavaScript expressions for After Effects layers to link them to Hard Card variables.
After Effects expressions are JavaScript code that runs in the composition to make layers dynamic.

The Hard Card is a composition named "Hard_Card" containing text layers for each variable
(prefixed with 'z'). Other layers reference these variables via expressions.
"""

from dataclasses import dataclass
from typing import Optional, List
from modules.expression_system.variable_definitions import StandardVariables


@dataclass
class ExpressionConfig:
    """
    Configuration for expression generation.

    Attributes:
        hard_card_comp_name: Name of the Hard Card composition (default: "Hard_Card")
        use_lowercase_comparison: Use toLowerCase() for string comparisons (default: True)
        add_error_handling: Add try-catch error handling to expressions (default: True)

    Example:
        >>> config = ExpressionConfig(
        ...     hard_card_comp_name="Hard_Card",
        ...     use_lowercase_comparison=True,
        ...     add_error_handling=True
        ... )
    """
    hard_card_comp_name: str = "Hard_Card"
    use_lowercase_comparison: bool = True
    add_error_handling: bool = True


class ExpressionGenerator:
    """
    Generates After Effects JavaScript expressions for parametrized templates.

    This class provides methods to generate common expression patterns for:
    - Text linking (simple and complex)
    - Conditional visibility
    - Logo and image scaling
    - Color conversion
    - Ranking displays
    - Number comparisons

    Usage:
        >>> generator = ExpressionGenerator()
        >>> expr = generator.simple_text_link(variable_name="homeTeamName")
        >>> print(expr)
        comp("Hard_Card").layer("zhomeTeamName").text.sourceText

    All generated expressions are valid After Effects JavaScript and can be directly
    applied to layer properties via the AEPX Expression Writer.
    """

    def __init__(self, config: Optional[ExpressionConfig] = None):
        """
        Initialize the expression generator.

        Args:
            config: Optional ExpressionConfig, uses defaults if not provided
        """
        self.config = config or ExpressionConfig()

    def _validate_variable(self, variable_name: str) -> None:
        """
        Validate that a variable name exists in StandardVariables.

        Args:
            variable_name: Variable name (with or without z prefix)

        Raises:
            ValueError: If variable does not exist

        Example:
            >>> generator._validate_variable("homeTeamName")  # OK
            >>> generator._validate_variable("invalidVar")  # Raises ValueError
        """
        if not StandardVariables.variable_exists(variable_name):
            raise ValueError(
                f"Variable '{variable_name}' not found in StandardVariables. "
                f"Use StandardVariables.get_variable_names() to see available variables."
            )

    def _add_z_prefix(self, variable_name: str) -> str:
        """
        Add z prefix to variable name if not already present.

        Args:
            variable_name: Variable name

        Returns:
            Variable name with z prefix

        Example:
            >>> generator._add_z_prefix("homeTeamName")
            'zhomeTeamName'
            >>> generator._add_z_prefix("zhomeTeamName")
            'zhomeTeamName'
        """
        return variable_name if variable_name.startswith('z') else f"z{variable_name}"

    def simple_text_link(
        self,
        layer_name: Optional[str] = None,
        variable_name: Optional[str] = None
    ) -> str:
        """
        Generate a simple text link expression that references a Hard Card variable.

        This is the most common expression type - it makes a text layer display
        the value from a Hard Card variable.

        Args:
            layer_name: If provided, uses thisLayer.name to dynamically reference variable
            variable_name: If provided, directly references this specific variable

        Returns:
            JavaScript expression string

        Raises:
            ValueError: If variable_name is provided but doesn't exist

        Example:
            >>> # Dynamic linking - layer name must match variable name
            >>> expr = generator.simple_text_link()
            >>> print(expr)
            comp("Hard_Card").layer("z" + thisLayer.name).text.sourceText

            >>> # Direct linking to specific variable
            >>> expr = generator.simple_text_link(variable_name="homeTeamName")
            >>> print(expr)
            comp("Hard_Card").layer("zhomeTeamName").text.sourceText

        After Effects Usage:
            Apply this expression to a text layer's "Source Text" property.
            The layer will display the value from the corresponding Hard Card variable.
        """
        if variable_name:
            self._validate_variable(variable_name)
            z_var_name = self._add_z_prefix(variable_name)
            return f'comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText'
        else:
            # Use thisLayer.name to dynamically reference the variable
            return f'comp("{self.config.hard_card_comp_name}").layer("z" + thisLayer.name).text.sourceText'

    def complex_text_concatenation(
        self,
        variables: List[str],
        separators: Optional[List[str]] = None
    ) -> str:
        """
        Generate expression for concatenating multiple Hard Card variables.

        Useful for creating composite text like "March 15, 2025" from separate
        eventMonth, eventDayOfTheMonth, and eventYear variables.

        Args:
            variables: List of variable names to concatenate
            separators: Optional list of separator strings between variables.
                       Must have len(variables)-1 separators. Defaults to single space.

        Returns:
            Multi-line JavaScript expression

        Raises:
            ValueError: If any variable doesn't exist or separator count is wrong

        Example:
            >>> # Create date string: "March 15, 2025"
            >>> expr = generator.complex_text_concatenation(
            ...     variables=["eventMonth", "eventDayOfTheMonth", "eventYear"],
            ...     separators=[" ", ", "]
            ... )
            >>> print(expr)
            // Concatenate multiple Hard Card variables
            var txt1 = comp("Hard_Card").layer("zeventMonth").text.sourceText;
            var txt2 = comp("Hard_Card").layer("zeventDayOfTheMonth").text.sourceText;
            var txt3 = comp("Hard_Card").layer("zeventYear").text.sourceText;
            txt1 + " " + txt2 + ", " + txt3

        After Effects Usage:
            Apply to a text layer's "Source Text" property to display combined text.
        """
        if not variables:
            raise ValueError("variables list cannot be empty")

        # Validate all variables
        for var in variables:
            self._validate_variable(var)

        # Set default separators
        if separators is None:
            separators = [" "] * (len(variables) - 1)

        # Validate separator count
        if len(separators) != len(variables) - 1:
            raise ValueError(
                f"separators must have {len(variables) - 1} elements "
                f"(one less than variables), got {len(separators)}"
            )

        # Build expression
        lines = ["// Concatenate multiple Hard Card variables"]

        # Declare variables
        for i, var in enumerate(variables, 1):
            z_var_name = self._add_z_prefix(var)
            lines.append(
                f'var txt{i} = comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText;'
            )

        # Build concatenation
        concat_parts = []
        for i in range(len(variables)):
            concat_parts.append(f"txt{i + 1}")
            if i < len(separators):
                concat_parts.append(f'"{separators[i]}"')

        lines.append(" + ".join(concat_parts))

        return "\n".join(lines)

    def conditional_visibility_text(
        self,
        variable_name: str,
        target_value: str,
        visible_when_match: bool = True
    ) -> str:
        """
        Generate opacity expression for conditional visibility based on text value.

        Shows/hides layer based on whether a Hard Card text variable matches a target value.
        Commonly used for state-based graphics (e.g., show "FINAL" badge only when
        statusText == "FINAL").

        Args:
            variable_name: Variable name to check
            target_value: Text value to compare against
            visible_when_match: If True, visible when match; if False, visible when no match

        Returns:
            JavaScript expression for opacity property

        Raises:
            ValueError: If variable doesn't exist

        Example:
            >>> # Show layer only when dropdownValue1 is "FINAL"
            >>> expr = generator.conditional_visibility_text(
            ...     variable_name="dropdownValue1",
            ...     target_value="FINAL",
            ...     visible_when_match=True
            ... )
            >>> print(expr)
            // Show/hide based on text value
            var text1 = comp("Hard_Card").layer("zdropdownValue1").text.sourceText;
            if (text1.toLowerCase() == "final") { 100; } else { 0; }

        After Effects Usage:
            Apply to a layer's "Opacity" property to conditionally show/hide it.
        """
        self._validate_variable(variable_name)
        z_var_name = self._add_z_prefix(variable_name)

        # Prepare comparison
        if self.config.use_lowercase_comparison:
            comparison = f'text1.toLowerCase() == "{target_value.lower()}"'
        else:
            comparison = f'text1 == "{target_value}"'

        # Determine visibility values
        if visible_when_match:
            visible_value = 100
            hidden_value = 0
        else:
            visible_value = 0
            hidden_value = 100

        expression = f'''// Show/hide based on text value
var text1 = comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText;
if ({comparison}) {{ {visible_value}; }} else {{ {hidden_value}; }}'''

        return expression

    def conditional_visibility_number(
        self,
        variable_name: str,
        target_value: int,
        visible_when_match: bool = True
    ) -> str:
        """
        Generate opacity expression for conditional visibility based on numeric value.

        Shows/hides layer based on whether a Hard Card numeric variable matches a target value.
        Uses parseInt to convert text to number.

        Args:
            variable_name: Variable name to check
            target_value: Numeric value to compare against
            visible_when_match: If True, visible when match; if False, visible when no match

        Returns:
            JavaScript expression for opacity property

        Raises:
            ValueError: If variable doesn't exist

        Example:
            >>> # Show layer only when additionalAwayTeamScore equals 3
            >>> expr = generator.conditional_visibility_number(
            ...     variable_name="additionalAwayTeamScore",
            ...     target_value=3,
            ...     visible_when_match=True
            ... )
            >>> print(expr)
            // Show/hide based on numeric value
            var value = parseInt(comp("Hard_Card").layer("zadditionalAwayTeamScore").text.sourceText);
            if (value == 3) { 100; } else { 0; }

        After Effects Usage:
            Apply to a layer's "Opacity" property to conditionally show/hide it.
        """
        self._validate_variable(variable_name)
        z_var_name = self._add_z_prefix(variable_name)

        # Determine visibility values
        if visible_when_match:
            visible_value = 100
            hidden_value = 0
        else:
            visible_value = 0
            hidden_value = 100

        expression = f'''// Show/hide based on numeric value
var value = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText);
if (value == {target_value}) {{ {visible_value}; }} else {{ {hidden_value}; }}'''

        return expression

    def logo_scaling_max_dimensions(self, max_width: int, max_height: int) -> str:
        """
        Generate scale expression to fit logo within maximum dimensions.

        Scales logo proportionally to fit within specified width/height while maintaining
        aspect ratio. Useful for standardizing logo sizes across templates.

        Args:
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels

        Returns:
            JavaScript expression for scale property

        Example:
            >>> # Scale logo to fit within 500x500
            >>> expr = generator.logo_scaling_max_dimensions(500, 500)
            >>> print(expr)
            // Scale logo to fit within max dimensions while maintaining aspect ratio
            var maxWidth = 500;
            var maxHeight = 500;
            var scaleWidth = (maxWidth / thisLayer.width) * 100;
            var scaleHeight = (maxHeight / thisLayer.height) * 100;
            var finalScale = Math.min(scaleWidth, scaleHeight);
            [finalScale, finalScale]

        After Effects Usage:
            Apply to a logo layer's "Scale" property to auto-fit within dimensions.
        """
        expression = f'''// Scale logo to fit within max dimensions while maintaining aspect ratio
var maxWidth = {max_width};
var maxHeight = {max_height};
var scaleWidth = (maxWidth / thisLayer.width) * 100;
var scaleHeight = (maxHeight / thisLayer.height) * 100;
var finalScale = Math.min(scaleWidth, scaleHeight);
[finalScale, finalScale]'''

        return expression

    def image_scaling_fill_comp(self, fill_mode: str = "min") -> str:
        """
        Generate scale expression to fill composition with image.

        Scales image to fill entire composition, either fitting inside (min) or
        covering completely (max).

        Args:
            fill_mode: Either "min" (fit inside, may have bars) or
                      "max" (cover completely, may crop)

        Returns:
            JavaScript expression for scale property

        Raises:
            ValueError: If fill_mode is not "min" or "max"

        Example:
            >>> # Scale image to fit within comp
            >>> expr = generator.image_scaling_fill_comp("min")
            >>> print(expr)
            // Scale image to fit composition
            var x = 100 * thisComp.width / thisLayer.width;
            var y = 100 * thisComp.height / thisLayer.height;
            var s = Math.min(x, y);
            [s, s]

            >>> # Scale image to cover comp
            >>> expr = generator.image_scaling_fill_comp("max")
            >>> print(expr)
            // Scale image to cover composition
            var x = 100 * thisComp.width / thisLayer.width;
            var y = 100 * thisComp.height / thisLayer.height;
            var s = Math.max(x, y);
            [s, s]

        After Effects Usage:
            Apply to an image layer's "Scale" property to auto-fill composition.
        """
        if fill_mode not in ("min", "max"):
            raise ValueError(f"fill_mode must be 'min' or 'max', got '{fill_mode}'")

        action = "fit" if fill_mode == "min" else "cover"

        expression = f'''// Scale image to {action} composition
var x = 100 * thisComp.width / thisLayer.width;
var y = 100 * thisComp.height / thisLayer.height;
var s = Math.{fill_mode}(x, y);
[s, s]'''

        return expression

    def hex_color_to_rgb(self, variable_name: str) -> str:
        """
        Generate expression to convert hex color code to RGB.

        Converts hex color code from Hard Card variable (e.g., "#FF0000") to RGB
        values that After Effects can use for fill colors, strokes, etc.

        Args:
            variable_name: Variable name containing hex color code

        Returns:
            JavaScript expression for color property

        Raises:
            ValueError: If variable doesn't exist

        Example:
            >>> expr = generator.hex_color_to_rgb("homeTeamColor1")
            >>> print(expr)
            // Convert hex color to RGB
            hexToRgb(comp("Hard_Card").layer("zhomeTeamColor1").text.sourceText)

        After Effects Usage:
            Apply to a layer's "Fill Color" or "Stroke Color" property.
            Note: hexToRgb() is a built-in After Effects function.
        """
        self._validate_variable(variable_name)
        z_var_name = self._add_z_prefix(variable_name)

        expression = f'''// Convert hex color to RGB
hexToRgb(comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText)'''

        return expression

    def ranking_display_conditional(self, variable_name: str) -> str:
        """
        Generate expression to display ranking with # prefix only if valid number.

        Shows "#15" if variable contains a number, blank if not. Useful for team
        rankings that may not always be present.

        Args:
            variable_name: Variable name containing ranking number

        Returns:
            JavaScript expression for text source

        Raises:
            ValueError: If variable doesn't exist

        Example:
            >>> expr = generator.ranking_display_conditional("homeTeamRank")
            >>> print(expr)
            // Display ranking with # prefix if number, blank otherwise
            var txt1 = comp("Hard_Card").layer("zhomeTeamRank").text.sourceText;
            if (!isNaN(txt1) && txt1 !== "") { "#" + txt1; } else { ""; }

        After Effects Usage:
            Apply to a text layer's "Source Text" property.
            If homeTeamRank = "15", displays "#15"
            If homeTeamRank = "", displays nothing
        """
        self._validate_variable(variable_name)
        z_var_name = self._add_z_prefix(variable_name)

        expression = f'''// Display ranking with # prefix if number, blank otherwise
var txt1 = comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText;
if (!isNaN(txt1) && txt1 !== "") {{ "#" + txt1; }} else {{ ""; }}'''

        return expression

    def ranking_with_parentheses(self, variable_name: str) -> str:
        """
        Generate expression to display ranking with (#) format only if valid number.

        Shows "(#15)" if variable contains a number, blank if not.

        Args:
            variable_name: Variable name containing ranking number

        Returns:
            JavaScript expression for text source

        Raises:
            ValueError: If variable doesn't exist

        Example:
            >>> expr = generator.ranking_with_parentheses("awayTeamRank")
            >>> print(expr)
            // Display ranking with (#) format if number, blank otherwise
            var txt1 = comp("Hard_Card").layer("zawayTeamRank").text.sourceText;
            if (!isNaN(txt1) && txt1 !== "") { "(#" + txt1 + ")"; } else { ""; }

        After Effects Usage:
            Apply to a text layer's "Source Text" property.
            If awayTeamRank = "7", displays "(#7)"
            If awayTeamRank = "", displays nothing
        """
        self._validate_variable(variable_name)
        z_var_name = self._add_z_prefix(variable_name)

        expression = f'''// Display ranking with (#) format if number, blank otherwise
var txt1 = comp("{self.config.hard_card_comp_name}").layer("{z_var_name}").text.sourceText;
if (!isNaN(txt1) && txt1 !== "") {{ "(#" + txt1 + ")"; }} else {{ ""; }}'''

        return expression

    def compare_two_numbers_greater(self, variable1: str, variable2: str) -> str:
        """
        Generate opacity expression based on comparing two numbers (greater than).

        Shows layer (opacity 100) if variable1 > variable2, hides (opacity 0) otherwise.
        Useful for highlighting winning scores, better stats, etc.

        Args:
            variable1: First variable name (numeric)
            variable2: Second variable name (numeric)

        Returns:
            JavaScript expression for opacity property

        Raises:
            ValueError: If either variable doesn't exist

        Example:
            >>> # Show layer if home score > away score
            >>> expr = generator.compare_two_numbers_greater(
            ...     "homeTeamScore1", "awayTeamScore1"
            ... )
            >>> print(expr)
            // Show if first number > second number
            var text1 = parseInt(comp("Hard_Card").layer("zhomeTeamScore1").text.sourceText);
            var text2 = parseInt(comp("Hard_Card").layer("zawayTeamScore1").text.sourceText);
            if (text1 > text2) { 100; } else { 0; }

        After Effects Usage:
            Apply to a layer's "Opacity" property to highlight winning score.
        """
        self._validate_variable(variable1)
        self._validate_variable(variable2)

        z_var_name1 = self._add_z_prefix(variable1)
        z_var_name2 = self._add_z_prefix(variable2)

        expression = f'''// Show if first number > second number
var text1 = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name1}").text.sourceText);
var text2 = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name2}").text.sourceText);
if (text1 > text2) {{ 100; }} else {{ 0; }}'''

        return expression

    def compare_two_numbers_less(self, variable1: str, variable2: str) -> str:
        """
        Generate opacity expression based on comparing two numbers (less than).

        Shows layer if variable1 < variable2, hides otherwise.

        Args:
            variable1: First variable name (numeric)
            variable2: Second variable name (numeric)

        Returns:
            JavaScript expression for opacity property

        Example:
            >>> expr = generator.compare_two_numbers_less(
            ...     "awayTeamScore", "homeTeamScore"
            ... )
        """
        self._validate_variable(variable1)
        self._validate_variable(variable2)

        z_var_name1 = self._add_z_prefix(variable1)
        z_var_name2 = self._add_z_prefix(variable2)

        expression = f'''// Show if first number < second number
var text1 = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name1}").text.sourceText);
var text2 = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name2}").text.sourceText);
if (text1 < text2) {{ 100; }} else {{ 0; }}'''

        return expression

    def compare_two_numbers_equal(self, variable1: str, variable2: str) -> str:
        """
        Generate opacity expression based on comparing two numbers (equal).

        Shows layer if variable1 == variable2, hides otherwise.

        Args:
            variable1: First variable name (numeric)
            variable2: Second variable name (numeric)

        Returns:
            JavaScript expression for opacity property

        Example:
            >>> expr = generator.compare_two_numbers_equal(
            ...     "homeTeamScore", "awayTeamScore"
            ... )
        """
        self._validate_variable(variable1)
        self._validate_variable(variable2)

        z_var_name1 = self._add_z_prefix(variable1)
        z_var_name2 = self._add_z_prefix(variable2)

        expression = f'''// Show if numbers are equal
var text1 = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name1}").text.sourceText);
var text2 = parseInt(comp("{self.config.hard_card_comp_name}").layer("{z_var_name2}").text.sourceText);
if (text1 == text2) {{ 100; }} else {{ 0; }}'''

        return expression
