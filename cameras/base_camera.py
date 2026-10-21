"""
Classe base abstrata para módulos de câmera no PiHive-Recorder.
Permite que novos modelos de câmeras sejam adicionados implementando esta interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Tuple


class BaseCamera(ABC):
    """Interface padrão para drivers de câmera."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador da câmera (ex: 'imx708', 'imx477', 'usb_v4l2')."""
        pass

    @abstractmethod
    def load_settings(self, settings_file: Path) -> Dict[str, Any]:
        """Carrega e retorna o dicionário de configurações da câmera."""
        pass

    @abstractmethod
    def get_modes(self) -> Dict[str, Dict[str, Any]]:
        """Retorna os modos de resolução e taxa de quadros suportados."""
        pass

    @abstractmethod
    def build_record_command(
        self,
        output_h264: str,
        duration_ms: int,
        settings: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        """
        Gera a lista com o comando de linha de comando para gravação.
        Retorna (comando_list, fps).
        """
        pass

    @abstractmethod
    def convert_to_container(self, input_h264: str, output_mkv: str, fps: int) -> bool:
        """Encapsula o arquivo raw h264 em container (ex: MKV) com a taxa de quadros correta."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se a câmera e ferramentas necessárias estão disponíveis no sistema."""
        pass
