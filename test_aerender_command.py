#!/usr/bin/env python3
"""
Test aerender command construction after removing -OMtemplate parameter.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import render_with_aerender

def test_aerender_command_without_omtemplate():
    """Verify aerender command no longer includes -OMtemplate."""

    print("\n" + "="*70)
    print("TEST: aerender Command Without -OMtemplate")
    print("="*70)

    temp_dir = tempfile.mkdtemp(prefix='test_aerender_')

    try:
        project_path = f"{temp_dir}/test.aep"
        output_path = f"{temp_dir}/preview.mp4"

        # Create dummy project file
        with open(project_path, 'w') as f:
            f.write('mock project')

        # Capture the command that would be executed
        captured_cmd = None

        def mock_subprocess_run(*args, **kwargs):
            nonlocal captured_cmd
            captured_cmd = args[0]

            # Create output file
            with open(output_path, 'wb') as f:
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
                output_path,
                options,
                aerender_path
            )

            # Verify command
            print(f"\nCaptured Command:")
            cmd_str = ' '.join([f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in captured_cmd])
            print(f"  {cmd_str}\n")

            print("Command Analysis:")

            # Check for -OMtemplate
            if '-OMtemplate' in captured_cmd:
                print(f"  ❌ FAIL: Command contains -OMtemplate")
                idx = captured_cmd.index('-OMtemplate')
                template_name = captured_cmd[idx + 1] if idx + 1 < len(captured_cmd) else 'N/A'
                print(f"     Template used: '{template_name}'")
                return False
            else:
                print(f"  ✅ PASS: -OMtemplate removed from command")

            # Check for required parameters
            required = ['-project', '-comp', '-output', '-RStemplate']
            for param in required:
                if param in captured_cmd:
                    print(f"  ✅ Contains {param}")
                else:
                    print(f"  ❌ Missing {param}")
                    return False

            # Check output file extension
            if output_path.endswith('.mp4'):
                print(f"  ✅ Output file has .mp4 extension (AE will use default MP4 encoder)")

            return result

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_command_for_different_formats():
    """Test that command works for different output formats."""

    print("\n" + "="*70)
    print("TEST: Different Output Formats")
    print("="*70)

    formats = [
        ('.mp4', 'MP4 video'),
        ('.mov', 'QuickTime movie'),
        ('.avi', 'AVI video')
    ]

    temp_dir = tempfile.mkdtemp(prefix='test_formats_')

    try:
        for ext, description in formats:
            print(f"\nTesting {ext} format ({description}):")

            project_path = f"{temp_dir}/test.aep"
            output_path = f"{temp_dir}/preview{ext}"

            with open(project_path, 'w') as f:
                f.write('mock project')

            def mock_subprocess_run(*args, **kwargs):
                cmd = args[0]
                with open(output_path, 'wb') as f:
                    f.write(b'mock video')
                return Mock(returncode=0, stdout='Render completed', stderr='')

            with patch('subprocess.run', side_effect=mock_subprocess_run):
                options = {'resolution': 'half', 'duration': 5.0, 'format': 'mp4', 'fps': 15}
                result = render_with_aerender(
                    project_path, 'test-aep', output_path, options,
                    '/Applications/Adobe After Effects 2025/aerender'
                )

                if result:
                    print(f"  ✅ {ext} format works")
                else:
                    print(f"  ❌ {ext} format failed")
                    return False

        return True

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def show_before_after_comparison():
    """Show before/after comparison of aerender commands."""

    print("\n" + "="*70)
    print("BEFORE/AFTER COMPARISON")
    print("="*70)

    print("\n❌ BEFORE (with -OMtemplate):")
    print("  /Applications/Adobe After Effects 2025/aerender")
    print("    -project /tmp/project.aep")
    print("    -comp test-aep")
    print("    -output /previews/preview.mp4")
    print("    -RStemplate 'Best Settings'")
    print("    -OMtemplate H.264  ← This template doesn't exist in AE 2025!")
    print("    -s 0")
    print("    -e 75")

    print("\n✅ AFTER (without -OMtemplate):")
    print("  /Applications/Adobe After Effects 2025/aerender")
    print("    -project /tmp/project.aep")
    print("    -comp test-aep")
    print("    -output /previews/preview.mp4  ← AE uses file extension")
    print("    -RStemplate 'Best Settings'")
    print("    -s 0")
    print("    -e 75")

    print("\n💡 How it works now:")
    print("  - No -OMtemplate parameter specified")
    print("  - After Effects automatically chooses encoder based on file extension")
    print("  - .mp4 → Default MP4 encoder")
    print("  - .mov → Default QuickTime encoder")
    print("  - .avi → Default AVI encoder")
    print("  - More reliable and compatible with all AE versions")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 16 + "AERENDER COMMAND FIX TEST" + " " * 27 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []
    results.append(("Command without -OMtemplate", test_aerender_command_without_omtemplate()))
    results.append(("Different output formats", test_command_for_different_formats()))

    show_before_after_comparison()

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
