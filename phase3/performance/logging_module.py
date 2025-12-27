import csv
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional, List
from enum import Enum


class RequestStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"
    TIMEOUT = "TIMEOUT"


@dataclass
class RequestMetric:
    timestamp_ms: float          # when response was received (ms)
    send_time_ms: float          # when request was sent (ms)
    latency_ms: float            # end-to-end latency in ms
    status: str                  # SUCCESS, FAILED, RECOVERED, TIMEOUT
    server_replica: str          # which server handled the request
    request_id: Optional[str] = None


@dataclass
class FailureEvent:
    failure_start_ms: float      # when failure was injected
    recovery_time_ms: Optional[float] = None  # when recovery completed
    event_type: str = "crash"    # crash, network_timeout, etc.
    description: str = ""


class MetricsLogger:    
    def __init__(self, output_dir: str = ".", file_prefix: str = "metrics"):
        self.output_dir = output_dir
        self.file_prefix = file_prefix
        self.metrics: List[RequestMetric] = []
        self.failure_events: List[FailureEvent] = []
        
        os.makedirs(output_dir, exist_ok=True)
    
    def log_request(
        self,
        send_time: float,
        receive_time: float,
        status: str,
        server_replica: str,
        request_id: Optional[str] = None
    ) -> RequestMetric:

        metric = RequestMetric(
            timestamp_ms=receive_time * 1000,
            send_time_ms=send_time * 1000,
            latency_ms=(receive_time - send_time) * 1000,
            status=status,
            server_replica=server_replica,
            request_id=request_id
        )
        self.metrics.append(metric)
        return metric
    
    def log_failure_event(
        self,
        failure_start: float,
        recovery_time: Optional[float] = None,
        event_type: str = "crash",
        description: str = ""
    ) -> FailureEvent:
    
        event = FailureEvent(
            failure_start_ms=failure_start * 1000,
            recovery_time_ms=recovery_time * 1000 if recovery_time else None,
            event_type=event_type,
            description=description
        )
        self.failure_events.append(event)
        return event
    
    def save_to_csv(self, filename: Optional[str] = None) -> str:
        if filename is None:
            filename = f"{self.file_prefix}_{int(time.time())}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='') as f:
            if self.metrics:
                fieldnames = ['timestamp_ms', 'send_time_ms', 'latency_ms', 
                             'status', 'server_replica', 'request_id']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for metric in self.metrics:
                    writer.writerow(asdict(metric))
        
        return filepath
    
    def save_to_json(self, filename: Optional[str] = None) -> str:
        if filename is None:
            filename = f"{self.file_prefix}_{int(time.time())}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        data = {
            "metrics": [asdict(m) for m in self.metrics],
            "failure_events": [asdict(e) for e in self.failure_events],
            "metadata": {
                "total_requests": len(self.metrics),
                "total_failures": len(self.failure_events),
                "export_time_ms": time.time() * 1000
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def load_from_csv(self, filepath: str) -> None:
        self.metrics = []
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle original format (timestamp, latency, status, server)
                if 'timestamp' in row and 'latency' in row:
                    timestamp = float(row['timestamp'])
                    latency = float(row['latency'])
                    send_time = timestamp - latency
                    
                    metric = RequestMetric(
                        timestamp_ms=timestamp * 1000,
                        send_time_ms=send_time * 1000,
                        latency_ms=latency * 1000,
                        status=row['status'],
                        server_replica=row.get('server', 'unknown'),
                        request_id=None
                    )
                # Handle new format
                else:
                    metric = RequestMetric(
                        timestamp_ms=float(row['timestamp_ms']),
                        send_time_ms=float(row['send_time_ms']),
                        latency_ms=float(row['latency_ms']),
                        status=row['status'],
                        server_replica=row.get('server_replica', 'unknown'),
                        request_id=row.get('request_id')
                    )
                self.metrics.append(metric)
    
    def load_from_json(self, filepath: str) -> None:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.metrics = [RequestMetric(**m) for m in data.get('metrics', [])]
        self.failure_events = [FailureEvent(**e) for e in data.get('failure_events', [])]
    
    def get_metrics_count(self) -> dict:
        counts = {"SUCCESS": 0, "FAILED": 0, "RECOVERED": 0, "TIMEOUT": 0}
        for m in self.metrics:
            if m.status in counts:
                counts[m.status] += 1
        return counts
    
    def clear(self) -> None:
        self.metrics = []
        self.failure_events = []
