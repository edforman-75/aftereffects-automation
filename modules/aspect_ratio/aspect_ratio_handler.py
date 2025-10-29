"""
Aspect Ratio Handler

Conservative aspect ratio handling system with human oversight and learning capabilities.
Handles PSD → AEPX aspect ratio mismatches with clear classification and safe transformations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List, Optional
from services.base_service import BaseService
import json
from datetime import datetime


class AspectRatioCategory(Enum):
    """Aspect ratio categories for composition classification"""
    PORTRAIT = "portrait"      # Taller than wide (< 0.9 ratio)
    SQUARE = "square"          # Nearly square (0.9 - 1.1 ratio)
    LANDSCAPE = "landscape"    # Wider than tall (> 1.1 ratio)


class TransformationType(Enum):
    """Types of transformations based on mismatch severity"""
    NONE = "none"                      # Perfect match (<5% diff), no transform needed
    MINOR_SCALE = "minor_scale"        # 5-10% difference, simple scale (auto-apply)
    MODERATE_ADJUST = "moderate"       # 10-20% difference, needs human approval
    HUMAN_REVIEW = "human_review"      # >20% or cross-category, requires review


@dataclass
class AspectRatioDecision:
    """Decision result from aspect ratio analysis"""
    psd_category: AspectRatioCategory
    aepx_category: AspectRatioCategory
    psd_dimensions: Tuple[int, int]
    aepx_dimensions: Tuple[int, int]
    transformation_type: TransformationType
    ratio_difference: float
    recommended_action: str
    confidence: float
    reasoning: str
    can_auto_apply: bool


class AspectRatioClassifier:
    """Classifier for aspect ratio categories"""

    @staticmethod
    def classify(width: int, height: int) -> AspectRatioCategory:
        """
        Classify composition as portrait, square, or landscape

        Rules:
        - Portrait: ratio < 0.9 (e.g., 1080×1920 = 0.56)
        - Square: 0.9 ≤ ratio ≤ 1.1 (e.g., 1080×1080 = 1.0)
        - Landscape: ratio > 1.1 (e.g., 1920×1080 = 1.78)

        Args:
            width: Composition width in pixels
            height: Composition height in pixels

        Returns:
            AspectRatioCategory enum value

        Examples:
            >>> classify(1080, 1920)  # Portrait (Instagram Story)
            AspectRatioCategory.PORTRAIT
            >>> classify(1080, 1080)  # Square (Instagram Post)
            AspectRatioCategory.SQUARE
            >>> classify(1920, 1080)  # Landscape (HD Video)
            AspectRatioCategory.LANDSCAPE
        """
        if height == 0:
            raise ValueError("Height cannot be zero")

        ratio = width / height

        if ratio < 0.9:
            return AspectRatioCategory.PORTRAIT
        elif ratio <= 1.1:
            return AspectRatioCategory.SQUARE
        else:
            return AspectRatioCategory.LANDSCAPE

    @staticmethod
    def get_ratio_difference(
        psd_width: int,
        psd_height: int,
        aepx_width: int,
        aepx_height: int
    ) -> float:
        """
        Calculate percentage difference between aspect ratios

        Formula:
        ratio_diff = abs(psd_ratio - aepx_ratio) / max(psd_ratio, aepx_ratio)

        Args:
            psd_width, psd_height: PSD dimensions
            aepx_width, aepx_height: AEPX dimensions

        Returns:
            Float from 0.0 to 1.0
            - 0.0 = identical ratios
            - 0.05 = 5% difference
            - 0.20 = 20% difference
            - 1.0 = completely different

        Examples:
            >>> get_ratio_difference(1920, 1080, 1920, 1080)
            0.0  # Perfect match
            >>> get_ratio_difference(1920, 1080, 1280, 720)
            0.0  # Same ratio (16:9)
            >>> get_ratio_difference(1920, 1080, 1080, 1920)
            0.688  # Portrait vs Landscape (~69% different)
        """
        if psd_height == 0 or aepx_height == 0:
            raise ValueError("Height dimensions cannot be zero")

        psd_ratio = psd_width / psd_height
        aepx_ratio = aepx_width / aepx_height

        ratio_diff = abs(psd_ratio - aepx_ratio) / max(psd_ratio, aepx_ratio)

        return ratio_diff


class AspectRatioHandler(BaseService):
    """
    Conservative aspect ratio handler with human oversight

    Handles aspect ratio mismatches between PSD and AEPX compositions with:
    - Conservative classification (portrait/square/landscape)
    - Safe auto-transformations (same category, <10% difference)
    - Human review flags for risky transformations
    - Learning system to improve recommendations
    """

    def __init__(self, logger):
        """
        Initialize aspect ratio handler

        Args:
            logger: Logger instance for tracking operations
        """
        super().__init__(logger)
        self.classifier = AspectRatioClassifier()
        self.learning_data: List[Dict] = []

    def analyze_mismatch(
        self,
        psd_width: int,
        psd_height: int,
        aepx_width: int,
        aepx_height: int
    ) -> AspectRatioDecision:
        """
        Analyze aspect ratio mismatch and recommend action

        Decision Logic:
        1. Classify both compositions (portrait/square/landscape)

        2. If DIFFERENT categories:
           → TransformationType.HUMAN_REVIEW
           → recommended_action: "Manual review required - cross-category transformation"
           → can_auto_apply: False
           → confidence: 0.0

        3. If SAME category:
           Calculate ratio difference:

           - If <5%:
             → TransformationType.NONE
             → recommended_action: "No transformation needed"
             → can_auto_apply: True
             → confidence: 1.0

           - If 5-10%:
             → TransformationType.MINOR_SCALE
             → recommended_action: "Apply minor scaling adjustment"
             → can_auto_apply: True
             → confidence: 0.85

           - If 10-20%:
             → TransformationType.MODERATE_ADJUST
             → recommended_action: "Moderate adjustment recommended - human approval suggested"
             → can_auto_apply: False
             → confidence: 0.60

           - If >20%:
             → TransformationType.HUMAN_REVIEW
             → recommended_action: "Significant difference - manual review required"
             → can_auto_apply: False
             → confidence: 0.30

        Args:
            psd_width, psd_height: PSD dimensions
            aepx_width, aepx_height: AEPX dimensions

        Returns:
            AspectRatioDecision with full analysis and recommendation

        Examples:
            >>> handler.analyze_mismatch(1920, 1080, 1920, 1080)
            AspectRatioDecision(
                transformation_type=TransformationType.NONE,
                ratio_difference=0.0,
                can_auto_apply=True,
                confidence=1.0
            )

            >>> handler.analyze_mismatch(1920, 1080, 1080, 1920)  # Portrait vs Landscape
            AspectRatioDecision(
                transformation_type=TransformationType.HUMAN_REVIEW,
                can_auto_apply=False,
                confidence=0.0
            )
        """
        # Classify both compositions
        psd_category = self.classifier.classify(psd_width, psd_height)
        aepx_category = self.classifier.classify(aepx_width, aepx_height)

        # Calculate ratio difference
        ratio_diff = self.classifier.get_ratio_difference(
            psd_width, psd_height,
            aepx_width, aepx_height
        )

        self.log_info(
            f"Aspect ratio analysis: PSD {psd_width}x{psd_height} ({psd_category.value}) → "
            f"AEPX {aepx_width}x{aepx_height} ({aepx_category.value}), "
            f"diff: {ratio_diff:.1%}"
        )

        # Check for cross-category transformation
        if psd_category != aepx_category:
            return AspectRatioDecision(
                psd_category=psd_category,
                aepx_category=aepx_category,
                psd_dimensions=(psd_width, psd_height),
                aepx_dimensions=(aepx_width, aepx_height),
                transformation_type=TransformationType.HUMAN_REVIEW,
                ratio_difference=ratio_diff,
                recommended_action="Manual review required - cross-category transformation",
                confidence=0.0,
                reasoning=(
                    f"Cross-category transformation detected: {psd_category.value} → {aepx_category.value}. "
                    f"Automatic transformation may cause significant layout issues. "
                    f"Human review required to determine appropriate approach."
                ),
                can_auto_apply=False
            )

        # Same category - analyze difference percentage
        # Use strict boundaries: <5%, 5-10%, 10-20%, >20%
        if ratio_diff < 0.05:
            # Perfect or near-perfect match (<5%)
            return AspectRatioDecision(
                psd_category=psd_category,
                aepx_category=aepx_category,
                psd_dimensions=(psd_width, psd_height),
                aepx_dimensions=(aepx_width, aepx_height),
                transformation_type=TransformationType.NONE,
                ratio_difference=ratio_diff,
                recommended_action="No transformation needed",
                confidence=1.0,
                reasoning=(
                    f"Aspect ratios are nearly identical ({ratio_diff:.1%} difference). "
                    f"No transformation required - simple scaling will preserve layout perfectly."
                ),
                can_auto_apply=True
            )

        elif ratio_diff < 0.10:
            # Minor difference (5-10%) - safe to auto-apply
            return AspectRatioDecision(
                psd_category=psd_category,
                aepx_category=aepx_category,
                psd_dimensions=(psd_width, psd_height),
                aepx_dimensions=(aepx_width, aepx_height),
                transformation_type=TransformationType.MINOR_SCALE,
                ratio_difference=ratio_diff,
                recommended_action="Apply minor scaling adjustment",
                confidence=0.85,
                reasoning=(
                    f"Minor aspect ratio difference ({ratio_diff:.1%}) within same category "
                    f"({psd_category.value}). Simple scaling adjustment will maintain layout "
                    f"with minimal letterboxing/cropping. Safe to auto-apply."
                ),
                can_auto_apply=True
            )

        elif ratio_diff < 0.20:
            # Moderate difference - needs approval
            return AspectRatioDecision(
                psd_category=psd_category,
                aepx_category=aepx_category,
                psd_dimensions=(psd_width, psd_height),
                aepx_dimensions=(aepx_width, aepx_height),
                transformation_type=TransformationType.MODERATE_ADJUST,
                ratio_difference=ratio_diff,
                recommended_action="Moderate adjustment recommended - human approval suggested",
                confidence=0.60,
                reasoning=(
                    f"Moderate aspect ratio difference ({ratio_diff:.1%}) detected. "
                    f"Both compositions are {psd_category.value}, but transformation will "
                    f"result in noticeable letterboxing or cropping. Human approval "
                    f"recommended to verify acceptable results."
                ),
                can_auto_apply=False
            )

        else:
            # Large difference - requires review
            return AspectRatioDecision(
                psd_category=psd_category,
                aepx_category=aepx_category,
                psd_dimensions=(psd_width, psd_height),
                aepx_dimensions=(aepx_width, aepx_height),
                transformation_type=TransformationType.HUMAN_REVIEW,
                ratio_difference=ratio_diff,
                recommended_action="Significant difference - manual review required",
                confidence=0.30,
                reasoning=(
                    f"Significant aspect ratio difference ({ratio_diff:.1%}) detected. "
                    f"Although both are {psd_category.value}, the large difference will "
                    f"cause substantial letterboxing or content cropping. Manual review "
                    f"required to ensure acceptable results."
                ),
                can_auto_apply=False
            )

    def can_auto_transform(self, decision: AspectRatioDecision) -> bool:
        """
        Determine if transformation can be applied automatically

        Auto-apply ONLY if:
        - Same category (portrait → portrait, landscape → landscape, square → square)
        - Difference < 10%
        - Transformation type is NONE or MINOR_SCALE

        Args:
            decision: AspectRatioDecision from analyze_mismatch()

        Returns:
            True if safe to auto-apply, False if needs human review

        Examples:
            >>> decision = handler.analyze_mismatch(1920, 1080, 1920, 1080)
            >>> handler.can_auto_transform(decision)
            True  # Perfect match

            >>> decision = handler.analyze_mismatch(1920, 1080, 1080, 1920)
            >>> handler.can_auto_transform(decision)
            False  # Cross-category
        """
        # Must be same category
        if decision.psd_category != decision.aepx_category:
            self.log_info("Auto-transform denied: cross-category transformation")
            return False

        # Must be <10% difference
        if decision.ratio_difference >= 0.10:
            self.log_info(f"Auto-transform denied: difference {decision.ratio_difference:.1%} >= 10%")
            return False

        # Must be NONE or MINOR_SCALE type
        if decision.transformation_type not in [TransformationType.NONE, TransformationType.MINOR_SCALE]:
            self.log_info(f"Auto-transform denied: transformation type {decision.transformation_type.value}")
            return False

        self.log_info("Auto-transform approved: safe transformation criteria met")
        return True

    def calculate_transform(
        self,
        psd_width: int,
        psd_height: int,
        aepx_width: int,
        aepx_height: int,
        method: str = "fit"
    ) -> Dict[str, Any]:
        """
        Calculate transformation parameters for minor adjustments

        Args:
            psd_width, psd_height: PSD dimensions
            aepx_width, aepx_height: AEPX dimensions
            method: "fit" (letterbox) or "fill" (crop)

        Returns dict with:
        {
            'scale': float,          # Scale factor to apply
            'offset_x': float,       # Horizontal offset in pixels
            'offset_y': float,       # Vertical offset in pixels
            'method': str,           # "fit" or "fill"
            'new_width': float,      # PSD width after scaling
            'new_height': float,     # PSD height after scaling
            'bars': str or None      # "horizontal" or "vertical" if letterboxing
        }

        Examples:
            >>> handler.calculate_transform(1920, 1080, 3840, 2160, method="fit")
            {
                'scale': 2.0,
                'offset_x': 0.0,
                'offset_y': 0.0,
                'method': 'fit',
                'new_width': 3840.0,
                'new_height': 2160.0,
                'bars': None
            }
        """
        if method == "fit":
            return self._scale_to_fit(psd_width, psd_height, aepx_width, aepx_height)
        elif method == "fill":
            return self._scale_to_fill(psd_width, psd_height, aepx_width, aepx_height)
        else:
            raise ValueError(f"Invalid method: {method}. Must be 'fit' or 'fill'")

    def _scale_to_fit(
        self,
        psd_w: int,
        psd_h: int,
        aepx_w: int,
        aepx_h: int
    ) -> Dict:
        """
        Scale PSD to fit inside AEPX (letterbox/pillarbox)
        Maintains aspect ratio, adds bars if needed

        Args:
            psd_w, psd_h: PSD dimensions
            aepx_w, aepx_h: AEPX dimensions

        Returns:
            Transform dict with scale, offsets, and bar information
        """
        # Calculate scale factors for both dimensions
        scale_x = aepx_w / psd_w
        scale_y = aepx_h / psd_h

        # Use smaller scale to fit inside (maintains aspect ratio)
        scale = min(scale_x, scale_y)

        # Calculate new dimensions
        new_width = psd_w * scale
        new_height = psd_h * scale

        # Calculate offsets to center
        offset_x = (aepx_w - new_width) / 2
        offset_y = (aepx_h - new_height) / 2

        # Determine if bars are needed
        bars = None
        if abs(new_width - aepx_w) > 1:  # Vertical bars (pillarbox)
            bars = "vertical"
        elif abs(new_height - aepx_h) > 1:  # Horizontal bars (letterbox)
            bars = "horizontal"

        return {
            'scale': scale,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'method': 'fit',
            'new_width': new_width,
            'new_height': new_height,
            'bars': bars
        }

    def _scale_to_fill(
        self,
        psd_w: int,
        psd_h: int,
        aepx_w: int,
        aepx_h: int
    ) -> Dict:
        """
        Scale PSD to fill AEPX completely (crop edges)
        Maintains aspect ratio, crops overflow

        Args:
            psd_w, psd_h: PSD dimensions
            aepx_w, aepx_h: AEPX dimensions

        Returns:
            Transform dict with scale, offsets, and crop information
        """
        # Calculate scale factors for both dimensions
        scale_x = aepx_w / psd_w
        scale_y = aepx_h / psd_h

        # Use larger scale to fill completely (maintains aspect ratio)
        scale = max(scale_x, scale_y)

        # Calculate new dimensions (will overflow)
        new_width = psd_w * scale
        new_height = psd_h * scale

        # Calculate offsets to center (negative if cropping)
        offset_x = (aepx_w - new_width) / 2
        offset_y = (aepx_h - new_height) / 2

        return {
            'scale': scale,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'method': 'fill',
            'new_width': new_width,
            'new_height': new_height,
            'bars': None  # No bars when filling
        }

    def record_human_decision(
        self,
        psd_dims: Tuple[int, int],
        aepx_dims: Tuple[int, int],
        ai_recommendation: str,
        human_choice: str
    ):
        """
        Record human decision for learning system

        Args:
            psd_dims: (width, height) of PSD
            aepx_dims: (width, height) of AEPX
            ai_recommendation: What AI suggested (TransformationType.value)
            human_choice: What human chose - one of:
                - "proceed": Human accepted AI recommendation
                - "skip": Human chose to skip this graphic
                - "manual_fix": Human will fix manually in AE
                - "different_transform": Human chose different method

        Stores to self.learning_data list for analysis

        Examples:
            >>> handler.record_human_decision(
            ...     (1920, 1080),
            ...     (1920, 1080),
            ...     "none",
            ...     "proceed"
            ... )
        """
        # Analyze the dimensions for context
        psd_category = self.classifier.classify(psd_dims[0], psd_dims[1])
        aepx_category = self.classifier.classify(aepx_dims[0], aepx_dims[1])
        ratio_diff = self.classifier.get_ratio_difference(
            psd_dims[0], psd_dims[1],
            aepx_dims[0], aepx_dims[1]
        )

        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'psd_dimensions': psd_dims,
            'aepx_dimensions': aepx_dims,
            'psd_category': psd_category.value,
            'aepx_category': aepx_category.value,
            'ratio_difference': ratio_diff,
            'ai_recommendation': ai_recommendation,
            'human_choice': human_choice,
            'agreed': human_choice == "proceed"
        }

        self.learning_data.append(decision_record)

        self.log_info(
            f"Recorded decision: AI recommended '{ai_recommendation}', "
            f"human chose '{human_choice}' for {psd_dims} → {aepx_dims}"
        )

    def get_learning_stats(self) -> Dict:
        """
        Analyze learning data to identify patterns

        Returns dict with:
        {
            'total_decisions': int,
            'auto_apply_accuracy': float,  # % of times human agreed with auto-apply
            'common_overrides': List[Dict],  # Patterns where human disagrees
            'by_category': Dict  # Stats broken down by aspect ratio category
        }

        Examples:
            >>> stats = handler.get_learning_stats()
            >>> print(stats['total_decisions'])
            45
            >>> print(stats['auto_apply_accuracy'])
            0.87  # 87% agreement rate
        """
        if not self.learning_data:
            return {
                'total_decisions': 0,
                'auto_apply_accuracy': 0.0,
                'common_overrides': [],
                'by_category': {}
            }

        total = len(self.learning_data)

        # Calculate accuracy for auto-apply recommendations
        auto_apply_recs = [
            d for d in self.learning_data
            if d['ai_recommendation'] in ['none', 'minor_scale']
        ]
        auto_apply_agreed = [d for d in auto_apply_recs if d['agreed']]
        auto_apply_accuracy = (
            len(auto_apply_agreed) / len(auto_apply_recs)
            if auto_apply_recs else 0.0
        )

        # Find common override patterns
        overrides = [d for d in self.learning_data if not d['agreed']]
        common_overrides = []

        for override in overrides[:5]:  # Top 5 most recent
            common_overrides.append({
                'psd_category': override['psd_category'],
                'aepx_category': override['aepx_category'],
                'ratio_difference': override['ratio_difference'],
                'ai_recommendation': override['ai_recommendation'],
                'human_choice': override['human_choice']
            })

        # Stats by category
        by_category = {}
        for category in ['portrait', 'square', 'landscape']:
            category_data = [
                d for d in self.learning_data
                if d['psd_category'] == category
            ]

            if category_data:
                category_agreed = [d for d in category_data if d['agreed']]
                by_category[category] = {
                    'total': len(category_data),
                    'agreed': len(category_agreed),
                    'accuracy': len(category_agreed) / len(category_data)
                }

        return {
            'total_decisions': total,
            'auto_apply_accuracy': auto_apply_accuracy,
            'common_overrides': common_overrides,
            'by_category': by_category,
            'agreement_rate': sum(1 for d in self.learning_data if d['agreed']) / total
        }

    def export_learning_data(self, filepath: str):
        """
        Export learning data to JSON file for analysis

        Args:
            filepath: Path to save JSON file

        Examples:
            >>> handler.export_learning_data('learning_data.json')
        """
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_records': len(self.learning_data),
                    'statistics': self.get_learning_stats(),
                    'decisions': self.learning_data
                }, f, indent=2)

            self.log_info(f"Exported {len(self.learning_data)} learning records to {filepath}")

        except Exception as e:
            self.log_error(f"Failed to export learning data: {e}", e)
            raise
