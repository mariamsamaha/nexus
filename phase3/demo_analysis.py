import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from performance.logging_module import MetricsLogger
from performance.analysis_module import MetricsAnalyzer
from performance.plotting_module import MetricsPlotter


def run_demo():
    """Demonstrate the performance analysis module with existing metrics."""
    
    print("=" * 60)
    print("PERFORMANCE ANALYSIS DEMO")
    print("=" * 60)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    metrics_file = os.path.join(script_dir, "metrics.csv")
    output_dir = os.path.join(script_dir, "demo_results")
    
    # Check if metrics file exists
    if not os.path.exists(metrics_file):
        print(f"Error: Metrics file not found: {metrics_file}")
        print("Please run the load generator first to create metrics.")
        return
    
    # Step 1: Load metrics
    print("\n[Step 1] Loading metrics from CSV...")
    logger = MetricsLogger(output_dir=output_dir)
    logger.load_from_csv(metrics_file)
    print(f"   Loaded {len(logger.metrics)} records")
    
    # Step 2: Create analyzer and compute metrics
    print("\n[Step 2] Computing throughput and latency...")
    analyzer = MetricsAnalyzer(logger)
    
    throughput = analyzer.compute_throughput(window_size_ms=1000.0)
    print(f"   Throughput data points: {len(throughput)}")
    
    latency = analyzer.compute_percentile_latency(window_size_ms=1000.0)
    print(f"   Latency data points: {len(latency)}")
    
    # Step 3: Auto-detect failure periods
    print("\n[Step 3] Detecting failure periods...")
    failures = analyzer.detect_failure_from_metrics(
        latency_spike_threshold_ms=1000.0,
        min_spike_duration_ms=2000.0
    )
    
    if failures:
        failure_start, recovery_end = failures[0]
        print(f"   Detected failure period:")
        print(f"   - Start: {failure_start:.0f} ms")
        print(f"   - End: {recovery_end:.0f} ms")
        print(f"   - Duration: {(recovery_end - failure_start)/1000:.1f} seconds")
        
        # Add failure annotation
        analyzer.annotate_failure_events(
            failure_timestamps_ms=[failure_start],
            recovery_timestamps_ms=[recovery_end]
        )
    else:
        print("   No significant failure periods detected")
        failure_start, recovery_end = None, None
    
    # Step 4: Compute recovery time
    print("\n[Step 4] Computing recovery time...")
    if failure_start:
        recovery = analyzer.compute_recovery_time(failure_start_ms=failure_start)
        if recovery:
            print(f"   Recovery Duration: {recovery.recovery_duration_seconds:.2f} seconds")
            print(f"   Baseline P95 Latency: {recovery.baseline_latency_ms:.2f} ms")
            print(f"   Recovered P95 Latency: {recovery.recovered_latency_ms:.2f} ms")
    else:
        print("   Skipped (no failure detected)")
    
    # Step 5: Phase separation
    print("\n[Step 5] Separating phases...")
    if failure_start and recovery_end:
        phases = analyzer.separate_phases(failure_start, recovery_end)
        for name, metrics in phases.items():
            print(f"   {name}:")
            print(f"      Requests: {metrics.request_count}")
            print(f"      Throughput: {metrics.throughput_avg:.2f} req/s")
            print(f"      P95 Latency: {metrics.latency_p95_avg:.2f} ms")
            print(f"      Success Rate: {metrics.success_rate:.1f}%")
    else:
        print("   Skipped (no failure detected)")
    
    # Step 6: Generate plots
    print("\n[Step 6] Generating plots...")
    plotter = MetricsPlotter(analyzer, output_dir=output_dir)
    
    plots = plotter.generate_all_plots(
        failure_start_ms=failure_start,
        recovery_end_ms=recovery_end
    )
    
    # Step 7: Print summary
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    summary = analyzer.get_summary_statistics()
    
    print(f"\n  Total Requests:     {summary['total_requests']}")
    print(f"  Duration:           {summary['duration_seconds']:.1f}s")
    print(f"  Throughput:         {summary['overall_throughput_rps']:.2f} req/s")
    print(f"\n  Latency:")
    print(f"    Min:              {summary['latency_min_ms']:.2f} ms")
    print(f"    Mean:             {summary['latency_mean_ms']:.2f} ms")
    print(f"    P95:              {summary['latency_p95_ms']:.2f} ms")
    print(f"    Max:              {summary['latency_max_ms']:.2f} ms")
    print(f"\n  Status:")
    print(f"    Success:          {summary['success_count']}")
    print(f"    Recovered:        {summary['recovered_count']}")
    print(f"    Failed:           {summary['failed_count']}")
    print(f"    Success Rate:     {summary['success_rate_percent']:.1f}%")
    
    print(f"\n  Output Directory:   {output_dir}")
    print(f"  Plots Generated:    {len(plots)}")
    for plot in plots:
        print(f"    - {os.path.basename(plot)}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
