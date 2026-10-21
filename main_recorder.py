"""
Orquestrador Principal de Gravação e Monitoramento - PiHive-Recorder.
Coordena a captura de vídeo da câmera, monitoramento de sensores e telemetria de hardware.
"""

import os
import sys
import time
import json
import signal
import shutil
import datetime
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import config
from cameras import get_camera
from sensors import SensorService


def setup_markdown() -> None:
    """Gera o cabeçalho da tabela no relatório Markdown se ele não existir."""
    header = """# Relatório de Execução - PiHive-Recorder

| Data/Hora | Evento | Arq. Vídeo | CPU | Temp | Watts (Min/Med/Max) | Throttled | Boot Time | Espaço (GB) | Status |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    if not config.LOG_MARKDOWN.exists() or config.LOG_MARKDOWN.stat().st_size == 0:
        config.LOG_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
        with open(config.LOG_MARKDOWN, "w", encoding="utf-8") as f:
            f.write(header)


def log_to_markdown(
    evento: str,
    arquivo_video: str,
    cpu: Optional[float],
    temp: Optional[float],
    w_min: Optional[float],
    w_med: Optional[float],
    w_max: Optional[float],
    throttled: Optional[str],
    boot: Optional[str],
    espaco: float,
    status_msg: str
) -> None:
    """Registra uma linha no relatório Markdown."""
    now = datetime.datetime.now().strftime("%d/%m %H:%M:%S")
    cpu_s = f"{cpu}%" if cpu is not None else "-"
    temp_s = f"{temp}°C" if temp is not None else "-"
    watts_s = f"{w_min} / **{w_med}** / {w_max}" if w_med is not None else "-"
    throttled_s = f"`{throttled}`" if throttled else "-"
    boot_s = str(boot) if boot else "-"

    line = f"| {now} | {evento} | `{arquivo_video}` | {cpu_s} | {temp_s} | {watts_s} | {throttled_s} | {boot_s} | {espaco:.2f} | {status_msg} |\n"

    try:
        with open(config.LOG_MARKDOWN, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"[LOG] Falha ao escrever no Markdown: {e}")


def get_system_status() -> Optional[dict]:
    """Lê o status atual do sistema salvo pelo monitor de hardware."""
    try:
        if config.STATUS_FILE.exists():
            with open(config.STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def print_banner(text: str) -> None:
    print("\n" + "═" * 60)
    print(f"   {text}")
    print("═" * 60)


def check_disk_space(path: Path) -> float:
    """Retorna o espaço livre em Gigabytes no caminho fornecido."""
    try:
        _, _, free = shutil.disk_usage(path)
        return free / (1024 ** 3)
    except Exception:
        return 0.0


def create_filepath_generator():
    """Gera caminhos organizados por ano_mes_dia/hora para salvar os vídeos."""
    while True:
        now = datetime.datetime.now()
        output_dir = config.VIDEOS_DIR / now.strftime("%Y_%m_%d") / now.strftime("h%H")
        output_dir.mkdir(parents=True, exist_ok=True)
        filename_base = now.strftime("%Y_%m_%d_h%H_M%M_S%S")
        yield str(output_dir / filename_base), output_dir


def main():
    config.init_storage()
    setup_markdown()
    print_banner("PIHIVE-RECORDER: SISTEMA DE GRAVAÇÃO E TELEMETRIA")

    # 1. Inicializa o serviço de sensores e telemetria em segundo plano
    sensor_service = SensorService()
    sensor_service.start()

    def signal_handler(sig, frame):
        print("\n[ENCERRAMENTO] Sinal de interrupção recebido.")
        sensor_service.stop()
        log_to_markdown("INTERRUPCAO", "-", None, None, None, None, None, None, None, 0, "Finalizado por Sinal")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 2. Carrega a câmera configurada
    try:
        camera = get_camera(config.CAMERA_DRIVER)
    except Exception as e:
        print(f"[ERRO CRÍTICO] Driver de câmera inválido: {e}")
        sensor_service.stop()
        return

    # Carrega configurações do arquivo camera_settings.txt
    cam_settings = camera.load_settings(config.SETTINGS_FILE)
    mode_key = cam_settings.get("MODE", "HIGH_QUALITY")
    modes = camera.get_modes()
    res, fps = modes.get(mode_key, {}).get("resolution", (1920, 1080)), modes.get(mode_key, {}).get("fps", 30)

    print(f"► Câmera: {camera.name.upper()} | Modo: {mode_key} ({res[0]}x{res[1]} @ {fps}fps)")
    print(f"► Foco (Lens Position): {cam_settings.get('LENS_POSITION', 0.0)}")
    print(f"► Armazenamento: {config.STORAGE_DIR}")
    print(f"► Janela de Gravação: {config.HORA_INICIO_GRAVACAO:02d}:00 até {config.HORA_TERMINO_GRAVACAO:02d}:00")
    print("-" * 60)

    filepath_gen = create_filepath_generator()
    duration_ms = config.VIDEO_DURATION_SEC * 1000

    try:
        while True:
            # 1. Checagem de Espaço em Disco
            free_gb = check_disk_space(config.STORAGE_DIR)
            if free_gb < config.LIMITE_ESPACO_LIVRE_GB:
                print(f"\n[CRÍTICO] Espaço insuficiente em disco: {free_gb:.2f}GB (Mínimo: {config.LIMITE_ESPACO_LIVRE_GB}GB)")
                log_to_markdown("ERRO", "-", None, None, None, None, None, None, None, free_gb, "Disco Cheio")
                break

            # 2. Checagem de Janela de Horário
            hora = datetime.datetime.now().hour
            if not (config.HORA_INICIO_GRAVACAO <= hora < config.HORA_TERMINO_GRAVACAO):
                sys.stdout.write(f"\r[AGUARDANDO] Fora do horário de gravação ({hora:02d}h). Monitorando sensores...   ")
                sys.stdout.flush()
                time.sleep(60)
                continue

            # 3. Coleta de Status de Telemetria
            status = get_system_status()
            cpu_val = status.get("cpu") if status else None
            temp_val = status.get("temp") if status else None
            w_min = status.get("watts_min") if status else None
            w_med = status.get("watts_med") if status else None
            w_max = status.get("watts_max") if status else None
            throttled = status.get("throttled") if status else None
            boot_val = status.get("boot") if status else None

            # 4. Preparação do Arquivo
            base_path, _ = next(filepath_gen)
            filename_only = Path(base_path).name
            h264_path = base_path + ".h264"
            mkv_path = base_path + ".mkv"

            print(f"\n[REC] Gravando bloco: {filename_only} ({config.VIDEO_DURATION_SEC}s)...")

            # 5. Montagem do comando de gravação
            cmd_cam, target_fps = camera.build_record_command(h264_path, duration_ms, cam_settings)

            log_to_markdown("INICIO", filename_only, cpu_val, temp_val, w_min, w_med, w_max, throttled, boot_val, free_gb, "Gravando")

            try:
                start_time = time.time()
                subprocess.run(cmd_cam, check=True)

                print("  ⚙️  Empacotando MKV...", end="", flush=True)
                success_mkv = camera.convert_to_container(h264_path, mkv_path, target_fps)

                if os.path.exists(h264_path):
                    os.remove(h264_path)

                elapsed = time.time() - start_time
                if success_mkv:
                    print(f" Concluído ({elapsed:.1f}s)")
                    log_to_markdown("SUCESSO", filename_only, cpu_val, temp_val, w_min, w_med, w_max, throttled, boot_val, free_gb, "OK")
                else:
                    print(" Falha no MKV")
                    log_to_markdown("AVISO", filename_only, cpu_val, temp_val, w_min, w_med, w_max, throttled, boot_val, free_gb, "MKVmerge Falhou")

            except subprocess.CalledProcessError as e:
                print(f"\n  ❌ ERRO na gravação: {e}")
                log_to_markdown("FALHA", filename_only, cpu_val, temp_val, w_min, w_med, w_max, throttled, boot_val, free_gb, f"Erro: {e}")
                time.sleep(5)
            except Exception as e:
                print(f"\n  ❌ ERRO inesperado: {e}")
                log_to_markdown("FALHA", filename_only, cpu_val, temp_val, w_min, w_med, w_max, throttled, boot_val, free_gb, f"Excecao: {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n[FIM] Gravação encerrada pelo usuário.")
        log_to_markdown("INTERRUPCAO", "-", None, None, None, None, None, None, None, 0, "Cancelado pelo Usuário")
    finally:
        sensor_service.stop()


if __name__ == "__main__":
    main()
