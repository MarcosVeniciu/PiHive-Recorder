#!/usr/bin/env bash
# ==============================================================================
# PiHive-Recorder: Configuração Automatizada de USB Tethering e Acesso VNC
# ==============================================================================
# Este script configura o Raspberry Pi 5 para receber internet e ser controlado
# remotamente por um smartphone Android conectado via cabo USB (Tethering),
# permitindo operação "headless" (sem monitor físico) via VNC.
# ==============================================================================

set -e

# Cores para formatação de saída
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sem cor

echo -e "${BLUE}=============================================================${NC}"
echo -e "${BLUE}   PiHive-Recorder: Configuração de USB Tethering & VNC      ${NC}"
echo -e "${BLUE}=============================================================${NC}"

# 1. Garante privilégios de superusuário (root)
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERRO] Este script precisa ser executado como root (sudo).${NC}"
    echo -e "Execute com: ${YELLOW}sudo ./setup_tethering.sh${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Configurar USB Tethering (suporte a wwan0, usb0 e rndis0)
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[1/4] Configurando interface de rede para USB Tethering...${NC}"

# Cria arquivo de configuração no systemd-networkd
# O padrão 'wwan* usb* rndis*' garante compatibilidade com qualquer fabricante de smartphone (Samsung, Motorola, Xiaomi, etc.)
cat << 'EOF' > /etc/systemd/network/10-usb-tethering.network
[Match]
Name=wwan* usb* rndis*

[Network]
DHCP=yes
RouteMetric=10
EOF

systemctl enable systemd-networkd
systemctl restart systemd-networkd 2>/dev/null || true
echo -e " -> Arquivo ${YELLOW}/etc/systemd/network/10-usb-tethering.network${NC} criado."
echo -e " -> Suporte automático a DHCP para interfaces ${YELLOW}wwan*${NC}, ${YELLOW}usb*${NC} e ${YELLOW}rndis*${NC} ativado."

# ------------------------------------------------------------------------------
# 3. Habilitar Servidor VNC de forma não-interativa
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[2/4] Habilitando servidor de acesso remoto (VNC)...${NC}"
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_vnc 0
    echo -e " -> Servidor VNC habilitado com sucesso via raspi-config."
else
    echo -e "${YELLOW}[AVISO] raspi-config não encontrado. Certifique-se de que o VNC está instalado.${NC}"
fi

# ------------------------------------------------------------------------------
# 4. Otimizar tempo de Boot (Remover timeouts de espera por rede)
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[3/4] Otimizando tempo de inicialização (boot rápido sem travas)...${NC}"

# Evita que o sistema fique travado aguardando conexão com a internet para concluir o boot
systemctl mask systemd-networkd-wait-online.service 2>/dev/null || true
systemctl mask NetworkManager-wait-online.service 2>/dev/null || true

# Desativa checagens desnecessárias em campo sem conexão
mkdir -p /etc/cloud
touch /etc/cloud/cloud-init.disabled
systemctl disable rpi-eeprom-update.service 2>/dev/null || true

echo -e " -> Bloqueios e timeouts de espera por rede desativados."

# ------------------------------------------------------------------------------
# 5. Verificação da Câmera no Raspberry Pi 5
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[4/4] Verificando configuração da câmera no boot...${NC}"
CONFIG_FILE="/boot/firmware/config.txt"

if [ -f "$CONFIG_FILE" ]; then
    if grep -q "^camera_auto_detect=1" "$CONFIG_FILE"; then
        echo -e " -> ${GREEN}camera_auto_detect=1${NC} ativo no config.txt (câmeras oficiais IMX708 são detectadas automaticamente no Pi 5)."
    else
        if ! grep -q "imx708" "$CONFIG_FILE"; then
            echo -e "\n[all]\ndtoverlay=imx708,cam0" >> "$CONFIG_FILE"
            echo -e " -> Overlay ${YELLOW}dtoverlay=imx708,cam0${NC} adicionado ao $CONFIG_FILE."
        else
            echo -e " -> Overlay da câmera já configurado em $CONFIG_FILE."
        fi
    fi
else
    echo -e "${YELLOW}[AVISO] Arquivo $CONFIG_FILE não encontrado.${NC}"
fi

echo -e "\n${BLUE}=============================================================${NC}"
echo -e "${GREEN}✔ Configuração concluída com sucesso!${NC}"
echo -e "${BLUE}=============================================================${NC}"
echo -e "Recomenda-se reiniciar a placa agora para aplicar todas as mudanças:"
echo -e "  ${YELLOW}sudo reboot${NC}\n"
echo -e "${BLUE}📱 Instruções de conexão no smartphone Android:${NC}"
echo -e "  1. Conecte o cabo USB entre o smartphone e a Raspberry Pi."
echo -e "  2. No Android, ative: ${YELLOW}Configurações > Roteador Wi-Fi / Tethering > Vínculo USB (Tethering)${NC}."
echo -e "  3. No app ${YELLOW}Termux${NC} do celular, execute: ${YELLOW}ip neigh${NC}"
echo -e "  4. Copie o IP listado (ex: 10.x.x.x ou 192.168.x.x)."
echo -e "  5. No app ${YELLOW}VNC Viewer${NC}, conecte nesse IP com o usuário e senha do Pi."
echo -e "${BLUE}=============================================================${NC}"
