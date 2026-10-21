"""
Serviço gerenciador de sensores em segundo plano para o PiHive-Recorder.
Executa leituras periódicas de sensores climáticos e telemetria elétrica sem bloquear a gravação de vídeo.
"""

import csv
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sensors.base_sensor import BaseSensor
from sensors.sht20 import SHT20Sensor
from sensors.hardware_monitor import HardwareMonitor
import config


class SensorService:
    """Gerencia threads em segundo plano para sensores ambientais e monitor de telemetria."""

    def __init__(self):
        self._running = False
        self._thread_env: Optional[threading.Thread] = None
        self._thread_hw: Optional[threading.Thread] = None
        self.sensors: List[BaseSensor] = []
        self.hw_monitor = HardwareMonitor(
            status_file=config.STATUS_FILE,
            energy_csv=config.ENERGY_CSV,
            interval_sec=config.HARDWARE_INTERVAL_SEC,
            videos_dir=config.VIDEOS_DIR
        )

        self._setup_sensors()

    def _setup_sensors(self) -> None:
        """Instancia sensores configurados em config.ACTIVE_SENSORS."""
        for s_conf in config.ACTIVE_SENSORS:
            driver = s_conf.get("driver", "").lower()
            name = s_conf.get("name", "Sensor")
            bus = s_conf.get("bus", 1)
            address = s_conf.get("address", 0x40)
            info = s_conf.get("info", "")

            if driver == "sht20":
                sensor = SHT20Sensor(name=name, bus_id=bus, address=address, info=info)
                self.sensors.append(sensor)
            else:
                print(f"[SensorService] Driver de sensor desconhecido: '{driver}'")

    def _init_env_csv(self) -> None:
        """Garante a criação do cabeçalho unificado do CSV de sensores ambientais."""
        if not config.SENSORS_CSV.exists() or config.SENSORS_CSV.stat().st_size == 0:
            config.SENSORS_CSV.parent.mkdir(parents=True, exist_ok=True)
            headers = ["Data_Hora"]
            for sensor in self.sensors:
                headers.extend(sensor.get_headers())

            with open(config.SENSORS_CSV, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def _env_loop(self) -> None:
        """Loop em segundo plano para sensores climáticos."""
        self._init_env_csv()
        for sensor in self.sensors:
            sensor.initialize()

        while self._running:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [agora]

            for sensor in self.sensors:
                try:
                    data = sensor.read()
                    row.extend(sensor.get_csv_values(data))
                except Exception:
                    row.extend(["", "", getattr(sensor, "info", "")])

            try:
                with open(config.SENSORS_CSV, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
            except Exception:
                pass

            # Dorme em pequenos passos para permitir parada imediata
            for _ in range(config.SENSOR_READ_INTERVAL_SEC):
                if not self._running:
                    break
                time.sleep(1)

        for sensor in self.sensors:
            sensor.close()

    def _hw_loop(self) -> None:
        """Loop em segundo plano para monitoramento do hardware do Raspberry Pi."""
        self.hw_monitor.init_csv()
        csv_counter = 0
        samples_per_csv_write = max(1, int(60 / config.HARDWARE_INTERVAL_SEC))

        while self._running:
            try:
                metrics = self.hw_monitor.sample()
                csv_counter += 1
                if csv_counter >= samples_per_csv_write:
                    self.hw_monitor.record_to_csv(metrics)
                    csv_counter = 0
            except Exception:
                pass

            for _ in range(config.HARDWARE_INTERVAL_SEC):
                if not self._running:
                    break
                time.sleep(1)

    def start(self) -> None:
        """Inicia os serviços de sensores e monitoramento."""
        if self._running:
            return

        self._running = True

        self._thread_env = threading.Thread(target=self._env_loop, name="EnvSensorsThread", daemon=True)
        self._thread_env.start()

        self._thread_hw = threading.Thread(target=self._hw_loop, name="HwMonitorThread", daemon=True)
        self._thread_hw.start()

        print("[SensorService] Sensores e telemetria iniciados em segundo plano.")

    def stop(self) -> None:
        """Para os serviços de forma graciosa."""
        if not self._running:
            return

        self._running = False
        if self._thread_env and self._thread_env.is_alive():
            self._thread_env.join(timeout=2.0)
        if self._thread_hw and self._thread_hw.is_alive():
            self._thread_hw.join(timeout=2.0)

        print("[SensorService] Sensores e telemetria finalizados.")
