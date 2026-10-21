#!/usr/bin/env python3
"""
Ferramenta de Diagnóstico: Teste de Sensores I2C (SHT20)
Verifica a conectividade e exibe leituras instantâneas nos barramentos I2C configurados.
"""

import time
from datetime import datetime

try:
    import smbus
except ImportError:
    try:
        import smbus2 as smbus
    except ImportError:
        smbus = None

FREQUENCIA_SEGUNDOS = 2
ENDERECO = 0x40
CMD_TEMP = 0xF3
CMD_UMID = 0xF5

print("==================================================================")
print("   PiHive-Recorder: Diagnóstico de Sensores I2C (SHT20)")
print("==================================================================")

bus_interno = None
bus_externo = None

if smbus is None:
    print("[ERRO CRÍTICO] Biblioteca smbus não está instalada no ambiente Python.")
else:
    # Bus 1 = Hardware (Pinos 3 e 5)
    try:
        bus_interno = smbus.SMBus(1)
        print("[OK] Barramento I2C-1 (Hardware - Pinos 3 e 5) conectado.")
    except Exception as e:
        print(f"[ERRO] Falha ao abrir I2C-1: {e}")

    # Bus 3 = Software (Pinos 23 e 24)
    try:
        bus_externo = smbus.SMBus(3)
        print("[OK] Barramento I2C-3 (Software - GPIO 23 e 24) conectado.")
    except Exception as e:
        print(f"[AVISO] Barramento I2C-3 não encontrado: {e}")
        print("       (Para ativar o I2C-3 por software, verifique dtoverlay=i2c-gpio no config.txt)")


def ler_sensor(bus):
    if bus is None:
        return None, None
    try:
        bus.write_byte(ENDERECO, CMD_TEMP)
        time.sleep(0.085)
        msb = bus.read_byte(ENDERECO)
        lsb = bus.read_byte(ENDERECO)
        raw_temp = ((msb << 8) | lsb) & ~0x0003
        temp = -46.85 + (175.72 * raw_temp / 65536.0)

        bus.write_byte(ENDERECO, CMD_UMID)
        time.sleep(0.030)
        msb = bus.read_byte(ENDERECO)
        lsb = bus.read_byte(ENDERECO)
        raw_umid = ((msb << 8) | lsb) & ~0x0003
        umid = -6.0 + (125.0 * raw_umid / 65536.0)

        return round(temp, 2), round(umid, 2)
    except Exception:
        return None, None


def main():
    print("\n--- INICIANDO LEITURA EM TEMPO REAL (Pressione CTRL+C para sair) ---")
    print(f"{'HORA':<10} | {'SENSOR INTERNO (Bus 1)':<25} | {'SENSOR EXTERNO (Bus 3)':<25}")
    print("-" * 65)

    try:
        while True:
            agora = datetime.now().strftime("%H:%M:%S")
            t_in, u_in = ler_sensor(bus_interno)
            t_out, u_out = ler_sensor(bus_externo)

            str_in = f"{t_in}°C / {u_in}%" if t_in is not None else "-- Falha / Ausente --"
            str_out = f"{t_out}°C / {u_out}%" if t_out is not None else "-- Falha / Ausente --"

            print(f"{agora:<10} | {str_in:<25} | {str_out:<25}")
            time.sleep(FREQUENCIA_SEGUNDOS)

    except KeyboardInterrupt:
        print("\nDiagnóstico encerrado pelo usuário.")


if __name__ == "__main__":
    main()
