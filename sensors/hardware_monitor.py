"""
Monitor de hardware e telemetria elétrica para Raspberry Pi (otimizado para Pi 5).
Coleta temperatura, clock da CPU, status de throttling e estima consumo de energia em Watts.
"""

import os
import json
import csv
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import psutil
except ImportError:
    psutil = None


class HardwareMonitor:
    """Monitor de telemetria do sistema operacional e hardware Raspberry Pi."""

    CONF_MIN = [2.5, 6.0, 0.2]  # Otimista: ocioso, periféricos em standby
    CONF_MED = [2.7, 7.5, 1.5]  # Provável: gravação ativa, encoder de vídeo e sensores
    CONF_MAX = [3.0, 9.0, 2.0]  # Pessimista: picos de CPU, escrita pesada e rede

    def __init__(
        self,
        status_file: Path,
        energy_csv: Path,
        interval_sec: int = 5,
        videos_dir: Optional[Path] = None
    ):
        self.status_file = Path(status_file)
        self.energy_csv = Path(energy_csv)
        self.interval_sec = interval_sec
        self.videos_dir = Path(videos_dir) if videos_dir else None

        self.boot_time_str = "Desconhecido"
        if psutil:
            try:
                self.boot_time_str = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

    @staticmethod
    def get_temperature() -> float:
        """Lê a temperatura do SoC via vcgencmd."""
        try:
            temp = subprocess.check_output(["vcgencmd", "measure_temp"], stderr=subprocess.DEVNULL).decode("utf-8")
            return float(temp.replace("temp=", "").replace("'C\n", "").strip())
        except Exception:
            return 0.0

    @staticmethod
    def get_cpu_clock() -> int:
        """Lê o clock da CPU (ARM) em MHz via vcgencmd."""
        try:
            clock = subprocess.check_output(["vcgencmd", "measure_clock", "arm"], stderr=subprocess.DEVNULL).decode("utf-8")
            val_hz = int(clock.split("=")[1])
            return round(val_hz / 1_000_000)
        except Exception:
            return 0

    @staticmethod
    def get_throttled_status() -> str:
        """
        Retorna o código de throttling do Raspberry Pi.
        0x0: Normal / OK
        0x50000: Superaquecimento (Thermal throttling)
        0x50005: Throttling + Subtensão (Undervoltage)
        """
        try:
            status = subprocess.check_output(["vcgencmd", "get_throttled"], stderr=subprocess.DEVNULL).decode("utf-8")
            return status.split("=")[1].strip()
        except Exception:
            return "0x0"

    @classmethod
    def calculate_watts(cls, cpu_pct: float, config: list) -> float:
        base, max_cpu, perifericos = config
        return round(base + ((cpu_pct / 100.0) * max_cpu) + perifericos, 2)

    def count_videos(self) -> int:
        """Conta quantos arquivos de vídeo existem no diretório de saída."""
        if not self.videos_dir or not self.videos_dir.exists():
            return 0
        try:
            count = 0
            for ext in ("*.mkv", "*.h264", "*.mp4"):
                count += len(list(self.videos_dir.rglob(ext)))
            return count
        except Exception:
            return 0

    def init_csv(self) -> None:
        """Garante a existência do cabeçalho do arquivo CSV de energia."""
        if not self.energy_csv.exists() or self.energy_csv.stat().st_size == 0:
            self.energy_csv.parent.mkdir(parents=True, exist_ok=True)
            with open(self.energy_csv, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Data_Hora", "CPU%", "RAM%", "Disk%", "Free_GB",
                    "Temp_C", "Clock_MHz", "Throttled",
                    "W_Min", "W_Med", "W_Max",
                    "Video_Count", "Boot_Time"
                ])

    def sample(self) -> Dict[str, Any]:
        """Realiza uma amostragem instantânea das métricas do sistema."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cpu_pct = psutil.cpu_percent(interval=None) if psutil else 0.0
        ram_pct = psutil.virtual_memory().percent if psutil else 0.0

        disk_pct = 0.0
        disk_free_gb = 0.0
        if psutil:
            try:
                disk = psutil.disk_usage("/")
                disk_pct = disk.percent
                disk_free_gb = round(disk.free / (1024**3), 2)
            except Exception:
                pass

        temp = self.get_temperature()
        clock = self.get_cpu_clock()
        throttled = self.get_throttled_status()
        qtd_videos = self.count_videos()

        w_min = self.calculate_watts(cpu_pct, self.CONF_MIN)
        w_med = self.calculate_watts(cpu_pct, self.CONF_MED)
        w_max = self.calculate_watts(cpu_pct, self.CONF_MAX)

        metrics = {
            "timestamp": now_str,
            "cpu": cpu_pct,
            "ram": ram_pct,
            "disk_pct": disk_pct,
            "disk_free_gb": disk_free_gb,
            "temp": temp,
            "clock_mhz": clock,
            "throttled": throttled,
            "watts_min": w_min,
            "watts_med": w_med,
            "watts_max": w_max,
            "videos_gravados": qtd_videos,
            "boot": self.boot_time_str
        }

        # Atualiza arquivo de estado em tempo real (JSON) de forma atômica
        temp_status = self.status_file.with_suffix(".tmp")
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_status, "w", encoding="utf-8") as f:
                json.dump(metrics, f)
            temp_status.replace(self.status_file)
        except Exception:
            pass

        return metrics

    def record_to_csv(self, metrics: Dict[str, Any]) -> None:
        """Salva a amostra de telemetria no CSV."""
        self.init_csv()
        try:
            with open(self.energy_csv, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    metrics["timestamp"],
                    metrics["cpu"],
                    metrics["ram"],
                    metrics["disk_pct"],
                    metrics["disk_free_gb"],
                    metrics["temp"],
                    metrics["clock_mhz"],
                    metrics["throttled"],
                    metrics["watts_min"],
                    metrics["watts_med"],
                    metrics["watts_max"],
                    metrics["videos_gravados"],
                    metrics["boot"]
                ])
        except Exception:
            pass
