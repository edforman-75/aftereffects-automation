"""
Variable Definitions System

Defines all standardized variables used in After Effects Hard Card compositions.
Variables follow naming conventions:
- In Hard Card: prefixed with 'z' (e.g., "zhomeTeamName")
- In layer names: no 'z' prefix (e.g., "homeTeamName")
- Use camelCase for simple names
- Use underscores for complex composite fields

Total Variables: 185
- Team: 10
- Score: 15
- Event: 10
- Player: 135 (9 fields × 15 players)
- Template Control: 6
- Media: 9
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict


class VariableCategory(Enum):
    """Categories for organizing Hard Card variables"""
    TEAM = "team"
    EVENT = "event"
    PLAYER = "player"
    TEMPLATE_CONTROL = "template_control"
    MEDIA = "media"
    SCORE = "score"


@dataclass
class VariableDefinition:
    """
    Definition of a Hard Card variable.

    Attributes:
        name: Variable name without z prefix (e.g., "homeTeamName")
        category: Variable category for organization
        data_type: Data type ('text', 'number', 'color', 'image', 'logo')
        description: Human-readable description of the variable's purpose
        default_value: Optional default value for testing/preview

    Example:
        >>> var = VariableDefinition(
        ...     name="homeTeamName",
        ...     category=VariableCategory.TEAM,
        ...     data_type="text",
        ...     description="Full name of the home team",
        ...     default_value="Lakers"
        ... )
        >>> var.hard_card_name
        'zhomeTeamName'
    """
    name: str
    category: VariableCategory
    data_type: str
    description: str
    default_value: Optional[str] = None

    @property
    def hard_card_name(self) -> str:
        """
        Returns the variable name with z prefix as used in Hard Card composition.

        Returns:
            Variable name with 'z' prefix

        Example:
            >>> var.name = "homeTeamName"
            >>> var.hard_card_name
            'zhomeTeamName'
        """
        return f"z{self.name}"


class StandardVariables:
    """
    Standard variable definitions for After Effects Hard Card compositions.

    Provides centralized definitions for all variables used across templates,
    ensuring consistency in naming, typing, and categorization.

    Usage:
        >>> # Get all variables
        >>> all_vars = StandardVariables.get_all_variables()
        >>> len(all_vars)
        185

        >>> # Find a specific variable
        >>> home_team = StandardVariables.get_by_name("homeTeamName")
        >>> home_team.default_value
        'Lakers'

        >>> # Get variables by category
        >>> team_vars = StandardVariables.get_by_category(VariableCategory.TEAM)
        >>> len(team_vars)
        10
    """

    # Team Variables (10 total)
    TEAM_VARS = [
        VariableDefinition(
            name="homeTeamName",
            category=VariableCategory.TEAM,
            data_type="text",
            description="Full name of the home team",
            default_value="Lakers"
        ),
        VariableDefinition(
            name="awayTeamName",
            category=VariableCategory.TEAM,
            data_type="text",
            description="Full name of the away team",
            default_value="Warriors"
        ),
        VariableDefinition(
            name="homeTeamAbbreviation",
            category=VariableCategory.TEAM,
            data_type="text",
            description="Home team abbreviation (2-4 characters)",
            default_value="LAL"
        ),
        VariableDefinition(
            name="awayTeamAbbreviation",
            category=VariableCategory.TEAM,
            data_type="text",
            description="Away team abbreviation (2-4 characters)",
            default_value="GSW"
        ),
        VariableDefinition(
            name="homeTeamRank",
            category=VariableCategory.TEAM,
            data_type="number",
            description="Home team ranking (1-25)",
            default_value="3"
        ),
        VariableDefinition(
            name="awayTeamRank",
            category=VariableCategory.TEAM,
            data_type="number",
            description="Away team ranking (1-25)",
            default_value="7"
        ),
        VariableDefinition(
            name="homeTeamColor1",
            category=VariableCategory.TEAM,
            data_type="color",
            description="Home team primary color (hex code)",
            default_value="#552583"
        ),
        VariableDefinition(
            name="awayTeamColor1",
            category=VariableCategory.TEAM,
            data_type="color",
            description="Away team primary color (hex code)",
            default_value="#1D428A"
        ),
        VariableDefinition(
            name="homeTeamColor2",
            category=VariableCategory.TEAM,
            data_type="color",
            description="Home team secondary color (hex code)",
            default_value="#FDB927"
        ),
        VariableDefinition(
            name="awayTeamColor2",
            category=VariableCategory.TEAM,
            data_type="color",
            description="Away team secondary color (hex code)",
            default_value="#FFC72C"
        ),
    ]

    # Score Variables (15 total)
    SCORE_VARS = [
        VariableDefinition(
            name="homeTeamScore",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Home team final score",
            default_value="102"
        ),
        VariableDefinition(
            name="awayTeamScore",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Away team final score",
            default_value="98"
        ),
        VariableDefinition(
            name="homeTeamScore1",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Home team score for period/set 1",
            default_value="25"
        ),
        VariableDefinition(
            name="awayTeamScore1",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Away team score for period/set 1",
            default_value="22"
        ),
        VariableDefinition(
            name="homeTeamScore2",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Home team score for period/set 2",
            default_value="28"
        ),
        VariableDefinition(
            name="awayTeamScore2",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Away team score for period/set 2",
            default_value="24"
        ),
        VariableDefinition(
            name="homeTeamScore3",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Home team score for period/set 3",
            default_value="24"
        ),
        VariableDefinition(
            name="awayTeamScore3",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Away team score for period/set 3",
            default_value="26"
        ),
        VariableDefinition(
            name="homeTeamScore4",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Home team score for period/set 4",
            default_value="25"
        ),
        VariableDefinition(
            name="awayTeamScore4",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Away team score for period/set 4",
            default_value="26"
        ),
        VariableDefinition(
            name="homeTeamScore5",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Home team score for period/set 5 (overtime/extra)",
            default_value="0"
        ),
        VariableDefinition(
            name="awayTeamScore5",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Away team score for period/set 5 (overtime/extra)",
            default_value="0"
        ),
        VariableDefinition(
            name="additionalHomeTeamScore",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Additional home team score (e.g., sets won in volleyball)",
            default_value="3"
        ),
        VariableDefinition(
            name="additionalAwayTeamScore",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Additional away team score (e.g., sets won in volleyball)",
            default_value="2"
        ),
        VariableDefinition(
            name="currentPeriod",
            category=VariableCategory.SCORE,
            data_type="number",
            description="Current period/quarter being played (1-5)",
            default_value="4"
        ),
    ]

    # Event Variables (10 total)
    EVENT_VARS = [
        VariableDefinition(
            name="eventMonth",
            category=VariableCategory.EVENT,
            data_type="text",
            description="Event month (e.g., 'March', 'MAR')",
            default_value="March"
        ),
        VariableDefinition(
            name="eventDayOfTheMonth",
            category=VariableCategory.EVENT,
            data_type="number",
            description="Day of the month (1-31)",
            default_value="15"
        ),
        VariableDefinition(
            name="eventYear",
            category=VariableCategory.EVENT,
            data_type="number",
            description="Event year (e.g., 2025)",
            default_value="2025"
        ),
        VariableDefinition(
            name="eventTimeShort",
            category=VariableCategory.EVENT,
            data_type="text",
            description="Event time in short format (e.g., '7:30 PM')",
            default_value="7:30 PM"
        ),
        VariableDefinition(
            name="eventTimeLong",
            category=VariableCategory.EVENT,
            data_type="text",
            description="Event time in long format (e.g., '7:30 PM EST')",
            default_value="7:30 PM EST"
        ),
        VariableDefinition(
            name="eventCity",
            category=VariableCategory.EVENT,
            data_type="text",
            description="City where event takes place",
            default_value="Los Angeles"
        ),
        VariableDefinition(
            name="eventStateAbbreviation",
            category=VariableCategory.EVENT,
            data_type="text",
            description="State abbreviation (e.g., 'CA')",
            default_value="CA"
        ),
        VariableDefinition(
            name="eventVenue",
            category=VariableCategory.EVENT,
            data_type="text",
            description="Venue name",
            default_value="Crypto.com Arena"
        ),
        VariableDefinition(
            name="eventDate",
            category=VariableCategory.EVENT,
            data_type="text",
            description="Full event date (e.g., 'March 15, 2025')",
            default_value="March 15, 2025"
        ),
        VariableDefinition(
            name="vsOrAt",
            category=VariableCategory.EVENT,
            data_type="text",
            description="'vs' for home game, 'at' for away game",
            default_value="vs"
        ),
    ]

    # Player Variables (135 total: 9 fields × 15 players)
    PLAYER_VARS = []
    for i in range(1, 16):
        PLAYER_VARS.extend([
            VariableDefinition(
                name=f"player{i}FirstName",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} first name",
                default_value=f"John"
            ),
            VariableDefinition(
                name=f"player{i}LastName",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} last name",
                default_value=f"Smith"
            ),
            VariableDefinition(
                name=f"player{i}FullName",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} full name",
                default_value=f"John Smith"
            ),
            VariableDefinition(
                name=f"player{i}Number",
                category=VariableCategory.PLAYER,
                data_type="number",
                description=f"Player {i} jersey number",
                default_value=str(i)
            ),
            VariableDefinition(
                name=f"player{i}Position",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} position",
                default_value="PG"
            ),
            VariableDefinition(
                name=f"player{i}Height",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} height",
                default_value="6-3"
            ),
            VariableDefinition(
                name=f"player{i}Weight",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} weight",
                default_value="185"
            ),
            VariableDefinition(
                name=f"player{i}Year",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} year/class",
                default_value="Junior"
            ),
            VariableDefinition(
                name=f"player{i}Stats",
                category=VariableCategory.PLAYER,
                data_type="text",
                description=f"Player {i} statistics",
                default_value="12 PPG, 5 APG"
            ),
        ])

    # Template Control Variables (6 total)
    TEMPLATE_VARS = [
        VariableDefinition(
            name="dropdownValue1",
            category=VariableCategory.TEMPLATE_CONTROL,
            data_type="text",
            description="Template dropdown control value 1",
            default_value="Option A"
        ),
        VariableDefinition(
            name="dropdownValue2",
            category=VariableCategory.TEMPLATE_CONTROL,
            data_type="text",
            description="Template dropdown control value 2",
            default_value="Option B"
        ),
        VariableDefinition(
            name="dropdownValue3",
            category=VariableCategory.TEMPLATE_CONTROL,
            data_type="text",
            description="Template dropdown control value 3",
            default_value="Option C"
        ),
        VariableDefinition(
            name="statusText",
            category=VariableCategory.TEMPLATE_CONTROL,
            data_type="text",
            description="Game status text (e.g., 'FINAL', 'LIVE', 'UPCOMING')",
            default_value="FINAL"
        ),
        VariableDefinition(
            name="gameType",
            category=VariableCategory.TEMPLATE_CONTROL,
            data_type="text",
            description="Type of game (e.g., 'Regular Season', 'Playoffs')",
            default_value="Regular Season"
        ),
        VariableDefinition(
            name="broadcastNetwork",
            category=VariableCategory.TEMPLATE_CONTROL,
            data_type="text",
            description="Broadcasting network name",
            default_value="ESPN"
        ),
    ]

    # Media Variables (9 total)
    MEDIA_VARS = [
        VariableDefinition(
            name="featuredImage1",
            category=VariableCategory.MEDIA,
            data_type="image",
            description="Featured image 1",
            default_value="image1.jpg"
        ),
        VariableDefinition(
            name="featuredImage2",
            category=VariableCategory.MEDIA,
            data_type="image",
            description="Featured image 2",
            default_value="image2.jpg"
        ),
        VariableDefinition(
            name="featuredImage3",
            category=VariableCategory.MEDIA,
            data_type="image",
            description="Featured image 3",
            default_value="image3.jpg"
        ),
        VariableDefinition(
            name="homeTeamLogo",
            category=VariableCategory.MEDIA,
            data_type="logo",
            description="Home team full-color logo",
            default_value="home_logo.png"
        ),
        VariableDefinition(
            name="awayTeamLogo",
            category=VariableCategory.MEDIA,
            data_type="logo",
            description="Away team full-color logo",
            default_value="away_logo.png"
        ),
        VariableDefinition(
            name="homeTeamLogoSingleColor",
            category=VariableCategory.MEDIA,
            data_type="logo",
            description="Home team single-color logo",
            default_value="home_logo_mono.png"
        ),
        VariableDefinition(
            name="awayTeamLogoSingleColor",
            category=VariableCategory.MEDIA,
            data_type="logo",
            description="Away team single-color logo",
            default_value="away_logo_mono.png"
        ),
        VariableDefinition(
            name="opponentLogo",
            category=VariableCategory.MEDIA,
            data_type="logo",
            description="Opponent team logo",
            default_value="opponent_logo.png"
        ),
        VariableDefinition(
            name="leagueLogo",
            category=VariableCategory.MEDIA,
            data_type="logo",
            description="League logo",
            default_value="league_logo.png"
        ),
    ]

    @classmethod
    def get_all_variables(cls) -> List[VariableDefinition]:
        """
        Get all defined variables across all categories.

        Returns:
            List of all VariableDefinition objects (185 total)

        Example:
            >>> all_vars = StandardVariables.get_all_variables()
            >>> len(all_vars)
            185
            >>> all_vars[0].name
            'homeTeamName'
        """
        return (
            cls.TEAM_VARS +
            cls.SCORE_VARS +
            cls.EVENT_VARS +
            cls.PLAYER_VARS +
            cls.TEMPLATE_VARS +
            cls.MEDIA_VARS
        )

    @classmethod
    def get_by_name(cls, name: str) -> Optional[VariableDefinition]:
        """
        Get a variable definition by name.

        Handles both forms:
        - Without z prefix: "homeTeamName"
        - With z prefix: "zhomeTeamName"

        Args:
            name: Variable name (with or without z prefix)

        Returns:
            VariableDefinition if found, None otherwise

        Example:
            >>> # Both forms work
            >>> var1 = StandardVariables.get_by_name("homeTeamName")
            >>> var2 = StandardVariables.get_by_name("zhomeTeamName")
            >>> var1.name == var2.name
            True
            >>> var1.name
            'homeTeamName'
        """
        # Remove z prefix if present
        search_name = name[1:] if name.startswith('z') else name

        for var in cls.get_all_variables():
            if var.name == search_name:
                return var

        return None

    @classmethod
    def get_by_category(cls, category: VariableCategory) -> List[VariableDefinition]:
        """
        Get all variables in a specific category.

        Args:
            category: VariableCategory enum value

        Returns:
            List of VariableDefinition objects in the category

        Example:
            >>> team_vars = StandardVariables.get_by_category(VariableCategory.TEAM)
            >>> len(team_vars)
            10
            >>> team_vars[0].category
            <VariableCategory.TEAM: 'team'>
        """
        return [var for var in cls.get_all_variables() if var.category == category]

    @classmethod
    def variable_exists(cls, name: str) -> bool:
        """
        Check if a variable exists.

        Args:
            name: Variable name (with or without z prefix)

        Returns:
            True if variable exists, False otherwise

        Example:
            >>> StandardVariables.variable_exists("homeTeamName")
            True
            >>> StandardVariables.variable_exists("zhomeTeamName")
            True
            >>> StandardVariables.variable_exists("nonexistent")
            False
        """
        return cls.get_by_name(name) is not None

    @classmethod
    def get_variable_names(cls, include_z_prefix: bool = False) -> List[str]:
        """
        Get list of all variable names.

        Args:
            include_z_prefix: If True, include z prefix; if False, use plain names

        Returns:
            List of variable names

        Example:
            >>> names = StandardVariables.get_variable_names()
            >>> "homeTeamName" in names
            True
            >>> "zhomeTeamName" in names
            False

            >>> names_with_z = StandardVariables.get_variable_names(include_z_prefix=True)
            >>> "zhomeTeamName" in names_with_z
            True
        """
        all_vars = cls.get_all_variables()
        if include_z_prefix:
            return [var.hard_card_name for var in all_vars]
        else:
            return [var.name for var in all_vars]

    @classmethod
    def get_variables_by_type(cls, data_type: str) -> List[VariableDefinition]:
        """
        Get all variables of a specific data type.

        Args:
            data_type: Data type ('text', 'number', 'color', 'image', 'logo')

        Returns:
            List of VariableDefinition objects matching the data type

        Example:
            >>> color_vars = StandardVariables.get_variables_by_type('color')
            >>> len(color_vars)
            4
            >>> all(v.data_type == 'color' for v in color_vars)
            True
        """
        return [var for var in cls.get_all_variables() if var.data_type == data_type]

    @classmethod
    def get_summary(cls) -> Dict[str, any]:
        """
        Get summary statistics about defined variables.

        Returns:
            Dictionary with counts by category and type

        Example:
            >>> summary = StandardVariables.get_summary()
            >>> summary['total']
            185
            >>> summary['by_category']['team']
            10
            >>> summary['by_category']['player']
            135
        """
        all_vars = cls.get_all_variables()

        summary = {
            'total': len(all_vars),
            'by_category': {},
            'by_type': {}
        }

        # Count by category
        for category in VariableCategory:
            count = len(cls.get_by_category(category))
            summary['by_category'][category.value] = count

        # Count by type
        for var in all_vars:
            data_type = var.data_type
            summary['by_type'][data_type] = summary['by_type'].get(data_type, 0) + 1

        return summary
