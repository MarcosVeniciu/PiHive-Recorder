"""
Fábrica para instanciar drivers de câmeras no PiHive-Recorder.
"""

from typing import Dict, Type
from cameras.base_camera import BaseCamera
from cameras.imx708 import IMX708Camera

# Registro de câmeras disponíveis
_CAMERA_REGISTRY: Dict[str, Type[BaseCamera]] = {
    "imx708": IMX708Camera,
    "camera_module_3": IMX708Camera,
}


def register_camera(name: str, camera_cls: Type[BaseCamera]) -> None:
    """Permite registrar novos módulos de câmera dinamicamente."""
    _CAMERA_REGISTRY[name.lower()] = camera_cls


def get_camera(driver_name: str) -> BaseCamera:
    """Retorna uma instância da câmera solicitada."""
    key = driver_name.lower()
    if key not in _CAMERA_REGISTRY:
        raise ValueError(
            f"Driver de câmera '{driver_name}' não encontrado. "
            f"Disponíveis: {list(_CAMERA_REGISTRY.keys())}"
        )
    return _CAMERA_REGISTRY[key]()
