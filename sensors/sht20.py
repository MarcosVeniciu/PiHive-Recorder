"""
Driver para sensor de temperatura e umidade SHT20 via barramento I2C (SMBus).
Suporta I2C por hardware e software (i2c-gpio).
"""

import time
from typing import Dict, Any, List, Optional
from sensors.base_sensor import BaseSensor

try:
    import smbus
except ImportError:
    try:
        import smbus2 as smbus
    except ImportError:
        smbus = None


class SHT20Sensor(BaseSensor):
    """Driver para sensor Sensirion SHT20."""

    CMD_TEMP = 0xF3
    CMD_UMID = 0xF5

    def __init__(self, name: str, bus_id: int = 1, address: int = 0x40, info: str = ""):
        self._name = name
        self.bus_id = bus_id
        self.address = address
        self.info = info or f"I2C-{bus_id} (0x{address:02x})"
        self.bus: Optional[Any] = None

    @property
    def name(self) -> str:
        return self._name

    def initialize(self) -> bool:
        if smbus is None:
            print(f"[SHT20 - {self.name}] Biblioteca smbus não encontrada no ambiente.")
            return False
        try:
            self.bus = smbus.SMBus(self.bus_id)
            return True
        except Exception as e:
            self.bus = None
            # Silencioso em loop para evitar poluição, mas loga na inicialização
            print(f"[SHT20 - {self.name}] Barramento I2C-{self.bus_id} indisponível: {e}")
            return False

    def read(self) -> Dict[str, Any]:
        if self.bus is None:
            # Tenta reconectar caso o barramento tenha sido ativado posteriormente
            if not self.initialize():
                return {"temp": None, "umid": None}

        try:
            # Leitura de Temperatura
            self.bus.write_byte(self.address, self.CMD_TEMP)
            time.sleep(0.085)  # Tempo de conversão SHT20 (~85ms para 14-bit)
            msb = self.bus.read_byte(self.address)
            lsb = self.bus.read_byte(self.address)
            raw_temp = ((msb << 8) | lsb) & ~0x0003
            temp = -46.85 + (175.72 * raw_temp / 65536.0)

            # Leitura de Umidade
            self.bus.write_byte(self.address, self.CMD_UMID)
            time.sleep(0.030)  # Tempo de conversão (~29ms para 12-bit)
            msb = self.bus.read_byte(self.address)
            lsb = self.bus.read_byte(self.address)
            raw_umid = ((msb << 8) | lsb) & ~0x0003
            umid = -6.0 + (125.0 * raw_umid / 65536.0)

            return {
                "temp": round(temp, 2),
                "umid": max(0.0, min(100.0, round(umid, 2)))
            }
        except Exception:
            return {"temp": None, "umid": None}

    def get_headers(self) -> List[str]:
        return [
            f"{self.name}_Temp_C",
            f"{self.name}_Umid_pct",
            f"{self.name}_Porta_Info"
        ]

    def get_csv_values(self, data: Dict[str, Any]) -> List[Any]:
        temp = data.get("temp")
        umid = data.get("umid")
        return [
            temp if temp is not None else "",
            umid if umid is not None else "",
            self.info
        ]

    def close(self) -> None:
        if self.bus is not None:
            try:
                self.bus.close()
            except Exception:
                pass
            self.bus = None
