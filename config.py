"""
Configurações Globais do PiHive-Recorder.
Centraliza caminhos de armazenamento, parâmetros de gravação e definição de hardware.
"""

import os
import shutil
from pathlib import Path

# --- DIRETÓRIOS E CAMINHOS DO PROJETO ---
PROJECT_ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = PROJECT_ROOT / "camera_settings.txt"

# --- DIRETÓRIO DE ARMAZENAMENTO EXTERNO (ÁREA DE TRABALHO) ---
# Salva vídeos, logs e dados fora da pasta do código para manter o repositório limpo
STORAGE_DIR = Path.home() / "Desktop" / "Gravacoes_Colmeia"
VIDEOS_DIR = STORAGE_DIR / "videos"
LOGS_DIR = STORAGE_DIR / "logs"
SENSORS_DIR = STORAGE_DIR / "sensores"

# Arquivos de saída
LOG_MARKDOWN = LOGS_DIR / "RELATORIO_EXECUCAO.md"
STATUS_FILE = LOGS_DIR / "estado_atual.json"
ENERGY_CSV = LOGS_DIR / "log_energia_intervalo.csv"
SENSORS_CSV = SENSORS_DIR / "monitor_temperatura_umidade.csv"

# --- PARÂMETROS DE GRAVAÇÃO ---
VIDEO_DURATION_SEC = 60          # Duração de cada bloco de vídeo em segundos
HORA_INICIO_GRAVACAO = 4         # Início da gravação diária (04:00)
HORA_TERMINO_GRAVACAO = 19       # Término da gravação diária (19:00)
LIMITE_ESPACO_LIVRE_GB = 5.0     # Parar gravações se espaço livre < 5 GB
AUTOSTART_COUNTDOWN_SEC = 60     # Tempo de espera na inicialização antes de gravar

# --- SELEÇÃO DE CÂMERA ---
# Driver correspondente em cameras/ (atualmente 'imx708' para Camera Module 3)
CAMERA_DRIVER = "imx708"

# --- SENSORES ATIVOS ---
ACTIVE_SENSORS = [
    {
        "driver": "sht20",
        "name": "Interno",
        "bus": 1,
        "address": 0x40,
        "info": "I2C-1 (Hardware) - Pinos 3(SDA)/5(SCL)"
    },
    {
        "driver": "sht20",
        "name": "Externo",
        "bus": 3,
        "address": 0x40,
        "info": "I2C-3 (Software) - GPIO 23/24"
    }
]

# Intervalos de coleta
SENSOR_READ_INTERVAL_SEC = 60     # Leitura dos sensores ambientais a cada 60s
HARDWARE_INTERVAL_SEC = 5         # Telemetria do sistema a cada 5s


def init_storage():
    """Cria as pastas de armazenamento na Área de Trabalho se não existirem."""
    for folder in [STORAGE_DIR, VIDEOS_DIR, LOGS_DIR, SENSORS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
