#!/usr/bin/env python3
#############################################
# Copyright © 2026 SpcCb
# GitHub : https://github.com/SpcCb
# SPDX-License-Identifier: GPL-3.0-or-later
# Support: https://github.com/SpcCb/AOBPP-GUI
#############################################

"""
Advanced OSC Batch Pre-Processing GUI for Siril
requires Siril v1.4.5

Version History
===============
1.0.0 Intial version
"""

# Versions requises
VERSION = "1.0.0"
REQUIREDVERSION = "1.4.5"

# Import des modules
import os
import sys
import math
import re
import shutil
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from functools import partial

# Installation automatique et importation des dépendances via sirilpy
import sirilpy as s
s.ensure_installed("PyQt6", "astropy", "numpy", "rawpy", "ExifRead")

# Connexion à l'interface de Siril
siril = s.SirilInterface()
try:
    siril.connect()
except Exception as e:
    print(f"Siril connection notice: {e}")

import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QCheckBox, QMessageBox, QGroupBox,
    QComboBox, QRadioButton, QButtonGroup, QDoubleSpinBox, QSplitter, QGridLayout,
    QSlider, QListWidget, QDialog, QProgressBar, QSizePolicy, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QRectF, QPoint, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath, QImage, QPixmap, QPolygon

# Inspection des métadonnées FITS via astropy
try:
    from astropy.io import fits
    from astropy.coordinates import EarthLocation, AltAz, SkyCoord
    from astropy.time import Time
    import astropy.units as u
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

try:
    import rawpy
    HAS_RAWPY = True
except ImportError:
    HAS_RAWPY = False

try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False

# Définition des styles de base pour l'UI
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}
QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background-color: #323232;
}
QTabBar::tab {
    background-color: #2b2b2b;
    color: #a0a0a0;
    padding: 8px 16px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #323232;
    color: #ffffff;
    font-weight: bold;
}
QPushButton {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    padding: 5px 10px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #4c4c4c;
}
QPushButton:pressed {
    background-color: #2a2a2a;
}
QPushButton#RunButton {
    background-color: #2e7d32;
    color: white;
    font-weight: bold;
    font-size: 11pt;
    padding: 10px;
}
QPushButton#RunButton:hover {
    background-color: #388e3c;
}
QLineEdit, QTableWidget, QDoubleSpinBox, QListWidget, QPlainTextEdit {
    background-color: #1e1e1e;
    color: #ffffff;
    border: 1px solid #3c3c3c;
    selection-background-color: #007acc;
    padding: 4px;
}
QComboBox {
    background-color: #1e1e1e;
    color: #ffffff;
    border: 1px solid #3c3c3c;
    padding: 4px 24px 4px 6px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left-width: 1px;
    border-left-color: #3c3c3c;
    border-left-style: solid;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    background: #353535;
}
QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #aaaaaa;
    margin-top: 1px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #ffffff;
    selection-background-color: #007acc;
    selection-color: #ffffff;
    border: 1px solid #3c3c3c;
    outline: none;
}
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled {
    background-color: #181818;
    color: #555555;
    border: 1px solid #2a2a2a;
}
QLabel:disabled, QCheckBox:disabled, QRadioButton:disabled {
    color: #555555;
}
QHeaderView::section {
    background-color: #323232;
    color: #ffffff;
    padding: 4px;
    border: 1px solid #3c3c3c;
}
QTableCornerButton::section {
    background-color: #323232;
    border: 1px solid #3c3c3c;
}
QCheckBox, QRadioButton, QGroupBox {
    color: #e0e0e0;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}
"""

# Fenêtre de suivi en temps réel de l'avancement des étapes dans Siril
class ConsoleProgressDialog(QDialog):
    def __init__(self, parent=None, title="Siril Pre-Processing Progress"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(740, 440)
        self.setModal(False)
        self._running = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.lbl_status = QLabel("Preparing pre-processing...")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
                font-size: 8.5pt;
            }
            QProgressBar::chunk {
                background-color: #2e7d32;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.txt_console = QPlainTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #141414;
                color: #dcdcdc;
                border: 1px solid #3c3c3c;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 9pt;
            }
        """)
        layout.addWidget(self.txt_console, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.close)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    # Ajout d'une ligne horodatée dans la console et défilement automatique
    def append_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.txt_console.appendPlainText(f"[{now}] {message}")
        sb = self.txt_console.verticalScrollBar()
        sb.setValue(sb.maximum())
        QApplication.processEvents()

    # Mise à jour de la barre de progression et du libellé courant
    def set_step_progress(self, current: int, total: int, status_text: str):
        self.lbl_status.setText(status_text)
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        QApplication.processEvents()

    # Finalisation de la fenêtre une fois toutes les étapes traitées ou en cas d'erreur
    def mark_finished(self, success: bool, summary: str):
        self._running = False
        self.btn_close.setEnabled(True)
        self.append_log("-" * 55)
        self.append_log(summary)
        if success:
            self.lbl_status.setText("Pre-processing completed.")
        else:
            self.lbl_status.setText("Pre-processing stopped due to an error.")
        QApplication.processEvents()

    # Empêche la fermeture accidentelle pendant qu'une étape Siril est en cours
    def closeEvent(self, event):
        if self._running:
            event.ignore()
        else:
            super().closeEvent(event)

# Boîte de dialogue modale affichant la progression du chargement des fichiers
class FileLoadingDialog(QDialog):
    def __init__(self, parent=None, title="Loading files"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(440, 100)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        self.lbl_status = QLabel("Initializing loading...")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
                font-size: 8pt;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

    # Mise à jour du texte d'état et de la barre de progression
    def set_status(self, text, val, max_val):
        self.lbl_status.setText(text)
        if max_val > 0:
            self.progress_bar.setMaximum(max_val)
            self.progress_bar.setValue(val)
        QApplication.processEvents()

# Conteneur d'aperçu des Flats déclenchant un redimensionnement dynamique de l'image
class FlatPreviewGroupBox(QGroupBox):
    def __init__(self, title, app_ref, parent=None):
        super().__init__(title, parent)
        self.app_ref = app_ref

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self.app_ref, 'update_flat_preview'):
            self.app_ref.update_flat_preview()

# Conteneur d'aperçu des Lights déclenchant un redimensionnement dynamique de l'image
class LightPreviewGroupBox(QGroupBox):
    def __init__(self, title, app_ref, parent=None):
        super().__init__(title, parent)
        self.app_ref = app_ref

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self.app_ref, 'update_light_preview'):
            self.app_ref.update_light_preview()

# Conteneur d'aperçu des images de calibration (Biases / Darks) adapté au redimensionnement
class CalibrationPreviewGroupBox(QGroupBox):
    def __init__(self, title, app_ref, category, parent=None):
        super().__init__(title, parent)
        self.app_ref = app_ref
        self.category = category

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self.app_ref, 'update_calibration_preview'):
            self.app_ref.update_calibration_preview(self.category)

# Widget d'affichage de l'histogramme et des statistiques min/max/médiane d'une image de calibration
class HistogramStretchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.data = None
        self.hist_bins = None
        self.hist_counts = None
        self.v_min = 0.0
        self.v_max = 65535.0
        self.median_val = 0.0
        self.max_bin_idx = 0

    # Calcul des percentiles, de la médiane et des classes de l'histogramme
    def set_data(self, data):
        if data is None or data.size == 0:
            self.data = None
            self.hist_bins = None
            self.hist_counts = None
            self.v_min = 0.0
            self.v_max = 65535.0
            self.median_val = 0.0
            self.update()
            return
        
        self.data = data.astype(np.float32)
        if self.data.max() <= 1.0:
            self.data = self.data * 65535.0

        flat_data = self.data.ravel()
        self.v_min = float(np.percentile(flat_data, 0.1))
        self.v_max = float(np.percentile(flat_data, 99.9))
        self.median_val = float(np.median(flat_data))
        if self.v_max <= self.v_min:
            self.v_max = self.v_min + 1.0

        clipped = np.clip(flat_data, self.v_min, self.v_max)
        counts, bins = np.histogram(clipped, bins=100)
        self.hist_counts = counts
        self.hist_bins = bins
        if len(counts) > 0:
            self.max_bin_idx = int(np.argmax(counts))
        else:
            self.max_bin_idx = 50
        self.update()

    # Dessin graphique de l'histogramme et des repères numériques
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#1e1e1e"))

        bar_area_h = h - 16
        if self.hist_counts is not None and len(self.hist_counts) > 0:
            max_count = np.max(self.hist_counts)
            if max_count == 0:
                max_count = 1
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#007acc"))

            bin_width = w / len(self.hist_counts)
            for i, count in enumerate(self.hist_counts):
                bar_h = int((count / max_count) * bar_area_h)
                x = int(i * bin_width)
                y = bar_area_h - bar_h
                painter.drawRect(x, y, max(1, int(bin_width)), bar_h)

        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QColor("#aaaaaa"))
        fm = painter.fontMetrics()

        text_min = f"{int(round(self.v_min))}"
        text_max = f"{int(round(self.v_max))}"
        text_med = f"Med: {int(round(self.median_val))}"

        w_min = fm.horizontalAdvance(text_min)
        w_max = fm.horizontalAdvance(text_max)
        w_med = fm.horizontalAdvance(text_med)

        painter.drawText(4, h - 3, text_min)
        painter.drawText(w - w_max - 4, h - 3, text_max)

        if self.hist_counts is not None and len(self.hist_counts) > 0:
            bin_width = w / len(self.hist_counts)
            peak_x = (self.max_bin_idx + 0.5) * bin_width
            med_x = int(peak_x - w_med / 2)
            min_allowed_x = w_min + 8
            max_allowed_x = w - w_max - w_med - 8
            med_x = max(min_allowed_x, min(max_allowed_x, med_x))
            painter.drawText(med_x, h - 3, text_med)

# Conversion d'une ascension droite (heures/sexagésimal ou degrés) en degrés décimaux
def parse_ra_deg(ra_val):
    if ra_val is None:
        return None
    if isinstance(ra_val, (int, float)):
        return float(ra_val)
    try:
        s_val = str(ra_val).strip()
        if not any(c in s_val for c in ['h', 'm', 's', ':', ' ']):
            return float(s_val)
        s_clean = re.sub(r'[hmsHMS\'"]', ':', s_val)
        parts = [p for p in re.split(r'[:\s]+', s_clean) if p]
        if len(parts) == 3:
            h, m, s_deg = float(parts[0]), float(parts[1]), float(parts[2])
            return (h + m/60.0 + s_deg/3600.0) * 15.0
        elif len(parts) == 2:
            h, m = float(parts[0]), float(parts[1])
            return (h + m/60.0) * 15.0
        elif len(parts) == 1:
            return float(parts[0])
    except Exception:
        pass
    return None

# Conversion d'une déclinaison (sexagésimal ou degrés) en degrés décimaux
def parse_dec_deg(dec_val):
    if dec_val is None:
        return None
    if isinstance(dec_val, (int, float)):
        return float(dec_val)
    try:
        s_val = str(dec_val).strip()
        sign = -1.0 if s_val.startswith('-') else 1.0
        s_clean = re.sub(r'[dmsDMS°\'"]', ':', s_val.lstrip('+-'))
        parts = [p for p in re.split(r'[:\s]+', s_clean) if p]
        if len(parts) == 3:
            d, m, s_deg = float(parts[0]), float(parts[1]), float(parts[2])
            return sign * (d + m/60.0 + s_deg/3600.0)
        elif len(parts) == 2:
            d, m = float(parts[0]), float(parts[1])
            return sign * (d + m/60.0)
        elif len(parts) == 1:
            return sign * abs(float(parts[0]))
    except Exception:
        pass
    return None

# Calcul de la hauteur (altitude en degrés) d'une cible céleste selon l'instant et la position géographique
def calculate_altitude(ra_deg, dec_deg, dt_obs, lat_deg=45.5, lon_deg=3.0):
    if ra_deg is None or dec_deg is None or dt_obs is None:
        return None

    if dt_obs.tzinfo is None:
        dt_utc = dt_obs.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt_obs.astimezone(timezone.utc)

    if HAS_ASTROPY:
        try:
            location = EarthLocation(lat=lat_deg * u.deg, lon=lon_deg * u.deg)
            obstime = Time(dt_utc)
            coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
            altaz = coord.transform_to(AltAz(obstime=obstime, location=location))
            return float(altaz.alt.deg)
        except Exception:
            pass

    try:
        Y, M, D = dt_utc.year, dt_utc.month, dt_utc.day
        if M <= 2:
            Y -= 1
            M += 12
        A = math.floor(Y / 100)
        B = 2 - A + math.floor(A / 4)
        day_frac = (dt_utc.hour - 12) / 24.0 + dt_utc.minute / 1440.0 + dt_utc.second / 86400.0
        jd = math.floor(365.25 * (Y + 4716)) + math.floor(30.6001 * (M + 1)) + D + day_frac + B - 1524.5
        
        d = jd - 2451545.0
        gst = (280.46061837 + 360.98564736629 * d) % 360.0
        lst = (gst + lon_deg) % 360.0
        
        ha_rad = math.radians((lst - ra_deg) % 360.0)
        dec_rad = math.radians(dec_deg)
        lat_rad = math.radians(lat_deg)
        
        sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad)
        sin_alt = max(-1.0, min(1.0, sin_alt))
        return math.degrees(math.asin(sin_alt))
    except Exception:
        return None

# Chargement et étirement d'une image FITS/RAW pour l'aperçu des Flats
def load_fits_preview_pixmap(file_path, target_width=260, stretch_pct=1.0):
    default_h = int(target_width * 2 / 3)
    if not file_path or not os.path.exists(file_path):
        return None, default_h
    try:
        ext = os.path.splitext(file_path)[1].lower()
        data = None
        if ext in ['.fits', '.fit', '.fts', '.xisf'] and HAS_ASTROPY:
            with fits.open(file_path, ignore_missing_end=True) as hdul:
                data = hdul[0].data
                if data is None and len(hdul) > 1:
                    data = hdul[1].data
        elif ext in ['.cr2', '.nef', '.arw', '.dng'] and HAS_RAWPY:
            with rawpy.imread(file_path) as raw:
                data = raw.raw_image.astype(np.float32)

        if data is not None:
            while data.ndim > 2:
                data = data[0]
            data = data.astype(np.float32)
            if data.max() <= 1.0:
                data = data * 65535.0

            orig_h, orig_w = data.shape
            target_height = int(target_width * orig_h / orig_w)
            target_height = max(50, min(800, target_height))

            p_high = 100.0 - stretch_pct
            p_low = min(p_high - 0.1, stretch_pct * 2.5)
            
            v_min, v_max = np.percentile(data, p_low), np.percentile(data, p_high)
            
            if v_max > v_min:
                data = np.clip((data - v_min) / (v_max - v_min) * 255.0, 0, 255)
            else:
                data = np.zeros_like(data)
                
            img_uint8 = data.astype(np.uint8)
            qimg = QImage(img_uint8.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg).scaled(target_width, target_height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return pixmap, target_height
    except Exception:
        pass
    return None, int(target_width * 2 / 3)

# Chargement et étirement centré d'une image brute ou FITS pour l'aperçu des Lights
def load_lights_preview_pixmap(file_path, target_width=120, target_height=80, stretch_val=5.0):
    if not file_path or not os.path.exists(file_path):
        return None, target_width, target_height
    try:
        ext = os.path.splitext(file_path)[1].lower()
        data = None
        if ext in ['.fits', '.fit', '.fts', '.xisf'] and HAS_ASTROPY:
            with fits.open(file_path, ignore_missing_end=True) as hdul:
                data = hdul[0].data
                if data is None and len(hdul) > 1:
                    data = hdul[1].data
        elif ext in ['.cr2', '.nef', '.arw', '.dng'] and HAS_RAWPY:
            with rawpy.imread(file_path) as raw:
                data = raw.raw_image.astype(np.float32)

        if data is not None:
            while data.ndim > 2:
                data = data[0]
            data = data.astype(np.float32)
            if data.max() <= 1.0:
                data = data * 65535.0

            orig_h, orig_w = data.shape

            half_range = max(1.0, 50.0 - (stretch_val * 1.92))
            p_low = 50.0 - half_range
            p_high = 50.0 + half_range

            v_min, v_max = np.percentile(data, p_low), np.percentile(data, p_high)
            if v_max <= v_min:
                v_max = v_min + 1.0

            clipped = np.clip((data - v_min) / (v_max - v_min) * 255.0, 0, 255)
            img_uint8 = clipped.astype(np.uint8)
            qimg = QImage(img_uint8.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg).scaled(target_width, target_height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return pixmap, target_width, target_height
    except Exception:
        pass
    return None, target_width, target_height

# Génération de l'aperçu et du calcul du SNR pour les images de calibration (Biases / Darks)
def load_calibration_preview_pixmap(file_path, target_width=260):
    default_h = int(target_width * 2 / 3)
    if not file_path or not os.path.exists(file_path):
        return None, default_h, None
    try:
        ext = os.path.splitext(file_path)[1].lower()
        data = None
        if ext in ['.fits', '.fit', '.fts', '.xisf'] and HAS_ASTROPY:
            with fits.open(file_path, ignore_missing_end=True) as hdul:
                data = hdul[0].data
                if data is None and len(hdul) > 1:
                    data = hdul[1].data
        elif ext in ['.cr2', '.nef', '.arw', '.dng'] and HAS_RAWPY:
            with rawpy.imread(file_path) as raw:
                data = raw.raw_image.astype(np.float32)

        if data is not None:
            while data.ndim > 2:
                data = data[0]
            data = data.astype(np.float32)
            if data.max() <= 1.0:
                data = data * 65535.0

            orig_h, orig_w = data.shape
            target_height = int(target_width * orig_h / orig_w)
            target_height = max(50, min(800, target_height))

            flat_flat = data.ravel()
            v_min = float(np.percentile(flat_flat, 0.1))
            v_max = float(np.percentile(flat_flat, 99.9))

            if v_max <= v_min:
                v_max = v_min + 1.0

            std_v = float(np.std(flat_flat))
            mean_v = float(np.mean(flat_flat))
            rsb_v = (mean_v / std_v) if std_v > 1e-6 else 0.0

            text_snr = f"SNR: {int(round(rsb_v))}"

            clipped_data = np.clip((data - v_min) / (v_max - v_min) * 255.0, 0, 255)
            img_uint8 = clipped_data.astype(np.uint8)
            qimg = QImage(img_uint8.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg).scaled(target_width, target_height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            
            fm = painter.fontMetrics()
            box_w = fm.horizontalAdvance(text_snr) + 12
            box_h = 20
            box_x = target_width - box_w - 6
            box_y = 6
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 160))
            painter.drawRoundedRect(box_x, box_y, box_w, box_h, 3, 3)
            
            painter.setPen(QColor("#ffffff"))
            painter.drawText(box_x + 6, box_y + 14, text_snr)
            painter.end()

            return pixmap, target_height, data
    except Exception:
        pass
    return None, default_h, None

# Widget de visualisation chronologique des poses et courbes de hauteur (FITS) ou durées (RAW)
class ImagingTimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.sub_data = []
        self.mode = "EMPTY"
        self.summary_title = "Imaging timeline"
        self.summary_sub = "No Light frames loaded"
        self.summary_header_right = ""
        self.summary_footer = "Timeline overview"

    # Réception des métadonnées des Lights et mise à jour du mode d'affichage
    def set_data(self, files_metadata):
        self.sub_data = files_metadata
        if not files_metadata:
            self.mode = "EMPTY"
            self.summary_title = "Imaging timeline"
            self.summary_sub = "No Light frames loaded"
            self.summary_header_right = ""
        else:
            first_path = files_metadata[0].get("file_path", "")
            ext = os.path.splitext(first_path)[1].lower()
            if ext in ['.cr2', '.nef', '.arw', '.dng']:
                self.mode = "RAW"
            else:
                self.mode = "FITS"
            self.update_summary()
        self.update()

    # Calcul des libellés récapitulatifs (nuits, filtres, temps de pose cumulé)
    def update_summary(self):
        total_subs = len(self.sub_data)
        total_sec = sum(d.get("exp_sec", 0) for d in self.sub_data)
        hours = int(total_sec // 3600)
        mins = int((total_sec % 3600) // 60)
        
        nights_dict = defaultdict(list)
        filters = set()
        exposures = set()
        dates_dt = []
        
        for d in self.sub_data:
            dt = d.get("date") or datetime.now()
            dates_dt.append(dt)
            obs_night = (dt - timedelta(hours=12)).strftime("%Y-%m-%d")
            nights_dict[obs_night].append(d)

            if d.get("filter"):
                filters.add(d["filter"])
            if d.get("exp_sec"):
                exposures.add(f"{int(d['exp_sec'])}s")

        num_nights = len(nights_dict) if nights_dict else 1
        filt_str = ", ".join(filters) if filters else "No Filter"
        exp_str = ", ".join(exposures) if exposures else "subs"

        if dates_dt:
            dates_dt.sort()
            start_m = dates_dt[0].strftime("%b %Y")
            self.summary_header_right = f"{start_m} · {num_nights} night{'s' if num_nights > 1 else ''}"
        else:
            self.summary_header_right = ""

        self.summary_title = "Imaging timeline" # Il va falloir encore un peu réfléchir aux textes, je ne suis pas tout à fait convaincu de leurs pertinances..
        if self.mode == "RAW":
            self.summary_sub = f"{num_nights} night{'s' if num_nights > 1 else ''}, RAW exposures ({exp_str})"
            self.summary_footer = f"Exposure durations / {num_nights} night{'s' if num_nights > 1 else ''} / {total_subs} subs / {hours}h {mins}m kept"
        else:
            self.summary_sub = f"{num_nights} night{'s' if num_nights > 1 else ''}, {filt_str}, {exp_str} subs"
            self.summary_footer = f"Altitude during exposures / {num_nights} night{'s' if num_nights > 1 else ''} / {total_subs} subs / {hours}h {mins}m kept"

    # Rendu graphique de la chronologie par nuit d'observation
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#181818"))
        
        painter.setPen(QColor("#ffffff"))
        font_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.drawText(15, 22, self.summary_title)

        if self.summary_header_right:
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(w - 180, 22, self.summary_header_right)

        font_sub = QFont("Segoe UI", 8)
        painter.setFont(font_sub)
        painter.setPen(QColor("#a0a0a0"))
        painter.drawText(15, 38, self.summary_sub)

        if self.mode == "EMPTY":
            painter.setPen(QColor("#555555"))
            painter.drawText(15, h // 2 + 10, "Add Light files to visualize imaging timeline.")
            return

        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.setPen(QColor("#777777"))
        painter.drawText(15, h - 8, self.summary_footer)

        top_y = 50
        bottom_y = h - 55
        plot_h = bottom_y - top_y
        left_x = 45
        right_x = w - 20
        plot_w = right_x - left_x

        nights_dict = defaultdict(list)
        for sub in self.sub_data:
            dt = sub.get("date") or datetime.now()
            obs_night = (dt - timedelta(hours=12)).strftime("%Y-%m-%d")
            nights_dict[obs_night].append(sub)

        sorted_nights = sorted(nights_dict.keys())
        num_nights = len(sorted_nights)

        night_w = plot_w / max(1, num_nights)
        
        for n_idx, night_key in enumerate(sorted_nights):
            subs_in_night = nights_dict[night_key]
            subs_in_night.sort(key=lambda s: (s.get("date") or datetime.now(), s.get("file_path", "")))

            n_start_x = left_x + n_idx * night_w + 10
            actual_w = max(40.0, night_w - 20)

            night_sub_starts = [s.get("date") for s in subs_in_night if s.get("date") is not None]
            night_sub_ends = [(s.get("date") + timedelta(seconds=s.get("exp_sec", 300))) for s in subs_in_night if s.get("date") is not None]
            
            if night_sub_starts and night_sub_ends:
                start_dt = min(night_sub_starts)
                end_dt = max(night_sub_ends)
            else:
                start_dt = datetime.now()
                end_dt = start_dt + timedelta(hours=1)

            time_span = (end_dt - start_dt).total_seconds()
            if time_span < 60:
                start_dt -= timedelta(minutes=30)
                end_dt += timedelta(minutes=30)
                time_span = (end_dt - start_dt).total_seconds()
            else:
                margin = max(300.0, time_span * 0.05)
                start_dt -= timedelta(seconds=margin)
                end_dt += timedelta(seconds=margin)
                time_span = (end_dt - start_dt).total_seconds()

            first_dt = night_sub_starts[0] if night_sub_starts else None
            label_date = f"{first_dt.strftime('%d %b.')}" if first_dt else night_key
            painter.setPen(QColor("#888888"))
            painter.drawText(int(n_start_x + actual_w / 2 - 18), bottom_y + 28, label_date)

            duration_hours = time_span / 3600.0

            if duration_hours <= 1.0:
                step_hours = 0.25
            elif duration_hours <= 3.0:
                step_hours = 0.5
            elif duration_hours <= 8.0:
                step_hours = 1.0
            elif duration_hours <= 16.0:
                step_hours = 2.0
            else:
                step_hours = 4.0

            painter.setPen(QPen(QColor("#444444"), 1, Qt.PenStyle.DashLine))
            
            current_t = start_dt.replace(minute=0, second=0, microsecond=0)
            if step_hours < 1.0:
                step_minutes = int(step_hours * 60)
                total_min = current_t.hour * 60 + current_t.minute
                aligned_min = (total_min // step_minutes) * step_minutes
                current_t = current_t.replace(hour=aligned_min // 60, minute=aligned_min % 60, second=0, microsecond=0)
                if current_t < start_dt:
                    current_t += timedelta(minutes=step_minutes)
            else:
                current_t = start_dt.replace(minute=0, second=0, microsecond=0)
                if current_t < start_dt:
                    current_t += timedelta(hours=1)
            
            while current_t <= end_dt + timedelta(hours=step_hours):
                if current_t >= start_dt - timedelta(hours=step_hours):
                    frac = (current_t - start_dt).total_seconds() / time_span
                    if 0.0 <= frac <= 1.0:
                        tick_x = n_start_x + frac * actual_w
                        painter.drawLine(int(tick_x), top_y, int(tick_x), bottom_y)
                        
                        if step_hours >= 1.0:
                            hour_str = current_t.strftime("%Hh")
                        else:
                            hour_str = current_t.strftime("%H:%M")

                        painter.setPen(QColor("#aaaaaa"))
                        painter.drawText(int(tick_x) - 14, bottom_y + 14, hour_str)
                        painter.setPen(QPen(QColor("#444444"), 1, Qt.PenStyle.DashLine))
                
                if step_hours < 1.0:
                    current_t += timedelta(minutes=int(step_hours * 60))
                else:
                    current_t += timedelta(hours=int(step_hours))

            if self.mode == "RAW":
                exps_in_night = [sub.get("exp_sec", 1.0) for sub in subs_in_night]
                max_exp = max(exps_in_night) if exps_in_night else 1.0
                if max_exp <= 0:
                    max_exp = 1.0

                painter.setFont(QFont("Segoe UI", 7))
                painter.setPen(QColor("#666666"))
                for ratio_val, label_txt in [(0.0, "0s"), (0.5, f"{int(max_exp*0.5)}s"), (1.0, f"{int(max_exp)}s")]:
                    y_pos = bottom_y - int(ratio_val * plot_h * 0.75)
                    painter.drawText(10, y_pos + 3, label_txt)
                    if ratio_val > 0.0:
                        painter.setPen(QPen(QColor("#2c2c2c"), 1, Qt.PenStyle.DashLine))
                        painter.drawLine(left_x, y_pos, right_x, y_pos)
                        painter.setPen(QColor("#666666"))

                for sub in subs_in_night:
                    sub_dt = sub.get("date") or start_dt
                    if time_span > 0:
                        frac = (sub_dt - start_dt).total_seconds() / time_span
                    else:
                        frac = 0.0
                    frac = max(0.0, min(1.0, frac))

                    x_p = n_start_x + frac * actual_w
                    exp_val = sub.get("exp_sec", 1.0)
                    
                    bar_h = int((exp_val / max_exp) * (plot_h * 0.75))
                    bar_h = max(8, min(int(plot_h * 0.75), bar_h))
                    y_p = bottom_y - bar_h

                    painter.setPen(QPen(QColor("#3498db"), 3))
                    painter.drawLine(int(x_p), bottom_y, int(x_p), int(y_p))

            else:
                all_alt_vals = []
                sub_arcs = []

                for sub in subs_in_night:
                    sub_start = sub.get("date") or start_dt
                    exp_sec = sub.get("exp_sec", 300.0)
                    sub_end = sub_start + timedelta(seconds=exp_sec)

                    ra_deg = sub.get("ra_deg")
                    dec_deg = sub.get("dec_deg")
                    lat_deg = sub.get("lat_deg", 45.5)
                    lon_deg = sub.get("lon_deg", 3.0)

                    if ra_deg is not None and dec_deg is not None and sub_start is not None:
                        month = sub_start.month
                        offset_hours = 2 if 4 <= month <= 10 else 1
                        sub_start_utc = sub_start - timedelta(hours=offset_hours)

                        alt_start = calculate_altitude(ra_deg, dec_deg, sub_start_utc, lat_deg, lon_deg)
                        alt_end = calculate_altitude(ra_deg, dec_deg, sub_start_utc + timedelta(seconds=exp_sec), lat_deg, lon_deg)

                        if alt_start is not None and alt_end is not None:
                            all_alt_vals.extend([alt_start, alt_end])
                            sub_arcs.append((sub_start, sub_end, alt_start, alt_end))

                if all_alt_vals:
                    min_a = min(all_alt_vals)
                    max_a = max(all_alt_vals)
                    if max_a - min_a < 10.0:
                        min_a -= 5.0
                        max_a += 5.0
                    else:
                        min_a -= 3.0
                        max_a += 3.0
                    min_a = max(0.0, min_a)
                    max_a = min(90.0, max_a)
                else:
                    min_a, max_a = 0.0, 90.0

                alt_span = max_a - min_a if max_a > min_a else 1.0

                painter.setFont(QFont("Segoe UI", 7))
                painter.setPen(QColor("#666666"))
                step_alt = max(5.0, (max_a - min_a) / 3.0)
                step_alt = round(step_alt / 5.0) * 5.0
                if step_alt < 5.0:
                    step_alt = 5.0

                curr_alt = math.ceil(min_a / step_alt) * step_alt
                while curr_alt <= max_a:
                    y_pos = bottom_y - int(((curr_alt - min_a) / alt_span) * plot_h)
                    if top_y <= y_pos <= bottom_y:
                        painter.drawText(10, y_pos + 3, f"{int(curr_alt)}°")
                        painter.setPen(QPen(QColor("#2c2c2c"), 1, Qt.PenStyle.DashLine))
                        painter.drawLine(left_x, y_pos, right_x, y_pos)
                        painter.setPen(QColor("#666666"))
                    curr_alt += step_alt

                painter.setPen(QPen(QColor("#d0d0d0"), 3.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)

                for sub_start, sub_end, alt_start, alt_end in sub_arcs:
                    if time_span > 0:
                        frac_start = (sub_start - start_dt).total_seconds() / time_span
                        frac_end = (sub_end - start_dt).total_seconds() / time_span
                    else:
                        frac_start = frac_end = 0.0

                    frac_start = max(0.0, min(1.0, frac_start))
                    frac_end = max(0.0, min(1.0, frac_end))

                    x_start = n_start_x + frac_start * actual_w
                    x_end = n_start_x + frac_end * actual_w

                    alt_c_start = max(min_a, min(max_a, alt_start))
                    alt_c_end = max(min_a, min(max_a, alt_end))

                    y_start = bottom_y - int(((alt_c_start - min_a) / alt_span) * plot_h)
                    y_end = bottom_y - int(((alt_c_end - min_a) / alt_span) * plot_h)

                    painter.drawLine(int(x_start), int(y_start), int(x_end), int(y_end))

# Extraction des métadonnées astronomiques et matérielles depuis un fichier FITS/XISF ou RAW
def inspect_fits_metadata(file_path):
    meta = {
        "file_path": file_path,
        "gain": None, "exposure": None, "filter": None, "exp_sec": 300,
        "date": None, "ra": None, "dec": None, "ra_deg": None, "dec_deg": None,
        "lat_deg": 45.5, "lon_deg": 3.0, "alt_deg": None,
        "scope_name": None, "focal_len": None, "f_ratio": None,
        "camera_name": None, "resolution": None, "binning": None, "sensor_temp": None,
        "focuser_name": None, "focuser_pos": None, "focuser_temp": None,
        "raw_temp_val": None, "raw_pos_val": None, "raw_foc_temp_val": None
    }
    if not os.path.exists(file_path):
        return meta

    ext = os.path.splitext(file_path)[1].lower()
    
    if HAS_ASTROPY and ext in ['.fits', '.fit', '.fts', '.xisf']:
        try:
            with fits.open(file_path, ignore_missing_end=True) as hdul:
                header = hdul[0].header
                data = hdul[0].data
                if data is None and len(hdul) > 1:
                    data = hdul[1].data

                if data is not None:
                    while data.ndim > 2:
                        data = data[0]
                    h_px, w_px = data.shape
                    meta["resolution"] = f"{w_px}x{h_px}px"

                exp = header.get('EXPTIME') or header.get('EXPOSURE')
                if exp is not None:
                    try:
                        meta["exp_sec"] = float(exp)
                        meta["exposure"] = f"{float(exp):.1f}s".replace('.0s', 's')
                    except ValueError:
                        pass

                gain = header.get('GAIN') or header.get('EGAIN')
                iso = header.get('ISOSPEED') or header.get('ISO')
                if gain is not None:
                    meta["gain"] = str(gain)
                elif iso is not None:
                    meta["gain"] = f"ISO {iso}"

                temp = header.get('CCD-TEMP') or header.get('SET-TEMP') or header.get('TEMPERAT')
                if temp is not None:
                    try:
                        t_val = float(temp)
                        meta["raw_temp_val"] = t_val
                        meta["sensor_temp"] = f"{t_val:.1f}°C"
                    except ValueError:
                        pass

                filt = header.get('FILTER') or header.get('FILT')
                if filt and str(filt).strip() and str(filt).strip().lower() != 'none':
                    meta["filter"] = str(filt).strip()

                scope = header.get('TELESCOP')
                if scope and str(scope).strip():
                    meta["scope_name"] = str(scope).strip()

                focal = header.get('FOCALLEN')
                if focal is not None:
                    try:
                        fl_val = float(focal)
                        meta["focal_len"] = f"{fl_val:.0f}mm"
                    except ValueError:
                        pass

                fratio = header.get('FOCRATIO') or header.get('F-RATIO')
                if fratio is not None:
                    try:
                        meta["f_ratio"] = f"f/{float(fratio):.1f}"
                    except ValueError:
                        pass
                elif focal is not None and header.get('APERTURE'):
                    try:
                        ap = float(header.get('APERTURE'))
                        fl = float(focal)
                        if ap > 0:
                            meta["f_ratio"] = f"f/{fl/ap:.1f}"
                    except Exception:
                        pass

                cam = header.get('INSTRUME') or header.get('CAMERA')
                if cam and str(cam).strip():
                    meta["camera_name"] = str(cam).strip()

                bin_x = header.get('XBINNING') or header.get('CCDXBIN') or 1
                bin_y = header.get('YBINNING') or header.get('CCDYBIN') or 1
                meta["binning"] = f"{bin_x}x{bin_y}"

                foc_name = header.get('FOCNAME') or header.get('FOCUSER')
                if foc_name and str(foc_name).strip():
                    meta["focuser_name"] = str(foc_name).strip()

                foc_pos = header.get('FOCPOS')
                if foc_pos is not None:
                    try:
                        p_val = int(foc_pos)
                        meta["raw_pos_val"] = p_val
                        meta["focuser_pos"] = f"{p_val} steps"
                    except ValueError:
                        pass

                foc_temp = header.get('FOCTEMP')
                if foc_temp is not None:
                    try:
                        ft_val = float(foc_temp)
                        meta["raw_foc_temp_val"] = ft_val
                        meta["focuser_temp"] = f"{ft_val:.1f}°C"
                    except ValueError:
                        pass

                date_str = header.get('DATE-OBS') or header.get('DATE')
                if date_str:
                    try:
                        s_d = str(date_str).strip()
                        dt_parsed = datetime.fromisoformat(s_d.replace('Z', '+00:00'))
                        if dt_parsed.tzinfo is None:
                            dt_parsed = dt_parsed.replace(tzinfo=timezone.utc)
                        
                        month = dt_parsed.month
                        offset_hours = 2 if 4 <= month <= 10 else 1
                        dt_local = dt_parsed + timedelta(hours=offset_hours)
                        meta["date"] = dt_local.replace(tzinfo=None)
                    except Exception:
                        pass

                ra_keys = ['RA', 'OBJCTRA', 'CRVAL1', 'RA_DEG', 'OBJ-RA', 'CAT-RA']
                for k in ra_keys:
                    if k in header and header[k] is not None:
                        meta["ra"] = header[k]
                        break

                dec_keys = ['DEC', 'OBJCTDEC', 'CRVAL2', 'DEC_DEG', 'OBJ-DEC', 'CAT-DEC']
                for k in dec_keys:
                    if k in header and header[k] is not None:
                        meta["dec"] = header[k]
                        break

                meta["ra_deg"] = parse_ra_deg(meta["ra"])
                meta["dec_deg"] = parse_dec_deg(meta["dec"])

                site_lat = header.get('SITELAT') or header.get('LATITUDE')
                site_lon = header.get('SITELONG') or header.get('LONGITUD')
                if site_lat is not None:
                    try:
                        meta["lat_deg"] = float(site_lat)
                    except ValueError:
                        pass
                if site_lon is not None:
                    try:
                        meta["lon_deg"] = float(site_lon)
                    except ValueError:
                        pass

                if meta["ra_deg"] is not None and meta["dec_deg"] is not None and meta["date"] is not None:
                    month = meta["date"].month
                    offset_hours = 2 if 4 <= month <= 10 else 1
                    dt_utc_calc = meta["date"] - timedelta(hours=offset_hours)
                    meta["alt_deg"] = calculate_altitude(
                        meta["ra_deg"], meta["dec_deg"], dt_utc_calc, meta["lat_deg"], meta["lon_deg"]
                    )

        except Exception:
            pass
    elif ext in ['.cr2', '.nef', '.arw', '.dng']:
        if HAS_EXIFREAD:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f, details=True)
                    
                    make = str(tags.get("Image Make", "")).strip()
                    model = str(tags.get("Image Model", "")).strip()
                    if make or model:
                        meta["camera_name"] = f"{make} {model}".strip()

                    w = tags.get("EXIF ExifImageWidth") or tags.get("Image ImageWidth")
                    h = tags.get("EXIF ExifImageLength") or tags.get("Image ImageLength")
                    if w and h:
                        meta["resolution"] = f"{w}x{h}px"

                    iso = tags.get("EXIF ISOSpeedRatings") or tags.get("Image ISOSpeed")
                    if iso:
                        meta["gain"] = f"ISO {iso}"

                    exp_tag = tags.get("EXIF ExposureTime") or tags.get("Image ExposureTime")
                    if exp_tag:
                        try:
                            val_str = str(exp_tag)
                            if '/' in val_str:
                                num, den = map(float, val_str.split('/'))
                                meta["exp_sec"] = num / den if den != 0 else 180
                            else:
                                meta["exp_sec"] = float(val_str)
                            meta["exposure"] = f"{meta['exp_sec']:.1f}s".replace('.0s', 's')
                        except Exception:
                            pass
            except Exception:
                pass

        if HAS_RAWPY:
            try:
                with rawpy.imread(file_path) as raw:
                    if not meta["camera_name"]:
                        maker = getattr(raw, 'camera_maker', b'').decode('utf-8', errors='ignore').strip()
                        model = getattr(raw, 'camera_model', b'').decode('utf-8', errors='ignore').strip()
                        if maker or model:
                            meta["camera_name"] = f"{maker} {model}".strip()

                    if not meta["resolution"]:
                        sizes = raw.sizes
                        if sizes.width > 0 and sizes.height > 0:
                            meta["resolution"] = f"{sizes.width}x{sizes.height}px"

                    if not meta["gain"]:
                        try:
                            iso = getattr(raw, 'iso_speed', None)
                            if iso:
                                meta["gain"] = f"ISO {iso}"
                        except Exception:
                            pass
            except Exception:
                pass

        meta["binning"] = "1x1"

        try:
            mtime = os.path.getmtime(file_path)
            dt_raw = datetime.fromtimestamp(mtime, tz=timezone.utc)
            month = dt_raw.month
            offset_hours = 2 if 4 <= month <= 10 else 1
            dt_local = dt_raw + timedelta(hours=offset_hours)
            meta["date"] = dt_local.replace(tzinfo=None)
        except Exception:
            meta["date"] = datetime.now()

        if "exp_sec" not in meta or meta["exp_sec"] is None:
            meta["exp_sec"] = 180
            meta["exposure"] = "180s"

    return meta

# Fenêtre principale de l'application de prétraitement par lots OSC pour Siril
class MultiBatchPreProcessingApp(QMainWindow):
    header_msg = (
        f"\n################################################\n"
        f"# Advanced OSC Batch Pre-Processing GUI v{VERSION} #\n"
        "################################################"
    )
    try: s.log(header_msg)
    except Exception: print(header_msg)

    # Initialisation de l'état des fichiers, masters et de l'interface
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Advanced OSC Batch Pre-Processing GUI v{VERSION}")
        self.setGeometry(100, 30, 1220, 800)
        
        self.files = {
            "Lights": [],
            "Darks": [],
            "Flats": [],
            "Biases": [],
            "Dark-Flats": [],
            "Bias-Flats": []
        }
        
        self.masters = {
            "Darks": "",
            "Flats": "",
            "Biases": "",
            "Dark-Flats": "",
            "Bias-Flats": ""
        }
        
        self.use_master = {
            "Darks": False,
            "Flats": False,
            "Biases": False,
            "Dark-Flats": False,
            "Bias-Flats": False
        }

        self.file_count_labels = {}
        self._progress_dialog = None
        self.init_ui()

    # Construction de la structure principale à onglets
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.init_calibration_tab("Biases")
        self.init_calibration_tab("Darks")
        self.init_flats_tab()
        self.init_lights_tab()
        main_layout.addWidget(self.tabs)

    # Création d'un tableau initialisé avec une colonne "File name"
    def create_single_column_table(self):
        table = QTableWidget(0, 1)
        table.setHorizontalHeaderLabels(["File name"])
        table.horizontalHeader().setStretchLastSection(True)
        return table

    # Actualisation des colonnes et lignes d'un tableau selon la catégorie et la présence de fichiers RAW
    def refresh_table(self, category):
        table = getattr(self, f"table_{category.lower()}", None)
        if not table:
            if category == "Dark-Flats":
                table = self.table_dark_flats
            elif category == "Bias-Flats":
                table = self.table_bias_flats
            else:
                return

        file_list = self.files[category]
        has_raw = any(os.path.splitext(f)[1].lower() in ['.cr2', '.nef', '.arw', '.dng'] for f in file_list)

        if category in ["Biases", "Flats", "Bias-Flats"]:
            if has_raw:
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(["File name", "ISO"])
            else:
                table.setColumnCount(1)
                table.setHorizontalHeaderLabels(["File name"])
        elif category in ["Darks", "Dark-Flats", "Lights"]:
            if has_raw:
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["File name", "ISO", "Exposure"])
            else:
                table.setColumnCount(1)
                table.setHorizontalHeaderLabels(["File name"])
        else:
            table.setColumnCount(1)
            table.setHorizontalHeaderLabels(["File name"])

        table.setRowCount(0)
        for f in file_list:
            row_pos = table.rowCount()
            table.insertRow(row_pos)
            
            item_name = QTableWidgetItem(os.path.basename(f))
            item_name.setToolTip(f)
            table.setItem(row_pos, 0, item_name)

            if has_raw:
                meta = inspect_fits_metadata(f)
                if category in ["Biases", "Flats", "Bias-Flats"]:
                    gain_str = meta.get("gain", "")
                    iso_val = gain_str.replace("ISO", "").strip() if gain_str else "-"
                    item_iso = QTableWidgetItem(iso_val)
                    item_iso.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(row_pos, 1, item_iso)
                elif category in ["Darks", "Dark-Flats", "Lights"]:
                    gain_str = meta.get("gain", "")
                    iso_val = gain_str.replace("ISO", "").strip() if gain_str else "-"
                    item_iso = QTableWidgetItem(iso_val)
                    item_iso.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(row_pos, 1, item_iso)

                    exp_sec = meta.get("exp_sec", 0)
                    exp_val = f"{exp_sec:g}s" if exp_sec else "-"
                    item_exp = QTableWidgetItem(exp_val)
                    item_exp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(row_pos, 2, item_exp)

    # Mise à jour du compteur de fichiers affiché à côté des boutons d'une catégorie
    def update_file_count(self, category):
        if category in self.file_count_labels:
            count = len(self.files[category])
            self.file_count_labels[category].setText(f"({count} file{'s' if count > 1 else ''})")

    # Construction de l'onglet Lights (liste, registration/rescaling/drizzle, stacking, chronologie, métadonnées, aperçu)
    def init_lights_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(10, 15, 10, 10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.table_lights = self.create_single_column_table()
        self.table_lights.itemSelectionChanged.connect(self.on_light_selection_changed)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Lights...")
        btn_add.clicked.connect(lambda: self.add_files("Lights", self.table_lights))
        btn_clear = QPushButton("Clear list")
        btn_clear.clicked.connect(lambda: self.clear_files("Lights", self.table_lights))
        
        lbl_count = QLabel("(0 files)")
        self.file_count_labels["Lights"] = lbl_count

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(lbl_count)
        btn_layout.addStretch()

        left_layout.addLayout(btn_layout)
        left_layout.addWidget(self.table_lights)
        splitter.addWidget(left_container)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        group_drizzle = QGroupBox("Registration")
        reg_main_layout = QVBoxLayout(group_drizzle)
        reg_main_layout.setSpacing(6)

        reg_top_row = QHBoxLayout()
        reg_top_row.setSpacing(4)

        reg_top_row.addWidget(QLabel("Layer color reference")) # Ici j'hésite avec "Bayer matrix color reference" qui est peut-être plus proche de la réalité
        self.combo_layer_ref = QComboBox()
        self.combo_layer_ref.addItems(["Red", "Green", "Blue"])
        self.combo_layer_ref.setCurrentText("Red")
        reg_top_row.addWidget(self.combo_layer_ref)

        reg_top_row.addSpacing(15)

        reg_top_row.addWidget(QLabel("Auto-crop"))
        self.combo_autocrop = QComboBox()
        self.combo_autocrop.addItems(["None", "Inside", "Outside", "Center of gravity"])
        self.combo_autocrop.setCurrentText("None")
        reg_top_row.addWidget(self.combo_autocrop)

        reg_top_row.addSpacing(15)

        reg_top_row.addWidget(QLabel("Rescaling"))
        self.spin_rescaling = QDoubleSpinBox()
        self.spin_rescaling.setRange(0.1, 3.0)
        self.spin_rescaling.setValue(1.00)
        self.spin_rescaling.setSingleStep(0.1)
        reg_top_row.addWidget(self.spin_rescaling)

        reg_top_row.addStretch()
        reg_main_layout.addLayout(reg_top_row)

        drizzle_layout = QHBoxLayout()
        drizzle_layout.setSpacing(4)

        self.chk_enable_drizzle = QCheckBox("Enable drizzle")
        drizzle_layout.addWidget(self.chk_enable_drizzle)

        drizzle_layout.addSpacing(15)

        self.lbl_scaling = QLabel("Scaling")
        self.spin_drizzle_scale = QDoubleSpinBox()
        self.spin_drizzle_scale.setRange(1.0, 3.0)
        self.spin_drizzle_scale.setValue(1.00)
        self.spin_drizzle_scale.setSingleStep(0.1)
        self.spin_drizzle_scale.setEnabled(False)
        drizzle_layout.addWidget(self.lbl_scaling)
        drizzle_layout.addWidget(self.spin_drizzle_scale)

        drizzle_layout.addSpacing(15)

        self.lbl_pixel_frac = QLabel("Pixel fraction")
        self.spin_pixel_frac = QDoubleSpinBox()
        self.spin_pixel_frac.setRange(0.1, 1.0)
        self.spin_pixel_frac.setValue(1.00)
        self.spin_pixel_frac.setSingleStep(0.1)
        self.spin_pixel_frac.setEnabled(False)
        drizzle_layout.addWidget(self.lbl_pixel_frac)
        drizzle_layout.addWidget(self.spin_pixel_frac)

        drizzle_layout.addSpacing(15)

        self.lbl_kernel = QLabel("Kernel")
        self.combo_kernel = QComboBox()
        self.combo_kernel.addItems(["point", "turbo", "square", "gaussian", "lanczos2", "lanczos3"])
        idx_square = self.combo_kernel.findText("gaussian")
        if idx_square >= 0:
            self.combo_kernel.setCurrentIndex(idx_square)
        self.combo_kernel.setEnabled(False)
        drizzle_layout.addWidget(self.lbl_kernel)
        drizzle_layout.addWidget(self.combo_kernel)

        drizzle_layout.addStretch()
        reg_main_layout.addLayout(drizzle_layout)

        self.lbl_scaling.setEnabled(False)
        self.lbl_pixel_frac.setEnabled(False)
        self.lbl_kernel.setEnabled(False)

        # Activation ou désactivation des contrôles associés au Drizzle
        def toggle_drizzle_widgets(checked):
            self.spin_drizzle_scale.setEnabled(checked)
            self.spin_pixel_frac.setEnabled(checked)
            self.combo_kernel.setEnabled(checked)
            self.lbl_scaling.setEnabled(checked)
            self.lbl_pixel_frac.setEnabled(checked)
            self.lbl_kernel.setEnabled(checked)

        self.chk_enable_drizzle.toggled.connect(toggle_drizzle_widgets)

        group_stacking = QGroupBox("Stacking")
        stacking_layout = QVBoxLayout(group_stacking)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)
        
        row1_layout.addWidget(QLabel("Method"))
        self.combo_stack_method = QComboBox()
        self.combo_stack_method.addItems([
            "Rejection (sigma)",
            "Average",
            "Median",
            "Minimum",
            "Maximum",
            "Additive with scaling",
            "Winsorized sigma clipping",
            "Linear fit clipping"
        ])
        idx_winsorized = self.combo_stack_method.findText("Winsorized sigma clipping")
        if idx_winsorized >= 0:
            self.combo_stack_method.setCurrentIndex(idx_winsorized)
        row1_layout.addWidget(self.combo_stack_method)

        row1_layout.addSpacing(15)

        row1_layout.addWidget(QLabel("Sigma low"))
        self.spin_sigma_low = QDoubleSpinBox()
        self.spin_sigma_low.setRange(1.0, 10.0)
        self.spin_sigma_low.setValue(3.00)
        row1_layout.addWidget(self.spin_sigma_low)

        row1_layout.addSpacing(15)

        row1_layout.addWidget(QLabel("Sigma high"))
        self.spin_sigma_high = QDoubleSpinBox()
        self.spin_sigma_high.setRange(1.0, 10.0)
        self.spin_sigma_high.setValue(3.00)
        row1_layout.addWidget(self.spin_sigma_high)

        row1_layout.addSpacing(15)

        self.chk_cfa_calibration = QCheckBox("CFA")
        self.chk_cfa_calibration.setChecked(True)
        row1_layout.addWidget(self.chk_cfa_calibration)

        row1_layout.addStretch()
        stacking_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)

        row2_layout.addWidget(QLabel("Dark optimization"))
        self.combo_dark_opt = QComboBox()
        self.combo_dark_opt.addItems([
            "Disabled",
            "Automatic",
            "Forced"
        ])
        row2_layout.addWidget(self.combo_dark_opt)

        row2_layout.addSpacing(15)

        self.chk_enable_cosmetic = QCheckBox("Cosmetic correction")
        self.chk_enable_cosmetic.setChecked(True)
        row2_layout.addWidget(self.chk_enable_cosmetic)

        row2_layout.addSpacing(4)

        row2_layout.addWidget(QLabel("Sigma hot"))
        self.spin_cosmetic_hot = QDoubleSpinBox()
        self.spin_cosmetic_hot.setRange(1.0, 10.0)
        self.spin_cosmetic_hot.setValue(3.00)
        self.spin_cosmetic_hot.setEnabled(True)
        row2_layout.addWidget(self.spin_cosmetic_hot)

        row2_layout.addSpacing(8)

        row2_layout.addWidget(QLabel("Sigma cold"))
        self.spin_cosmetic_cold = QDoubleSpinBox()
        self.spin_cosmetic_cold.setRange(1.0, 10.0)
        self.spin_cosmetic_cold.setValue(3.00)
        self.spin_cosmetic_cold.setEnabled(True)
        row2_layout.addWidget(self.spin_cosmetic_cold)

        row2_layout.addStretch()
        stacking_layout.addLayout(row2_layout)

        # Activation ou désactivation des seuils sigma de correction cosmétique
        def toggle_cosmetic_widgets(checked):
            self.spin_cosmetic_hot.setEnabled(checked)
            self.spin_cosmetic_cold.setEnabled(checked)

        self.chk_enable_cosmetic.toggled.connect(toggle_cosmetic_widgets)

        right_layout.addWidget(group_drizzle)
        right_layout.addWidget(group_stacking)

        self.timeline_widget = ImagingTimelineWidget()
        right_layout.addWidget(self.timeline_widget)

        meta_and_preview_layout = QHBoxLayout()
        meta_and_preview_layout.setSpacing(10)

        left_bottom_layout = QVBoxLayout()
        left_bottom_layout.setContentsMargins(0, 0, 0, 0)
        left_bottom_layout.setSpacing(6)

        group_meta = QGroupBox("Imaging informations")
        meta_layout = QVBoxLayout(group_meta)
        meta_layout.setContentsMargins(8, 4, 8, 4)
        meta_layout.setSpacing(1)

        self.lbl_meta_scope = QLabel()
        self.lbl_meta_focal = QLabel()
        self.lbl_meta_camera = QLabel()
        self.lbl_meta_res = QLabel()
        self.lbl_meta_gain = QLabel()
        self.lbl_meta_focuser = QLabel()

        for lbl in [self.lbl_meta_scope, self.lbl_meta_focal, self.lbl_meta_camera, self.lbl_meta_res, self.lbl_meta_gain, self.lbl_meta_focuser]:
            meta_layout.addWidget(lbl)

        left_bottom_layout.addWidget(group_meta)

        # Case à cocher alignée à droite juste sous "Imaging informations"
        clear_inter_layout = QHBoxLayout()
        clear_inter_layout.addStretch()
        self.chk_clear_intermediate = QCheckBox("Clear intermediate files after processing")
        self.chk_clear_intermediate.setChecked(True)
        clear_inter_layout.addWidget(self.chk_clear_intermediate)
        left_bottom_layout.addLayout(clear_inter_layout)

        run_buttons_layout = QHBoxLayout()
        run_buttons_layout.addStretch()

        btn_reset_all = QPushButton("Reset all")
        btn_reset_all.setStyleSheet("padding: 10px 16px; font-weight: bold;")
        btn_reset_all.clicked.connect(self.reset_all_parameters)
        run_buttons_layout.addWidget(btn_reset_all)

        self.btn_run = QPushButton("Run Pre-Processing")
        self.btn_run.setObjectName("RunButton")
        self.btn_run.clicked.connect(self.run_preprocessing)
        run_buttons_layout.addWidget(self.btn_run)

        left_bottom_layout.addLayout(run_buttons_layout)
        meta_and_preview_layout.addLayout(left_bottom_layout, 1)

        self.group_light_preview = LightPreviewGroupBox("Light preview", self)
        self.group_light_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        light_preview_layout = QVBoxLayout(self.group_light_preview)
        light_preview_layout.setContentsMargins(4, 4, 4, 4)

        light_slider_layout = QHBoxLayout()
        self.lbl_light_stretch_val = QLabel("Stretch : 1%")
        self.lbl_light_stretch_val.setMinimumWidth(80)
        self.slider_light_stretch = QSlider(Qt.Orientation.Horizontal)
        self.slider_light_stretch.setRange(1, 25)
        self.slider_light_stretch.setValue(1)
        self.slider_light_stretch.setTickInterval(5)
        self.slider_light_stretch.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_light_stretch.valueChanged.connect(self.on_light_stretch_slider_changed)

        light_slider_layout.addWidget(self.lbl_light_stretch_val)
        light_slider_layout.addWidget(self.slider_light_stretch)
        light_preview_layout.addLayout(light_slider_layout)

        self.lbl_light_preview = QLabel("No light image to preview")
        self.lbl_light_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_light_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_light_preview.setScaledContents(True)
        self.lbl_light_preview.setStyleSheet("background-color: #1a1a1a; color: #777777; border: 1px dashed #444444;")
        light_preview_layout.addWidget(self.lbl_light_preview, 0)

        meta_and_preview_layout.addWidget(self.group_light_preview, 1)
        right_layout.addLayout(meta_and_preview_layout, 1)

        self.update_lights_metadata_display()
        self.update_light_preview()

        splitter.addWidget(right_container)
        splitter.setSizes([450, 730])

        main_layout.addWidget(splitter)
        self.tabs.addTab(widget, "Lights")

    # Réinitialisation complète des listes de fichiers, masters, paramètres et aperçus
    def reset_all_parameters(self):
        for cat in self.files:
            self.files[cat].clear()
            self.update_file_count(cat)

        self.refresh_table("Biases")
        self.refresh_table("Darks")
        self.refresh_table("Flats")
        self.refresh_table("Dark-Flats")
        self.refresh_table("Bias-Flats")
        self.refresh_table("Lights")

        for cat in self.masters:
            self.masters[cat] = ""
            self.use_master[cat] = False

        if hasattr(self, 'master_input_biases'): self.master_input_biases.clear()
        if hasattr(self, 'master_input_darks'): self.master_input_darks.clear()
        if hasattr(self, 'master_input_flats'): self.master_input_flats.clear()
        if hasattr(self, 'master_input_dark_flats'): self.master_input_dark_flats.clear()
        if hasattr(self, 'master_input_bias_flats'): self.master_input_bias_flats.clear()

        if hasattr(self, 'combo_layer_ref'): self.combo_layer_ref.setCurrentText("Red")
        if hasattr(self, 'combo_autocrop'): self.combo_autocrop.setCurrentText("None")
        if hasattr(self, 'spin_rescaling'): self.spin_rescaling.setValue(1.00)
        if hasattr(self, 'chk_enable_drizzle'): self.chk_enable_drizzle.setChecked(False)
        if hasattr(self, 'spin_drizzle_scale'): self.spin_drizzle_scale.setValue(1.00)
        if hasattr(self, 'spin_pixel_frac'): self.spin_pixel_frac.setValue(1.00)
        if hasattr(self, 'combo_kernel'): 
            idx_square = self.combo_kernel.findText("square")
            if idx_square >= 0: self.combo_kernel.setCurrentIndex(idx_square)

        if hasattr(self, 'combo_stack_method'):
            idx = self.combo_stack_method.findText("Winsorized sigma clipping")
            if idx >= 0: self.combo_stack_method.setCurrentIndex(idx)
        if hasattr(self, 'spin_sigma_low'): self.spin_sigma_low.setValue(3.00)
        if hasattr(self, 'spin_sigma_high'): self.spin_sigma_high.setValue(3.00)
        if hasattr(self, 'chk_cfa_calibration'): self.chk_cfa_calibration.setChecked(True)

        if hasattr(self, 'chk_enable_cosmetic'): 
            self.chk_enable_cosmetic.setChecked(True)
        if hasattr(self, 'spin_cosmetic_hot'): self.spin_cosmetic_hot.setValue(3.00)
        if hasattr(self, 'spin_cosmetic_cold'): self.spin_cosmetic_cold.setValue(3.00)
        if hasattr(self, 'combo_dark_opt'): self.combo_dark_opt.setCurrentIndex(0)

        if hasattr(self, 'chk_clear_intermediate'):
            self.chk_clear_intermediate.setChecked(True)

        if hasattr(self, 'slider_light_stretch'): self.slider_light_stretch.setValue(5)
        if hasattr(self, 'slider_stretch'): self.slider_stretch.setValue(1)

        self.timeline_widget.set_data([])
        self.update_lights_metadata_display()
        self.update_light_preview()
        self.update_flat_preview()
        for cat in ["Biases", "Darks"]:
            self.update_calibration_preview(cat, update_hist=True)

    # Mise à jour de l'étiquette d'étirement et de l'aperçu des Lights
    def on_light_stretch_slider_changed(self, val):
        self.lbl_light_stretch_val.setText(f"Stretch : {val}%")
        self.update_light_preview()

    # Rafraîchissement de l'aperçu Light lors d'un changement de sélection dans le tableau
    def on_light_selection_changed(self):
        self.update_light_preview()

    # Rendu de l'aperçu de l'image Light sélectionnée ou de la première image disponible
    def update_light_preview(self):
        target_path = ""
        stretch_val = float(self.slider_light_stretch.value())

        selected_items = self.table_lights.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            if row < len(self.files["Lights"]):
                target_path = self.files["Lights"][row]
        elif self.files["Lights"]:
            target_path = self.files["Lights"][0]

        container_h = self.group_light_preview.height() - 40 if self.group_light_preview.height() > 50 else 180
        container_w = self.group_light_preview.width() - 15 if self.group_light_preview.width() > 50 else 300

        calc_w = int(container_h * 1.5)
        if calc_w <= container_w:
            target_h = container_h
            target_w = calc_w
        else:
            target_w = container_w
            target_h = int(container_w / 1.5)

        target_w = max(50, target_w)
        target_h = max(33, target_h)

        if target_path:
            pixmap, dyn_w, dyn_h = load_lights_preview_pixmap(target_path, target_width=target_w, target_height=target_h, stretch_val=stretch_val)
            if pixmap:
                self.lbl_light_preview.setFixedSize(dyn_w, dyn_h)
                self.lbl_light_preview.setPixmap(pixmap)
                self.lbl_light_preview.setText("")
            else:
                self.lbl_light_preview.clear()
                self.lbl_light_preview.setText("Failed to load light preview")
        else:
            self.lbl_light_preview.clear()
            self.lbl_light_preview.setText("No light image to preview")

    # Synthèse et affichage des informations optiques, caméra et acquisition des Lights
    def update_lights_metadata_display(self):
        if not self.files["Lights"]:
            self.lbl_meta_scope.setText("<span style='color:#888888; font-size:10.5pt;'>Scope :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
            self.lbl_meta_focal.setText("<span style='color:#888888; font-size:10.5pt;'>Focal :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
            self.lbl_meta_camera.setText("<span style='color:#888888; font-size:10.5pt;'>Camera :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
            self.lbl_meta_res.setText("<span style='color:#888888; font-size:10.5pt;'>Resolution :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
            self.lbl_meta_gain.setText("<span style='color:#888888; font-size:10.5pt;'>Gain :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
            self.lbl_meta_focuser.setText("<span style='color:#888888; font-size:10.5pt;'>Focuser :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
            return

        all_meta = [inspect_fits_metadata(f) for f in self.files["Lights"]]
        is_raw = os.path.splitext(self.files["Lights"][0])[1].lower() in ['.cr2', '.nef', '.arw', '.dng']

        scopes = []
        focales_ratios = []
        cameras = []
        resolutions = []
        binnings = []
        gains = []
        temps = []
        foc_names = []

        for m in all_meta:
            if m.get("scope_name") and m["scope_name"] not in scopes:
                scopes.append(m["scope_name"])
            
            f_str = ""
            if m.get("focal_len"):
                f_str += m["focal_len"]
            if m.get("f_ratio"):
                f_str += f" {m['f_ratio']}" if f_str else m["f_ratio"]
            if f_str and f_str not in focales_ratios:
                focales_ratios.append(f_str)

            if m.get("camera_name") and m["camera_name"] not in cameras:
                cameras.append(m["camera_name"])

            if m.get("resolution") and m["resolution"] not in resolutions:
                resolutions.append(m["resolution"])

            if m.get("binning") and m["binning"] not in binnings:
                binnings.append(m["binning"])

            if m.get("gain") and m["gain"] not in gains:
                gains.append(m["gain"])

            if m.get("raw_temp_val") is not None and m["raw_temp_val"] not in temps:
                temps.append(m["raw_temp_val"])

            if m.get("focuser_name") and m["focuser_name"] not in foc_names:
                foc_names.append(m["focuser_name"])

        if scopes:
            scope_str = ", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{s}</span>" for s in scopes])
            self.lbl_meta_scope.setText(f"<span style='color:#888888; font-size:10.5pt;'>Scope :</span> {scope_str}")
        else:
            self.lbl_meta_scope.setText("<span style='color:#888888; font-size:10.5pt;'>Scope :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")

        if focales_ratios:
            foc_str = ", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{fr}</span>" for fr in focales_ratios])
            self.lbl_meta_focal.setText(f"<span style='color:#888888; font-size:10.5pt;'>Focal :</span> {foc_str}")
        else:
            self.lbl_meta_focal.setText("<span style='color:#888888; font-size:10.5pt;'>Focal :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")

        if cameras:
            cam_str = ", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{c}</span>" for c in cameras])
            self.lbl_meta_camera.setText(f"<span style='color:#888888; font-size:10.5pt;'>Camera :</span> {cam_str}")
        else:
            self.lbl_meta_camera.setText("<span style='color:#888888; font-size:10.5pt;'>Camera :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")

        if resolutions or binnings:
            res_full = []
            if resolutions:
                res_full.append(", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{r}</span>" for r in resolutions]))
            if binnings:
                res_full.append(f"<span style='color:#888888; font-size:10.5pt;'>Bin :</span> " + ", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{b}</span>" for b in binnings]))
            self.lbl_meta_res.setText(f"<span style='color:#888888; font-size:10.5pt;'>Resolution :</span> " + " ".join(res_full))
        else:
            self.lbl_meta_res.setText("<span style='color:#888888; font-size:10.5pt;'>Resolution :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")

        gain_str = ", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{g}</span>" for g in gains]) if gains else ""
        temp_str = ""
        if not is_raw:
            if temps:
                min_t, max_t = min(temps), max(temps)
                if min_t == max_t:
                    temp_str = f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{min_t:.1f}°C</span>"
                else:
                    temp_str = f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>temp. min/max {min_t:.0f}/{max_t:.0f}°C</span>"
            elif all_meta[0].get("sensor_temp"):
                temp_str = f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{all_meta[0]['sensor_temp']}</span>"

        if gain_str or temp_str:
            full_gain_text = f"<span style='color:#888888; font-size:10.5pt;'>Gain :</span> " + gain_str
            if temp_str:
                full_gain_text += f" <span style='color:#888888; font-size:10.5pt;'>Temp :</span> " + temp_str
            self.lbl_meta_gain.setText(full_gain_text)
        else:
            self.lbl_meta_gain.setText("<span style='color:#888888; font-size:10.5pt;'>Gain :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")

        if not is_raw:
            if foc_names:
                foc_str = ", ".join([f"<span style='color:#888888; font-weight:bold; font-size:10.5pt;'>{fn}</span>" for fn in foc_names])
                self.lbl_meta_focuser.setText(f"<span style='color:#888888; font-size:10.5pt;'>Focuser :</span> {foc_str}")
                self.lbl_meta_focuser.setVisible(True)
            else:
                self.lbl_meta_focuser.setText("<span style='color:#888888; font-size:10.5pt;'>Focuser :</span> <span style='color:#888888; font-size:10.5pt;'>unknown</span>")
                self.lbl_meta_focuser.setVisible(True)
        else:
            self.lbl_meta_focuser.setVisible(False)

    # Construction générique d'un onglet de calibration (Biases ou Darks)
    def init_calibration_tab(self, category):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(10, 15, 10, 10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        table = self.create_single_column_table()
        table.itemSelectionChanged.connect(partial(self.on_calibration_selection_changed, category))
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton(f"Add {category}...")
        btn_add.clicked.connect(lambda: self.add_files(category, table))
        btn_clear = QPushButton("Clear list")
        btn_clear.clicked.connect(lambda: self.clear_files(category, table))
        
        lbl_count = QLabel("(0 files)")
        self.file_count_labels[category] = lbl_count

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(lbl_count)
        btn_layout.addStretch()
        
        left_layout.addLayout(btn_layout)
        left_layout.addWidget(table)

        master_layout = QHBoxLayout()
        master_input = QLineEdit()
        sing_cat = "bias" if category == "Biases" else category[:-1].lower()
        master_input.setPlaceholderText(f"Or master {sing_cat} file...")
        master_input.setReadOnly(True)
        btn_browse_master = QPushButton("Browse...")
        btn_browse_master.clicked.connect(lambda: self.select_master_file(category, master_input))
        master_layout.addWidget(master_input)
        master_layout.addWidget(btn_browse_master)
        left_layout.addLayout(master_layout)

        splitter.addWidget(left_container)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        group_opts = QGroupBox("Stacking")
        opts_layout = QVBoxLayout(group_opts)

        stack_row = QHBoxLayout()
        stack_row.setSpacing(4)
        stack_row.addWidget(QLabel("Method"))
        
        stack_method_combo = QComboBox()
        stack_method_combo.addItems([
            "Rejection (sigma)",
            "Average",
            "Median",
            "Minimum",
            "Maximum",
            "Additive with scaling",
            "Winsorized sigma clipping",
            "Linear fit clipping"
        ])
        idx_winsorized = stack_method_combo.findText("Winsorized sigma clipping")
        if idx_winsorized >= 0:
            stack_method_combo.setCurrentIndex(idx_winsorized)
        stack_row.addWidget(stack_method_combo)

        stack_row.addSpacing(15)
        stack_row.addWidget(QLabel("Sigma low"))
        spin_sigma_low = QDoubleSpinBox()
        spin_sigma_low.setRange(1.0, 10.0)
        spin_sigma_low.setValue(3.00)
        stack_row.addWidget(spin_sigma_low)

        stack_row.addSpacing(15)
        stack_row.addWidget(QLabel("Sigma high"))
        spin_sigma_high = QDoubleSpinBox()
        spin_sigma_high.setRange(1.0, 10.0)
        spin_sigma_high.setValue(3.00)
        stack_row.addWidget(spin_sigma_high)
        stack_row.addStretch()

        opts_layout.addLayout(stack_row)

        if category == "Darks":
            self.chk_calibrate_dark = QCheckBox("Calibrate darks with a master bias")
            self.chk_calibrate_dark.setChecked(False)
            opts_layout.addSpacing(5)
            opts_layout.addWidget(self.chk_calibrate_dark)

        opts_layout.addStretch()
        right_layout.addWidget(group_opts)

        group_preview = CalibrationPreviewGroupBox(f"{sing_cat.capitalize()} preview", self, category)
        preview_layout = QVBoxLayout(group_preview)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        lbl_preview = QLabel("No image to preview")
        lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_preview.setMinimumHeight(150)
        lbl_preview.setStyleSheet("background-color: #1a1a1a; color: #777777; border: 1px dashed #444444;")
        preview_layout.addWidget(lbl_preview)

        hist_widget = HistogramStretchWidget()
        preview_layout.addWidget(hist_widget)

        right_layout.addWidget(group_preview)

        btn_gen_master = QPushButton(f"Generate Master {sing_cat.capitalize()}")
        btn_gen_master.clicked.connect(partial(self.generate_standalone_master, category))
        right_layout.addWidget(btn_gen_master)

        splitter.addWidget(right_container)
        splitter.setSizes([450, 730])

        main_layout.addWidget(splitter)
        
        setattr(self, f"table_{category.lower()}", table)
        setattr(self, f"master_input_{category.lower()}", master_input)
        setattr(self, f"combo_stack_{category.lower()}", stack_method_combo)
        setattr(self, f"spin_sigma_low_{category.lower()}", spin_sigma_low)
        setattr(self, f"spin_sigma_high_{category.lower()}", spin_sigma_high)
        setattr(self, f"group_preview_{category.lower()}", group_preview)
        setattr(self, f"lbl_preview_{category.lower()}", lbl_preview)
        setattr(self, f"hist_widget_{category.lower()}", hist_widget)
        
        self.tabs.addTab(widget, category)
        self.update_calibration_preview(category)

    # Construction de l'onglet Flats (Flats, Dark-Flats, Bias-Flats, options d'empilement et aperçu)
    def init_flats_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(10, 15, 10, 10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.table_flats = self.create_single_column_table()
        self.table_flats.itemSelectionChanged.connect(self.on_flat_selection_changed)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Flats...")
        btn_add.clicked.connect(lambda: self.add_files("Flats", self.table_flats))
        btn_clear = QPushButton("Clear list")
        btn_clear.clicked.connect(lambda: self.clear_files("Flats", self.table_flats))
        
        lbl_count = QLabel("(0 files)")
        self.file_count_labels["Flats"] = lbl_count

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(lbl_count)
        btn_layout.addStretch()

        left_layout.addLayout(btn_layout)
        left_layout.addWidget(self.table_flats)

        flat_master_layout = QHBoxLayout()
        self.master_input_flats = QLineEdit()
        self.master_input_flats.setPlaceholderText("Or master flat file...")
        self.master_input_flats.setReadOnly(True)
        btn_browse_flat_master = QPushButton("Browse...")
        btn_browse_flat_master.clicked.connect(lambda: self.select_master_file("Flats", self.master_input_flats))
        flat_master_layout.addWidget(self.master_input_flats)
        flat_master_layout.addWidget(btn_browse_flat_master)
        left_layout.addLayout(flat_master_layout)

        splitter.addWidget(left_container)

        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(5, 0, 0, 0)

        right_splitter = QSplitter(Qt.Orientation.Horizontal)

        calib_lists_container = QWidget()
        calib_lists_container.setMinimumWidth(280)
        calib_lists_layout = QVBoxLayout(calib_lists_container)
        calib_lists_layout.setContentsMargins(0, 0, 0, 0)

        self.table_dark_flats = self.create_single_column_table()
        df_btn_layout = QHBoxLayout()
        df_add = QPushButton("Add Dark-Flats...")
        df_add.clicked.connect(lambda: self.add_files("Dark-Flats", self.table_dark_flats))
        df_clear = QPushButton("Clear")
        df_clear.clicked.connect(lambda: self.clear_files("Dark-Flats", self.table_dark_flats))
        df_count = QLabel("(0)")
        self.file_count_labels["Dark-Flats"] = df_count
        df_btn_layout.addWidget(df_add)
        df_btn_layout.addWidget(df_clear)
        df_btn_layout.addWidget(df_count)
        df_btn_layout.addStretch()
        calib_lists_layout.addLayout(df_btn_layout)
        calib_lists_layout.addWidget(self.table_dark_flats)

        df_master_layout = QHBoxLayout()
        self.master_input_dark_flats = QLineEdit()
        self.master_input_dark_flats.setPlaceholderText("Or master dark-flat file...")
        self.master_input_dark_flats.setReadOnly(True)
        btn_browse_df_master = QPushButton("Browse...")
        btn_browse_df_master.clicked.connect(lambda: self.select_master_file("Dark-Flats", self.master_input_dark_flats))
        df_master_layout.addWidget(self.master_input_dark_flats)
        df_master_layout.addWidget(btn_browse_df_master)
        calib_lists_layout.addLayout(df_master_layout)

        calib_lists_layout.addSpacing(10)

        self.table_bias_flats = self.create_single_column_table()
        bf_btn_layout = QHBoxLayout()
        bf_add = QPushButton("Add Bias-Flats...")
        bf_add.clicked.connect(lambda: self.add_files("Bias-Flats", self.table_bias_flats))
        bf_clear = QPushButton("Clear")
        bf_clear.clicked.connect(lambda: self.clear_files("Bias-Flats", self.table_bias_flats))
        bf_count = QLabel("(0)")
        self.file_count_labels["Bias-Flats"] = bf_count
        bf_btn_layout.addWidget(bf_add)
        bf_btn_layout.addWidget(bf_clear)
        bf_btn_layout.addWidget(bf_count)
        bf_btn_layout.addStretch()
        calib_lists_layout.addLayout(bf_btn_layout)
        calib_lists_layout.addWidget(self.table_bias_flats)

        bf_master_layout = QHBoxLayout()
        self.master_input_bias_flats = QLineEdit()
        self.master_input_bias_flats.setPlaceholderText("Or master bias-flat file...")
        self.master_input_bias_flats.setReadOnly(True)
        btn_browse_bf_master = QPushButton("Browse...")
        btn_browse_bf_master.clicked.connect(lambda: self.select_master_file("Bias-Flats", self.master_input_bias_flats))
        bf_master_layout.addWidget(self.master_input_bias_flats)
        bf_master_layout.addWidget(btn_browse_bf_master)
        calib_lists_layout.addLayout(bf_master_layout)

        right_splitter.addWidget(calib_lists_container)

        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        options_layout.setContentsMargins(5, 0, 0, 0)
        options_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        group_opts = QGroupBox("Stacking")
        opts_inner = QVBoxLayout(group_opts)
        
        flat_stack_row = QHBoxLayout()
        flat_stack_row.setSpacing(4)
        flat_stack_row.addWidget(QLabel("Method"))
        
        self.combo_flat_method = QComboBox()
        self.combo_flat_method.addItems([
            "Rejection (sigma)",
            "Average",
            "Median",
            "Minimum",
            "Maximum",
            "Additive with scaling",
            "Winsorized sigma clipping",
            "Linear fit clipping"
        ])
        idx_winsorized = self.combo_flat_method.findText("Winsorized sigma clipping")
        if idx_winsorized >= 0:
            self.combo_flat_method.setCurrentIndex(idx_winsorized)
        flat_stack_row.addWidget(self.combo_flat_method)

        flat_stack_row.addSpacing(15)
        flat_stack_row.addWidget(QLabel("Sigma low"))
        self.spin_flat_sigma_low = QDoubleSpinBox()
        self.spin_flat_sigma_low.setRange(1.0, 10.0)
        self.spin_flat_sigma_low.setValue(3.00)
        flat_stack_row.addWidget(self.spin_flat_sigma_low)

        flat_stack_row.addSpacing(15)
        flat_stack_row.addWidget(QLabel("Sigma high"))
        self.spin_flat_sigma_high = QDoubleSpinBox()
        self.spin_flat_sigma_high.setRange(1.0, 10.0)
        self.spin_flat_sigma_high.setValue(3.00)
        flat_stack_row.addWidget(self.spin_flat_sigma_high)
        flat_stack_row.addStretch()

        opts_inner.addLayout(flat_stack_row)

        self.chk_normalize_flats = QCheckBox("Normalize master flat")
        self.chk_normalize_flats.setChecked(True)
        opts_inner.addWidget(self.chk_normalize_flats)
        opts_inner.addStretch()

        options_layout.addWidget(group_opts)

        self.group_preview = FlatPreviewGroupBox("Flat preview", self)
        preview_layout = QVBoxLayout(self.group_preview)
        preview_layout.setContentsMargins(4, 4, 4, 4)
        
        slider_layout = QHBoxLayout()
        self.lbl_stretch_val = QLabel("Stretch : 1%")
        self.lbl_stretch_val.setMinimumWidth(85)
        self.slider_stretch = QSlider(Qt.Orientation.Horizontal)
        self.slider_stretch.setRange(1, 25)
        self.slider_stretch.setValue(1)
        self.slider_stretch.setTickInterval(2)
        self.slider_stretch.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_stretch.valueChanged.connect(self.on_stretch_slider_changed)

        slider_layout.addWidget(self.lbl_stretch_val)
        slider_layout.addWidget(self.slider_stretch)
        preview_layout.addLayout(slider_layout)

        self.lbl_flat_preview = QLabel("No flat image to preview")
        self.lbl_flat_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_flat_preview.setMinimumHeight(150)
        self.lbl_flat_preview.setStyleSheet("background-color: #1a1a1a; color: #777777; border: 1px dashed #444444;")
        preview_layout.addWidget(self.lbl_flat_preview)

        options_layout.addWidget(self.group_preview)

        btn_gen_master_flat = QPushButton("Generate Master Flat")
        btn_gen_master_flat.clicked.connect(partial(self.generate_standalone_master, "Flats"))
        options_layout.addWidget(btn_gen_master_flat)

        right_splitter.addWidget(options_container)
        right_splitter.setSizes([410, 400])
        right_layout.addWidget(right_splitter)

        splitter.addWidget(right_container)
        splitter.setSizes([410, 810])

        main_layout.addWidget(splitter)
        self.tabs.addTab(widget, "Flats")
        self.update_flat_preview()

    # Mise à jour de l'étiquette d'étirement et de l'aperçu des Flats
    def on_stretch_slider_changed(self, val):
        self.lbl_stretch_val.setText(f"Stretch : {val}%")
        self.update_flat_preview()

    # Rafraîchissement de l'aperçu Flat lors d'un changement de sélection
    def on_flat_selection_changed(self):
        self.update_flat_preview()

    # Rafraîchissement de l'aperçu et de l'histogramme lors d'un changement de sélection de calibration
    def on_calibration_selection_changed(self, category):
        self.update_calibration_preview(category, update_hist=True)

    # Rendu de l'aperçu d'un Master Flat ou d'une image Flat sélectionnée
    def update_flat_preview(self):
        target_path = ""
        stretch_val = float(self.slider_stretch.value())

        if self.use_master["Flats"] and self.masters["Flats"]:
            target_path = self.masters["Flats"]
        else:
            selected_items = self.table_flats.selectedItems()
            if selected_items:
                row = selected_items[0].row()
                if row < len(self.files["Flats"]):
                    target_path = self.files["Flats"][row]
            elif self.files["Flats"]:
                target_path = self.files["Flats"][0]

        w_avail = self.group_preview.width() - 12 if hasattr(self, 'group_preview') and self.group_preview.width() > 50 else 260
        default_h = int(w_avail * 2 / 3)

        if target_path:
            pixmap, dyn_height = load_fits_preview_pixmap(target_path, target_width=w_avail, stretch_pct=stretch_val)
            if pixmap:
                self.lbl_flat_preview.setFixedSize(w_avail, dyn_height)
                self.lbl_flat_preview.setPixmap(pixmap)
                self.lbl_flat_preview.setText("")
            else:
                self.lbl_flat_preview.setFixedSize(w_avail, default_h)
                self.lbl_flat_preview.clear()
                self.lbl_flat_preview.setText("Failed to load flat preview")
        else:
            self.lbl_flat_preview.setFixedSize(w_avail, default_h)
            self.lbl_flat_preview.clear()
            self.lbl_flat_preview.setText("No flat image to preview")

    # Rendu de l'aperçu et de l'histogramme pour une catégorie de calibration donnée
    def update_calibration_preview(self, category, update_hist=False):
        table = getattr(self, f"table_{category.lower()}")
        group_box = getattr(self, f"group_preview_{category.lower()}")
        lbl_preview = getattr(self, f"lbl_preview_{category.lower()}")
        hist_widget = getattr(self, f"hist_widget_{category.lower()}")

        target_path = ""
        if self.use_master[category] and self.masters[category]:
            target_path = self.masters[category]
        else:
            selected_items = table.selectedItems()
            if selected_items:
                row = selected_items[0].row()
                if row < len(self.files[category]):
                    target_path = self.files[category][row]
            elif self.files[category]:
                target_path = self.files[category][0]

        w_avail = group_box.width() - 12 if group_box.width() > 50 else 260
        hist_widget.setFixedWidth(w_avail)
        default_h = int(w_avail * 2 / 3)

        if target_path:
            pixmap, dyn_height, raw_data = load_calibration_preview_pixmap(target_path, target_width=w_avail)
            if pixmap:
                lbl_preview.setFixedSize(w_avail, dyn_height)
                lbl_preview.setPixmap(pixmap)
                lbl_preview.setText("")
                if update_hist and raw_data is not None:
                    hist_widget.set_data(raw_data)
            else:
                lbl_preview.setFixedSize(w_avail, default_h)
                lbl_preview.clear()
                lbl_preview.setText("Failed to load preview")
                if update_hist:
                    hist_widget.set_data(None)
        else:
            lbl_preview.setFixedSize(w_avail, default_h)
            lbl_preview.clear()
            lbl_preview.setText("No image to preview")
            if update_hist:
                hist_widget.set_data(None)

    # Sélection, analyse des métadonnées et ajout de fichiers à une catégorie
    def add_files(self, category, table):
        files, _ = QFileDialog.getOpenFileNames(
            self, f"Select {category.lower()} images", "", 
            "Astronomical/RAW Files (*.fits *.fit *.fts *.xisf *.cr2 *.nef *.arw *.dng)"
        )
        if files:
            dialog = FileLoadingDialog(self, f"Loading {category.lower()}")
            dialog.show()
            
            total = len(files)
            for i, f in enumerate(files):
                if f not in self.files[category]:
                    fname = os.path.basename(f)
                    dialog.set_status(f"Reading and analyzing ({i+1}/{total}) :\n{fname}", i, total)
                    inspect_fits_metadata(f)
                    self.files[category].append(f)

            dialog.set_status("Updating tables...", total, total)
            self.refresh_table(category)
            self.update_file_count(category)

            if category == "Lights":
                lights_list = self.files["Lights"]
                l_total = len(lights_list)
                parsed_meta = []
                for i, lf in enumerate(lights_list):
                    fname = os.path.basename(lf)
                    dialog.set_status(f"Global metadata analysis ({i+1}/{l_total}) :\n{fname}", i+1, l_total)
                    parsed_meta.append(inspect_fits_metadata(lf))
                
                dialog.set_status("Generating timeline and updating view...", l_total, l_total)
                self.timeline_widget.set_data(parsed_meta)
                self.update_lights_metadata_display()
                self.update_light_preview()
            elif category == "Flats":
                self.update_flat_preview()
            elif category in ["Biases", "Darks"]:
                self.update_calibration_preview(category, update_hist=True)

            dialog.close()

    # Sélection d'un fichier Master existant pour remplacer un lot d'images de calibration
    def select_master_file(self, category, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select master {category.lower()}", "", 
            "Master Files (*.fits *.fit *.fts *.xisf)"
        )
        if file_path:
            line_edit.setText(file_path)
            self.masters[category] = file_path
            self.use_master[category] = True
            if category == "Flats":
                self.update_flat_preview()
            elif category in ["Biases", "Darks"]:
                self.update_calibration_preview(category, update_hist=True)

    # Vidage de la liste de fichiers d'une catégorie et mise à jour de l'interface
    def clear_files(self, category, table):
        self.files[category].clear()
        self.refresh_table(category)
        self.update_file_count(category)
        if category == "Lights":
            self.timeline_widget.set_data([])
            self.update_lights_metadata_display()
            self.update_light_preview()
        elif category == "Flats":
            self.update_flat_preview()
        elif category in ["Biases", "Darks"]:
            self.update_calibration_preview(category, update_hist=True)

    # Génération autonome d'un Master (Bias, Dark ou Flat) via script SSF et exécution Siril
    def generate_standalone_master(self, category):
        if not self.files[category]:
            QMessageBox.warning(self, "Error", f"No files loaded in {category} list to calculate master.")
            return

        base_work_dir = os.getcwd()
        
        if category == "Biases":
            sing_cat = "bias"
            cat_folder = "biases"
        elif category == "Darks":
            sing_cat = "dark"
            cat_folder = "darks"
        elif category == "Flats":
            sing_cat = "flat"
            cat_folder = "flats"
        else:
            return

        target_dir = os.path.join(base_work_dir, cat_folder)
        converted_dir = os.path.join(target_dir, "converted")
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(converted_dir, exist_ok=True)

        for f_path in self.files[category]:
            fname = os.path.basename(f_path)
            dst_path = os.path.join(target_dir, fname)
            if os.path.exists(dst_path):
                try:
                    os.remove(dst_path)
                except Exception:
                    pass
            try:
                os.symlink(f_path, dst_path)
            except OSError:
                shutil.copy2(f_path, dst_path)

        all_meta = [inspect_fits_metadata(f) for f in self.files[category]]
        first_file = self.files[category][0]
        ext = os.path.splitext(first_file)[1].lower()
        is_raw = ext in ['.cr2', '.nef', '.arw', '.dng']

        gain_iso_part = ""
        gain_val = all_meta[0].get("gain")
        if gain_val:
            g_clean = str(gain_val).replace("Gain", "").replace("ISO", "").strip()
            gain_iso_part = f"iso-{g_clean}" if is_raw else f"gain-{g_clean}"

        if category == "Biases":
            filename = f"master-bias_{gain_iso_part}.fit" if gain_iso_part else "master-bias.fit"
        elif category == "Darks":
            exposures = [m["exp_sec"] for m in all_meta if m.get("exp_sec") is not None]
            avg_exp = round(sum(exposures) / len(exposures)) if exposures else 0
            temps = [m["raw_temp_val"] for m in all_meta if m.get("raw_temp_val") is not None]
            avg_temp = round(sum(temps) / len(temps)) if temps else None
            parts = ["master-dark"]
            if gain_iso_part:
                parts.append(gain_iso_part)
            if avg_exp > 0:
                parts.append(f"{avg_exp}s")
            if avg_temp is not None:
                parts.append(f"{avg_temp}deg")
            filename = "_".join(parts) + ".fit"
        elif category == "Flats":
            scope_name = all_meta[0].get("scope_name") if not is_raw else None
            filter_name = all_meta[0].get("filter") if not is_raw else None
            curr_date = datetime.now().strftime("%Y%m%d")
            parts = ["master-flat"]
            if scope_name and scope_name.strip():
                parts.append(re.sub(r'[\s/\\:]+', '-', scope_name.strip()))
            if filter_name and filter_name.strip():
                parts.append(re.sub(r'[\s/\\:]+', '-', filter_name.strip()))
            parts.append(curr_date)
            filename = "_".join(parts) + ".fit"

        script_path = os.path.join(base_work_dir, f"generate_master_{sing_cat}.ssf")

        posix_base = base_work_dir.replace("\\", "/")
        posix_target = target_dir.replace("\\", "/")
        posix_converted = converted_dir.replace("\\", "/")
        master_out_posix = os.path.join(base_work_dir, filename).replace("\\", "/")

        master_bias_flat_posix = ""
        master_dark_flat_posix = ""
        master_bias_for_dark_posix = ""

        if category == "Flats":
            stack_combo = self.combo_flat_method
            s_low = f"{self.spin_flat_sigma_low.value():.2f}"
            s_high = f"{self.spin_flat_sigma_high.value():.2f}"
        else:
            stack_combo = getattr(self, f"combo_stack_{category.lower()}")
            s_low = f"{getattr(self, f'spin_sigma_low_{category.lower()}').value():.2f}"
            s_high = f"{getattr(self, f'spin_sigma_high_{category.lower()}').value():.2f}"

        stack_method_text = stack_combo.currentText().lower()

        # Conversion de la méthode d'empilement sélectionnée en arguments de commande Siril `stack`
        def get_stack_args(method_text, low, high, is_master_calib=False):
            if "median" in method_text:
                res = "median"
            elif "average" in method_text:
                res = "avg"
            elif "minimum" in method_text:
                res = "min"
            elif "maximum" in method_text:
                res = "max"
            elif "linear fit" in method_text:
                res = "linearfit"
            elif "winsorized" in method_text:
                res = f"rej w {low} {high}"
            elif "rejection" in method_text or "sigma" in method_text:
                res = f"rej s {low} {high}"
            else:
                res = f"rej w {low} {high}"
            
            if is_master_calib:
                res += " -nonorm"
            return res

        stack_args_str = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=(category != "Flats"))

        if category == "Darks" and self.chk_calibrate_dark.isChecked():
            if not (self.use_master["Biases"] and self.masters["Biases"]) and not self.files["Biases"]:
                QMessageBox.warning(self, "Warning", "No bias files are loaded in the Biases tab.")
                return

            bias_target = os.path.join(base_work_dir, "biases")
            bias_converted = os.path.join(bias_target, "converted")
            if self.use_master["Biases"] and self.masters["Biases"]:
                master_bias_for_dark_posix = self.masters["Biases"].replace("\\", "/")
            elif self.files["Biases"]:
                os.makedirs(bias_target, exist_ok=True)
                os.makedirs(bias_converted, exist_ok=True)
                for b_path in self.files["Biases"]:
                    b_name = os.path.basename(b_path)
                    b_dst = os.path.join(bias_target, b_name)
                    if os.path.exists(b_dst):
                        try: os.remove(b_dst)
                        except: pass
                    try: os.symlink(b_path, b_dst)
                    except OSError: shutil.copy2(b_path, b_dst)
                
                b_meta = [inspect_fits_metadata(f) for f in self.files["Biases"]]
                b_ext = os.path.splitext(self.files["Biases"][0])[1].lower()
                b_is_raw = b_ext in ['.cr2', '.nef', '.arw', '.dng']
                b_gain_iso_part = ""
                b_gain_val = b_meta[0].get("gain")
                if b_gain_val:
                    g_clean = str(b_gain_val).replace("Gain", "").replace("ISO", "").strip()
                    b_gain_iso_part = f"iso-{g_clean}" if b_is_raw else f"gain-{g_clean}"
                b_filename = f"master-bias_{b_gain_iso_part}.fit" if b_gain_iso_part else "master-bias.fit"

                master_bias_for_dark_posix = os.path.join(base_work_dir, b_filename).replace("\\", "/")
                
                try:
                    siril.cmd("cd", bias_target.replace("\\", "/"))
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "bias", f"-out={bias_converted.replace('\\', '/')}")
                    siril.cmd("cd", bias_converted.replace("\\", "/"))
                    siril.cmd("stack", "bias", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_bias_for_dark_posix}")
                    siril.cmd("cd", posix_base)
                except Exception as e:
                    try: siril.cmd("cd", posix_base)
                    except: pass
                    print(f"Master bias generation for dark notice: {e}")

        if category == "Flats":
            if not (self.use_master["Bias-Flats"] and self.masters["Bias-Flats"]) and not self.files["Bias-Flats"]:
                QMessageBox.warning(self, "Warning", "No bias-flat files or master bias-flat provided in the Bias-Flats section.")
                return

            flat_exposures = [m.get("exp_sec", 0) for m in all_meta if m.get("exp_sec") is not None]
            if flat_exposures and any(exp > 1.0 for exp in flat_exposures):
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("Flat exposure time is greater than 1s. In this case, it is preferable to calibrate flats with a master dark-flat.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
                ret = msg_box.exec()
                if ret == QMessageBox.StandardButton.Cancel:
                    return

            bf_target = os.path.join(target_dir, "bias-flats")
            bf_converted = os.path.join(bf_target, "converted")
            if self.use_master["Bias-Flats"] and self.masters["Bias-Flats"]:
                master_bias_flat_posix = self.masters["Bias-Flats"].replace("\\", "/")
            elif self.files["Bias-Flats"]:
                os.makedirs(bf_target, exist_ok=True)
                os.makedirs(bf_converted, exist_ok=True)
                for bf_path in self.files["Bias-Flats"]:
                    bf_name = os.path.basename(bf_path)
                    bf_dst = os.path.join(bf_target, bf_name)
                    if os.path.exists(bf_dst):
                        try: os.remove(bf_dst)
                        except: pass
                    try: os.symlink(bf_path, bf_dst)
                    except OSError: shutil.copy2(bf_path, bf_dst)
                
                bf_meta = [inspect_fits_metadata(f) for f in self.files["Bias-Flats"]]
                bf_ext = os.path.splitext(self.files["Bias-Flats"][0])[1].lower()
                bf_is_raw = bf_ext in ['.cr2', '.nef', '.arw', '.dng']
                bf_gain_iso_part = ""
                bf_gain_val = bf_meta[0].get("gain")
                if bf_gain_val:
                    g_clean = str(bf_gain_val).replace("Gain", "").replace("ISO", "").strip()
                    bf_gain_iso_part = f"iso-{g_clean}" if bf_is_raw else f"gain-{g_clean}"
                bf_filename = f"master-bias-flat_{bf_gain_iso_part}.fit" if bf_gain_iso_part else "master-bias-flat.fit"
                master_bias_flat_posix = os.path.join(base_work_dir, bf_filename).replace("\\", "/")
                
                try:
                    siril.cmd("cd", bf_target.replace("\\", "/"))
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "bias", f"-out={bf_converted.replace('\\', '/')}")
                    siril.cmd("cd", bf_converted.replace("\\", "/"))
                    siril.cmd("stack", "bias", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_bias_flat_posix}")
                    siril.cmd("cd", posix_base)
                except Exception as e:
                    try: siril.cmd("cd", posix_base)
                    except: pass
                    print(f"Bias-flat generation notice: {e}")

            df_target = os.path.join(target_dir, "dark-flats")
            df_converted = os.path.join(df_target, "converted")
            if self.use_master["Dark-Flats"] and self.masters["Dark-Flats"]:
                master_dark_flat_posix = self.masters["Dark-Flats"].replace("\\", "/")
            elif self.files["Dark-Flats"]:
                os.makedirs(df_target, exist_ok=True)
                os.makedirs(df_converted, exist_ok=True)
                for df_path in self.files["Dark-Flats"]:
                    df_name = os.path.basename(df_path)
                    df_dst = os.path.join(df_target, df_name)
                    if os.path.exists(df_dst):
                        try: os.remove(df_dst)
                        except: pass
                    try: os.symlink(df_path, df_dst)
                    except OSError: shutil.copy2(df_path, df_dst)

                df_meta = [inspect_fits_metadata(f) for f in self.files["Dark-Flats"]]
                df_ext = os.path.splitext(self.files["Dark-Flats"][0])[1].lower()
                df_is_raw = df_ext in ['.cr2', '.nef', '.arw', '.dng']
                df_gain_iso_part = ""
                df_gain_val = df_meta[0].get("gain")
                if df_gain_val:
                    g_clean = str(df_gain_val).replace("Gain", "").replace("ISO", "").strip()
                    df_gain_iso_part = f"iso-{g_clean}" if df_is_raw else f"gain-{g_clean}"
                df_exposures = [m["exp_sec"] for m in df_meta if m.get("exp_sec") is not None]
                df_avg_exp = round(sum(df_exposures) / len(df_exposures)) if df_exposures else 0
                df_temps = [m["raw_temp_val"] for m in df_meta if m.get("raw_temp_val") is not None]
                df_avg_temp = round(sum(df_temps) / len(df_temps)) if df_temps else None
                df_parts = ["master-dark-flat"]
                if df_gain_iso_part:
                    df_parts.append(df_gain_iso_part)
                if df_avg_exp > 0:
                    df_parts.append(f"{df_avg_exp}s")
                if df_avg_temp is not None:
                    df_parts.append(f"{df_avg_temp}deg")
                df_filename = "_".join(df_parts) + ".fit"
                master_dark_flat_posix = os.path.join(base_work_dir, df_filename).replace("\\", "/")

                try:
                    siril.cmd("cd", df_target.replace("\\", "/"))
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "dark", f"-out={df_converted.replace('\\', '/')}")
                    siril.cmd("cd", df_converted.replace("\\", "/"))
                    if master_bias_flat_posix:
                        siril.cmd("calibrate", "dark", f"-bias={master_bias_flat_posix}")
                        siril.cmd("stack", "pp_dark", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_dark_flat_posix}")
                    else:
                        siril.cmd("stack", "dark", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_dark_flat_posix}")
                    siril.cmd("cd", posix_base)
                except Exception as e:
                    try: siril.cmd("cd", posix_base)
                    except: pass
                    print(f"Dark-flat generation notice: {e}")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(f'# Automatically generated script to generate {filename}\n')
            
            if category == "Darks" and self.chk_calibrate_dark.isChecked() and not (self.use_master["Biases"] and self.masters["Biases"]) and self.files["Biases"]:
                bias_target_posix = os.path.join(base_work_dir, "biases").replace("\\", "/")
                bias_converted_posix = os.path.join(base_work_dir, "biases", "converted").replace("\\", "/")
                b_meta = [inspect_fits_metadata(f) for f in self.files["Biases"]]
                b_ext = os.path.splitext(self.files["Biases"][0])[1].lower()
                b_is_raw = b_ext in ['.cr2', '.nef', '.arw', '.dng']
                b_gain_iso_part = ""
                b_gain_val = b_meta[0].get("gain")
                if b_gain_val:
                    g_clean = str(b_gain_val).replace("Gain", "").replace("ISO", "").strip()
                    b_gain_iso_part = f"iso-{g_clean}" if b_is_raw else f"gain-{g_clean}"
                b_filename = f"master-bias_{b_gain_iso_part}.fit" if b_gain_iso_part else "master-bias.fit"
                b_out_posix = os.path.join(base_work_dir, b_filename).replace("\\", "/")
                
                f.write(f'cd "{bias_target_posix}"\n')
                f.write(f'setext fit\n')
                f.write(f'convert bias -out={bias_converted_posix}\n')
                f.write(f'cd "{bias_converted_posix}"\n')
                f.write(f'stack bias rej w {s_low} {s_high} -nonorm -out={b_out_posix}\n\n')

            if category == "Flats":
                if not (self.use_master["Bias-Flats"] and self.masters["Bias-Flats"]) and self.files["Bias-Flats"]:
                    bf_target_posix = os.path.join(target_dir, "bias-flats").replace("\\", "/")
                    bf_converted_posix = os.path.join(target_dir, "bias-flats", "converted").replace("\\", "/")
                    f.write(f'cd "{bf_target_posix}"\n')
                    f.write(f'setext fit\n')
                    f.write(f'convert bias -out={bf_converted_posix}\n')
                    f.write(f'cd "{bf_converted_posix}"\n')
                    f.write(f'stack bias rej w {s_low} {s_high} -nonorm -out={master_bias_flat_posix}\n\n')

                if not (self.use_master["Dark-Flats"] and self.masters["Dark-Flats"]) and self.files["Dark-Flats"]:
                    df_target_posix = os.path.join(target_dir, "dark-flats").replace("\\", "/")
                    df_converted_posix = os.path.join(target_dir, "dark-flats", "converted").replace("\\", "/")
                    f.write(f'cd "{df_target_posix}"\n')
                    f.write(f'setext fit\n')
                    f.write(f'convert dark -out={df_converted_posix}\n')
                    f.write(f'cd "{df_converted_posix}"\n')
                    if master_bias_flat_posix:
                        f.write(f'calibrate dark -bias={master_bias_flat_posix}\n')
                        f.write(f'stack pp_dark rej w {s_low} {s_high} -nonorm -out={master_dark_flat_posix}\n\n')
                    else:
                        f.write(f'stack dark rej w {s_low} {s_high} -nonorm -out={master_dark_flat_posix}\n\n')

            f.write(f'cd "{posix_target}"\n')
            f.write(f'setext fit\n')
            f.write(f'convert {sing_cat} -out={posix_converted}\n')
            f.write(f'cd "{posix_converted}"\n')
            
            if category == "Flats":
                calib_args = []
                if master_bias_flat_posix:
                    calib_args.append(f'-bias={master_bias_flat_posix}')
                if master_dark_flat_posix:
                    calib_args.append(f'-dark={master_dark_flat_posix}')
                
                if calib_args:
                    f.write(f'calibrate flat {" ".join(calib_args)}\n')
                    stack_target_seq = "pp_flat"
                else:
                    stack_target_seq = "flat"

                norm_arg = "-norm=mul" if self.chk_normalize_flats.isChecked() else ""
                stack_script_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=False)
                f.write(f'stack {stack_target_seq} {stack_script_args} {norm_arg} -out={master_out_posix}\n')
            else:
                if category == "Darks" and self.chk_calibrate_dark.isChecked() and master_bias_for_dark_posix:
                    f.write(f'calibrate dark -bias={master_bias_for_dark_posix}\n')
                    stack_seq = "pp_dark"
                else:
                    stack_seq = sing_cat

                f.write(f'stack {stack_seq} {stack_args_str} -out={master_out_posix}\n')
                
            f.write(f'cd "{posix_base}"\n')

        try:
            if category == "Darks" and self.chk_calibrate_dark.isChecked() and not (self.use_master["Biases"] and self.masters["Biases"]) and self.files["Biases"]:
                bias_target = os.path.join(base_work_dir, "biases")
                bias_converted = os.path.join(bias_target, "converted")
                siril.cmd("cd", bias_target.replace("\\", "/"))
                siril.cmd("setext", "fit")
                siril.cmd("convert", "bias", f"-out={bias_converted.replace('\\', '/')}")
                siril.cmd("cd", bias_converted.replace("\\", "/"))
                siril.cmd("stack", "bias", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_bias_for_dark_posix}")
                siril.cmd("cd", posix_base)

            if category == "Flats":
                if not (self.use_master["Bias-Flats"] and self.masters["Bias-Flats"]) and self.files["Bias-Flats"]:
                    bf_target = os.path.join(target_dir, "bias-flats")
                    bf_converted = os.path.join(bf_target, "converted")
                    siril.cmd("cd", bf_target.replace("\\", "/"))
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "bias", f"-out={bf_converted.replace('\\', '/')}")
                    siril.cmd("cd", bf_converted.replace("\\", "/"))
                    siril.cmd("stack", "bias", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_bias_flat_posix}")
                    siril.cmd("cd", posix_base)

                if not (self.use_master["Dark-Flats"] and self.masters["Dark-Flats"]) and self.files["Dark-Flats"]:
                    df_target = os.path.join(target_dir, "dark-flats")
                    df_converted = os.path.join(df_target, "converted")
                    siril.cmd("cd", df_target.replace("\\", "/"))
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "dark", f"-out={df_converted.replace('\\', '/')}")
                    siril.cmd("cd", df_converted.replace("\\", "/"))
                    if master_bias_flat_posix:
                        siril.cmd("calibrate", "dark", f"-bias={master_bias_flat_posix}")
                        siril.cmd("stack", "pp_dark", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_dark_flat_posix}")
                    else:
                        siril.cmd("stack", "dark", "rej", "w", s_low, s_high, "-nonorm", f"-out={master_dark_flat_posix}")
                    siril.cmd("cd", posix_base)

            siril.cmd("cd", posix_target)
            siril.cmd("setext", "fit")
            siril.cmd("convert", sing_cat, f"-out={posix_converted}")
            siril.cmd("cd", posix_converted)

            if category == "Flats":
                if master_bias_flat_posix or master_dark_flat_posix:
                    c_args = ["calibrate", "flat"]
                    if master_bias_flat_posix:
                        c_args.append(f"-bias={master_bias_flat_posix}")
                    if master_dark_flat_posix:
                        c_args.append(f"-dark={master_dark_flat_posix}")
                    siril.cmd(*c_args)
                    stk_seq = "pp_flat"
                else:
                    stk_seq = "flat"

                norm_flag = "-norm=mul" if self.chk_normalize_flats.isChecked() else ""
                flat_cmd_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=False).split()
                siril.cmd("stack", stk_seq, *flat_cmd_args, norm_flag, f"-out={master_out_posix}")
            elif category == "Darks":
                if self.chk_calibrate_dark.isChecked() and master_bias_for_dark_posix:
                    siril.cmd("calibrate", "dark", f"-bias={master_bias_for_dark_posix}")
                    stk_seq = "pp_dark"
                else:
                    stk_seq = "dark"

                dark_cmd_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=True).split()
                siril.cmd("stack", stk_seq, *dark_cmd_args, f"-out={master_out_posix}")
            else:
                bias_cmd_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=True).split()
                siril.cmd("stack", sing_cat, *bias_cmd_args, f"-out={master_out_posix}")

            siril.cmd("cd", posix_base)

            # Nettoyage des dossiers de travail temporaires après génération du Master
            def clear_folder_contents(folder_path):
                if os.path.exists(folder_path):
                    for item in os.listdir(folder_path):
                        item_path = os.path.join(folder_path, item)
                        try:
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)
                            else:
                                os.remove(item_path)
                        except Exception:
                            pass

            try:
                clear_folder_contents(target_dir)
                if category == "Darks" and self.chk_calibrate_dark.isChecked() and not self.use_master["Biases"] and self.files["Biases"]:
                    clear_folder_contents(os.path.join(base_work_dir, "biases"))
                if category == "Flats":
                    if not self.use_master["Bias-Flats"] and self.files["Bias-Flats"]:
                        clear_folder_contents(os.path.join(target_dir, "bias-flats"))
                    if not self.use_master["Dark-Flats"] and self.files["Dark-Flats"]:
                        clear_folder_contents(os.path.join(target_dir, "dark-flats"))
            except Exception:
                pass

            QMessageBox.information(
                self, "Master Generation Complete",
                f"Master generated successfully in Siril!\n\nFile: {filename}\nScript: {script_path}"
            )
        except Exception as err:
            try:
                siril.cmd("cd", posix_base)
            except:
                pass
            QMessageBox.critical(
                self, "Siril Execution Error",
                f"Failed to execute commands in Siril:\n{err}"
            )

    # Génération du fichier .ssf et exécution pas à pas dans Siril avec fenêtre de suivi temps réel
    def run_preprocessing(self):
        work_dir = os.getcwd()
        if not self.files["Lights"]:
            QMessageBox.warning(self, "Error", "No 'Light' images selected.")
            return

        script_path = os.path.join(work_dir, "aobpp_gui_script.ssf")
        posix_base = work_dir.replace("\\", "/")

        stack_method_text = self.combo_stack_method.currentText().lower()
        s_low = f"{self.spin_sigma_low.value():.2f}"
        s_high = f"{self.spin_sigma_high.value():.2f}"

        # Mise en forme des paramètres d'empilement pour le script SSF et les commandes Siril
        def get_stack_args(method_text, low, high, is_master_calib=False):
            if "median" in method_text:
                res = "median"
            elif "average" in method_text:
                res = "avg"
            elif "minimum" in method_text:
                res = "min"
            elif "maximum" in method_text:
                res = "max"
            elif "linear fit" in method_text:
                res = "linearfit"
            elif "winsorized" in method_text:
                res = f"rej w {low} {high}"
            elif "rejection" in method_text or "sigma" in method_text:
                res = f"rej s {low} {high}"
            else:
                res = f"rej w {low} {high}"
            
            if is_master_calib:
                res += " -nonorm"
            return res

        master_bias_path = ""
        master_dark_path = ""
        master_flat_path = ""

        script_lines = []
        script_lines.append('# Siril script automatically generated by AOBPP GUI')
        script_lines.append(f'requires "{REQUIREDVERSION}"\n')
        script_lines.append('setfindstar reset\n')
        script_lines.append(f'cd "{posix_base}"\n')

        steps = []

        # Étape initiale : initialisation du répertoire de travail et réinitialisation de setfindstar
        def step_init_env():
            siril.cmd("setfindstar", "reset")
            siril.cmd("cd", posix_base)

        steps.append(("Initialize Siril environment", step_init_env))

        # 1. Master Bias
        if self.use_master["Biases"] and self.masters["Biases"]:
            master_bias_path = self.masters["Biases"].replace("\\", "/")
        elif self.files["Biases"]:
            script_lines.append('# --- Master Bias Generation ---')
            bias_target = os.path.join(work_dir, "biases")
            bias_converted = os.path.join(bias_target, "converted")
            os.makedirs(bias_target, exist_ok=True)
            os.makedirs(bias_converted, exist_ok=True)
            
            for b_path in self.files["Biases"]:
                b_name = os.path.basename(b_path)
                b_dst = os.path.join(bias_target, b_name)
                if os.path.exists(b_dst):
                    try: os.remove(b_dst)
                    except: pass
                try: os.symlink(b_path, b_dst)
                except OSError: shutil.copy2(b_path, b_dst)

            b_meta = [inspect_fits_metadata(f) for f in self.files["Biases"]]
            b_ext = os.path.splitext(self.files["Biases"][0])[1].lower()
            b_is_raw = b_ext in ['.cr2', '.nef', '.arw', '.dng']
            b_gain_iso_part = ""
            b_gain_val = b_meta[0].get("gain")
            if b_gain_val:
                g_clean = str(b_gain_val).replace("Gain", "").replace("ISO", "").strip()
                b_gain_iso_part = f"iso-{g_clean}" if b_is_raw else f"gain-{g_clean}"
            b_filename = f"master-bias_{b_gain_iso_part}.fit" if b_gain_iso_part else "master-bias.fit"
            master_bias_path = os.path.join(work_dir, b_filename).replace("\\", "/")

            bias_target_posix = bias_target.replace("\\", "/")
            bias_converted_posix = bias_converted.replace("\\", "/")
            bias_stack_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=True)
            
            script_lines.append(f'cd "{bias_target_posix}"')
            script_lines.append('setext fit')
            script_lines.append(f'convert bias -out={bias_converted_posix}')
            script_lines.append(f'cd "{bias_converted_posix}"')
            script_lines.append(f'stack bias {bias_stack_args} -out={master_bias_path}')
            script_lines.append(f'cd "{posix_base}"\n')

            # Exécution dans Siril de la conversion et de l'empilement du Master Bias
            def step_master_bias(
                t_pos=bias_target_posix,
                c_pos=bias_converted_posix,
                s_args=bias_stack_args,
                out_p=master_bias_path
            ):
                siril.cmd("cd", t_pos)
                siril.cmd("setext", "fit")
                siril.cmd("convert", "bias", f"-out={c_pos}")
                siril.cmd("cd", c_pos)
                siril.cmd("stack", "bias", *s_args.split(), f"-out={out_p}")
                siril.cmd("cd", posix_base)

            steps.append((f"Generate Master Bias ({b_filename})", step_master_bias))

        # 2. Master Dark
        if self.use_master["Darks"] and self.masters["Darks"]:
            master_dark_path = self.masters["Darks"].replace("\\", "/")
        elif self.files["Darks"]:
            script_lines.append('# --- Master Dark Generation ---')
            dark_target = os.path.join(work_dir, "darks")
            dark_converted = os.path.join(dark_target, "converted")
            os.makedirs(dark_target, exist_ok=True)
            os.makedirs(dark_converted, exist_ok=True)

            for d_path in self.files["Darks"]:
                d_name = os.path.basename(d_path)
                d_dst = os.path.join(dark_target, d_name)
                if os.path.exists(d_dst):
                    try: os.remove(d_dst)
                    except: pass
                try: os.symlink(d_path, d_dst)
                except OSError: shutil.copy2(d_path, d_dst)

            d_meta = [inspect_fits_metadata(f) for f in self.files["Darks"]]
            d_ext = os.path.splitext(self.files["Darks"][0])[1].lower()
            d_is_raw = d_ext in ['.cr2', '.nef', '.arw', '.dng']
            d_gain_iso_part = ""
            d_gain_val = d_meta[0].get("gain")
            if d_gain_val:
                g_clean = str(d_gain_val).replace("Gain", "").replace("ISO", "").strip()
                d_gain_iso_part = f"iso-{g_clean}" if d_is_raw else f"gain-{g_clean}"
            exposures = [m["exp_sec"] for m in d_meta if m.get("exp_sec") is not None]
            avg_exp = round(sum(exposures) / len(exposures)) if exposures else 0
            temps = [m["raw_temp_val"] for m in d_meta if m.get("raw_temp_val") is not None]
            avg_temp = round(sum(temps) / len(temps)) if temps else None
            parts = ["master-dark"]
            if d_gain_iso_part:
                parts.append(d_gain_iso_part)
            if avg_exp > 0:
                parts.append(f"{avg_exp}s")
            if avg_temp is not None:
                parts.append(f"{avg_temp}deg")
            d_filename = "_".join(parts) + ".fit"
            master_dark_path = os.path.join(work_dir, d_filename).replace("\\", "/")

            dark_target_posix = dark_target.replace("\\", "/")
            dark_converted_posix = dark_converted.replace("\\", "/")
            cal_dark_with_bias = bool(hasattr(self, 'chk_calibrate_dark') and self.chk_calibrate_dark.isChecked() and master_bias_path)
            dark_stack_seq = "pp_dark" if cal_dark_with_bias else "dark"
            dark_stack_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=True)

            script_lines.append(f'cd "{dark_target_posix}"')
            script_lines.append('setext fit')
            script_lines.append(f'convert dark -out={dark_converted_posix}')
            script_lines.append(f'cd "{dark_converted_posix}"')
            if cal_dark_with_bias:
                script_lines.append(f'calibrate dark -bias={master_bias_path}')
            script_lines.append(f'stack {dark_stack_seq} {dark_stack_args} -out={master_dark_path}')
            script_lines.append(f'cd "{posix_base}"\n')

            # Exécution dans Siril de la conversion, calibration optionnelle et empilement du Master Dark
            def step_master_dark(
                t_pos=dark_target_posix,
                c_pos=dark_converted_posix,
                cal_bias=cal_dark_with_bias,
                b_path=master_bias_path,
                seq_name=dark_stack_seq,
                s_args=dark_stack_args,
                out_p=master_dark_path
            ):
                siril.cmd("cd", t_pos)
                siril.cmd("setext", "fit")
                siril.cmd("convert", "dark", f"-out={c_pos}")
                siril.cmd("cd", c_pos)
                if cal_bias:
                    siril.cmd("calibrate", "dark", f"-bias={b_path}")
                siril.cmd("stack", seq_name, *s_args.split(), f"-out={out_p}")
                siril.cmd("cd", posix_base)

            steps.append((f"Generate Master Dark ({d_filename})", step_master_dark))

        # 3. Master Flat
        if self.use_master["Flats"] and self.masters["Flats"]:
            master_flat_path = self.masters["Flats"].replace("\\", "/")
        elif self.files["Flats"]:
            script_lines.append('# --- Master Flat Generation ---')
            flat_target = os.path.join(work_dir, "flats")
            flat_converted = os.path.join(flat_target, "converted")
            os.makedirs(flat_target, exist_ok=True)
            os.makedirs(flat_converted, exist_ok=True)

            for fl_path in self.files["Flats"]:
                fl_name = os.path.basename(fl_path)
                fl_dst = os.path.join(flat_target, fl_name)
                if os.path.exists(fl_dst):
                    try: os.remove(fl_dst)
                    except: pass
                try: os.symlink(fl_path, fl_dst)
                except OSError: shutil.copy2(fl_path, fl_dst)

            fl_meta = [inspect_fits_metadata(f) for f in self.files["Flats"]]
            fl_ext = os.path.splitext(self.files["Flats"][0])[1].lower()
            fl_is_raw = fl_ext in ['.cr2', '.nef', '.arw', '.dng']
            scope_name = fl_meta[0].get("scope_name") if not fl_is_raw else None
            filter_name = fl_meta[0].get("filter") if not fl_is_raw else None
            curr_date = datetime.now().strftime("%Y%m%d")
            fl_parts = ["master-flat"]
            if scope_name and scope_name.strip():
                fl_parts.append(re.sub(r'[\s/\\:]+', '-', scope_name.strip()))
            if filter_name and filter_name.strip():
                fl_parts.append(re.sub(r'[\s/\\:]+', '-', filter_name.strip()))
            fl_parts.append(curr_date)
            fl_filename = "_".join(fl_parts) + ".fit"
            master_flat_path = os.path.join(work_dir, fl_filename).replace("\\", "/")

            master_bias_flat_posix = ""
            master_dark_flat_posix = ""

            if self.use_master["Bias-Flats"] and self.masters["Bias-Flats"]:
                master_bias_flat_posix = self.masters["Bias-Flats"].replace("\\", "/")
            elif self.files["Bias-Flats"]:
                bf_target = os.path.join(flat_target, "bias-flats")
                bf_converted = os.path.join(bf_target, "converted")
                os.makedirs(bf_target, exist_ok=True)
                os.makedirs(bf_converted, exist_ok=True)
                for bf_path in self.files["Bias-Flats"]:
                    bf_name = os.path.basename(bf_path)
                    bf_dst = os.path.join(bf_target, bf_name)
                    if os.path.exists(bf_dst):
                        try: os.remove(bf_dst)
                        except: pass
                    try: os.symlink(bf_path, bf_dst)
                    except OSError: shutil.copy2(bf_path, bf_dst)

                bf_meta = [inspect_fits_metadata(f) for f in self.files["Bias-Flats"]]
                bf_ext = os.path.splitext(self.files["Bias-Flats"][0])[1].lower()
                bf_is_raw = bf_ext in ['.cr2', '.nef', '.arw', '.dng']
                bf_gain_iso_part = ""
                bf_gain_val = bf_meta[0].get("gain")
                if bf_gain_val:
                    g_clean = str(bf_gain_val).replace("Gain", "").replace("ISO", "").strip()
                    bf_gain_iso_part = f"iso-{g_clean}" if bf_is_raw else f"gain-{g_clean}"
                bf_filename = f"master-bias-flat_{bf_gain_iso_part}.fit" if bf_gain_iso_part else "master-bias-flat.fit"
                master_bias_flat_posix = os.path.join(work_dir, bf_filename).replace("\\", "/")

                bf_target_pos = bf_target.replace("\\", "/")
                bf_conv_pos = bf_converted.replace("\\", "/")
                script_lines.append(f'cd "{bf_target_pos}"')
                script_lines.append('setext fit')
                script_lines.append(f'convert bias -out={bf_conv_pos}')
                script_lines.append(f'cd "{bf_conv_pos}"')
                script_lines.append(f'stack bias rej w {s_low} {s_high} -nonorm -out={master_bias_flat_posix}')
                script_lines.append(f'cd "{posix_base}"')

                # Génération du Master Bias-Flat dans Siril
                def step_master_bias_flat(
                    t_p=bf_target_pos,
                    c_p=bf_conv_pos,
                    low_v=s_low,
                    high_v=s_high,
                    out_p=master_bias_flat_posix
                ):
                    siril.cmd("cd", t_p)
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "bias", f"-out={c_p}")
                    siril.cmd("cd", c_p)
                    siril.cmd("stack", "bias", "rej", "w", low_v, high_v, "-nonorm", f"-out={out_p}")
                    siril.cmd("cd", posix_base)

                steps.append((f"Generate Master Bias-Flat ({bf_filename})", step_master_bias_flat))

            if self.use_master["Dark-Flats"] and self.masters["Dark-Flats"]:
                master_dark_flat_posix = self.masters["Dark-Flats"].replace("\\", "/")
            elif self.files["Dark-Flats"]:
                df_target = os.path.join(flat_target, "dark-flats")
                df_converted = os.path.join(df_target, "converted")
                os.makedirs(df_target, exist_ok=True)
                os.makedirs(df_converted, exist_ok=True)
                for df_path in self.files["Dark-Flats"]:
                    df_name = os.path.basename(df_path)
                    df_dst = os.path.join(df_target, df_name)
                    if os.path.exists(df_dst):
                        try: os.remove(df_dst)
                        except: pass
                    try: os.symlink(df_path, df_dst)
                    except OSError: shutil.copy2(df_path, df_dst)

                df_meta = [inspect_fits_metadata(f) for f in self.files["Dark-Flats"]]
                df_ext = os.path.splitext(self.files["Dark-Flats"][0])[1].lower()
                df_is_raw = df_ext in ['.cr2', '.nef', '.arw', '.dng']
                df_gain_iso_part = ""
                df_gain_val = df_meta[0].get("gain")
                if df_gain_val:
                    g_clean = str(df_gain_val).replace("Gain", "").replace("ISO", "").strip()
                    df_gain_iso_part = f"iso-{g_clean}" if df_is_raw else f"gain-{g_clean}"
                df_exposures = [m["exp_sec"] for m in df_meta if m.get("exp_sec") is not None]
                df_avg_exp = round(sum(df_exposures) / len(df_exposures)) if df_exposures else 0
                df_temps = [m["raw_temp_val"] for m in df_meta if m.get("raw_temp_val") is not None]
                df_avg_temp = round(sum(df_temps) / len(df_temps)) if df_temps else None
                df_parts = ["master-dark-flat"]
                if df_gain_iso_part:
                    df_parts.append(df_gain_iso_part)
                if df_avg_exp > 0:
                    df_parts.append(f"{df_avg_exp}s")
                if df_avg_temp is not None:
                    df_parts.append(f"{df_avg_temp}deg")
                df_filename = "_".join(df_parts) + ".fit"
                master_dark_flat_posix = os.path.join(work_dir, df_filename).replace("\\", "/")

                df_target_pos = df_target.replace("\\", "/")
                df_conv_pos = df_converted.replace("\\", "/")
                has_bf = bool(master_bias_flat_posix)
                script_lines.append(f'cd "{df_target_pos}"')
                script_lines.append('setext fit')
                script_lines.append(f'convert dark -out={df_conv_pos}')
                script_lines.append(f'cd "{df_conv_pos}"')
                if has_bf:
                    script_lines.append(f'calibrate dark -bias={master_bias_flat_posix}')
                    script_lines.append(f'stack pp_dark rej w {s_low} {s_high} -nonorm -out={master_dark_flat_posix}\n')
                else:
                    script_lines.append(f'stack dark rej w {s_low} {s_high} -nonorm -out={master_dark_flat_posix}\n')
                script_lines.append(f'cd "{posix_base}"')

                # Génération du Master Dark-Flat dans Siril
                def step_master_dark_flat(
                    t_p=df_target_pos,
                    c_p=df_conv_pos,
                    use_bf=has_bf,
                    bf_p=master_bias_flat_posix,
                    low_v=s_low,
                    high_v=s_high,
                    out_p=master_dark_flat_posix
                ):
                    siril.cmd("cd", t_p)
                    siril.cmd("setext", "fit")
                    siril.cmd("convert", "dark", f"-out={c_p}")
                    siril.cmd("cd", c_p)
                    if use_bf:
                        siril.cmd("calibrate", "dark", f"-bias={bf_p}")
                        siril.cmd("stack", "pp_dark", "rej", "w", low_v, high_v, "-nonorm", f"-out={out_p}")
                    else:
                        siril.cmd("stack", "dark", "rej", "w", low_v, high_v, "-nonorm", f"-out={out_p}")
                    siril.cmd("cd", posix_base)

                steps.append((f"Generate Master Dark-Flat ({df_filename})", step_master_dark_flat))

            flat_target_posix = flat_target.replace("\\", "/")
            flat_converted_posix = flat_converted.replace("\\", "/")

            calib_args = []
            if master_bias_flat_posix:
                calib_args.append(f'-bias={master_bias_flat_posix}')
            if master_dark_flat_posix:
                calib_args.append(f'-dark={master_dark_flat_posix}')

            if calib_args:
                stack_target_seq = "pp_flat"
            else:
                stack_target_seq = "flat"

            norm_arg = "-norm=mul" if hasattr(self, 'chk_normalize_flats') and self.chk_normalize_flats.isChecked() else ""
            flat_stack_args = get_stack_args(stack_method_text, s_low, s_high, is_master_calib=False)

            script_lines.append(f'cd "{flat_target_posix}"')
            script_lines.append('setext fit')
            script_lines.append(f'convert flat -out={flat_converted_posix}')
            script_lines.append(f'cd "{flat_converted_posix}"')
            if calib_args:
                script_lines.append(f'calibrate flat {" ".join(calib_args)}')
            script_lines.append(f'stack {stack_target_seq} {flat_stack_args} {norm_arg} -out={master_flat_path}')
            script_lines.append(f'cd "{posix_base}"\n')

            # Exécution dans Siril de la génération du Master Flat
            def step_master_flat(
                t_pos=flat_target_posix,
                c_pos=flat_converted_posix,
                c_args=list(calib_args),
                stk_seq=stack_target_seq,
                s_args=flat_stack_args,
                n_flag=norm_arg,
                out_p=master_flat_path
            ):
                siril.cmd("cd", t_pos)
                siril.cmd("setext", "fit")
                siril.cmd("convert", "flat", f"-out={c_pos}")
                siril.cmd("cd", c_pos)
                if c_args:
                    siril.cmd("calibrate", "flat", *c_args)
                cmd_parts = ["stack", stk_seq] + s_args.split()
                if n_flag:
                    cmd_parts.append(n_flag)
                cmd_parts.append(f"-out={out_p}")
                siril.cmd(*cmd_parts)
                siril.cmd("cd", posix_base)

            steps.append((f"Generate Master Flat ({fl_filename})", step_master_flat))

        # 4. Calibration des lights
        script_lines.append('# --- Lights Calibration ---')
        lights_target = os.path.join(work_dir, "lights")
        lights_converted = os.path.join(lights_target, "converted")
        os.makedirs(lights_target, exist_ok=True)
        os.makedirs(lights_converted, exist_ok=True)

        for l_path in self.files["Lights"]:
            l_name = os.path.basename(l_path)
            l_dst = os.path.join(lights_target, l_name)
            if os.path.exists(l_dst):
                try: os.remove(l_dst)
                except: pass
            try: os.symlink(l_path, l_dst)
            except OSError: shutil.copy2(l_path, l_dst)

        lights_target_posix = lights_target.replace("\\", "/")
        lights_converted_posix = lights_converted.replace("\\", "/")

        drizzle_enabled = self.chk_enable_drizzle.isChecked()

        calib_flags = []
        if self.chk_cfa_calibration.isChecked():
            calib_flags.append("-cfa")

        if master_dark_path:
            calib_flags.append(f"-dark={master_dark_path}")
        if master_flat_path:
            calib_flags.append(f"-flat={master_flat_path}")

        dark_opt_idx = self.combo_dark_opt.currentIndex()
        if dark_opt_idx == 1:
            calib_flags.append("-opt")
        elif dark_opt_idx == 2:
            calib_flags.append("-opt=exp")

        cosmetic_enabled = self.chk_enable_cosmetic.isChecked()
        if cosmetic_enabled:
            c_hot = f"{self.spin_cosmetic_hot.value():.2f}"
            c_cold = f"{self.spin_cosmetic_cold.value():.2f}"
            calib_flags.extend(["-cc=dark", c_hot, c_cold])

        if not drizzle_enabled:
            calib_flags.append("-debayer")

        calib_line = 'calibrate lights' + (' ' + ' '.join(calib_flags) if calib_flags else '')

        script_lines.append(f'cd "{lights_target_posix}"')
        script_lines.append('setext fit')
        script_lines.append(f'convert lights -out={lights_converted_posix}')
        script_lines.append(f'cd "{lights_converted_posix}"')
        script_lines.append(calib_line + '\n')

        # Conversion des images Light dans Siril
        def step_convert_lights(t_pos=lights_target_posix, c_pos=lights_converted_posix):
            siril.cmd("cd", t_pos)
            siril.cmd("setext", "fit")
            siril.cmd("convert", "lights", f"-out={c_pos}")
            siril.cmd("cd", c_pos)

        # Calibration des images Light dans Siril
        def step_calibrate_lights(c_pos=lights_converted_posix, c_flags=list(calib_flags)):
            siril.cmd("cd", c_pos)
            siril.cmd("calibrate", "lights", *c_flags)

        steps.append(("Convert Light frames", step_convert_lights))
        steps.append(("Calibrate Light frames", step_calibrate_lights))

        seq_target = 'pp_lights'

        # 5. Registration, Rescaling et Drizzle des Lights
        layer_map = {"Red": 0, "Green": 1, "Blue": 2}
        layer_idx = layer_map.get(self.combo_layer_ref.currentText(), 0)
        framing_map = {"None": "current", "Inside": "min", "Outside": "max", "Center of gravity": "cog"}
        framing_mode = framing_map.get(self.combo_autocrop.currentText(), "current")
        rescaling_val = self.spin_rescaling.value()

        script_lines.append('# --- Lights Registration ---')
        script_lines.append('setfindstar')
        register_line = f'register {seq_target} -layer={layer_idx} -2pass'
        script_lines.append(register_line)

        applyreg_line = f'seqapplyreg {seq_target} -layer={layer_idx} -framing={framing_mode}'
        applyreg_flags = [f"-layer={layer_idx}", f"-framing={framing_mode}"]
        if drizzle_enabled:
            d_scale = self.spin_drizzle_scale.value()
            d_frac = self.spin_pixel_frac.value()
            d_kernel = self.combo_kernel.currentText()
            d_args = ['-drizzle', f'-scale={d_scale}', f'-pixfrac={d_frac}', f'-kernel={d_kernel}']
            if master_flat_path:
                d_args.append(f'-flat={master_flat_path}')
            applyreg_line += ' ' + ' '.join(d_args)
            applyreg_flags.extend(d_args)
        else:
            applyreg_line += f' -scale={rescaling_val}'
            applyreg_flags.append(f"-scale={rescaling_val}")

        script_lines.append(applyreg_line + '\n')

        # Détection d'étoiles et alignement (register + seqapplyreg) dans Siril
        def step_register_lights(
            c_pos=lights_converted_posix,
            s_seq=seq_target,
            l_idx=layer_idx,
            a_flags=list(applyreg_flags)
        ):
            siril.cmd("cd", c_pos)
            siril.cmd("setfindstar")
            siril.cmd("register", s_seq, f"-layer={l_idx}", "-2pass")
            siril.cmd("seqapplyreg", s_seq, *a_flags)

        steps.append(("Register & align Light frames", step_register_lights))

        # 6. Stacking et finalisation, enfin !
        script_lines.append('# --- Lights Stacking ---')
        if "median" in stack_method_text:
            stk_args = "median"
        elif "average" in stack_method_text:
            stk_args = "avg"
        elif "minimum" in stack_method_text:
            stk_args = "min"
        elif "maximum" in stack_method_text:
            stk_args = "max"
        elif "linear fit" in stack_method_text:
            stk_args = "linearfit"
        elif "winsorized" in stack_method_text:
            stk_args = f"rej w {s_low} {s_high}"
        else:
            stk_args = f"rej s {s_low} {s_high}"

        stack_line = f'stack r_{seq_target} {stk_args}'
        stack_flags = stk_args.split()

        if "median" in stack_method_text or "average" in stack_method_text or "rej" in stk_args or "winsorized" in stack_method_text or "linear fit" in stack_method_text:
            stack_line += ' -norm=addscale -output_norm -rgb_equal'
            stack_flags.extend(["-norm=addscale", "-output_norm", "-rgb_equal"])

        if framing_mode == "max":
            stack_line += ' -maximize'
            stack_flags.append("-maximize")

        stack_line += ' -out=result.fit'
        stack_flags.append("-out=result.fit")

        script_lines.append(stack_line + '\n')
        script_lines.append('load result.fit')
        script_lines.append('mirrorx -bottomup')
        script_lines.append(f'cd "{posix_base}"')
        script_lines.append('save "final_stack.fit"\n')
        script_lines.append('setfindstar reset')

        # Empilement des images alignées dans Siril
        def step_stack_lights(c_pos=lights_converted_posix, s_seq=seq_target, s_flags=list(stack_flags)):
            siril.cmd("cd", c_pos)
            siril.cmd("stack", f"r_{s_seq}", *s_flags)

        # Chargement, retournement vertical et sauvegarde du résultat final
        def step_finalize_stack(c_pos=lights_converted_posix, b_pos=posix_base):
            siril.cmd("cd", c_pos)
            siril.cmd("load", "result.fit")
            siril.cmd("mirrorx", "-bottomup")
            siril.cmd("cd", b_pos)
            siril.cmd("save", "final_stack.fit")
            siril.cmd("setfindstar", "reset")

        steps.append(("Stack aligned Light frames", step_stack_lights))
        steps.append(("Load, flip and save final_stack.fit", step_finalize_stack))

        # 7. Purge optionnelle des fichiers intermédiaires dans le dossier "lights" du dossier de travail
        if hasattr(self, 'chk_clear_intermediate') and self.chk_clear_intermediate.isChecked():
            def step_clear_lights_folder(l_dir=lights_target):
                if os.path.exists(l_dir):
                    for item in os.listdir(l_dir):
                        item_path = os.path.join(l_dir, item)
                        try:
                            if os.path.isdir(item_path) and not os.path.islink(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)
                            else:
                                os.remove(item_path)
                        except Exception:
                            pass

            steps.append(("Clear intermediate files in lights folder", step_clear_lights_folder))

        # Écriture du fichier de script SSF sur disque
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("\n".join(script_lines) + "\n")

        # Ouverture de la fenêtre de suivi temps réel à la place de la popup "Process loaded"
        self.btn_run.setEnabled(False)
        dlg = ConsoleProgressDialog(self, title="Pre-Processing Console")
        self._progress_dialog = dlg
        dlg.show()
        dlg.append_log(f"SSF script generated: {script_path}")
        dlg.append_log(f"Total steps to execute: {len(steps)}")
        dlg.set_step_progress(0, len(steps), f"Starting step 1/{len(steps)}...")

        # Exécution séquentielle non bloquante des étapes via QTimer
        def execute_step(index):
            total_steps = len(steps)
            if index >= total_steps:
                try:
                    siril.cmd("cd", posix_base)
                except Exception:
                    pass
                self.btn_run.setEnabled(True)
                dlg.mark_finished(
                    True,
                    f"All {total_steps} steps completed."
                )
                return

            step_label, step_fn = steps[index]
            dlg.set_step_progress(index, total_steps, f"[{index + 1}/{total_steps}] {step_label}...")
            dlg.append_log(f"▶ [{index + 1}/{total_steps}] {step_label}")

            try:
                step_fn()
                dlg.append_log(f"✔ [{index + 1}/{total_steps}] Completed: {step_label}")
                dlg.set_step_progress(index + 1, total_steps, f"[{index + 1}/{total_steps}] {step_label} — Done")
                QTimer.singleShot(30, lambda: execute_step(index + 1))
            except Exception as err:
                try:
                    siril.cmd("cd", posix_base)
                    siril.cmd("setfindstar", "reset")
                except Exception:
                    pass
                self.btn_run.setEnabled(True)
                dlg.append_log(f"✖ Error during '{step_label}': {err}")
                dlg.mark_finished(
                    False,
                    f"Execution failed at step {index + 1}/{total_steps} ({step_label}):\n{err}"
                )

        QTimer.singleShot(30, lambda: execute_step(0))

# Point d'entrée de l'application Qt
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MultiBatchPreProcessingApp()
    window.show()
    sys.exit(app.exec())