#!/usr/bin/env bash
# ==============================================================================
# PiHive-Recorder: Script de Inicialização da Gravação
# Suporta contagem regressiva no boot com opção de cancelamento / menu de ajuste
# ==============================================================================

# Localiza dinamicamente a pasta raiz do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

# Ativa o ambiente virtual se existir
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Tempo padrão de contagem regressiva (em segundos) - lido do config.py ou 180s por padrão
COUNTDOWN_SECONDS=$(python3 -c "import config; print(getattr(config, 'AUTOSTART_COUNTDOWN_SEC', 180))" 2>/dev/null || echo 180)

echo ""
echo "=================================================================="
echo "   PiHive-Recorder: Gravação Automática & Telemetria"
echo "=================================================================="
echo " Diretório do Projeto: $PROJECT_DIR"
echo ""

CANCELLED=0

# Loop de contagem regressiva
for (( i=COUNTDOWN_SECONDS; i>0; i-- )); do
    echo -ne "\r [INICIALIZAÇÃO] Gravando em $i s... (Pressione 'C' p/ Cancelar | 'ENTER' p/ Iniciar): \033[0K"
    
    # Lê 1 tecla com timeout de 1 segundo
    if read -t 1 -n 1 -s key; then
        if [[ "$key" == "c" || "$key" == "C" || "$key" == $'\e' ]]; then
            CANCELLED=1
            break
        elif [[ "$key" == "" ]]; then
            # Enter pressionado: iniciar imediatamente
            echo ""
            echo ">> Inicialização adiantada pelo usuário."
            break
        fi
    fi
done

echo ""

if [ $CANCELLED -eq 1 ]; then
    echo ""
    echo "=================================================================="
    echo "                 INICIALIZAÇÃO AUTOMÁTICA CANCELADA               "
    echo "=================================================================="
    echo " Escolha uma opção:"
    echo "  [1] Abrir Interface de Ajuste e Calibração da Câmera (GUI)"
    echo "  [2] Iniciar Gravação Agora"
    echo "  [3] Testar Sensores I2C (Diagnóstico)"
    echo "  [4] Sair para o Terminal"
    echo "=================================================================="
    read -p "Opção [1-4]: " opcao

    case "$opcao" in
        1)
            echo ">> Abrindo interface de ajuste..."
            bash "$PROJECT_DIR/scripts/ajustar_camera.sh"
            exit 0
            ;;
        2)
            echo ">> Iniciando gravação..."
            ;;
        3)
            echo ">> Executando teste de sensores..."
            python3 "$PROJECT_DIR/tools/teste_sensor.py"
            read -p "Pressione Enter para fechar..."
            exit 0
            ;;
        *)
            echo ">> Operação cancelada. Saindo..."
            exit 0
            ;;
    esac
fi

echo "=================================================================="
echo ">> Iniciando Orquestrador PiHive-Recorder..."
echo "=================================================================="

# Executa o orquestrador principal em primeiro plano
python3 "$PROJECT_DIR/main_recorder.py"

EXIT_CODE=$?
echo ""
echo "=================================================================="
echo "Gravação finalizada (Código de saída: $EXIT_CODE)."
echo "=================================================================="
read -p "Pressione Enter para fechar esta janela..."
