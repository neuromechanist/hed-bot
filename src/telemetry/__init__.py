"""Telemetry module for HEDit.

Provides opt-out telemetry collection for service improvement and model fine-tuning.
"""

from src.telemetry.collector import DEFAULT_MODEL_BLACKLIST, TelemetryCollector
from src.telemetry.schema import TelemetryEvent
from src.telemetry.storage import CloudflareKVStorage, LocalFileStorage, TelemetryStorage

__all__ = [
    "TelemetryEvent",
    "TelemetryCollector",
    "TelemetryStorage",
    "LocalFileStorage",
    "CloudflareKVStorage",
    "DEFAULT_MODEL_BLACKLIST",
]
