#!/usr/bin/env bash
# ==============================================================================
# PiHive-Recorder: Script de Instalação e Configuração Automática
# Configura dependências do sistema, ambiente virtual, atalhos na Área de Trabalho e Autostart.
# ==============================================================================

set -e

# Cores para mensagens
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
RED="\033[1;31m"
RESET="\033[0m"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}==================================================================${RESET}"
echo -e "${GREEN}       Instalador Automatizado: PiHive-Recorder                   ${RESET}"
echo -e "${BLUE}==================================================================${RESET}"
echo -e "Diretório de instalação: ${YELLOW}$PROJECT_DIR${RESET}"
echo ""

# 1. Verifica permissões de sudo
if ! command -v sudo &>/dev/null; then
    echo -e "${RED}[ERRO] O comando 'sudo' não foi encontrado. Execute como usuário com privilégios sudo.${RESET}"
    exit 1
fi

# 2. Instalação de pacotes do sistema (Debian / Raspberry Pi OS)
echo -e "${BLUE}[1/6] Atualizando listas e instalando pacotes do sistema...${RESET}"
sudo apt-get update
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    python3-picamera2 \
    python3-pyqt5 \
    python3-smbus \
    python3-psutil \
    mkvtoolnix \
    i2c-tools \
    lxterminal

# 3. Adiciona usuário aos grupos de hardware necessários
echo -e "${BLUE}[2/6] Configurando permissões de usuário para vídeo e I2C...${RESET}"
sudo usermod -aG video,i2c "$USER" || true

# Ativa I2C via raspi-config se disponível
if command -v raspi-config &>/dev/null; then
    sudo raspi-config nonint do_i2c 0 || true
fi

# 4. Criação do Ambiente Virtual Python
echo -e "${BLUE}[3/6] Configurando ambiente virtual Python (.venv)...${RESET}"
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    # Usamos --system-site-packages para ter acesso ao picamera2 e PyQt5 otimizados para o Pi
    python3 -m venv --system-site-packages "$PROJECT_DIR/.venv"
    echo -e "${GREEN}Ambiente virtual criado com sucesso.${RESET}"
fi

source "$PROJECT_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# 5. Permissões de execução nos scripts
echo -e "${BLUE}[4/6] Concedendo permissões de execução aos scripts...${RESET}"
chmod +x "$PROJECT_DIR/scripts/"*.sh
chmod +x "$PROJECT_DIR/install.sh"
[ -f "$PROJECT_DIR/tools/teste_sensor.py" ] && chmod +x "$PROJECT_DIR/tools/teste_sensor.py"

# 6. Criação dos Atalhos na Área de Trabalho
echo -e "${BLUE}[5/6] Criando atalhos na Área de Trabalho...${RESET}"
DESKTOP_DIR="$HOME/Desktop"
if command -v xdg-user-dir &>/dev/null; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
fi
mkdir -p "$DESKTOP_DIR"

# Gera Gravar_Videos.desktop
sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" "$PROJECT_DIR/templates/Gravar_Videos.desktop.template" > "$DESKTOP_DIR/Gravar_Videos.desktop"
chmod +x "$DESKTOP_DIR/Gravar_Videos.desktop"

# Gera Ajustar_Camera.desktop
sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" "$PROJECT_DIR/templates/Ajustar_Camera.desktop.template" > "$DESKTOP_DIR/Ajustar_Camera.desktop"
chmod +x "$DESKTOP_DIR/Ajustar_Camera.desktop"

# Marca os atalhos como confiáveis no ambiente desktop (GNOME/LXDE/Wayfire)
if command -v gio &>/dev/null; then
    gio set "$DESKTOP_DIR/Gravar_Videos.desktop" metadata::trusted true 2>/dev/null || true
    gio set "$DESKTOP_DIR/Ajustar_Camera.desktop" metadata::trusted true 2>/dev/null || true
fi

echo -e "${GREEN}Atalhos criados em: $DESKTOP_DIR${RESET}"

# 7. Configuração do Autostart no Boot
echo -e "${BLUE}[6/6] Configuração de Inicialização Automática (Autostart)...${RESET}"
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

ENABLE_AUTOSTART=true
# Se não estiver em modo não-interativo, pergunta ao usuário
if [ -t 0 ]; then
    read -p "Deseja que a gravação inicie automaticamente ao ligar o Raspberry Pi? [S/n]: " resp
    if [[ "$resp" =~ ^[Nn]$ ]]; then
        ENABLE_AUTOSTART=false
    fi
fi

if [ "$ENABLE_AUTOSTART" = true ]; then
    sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" "$PROJECT_DIR/templates/PiHive_Autostart.desktop.template" > "$AUTOSTART_DIR/PiHive_Autostart.desktop"
    chmod +x "$AUTOSTART_DIR/PiHive_Autostart.desktop"
    echo -e "${GREEN}Autostart ATIVADO em: $AUTOSTART_DIR/PiHive_Autostart.desktop${RESET}"
    echo -e "Ao ligar o Raspberry Pi, uma janela abrirá com 60s de contagem regressiva para cancelamento."
else
    rm -f "$AUTOSTART_DIR/PiHive_Autostart.desktop"
    echo -e "${YELLOW}Autostart não ativado.${RESET}"
fi

# Criação inicial da pasta de armazenamento externa
python3 -c "import config; config.init_storage()"

echo ""
echo -e "${GREEN}==================================================================${RESET}"
echo -e "${GREEN}         Instalação do PiHive-Recorder Concluída com Sucesso!    ${RESET}"
echo -e "${GREEN}==================================================================${RESET}"
echo -e "• Pasta de gravações e dados: ${YELLOW}$HOME/Desktop/Gravacoes_Colmeia${RESET}"
echo -e "• Para calibrar a câmera: use o atalho '${YELLOW}Ajustar Câmera${RESET}' na Área de Trabalho"
echo -e "• Para iniciar a gravação: use o atalho '${YELLOW}Gravar Vídeos${RESET}' ou ligue a placa"
echo ""
