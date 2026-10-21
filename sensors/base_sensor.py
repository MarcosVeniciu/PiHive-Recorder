"""
Classe base abstrata para sensores ambientais no PiHive-Recorder.
Permite adicionar novos sensores (SHT20, BME280, DHT22, etc.) implementando esta interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseSensor(ABC):
    """Interface padrão para sensores climáticos e ambientais."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome ou identificador da instância do sensor (ex: 'Interno', 'Externo')."""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """Inicializa barramento, pinos ou conexões necessárias."""
        pass

    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """
        Executa a leitura do sensor.
        Retorna dicionário com os valores medidos ou None para valores que falharam.
        Ex: {"temperatura": 25.4, "umidade": 60.2}
        """
        pass

    @abstractmethod
    def get_headers(self) -> List[str]:
        """Retorna lista de nomes de colunas que este sensor gera no arquivo CSV."""
        pass

    @abstractmethod
    def get_csv_values(self, data: Dict[str, Any]) -> List[Any]:
        """Retorna a lista de valores ordenados correspondentes ao cabeçalho para gravação no CSV."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Encerra conexões e libera recursos/barramentos."""
        pass
