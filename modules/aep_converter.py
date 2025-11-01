"""
AEP to AEPX Converter

Automatically detect and convert .aep files to .aepx format using AppleScript or aerender.
"""

import os
import subprocess
import logging
from typing import Optional, List
from pathlib import Path


class AEPConverter:
    """Convert AEP files to AEPX format"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def find_aep_files(self, directory: str) -> List[str]:
        """Find all .aep files in directory"""
        aep_files = []

        if not os.path.exists(directory):
            return aep_files

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.aep'):
                    aep_files.append(os.path.join(root, file))

        return aep_files

    def convert_aep_to_aepx_applescript(self, aep_path: str, output_path: Optional[str] = None) -> dict:
        """
        Convert AEP to AEPX using AppleScript (Mac only)

        Args:
            aep_path: Path to .aep file
            output_path: Optional output path for .aepx (defaults to same location)

        Returns:
            dict with success status and output path or error
        """
        try:
            if not os.path.exists(aep_path):
                return {
                    'success': False,
                    'error': f'AEP file not found: {aep_path}'
                }

            # Generate output path if not provided
            if not output_path:
                output_path = aep_path.replace('.aep', '.aepx')

            # Convert to absolute paths
            aep_path = os.path.abspath(aep_path)
            output_path = os.path.abspath(output_path)

            # AppleScript to open AEP and save as AEPX (headless mode)
            applescript = f'''
            tell application "Adobe After Effects 2025"
                -- Don't activate to keep AE in background

                -- Open the AEP file
                open POSIX file "{aep_path}"

                -- Save as AEPX (XML format)
                tell front project
                    save in POSIX file "{output_path}"
                end tell

                -- Close the project without saving again
                close front project saving no
            end tell

            -- Hide After Effects after conversion
            tell application "System Events"
                set visible of process "Adobe After Effects 2025" to false
            end tell
            '''

            self.logger.info(f"Converting AEP to AEPX: {aep_path}")

            # Execute AppleScript
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error during conversion"
                self.logger.error(f"AppleScript conversion failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

            # Verify output file was created
            if os.path.exists(output_path):
                self.logger.info(f"Successfully converted to AEPX: {output_path}")
                return {
                    'success': True,
                    'aepx_path': output_path,
                    'original_aep': aep_path
                }
            else:
                return {
                    'success': False,
                    'error': 'AEPX file was not created'
                }

        except subprocess.TimeoutExpired:
            self.logger.error(f"Conversion timeout for {aep_path}")
            return {
                'success': False,
                'error': 'Conversion timed out after 60 seconds'
            }
        except Exception as e:
            self.logger.error(f"Error converting AEP to AEPX: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def convert_aep_to_aepx_aerender(self, aep_path: str, output_path: Optional[str] = None) -> dict:
        """
        Convert AEP to AEPX using aerender command line (cross-platform)

        Note: This requires a render script that saves as AEPX

        Args:
            aep_path: Path to .aep file
            output_path: Optional output path for .aepx

        Returns:
            dict with success status and output path or error
        """
        try:
            if not os.path.exists(aep_path):
                return {
                    'success': False,
                    'error': f'AEP file not found: {aep_path}'
                }

            # Generate output path
            if not output_path:
                output_path = aep_path.replace('.aep', '.aepx')

            # Convert to absolute paths
            aep_path = os.path.abspath(aep_path)
            output_path = os.path.abspath(output_path)

            # Create a temporary JSX script to do the conversion
            jsx_script = f'''
var project = app.open(new File("{aep_path}"));
project.save(new File("{output_path}"));
project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
app.quit();
'''

            jsx_path = '/tmp/convert_aep.jsx'
            with open(jsx_path, 'w') as f:
                f.write(jsx_script)

            # Execute aerender with the script
            aerender_path = '/Applications/Adobe After Effects 2025/aerender'

            if not os.path.exists(aerender_path):
                return {
                    'success': False,
                    'error': 'aerender not found at expected location'
                }

            result = subprocess.run(
                [aerender_path, '-s', jsx_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Clean up temp script
            if os.path.exists(jsx_path):
                os.remove(jsx_path)

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error during conversion"
                self.logger.error(f"aerender conversion failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

            if os.path.exists(output_path):
                self.logger.info(f"Successfully converted to AEPX: {output_path}")
                return {
                    'success': True,
                    'aepx_path': output_path,
                    'original_aep': aep_path
                }
            else:
                return {
                    'success': False,
                    'error': 'AEPX file was not created'
                }

        except Exception as e:
            self.logger.error(f"Error converting AEP to AEPX: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def batch_convert_directory(self, directory: str, use_applescript: bool = True) -> dict:
        """
        Find and convert all AEP files in a directory

        Args:
            directory: Directory to scan for .aep files
            use_applescript: If True, use AppleScript; if False, use aerender

        Returns:
            dict with conversion results
        """
        aep_files = self.find_aep_files(directory)

        if not aep_files:
            return {
                'success': True,
                'message': 'No AEP files found',
                'converted': [],
                'failed': []
            }

        self.logger.info(f"Found {len(aep_files)} AEP files to convert")

        converted = []
        failed = []

        for aep_path in aep_files:
            self.logger.info(f"Converting: {aep_path}")

            if use_applescript:
                result = self.convert_aep_to_aepx_applescript(aep_path)
            else:
                result = self.convert_aep_to_aepx_aerender(aep_path)

            if result['success']:
                converted.append({
                    'original': aep_path,
                    'converted': result['aepx_path']
                })
            else:
                failed.append({
                    'file': aep_path,
                    'error': result['error']
                })

        return {
            'success': len(failed) == 0,
            'total': len(aep_files),
            'converted': converted,
            'failed': failed,
            'message': f"Converted {len(converted)}/{len(aep_files)} files"
        }
