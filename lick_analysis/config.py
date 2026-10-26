from dataclasses import dataclass


@dataclass(frozen=True)
class SyncParameters:
    """Parameters used to generate the ESP32 synchronization signal."""

    interval_samples: int = 1_000
    pulse_step_ms: int = 100
    pulse_max_ms: int = 9_000
    pin: int = 25


@dataclass(frozen=True)
class ViewerSettings:
    """Interactive viewer and video decoder settings."""

    zoom_duration_s: float = 5.0
    frame_cache_size: int = 20
    sequential_decode_limit: int = 60
    display_max_width: int = 640
