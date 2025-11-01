#!/usr/bin/env python3
"""Quick script to check what placeholders are in the AEPX file"""

import sys
from services.aepx_service import AEPXService
from pathlib import Path

def main():
    if len(sys.argv) > 1:
        aepx_path = sys.argv[1]
    else:
        # Use the most recent upload
        uploads_dir = Path("uploads")
        aepx_files = list(uploads_dir.glob("*_aepx_*.aepx"))
        if not aepx_files:
            print("No AEPX files found in uploads/")
            return
        aepx_path = str(sorted(aepx_files, key=lambda p: p.stat().st_mtime)[-1])

    print(f"Checking AEPX file: {aepx_path}")
    print("=" * 70)

    service = AEPXService()
    result = service.parse_aepx(aepx_path)

    if result.is_success():
        data = result.get_data()
        print(f"✅ Successfully parsed AEPX")
        print(f"Compositions: {len(data.get('compositions', []))}")
        print(f"Placeholders: {len(data.get('placeholders', []))}")
        print()
        print("=" * 70)
        print("PLACEHOLDER DETAILS:")
        print("=" * 70)

        for i, ph in enumerate(data.get('placeholders', []), 1):
            print(f"\n{i}. Name: {ph.get('name', 'UNKNOWN')}")
            print(f"   Type: {ph.get('type', 'UNKNOWN')}")
            print(f"   Full data: {ph}")

        print("\n" + "=" * 70)
        print("PLACEHOLDER NAMES LIST:")
        print("=" * 70)
        placeholder_names = [ph.get('name') for ph in data.get('placeholders', [])]
        print(placeholder_names)
    else:
        print(f"❌ Failed to parse AEPX: {result.get_error()}")

if __name__ == "__main__":
    main()
