#!/usr/bin/env bash
# ==============================================================================
# PiHive-Recorder: Configuração Automatizada de USB Tethering, VNC & mDNS/Bonjour
# ==============================================================================
# Configura o Raspberry Pi 5 para operação headless via cabo USB (Tethering),
# ativa o servidor VNC e publica o serviço via mDNS/Avahi para descoberta no
# aplicativo Service Browser e conexão direta por raspberrypi.local.
# ==============================================================================

set -e

# Cores para formatação de saída
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=============================================================${NC}"
echo -e "${BLUE}  PiHive-Recorder: Configuração de Tethering, VNC & mDNS     ${NC}"
echo -e "${BLUE}=============================================================${NC}"

# 1. Garante privilégios de superusuário (root)
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERRO] Este script precisa ser executado como root (sudo).${NC}"
    echo -e "Execute com: ${YELLOW}sudo ./setup_tethering.sh${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Configurar USB Tethering com suporte a MulticastDNS
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[1/5] Configurando interface de rede USB com MulticastDNS...${NC}"

# Cria arquivo de rede com DHCP e suporte a MulticastDNS para wwan*, usb* e rndis*
cat << 'EOF' > /etc/systemd/network/10-usb-tethering.network
[Match]
Name=wwan* usb* rndis*

[Network]
DHCP=yes
RouteMetric=10
MulticastDNS=yes
EOF

systemctl enable systemd-networkd
echo -e " -> Arquivo ${YELLOW}/etc/systemd/network/10-usb-tethering.network${NC} criado com ${GREEN}MulticastDNS=yes${NC}."

# ------------------------------------------------------------------------------
# 3. Instalar e Configurar Avahi (mDNS / Bonjour / Service Discovery)
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[2/5] Configurando anúncio mDNS para Service Browser (Avahi)...${NC}"

if ! dpkg -s avahi-daemon >/dev/null 2>&1; then
    echo -e " -> Instalando avahi-daemon..."
    apt-get update -qq
    apt-get install -y -qq avahi-daemon
fi

mkdir -p /etc/avahi/services

# Anúncio do serviço VNC (_rfb._tcp na porta padrão 5900)
cat << 'EOF' > /etc/avahi/services/vnc.service
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h (VNC)</name>
  <service>
    <type>_rfb._tcp</type>
    <port>5900</port>
  </service>
</service-group>
EOF

systemctl enable avahi-daemon
systemctl restart avahi-daemon 2>/dev/null || true
echo -e " -> Anúncio ${YELLOW}/etc/avahi/services/vnc.service${NC} ativado (_rfb._tcp na porta 5900)."

# ------------------------------------------------------------------------------
# 4. Habilitar Servidor VNC de forma não-interativa
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[3/5] Habilitando servidor de acesso remoto (VNC)...${NC}"
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_vnc 0
    echo -e " -> Servidor VNC habilitado via raspi-config."
else
    echo -e "${YELLOW}[AVISO] raspi-config não encontrado. Verifique a instalação do VNC.${NC}"
fi

# ------------------------------------------------------------------------------
# 5. Otimizar tempo de Boot (Remover timeouts de espera por rede)
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[4/5] Otimizando tempo de inicialização (boot rápido sem travas)...${NC}"

systemctl mask systemd-networkd-wait-online.service 2>/dev/null || true
systemctl mask NetworkManager-wait-online.service 2>/dev/null || true

mkdir -p /etc/cloud
touch /etc/cloud/cloud-init.disabled
systemctl disable rpi-eeprom-update.service 2>/dev/null || true

echo -e " -> Bloqueios e timeouts de espera por rede desativados."

# ------------------------------------------------------------------------------
# 6. Verificação da Câmera no Raspberry Pi 5
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}[5/5] Verificando configuração da câmera no boot...${NC}"
CONFIG_FILE="/boot/firmware/config.txt"

if [ -f "$CONFIG_FILE" ]; then
    if grep -q "^camera_auto_detect=1" "$CONFIG_FILE"; then
        echo -e " -> ${GREEN}camera_auto_detect=1${NC} ativo no config.txt."
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

systemctl restart systemd-networkd 2>/dev/null || true

echo -e "\n${BLUE}=============================================================${NC}"
echo -e "${GREEN}✔ Configuração concluída com sucesso!${NC}"
echo -e "${BLUE}=============================================================${NC}"
echo -e "Reinicie a placa para carregar todas as definições:"
echo -e "  ${YELLOW}sudo reboot${NC}\n"
echo -e "${BLUE}📱 Dica para descoberta no celular Android:${NC}"
echo -e "  Ao usar o ${YELLOW}Service Browser${NC}, desligue temporariamente o ${RED}Wi-Fi${NC} e o ${RED}4G/5G${NC}"
echo -e "  do celular para forçar a busca mDNS diretamente no cabo USB."
echo -e "${BLUE}=============================================================${NC}"
