#!/usr/bin/env bash
# ==============================================================================
# PiHive-Recorder: Script para Ajuste e Calibração da Câmera (GUI)
# ==============================================================================

# Localiza dinamicamente a pasta raiz do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

# Ativa o ambiente virtual se existir
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Configurações de compatibilidade para renderização Qt com PiCamera2 no Pi 5
# 1. QT_QPA_PLATFORM=xcb: Impede o erro "EGL_BAD_ALLOC" no preview da câmera
# 2. vblank_mode=3: Sincroniza com a taxa de atualização do monitor
export QT_QPA_PLATFORM=xcb
export vblank_mode=3

echo "=================================================================="
echo "   PiHive-Recorder: Interface de Ajuste da Câmera"
echo "=================================================================="
echo " Iniciando GUI..."

python3 "$PROJECT_DIR/gui/camera_control_gui.py"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "[AVISO] O aplicativo encerrou com código de erro $EXIT_CODE."
    read -p "Pressione Enter para fechar esta janela..."
fi
