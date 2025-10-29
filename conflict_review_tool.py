#!/usr/bin/env python3
"""
Conflict Review Tool

Interactive terminal tool for reviewing and managing detected conflicts.
"""

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.conflict_detector import detect_conflicts
from modules.phase3.conflict_config import load_config, save_config, DEFAULT_CONFLICT_CONFIG
import json
from datetime import datetime
from pathlib import Path


class ConflictReviewer:
    """Interactive conflict review manager."""
    
    def __init__(self, psd_path, aepx_path, config_path=None):
        self.psd_path = psd_path
        self.aepx_path = aepx_path
        self.config_path = config_path
        self.config = load_config(config_path)
        self.decisions = {}
        
    def run(self):
        """Run the interactive review process."""
        print("=" * 70)
        print("CONFLICT REVIEW TOOL")
        print("=" * 70)
        
        # Load and analyze
        print("\n📄 Loading files...")
        psd = parse_psd(self.psd_path)
        aepx = parse_aepx(self.aepx_path)
        print(f"   ✓ PSD: {psd['filename']}")
        print(f"   ✓ AEPX: {aepx['filename']}")
        
        print("\n🔗 Matching content...")
        mappings = match_content_to_slots(psd, aepx)
        print(f"   ✓ Created {len(mappings['mappings'])} mappings")
        
        print("\n🔍 Detecting conflicts...")
        conflicts_result = detect_conflicts(psd, aepx, mappings, self.config)
        print(f"   ✓ Found {conflicts_result['summary']['total']} potential issues")
        
        if conflicts_result['summary']['total'] == 0:
            print("\n✅ No conflicts detected! Ready to proceed.")
            return True
        
        # Review conflicts
        print(f"\n📊 Conflicts breakdown:")
        print(f"   - 🔴 Critical: {conflicts_result['summary']['critical']}")
        print(f"   - ⚠️  Warnings: {conflicts_result['summary']['warning']}")
        print(f"   - ℹ️  Info: {conflicts_result['summary']['info']}")
        
        # Sort by severity
        conflicts = sorted(
            conflicts_result['conflicts'],
            key=lambda c: {'critical': 0, 'warning': 1, 'info': 2}[c['severity']]
        )
        
        print("\n" + "=" * 70)
        print("REVIEWING CONFLICTS")
        print("=" * 70)
        
        for i, conflict in enumerate(conflicts, 1):
            if not self._review_conflict(conflict, i, len(conflicts)):
                print("\n🛑 Review aborted by user.")
                return False
        
        # Show summary
        self._show_summary(conflicts_result)
        
        # Save review log
        self._save_review_log(conflicts_result, psd, aepx)
        
        return self._is_ready_to_proceed()
    
    def _review_conflict(self, conflict, num, total):
        """Review a single conflict. Returns True to continue, False to quit."""
        severity_icons = {'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}
        icon = severity_icons[conflict['severity']]
        
        print(f"\n{'=' * 70}")
        print(f"Conflict {num}/{total} - {icon} {conflict['severity'].upper()}")
        print(f"{'=' * 70}")
        print(f"ID: {conflict['id']}")
        print(f"Type: {conflict['type']}")
        
        if 'psd_layer' in conflict['mapping'] and 'aepx_placeholder' in conflict['mapping']:
            print(f"Mapping: {conflict['mapping']['psd_layer']} → {conflict['mapping']['aepx_placeholder']}")
        
        print(f"\n📋 Issue:")
        print(f"   {conflict['issue']}")
        print(f"\n💡 Suggestion:")
        print(f"   {conflict['suggestion']}")
        
        if conflict.get('auto_fixable'):
            print(f"\n✨ This conflict is auto-fixable")
        
        # Get user decision
        while True:
            print(f"\nOptions:")
            print(f"  [A] Accept - Proceed anyway")
            print(f"  [F] Fix - I'll fix the source file")
            print(f"  [I] Ignore - Mark as false positive")
            print(f"  [C] Configure - Adjust detection thresholds")
            print(f"  [Q] Quit - Abort review")
            
            choice = input(f"\nYour choice: ").strip().upper()
            
            if choice == 'A':
                self.decisions[conflict['id']] = 'accept'
                print("✓ Accepted")
                return True
            
            elif choice == 'F':
                self.decisions[conflict['id']] = 'fix'
                print("✓ Marked for fixing")
                return True
            
            elif choice == 'I':
                self.decisions[conflict['id']] = 'ignore'
                print("✓ Ignored")
                return True
            
            elif choice == 'C':
                self._configure_threshold(conflict)
                # Re-ask for decision
                continue
            
            elif choice == 'Q':
                return False
            
            else:
                print("Invalid choice. Please enter A, F, I, C, or Q.")
    
    def _configure_threshold(self, conflict):
        """Interactive threshold configuration."""
        print(f"\n⚙️  Configure threshold for {conflict['type']}")
        print(f"\nCurrent configuration:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")
        
        print(f"\nWhich setting would you like to adjust? (or 'cancel')")
        setting = input("> ").strip()
        
        if setting == 'cancel' or setting not in self.config:
            print("Configuration unchanged.")
            return
        
        print(f"\nCurrent value for {setting}: {self.config[setting]}")
        new_value = input(f"New value (or 'cancel'): ").strip()
        
        if new_value == 'cancel':
            print("Configuration unchanged.")
            return
        
        try:
            # Try to convert to the same type as current value
            if isinstance(self.config[setting], float):
                self.config[setting] = float(new_value)
            elif isinstance(self.config[setting], int):
                self.config[setting] = int(new_value)
            
            print(f"✓ Updated {setting} to {self.config[setting]}")
            
            # Save config if path provided
            if self.config_path:
                save_config(self.config, self.config_path)
                print(f"✓ Saved to {self.config_path}")
        
        except ValueError:
            print("Invalid value. Configuration unchanged.")
    
    def _show_summary(self, conflicts_result):
        """Show review summary."""
        print(f"\n{'=' * 70}")
        print("REVIEW SUMMARY")
        print(f"{'=' * 70}")
        
        accepted = sum(1 for d in self.decisions.values() if d == 'accept')
        to_fix = sum(1 for d in self.decisions.values() if d == 'fix')
        ignored = sum(1 for d in self.decisions.values() if d == 'ignore')
        
        print(f"\n✅ Conflicts accepted: {accepted}")
        print(f"🔧 Conflicts to fix: {to_fix}")
        print(f"⊘  Conflicts ignored: {ignored}")
        
        critical_unfixed = sum(
            1 for c in conflicts_result['conflicts']
            if c['severity'] == 'critical' and self.decisions.get(c['id']) not in ['accept', 'ignore']
        )
        
        if critical_unfixed > 0:
            print(f"\n⚠️  {critical_unfixed} critical issue(s) not addressed")
    
    def _is_ready_to_proceed(self):
        """Check if ready to proceed."""
        to_fix = sum(1 for d in self.decisions.values() if d == 'fix')
        
        if to_fix > 0:
            print(f"\n🔄 Please fix {to_fix} issue(s) in source files and re-run.")
            return False
        
        print(f"\n✅ Ready to proceed with rendering!")
        return True
    
    def _save_review_log(self, conflicts_result, psd, aepx):
        """Save review decisions to log file."""
        log = {
            "timestamp": datetime.now().isoformat(),
            "psd_file": psd['filename'],
            "aepx_file": aepx['filename'],
            "total_conflicts": conflicts_result['summary']['total'],
            "decisions": self.decisions,
            "conflicts": conflicts_result['conflicts']
        }
        
        with open('conflict_review_log.json', 'w') as f:
            json.dump(log, f, indent=2)
        
        print(f"\n💾 Review log saved to: conflict_review_log.json")


def main():
    """Main entry point."""
    import sys
    
    # Get file paths from command line or use defaults
    psd_path = sys.argv[1] if len(sys.argv) > 1 else 'sample_files/test-photoshop-doc.psd'
    aepx_path = sys.argv[2] if len(sys.argv) > 2 else 'sample_files/test-after-effects-project.aepx'
    config_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    reviewer = ConflictReviewer(psd_path, aepx_path, config_path)
    success = reviewer.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
