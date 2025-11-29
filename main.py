import sys
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QSplitter,
                               QToolBar, QMenu, QFileDialog, QMessageBox, QLabel, QStatusBar,
                               QPlainTextEdit, QInputDialog, QSlider, QPushButton, QHBoxLayout, 
                               QVBoxLayout, QDoubleSpinBox, QGroupBox, QDialog, QFormLayout, QDialogButtonBox,
                               QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtGui import QAction, QFont, QIcon, QDesktopServices, QColor, QPixmap, QPainter, QBrush, QPen, QTextCursor, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, QTimer, QUrl, QSize

from viewer import NCPreviewWidget
from parser import SimpleParser
from utils import GCodeHighlighter, CodeTransformer
from config_manager import ConfigManager
from dxf_exporter import DXFExporter

# --- WELCOME / DONATION DIALOG ---
class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome")
        self.setFixedSize(450, 350)
        # Ukloni ? dugme iz naslova
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        
        # Logo / Naslov
        title = QLabel("PyNC Viewer PRO")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #007acc; margin-top: 10px;")
        layout.addWidget(title)
        
        version = QLabel("v1.6 (Open Source Edition)")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(version)
        
        layout.addSpacing(20)
        
        # Tekst
        msg = QLabel("Thank you for using this software!\nIt is designed to help engineers and machinists visualize and debug G-Code quickly.")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(msg)
        
        layout.addSpacing(10)
        
        # Donation Button
        btn_donate = QPushButton("☕ Buy me a Coffee")
        btn_donate.setCursor(Qt.PointingHandCursor)
        btn_donate.setMinimumHeight(50)
        btn_donate.setFont(QFont("Segoe UI", 12, QFont.Bold))
        # Zlatna/Narandzasta boja
        btn_donate.setStyleSheet("""
            QPushButton {
                background-color: #FFDD00;
                color: #000000;
                border-radius: 8px;
                border: 1px solid #cca300;
            }
            QPushButton:hover {
                background-color: #ffea5c;
            }
        """)
        btn_donate.clicked.connect(self.open_donation)
        layout.addWidget(btn_donate)
        
        hint = QLabel("(Support future development)")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Close
        btn_close = QPushButton("Start Using App")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("padding: 8px;")
        layout.addWidget(btn_close)
        
        self.setLayout(layout)

    def open_donation(self):
        # --- OVDE STAVI SVOJ LINK ---
        url = QUrl("https://www.buymeacoffee.com/tvoj_username") 
        QDesktopServices.openUrl(url)

# --- SCAN RESULT DIALOG ---
class ScanResultDialog(QDialog):
    def __init__(self, issues, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Smart Scan Report")
        self.resize(600, 400)
        layout = QVBoxLayout()
        title = QLabel(f"Found {len(issues)} issues")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold)); layout.addWidget(title)
        self.table = QTableWidget(); self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Line", "Severity", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setRowCount(len(issues))
        for i, issue in enumerate(issues):
            self.table.setItem(i, 0, QTableWidgetItem(str(issue['line'])))
            item_sev = QTableWidgetItem(issue['type'])
            if issue['type'] == 'CRITICAL': item_sev.setForeground(QColor("red")); item_sev.setFont(QFont("Arial", 10, QFont.Bold))
            elif issue['type'] == 'ERROR': item_sev.setForeground(QColor("orange"))
            else: item_sev.setForeground(QColor("yellow"))
            self.table.setItem(i, 1, item_sev); self.table.setItem(i, 2, QTableWidgetItem(issue['msg']))
        layout.addWidget(self.table)
        btn_close = QPushButton("Close"); btn_close.clicked.connect(self.accept); layout.addWidget(btn_close)
        self.setLayout(layout)

# --- TOOL LIBRARY DIALOG ---
class ToolLibraryDialog(QDialog):
    def __init__(self, tools_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tool Library")
        self.resize(400, 400)
        self.tools = tools_dict.copy()
        layout = QVBoxLayout()
        self.table = QTableWidget(); self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Tool Number (T)", "Diameter (mm)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.refresh_table(); layout.addWidget(self.table)
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Tool"); btn_add.clicked.connect(self.add_tool)
        btn_del = QPushButton("Remove Selected"); btn_del.clicked.connect(self.del_tool)
        btn_layout.addWidget(btn_add); btn_layout.addWidget(btn_del); layout.addLayout(btn_layout)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.save_and_close); bbox.rejected.connect(self.reject); layout.addWidget(bbox)
        self.setLayout(layout)
    def refresh_table(self):
        self.table.setRowCount(0); sorted_tools = sorted([int(k) for k in self.tools.keys()])
        for t_id in sorted_tools:
            row = self.table.rowCount(); self.table.insertRow(row)
            item_id = QTableWidgetItem(str(t_id)); item_id.setFlags(item_id.flags() ^ Qt.ItemIsEditable); self.table.setItem(row, 0, item_id)
            item_dia = QTableWidgetItem(str(self.tools[str(t_id)])); self.table.setItem(row, 1, item_dia)
    def add_tool(self):
        t_id, ok = QInputDialog.getInt(self, "New Tool", "Tool Number (T):", 1, 1, 99)
        if ok:
            dia, ok2 = QInputDialog.getDouble(self, "New Tool", "Diameter (mm):", 10.0, 0.1, 100.0)
            if ok2: self.tools[str(t_id)] = dia; self.refresh_table()
    def del_tool(self):
        row = self.table.currentRow()
        if row >= 0:
            t_id = self.table.item(row, 0).text()
            if t_id in self.tools: del self.tools[t_id]; self.refresh_table()
    def save_and_close(self):
        for row in range(self.table.rowCount()):
            t_id = self.table.item(row, 0).text()
            try: dia = float(self.table.item(row, 1).text()); self.tools[t_id] = dia
            except: pass
        self.accept()
    def get_data(self): return self.tools

# --- SETTINGS DIALOG ---
class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setFixedWidth(350)
        self.config = current_config.copy()
        layout = QVBoxLayout(); form = QFormLayout()
        self.spin_x = QDoubleSpinBox(); self.spin_x.setRange(10, 5000); self.spin_x.setValue(self.config['machine_size_x'])
        self.spin_y = QDoubleSpinBox(); self.spin_y.setRange(10, 5000); self.spin_y.setValue(self.config['machine_size_y'])
        self.spin_z = QDoubleSpinBox(); self.spin_z.setRange(10, 2000); self.spin_z.setValue(self.config['machine_size_z'])
        form.addRow("Machine Width (X):", self.spin_x); form.addRow("Machine Depth (Y):", self.spin_y); form.addRow("Machine Height (Z):", self.spin_z)
        layout.addSpacing(10)
        self.spin_rapid = QDoubleSpinBox(); self.spin_rapid.setRange(100, 50000); self.spin_rapid.setValue(self.config['rapid_feed'])
        form.addRow("G0 Rapid Speed:", self.spin_rapid)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)
    def get_data(self):
        self.config.update({"machine_size_x": self.spin_x.value(), "machine_size_y": self.spin_y.value(), "machine_size_z": self.spin_z.value(), "rapid_feed": self.spin_rapid.value()})
        return self.config

# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyNC Viewer PRO - v1.6")
        self.resize(1400, 850)
        
        self.setAcceptDrops(True)
        self.setWindowIcon(self.create_app_icon())
        
        self.cfg_manager = ConfigManager()
        self.settings = self.cfg_manager.load_config()
        self.is_dark = (self.settings.get('theme', 'dark') == 'dark')
        
        self.parser = SimpleParser()
        self.transformer = CodeTransformer()
        self.dxf_exporter = DXFExporter()
        
        self.is_playing = False; self.current_anim_dist = 0.0; self.anim_speed = 1.0
        
        self.init_ui()
        self.apply_settings_to_components()
        
        self.highlighter = GCodeHighlighter(self.editor.document())
        self.update_timer = QTimer(); self.update_timer.setSingleShot(True); self.update_timer.timeout.connect(self.process_gcode)
        self.anim_timer = QTimer(); self.anim_timer.timeout.connect(self.animate_step)
        
        self.editor.textChanged.connect(self.schedule_update)
        self.editor.cursorPositionChanged.connect(self.on_cursor_move)
        self.gl_widget.toolMoved.connect(self.update_dro)
        
        self.apply_theme()
        self.load_demo()
        
        # STARTUP WELCOME SCREEN (Samo ako zelis da iskoci svaki put)
        QTimer.singleShot(200, self.show_welcome)

    def show_welcome(self):
        dlg = WelcomeDialog(self)
        dlg.exec()

    def create_app_icon(self):
        pixmap = QPixmap(64, 64); pixmap.fill(Qt.transparent); painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing); painter.setBrush(QBrush(QColor("#007acc"))); painter.setPen(Qt.NoPen); painter.drawRoundedRect(0, 0, 64, 64, 10, 10)
        painter.setPen(QColor("white")); painter.setFont(QFont("Arial", 28, QFont.Bold)); painter.drawText(pixmap.rect(), Qt.AlignCenter, "NC"); painter.end()
        return QIcon(pixmap)

    def create_dxf_icon(self):
        pixmap = QPixmap(32, 32); pixmap.fill(Qt.transparent); painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing); painter.setBrush(QBrush(QColor("#28a745"))); painter.setPen(Qt.NoPen); painter.drawRoundedRect(0, 0, 32, 32, 5, 5)
        painter.setPen(QColor("white")); painter.setFont(QFont("Arial", 10, QFont.Bold)); painter.drawText(pixmap.rect(), Qt.AlignCenter, "DXF"); painter.end()
        return QIcon(pixmap)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files: self.load_file_from_path(files[0])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space: self.toggle_play()
        else: super().keyPressEvent(event)

    def init_ui(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Open...", self.open_file, "Ctrl+O")
        file_menu.addAction("Save...", self.save_file, "Ctrl+S")
        file_menu.addSeparator()
        file_menu.addAction("Export to DXF...", self.export_dxf) 
        file_menu.addSeparator(); file_menu.addAction("Exit", self.close)
        
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction("Tool Library...", self.open_tool_library)
        tools_menu.addSeparator()
        tools_menu.addAction("Preferences...", self.open_settings)
        tools_menu.addAction("Smart Scan / Check Code", self.run_smart_scan)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Renumber...", self.renumber_advanced); edit_menu.addAction("Remove N Numbers", self.remove_line_numbers) 
        
        trans_menu = menubar.addMenu("&Transform")
        trans_menu.addAction("Mirror X", lambda: self.apply_transform("mirror_x")); trans_menu.addAction("Mirror Y", lambda: self.apply_transform("mirror_y"))
        trans_menu.addSeparator(); trans_menu.addAction("Scale: mm to Inch", lambda: self.apply_transform("mm_to_inch")); trans_menu.addAction("Shift X/Y/Z...", self.open_shift_dialog)
        trans_menu.addSeparator()
        trans_menu.addAction("Swap Axes (X->-X, Y<->Z)", lambda: self.apply_transform("swap_axes_maho")) 

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Switch Theme", self.toggle_theme); view_menu.addAction("Reset View", lambda: self.gl_widget.reset_view())
        
        # HELP MENU (Za donacije kasnije)
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About / Donate", self.show_welcome)

        toolbar = QToolBar(); self.addToolBar(toolbar)
        toolbar.addAction(QAction("📂 Open", self, triggered=self.open_file))
        toolbar.addAction(QAction("💾 Save", self, triggered=self.save_file))
        toolbar.addSeparator()
        toolbar.addAction(QAction("⚡ Refresh", self, triggered=self.process_gcode))
        toolbar.addAction(QAction("🐞 Scan", self, triggered=self.run_smart_scan))
        action_dxf = QAction(self.create_dxf_icon(), "DXF Export", self); action_dxf.triggered.connect(self.export_dxf); toolbar.addAction(action_dxf)
        toolbar.addSeparator()
        toolbar.addAction(QAction("🎥 Reset", self, triggered=lambda: self.gl_widget.reset_view()))
        toolbar.addAction(QAction("🛠 Tools", self, triggered=self.open_tool_library)) 
        empty = QWidget(); empty.setFixedWidth(20); toolbar.addWidget(empty)
        self.time_label = QLabel("Time: 00:00"); self.time_label.setFont(QFont("Arial", 10, QFont.Bold)); toolbar.addWidget(self.time_label)

        anim_toolbar = QToolBar("Animation"); self.addToolBar(Qt.BottomToolBarArea, anim_toolbar)
        self.btn_play = QPushButton("▶ Play"); self.btn_play.clicked.connect(self.toggle_play); anim_toolbar.addWidget(self.btn_play)
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.on_slider_move); self.slider.sliderPressed.connect(lambda: self.anim_timer.stop()); self.slider.sliderReleased.connect(lambda: self.anim_timer.start(30) if self.is_playing else None)
        anim_toolbar.addWidget(self.slider)

        splitter = QSplitter(Qt.Horizontal)
        self.editor = QPlainTextEdit(); self.editor.setFont(QFont("Consolas", 11))
        self.gl_widget = NCPreviewWidget(); dro_panel = self.create_dro_panel()
        splitter.addWidget(self.editor); splitter.addWidget(self.gl_widget); splitter.addWidget(dro_panel)
        splitter.setSizes([350, 800, 250]); self.setCentralWidget(splitter); self.status = QStatusBar(); self.setStatusBar(self.status)

    def create_dro_panel(self):
        panel = QWidget(); layout = QVBoxLayout(); panel.setLayout(layout)
        panel.setStyleSheet("background-color: #111; border-left: 1px solid #444;")
        lbl_title = QLabel("DIGITAL READOUT"); lbl_title.setStyleSheet("color: #888; font-weight: bold; letter-spacing: 2px;"); lbl_title.setAlignment(Qt.AlignCenter); layout.addWidget(lbl_title); layout.addSpacing(20)
        self.lbl_x = self.create_axis_label("X", "0.000"); self.lbl_y = self.create_axis_label("Y", "0.000"); self.lbl_z = self.create_axis_label("Z", "0.000")
        layout.addWidget(self.lbl_x); layout.addWidget(self.lbl_y); layout.addWidget(self.lbl_z); layout.addSpacing(30)
        grp_tool = QGroupBox("Active Tool"); grp_tool.setStyleSheet("QGroupBox { color: white; border: 1px solid #444; margin-top: 10px; }"); t_layout = QVBoxLayout()
        self.lbl_tool_t = QLabel("T1"); self.lbl_tool_t.setFont(QFont("Arial", 28, QFont.Bold)); self.lbl_tool_t.setStyleSheet("color: yellow; margin-bottom: 5px;"); self.lbl_tool_t.setAlignment(Qt.AlignCenter)
        self.lbl_tool_dia = QLabel("Dia: 10.0 mm"); self.lbl_tool_dia.setStyleSheet("color: #ccc; font-size: 14px;"); self.lbl_tool_dia.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_tool_t); t_layout.addWidget(self.lbl_tool_dia); grp_tool.setLayout(t_layout)
        layout.addWidget(grp_tool); layout.addStretch(); return panel

    def create_axis_label(self, axis, val):
        lbl = QLabel(f"{axis}  {val}"); lbl.setFont(QFont("Consolas", 24, QFont.Bold)); lbl.setStyleSheet("QLabel { color: #00ff00; background-color: #000; border: 2px solid #333; padding: 10px; border-radius: 5px; }"); lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter); return lbl

    def export_dxf(self):
        text = self.editor.toPlainText()
        lines = self.parser.parse(text)
        if not lines: QMessageBox.warning(self, "Export", "No G-Code to export."); return
        filename, _ = QFileDialog.getSaveFileName(self, "Export DXF", "", "DXF Files (*.dxf)")
        if filename:
            success, msg = self.dxf_exporter.export(filename, lines)
            if success: QMessageBox.information(self, "Success", f"Successfully exported to:\n{filename}")
            else: QMessageBox.critical(self, "Error", f"Failed to export:\n{msg}")

    def run_smart_scan(self):
        txt = self.editor.toPlainText(); tool_lib = self.settings.get("tool_library", {}); limits = [self.settings['machine_size_x'], self.settings['machine_size_y'], self.settings['machine_size_z']]
        issues = self.parser.scan_for_errors(txt, tool_lib, limits)
        if not issues: QMessageBox.information(self, "Scan Complete", "No issues found! Your G-Code looks clean.")
        else: dlg = ScanResultDialog(issues, self); dlg.exec()
    def open_tool_library(self):
        dlg = ToolLibraryDialog(self.settings.get("tool_library", {}), self)
        if dlg.exec(): new_lib = dlg.get_data(); self.settings["tool_library"] = new_lib; self.cfg_manager.save_config(self.settings); self.apply_settings_to_components(); self.status.showMessage("Tool Library Updated.")
    def update_dro(self, x, y, z, tool_id):
        self.lbl_x.setText(f"X  {x:.3f}"); self.lbl_y.setText(f"Y  {y:.3f}"); self.lbl_z.setText(f"Z  {z:.3f}")
        self.lbl_tool_t.setText(f"T{tool_id}"); dia = self.settings["tool_library"].get(str(tool_id), 10.0); self.lbl_tool_dia.setText(f"Dia: {dia:.1f} mm")
    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec(): new_data = dlg.get_data(); self.settings.update(new_data); self.cfg_manager.save_config(self.settings); self.apply_settings_to_components(); self.process_gcode(); self.status.showMessage("Preferences Saved.")
    def apply_settings_to_components(self):
        self.gl_widget.machine_size = [self.settings['machine_size_x'], self.settings['machine_size_y'], self.settings['machine_size_z']]; self.parser.set_rapid_feed(self.settings['rapid_feed'])
        if "tool_library" in self.settings: self.gl_widget.set_tool_library(self.settings["tool_library"])
        self.gl_widget.update()
    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing: self.btn_play.setText("⏸ Pause"); self.anim_timer.start(30); 
        else: self.btn_play.setText("▶ Play"); self.anim_timer.stop()
        if self.current_anim_dist >= self.parser.total_length: self.current_anim_dist = 0
    def on_slider_move(self, val):
        if self.parser.total_length > 0: self.current_anim_dist = (val / 1000.0) * self.parser.total_length; self.update_tool_visuals()
    def animate_step(self):
        if self.parser.total_length == 0: return
        step = 5.0 * self.anim_speed; self.current_anim_dist += step
        if self.current_anim_dist >= self.parser.total_length: self.current_anim_dist = self.parser.total_length; self.toggle_play() 
        percentage = (self.current_anim_dist / self.parser.total_length) * 1000; self.slider.setValue(int(percentage)); self.update_tool_visuals()
    def update_tool_visuals(self):
        pos, t_id, line_idx = self.get_pos_and_tool_at_distance(self.current_anim_dist)
        self.gl_widget.set_tool_state(pos, t_id)
        if line_idx != -1 and self.is_playing:
            cursor = QTextCursor(self.editor.document().findBlockByNumber(line_idx)); self.editor.setTextCursor(cursor); self.editor.centerCursor()
    def get_pos_and_tool_at_distance(self, target_dist):
        path = self.gl_widget.path_data
        if not path: return (0,0,0), 1, -1
        for seg in path:
            if target_dist >= seg.get('dist_start', 0) and target_dist <= seg.get('dist_end', 0):
                len_seg = seg['dist_end'] - seg['dist_start']; t_id = seg.get('tool', 1); line = seg.get('source_line', -1)
                if len_seg == 0: return seg['start'], t_id, line
                ratio = (target_dist - seg['dist_start']) / len_seg
                x = seg['start'][0] + (seg['end'][0] - seg['start'][0]) * ratio; y = seg['start'][1] + (seg['end'][1] - seg['start'][1]) * ratio; z = seg['start'][2] + (seg['end'][2] - seg['start'][2]) * ratio
                return (x, y, z), t_id, line
        last = path[-1]; return last['end'], last.get('tool', 1), last.get('source_line', -1)
    def apply_theme(self):
        if self.is_dark: self.setStyleSheet("QMainWindow { background-color: #2b2b2b; } QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e42; } QMenuBar { background-color: #333333; color: white; border-bottom: 1px solid #444; } QMenuBar::item:selected { background-color: #505050; } QMenu { background-color: #252526; color: white; border: 1px solid #454545; } QToolBar { background-color: #333333; border-bottom: 2px solid #007acc; spacing: 5px; } QStatusBar { background-color: #007acc; color: white; } QLabel { color: white; } QPushButton { background-color: #007acc; color: white; border: none; padding: 5px; }")
        else: self.setStyleSheet("")
        if hasattr(self, 'gl_widget'): self.gl_widget.set_theme(self.is_dark)
    def toggle_theme(self): self.is_dark = not self.is_dark; self.settings['theme'] = 'dark' if self.is_dark else 'light'; self.cfg_manager.save_config(self.settings); self.apply_theme()
    def process_gcode(self):
        text = self.editor.toPlainText(); lines = self.parser.parse(text); self.gl_widget.update_path(lines)
        m = int(self.parser.estimated_time); s = int((self.parser.estimated_time - m) * 60); self.time_label.setText(f"Est. Time: {m:02d}:{s:02d}")
    def on_cursor_move(self): current_line_idx = self.editor.textCursor().blockNumber(); self.gl_widget.set_highlight(current_line_idx)
    def load_file_from_path(self, filepath):
        try:
            with open(filepath, 'r') as f: self.editor.setPlainText(f.read()); self.process_gcode(); self.status.showMessage(f"Loaded: {filepath}")
        except Exception as e: QMessageBox.critical(self, "Error", f"Cannot open file:\n{str(e)}")
    def open_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open", "", "NC (*.nc *.gcode);;All (*)")
        if f: self.load_file_from_path(f)
    def save_file(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save", "", "NC (*.nc);;All (*)")
        if f: 
            with open(f, 'w') as file: file.write(self.editor.toPlainText())
    def remove_line_numbers(self): text = self.editor.toPlainText(); new_text = re.sub(r'(?m)^N\d+\s*', '', text, flags=re.MULTILINE); self.editor.setPlainText(new_text)
    def renumber_advanced(self):
        start, ok1 = QInputDialog.getInt(self, "Renumber", "Start:", 10, 1, 10000)
        if ok1:
            step, ok2 = QInputDialog.getInt(self, "Renumber", "Step:", 10, 1, 1000)
            if ok2:
                text = self.editor.toPlainText(); lines = text.split('\n'); new_lines = []; counter = start
                for line in lines:
                    line = line.strip()
                    if not line: new_lines.append(""); continue
                    clean_line = re.sub(r'^N\d+\s*', '', line, flags=re.IGNORECASE); new_lines.append(f"N{counter} {clean_line}"); counter += step
                self.editor.setPlainText('\n'.join(new_lines))
    def schedule_update(self): self.update_timer.start(500)
    def toggle_limits(self): self.gl_widget.show_limits = not self.gl_widget.show_limits; self.gl_widget.update()
    def set_limits(self): self.open_settings()
    def apply_transform(self, mode):
        txt = self.editor.toPlainText()
        if mode == "mirror_x": new = self.transformer.mirror_g2_g3(self.transformer.modify_values(txt, multipliers={'X':-1, 'I':-1}), True)
        elif mode == "mirror_y": new = self.transformer.mirror_g2_g3(self.transformer.modify_values(txt, multipliers={'Y':-1, 'J':-1}), True)
        elif mode == "inch_to_mm": new = self.transformer.modify_values(txt, multipliers={'X':25.4, 'Y':25.4, 'Z':25.4, 'I':25.4, 'J':25.4})
        elif mode == "mm_to_inch": f=1/25.4; new = self.transformer.modify_values(txt, multipliers={'X':f, 'Y':f, 'Z':f, 'I':f, 'J':f})
        elif mode == "swap_axes_maho": new = self.transformer.swap_axes_custom(txt)
        self.editor.setPlainText(new)
    def open_shift_dialog(self):
        x, ok = QInputDialog.getDouble(self, "Shift", "Offset X:", 0, -9999, 9999, 3)
        if ok: 
            y, ok = QInputDialog.getDouble(self, "Shift", "Offset Y:", 0, -9999, 9999, 3)
            if ok: z, ok = QInputDialog.getDouble(self, "Shift", "Offset Z:", 0, -9999, 9999, 3); 
            if ok: self.editor.setPlainText(self.transformer.modify_values(self.editor.toPlainText(), offsets={'X':x, 'Y':y, 'Z':z}))
    def load_demo(self):
        demo = """(DEMO: Polished v1.5)
(Drag & Drop files here!)
N10 G0 G90 G17 Z50
N20 T1 M6
N30 G0 X0 Y0 S1000 M3
N40 G0 Z5
N50 G1 Z-2 F300
N60 G1 X50 Y0
N70 G3 X50 Y50 I0 J25
N80 G1 X0 Y50
N90 G1 X0 Y0
N100 G0 Z50 M5"""
        self.editor.setPlainText(demo)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())