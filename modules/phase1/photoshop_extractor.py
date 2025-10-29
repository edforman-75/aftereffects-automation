"""
Photoshop ExtendScript Automation

Extracts PSD layer data using Adobe Photoshop via AppleScript automation.
This is used as a fallback when psd-tools cannot parse newer Photoshop formats.
"""

import os
import json
import glob
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def find_photoshop_app() -> Optional[str]:
    """
    Find installed Photoshop application.

    Searches /Applications for any Adobe Photoshop version (2020-2025+).

    Returns:
        Path to Photoshop.app, or None if not found
    """
    # Check environment variable first
    env_path = os.getenv('PHOTOSHOP_APP_PATH')
    if env_path and os.path.exists(env_path):
        logger.info(f"Using Photoshop from environment: {env_path}")
        return env_path

    # Search for Photoshop in Applications folder
    search_patterns = [
        "/Applications/Adobe Photoshop */Adobe Photoshop *.app",
        "/Applications/Adobe Photoshop.app",
    ]

    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            # Sort by version (newest first)
            matches.sort(reverse=True)
            app_path = matches[0]
            logger.info(f"Found Photoshop: {app_path}")
            return app_path

    logger.warning("Photoshop application not found in /Applications")
    return None


def is_photoshop_running() -> bool:
    """
    Check if Photoshop is currently running.

    Returns:
        True if Photoshop is running, False otherwise
    """
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "System Events" to (name of processes) contains "Adobe Photoshop"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() == "true"
    except Exception as e:
        logger.debug(f"Could not check if Photoshop is running: {e}")
        return False


def extract_with_photoshop(psd_path: str) -> Dict[str, Any]:
    """
    Extract PSD layer data using Photoshop via AppleScript automation.

    This function:
    1. Checks if Photoshop is installed
    2. Opens the PSD file in Photoshop
    3. Runs ExtendScript to extract layer data
    4. Reads the JSON output
    5. Closes the document (keeps Photoshop open)

    Args:
        psd_path: Path to the PSD file

    Returns:
        Dictionary containing layer data (same format as parse_psd())

    Raises:
        FileNotFoundError: If Photoshop is not installed
        ValueError: If extraction fails
        RuntimeError: If AppleScript execution fails
    """
    # Validate PSD file exists
    psd_path = os.path.abspath(psd_path)
    if not os.path.exists(psd_path):
        raise FileNotFoundError(f"PSD file not found: {psd_path}")

    # Find Photoshop
    photoshop_app = find_photoshop_app()
    if not photoshop_app:
        raise FileNotFoundError("Adobe Photoshop not found. Install Photoshop or set PHOTOSHOP_APP_PATH.")

    # Get ExtendScript path
    script_dir = Path(__file__).parent.parent.parent / "scripts"
    jsx_path = script_dir / "extract_psd_layers.jsx"

    if not jsx_path.exists():
        raise FileNotFoundError(f"ExtendScript not found: {jsx_path}")

    logger.info(f"Extracting PSD data using Photoshop: {psd_path}")
    logger.info(f"ExtendScript: {jsx_path}")

    # Check if Photoshop is already running
    ps_was_running = is_photoshop_running()
    if ps_was_running:
        logger.info("Photoshop is already running")
    else:
        logger.info("Photoshop will be launched")

    # Build AppleScript to automate Photoshop
    # Use quoted form to handle paths with spaces and special characters
    applescript = f'''
        tell application "{photoshop_app}"
            activate

            -- Open the PSD file using POSIX path
            try
                set psdFile to POSIX file "{psd_path}"
                open file psdFile
            on error errMsg
                return "ERROR: Could not open PSD file - " & errMsg
            end try

            -- Run the ExtendScript using POSIX path
            try
                set jsxFile to POSIX file "{jsx_path}"
                set outputPath to do javascript file jsxFile
            on error errMsg
                return "ERROR: ExtendScript failed - " & errMsg
            end try

            -- Close the document without saving
            try
                close current document saving no
            on error
                -- Document may already be closed
            end try

            return outputPath
        end tell
    '''

    try:
        # Execute AppleScript
        logger.debug("Executing AppleScript to control Photoshop...")
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"AppleScript failed: {result.stderr}")

        output_path = result.stdout.strip()
        logger.debug(f"ExtendScript output path: {output_path}")

        # Check for errors
        if output_path.startswith("ERROR:"):
            raise ValueError(output_path)

        # Read JSON output
        if not os.path.exists(output_path):
            raise ValueError(f"Output file not created: {output_path}")

        logger.info(f"Reading extracted data from: {output_path}")

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Clean up temporary file
        try:
            os.remove(output_path)
            logger.debug(f"Cleaned up temporary file: {output_path}")
        except Exception as e:
            logger.warning(f"Could not delete temporary file: {e}")

        # Add metadata
        data['limited_parse'] = False  # Full parsing with Photoshop
        data['parse_method'] = 'photoshop'

        logger.info(
            f"Successfully extracted PSD data with Photoshop: "
            f"{len(data['layers'])} layers, {data['width']}x{data['height']}"
        )

        return data

    except subprocess.TimeoutExpired:
        logger.error("Photoshop automation timed out after 60 seconds")
        raise RuntimeError("Photoshop automation timed out")

    except Exception as e:
        logger.error(f"Photoshop extraction failed: {e}")
        raise


def is_photoshop_available() -> bool:
    """
    Check if Photoshop extraction is available.

    Returns:
        True if Photoshop is installed and can be used
    """
    try:
        photoshop_app = find_photoshop_app()
        return photoshop_app is not None
    except Exception:
        return False


# Test function for direct execution
if __name__ == '__main__':
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python photoshop_extractor.py <psd_file>")
        sys.exit(1)

    psd_file = sys.argv[1]

    try:
        print(f"Testing Photoshop extraction with: {psd_file}")
        print("=" * 60)

        # Check if available
        if not is_photoshop_available():
            print("❌ Photoshop not available")
            sys.exit(1)

        print("✅ Photoshop is available")

        # Extract data
        result = extract_with_photoshop(psd_file)

        print(f"\n✅ Extraction successful!")
        print(f"Filename: {result['filename']}")
        print(f"Dimensions: {result['width']}x{result['height']}")
        print(f"Layers: {len(result['layers'])}")
        print(f"Parse method: {result.get('parse_method', 'unknown')}")

        if result['layers']:
            print(f"\nFirst few layers:")
            for i, layer in enumerate(result['layers'][:5]):
                print(f"  {i+1}. {layer['name']} (type: {layer['type']})")

    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
