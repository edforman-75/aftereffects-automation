"""
Dependency Injection Container

Central container for managing service instances and their dependencies.
"""

import logging
import os
from typing import Optional

from core.logging_config import setup_logging, get_service_logger
from services.enhanced_logging_service import EnhancedLoggingService
from services.psd_service import PSDService
from services.aepx_service import AEPXService
from services.matching_service import MatchingService
from services.preview_service import PreviewService
from services.settings_service import SettingsService
from services.project_service import ProjectService
from services.export_service import ExportService
from services.expression_applier_service import ExpressionApplierService
from services.recovery_service import RecoveryService
from services.validation_service import ValidationService
from modules.aep_converter import AEPConverter
from modules.expression_system import (
    ExpressionGenerator,
    ExpressionConfig,
    HardCardGenerator,
    AEPXExpressionWriter
)


class ServiceContainer:
    """
    Dependency injection container for services.

    This container:
    - Manages service lifecycle
    - Handles dependency injection
    - Provides a single point of access to all services
    - Ensures services share common logging configuration

    Usage:
        from config.container import container

        # Use services
        psd_result = container.psd_service.parse_psd(psd_path)
        aepx_result = container.aepx_service.parse_aepx(aepx_path)

        if psd_result.is_success() and aepx_result.is_success():
            psd_data = psd_result.get_data()
            aepx_data = aepx_result.get_data()

            # Match content
            match_result = container.matching_service.match_content(
                psd_data, aepx_data
            )

            if match_result.is_success():
                mappings = match_result.get_data()

                # Generate preview
                preview_result = container.preview_service.generate_preview(
                    aepx_path, mappings, output_path
                )
    """

    _instance: Optional['ServiceContainer'] = None

    def __new__(cls):
        """Singleton pattern - only one container instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the container and all services."""
        if self._initialized:
            return

        # Setup logging
        self.main_logger = setup_logging(
            app_name='aftereffects_automation',
            log_level=logging.INFO,
            console_output=True
        )

        self.main_logger.info("Initializing service container...")

        # Initialize services
        self._initialize_services()

        self._initialized = True
        self.main_logger.info("Service container initialized successfully")

    def _initialize_services(self):
        """Initialize all service instances."""
        # Create enhanced logging service if enabled
        use_enhanced = os.getenv('USE_ENHANCED_LOGGING', 'false').lower() == 'true'
        if use_enhanced:
            self.enhanced_logging = EnhancedLoggingService(self.main_logger)
            self.main_logger.info("Enhanced logging enabled")
        else:
            self.enhanced_logging = None

        # Settings Service
        self.settings_service = SettingsService(
            logger=get_service_logger('settings'),
            enhanced_logging=self.enhanced_logging
        )

        # PSD Service
        self.psd_service = PSDService(
            logger=get_service_logger('psd'),
            enhanced_logging=self.enhanced_logging
        )

        # AEPX Service
        self.aepx_service = AEPXService(
            logger=get_service_logger('aepx'),
            enhanced_logging=self.enhanced_logging
        )

        # Matching Service
        self.matching_service = MatchingService(
            logger=get_service_logger('matching'),
            enhanced_logging=self.enhanced_logging
        )

        # Preview Service
        self.preview_service = PreviewService(
            logger=get_service_logger('preview'),
            enhanced_logging=self.enhanced_logging
        )

        # AEP Converter
        self.aep_converter = AEPConverter(
            logger=get_service_logger('aep_converter')
        )

        # Export Service
        self.export_service = ExportService(
            logger=get_service_logger('export'),
            enhanced_logging=self.enhanced_logging
        )

        # Expression System Components
        # Configuration for expression generator
        self.expression_config = ExpressionConfig(
            hard_card_comp_name="Hard_Card",
            use_lowercase_comparison=True,
            add_error_handling=True
        )

        # Expression Generator (creates JavaScript expressions)
        self.expression_generator = ExpressionGenerator(self.expression_config)

        # Hard Card Generator (creates variable composition)
        self.hard_card_generator = HardCardGenerator(
            logger=get_service_logger('hard_card_generator'),
            comp_width=1920,
            comp_height=1080
        )

        # AEPX Expression Writer (modifies AEPX XML to add expressions)
        self.aepx_expression_writer = AEPXExpressionWriter(
            logger=get_service_logger('aepx_expression_writer')
        )

        # Expression Applier Service (intelligently matches layers to variables)
        self.expression_applier_service = ExpressionApplierService(
            logger=get_service_logger('expression_applier'),
            enhanced_logging=self.enhanced_logging
        )

        # Project Service (with audit trail and batch processing)
        # Get settings data from Result object
        settings_result = self.settings_service.get_settings()
        settings_data = settings_result.get_data() if settings_result.is_success() else {}

        self.project_service = ProjectService(
            logger=get_service_logger('project'),
            settings=settings_data,
            psd_service=self.psd_service,
            aepx_service=self.aepx_service,
            matching_service=self.matching_service,
            preview_service=self.preview_service,
            expression_applier_service=self.expression_applier_service,
            enhanced_logging=self.enhanced_logging
        )

        # Recovery Service (error recovery and retry mechanisms)
        self.recovery_service = RecoveryService(
            logger=get_service_logger('recovery'),
            project_service=self.project_service,
            enhanced_logging=self.enhanced_logging
        )

        # Validation Service (file validation before processing)
        self.validation_service = ValidationService(
            logger=get_service_logger('validation'),
            enhanced_logging=self.enhanced_logging
        )

    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Logger name (optional)

        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(f'aftereffects_automation.{name}')
        return self.main_logger

    def reset(self):
        """
        Reset the container (useful for testing).

        Warning: This will re-initialize all services.
        """
        self._initialized = False
        self.__init__()


# Global container instance
# Import this in other modules: from config.container import container
container = ServiceContainer()
