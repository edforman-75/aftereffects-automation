#!/usr/bin/env python3
"""
Test absolute path conversion for aerender output.
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import render_with_aerender

def test_relative_path_conversion():
    """Test that relative paths are converted to absolute paths."""

    print("\n" + "="*70)
    print("TEST: Relative Path Conversion")
    print("="*70)

    # Save current directory
    original_cwd = os.getcwd()

    temp_dir = tempfile.mkdtemp(prefix='test_abs_path_')

    try:
        # Create a subdirectory for output
        output_dir = Path(temp_dir) / 'previews'
        output_dir.mkdir()

        # Change to temp directory
        os.chdir(temp_dir)

        project_path = f"{temp_dir}/test.aep"

        # Use RELATIVE path (this is what would fail with aerender)
        relative_output_path = "previews/preview.mp4"

        print(f"\nSetup:")
        print(f"  Current directory: {os.getcwd()}")
        print(f"  Relative output path: {relative_output_path}")
        print(f"  Expected absolute path: {output_dir / 'preview.mp4'}")

        # Create dummy project file
        with open(project_path, 'w') as f:
            f.write('mock project')

        # Capture the command that would be executed
        captured_cmd = None
        captured_output_path = None

        def mock_subprocess_run(*args, **kwargs):
            nonlocal captured_cmd, captured_output_path
            captured_cmd = args[0]

            # Extract output path from command
            output_idx = captured_cmd.index('-output') + 1
            captured_output_path = captured_cmd[output_idx]

            # Create output file at the captured path
            with open(captured_output_path, 'wb') as f:
                f.write(b'mock video')

            return Mock(returncode=0, stdout='Render completed', stderr='')

        with patch('subprocess.run', side_effect=mock_subprocess_run):
            options = {
                'resolution': 'half',
                'duration': 5.0,
                'format': 'mp4',
                'fps': 15
            }

            aerender_path = '/Applications/Adobe After Effects 2025/aerender'

            result = render_with_aerender(
                project_path,
                'test-aep',
                relative_output_path,  # ← RELATIVE PATH
                options,
                aerender_path
            )

            print(f"\nResults:")
            print(f"  Captured output path: {captured_output_path}")
            print(f"  Is absolute: {Path(captured_output_path).is_absolute()}")
            print(f"  Resolves to: {Path(relative_output_path).resolve()}")

            # Verify path is absolute
            if not Path(captured_output_path).is_absolute():
                print(f"  ❌ FAIL: Path is still relative!")
                return False

            # Verify it's the correct absolute path
            expected_abs_path = str((output_dir / 'preview.mp4').resolve())
            if captured_output_path != expected_abs_path:
                print(f"  ❌ FAIL: Wrong absolute path!")
                print(f"     Expected: {expected_abs_path}")
                print(f"     Got: {captured_output_path}")
                return False

            print(f"  ✅ PASS: Relative path converted to absolute!")

            # Verify render succeeded
            if result:
                print(f"  ✅ PASS: Render completed successfully")
                return True
            else:
                print(f"  ❌ FAIL: Render failed")
                return False

    finally:
        # Restore original directory
        os.chdir(original_cwd)
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_absolute_path_unchanged():
    """Test that absolute paths remain unchanged."""

    print("\n" + "="*70)
    print("TEST: Absolute Path Unchanged")
    print("="*70)

    temp_dir = tempfile.mkdtemp(prefix='test_abs_unchanged_')

    try:
        project_path = f"{temp_dir}/test.aep"

        # Use ABSOLUTE path
        absolute_output_path = f"{temp_dir}/preview.mp4"

        print(f"\nSetup:")
        print(f"  Absolute output path: {absolute_output_path}")

        # Create dummy project file
        with open(project_path, 'w') as f:
            f.write('mock project')

        captured_cmd = None
        captured_output_path = None

        def mock_subprocess_run(*args, **kwargs):
            nonlocal captured_cmd, captured_output_path
            captured_cmd = args[0]

            output_idx = captured_cmd.index('-output') + 1
            captured_output_path = captured_cmd[output_idx]

            with open(captured_output_path, 'wb') as f:
                f.write(b'mock video')

            return Mock(returncode=0, stdout='Render completed', stderr='')

        with patch('subprocess.run', side_effect=mock_subprocess_run):
            options = {
                'resolution': 'half',
                'duration': 5.0,
                'format': 'mp4',
                'fps': 15
            }

            result = render_with_aerender(
                project_path,
                'test-aep',
                absolute_output_path,  # ← ABSOLUTE PATH
                options,
                '/Applications/Adobe After Effects 2025/aerender'
            )

            print(f"\nResults:")
            print(f"  Input path: {absolute_output_path}")
            print(f"  Captured path: {captured_output_path}")

            # Verify path is still absolute and correct
            if captured_output_path == str(Path(absolute_output_path).resolve()):
                print(f"  ✅ PASS: Absolute path preserved correctly!")
                return result
            else:
                print(f"  ❌ FAIL: Path was modified incorrectly")
                return False

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def show_before_after():
    """Show before/after comparison."""

    print("\n" + "="*70)
    print("BEFORE/AFTER COMPARISON")
    print("="*70)

    print("\n❌ BEFORE (relative path):")
    print("  User's code:")
    print("    output_path = 'previews/preview.mp4'")
    print("    render_with_aerender(..., output_path)")
    print()
    print("  aerender command:")
    print("    -output previews/preview.mp4")
    print()
    print("  aerender interprets as:")
    print("    /Applications/Adobe After Effects 2025/previews/preview.mp4")
    print("    ❌ Wrong directory! File saved to AE app folder")

    print("\n✅ AFTER (absolute path):")
    print("  User's code (unchanged):")
    print("    output_path = 'previews/preview.mp4'")
    print("    render_with_aerender(..., output_path)")
    print()
    print("  Function converts to absolute:")
    print("    abs_output_path = Path(output_path).resolve()")
    print("    # = '/Users/edf/aftereffects-automation/previews/preview.mp4'")
    print()
    print("  aerender command:")
    print("    -output /Users/edf/aftereffects-automation/previews/preview.mp4")
    print()
    print("  aerender saves to:")
    print("    /Users/edf/aftereffects-automation/previews/preview.mp4")
    print("    ✅ Correct directory!")

    print("\n💡 Benefits:")
    print("  - Works with relative paths from web_app.py")
    print("  - Works with absolute paths")
    print("  - aerender always gets absolute path")
    print("  - File is saved in the expected location")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "ABSOLUTE PATH FIX TEST" + " " * 27 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []
    results.append(("Relative path conversion", test_relative_path_conversion()))
    results.append(("Absolute path unchanged", test_absolute_path_unchanged()))

    show_before_after()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nRESULTS: {passed}/{total} tests passed")
    print("="*70)
    print()

    sys.exit(0 if passed == total else 1)
