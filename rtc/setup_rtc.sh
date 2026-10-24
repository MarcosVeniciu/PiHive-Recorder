#!/usr/bin/env bash
# ==============================================================================
# PiHive-Recorder: Configuração Automatizada de Bateria RTC e Fuso Horário
# ==============================================================================
# Configura o Raspberry Pi 5 para uso de bateria RTC não recarregável (CR2032)
# desativando o circuito de recarga, sincroniza o fuso horário lido do config.py,
# instala utilitários de relógio (hwclock) se necessário e grava a hora no RTC.
# ==============================================================================

set -e

# Cores para formatação de saída
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_PY="$PROJECT_DIR/config.py"
BOOT_CONFIG="/boot/firmware/config.txt"

echo -e "${BLUE}==================================================================${NC}"
echo -e "${BLUE}  PiHive-Recorder: Configuração de Bateria RTC e Fuso Horário     ${NC}"
echo -e "${BLUE}==================================================================${NC}"

# 1. Garante privilégios de superusuário (root)
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERRO] Este script precisa ser executado como root (sudo).${NC}"
    echo -e "Execute com: ${YELLOW}sudo ./rtc/setup_rtc.sh${NC}"
    exit 1
fi

# 2. Aviso e confirmação de instalação física da bateria RTC
echo -e "\n${YELLOW}⚠️  ATENÇÃO - VERIFICAÇÃO DE HARDWARE:${NC}"
echo -e "Antes de iniciar a instalação e sincronização, a ${YELLOW}bateria RTC (ex: CR2032)${NC}"
echo -e "já deve estar conectada fisicamente à placa Raspberry Pi."
echo -e "Caso utilize bateria não recarregável (CR2032), este script também garantirá"
echo -e "que o carregamento da bateria seja desativado para evitar danos."
echo ""
read -r -p "A bateria RTC já está instalada na Raspberry Pi? [s/N]: " confirm_battery
if [[ ! "$confirm_battery" =~ ^[SsYy]$ ]]; then
    echo -e "\n${RED}[CANCELADO] Instale a bateria RTC na placa e execute o script novamente.${NC}"
    exit 0
fi

# 3. Ler o fuso horário (TIMEZONE) do arquivo config.py
echo -e "\n${GREEN}[1/4] Lendo configuração de fuso horário em config.py...${NC}"
if [ -f "$CONFIG_PY" ]; then
    TIMEZONE=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
try:
    import config
    print(getattr(config, 'TIMEZONE', 'America/Sao_Paulo'))
except Exception:
    print('America/Sao_Paulo')
" 2>/dev/null)
else
    TIMEZONE="America/Sao_Paulo"
    echo -e "${YELLOW}[AVISO] Arquivo $CONFIG_PY não encontrado. Usando padrão: $TIMEZONE${NC}"
fi

if [ -z "$TIMEZONE" ]; then
    TIMEZONE="America/Sao_Paulo"
fi
echo -e " -> Fuso horário configurado em config.py: ${YELLOW}$TIMEZONE${NC}"

# 4. Configurar /boot/firmware/config.txt (Desativar carregamento para CR2032)
echo -e "\n${GREEN}[2/4] Verificando configurações de boot em $BOOT_CONFIG...${NC}"
NEEDS_REBOOT=false

if [ -f "$BOOT_CONFIG" ]; then
    if grep -q "^dtoverlay=rp1-rtc-charger,stop_charge" "$BOOT_CONFIG"; then
        echo -e " -> Proteção para bateria não recarregável (${GREEN}dtoverlay=rp1-rtc-charger,stop_charge${NC}) já está ativa."
    else
        echo "" >> "$BOOT_CONFIG"
        echo "# Desativa o carregador da bateria do RTC para usar baterias não recarregáveis" >> "$BOOT_CONFIG"
        echo "dtoverlay=rp1-rtc-charger,stop_charge" >> "$BOOT_CONFIG"
        echo -e " -> Linha ${YELLOW}dtoverlay=rp1-rtc-charger,stop_charge${NC} adicionada ao $BOOT_CONFIG."
        NEEDS_REBOOT=true
    fi

    # Opção para dtparam=rtc=pcf85063 (apenas se o RTC externo/específico for desejado)
    if grep -q "^dtparam=rtc=pcf85063" "$BOOT_CONFIG"; then
        echo -e " -> Parâmetro ${YELLOW}dtparam=rtc=pcf85063${NC} já consta em $BOOT_CONFIG."
    else
        echo -e "\n${YELLOW}Nota sobre dtparam=rtc=pcf85063:${NC}"
        echo -e "Em algumas placas (como o Raspberry Pi 5 que já possui RTC nativo via PMIC/RP1),"
        echo -e "o parâmetro 'dtparam=rtc=pcf85063' pode causar conflito e não é necessário."
        read -r -p "Deseja adicionar 'dtparam=rtc=pcf85063' ao config.txt mesmo assim? [s/N]: " add_pcf
        if [[ "$add_pcf" =~ ^[SsYy]$ ]]; then
            echo "dtparam=rtc=pcf85063" >> "$BOOT_CONFIG"
            echo -e " -> Linha ${YELLOW}dtparam=rtc=pcf85063${NC} adicionada ao $BOOT_CONFIG."
            NEEDS_REBOOT=true
        else
            echo -e " -> Mantendo configuração padrão sem 'dtparam=rtc=pcf85063' (evita conflitos)."
        fi
    fi
else
    echo -e "${YELLOW}[AVISO] Arquivo $BOOT_CONFIG não encontrado.${NC}"
fi

# 5. Verificar e instalar pacotes necessários (util-linux e util-linux-extra / hwclock)
echo -e "\n${GREEN}[3/4] Verificando pacotes de relógio de hardware (util-linux / util-linux-extra)...${NC}"

MISSING_PKGS=()
for pkg in util-linux util-linux-extra; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -eq 0 ] && command -v hwclock >/dev/null 2>&1; then
    echo -e " -> ${GREEN}Pacotes 'util-linux' e 'util-linux-extra' (hwclock) já estão instalados!${NC} Pulando download."
else
    echo -e " -> Instalando pacotes pendentes: ${YELLOW}${MISSING_PKGS[*]}${NC}..."
    apt-get update
    apt-get install -y util-linux util-linux-extra
    echo -e " -> ${GREEN}Pacotes instalados com sucesso.${NC}"
fi

# 6. Sincronizar NTP, aplicar Fuso Horário e gravar no RTC (hwclock)
echo -e "\n${GREEN}[4/4] Configurando fuso horário, NTP e sincronizando com o RTC...${NC}"

echo -e " -> Ativando sincronização de hora via rede (NTP)..."
timedatectl set-ntp true || echo -e "${YELLOW}[AVISO] Não foi possível ativar NTP via timedatectl.${NC}"

echo -e " -> Alterando fuso horário do sistema para ${YELLOW}$TIMEZONE${NC}..."
if timedatectl set-timezone "$TIMEZONE"; then
    echo -e " -> Fuso horário atualizado com sucesso para ${GREEN}$TIMEZONE${NC}."
else
    echo -e "${RED}[ERRO] Falha ao definir o fuso horário '$TIMEZONE'. Verifique se o nome está correto em config.py.${NC}"
    exit 1
fi

echo -e " -> Gravando hora atual do sistema no relógio de hardware (hwclock -w)..."
if [ -e /dev/rtc ] || [ -e /dev/rtc0 ]; then
    hwclock -w
    echo -e " -> Hora gravada no RTC com sucesso!"
    echo -e " -> Lendo hora diretamente do hardware (hwclock -r):"
    echo -e "    ${GREEN}$(hwclock -r)${NC}"
else
    echo -e "${YELLOW}[AVISO] Dispositivo /dev/rtc não encontrado no momento.${NC}"
    echo -e "    Se você acabou de alterar o $BOOT_CONFIG, reinicie a placa e execute este script novamente."
fi

echo -e "\n${BLUE}==================================================================${NC}"
echo -e "${GREEN}✔ Configuração de RTC e Fuso Horário concluída!${NC}"
echo -e "${BLUE}==================================================================${NC}"
echo -e "Resumo do sistema (timedatectl):"
timedatectl status | sed 's/^/  /'

# Leitura da tensão da bateria e status do carregador (Raspberry Pi 5)
BAT_VOLT_FILE="/sys/class/rtc/rtc0/battery_voltage"
CHG_VOLT_FILE="/sys/class/rtc/rtc0/charging_voltage"

if [ -f "$BAT_VOLT_FILE" ] || [ -f "$CHG_VOLT_FILE" ]; then
    echo -e "\n${BLUE}------------------------------------------------------------------${NC}"
    echo -e "🔋 ${YELLOW}Status de Energia e Segurança da Bateria RTC:${NC}"
    if [ -f "$BAT_VOLT_FILE" ]; then
        BAT_UV=$(cat "$BAT_VOLT_FILE" 2>/dev/null || echo "0")
        BAT_V=$(awk -v uv="$BAT_UV" 'BEGIN {printf "%.2f", uv / 1000000}')
        echo -e "  • Tensão atual da bateria : ${GREEN}${BAT_V} V${NC} (${BAT_UV} µV)"
        echo -e "    (Referência: para bateria CR2032 a tensão nominal é 3.00 V)"
    fi
    if [ -f "$CHG_VOLT_FILE" ]; then
        CHG_UV=$(cat "$CHG_VOLT_FILE" 2>/dev/null || echo "0")
        CHG_V=$(awk -v uv="$CHG_UV" 'BEGIN {printf "%.2f", uv / 1000000}')
        if [ "$CHG_UV" -eq 0 ] 2>/dev/null; then
            echo -e "  • Tensão de carregamento  : ${GREEN}${CHG_V} V${NC} (${CHG_UV} µV) — ${GREEN}Recarregamento DESATIVADO (Seguro para CR2032)${NC}"
        else
            echo -e "  • Tensão de carregamento  : ${RED}${CHG_V} V${NC} (${CHG_UV} µV) — ${RED}ATENÇÃO: Carregador ativo! Reinicie a placa se usa CR2032.${NC}"
        fi
    fi
fi
echo -e "${BLUE}==================================================================${NC}"

if [ "$NEEDS_REBOOT" = true ]; then
    echo -e "\n${YELLOW}⚠️  O arquivo $BOOT_CONFIG foi modificado.${NC}"
    echo -e "Para que a desativação do carregador da bateria tenha efeito imediato,"
    echo -e "é necessário reiniciar o Raspberry Pi."
    read -r -p "Deseja reiniciar o Raspberry Pi agora? [s/N]: " reboot_now
    if [[ "$reboot_now" =~ ^[SsYy]$ ]]; then
        echo -e "${YELLOW}Reiniciando o sistema...${NC}"
        reboot
    else
        echo -e "Lembre-se de reiniciar manualmente depois com: ${YELLOW}sudo reboot${NC}"
    fi
fi
