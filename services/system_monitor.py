"""Background system metrics collector (CPU, RAM, Disk, GPU)."""

from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass, field
from typing import Optional, List

import psutil
from PySide6.QtCore import QObject, QThread, Signal, QTimer

logger = logging.getLogger("CleanerPro.Monitor")


@dataclass
class SystemMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    uptime_seconds: float = 0.0
    windows_version: str = ""
    gpu_percent: Optional[float] = None
    boot_time: float = 0.0


class _MonitorWorker(QObject):
    metrics_updated = Signal(object)

    def __init__(self):
        super().__init__()
        self._running = True
        self._boot = psutil.boot_time()

    def stop(self):
        self._running = False

    def run(self):
        # First call to cpu_percent returns 0; warm it up
        psutil.cpu_percent(interval=None)
        while self._running:
            try:
                metrics = self._collect()
                self.metrics_updated.emit(metrics)
            except Exception as e:
                logger.exception("Monitor collect error: %s", e)
            time.sleep(1.5)

    def _collect(self) -> SystemMetrics:
        mem = psutil.virtual_memory()
        # Primary system drive (usually C:)
        try:
            disk = psutil.disk_usage("C:\\")
        except Exception:
            disk = psutil.disk_usage("/")

        gpu = None
        try:
            # Optional NVIDIA via pynvml if present; otherwise leave None
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu = float(util.gpu)
            pynvml.nvmlShutdown()
        except Exception:
            pass

        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=None),
            ram_percent=mem.percent,
            ram_used_gb=mem.used / (1024 ** 3),
            ram_total_gb=mem.total / (1024 ** 3),
            disk_used_gb=disk.used / (1024 ** 3),
            disk_total_gb=disk.total / (1024 ** 3),
            disk_free_gb=disk.free / (1024 ** 3),
            uptime_seconds=time.time() - self._boot,
            windows_version=platform.platform(),
            gpu_percent=gpu,
            boot_time=self._boot,
        )


class SystemMonitor(QObject):
    """Public monitor that lives in the main thread and emits metrics."""

    metrics_updated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[_MonitorWorker] = None
        self.latest: SystemMetrics = SystemMetrics()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = QThread()
        self._worker = _MonitorWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.metrics_updated.connect(self._on_metrics)
        self._thread.start()
        logger.info("System monitor started")

    def stop(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._worker = None
        logger.info("System monitor stopped")

    def _on_metrics(self, metrics: SystemMetrics) -> None:
        self.latest = metrics
        self.metrics_updated.emit(metrics)
