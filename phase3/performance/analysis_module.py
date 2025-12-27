import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .logging_module import MetricsLogger, RequestMetric, FailureEvent


@dataclass
class ThroughputPoint:
    """Throughput measurement at a specific time."""
    window_start_ms: float
    window_end_ms: float
    requests_per_second: float
    success_count: int
    failed_count: int


@dataclass
class LatencyPoint:
    window_start_ms: float
    window_end_ms: float
    p95_ms: float
    mean_ms: float
    sample_count: int


@dataclass
class PhaseMetrics:
    """Metrics for a specific phase (before/during/after failure)."""
    phase_name: str
    start_ms: float
    end_ms: float
    throughput_avg: float
    latency_p95_avg: float
    request_count: int
    success_rate: float


@dataclass  
class RecoveryAnalysis:
    """Recovery time calculation results."""
    failure_time_ms: float
    recovery_time_ms: float
    recovery_duration_seconds: float
    baseline_latency_ms: float
    baseline_throughput: float
    recovered_latency_ms: float
    recovered_throughput: float


class MetricsAnalyzer:
    """Analyzes collected metrics for fault-tolerance performance evaluation."""
    
    def __init__(self, logger: MetricsLogger):
        self.logger = logger
        self._throughput_data: List[ThroughputPoint] = []
        self._latency_data: List[LatencyPoint] = []
    
    def compute_throughput(
        self,
        window_size_ms: float = 1000.0,
        min_duration_ms: float = 60000.0
    ) -> List[ThroughputPoint]:
        """
        Compute throughput (requests/second) using time windows.
        
        Args:
            window_size_ms: Size of each time window in milliseconds
            min_duration_ms: Minimum duration to measure (60 seconds default)
        """
        if not self.logger.metrics:
            return []
        
        metrics = sorted(self.logger.metrics, key=lambda m: m.timestamp_ms)
        start_time = metrics[0].timestamp_ms
        end_time = metrics[-1].timestamp_ms
        
        # Ensure minimum duration coverage
        actual_duration = end_time - start_time
        if actual_duration < min_duration_ms:
            print(f"Warning: Data spans {actual_duration/1000:.1f}s, less than {min_duration_ms/1000:.0f}s")
        
        throughput_points = []
        current_window_start = start_time
        
        while current_window_start < end_time:
            window_end = current_window_start + window_size_ms
            
            # Count requests in this window
            window_metrics = [
                m for m in metrics 
                if current_window_start <= m.timestamp_ms < window_end
            ]
            
            success_count = sum(1 for m in window_metrics if m.status in ["SUCCESS", "RECOVERED"])
            failed_count = sum(1 for m in window_metrics if m.status in ["FAILED", "TIMEOUT"])
            
            # Convert to requests per second
            rps = len(window_metrics) / (window_size_ms / 1000.0)
            
            throughput_points.append(ThroughputPoint(
                window_start_ms=current_window_start,
                window_end_ms=window_end,
                requests_per_second=rps,
                success_count=success_count,
                failed_count=failed_count
            ))
            
            current_window_start = window_end
        
        self._throughput_data = throughput_points
        return throughput_points
    
    def compute_percentile_latency(
        self,
        window_size_ms: float = 1000.0,
        sliding: bool = False,
        slide_step_ms: float = 500.0
    ) -> List[LatencyPoint]:
        """
        Compute p50, p95, p99 latency over time.
        
        Args:
            window_size_ms: Size of each time window in milliseconds
            sliding: Use sliding window (True) or fixed window (False)
            slide_step_ms: Step size for sliding window
        """
        if not self.logger.metrics:
            return []
        
        metrics = sorted(self.logger.metrics, key=lambda m: m.timestamp_ms)
        start_time = metrics[0].timestamp_ms
        end_time = metrics[-1].timestamp_ms
        
        latency_points = []
        step = slide_step_ms if sliding else window_size_ms
        current_window_start = start_time
        
        while current_window_start < end_time:
            window_end = current_window_start + window_size_ms
            
            # Get latencies in this window (only successful requests for accurate latency)
            window_latencies = [
                m.latency_ms for m in metrics 
                if current_window_start <= m.timestamp_ms < window_end
            ]
            
            if window_latencies:
                latencies_arr = np.array(window_latencies)
                
                latency_points.append(LatencyPoint(
                    window_start_ms=current_window_start,
                    window_end_ms=window_end,
                    p95_ms=float(np.percentile(latencies_arr, 95)),
                    mean_ms=float(np.mean(latencies_arr)),
                    sample_count=len(window_latencies)
                ))
            
            current_window_start += step
        
        self._latency_data = latency_points
        return latency_points
    
    def annotate_failure_events(
        self,
        failure_timestamps_ms: List[float],
        recovery_timestamps_ms: Optional[List[float]] = None
    ) -> List[FailureEvent]:
        """
        Add failure injection event annotations.
        
        Args:
            failure_timestamps_ms: List of failure injection times (ms)
            recovery_timestamps_ms: List of recovery completion times (ms)
        """
        if recovery_timestamps_ms is None:
            recovery_timestamps_ms = [None] * len(failure_timestamps_ms)
        
        events = []
        for fail_time, rec_time in zip(failure_timestamps_ms, recovery_timestamps_ms):
            event = FailureEvent(
                failure_start_ms=fail_time,
                recovery_time_ms=rec_time,
                event_type="injected_failure"
            )
            events.append(event)
            self.logger.failure_events.append(event)
        
        return events
    
    def detect_failure_from_metrics(
        self,
        latency_spike_threshold_ms: float = 1000.0,
        min_spike_duration_ms: float = 2000.0
    ) -> List[Tuple[float, float]]:
        """
        Auto-detect failure periods from latency spikes.
        
        Returns list of (failure_start_ms, recovery_end_ms) tuples.
        """
        if not self.logger.metrics:
            return []
        
        metrics = sorted(self.logger.metrics, key=lambda m: m.timestamp_ms)
        
        # Calculate baseline latency from first 10% of requests
        baseline_count = max(5, len(metrics) // 10)
        baseline_latencies = [m.latency_ms for m in metrics[:baseline_count]]
        baseline_p95 = np.percentile(baseline_latencies, 95)
        
        # Detect spikes above threshold
        failure_periods = []
        in_failure = False
        failure_start = None
        
        for m in metrics:
            is_spike = m.latency_ms > latency_spike_threshold_ms or m.latency_ms > baseline_p95 * 3
            
            if is_spike and not in_failure:
                in_failure = True
                failure_start = m.timestamp_ms
            elif not is_spike and in_failure:
                # Check if spike lasted long enough
                if m.timestamp_ms - failure_start >= min_spike_duration_ms:
                    failure_periods.append((failure_start, m.timestamp_ms))
                in_failure = False
                failure_start = None
        
        return failure_periods
    
    def separate_phases(
        self,
        failure_start_ms: float,
        recovery_end_ms: float,
        buffer_ms: float = 1000.0
    ) -> Dict[str, PhaseMetrics]:
        """
        Separate metrics into before/during/after failure phases.
        """
        if not self.logger.metrics:
            return {}
        
        metrics = sorted(self.logger.metrics, key=lambda m: m.timestamp_ms)
        
        phases = {
            "before_failure": [],
            "during_failure": [],
            "after_recovery": []
        }
        
        for m in metrics:
            if m.timestamp_ms < failure_start_ms - buffer_ms:
                phases["before_failure"].append(m)
            elif m.timestamp_ms >= failure_start_ms and m.timestamp_ms <= recovery_end_ms:
                phases["during_failure"].append(m)
            elif m.timestamp_ms > recovery_end_ms + buffer_ms:
                phases["after_recovery"].append(m)
        
        results = {}
        for phase_name, phase_metrics in phases.items():
            if not phase_metrics:
                continue
            
            latencies = [m.latency_ms for m in phase_metrics]
            success_count = sum(1 for m in phase_metrics if m.status == "SUCCESS")
            
            t_start = min(m.timestamp_ms for m in phase_metrics)
            t_end = max(m.timestamp_ms for m in phase_metrics)
            duration_s = (t_end - t_start) / 1000.0 if t_end > t_start else 1.0
            
            results[phase_name] = PhaseMetrics(
                phase_name=phase_name,
                start_ms=t_start,
                end_ms=t_end,
                throughput_avg=len(phase_metrics) / duration_s,
                latency_p95_avg=float(np.percentile(latencies, 95)),
                request_count=len(phase_metrics),
                success_rate=success_count / len(phase_metrics) * 100
            )
        
        return results
    
    def compute_recovery_time(
        self,
        failure_start_ms: float,
        latency_threshold_factor: float = 1.5,
        throughput_threshold_factor: float = 0.8
    ) -> Optional[RecoveryAnalysis]:
        """
        Compute recovery time as duration between failure injection and return to baseline.
        
        Recovery is determined when:
        - Latency returns to within latency_threshold_factor of baseline
        - Throughput returns to throughput_threshold_factor of baseline
        """
        if not self.logger.metrics or not self._throughput_data or not self._latency_data:
            self.compute_throughput()
            self.compute_percentile_latency()
        
        # Find baseline metrics (before failure)
        before_failure = [m for m in self.logger.metrics if m.timestamp_ms < failure_start_ms]
        
        if len(before_failure) < 5:
            print("Warning: Not enough pre-failure data for baseline calculation")
            return None
        
        baseline_latencies = [m.latency_ms for m in before_failure]
        baseline_latency = float(np.percentile(baseline_latencies, 95))
        
        # Calculate baseline throughput
        bf_start = min(m.timestamp_ms for m in before_failure)
        bf_end = max(m.timestamp_ms for m in before_failure)
        bf_duration = (bf_end - bf_start) / 1000.0
        baseline_throughput = len(before_failure) / bf_duration if bf_duration > 0 else 0
        
        # Find recovery point
        after_failure = [m for m in self.logger.metrics if m.timestamp_ms >= failure_start_ms]
        after_failure.sort(key=lambda m: m.timestamp_ms)
        
        recovery_time_ms = None
        recovered_latency = None
        recovered_throughput = None
        
        # Sliding window to detect stable recovery
        window_size = 5
        for i in range(len(after_failure) - window_size):
            window = after_failure[i:i + window_size]
            window_latencies = [m.latency_ms for m in window]
            window_p95 = float(np.percentile(window_latencies, 95))
            
            # Check if latency has recovered
            latency_recovered = window_p95 <= baseline_latency * latency_threshold_factor
            
            # Check if mostly successful
            success_rate = sum(1 for m in window if m.status == "SUCCESS") / len(window)
            throughput_recovered = success_rate >= throughput_threshold_factor
            
            if latency_recovered and throughput_recovered:
                recovery_time_ms = window[0].timestamp_ms
                recovered_latency = window_p95
                
                # Calculate recovered throughput
                w_duration = (window[-1].timestamp_ms - window[0].timestamp_ms) / 1000.0
                recovered_throughput = len(window) / w_duration if w_duration > 0 else 0
                break
        
        if recovery_time_ms is None:
            print("Warning: System did not fully recover within the measurement period")
            return None
        
        return RecoveryAnalysis(
            failure_time_ms=failure_start_ms,
            recovery_time_ms=recovery_time_ms,
            recovery_duration_seconds=(recovery_time_ms - failure_start_ms) / 1000.0,
            baseline_latency_ms=baseline_latency,
            baseline_throughput=baseline_throughput,
            recovered_latency_ms=recovered_latency,
            recovered_throughput=recovered_throughput
        )
    
    def get_summary_statistics(self) -> Dict:
        """Get overall summary statistics."""
        if not self.logger.metrics:
            return {}
        
        latencies = [m.latency_ms for m in self.logger.metrics]
        latencies_arr = np.array(latencies)
        
        metrics = self.logger.metrics
        start_time = min(m.timestamp_ms for m in metrics)
        end_time = max(m.timestamp_ms for m in metrics)
        duration_s = (end_time - start_time) / 1000.0
        
        counts = self.logger.get_metrics_count()
        
        return {
            "total_requests": len(metrics),
            "duration_seconds": duration_s,
            "overall_throughput_rps": len(metrics) / duration_s if duration_s > 0 else 0,
            "latency_min_ms": float(np.min(latencies_arr)),
            "latency_max_ms": float(np.max(latencies_arr)),
            "latency_mean_ms": float(np.mean(latencies_arr)),
            "latency_p95_ms": float(np.percentile(latencies_arr, 95)),
            "success_count": counts["SUCCESS"],
            "failed_count": counts["FAILED"],
            "recovered_count": counts["RECOVERED"],
            "success_rate_percent": (counts["SUCCESS"] + counts["RECOVERED"]) / len(metrics) * 100
        }
