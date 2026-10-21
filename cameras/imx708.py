"""
Driver para Raspberry Pi Camera Module 3 (Sensor Sony IMX708).
Utiliza rpicam-vid para captura com aceleração de hardware e mkvmerge para empacotamento.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

from cameras.base_camera import BaseCamera


class IMX708Camera(BaseCamera):
    """Implementação para Camera Module 3 (Sony IMX708)."""

    MODES: Dict[str, Dict[str, Any]] = {
        "HIGH_QUALITY": {
            "label": "2304x1296 ~56 FPS (Qualidade Máxima)",
            "resolution": (2304, 1296),
            "fps": 56,
        },
        "FHD_MODE": {
            "label": "1920x1080 ~56 FPS (FHD)",
            "resolution": (1920, 1080),
            "fps": 56,
        },
        "HD_MODE": {
            "label": "1280x720 ~120 FPS (HD)",
            "resolution": (1280, 720),
            "fps": 120,
        },
        "HIGH_SPEED": {
            "label": "1536x864 ~120 FPS (Alta Velocidade)",
            "resolution": (1536, 864),
            "fps": 120,
        },
    }

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "MODE": "HIGH_QUALITY",
        "SHUTTER_SPEED": 8000,
        "ANALOGUE_GAIN": 10.0,
        "LENS_POSITION": 0.0,
        "AWB_ENABLE": True,
        "AUTO_GAIN": False,
        "EXPOSURE_VALUE": 0.0,
    }

    @property
    def name(self) -> str:
        return "imx708"

    def get_modes(self) -> Dict[str, Dict[str, Any]]:
        return self.MODES

    def load_settings(self, settings_file: Path) -> Dict[str, Any]:
        settings = self.DEFAULT_SETTINGS.copy()
        if not settings_file.exists():
            return settings

        try:
            with open(settings_file, "r") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.strip().split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if k == "MODE":
                            settings[k] = v if v in self.MODES else "HIGH_QUALITY"
                        elif k == "SHUTTER_SPEED":
                            settings[k] = int(float(v))
                        elif k in ("ANALOGUE_GAIN", "LENS_POSITION", "EXPOSURE_VALUE"):
                            settings[k] = float(v)
                        elif k in ("AWB_ENABLE", "AUTO_GAIN"):
                            settings[k] = v.lower() == "true"
        except Exception as e:
            print(f"[IMX708] Erro ao carregar configurações de {settings_file}: {e}")

        return settings

    def build_record_command(
        self,
        output_h264: str,
        duration_ms: int,
        settings: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        mode_key = settings.get("MODE", "HIGH_QUALITY")
        mode_info = self.MODES.get(mode_key, self.MODES["HIGH_QUALITY"])
        width, height = mode_info["resolution"]
        fps = mode_info["fps"]

        shutter = settings.get("SHUTTER_SPEED", 8000)
        gain = settings.get("ANALOGUE_GAIN", 10.0)
        lens = settings.get("LENS_POSITION", 0.0)
        awb_enable = settings.get("AWB_ENABLE", True)
        auto_gain = settings.get("AUTO_GAIN", False)
        ev_val = settings.get("EXPOSURE_VALUE", 0.0)

        cmd = [
            "rpicam-vid",
            "-o", str(output_h264),
            "-t", str(duration_ms),
            "--width", str(width),
            "--height", str(height),
            "--framerate", str(fps),
            "--lens-position", str(lens),
            "--nopreview",
            "--inline",
            "--metering", "matrix",
            "--denoise", "cdn_off",
            "--shutter", str(shutter),
        ]

        if auto_gain:
            cmd.extend(["--ev", str(ev_val)])
        else:
            cmd.extend(["--gain", str(gain)])

        if awb_enable:
            cmd.extend(["--awb", "auto"])
        else:
            cmd.extend(["--awbgains", "1.0,1.0"])

        return cmd, fps

    def convert_to_container(self, input_h264: str, output_mkv: str, fps: int) -> bool:
        cmd_mkv = [
            "mkvmerge",
            "-o", str(output_mkv),
            "--default-duration", f"0:{fps}fps",
            str(input_h264),
        ]
        res = subprocess.run(cmd_mkv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0

    def is_available(self) -> bool:
        return shutil.which("rpicam-vid") is not None and shutil.which("mkvmerge") is not None
