#!/usr/bin/env python3
"""
Usage:
    python run_analysis.py --input metrics.csv --output ./results
    python run_analysis.py --input metrics.csv --failure-time 1766783038106 --recovery-time 1766783078091
"""

import argparse
import os
import sys
import json
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance.logging_module import MetricsLogger
from performance.analysis_module import MetricsAnalyzer
from performance.plotting_module import MetricsPlotter


def run_analysis(
    input_file: str,
    output_dir: str = "./results",
    failure_time_ms: Optional[float] = None,
    recovery_time_ms: Optional[float] = None,
    window_size_ms: float = 1000.0,
    auto_detect_failure: bool = True
) -> dict:
    """
    Args:
        input_file: Path to metrics CSV or JSON file
        output_dir: Directory for output files
        failure_time_ms: Failure injection timestamp (ms)
        recovery_time_ms: Recovery completion timestamp (ms)
        window_size_ms: Time window size for analysis
        auto_detect_failure: Auto-detect failure periods if not provided
    
    Returns:
        Dictionary with analysis results
    """
    print("=" * 60)
    print("PERFORMANCE MEASUREMENT AND ANALYSIS")
    print("=" * 60)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Load metrics
    print("\n[1/6] Loading metrics...")
    logger = MetricsLogger(output_dir=output_dir)
    
    if input_file.endswith('.json'):
        logger.load_from_json(input_file)
    else:
        logger.load_from_csv(input_file)
    
    print(f"   Loaded {len(logger.metrics)} request records")
    counts = logger.get_metrics_count()
    print(f"   Status breakdown: {counts}")
    
    # Step 2: Initialize analyzer
    print("\n[2/6] Computing throughput...")
    analyzer = MetricsAnalyzer(logger)
    throughput_data = analyzer.compute_throughput(window_size_ms=window_size_ms)
    print(f"   Generated {len(throughput_data)} throughput data points")
    
    # Step 3: Compute latency percentiles
    print("\n[3/6] Computing latency percentiles...")
    latency_data = analyzer.compute_percentile_latency(window_size_ms=window_size_ms)
    print(f"   Generated {len(latency_data)} latency data points")
    
    # Step 4: Detect or use provided failure times
    print("\n[4/6] Processing failure events...")
    
    if failure_time_ms is None and auto_detect_failure:
        # Auto-detect from latency spikes
        failure_periods = analyzer.detect_failure_from_metrics(
            latency_spike_threshold_ms=1000.0,
            min_spike_duration_ms=2000.0
        )
        
        if failure_periods:
            failure_time_ms = failure_periods[0][0]
            recovery_time_ms = failure_periods[0][1]
            print(f"   Auto-detected failure period:")
            print(f"   Failure start: {failure_time_ms:.0f} ms")
            print(f"   Recovery end:  {recovery_time_ms:.0f} ms")
        else:
            print("   No failure periods detected automatically")
    
    # Add failure annotations if times are available
    if failure_time_ms:
        analyzer.annotate_failure_events(
            failure_timestamps_ms=[failure_time_ms],
            recovery_timestamps_ms=[recovery_time_ms] if recovery_time_ms else None
        )
        print(f"   Annotated {len(analyzer.logger.failure_events)} failure event(s)")
    
    # Step 5: Compute recovery time
    print("\n[5/6] Computing recovery time...")
    recovery_analysis = None
    phase_metrics = None
    
    if failure_time_ms:
        recovery_analysis = analyzer.compute_recovery_time(failure_start_ms=failure_time_ms)
        
        if recovery_analysis:
            print(f"   Recovery Duration: {recovery_analysis.recovery_duration_seconds:.2f} seconds")
            print(f"   Baseline Latency (P95): {recovery_analysis.baseline_latency_ms:.2f} ms")
            print(f"   Recovered Latency (P95): {recovery_analysis.recovered_latency_ms:.2f} ms")
        
        # Separate phases
        if recovery_time_ms:
            phase_metrics = analyzer.separate_phases(failure_time_ms, recovery_time_ms)
            print(f"   Separated {len(phase_metrics)} phases: {list(phase_metrics.keys())}")
    else:
        print("   No failure times available - skipping recovery analysis")
    
    # Step 6: Generate plots
    print("\n[6/6] Generating plots...")
    plotter = MetricsPlotter(analyzer, output_dir=output_dir)
    
    plot_files = plotter.generate_all_plots(
        failure_start_ms=failure_time_ms,
        recovery_end_ms=recovery_time_ms
    )
    
    # Get summary statistics
    summary = analyzer.get_summary_statistics()
    
    # Print summary
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nTotal Requests: {summary.get('total_requests', 0)}")
    print(f"Duration: {summary.get('duration_seconds', 0):.1f} seconds")
    print(f"Overall Throughput: {summary.get('overall_throughput_rps', 0):.2f} req/s")
    print(f"P95 Latency: {summary.get('latency_p95_ms', 0):.2f} ms")
    print(f"Success Rate: {summary.get('success_rate_percent', 0):.1f}%")
    
    if recovery_analysis:
        print(f"\nRecovery Time: {recovery_analysis.recovery_duration_seconds:.2f} seconds")
    
    print(f"\nGenerated {len(plot_files)} plot(s) in: {output_dir}")
    
    # Save results to JSON
    results = {
        "summary": summary,
        "recovery_analysis": {
            "failure_time_ms": recovery_analysis.failure_time_ms if recovery_analysis else None,
            "recovery_time_ms": recovery_analysis.recovery_time_ms if recovery_analysis else None,
            "recovery_duration_seconds": recovery_analysis.recovery_duration_seconds if recovery_analysis else None,
            "baseline_latency_ms": recovery_analysis.baseline_latency_ms if recovery_analysis else None,
            "baseline_throughput": recovery_analysis.baseline_throughput if recovery_analysis else None,
        } if recovery_analysis else None,
        "phase_metrics": {
            name: {
                "throughput_avg": pm.throughput_avg,
                "latency_p95_avg": pm.latency_p95_avg,
                "request_count": pm.request_count,
                "success_rate": pm.success_rate
            } for name, pm in phase_metrics.items()
        } if phase_metrics else None,
        "plot_files": plot_files
    }
    
    results_file = os.path.join(output_dir, "analysis_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Performance Measurement and Analysis for Fault-Tolerant gRPC Systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis with auto-detection
  python run_analysis.py --input ../metrics.csv

  # Analysis with manual failure times (in milliseconds)
  python run_analysis.py --input ../metrics.csv \\
      --failure-time 1766783038106 \\
      --recovery-time 1766783078091

  # Custom output directory and window size
  python run_analysis.py --input ../metrics.csv \\
      --output ./my_results \\
      --window-size 2000
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input metrics file (CSV or JSON)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="./results",
        help="Output directory for plots and results (default: ./results)"
    )
    
    parser.add_argument(
        "--failure-time",
        type=float,
        default=None,
        help="Failure injection timestamp in milliseconds"
    )
    
    parser.add_argument(
        "--recovery-time",
        type=float,
        default=None,
        help="Recovery completion timestamp in milliseconds"
    )
    
    parser.add_argument(
        "--window-size",
        type=float,
        default=1000.0,
        help="Time window size in milliseconds (default: 1000)"
    )
    
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Disable automatic failure detection"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Run analysis
    results = run_analysis(
        input_file=args.input,
        output_dir=args.output,
        failure_time_ms=args.failure_time,
        recovery_time_ms=args.recovery_time,
        window_size_ms=args.window_size,
        auto_detect_failure=not args.no_auto_detect
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
