#!/usr/bin/env python3
"""
Simple log analysis script

Supports both text and JSON log formats.

Usage:
    python scripts/analyze_logs.py app.log --graphic g1
    python scripts/analyze_logs.py app.log --step psd_parse
    python scripts/analyze_logs.py app.log --timing
    python scripts/analyze_logs.py app.log --errors
    python scripts/analyze_logs.py app.log --correlation abc-123-def
    python scripts/analyze_logs.py app.log --json  # Force JSON mode
"""

import sys
import re
import json
from collections import defaultdict
import argparse


def analyze_logs(log_file, filter_graphic=None, filter_step=None,
                 show_timing=False, show_errors=False, filter_correlation=None,
                 force_json=False):
    """Analyze log file (supports both text and JSON formats)"""

    timings = defaultdict(list)
    errors = []
    steps = []
    correlations = defaultdict(list)

    try:
        with open(log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Try to parse as JSON first
                log_entry = None
                is_json = force_json

                if line.startswith('{'):
                    try:
                        log_entry = json.loads(line)
                        is_json = True
                    except json.JSONDecodeError:
                        pass

                if is_json and log_entry:
                    # JSON format processing
                    context = log_entry.get('context', {})
                    event_type = log_entry.get('event_type', '')
                    message = log_entry.get('message', '')
                    level = log_entry.get('level', '')

                    # Filter by correlation ID
                    if filter_correlation and context.get('correlation_id') != filter_correlation:
                        continue

                    # Filter by graphic
                    if filter_graphic and context.get('graphic_id') != filter_graphic:
                        continue

                    # Filter by step
                    if filter_step and event_type != 'step':
                        continue
                    if filter_step and not message.startswith(filter_step):
                        continue

                    # Collect timing data
                    if event_type == 'timing' and 'duration_ms' in context:
                        # Extract operation name from message (format: "operation_name: 123.4ms")
                        op_match = re.match(r'^(\w+):', message)
                        if op_match:
                            operation = op_match.group(1)
                            duration = context['duration_ms']
                            timings[operation].append(duration)

                    # Collect errors
                    if event_type == 'error' or level == 'ERROR':
                        errors.append(json.dumps(log_entry))

                    # Track correlation IDs
                    if 'correlation_id' in context:
                        corr_id = context['correlation_id']
                        correlations[corr_id].append(json.dumps(log_entry))

                    # Print line if it matches filters
                    if not show_timing and not show_errors:
                        if filter_graphic or filter_step or filter_correlation:
                            print(json.dumps(log_entry, indent=2))

                else:
                    # Text format processing (original code)
                    # Filter by correlation ID if specified
                    if filter_correlation and f"correlation_id={filter_correlation}" not in line:
                        continue

                    # Filter by graphic if specified
                    if filter_graphic and f"graphic_id={filter_graphic}" not in line:
                        continue

                    # Filter by step if specified
                    if filter_step and f"[step:{filter_step}]" not in line:
                        continue

                    # Collect timing data
                    if '[TIMING]' in line:
                        match = re.search(r'\[TIMING\] (\w+): ([\d.]+)ms', line)
                        if match:
                            operation = match.group(1)
                            duration = float(match.group(2))
                            timings[operation].append(duration)

                    # Collect errors
                    if '[ERROR]' in line or 'ERROR' in line:
                        errors.append(line)

                    # Collect steps
                    if '[step:' in line:
                        steps.append(line)

                    # Track correlation IDs
                    corr_match = re.search(r'correlation_id=([^\s]+)', line)
                    if corr_match:
                        corr_id = corr_match.group(1)
                        correlations[corr_id].append(line)

                    # Print line if it matches filters and not showing summaries
                    if not show_timing and not show_errors:
                        if filter_graphic or filter_step or filter_correlation:
                            print(line)

        # Show timing summary
        if show_timing:
            if timings:
                print("\n=== TIMING SUMMARY ===")
                print(f"{'Operation':<25s} {'Avg (ms)':>10s} {'Min (ms)':>10s} {'Max (ms)':>10s} {'Count':>8s}")
                print("-" * 70)
                for operation, durations in sorted(timings.items()):
                    avg = sum(durations) / len(durations)
                    min_d = min(durations)
                    max_d = max(durations)
                    print(f"{operation:<25s} {avg:>10.1f} {min_d:>10.1f} {max_d:>10.1f} {len(durations):>8d}")
            else:
                print("No timing data found")

        # Show errors
        if show_errors:
            if errors:
                print("\n=== ERRORS ===")
                for error in errors:
                    print(error)
            else:
                print("No errors found")

        # Show correlation summary if no specific filter
        if not filter_graphic and not filter_step and not filter_correlation and not show_timing and not show_errors:
            if correlations:
                print(f"\n=== CORRELATION IDS ({len(correlations)} unique) ===")
                for corr_id, lines in sorted(correlations.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                    print(f"{corr_id}: {len(lines)} log entries")

    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing log file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze structured logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Filter by graphic ID
  python scripts/analyze_logs.py app.log --graphic g1

  # Filter by step
  python scripts/analyze_logs.py app.log --step psd_parse

  # Show timing summary
  python scripts/analyze_logs.py app.log --timing

  # Show errors only
  python scripts/analyze_logs.py app.log --errors

  # Filter by correlation ID
  python scripts/analyze_logs.py app.log --correlation abc-123

  # Combine filters
  python scripts/analyze_logs.py app.log --graphic g1 --timing
        '''
    )

    parser.add_argument('log_file', help='Log file to analyze')
    parser.add_argument('--graphic', help='Filter by graphic ID')
    parser.add_argument('--step', help='Filter by step name')
    parser.add_argument('--correlation', help='Filter by correlation ID')
    parser.add_argument('--timing', action='store_true', help='Show timing summary')
    parser.add_argument('--errors', action='store_true', help='Show errors only')
    parser.add_argument('--json', action='store_true', help='Force JSON parsing mode')

    args = parser.parse_args()

    analyze_logs(
        args.log_file,
        filter_graphic=args.graphic,
        filter_step=args.step,
        show_timing=args.timing,
        show_errors=args.errors,
        filter_correlation=args.correlation,
        force_json=args.json
    )


if __name__ == '__main__':
    main()
