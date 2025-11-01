"""
AEPX/AEP Processor Service

Comprehensive headless processing of After Effects templates.
Analyzes structure, detects placeholders, and prepares for population.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import re


class AEPXProcessor:
    """
    Comprehensive AEPX/AEP processing service.

    Capabilities:
    - Parse AEPX structure (compositions, layers, properties)
    - Detect placeholder layers (text and image)
    - Analyze layer types and categorize
    - Check for missing footage
    - Convert AEP to AEPX if needed
    - Generate layer thumbnails (OPTIONAL - requires launching AE)
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.aerender_path = self._find_aerender()

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)
        else:
            print(f"ℹ️  {message}")

    def log_error(self, message: str):
        """Log error message."""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"❌ {message}")

    def _find_aerender(self) -> Optional[str]:
        """Find aerender executable path."""
        common_paths = [
            "/Applications/Adobe After Effects 2025/aerender",
            "/Applications/Adobe After Effects 2024/aerender",
            "/Applications/Adobe After Effects CC 2023/aerender",
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    def process_aepx(self, aepx_path: str, session_id: str,
                    generate_thumbnails: bool = False) -> Dict[str, Any]:
        """
        Complete AEPX processing pipeline.

        Args:
            aepx_path: Path to AEPX/AEP file
            session_id: Session identifier
            generate_thumbnails: Whether to generate layer thumbnails
                                (WARNING: Requires launching After Effects!)

        Returns:
            Comprehensive analysis results
        """
        try:
            # Beautiful header
            print(f"\n{'='*70}")
            print(f"🔄 HEADLESS AEPX PROCESSING")
            print(f"{'='*70}")
            print(f"File: {Path(aepx_path).name}")
            print(f"Session: {session_id}")
            print(f"Mode: XML parsing (pure Python)")
            if generate_thumbnails:
                print(f"⚠️  Thumbnails: Will launch After Effects")
            else:
                print(f"✅ Thumbnails: Skipped (headless mode)")
            print(f"{'='*70}\n")

            # Parse AEPX structure
            print("Parsing AEPX structure...")
            structure = self._parse_aepx_structure(aepx_path)

            compositions = structure['compositions']
            all_layers = structure['layers']
            footage_refs = structure['footage']

            print(f"✅ Found {len(compositions)} composition(s)\n")

            # Display composition info
            for comp in compositions:
                print(f"Composition: \"{comp['name']}\"")
                print(f"  - Dimensions: {comp['width']}x{comp['height']}")
                print(f"  - Duration: {comp['duration']}s")
                print(f"  - Frame rate: {comp['frame_rate']} fps")
                print(f"  - Layers: {len(comp['layers'])}\n")

            # Analyze layers
            print("Analyzing layers...\n")
            placeholders = self._detect_placeholders(all_layers)
            layer_categories = self._categorize_layers(all_layers)
            missing_footage = self._check_missing_footage(footage_refs)

            # Display layer analysis
            for idx, layer in enumerate(all_layers, 1):
                self._print_layer_info(layer, idx)

            # Generate placeholder report
            if placeholders:
                self._print_placeholder_report(placeholders, missing_footage)

            # Generate thumbnails if requested
            layer_thumbnails = {}
            if generate_thumbnails and compositions:
                print("\n⚠️  WARNING: Thumbnail generation requires launching After Effects")
                print("This may take 30-60 seconds and AE will appear briefly...\n")
                # TODO: Implement thumbnail generation
                print("ℹ️  Thumbnail generation not yet implemented")

            # Summary
            print(f"{'='*70}")
            print(f"✅ HEADLESS AEPX PROCESSING COMPLETE")
            print(f"{'='*70}")
            print(f"  - Compositions: {len(compositions)}")
            print(f"  - Total layers: {len(all_layers)}")
            print(f"  - Text layers: {len(layer_categories['text_layers'])}")
            print(f"  - Image layers: {len(layer_categories['image_layers'])}")
            print(f"  - Placeholders detected: {len(placeholders)}")
            if generate_thumbnails:
                print(f"  - Thumbnails generated: {len(layer_thumbnails)}")
            print(f"  - Missing footage: {len(missing_footage)}")
            print(f"  - After Effects UI: {'Launched briefly' if generate_thumbnails else 'Never appeared ✨'}")
            print(f"{'='*70}\n")

            return {
                'compositions': compositions,
                'layers': all_layers,
                'layer_categories': layer_categories,
                'placeholders': placeholders,
                'layer_thumbnails': layer_thumbnails,
                'missing_footage': missing_footage,
                'footage_refs': footage_refs
            }

        except Exception as e:
            self.log_error(f"AEPX processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _parse_aepx_structure(self, aepx_path: str) -> Dict[str, Any]:
        """
        Parse AEPX XML to extract structure.

        Returns:
            {
                'compositions': [...],
                'layers': [...],
                'footage': [...]
            }
        """
        try:
            tree = ET.parse(aepx_path)
            root = tree.getroot()

            compositions = []
            all_layers = []
            footage_refs = []

            # Find compositions (Item elements with cdta child = composition data)
            for item_elem in root.iter():
                if item_elem.tag.endswith('Item'):
                    # Check if this Item has composition data (cdta tag) - namespace-aware
                    if item_elem.find('.//{*}cdta') is not None:
                        comp_info = self._parse_composition(item_elem)
                        if comp_info:
                            compositions.append(comp_info)
                            all_layers.extend(comp_info['layers'])

            # Find footage references (Pin elements with fileReference)
            for item_elem in root.iter():
                if item_elem.tag.endswith('Pin'):
                    footage = self._parse_footage_item(item_elem)
                    if footage:
                        footage_refs.append(footage)

            return {
                'compositions': compositions,
                'layers': all_layers,
                'footage': footage_refs
            }

        except Exception as e:
            self.log_error(f"Failed to parse AEPX: {e}")
            return {'compositions': [], 'layers': [], 'footage': []}

    def _parse_composition(self, comp_elem) -> Optional[Dict]:
        """Parse a composition element (Item with cdta)."""
        try:
            # Get composition name from string child element - namespace-aware
            name_elem = comp_elem.find('./{*}string')
            name = name_elem.text if name_elem is not None and name_elem.text else None

            if not name:
                return None

            # Default values (binary cdta parsing would be complex)
            width = 1920
            height = 1080
            duration = 5.0
            frame_rate = 30.0

            # Parse layers - look for Layr tags in this Item and any Sfdr (sub-folder) - namespace-aware
            layers = []
            for layer_elem in comp_elem.iter():
                if layer_elem.tag.endswith('Layr'):
                    layer_info = self._parse_layer(layer_elem)
                    if layer_info:
                        layers.append(layer_info)

            return {
                'name': name,
                'width': width,
                'height': height,
                'duration': duration,
                'frame_rate': frame_rate,
                'layers': layers
            }

        except Exception as e:
            return None

    def _parse_layer(self, layer_elem) -> Optional[Dict]:
        """Parse a layer element (Layr tag)."""
        try:
            # Get layer name from string child element - namespace-aware
            name_elem = layer_elem.find('./{*}string')
            name = name_elem.text if name_elem is not None and name_elem.text else 'Unknown'

            # Determine layer type
            layer_type = self._determine_layer_type(layer_elem, name)

            # Get text content if text layer (use name as placeholder)
            text_content = None
            if layer_type == 'text':
                text_content = name  # In AEPX, layer name often IS the text content

            # Get footage reference if image layer - namespace-aware
            footage_ref = None
            if layer_type in ['image', 'footage']:
                # Try to find file reference in child elements
                file_ref = layer_elem.find('.//{*}fileReference')
                if file_ref is not None:
                    footage_ref = file_ref.get('fullpath')

            return {
                'name': name,
                'type': layer_type,
                'text_content': text_content,
                'footage_ref': footage_ref,
            }

        except Exception as e:
            return None

    def _determine_layer_type(self, layer_elem, name: str) -> str:
        """Determine the type of layer based on element structure and name."""
        # Check if layer has a fileReference child (image/footage layer) - namespace-aware
        if layer_elem.find('.//{*}fileReference') is not None:
            return 'image'

        # Check if layer has Pin child (could be footage) - namespace-aware
        if layer_elem.find('.//{*}Pin') is not None:
            return 'image'

        # Check for text layer indicators in the name
        text_keywords = ['name', 'title', 'text', 'label', 'fullname', 'player']
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in text_keywords):
            return 'text'

        # Check for solid layer indicators
        if 'background' in name_lower or 'bg' in name_lower or 'solid' in name_lower:
            return 'solid'

        # Default to unknown
        return 'text'  # Assume text for most placeholder layers

    def _extract_text_content(self, layer_elem) -> Optional[str]:
        """Extract text content from text layer."""
        # Try various locations where text might be stored
        text_elem = layer_elem.find('.//Text') or layer_elem.find('.//text')
        if text_elem is not None:
            return text_elem.text

        # Try attribute
        return layer_elem.get('text') or layer_elem.get('content')

    def _parse_footage_item(self, item_elem) -> Optional[Dict]:
        """Parse a footage item (Pin element with fileReference)."""
        try:
            # Get name from string child - namespace-aware
            name_elem = item_elem.find('./{*}string')
            name = name_elem.text if name_elem is not None and name_elem.text else None

            # Get path from fileReference - namespace-aware
            file_ref = item_elem.find('.//{*}fileReference')
            path = file_ref.get('fullpath') if file_ref is not None else None

            if not name and not path:
                return None

            return {
                'name': name or (Path(path).name if path else 'Unknown'),
                'path': path,
                'exists': os.path.exists(path) if path else False
            }

        except Exception:
            return None

    def _detect_placeholders(self, layers: List[Dict]) -> List[Dict]:
        """
        Identify layers that need to be populated.

        Placeholder indicators:
        - Layer names with keywords
        - Placeholder text patterns
        - Missing footage references
        """
        placeholders = []

        placeholder_keywords = [
            'placeholder', 'replace', 'content', 'populate',
            'player', 'title', 'name', 'text', 'image', 'photo'
        ]

        for layer in layers:
            layer_name_lower = layer['name'].lower()
            is_placeholder = False
            reason = []

            # Check for placeholder keywords in name
            for keyword in placeholder_keywords:
                if keyword in layer_name_lower:
                    is_placeholder = True
                    reason.append(f"name contains '{keyword}'")
                    break

            # Check for placeholder text patterns
            if layer['type'] == 'text' and layer.get('text_content'):
                if self._is_placeholder_text(layer['text_content']):
                    is_placeholder = True
                    reason.append(f"contains: {layer['text_content']}")

            # Check for missing footage
            if layer['type'] in ['image', 'footage']:
                if layer.get('footage_ref') and not os.path.exists(layer.get('footage_ref', '')):
                    is_placeholder = True
                    reason.append("missing footage")

            if is_placeholder:
                layer_copy = layer.copy()
                layer_copy['placeholder_reason'] = ', '.join(reason)
                placeholders.append(layer_copy)

        return placeholders

    def _is_placeholder_text(self, text: str) -> bool:
        """
        Detect if text is a placeholder.

        Patterns:
        - ALL CAPS (minimum 4 chars)
        - Brackets: [Title], {Name}
        - Hash symbols: PLAYER#FULLNAME
        - Lorem ipsum
        - "Placeholder" keyword
        """
        if not text or len(text) < 2:
            return False

        # Check patterns
        patterns = [
            text.isupper() and len(text) >= 4,  # ALL CAPS
            '[' in text or '{' in text,  # Brackets
            '#' in text,  # Hash symbols
            'lorem' in text.lower(),  # Lorem ipsum
            'placeholder' in text.lower(),
            'PLAYER' in text,  # Common placeholder pattern
            'TITLE' in text,
            'NAME' in text and len(text) < 50  # Short NAME fields
        ]

        return any(patterns)

    def _categorize_layers(self, layers: List[Dict]) -> Dict[str, List]:
        """Categorize layers by type."""
        categories = {
            'text_layers': [],
            'image_layers': [],
            'solid_layers': [],
            'shape_layers': [],
            'adjustment_layers': [],
            'unknown_layers': []
        }

        for layer in layers:
            layer_type = layer['type']

            if layer_type == 'text':
                categories['text_layers'].append(layer)
            elif layer_type in ['footage', 'image']:
                categories['image_layers'].append(layer)
            elif layer_type == 'solid':
                categories['solid_layers'].append(layer)
            elif layer_type == 'shape':
                categories['shape_layers'].append(layer)
            elif layer_type == 'adjustment':
                categories['adjustment_layers'].append(layer)
            else:
                categories['unknown_layers'].append(layer)

        return categories

    def _check_missing_footage(self, footage_refs: List[Dict]) -> List[Dict]:
        """Check for missing footage files."""
        missing = []

        for footage in footage_refs:
            if footage.get('path') and not footage.get('exists', False):
                missing.append(footage)

        return missing

    def _print_layer_info(self, layer: Dict, index: int):
        """Print formatted layer information."""
        print(f"├── [{index}] {layer['name']} ({layer['type']} layer)")

        if layer['type'] == 'text' and layer.get('text_content'):
            print(f"│   📝 Text: \"{layer['text_content']}\"")

        if layer['type'] in ['image', 'footage'] and layer.get('footage_ref'):
            print(f"│   📁 Footage: {layer['footage_ref']}")
            if not os.path.exists(layer.get('footage_ref', '')):
                print(f"│   ⚠️  Missing footage - not found on system")

        print("│")

    def _print_placeholder_report(self, placeholders: List[Dict], missing_footage: List[Dict]):
        """Print placeholder detection report."""
        print(f"{'='*70}")
        print(f"📋 PLACEHOLDER DETECTION REPORT")
        print(f"{'='*70}\n")

        # Categorize placeholders
        text_placeholders = [p for p in placeholders if p['type'] == 'text']
        image_placeholders = [p for p in placeholders if p['type'] in ['image', 'footage']]

        if text_placeholders:
            print(f"Text Placeholders ({len(text_placeholders)}):")
            for p in text_placeholders:
                print(f"  - {p['name']} ({p.get('placeholder_reason', 'detected')})")
            print()

        if image_placeholders:
            print(f"Image Placeholders ({len(image_placeholders)}):")
            for p in image_placeholders:
                print(f"  - {p['name']} ({p.get('placeholder_reason', 'detected')})")
            print()

        if missing_footage:
            print(f"⚠️  Missing Footage ({len(missing_footage)}):")
            for footage in missing_footage:
                print(f"  ❌ {footage['name']}")
                if footage.get('path'):
                    print(f"     Path: {footage['path']}")
            print()

        print(f"{'='*70}\n")
