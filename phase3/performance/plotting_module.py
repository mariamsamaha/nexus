
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
import os

from .logging_module import MetricsLogger, FailureEvent
from .analysis_module import MetricsAnalyzer, ThroughputPoint, LatencyPoint


class MetricsPlotter:
    """Generates performance visualization plots."""
    
    def __init__(
        self,
        analyzer: MetricsAnalyzer,
        output_dir: str = ".",
        style: str = "seaborn-v0_8-darkgrid"
    ):
        self.analyzer = analyzer
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Try to set style, fall back to default if not available
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')
        
        # Color scheme
        self.colors = {
            "primary": "#2196F3",
            "secondary": "#4CAF50",
            "failure": "#F44336",
            "recovery": "#4CAF50",
            "warning": "#FF9800",
            "background": "#FAFAFA"
        }
    
    def _ms_to_relative_seconds(self, timestamps_ms: List[float]) -> List[float]:
        """Convert timestamps to relative seconds from start."""
        if not timestamps_ms:
            return []
        min_ts = min(timestamps_ms)
        return [(ts - min_ts) / 1000.0 for ts in timestamps_ms]
    
    def _add_failure_markers(
        self,
        ax: plt.Axes,
        base_time_ms: float,
        failure_events: List[FailureEvent]
    ) -> None:
        """Add vertical markers for failure and recovery points."""
        for i, event in enumerate(failure_events):
            # Failure start marker
            fail_time_rel = (event.failure_start_ms - base_time_ms) / 1000.0
            ax.axvline(
                x=fail_time_rel,
                color=self.colors["failure"],
                linestyle='--',
                linewidth=2,
                label='Failure Injection' if i == 0 else None
            )
            ax.annotate(
                'FAILURE',
                xy=(fail_time_rel, ax.get_ylim()[1] * 0.95),
                fontsize=8,
                color=self.colors["failure"],
                rotation=90,
                va='top'
            )
            
            # Recovery marker
            if event.recovery_time_ms:
                rec_time_rel = (event.recovery_time_ms - base_time_ms) / 1000.0
                ax.axvline(
                    x=rec_time_rel,
                    color=self.colors["recovery"],
                    linestyle=':',
                    linewidth=2,
                    label='Recovery Complete' if i == 0 else None
                )
                ax.annotate(
                    'RECOVERY',
                    xy=(rec_time_rel, ax.get_ylim()[1] * 0.95),
                    fontsize=8,
                    color=self.colors["recovery"],
                    rotation=90,
                    va='top'
                )
    
    def plot_latency_over_time(
        self,
        filename: str = "latency_vs_time.png",
        figsize: Tuple[int, int] = (12, 6)
    ) -> str:
        latency_data = self.analyzer._latency_data
        if not latency_data:
            latency_data = self.analyzer.compute_percentile_latency()
        
        if not latency_data:
            print("No latency data available for plotting")
            return ""
        
        fig, ax = plt.subplots(figsize=figsize)
        
        base_time = latency_data[0].window_start_ms
        times = [(lp.window_start_ms - base_time) / 1000.0 for lp in latency_data]
        
        # Plot P95 latency
        p95_values = [lp.p95_ms for lp in latency_data]
        ax.plot(times, p95_values, label='P95 Latency',
               color=self.colors["primary"], linewidth=2)
        ax.fill_between(times, 0, p95_values, alpha=0.2, color=self.colors["primary"])
        
        # Add failure markers
        if self.analyzer.logger.failure_events:
            self._add_failure_markers(ax, base_time, self.analyzer.logger.failure_events)
        
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Latency (ms)', fontsize=12)
        ax.set_title('Request Latency Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # Set y-axis to start from 0
        ax.set_ylim(bottom=0)
        
        plt.tight_layout()
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def plot_throughput_over_time(
        self,
        filename: str = "throughput_vs_time.png",
        figsize: Tuple[int, int] = (12, 6)
    ) -> str:
        """
        Generate Throughput (req/sec) vs Time plot.
        Shows throughput dips and recovery behavior.
        """
        throughput_data = self.analyzer._throughput_data
        if not throughput_data:
            throughput_data = self.analyzer.compute_throughput()
        
        if not throughput_data:
            print("No throughput data available for plotting")
            return ""
        
        fig, ax = plt.subplots(figsize=figsize)
        
        base_time = throughput_data[0].window_start_ms
        times = [(tp.window_start_ms - base_time) / 1000.0 for tp in throughput_data]
        rps_values = [tp.requests_per_second for tp in throughput_data]
        
        # Plot throughput
        ax.plot(times, rps_values, label='Throughput',
               color=self.colors["secondary"], linewidth=2)
        ax.fill_between(times, 0, rps_values, alpha=0.3, color=self.colors["secondary"])
        
        # Highlight low throughput periods
        avg_throughput = np.mean(rps_values)
        low_threshold = avg_throughput * 0.5
        for i, (t, rps) in enumerate(zip(times, rps_values)):
            if rps < low_threshold and rps < avg_throughput:
                ax.axvspan(t, t + 1, alpha=0.1, color=self.colors["failure"])
        
        # Add failure markers
        if self.analyzer.logger.failure_events:
            self._add_failure_markers(ax, base_time, self.analyzer.logger.failure_events)
        
        # Add average line
        ax.axhline(y=avg_throughput, color='gray', linestyle='--', 
                  alpha=0.7, label=f'Average ({avg_throughput:.1f} req/s)')
        
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Requests per Second', fontsize=12)
        ax.set_title('System Throughput Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)
        
        plt.tight_layout()
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def plot_combined_dashboard(
        self,
        filename: str = "performance_dashboard.png",
        figsize: Tuple[int, int] = (14, 10)
    ) -> str:
        """Generate combined dashboard with latency, throughput, and summary."""
        fig = plt.figure(figsize=figsize)
        
        # Create grid
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.3, wspace=0.25)
        
        # Get data
        latency_data = self.analyzer._latency_data or self.analyzer.compute_percentile_latency()
        throughput_data = self.analyzer._throughput_data or self.analyzer.compute_throughput()
        summary = self.analyzer.get_summary_statistics()
        
        if not latency_data or not throughput_data:
            print("Insufficient data for dashboard")
            return ""
        
        base_time = throughput_data[0].window_start_ms
        
        # Latency plot (top left)
        ax1 = fig.add_subplot(gs[0, 0])
        times = [(lp.window_start_ms - base_time) / 1000.0 for lp in latency_data]
        p95_values = [lp.p95_ms for lp in latency_data]
        ax1.plot(times, p95_values, color=self.colors["primary"], linewidth=2)
        ax1.fill_between(times, 0, p95_values, alpha=0.2, color=self.colors["primary"])
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('P95 Latency (ms)')
        ax1.set_title('P95 Latency Over Time', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(bottom=0)
        
        if self.analyzer.logger.failure_events:
            self._add_failure_markers(ax1, base_time, self.analyzer.logger.failure_events)
        
        # Throughput plot (top right)
        ax2 = fig.add_subplot(gs[0, 1])
        times = [(tp.window_start_ms - base_time) / 1000.0 for tp in throughput_data]
        rps_values = [tp.requests_per_second for tp in throughput_data]
        ax2.plot(times, rps_values, color=self.colors["secondary"], linewidth=2)
        ax2.fill_between(times, 0, rps_values, alpha=0.3, color=self.colors["secondary"])
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Requests/sec')
        ax2.set_title('Throughput Over Time', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(bottom=0)
        
        if self.analyzer.logger.failure_events:
            self._add_failure_markers(ax2, base_time, self.analyzer.logger.failure_events)
        
        # Latency distribution (bottom left)
        ax3 = fig.add_subplot(gs[1, 0])
        latencies = [m.latency_ms for m in self.analyzer.logger.metrics]
        ax3.hist(latencies, bins=50, color=self.colors["primary"], 
                alpha=0.7, edgecolor='white')
        ax3.axvline(summary.get('latency_p95_ms', 0), color=self.colors["failure"],
                   linestyle='--', label=f"P95: {summary.get('latency_p95_ms', 0):.1f}ms")
        ax3.set_xlabel('Latency (ms)')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Latency Distribution', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Summary stats (bottom right)
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis('off')
        
        summary_text = f"""
        PERFORMANCE SUMMARY
        {'='*40}
        
        Total Requests:     {summary.get('total_requests', 0):,}
        Duration:           {summary.get('duration_seconds', 0):.1f}s
        
        THROUGHPUT
        Overall:            {summary.get('overall_throughput_rps', 0):.2f} req/s
        
        LATENCY
        Min:                {summary.get('latency_min_ms', 0):.2f} ms
        Mean:               {summary.get('latency_mean_ms', 0):.2f} ms
        P95:                {summary.get('latency_p95_ms', 0):.2f} ms
        Max:                {summary.get('latency_max_ms', 0):.2f} ms
        
        REQUEST STATUS
        Success:            {summary.get('success_count', 0):,}
        Recovered:          {summary.get('recovered_count', 0):,}
        Failed:             {summary.get('failed_count', 0):,}
        Success Rate:       {summary.get('success_rate_percent', 0):.1f}%
        """
        
        ax4.text(0.1, 0.95, summary_text, transform=ax4.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle('Fault-Tolerance Performance Dashboard', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return filepath
    
    def plot_phase_comparison(
        self,
        failure_start_ms: float,
        recovery_end_ms: float,
        filename: str = "phase_comparison.png",
        figsize: Tuple[int, int] = (12, 5)
    ) -> str:
        """Generate bar chart comparing metrics across failure phases."""
        phases = self.analyzer.separate_phases(failure_start_ms, recovery_end_ms)
        
        if not phases:
            print("No phase data available")
            return ""
        
        fig, axes = plt.subplots(1, 3, figsize=figsize)
        
        phase_names = list(phases.keys())
        phase_labels = ['Before\nFailure', 'During\nFailure', 'After\nRecovery'][:len(phase_names)]
        colors = [self.colors["secondary"], self.colors["failure"], self.colors["primary"]]
        
        # Throughput comparison
        throughputs = [phases[p].throughput_avg for p in phase_names]
        axes[0].bar(phase_labels, throughputs, color=colors[:len(phase_names)])
        axes[0].set_ylabel('Requests/sec')
        axes[0].set_title('Throughput by Phase', fontweight='bold')
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Latency comparison  
        latencies = [phases[p].latency_p95_avg for p in phase_names]
        axes[1].bar(phase_labels, latencies, color=colors[:len(phase_names)])
        axes[1].set_ylabel('P95 Latency (ms)')
        axes[1].set_title('P95 Latency by Phase', fontweight='bold')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Success rate comparison
        success_rates = [phases[p].success_rate for p in phase_names]
        axes[2].bar(phase_labels, success_rates, color=colors[:len(phase_names)])
        axes[2].set_ylabel('Success Rate (%)')
        axes[2].set_title('Success Rate by Phase', fontweight='bold')
        axes[2].set_ylim(0, 105)
        axes[2].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_all_plots(
        self,
        failure_start_ms: Optional[float] = None,
        recovery_end_ms: Optional[float] = None
    ) -> List[str]:
        """Generate all standard plots and return list of filepaths."""
        plots = []
        
        # Required plots
        latency_plot = self.plot_latency_over_time()
        if latency_plot:
            plots.append(latency_plot)
            print(f"Generated: {latency_plot}")
        
        throughput_plot = self.plot_throughput_over_time()
        if throughput_plot:
            plots.append(throughput_plot)
            print(f"Generated: {throughput_plot}")
        
        dashboard = self.plot_combined_dashboard()
        if dashboard:
            plots.append(dashboard)
            print(f"Generated: {dashboard}")
        
        # Phase comparison if failure times provided
        if failure_start_ms and recovery_end_ms:
            phase_plot = self.plot_phase_comparison(failure_start_ms, recovery_end_ms)
            if phase_plot:
                plots.append(phase_plot)
                print(f"Generated: {phase_plot}")
        
        return plots
