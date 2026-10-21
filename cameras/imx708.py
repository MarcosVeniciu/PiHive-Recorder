"""
Driver para Raspberry Pi Camera Module 3 (Sensor Sony IMX708).
Configurações oficiais suportadas pelo sensor IMX708 via libcamera / rpicam-vid.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

from cameras.base_camera import BaseCamera


class IMX708Camera(BaseCamera):
    """
    Implementação para Raspberry Pi Camera Module 3 (Sony IMX708).
    
    Especificações Oficiais do Sensor:
      • Sensor: Sony IMX708 (CMOS retroiluminado e empilhado com PDAF)
      • Resolução Máxima Nativa: 4608 x 2592 pixels (11.9 Megapixels)
      • Modos Nativos de Sensor expostos pelo driver do kernel:
          - Modo 0: 4608x2592 [14.35 fps máx - Sem binning, crop total (0,0)/4608x2592]
          - Modo 1: 2304x1296 [56.03 fps máx - 2x2 binning, crop total (0,0)/4608x2592]
          - Modo 2: 1536x864  [120.13 fps máx - 2x2 binning com crop central 2x (768,432)/3072x1728]
      • Recursos de Hardware:
          - Foco Automático por Detecção de Fase (PDAF) e Controle de Lente Manual (0.0 a 32.0 dioptrias)
          - HDR Nativo de Múltipla Exposição no Sensor (até 2304x1296 @ 30fps)
          - Ajuste de Obturador de ~100µs até 11.2 segundos
          - Ganho Analógico de 1.0x até 16.0x (com ganho digital estendido)
    """

    MODES: Dict[str, Dict[str, Any]] = {
        "FULL_RES": {
            "label": "4608x2592 ~14 FPS (Resolução Máxima Nativa - Modo 0)",
            "resolution": (4608, 2592),
            "fps": 14,
            "hdr_capable": False,
            "description": "Modo nativo total (11.9 MP). Máxima nitidez e riqueza de detalhes para time-lapse ou estáticas.",
        },
        "HIGH_QUALITY": {
            "label": "2304x1296 ~56 FPS (Qualidade Máxima - Modo 1)",
            "resolution": (2304, 1296),
            "fps": 56,
            "hdr_capable": True,
            "description": "Modo nativo binned (3 MP, Full FOV). Maior sensibilidade luminosa e alta fluidez.",
        },
        "FHD_MODE": {
            "label": "1920x1080 ~56 FPS (Full HD 1080p)",
            "resolution": (1920, 1080),
            "fps": 56,
            "hdr_capable": True,
            "description": "Full HD 16:9 escalado por hardware pelo ISP. Padrão balanceado e compatível.",
        },
        "HIGH_SPEED": {
            "label": "1536x864 ~120 FPS (Alta Velocidade Nativa - Modo 2)",
            "resolution": (1536, 864),
            "fps": 120,
            "hdr_capable": False,
            "description": "Modo nativo de alta velocidade com recorte central 2x para capturar voo rápido de abelhas.",
        },
        "HD_MODE": {
            "label": "1280x720 ~120 FPS (HD Alta Velocidade)",
            "resolution": (1280, 720),
            "fps": 120,
            "hdr_capable": False,
            "description": "720p a 120 FPS. Excelente compromisso entre alta velocidade e tamanho de arquivo reduzido.",
        },
        "HDR_MODE": {
            "label": "2304x1296 ~30 FPS (HDR Multi-Exposição Nativo)",
            "resolution": (2304, 1296),
            "fps": 30,
            "hdr_capable": True,
            "is_hdr": True,
            "description": "Alto Alcance Dinâmico (HDR direto no sensor IMX708) para iluminação de alto contraste solar.",
        },
    }

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "MODE": "HIGH_SPEED",
        "SHUTTER_SPEED": 8000,
        "ANALOGUE_GAIN": 10.0,
        "LENS_POSITION": 0.0,
        "AWB_ENABLE": True,
        "AUTO_GAIN": False,
        "EXPOSURE_VALUE": 0.0,
        "HDR_ENABLE": False,
        "METERING": "matrix",
        "ROI_ENABLE": True,
        "ROI_WIDTH": 736,
        "ROI_HEIGHT": 736,
        "ROI_X": 400,
        "ROI_Y": 64,
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
            with open(settings_file, "r", encoding="utf-8") as f:
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
                        elif k in ("AWB_ENABLE", "AUTO_GAIN", "HDR_ENABLE", "ROI_ENABLE"):
                            settings[k] = v.lower() == "true"
                        elif k in ("ROI_WIDTH", "ROI_HEIGHT", "ROI_X", "ROI_Y"):
                            settings[k] = int(float(v))
                        elif k == "METERING":
                            settings[k] = v
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
        metering = settings.get("METERING", "matrix")
        
        # Suporte a HDR nativo do sensor IMX708
        use_hdr = mode_info.get("is_hdr", False) or settings.get("HDR_ENABLE", False)

        # Suporte a Recorte de Área de Interesse (Hardware ROI)
        roi_enable = settings.get("ROI_ENABLE", False)
        roi_w = settings.get("ROI_WIDTH", 736)
        roi_h = settings.get("ROI_HEIGHT", 736)
        roi_x = settings.get("ROI_X", 0)
        roi_y = settings.get("ROI_Y", 0)

        out_width = width
        out_height = height
        roi_str = None

        if roi_enable and width >= roi_w and height >= roi_h:
            # Enquadra o ROI dentro dos limites do modo do sensor
            clamped_x = max(0, min(roi_x, width - roi_w))
            clamped_y = max(0, min(roi_y, height - roi_h))
            norm_x = clamped_x / width
            norm_y = clamped_y / height
            norm_w = roi_w / width
            norm_h = roi_h / height
            
            out_width = roi_w
            out_height = roi_h
            roi_str = f"{norm_x:.4f},{norm_y:.4f},{norm_w:.4f},{norm_h:.4f}"

        cmd = [
            "rpicam-vid",
            "-o", str(output_h264),
            "-t", str(duration_ms),
            "--width", str(out_width),
            "--height", str(out_height),
            "--framerate", str(fps),
            "--lens-position", str(lens),
            "--nopreview",
            "--inline",
            "--metering", str(metering),
            "--denoise", "cdn_off",
            "--shutter", str(shutter),
        ]

        if roi_str:
            cmd.extend(["--roi", roi_str])

        if use_hdr:
            cmd.extend(["--hdr", "sensor"])

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
