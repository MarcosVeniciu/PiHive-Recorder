# --- MODIFICADO (VERSÃO COM CONTROLE DE EV) ---
# Câmera de referência e modos disponíveis para o sensor imx708.
# -----------------------------------------------------------------
# Available cameras
# -----------------
# 0 : imx708 [4608x2592 10-bit RGGB] (/base/axi/pcie@1000120000/rp1/i2c@88000/imx708@1a)
#     Modes: 'SRGGB10_CSI2P' : 1536x864 [120.13 fps - (768, 432)/3072x1728 crop]
#                              2304x1296 [56.03 fps - (0, 0)/4608x2592 crop]
#                              4608x2592 [14.35 fps - (0, 0)/4608x2592 crop]
# -----------------------------------------------------------------

import sys
import traceback
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QGroupBox, 
    QRadioButton, QSlider, QCheckBox, QStackedLayout
)
from PyQt5.QtCore import QSize, Qt, QTimer, QEvent
from PyQt5.QtGui import QSurfaceFormat, QPainter, QPen, QColor, QFont
from functools import partial 

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from cameras.imx708 import IMX708Camera

# Utiliza os modos e resoluções oficiais suportados pelo sensor IMX708
CAMERA_MODES = IMX708Camera.MODES
SETTINGS_FILE = config.SETTINGS_FILE

class FloatingOverlay(QWidget):
    """
    Uma janela separada, transparente e sem bordas, que flutua sobre o vídeo.
    Isso garante que o desenho apareça mesmo sobre renderização HW.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Configurações para ser uma janela transparente "fantasma"
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        parent = self.parent()
        
        # Se o recorte ROI estiver ativado, desenha a caixa de enquadramento
        if parent and getattr(parent, "roi_enabled", False):
            mode_w = max(1, getattr(parent, "current_mode_width", 1536))
            mode_h = max(1, getattr(parent, "current_mode_height", 864))
            
            # Escala as coordenadas do sensor para o tamanho visual do widget de preview
            scale_x = self.width() / mode_w
            scale_y = self.height() / mode_h
            
            bx = int(parent.roi_x * scale_x)
            by = int(parent.roi_y * scale_y)
            bw = int(parent.roi_w * scale_x)
            bh = int(parent.roi_h * scale_y)
            
            # 1. Máscara escura suave na área externa que será descartada
            painter.setBrush(QColor(0, 0, 0, 110))
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, self.width(), by)
            painter.drawRect(0, by + bh, self.width(), self.height() - (by + bh))
            painter.drawRect(0, by, bx, bh)
            painter.drawRect(bx + bw, by, self.width() - (bx + bw), bh)
            
            # 2. Retângulo demarcador de corte
            pen_box = QPen(QColor(255, 40, 40), 3)
            pen_box.setStyle(Qt.SolidLine)
            painter.setPen(pen_box)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(bx, by, bw, bh)
            
            # 3. Mira central suave no meio do enquadramento
            pen_cross = QPen(QColor(255, 255, 255, 200), 1)
            pen_cross.setStyle(Qt.DashLine)
            painter.setPen(pen_cross)
            cx = bx + bw // 2
            cy = by + bh // 2
            painter.drawLine(cx - 20, cy, cx + 20, cy)
            painter.drawLine(cx, cy - 20, cx, cy + 20)
            
            # 4. Etiqueta informativa
            painter.setBrush(QColor(220, 20, 20, 220))
            painter.setPen(Qt.NoPen)
            painter.drawRect(bx, max(0, by - 26), 230, 24)
            
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = QFont()
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(bx + 8, max(0, by - 26) + 16, f"REC HW: {parent.roi_w}x{parent.roi_h} (120 FPS)")
            
        else:
            # Modo padrão sem ROI: linha guia central
            pen = QPen(QColor(255, 0, 0), 2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            
            x_center = int(self.width() / 2)
            height = self.height()
            painter.drawLine(x_center, 0, x_center, height)
            
            # Fundo preto semi-transparente para legibilidade
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x_center - 130, 10, 260, 30)
            
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(x_center - 120, 30, "◄ LADO ESQUERDO | LADO DIREITO ►")

def load_settings():
    print("[LOG] Iniciando o carregamento das configurações...")
    defaults = {
        "MODE": "HIGH_QUALITY",
        "SHUTTER_SPEED": 8000,
        "ANALOGUE_GAIN": 10.0,
        "LENS_POSITION": 0.0,
        "AWB_ENABLE": "True",
        "AUTO_GAIN": "False",
        "EXPOSURE_VALUE": 0.0,
        "ROI_ENABLE": "False",
        "ROI_WIDTH": 736,
        "ROI_HEIGHT": 736,
        "ROI_X": 400,
        "ROI_Y": 64
    }
    try:
        config_map = {}
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.strip().split(':', 1)
                        config_map[key.strip()] = value.strip()
        
        mode = config_map.get("MODE", defaults["MODE"])
        if mode not in CAMERA_MODES:
            mode = defaults["MODE"]
            
        shutter = int(float(config_map.get("SHUTTER_SPEED", defaults["SHUTTER_SPEED"])))
        gain = float(config_map.get("ANALOGUE_GAIN", defaults["ANALOGUE_GAIN"]))
        lens_pos = float(config_map.get("LENS_POSITION", defaults["LENS_POSITION"]))
        awb_enable = config_map.get("AWB_ENABLE", defaults["AWB_ENABLE"]) == "True"
        auto_gain = config_map.get("AUTO_GAIN", defaults["AUTO_GAIN"]) == "True"
        ev_val = float(config_map.get("EXPOSURE_VALUE", defaults["EXPOSURE_VALUE"]))
        
        roi_enable = config_map.get("ROI_ENABLE", defaults["ROI_ENABLE"]) == "True"
        roi_w = int(float(config_map.get("ROI_WIDTH", defaults["ROI_WIDTH"])))
        roi_h = int(float(config_map.get("ROI_HEIGHT", defaults["ROI_HEIGHT"])))
        roi_x = int(float(config_map.get("ROI_X", defaults["ROI_X"])))
        roi_y = int(float(config_map.get("ROI_Y", defaults["ROI_Y"])))
        
        return {
            "MODE": mode, 
            "SHUTTER_SPEED": shutter, 
            "ANALOGUE_GAIN": gain, 
            "LENS_POSITION": lens_pos,
            "AWB_ENABLE": awb_enable,
            "AUTO_GAIN": auto_gain,
            "EXPOSURE_VALUE": ev_val,
            "ROI_ENABLE": roi_enable,
            "ROI_WIDTH": roi_w,
            "ROI_HEIGHT": roi_h,
            "ROI_X": roi_x,
            "ROI_Y": roi_y
        }

    except Exception as e:
        print(f"[LOG] Falha ao carregar configurações: {e}")
        return {
            "MODE": defaults["MODE"],
            "SHUTTER_SPEED": defaults["SHUTTER_SPEED"],
            "ANALOGUE_GAIN": defaults["ANALOGUE_GAIN"],
            "LENS_POSITION": defaults["LENS_POSITION"],
            "AWB_ENABLE": True,
            "AUTO_GAIN": False,
            "EXPOSURE_VALUE": 0.0,
            "ROI_ENABLE": False,
            "ROI_WIDTH": 736,
            "ROI_HEIGHT": 736,
            "ROI_X": 400,
            "ROI_Y": 64
        }

class CameraControlWindow(QWidget):
    def __init__(self, picam2, initial_config):
        super().__init__()
        print("[LOG] Inicializando a janela de controle da câmera...")
        self.picam2 = picam2
        self.initial_config = initial_config
        self.setWindowTitle("Controle e Preview da Câmera (IMX708)")
        
        self.current_focus_internal = int(self.initial_config["LENS_POSITION"] * 100)
        
        # --- Parâmetros de Recorte de Área de Interesse (ROI) ---
        self.roi_enabled = self.initial_config.get("ROI_ENABLE", False)
        self.roi_w = self.initial_config.get("ROI_WIDTH", 736)
        self.roi_h = self.initial_config.get("ROI_HEIGHT", 736)
        self.roi_x = self.initial_config.get("ROI_X", 400)
        self.roi_y = self.initial_config.get("ROI_Y", 64)
        
        init_mode = self.initial_config.get("MODE", "HIGH_QUALITY")
        self.current_mode_width, self.current_mode_height = CAMERA_MODES.get(init_mode, {}).get("resolution", (2304, 1296))

        main_layout = QVBoxLayout()

        # Container do Vídeo
        self.video_container = QWidget()
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0,0,0,0)
        
        self.preview_widget = QGlPicamera2(self.picam2)
        video_layout.addWidget(self.preview_widget)
        
        main_layout.addWidget(self.video_container, stretch=5)

        # Painel de controle
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)

        self.setLayout(main_layout)
        
        # --- CONFIGURAÇÃO DO OVERLAY FLUTUANTE ---
        self.floating_overlay = FloatingOverlay(self) 
        self.floating_overlay.show()
        
        # Timer para sincronizar a posição do overlay com o vídeo
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.update_overlay_position)
        self.sync_timer.start(30) 

        self.reconfigure_camera_and_apply(is_initial_setup=True)
        print("[LOG] Janela de controle inicializada com sucesso.")

    def update_overlay_position(self):
        """Mantém a linha vermelha colada em cima do vídeo, mesmo se mover a janela."""
        if self.isVisible() and self.preview_widget.isVisible():
            global_pos = self.preview_widget.mapToGlobal(self.preview_widget.rect().topLeft())
            self.floating_overlay.setGeometry(
                global_pos.x(), 
                global_pos.y(), 
                self.preview_widget.width(), 
                self.preview_widget.height()
            )
            self.floating_overlay.show()
        else:
            self.floating_overlay.hide()

    def moveEvent(self, event):
        self.update_overlay_position()
        super().moveEvent(event)
        
    def resizeEvent(self, event):
        self.update_overlay_position()
        super().resizeEvent(event)

    def create_control_panel(self):
        panel_frame = QFrame()
        panel_layout = QHBoxLayout(panel_frame)
        panel_layout.setSpacing(15)
        panel_layout.setContentsMargins(10, 10, 10, 10)

        # --- Grupo de Modo (IMX708) ---
        mode_groupbox = QGroupBox("Modo de Câmera (IMX708)")
        mode_layout = QVBoxLayout()
        
        self.mode_radios = {}
        current_mode = self.initial_config.get("MODE", "HIGH_QUALITY")
        if current_mode not in CAMERA_MODES:
            current_mode = "HIGH_QUALITY"

        for key, info in CAMERA_MODES.items():
            radio = QRadioButton(info["label"])
            radio.setChecked(key == current_mode)
            radio.toggled.connect(self.on_mode_change)
            self.mode_radios[key] = radio
            mode_layout.addWidget(radio)

        if not any(r.isChecked() for r in self.mode_radios.values()):
            list(self.mode_radios.values())[0].setChecked(True)
        
        mode_groupbox.setLayout(mode_layout)
        
        # --- Estilo ---
        value_label_style = """
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
                font-size: 14px;
                min-width: 70px;
                alignment: AlignCenter;
            }
        """

        settings_layout = QVBoxLayout()

        # Shutter
        layout_shutter = QHBoxLayout()
        self.label_shutter_value = QLabel(str(self.initial_config["SHUTTER_SPEED"]))
        self.label_shutter_value.setStyleSheet(value_label_style)
        self.label_shutter_value.setAlignment(Qt.AlignCenter)
        btn_s_m1000 = QPushButton("-1000")
        btn_s_m100 = QPushButton("-100")
        btn_s_p100 = QPushButton("+100")
        btn_s_p1000 = QPushButton("+1000")
        btn_s_m1000.clicked.connect(partial(self.adjust_shutter, -1000))
        btn_s_m100.clicked.connect(partial(self.adjust_shutter, -100))
        btn_s_p100.clicked.connect(partial(self.adjust_shutter, 100))
        btn_s_p1000.clicked.connect(partial(self.adjust_shutter, 1000))
        layout_shutter.addWidget(QLabel("Shutter (µs):"))
        layout_shutter.addWidget(btn_s_m1000)
        layout_shutter.addWidget(btn_s_m100)
        layout_shutter.addWidget(self.label_shutter_value)
        layout_shutter.addWidget(btn_s_p100)
        layout_shutter.addWidget(btn_s_p1000)

        # Gain Checkbox
        self.check_auto_gain = QCheckBox("Ganho Automático (Prioridade de Shutter)")
        self.check_auto_gain.setChecked(self.initial_config["AUTO_GAIN"])
        self.check_auto_gain.setToolTip("Marcado: Câmera ajusta o brilho (Gain) mas mantém o Shutter fixo na gravação.")
        self.check_auto_gain.stateChanged.connect(self.toggle_gain_controls)

        # Gain Controls
        self.layout_gain_controls = QHBoxLayout()
        self.label_gain_value = QLabel(f"{self.initial_config['ANALOGUE_GAIN']:.1f}")
        self.label_gain_value.setStyleSheet(value_label_style)
        self.label_gain_value.setAlignment(Qt.AlignCenter)
        self.btn_g_m10 = QPushButton("-10")
        self.btn_g_m1 = QPushButton("-1")
        self.btn_g_p1 = QPushButton("+1")
        self.btn_g_p10 = QPushButton("+10")
        
        self.btn_g_m10.clicked.connect(partial(self.adjust_gain, -10.0))
        self.btn_g_m1.clicked.connect(partial(self.adjust_gain, -1.0))
        self.btn_g_p1.clicked.connect(partial(self.adjust_gain, 1.0))
        self.btn_g_p10.clicked.connect(partial(self.adjust_gain, 10.0))
        
        self.layout_gain_controls.addWidget(QLabel("Ganho Manual:"))
        self.layout_gain_controls.addWidget(self.btn_g_m10)
        self.layout_gain_controls.addWidget(self.btn_g_m1)
        self.layout_gain_controls.addWidget(self.label_gain_value)
        self.layout_gain_controls.addWidget(self.btn_g_p1)
        self.layout_gain_controls.addWidget(self.btn_g_p10)

        self.gain_widget = QWidget()
        self.gain_widget.setLayout(self.layout_gain_controls)

        # --- NOVO: EV Controls ---
        self.layout_ev_controls = QHBoxLayout()
        self.label_ev_value = QLabel(f"{self.initial_config['EXPOSURE_VALUE']:.1f}")
        self.label_ev_value.setStyleSheet(value_label_style)
        self.label_ev_value.setAlignment(Qt.AlignCenter)
        
        btn_ev_minus = QPushButton("-0.5")
        btn_ev_plus = QPushButton("+0.5")
        
        btn_ev_minus.clicked.connect(partial(self.adjust_ev, -0.5))
        btn_ev_plus.clicked.connect(partial(self.adjust_ev, 0.5))
        
        self.layout_ev_controls.addWidget(QLabel("Compensação (EV):"))
        self.layout_ev_controls.addWidget(btn_ev_minus)
        self.layout_ev_controls.addWidget(self.label_ev_value)
        self.layout_ev_controls.addWidget(btn_ev_plus)
        
        # Focus
        layout_focus = QHBoxLayout()
        self.label_focus_value = QLabel(f"{self.initial_config['LENS_POSITION']:.2f}")
        self.label_focus_value.setStyleSheet(value_label_style)
        self.label_focus_value.setAlignment(Qt.AlignCenter)
        btn_f_m50 = QPushButton("-50")
        btn_f_m10 = QPushButton("-10")
        btn_f_p10 = QPushButton("+10")
        btn_f_p50 = QPushButton("+50")
        btn_f_m50.clicked.connect(partial(self.adjust_focus, -50))
        btn_f_m10.clicked.connect(partial(self.adjust_focus, -10))
        btn_f_p10.clicked.connect(partial(self.adjust_focus, 10))
        btn_f_p50.clicked.connect(partial(self.adjust_focus, 50))
        layout_focus.addWidget(QLabel("Foco Manual:"))
        layout_focus.addWidget(btn_f_m50)
        layout_focus.addWidget(btn_f_m10)
        layout_focus.addWidget(self.label_focus_value)
        layout_focus.addWidget(btn_f_p10)
        layout_focus.addWidget(btn_f_p50)

        # AWB Checkbox
        layout_awb = QHBoxLayout()
        self.check_awb = QCheckBox("AWB (Balanço de Branco Automático)")
        self.check_awb.setChecked(self.initial_config["AWB_ENABLE"])
        layout_awb.addWidget(self.check_awb)
        
        settings_layout.addLayout(layout_shutter)
        settings_layout.addWidget(self.check_auto_gain)
        settings_layout.addWidget(self.gain_widget)
        settings_layout.addLayout(self.layout_ev_controls) # Adiciona EV aqui
        settings_layout.addLayout(layout_focus)
        settings_layout.addLayout(layout_awb)
        
        settings_widget = QWidget()
        settings_widget.setLayout(settings_layout)

        self.toggle_gain_controls()

        self.apply_button = QPushButton("Aplicar e Salvar")
        self.apply_button.clicked.connect(lambda: self.reconfigure_camera_and_apply(is_initial_setup=False))

        self.close_button = QPushButton("Fechar Aplicativo")
        self.close_button.clicked.connect(self.close)

        actions_layout = QVBoxLayout()
        actions_layout.addWidget(self.apply_button)
        actions_layout.addWidget(self.close_button)
        actions_layout.addStretch() 
        
        actions_widget = QWidget()
        actions_widget.setLayout(actions_layout)

        roi_groupbox = self.create_roi_panel()

        panel_layout.addWidget(mode_groupbox, stretch=2)
        panel_layout.addWidget(settings_widget, stretch=4)
        panel_layout.addWidget(roi_groupbox, stretch=3)
        panel_layout.addStretch(1)
        panel_layout.addWidget(actions_widget, stretch=2)
        
        return panel_frame

    def create_roi_panel(self):
        roi_groupbox = QGroupBox("Enquadramento ROI (736x736)")
        roi_layout = QVBoxLayout()
        roi_layout.setSpacing(6)

        self.check_roi = QCheckBox("Ativar Recorte ROI (736x736)")
        self.check_roi.setChecked(self.roi_enabled)
        self.check_roi.toggled.connect(self.on_roi_toggle)
        roi_layout.addWidget(self.check_roi)

        self.roi_controls_widget = QWidget()
        ctrls_layout = QVBoxLayout(self.roi_controls_widget)
        ctrls_layout.setContentsMargins(0, 0, 0, 0)
        ctrls_layout.setSpacing(4)

        self.label_roi_info = QLabel(f"Posição: X={self.roi_x} | Y={self.roi_y}")
        self.label_roi_info.setStyleSheet("font-weight: bold; color: #D32F2F;")
        ctrls_layout.addWidget(self.label_roi_info)

        lbl_x = QLabel("Deslocamento X (Horizontal):")
        self.slider_roi_x = QSlider(Qt.Horizontal)
        self.slider_roi_x.setMinimum(0)
        self.slider_roi_x.setMaximum(max(0, self.current_mode_width - self.roi_w))
        self.slider_roi_x.setValue(self.roi_x)
        self.slider_roi_x.valueChanged.connect(self.on_roi_slider_changed)
        ctrls_layout.addWidget(lbl_x)
        ctrls_layout.addWidget(self.slider_roi_x)

        lbl_y = QLabel("Deslocamento Y (Vertical):")
        self.slider_roi_y = QSlider(Qt.Horizontal)
        self.slider_roi_y.setMinimum(0)
        self.slider_roi_y.setMaximum(max(0, self.current_mode_height - self.roi_h))
        self.slider_roi_y.setValue(self.roi_y)
        self.slider_roi_y.valueChanged.connect(self.on_roi_slider_changed)
        ctrls_layout.addWidget(lbl_y)
        ctrls_layout.addWidget(self.slider_roi_y)

        btn_center = QPushButton("Centralizar Recorte")
        btn_center.clicked.connect(self.center_roi)
        ctrls_layout.addWidget(btn_center)

        roi_layout.addWidget(self.roi_controls_widget)
        roi_layout.addStretch()
        roi_groupbox.setLayout(roi_layout)

        self.update_roi_limits()
        return roi_groupbox

    def on_roi_toggle(self, checked):
        self.roi_enabled = checked
        self.roi_controls_widget.setEnabled(checked)
        self.floating_overlay.update()

    def on_roi_slider_changed(self):
        self.roi_x = self.slider_roi_x.value()
        self.roi_y = self.slider_roi_y.value()
        self.label_roi_info.setText(f"Posição: X={self.roi_x} | Y={self.roi_y}")
        self.floating_overlay.update()

    def center_roi(self):
        max_x = max(0, self.current_mode_width - self.roi_w)
        max_y = max(0, self.current_mode_height - self.roi_h)
        self.slider_roi_x.setValue(max_x // 2)
        self.slider_roi_y.setValue(max_y // 2)

    def update_roi_limits(self):
        can_support = (self.current_mode_width >= self.roi_w and self.current_mode_height >= self.roi_h)
        if not can_support:
            self.check_roi.setEnabled(False)
            self.check_roi.setChecked(False)
            self.check_roi.setToolTip(f"O modo {self.current_mode_width}x{self.current_mode_height} é menor que {self.roi_w}x{self.roi_h}.")
            self.roi_controls_widget.setEnabled(False)
        else:
            self.check_roi.setEnabled(True)
            self.check_roi.setToolTip("Gravar recorte direto de 736x736 pelo hardware da câmera.")
            max_x = max(0, self.current_mode_width - self.roi_w)
            max_y = max(0, self.current_mode_height - self.roi_h)
            self.slider_roi_x.setMaximum(max_x)
            self.slider_roi_y.setMaximum(max_y)
            if self.slider_roi_x.value() > max_x:
                self.slider_roi_x.setValue(max_x)
            if self.slider_roi_y.value() > max_y:
                self.slider_roi_y.setValue(max_y)
            self.roi_controls_widget.setEnabled(self.check_roi.isChecked())
        self.floating_overlay.update()

    def toggle_gain_controls(self):
        is_auto = self.check_auto_gain.isChecked()
        self.gain_widget.setEnabled(not is_auto)
        
    def adjust_shutter(self, delta):
        try:
            current_value = int(self.label_shutter_value.text())
            new_value = max(100, current_value + delta) 
            self.label_shutter_value.setText(str(new_value))
            self.picam2.set_controls({"ExposureTime": new_value})
        except ValueError:
            pass

    def adjust_gain(self, delta):
        try:
            current_value = float(self.label_gain_value.text())
            new_value = max(1.0, current_value + delta) 
            self.label_gain_value.setText(f"{new_value:.1f}")
            if not self.check_auto_gain.isChecked():
                self.picam2.set_controls({"AnalogueGain": new_value})
        except ValueError:
            pass

    def adjust_ev(self, delta):
        try:
            current_value = float(self.label_ev_value.text())
            new_value = current_value + delta
            # Limita entre -10 e 10 (segurança, embora -2 a 2 seja o comum)
            if new_value > 10.0: new_value = 10.0
            if new_value < -10.0: new_value = -10.0
            
            self.label_ev_value.setText(f"{new_value:.1f}")
            # Aplica no preview se estiver em auto gain
            if self.check_auto_gain.isChecked():
                self.picam2.set_controls({"ExposureValue": new_value})
        except ValueError:
            pass

    def adjust_focus(self, delta_internal):
        self.current_focus_internal = max(0, min(1000, self.current_focus_internal + delta_internal))
        lens_position = self.current_focus_internal / 100.0
        self.label_focus_value.setText(f"{lens_position:.2f}")
        self.picam2.set_controls({"LensPosition": lens_position})

    def on_mode_change(self):
        if self.sender().isChecked():
            for key, radio in self.mode_radios.items():
                if radio.isChecked():
                    mode_info = CAMERA_MODES.get(key, {})
                    self.current_mode_width, self.current_mode_height = mode_info.get("resolution", (2304, 1296))
                    break
            self.update_roi_limits()
            self.reconfigure_camera_and_apply(is_initial_setup=True)

    def reconfigure_camera_and_apply(self, is_initial_setup=False):
        try:
            shutter_speed = int(self.label_shutter_value.text())
            analogue_gain = float(self.label_gain_value.text())
            lens_position = float(self.label_focus_value.text())
            awb_enabled = self.check_awb.isChecked()
            auto_gain_enabled = self.check_auto_gain.isChecked()
            ev_val = float(self.label_ev_value.text())
            
            self.current_focus_internal = int(lens_position * 100) 
            
            current_mode_key = "HIGH_QUALITY"
            for key, radio in self.mode_radios.items():
                if radio.isChecked():
                    current_mode_key = key
                    break
            
            mode_config = CAMERA_MODES.get(current_mode_key, CAMERA_MODES["HIGH_QUALITY"])

            if is_initial_setup:
                self.picam2.stop()
                
                # Para resoluções nativas acima de 2304x1296, dimensiona o preview widget para segurança
                p_w = min(mode_config["resolution"][0], 2304)
                p_h = min(mode_config["resolution"][1], 1296)

                preview_config = self.picam2.create_preview_configuration(
                    main={"size": (p_w, p_h)},
                    controls={"FrameRate": mode_config["fps"]},
                    queue=False, 
                    buffer_count=4 
                )
                
                self.picam2.configure(preview_config)
            
            controls = {
                "LensPosition": lens_position,
                "AfMode": 0,
                "AwbEnable": awb_enabled
            }
            
            if auto_gain_enabled:
                controls["AeEnable"] = True
                controls["ExposureValue"] = ev_val # Aplica o EV no preview
            else:
                controls["AeEnable"] = False
                controls["ExposureTime"] = shutter_speed
                controls["AnalogueGain"] = analogue_gain
                # Em manual, EV é ignorado
            
            if not awb_enabled:
                controls["ColourGains"] = (1.0, 1.0)
                
            self.picam2.set_controls(controls)
            
            if is_initial_setup:
                self.picam2.start()
            
            if not is_initial_setup:
                with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    f.write(f"MODE: {current_mode_key}\n")
                    f.write(f"SHUTTER_SPEED: {shutter_speed}\n")
                    f.write(f"ANALOGUE_GAIN: {analogue_gain}\n")
                    f.write(f"LENS_POSITION: {lens_position}\n")
                    f.write(f"AWB_ENABLE: {awb_enabled}\n")
                    f.write(f"AUTO_GAIN: {auto_gain_enabled}\n")
                    f.write(f"EXPOSURE_VALUE: {ev_val}\n")
                    f.write(f"HDR_ENABLE: {mode_config.get('is_hdr', False)}\n")
                    f.write(f"ROI_ENABLE: {self.check_roi.isChecked()}\n")
                    f.write(f"ROI_WIDTH: {self.roi_w}\n")
                    f.write(f"ROI_HEIGHT: {self.roi_h}\n")
                    f.write(f"ROI_X: {self.roi_x}\n")
                    f.write(f"ROI_Y: {self.roi_y}\n")
                print(f"[LOG] Configurações salvas em {SETTINGS_FILE}. Modo: {current_mode_key}, ROI: {self.check_roi.isChecked()} ({self.roi_w}x{self.roi_h} em X={self.roi_x}, Y={self.roi_y})")

        except Exception as e:
            print(f"[ERRO] Erro ao aplicar configurações: {e}")
            traceback.print_exc()

    def closeEvent(self, event):
        self.floating_overlay.close()
        self.picam2.stop()
        event.accept()

if __name__ == "__main__":
    import os
    from PyQt5.QtGui import QSurfaceFormat

    format = QSurfaceFormat()
    format.setSwapInterval(1) 
    QSurfaceFormat.setDefaultFormat(format)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    loaded_config = load_settings()
    picam2 = Picamera2()

    window = CameraControlWindow(picam2, loaded_config)
    window.resize(1180, 750)
    window.show()
    
    sys.exit(app.exec())
