"""
Services Layer - Business Logic

This package contains service classes that encapsulate business logic
and coordinate between different modules. Services provide a clean API
for the web layer and handle error management.
"""

from .base_service import BaseService, Result
from .project_service import ProjectService

__all__ = ['BaseService', 'Result', 'ProjectService']
