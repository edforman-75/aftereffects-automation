"""
Expression System Module

Provides variable definitions, expression generation, and Hard Card composition
management for After Effects parametrized templates.
"""

from .variable_definitions import (
    VariableCategory,
    VariableDefinition,
    StandardVariables
)

from .expression_generator import (
    ExpressionConfig,
    ExpressionGenerator
)

from .hard_card_generator import (
    HardCardLayer,
    HardCardGenerator
)

from .aepx_expression_writer import (
    ExpressionTarget,
    LayerExpression,
    AEPXExpressionWriter
)

__all__ = [
    'VariableCategory',
    'VariableDefinition',
    'StandardVariables',
    'ExpressionConfig',
    'ExpressionGenerator',
    'HardCardLayer',
    'HardCardGenerator',
    'ExpressionTarget',
    'LayerExpression',
    'AEPXExpressionWriter',
]
