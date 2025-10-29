"""
Phase 2: After Effects Template Understanding

Modules for parsing and analyzing After Effects template files.
"""

from .aepx_parser import parse_aepx
from .aepx_path_fixer import (
    find_footage_references,
    fix_footage_paths,
    collect_footage_files
)

__all__ = [
    'parse_aepx',
    'find_footage_references',
    'fix_footage_paths',
    'collect_footage_files'
]
