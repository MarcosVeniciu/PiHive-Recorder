# 🐝 PiHive-Recorder

[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205%20%7C%204-red.svg)](https://www.raspberrypi.com/)
[![OS](https://img.shields.io/badge/OS-Raspberry%20Pi%20OS%20(Bookworm)-blue.svg)](https://www.raspberrypi.com/software/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**PiHive-Recorder** é um sistema modular e autônomo desenvolvido para monitoramento contínuo de colmeias em Raspberry Pi (otimizado para Raspberry Pi 5). Ele integra **gravação de vídeo em alta velocidade**, **calibração de foco em tempo real com GUI**, **sensores climáticos de temperatura e umidade** e **telemetria elétrica do hardware**.

Projetado para operar em campo de forma resiliente, o sistema conta com **inicialização automática com contagem regressiva** para recuperação pós-queda de energia, salvamento de dados isolado na Área de Trabalho e arquitetura modular de drivers de câmeras e sensores.

---

## 📐 Arquitetura do Sistema

```mermaid
graph TD
    subgraph Entrada["Sensores & Câmera"]
        CAM["Câmera (IMX708 / Cam Module 3)"]
        SHT_INT["SHT20 Interno (I2C-1 Hardware)"]
        SHT_EXT["SHT20 Externo (I2C-3 Software)"]
        HW["Telemetria Pi 5 (CPU, Temp, Watts, Throttling)"]
    end

    subgraph Core["Núcleo PiHive-Recorder"]
        CONF["config.py & camera_settings.txt"]
        REC["main_recorder.py (Orquestrador)"]
        SERV["SensorService (Threads em 2º plano)"]
        GUI["camera_control_gui.py (PyQt5 + PiCamera2)"]
    end

    subgraph Saida["Armazenamento (~/Desktop/Gravacoes_Colmeia/)"]
        VID["📁 videos/ (Ano_Mes_Dia/Hora/*.mkv)"]
        LOG["📁 logs/ (RELATORIO_EXECUCAO.md, log_energia.csv)"]
        SNS["📁 sensores/ (monitor_temperatura_umidade.csv)"]
    end

    CAM -->|rpicam-vid + mkvmerge| REC
    SHT_INT --> SERV
    SHT_EXT --> SERV
    HW --> SERV
    SERV --> LOG
    SERV --> SNS
    REC --> VID
    REC --> LOG
    CONF --> REC
    GUI <-->|Ajuste em Tempo Real| CONF
```

---

## ✨ Principais Funcionalidades

* 🎥 **Gravação Automática Segmentada:** Fatiamento de vídeos (padrão 60s) diretamente em H.264 acelerado por hardware e empacotado para MKV via `mkvmerge` preservando taxa de quadros real.
* 🖥️ **Interface Gráfica de Calibração (GUI):** Preview em tempo real com overlay de centralização para ajuste fino de:
  * Posição da lente / Foco manual
  * Velocidade de obturador (Shutter speed em µs)
  * Ganho analógico e Prioridade de Shutter (Auto Gain)
  * Compensação de exposição (EV)
  * Balanço de branco automático (AWB)
  * Modos de resolução (Alta Qualidade 2304x1296@56fps, FHD, HD 1280x720@120fps, High Speed)
* 🌡️ **Monitoramento Climático Multissensor:** Suporte nativo a múltiplos sensores Sensirion SHT20 em barramentos I2C simultâneos (I2C-1 por hardware e I2C-3 por software GPIO).
* ⚡ **Telemetria de Consumo e Hardware:** Estimativa contínua de consumo em Watts (perfis Min/Med/Max para Pi 5), temperatura do SoC, clock de CPU e alertas de throttling por aquecimento ou subtensão via `vcgencmd`.
* 🔄 **Recuperação de Queda de Energia (Autostart Inteligente):** Inicialização automática no boot com contagem regressiva de 60 segundos com janela de cancelamento pelo teclado para permitir ajustes antes de iniciar a gravação.
* 📂 **Separação Limpa de Dados:** Todos os vídeos, logs de execução e arquivos CSV são gravados automaticamente na pasta `~/Desktop/Gravacoes_Colmeia/`, mantendo o repositório Git limpo.
* 🧩 **Extensibilidade Modular:** Classes base abstratas (`BaseCamera` e `BaseSensor`) facilitam adicionar suporte a novas câmeras (HQ Camera IMX477, USB V4L2) ou sensores (BME280, DHT22, DS18B20).

---

## 🔌 Esquema de Ligação do Hardware

### Sensores de Temperatura e Umidade (SHT20)

| Sensor | Barramento | Linha SDA | Linha SCL | Alimentação |
|:---|:---|:---|:---|:---|
| **SHT20 Interno** | **I2C-1 (Hardware)** | Pino 3 (GPIO 2) | Pino 5 (GPIO 3) | 3.3V (Pino 1) e GND (Pino 9) |
| **SHT20 Externo** | **I2C-3 (Software)** | Pino 16 (GPIO 23) | Pino 18 (GPIO 24) | 3.3V (Pino 17) e GND (Pino 25) |

> [!NOTE]
> Para habilitar o barramento I2C-3 por software (bit-banging via GPIO 23/24), adicione a seguinte linha ao final do arquivo `/boot/firmware/config.txt`:
> ```ini
> dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24,i2c_gpio_delay_us=2
> ```
> Após editar, reinicie a Raspberry Pi (`sudo reboot`).

---

## 🚀 Instalação Rápida

Em seu Raspberry Pi, clone o repositório e execute o instalador automatizado:

```bash
git clone git@github.com:MarcosVeniciu/PiHive-Recorder.git
cd PiHive-Recorder
./install.sh
```

### O que o `install.sh` faz automaticamente:
1. Instala pacotes do sistema necessários (`mkvtoolnix`, `i2c-tools`, `python3-picamera2`, `python3-pyqt5`, `python3-smbus`, `lxterminal`).
2. Configura o ambiente virtual Python (`.venv`) com permissão aos drivers de hardware da placa (`--system-site-packages`).
3. Adiciona o usuário aos grupos de sistema `video` e `i2c`.
4. Gera dois atalhos clicáveis diretamente na sua **Área de Trabalho**:
   * **`Gravar Vídeos (PiHive)`**
   * **`Ajustar Câmera (PiHive)`**
5. Configura a inicialização automática no boot (**Autostart** em `~/.config/autostart`).

---

## 🎮 Como Usar

### 1. Calibrar a Câmera e Foco
Dê duplo clique no atalho **`Ajustar Câmera (PiHive)`** na Área de Trabalho ou execute no terminal:
```bash
./scripts/ajustar_camera.sh
```
* Ajuste o foco manual até obter a nitidez ideal na colmeia.
* Configure o obturador (Shutter) para congelar o movimento das abelhas.
* Clique em **"Aplicar e Salvar"**. As configurações serão gravadas no arquivo `camera_settings.txt` e lidas automaticamente pelo gravador.

### 2. Iniciar a Gravação Automática
Dê duplo clique no atalho **`Gravar Vídeos (PiHive)`** na Área de Trabalho ou execute:
```bash
./scripts/iniciar_gravacao.sh
```
* Uma janela de terminal abrirá exibindo uma contagem regressiva de 60 segundos.
* Se precisar cancelar para mexer na colmeia ou câmera, basta pressionar **`C`** para abrir o menu interativo.
* Ao fim do tempo (ou pressionando `ENTER`), a gravação e a coleta de sensores iniciam imediatamente.

### 3. Diagnóstico Rápido de Sensores I2C
Para verificar se ambos os sensores climáticos estão respondendo corretamente:
```bash
python3 tools/teste_sensor.py
```

---

## 📁 Estrutura de Arquivos de Dados

Os dados gerados pelo sistema são salvos na sua Área de Trabalho em `~/Desktop/Gravacoes_Colmeia/`:

```
~/Desktop/Gravacoes_Colmeia/
├── videos/
│   └── 2026_10_21/
│       └── h14/
│           ├── 2026_10_21_h14_M05_S00.mkv
│           └── 2026_10_21_h14_M06_S00.mkv
├── logs/
│   ├── RELATORIO_EXECUCAO.md      # Tabela em Markdown de todos os blocos gravados
│   ├── log_energia_intervalo.csv  # Telemetria periódica (CPU, Temp, Clock, Watts)
│   └── estado_atual.json          # Status instantâneo em tempo real
└── sensores/
    └── monitor_temperatura_umidade.csv  # Leituras dos sensores ambientais
```

---

## ⚙️ Configurações Customizáveis (`config.py`)

No arquivo [`config.py`](file:///home/pi5/Desktop/gravacao_raspberry/config.py), você pode personalizar:

```python
VIDEO_DURATION_SEC = 60          # Duração de cada bloco de vídeo (segundos)
HORA_INICIO_GRAVACAO = 4         # Início do ciclo diário de gravação (04:00)
HORA_TERMINO_GRAVACAO = 19       # Término do ciclo diário de gravação (19:00)
LIMITE_ESPACO_LIVRE_GB = 5.0     # Parada preventiva se disco estiver quase cheio
AUTOSTART_COUNTDOWN_SEC = 60     # Duração da contagem regressiva no boot
CAMERA_DRIVER = "imx708"         # Driver da câmera ativa
```

---

## 🧩 Como Adicionar Novas Câmeras ou Sensores

### Adicionar uma Nova Câmera
1. Crie um novo arquivo em `cameras/` (ex: `cameras/imx477.py`) herdando de `BaseCamera` ([`cameras/base_camera.py`](file:///home/pi5/Desktop/gravacao_raspberry/cameras/base_camera.py)).
2. Implemente os métodos `build_record_command` e `load_settings`.
3. Registre no arquivo [`cameras/factory.py`](file:///home/pi5/Desktop/gravacao_raspberry/cameras/factory.py) e defina `CAMERA_DRIVER` no `config.py`.

### Adicionar um Novo Sensor
1. Crie um novo driver em `sensors/` (ex: `sensors/bme280.py`) herdando de `BaseSensor` ([`sensors/base_sensor.py`](file:///home/pi5/Desktop/gravacao_raspberry/sensors/base_sensor.py)).
2. Adicione os parâmetros do novo sensor na lista `ACTIVE_SENSORS` em [`config.py`](file:///home/pi5/Desktop/gravacao_raspberry/config.py). O gerenciador cuidará das threads e da escrita das colunas no CSV automaticamente.

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).
