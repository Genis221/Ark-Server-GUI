import sys
import os
import json
import uuid
import subprocess
import datetime
import zipfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QAction,
    QGroupBox, QCheckBox, QTimeEdit
)
from PyQt5.QtCore import Qt, QTimer, QTime, QDate

# ---------------------------
# 1) ConfigManager
# ---------------------------
class ConfigManager:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.data = {"servers": []}
        self.load_config()

    def load_config(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {"servers": []}

    def save_config(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)

# ---------------------------
# 2) ServerTab
# ---------------------------
class ServerTab(QWidget):
    """
    Layout:
      - QVBoxLayout (top-aligned)
      - Row 0: Horizontal box (Profile label, text field, Import, Start, RCON, Backup), left-aligned
      - Row 1: Installed Version & Installation Location
      - Row 2: Status, Availability, Players, Upgrade/Verify
      - Row 3: Automatic Management (Scheduler) group box
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_folder = ""
        self.server_process = None

        # We'll store whether we've done today's shutdown
        self.shutdown_triggered_today = False

        self.init_ui()
        self.init_scheduler_timer()

    def init_ui(self):
        # Outer vertical layout (aligned top)
        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(10, 10, 10, 10)
        outerLayout.setSpacing(5)
        outerLayout.setAlignment(Qt.AlignTop)

        # Inner grid for rows 1 and 2
        self.grid = QGridLayout()
        self.grid.setSpacing(5)

        # Add the grid to the outer layout
        outerLayout.addLayout(self.grid)

        #
        # Row 0: Horizontal layout for Profile & buttons, left-aligned
        #
        row0Layout = QHBoxLayout()
        row0Layout.setSpacing(5)

        label_profile = QLabel("Profile:")
        self.edit_profile = QLineEdit("New Server")

        # Buttons: Import, Start, RCON, and now Backup
        self.button_import = QPushButton("Import")
        self.button_start = QPushButton("Start")
        self.button_rcon = QPushButton("RCON")
        self.button_backup = QPushButton("Backup")

        # Add them all in one row
        row0Layout.addWidget(label_profile)
        row0Layout.addWidget(self.edit_profile)
        row0Layout.addWidget(self.button_import)
        row0Layout.addWidget(self.button_start)
        row0Layout.addWidget(self.button_rcon)
        row0Layout.addWidget(self.button_backup)

        # Place row0Layout in row 0 of the grid, spanning all columns
        self.grid.addLayout(row0Layout, 0, 0, 1, -1, alignment=Qt.AlignLeft)

        #
        # Row 1: Installed Version & Installation Location
        #
        label_version = QLabel("Installed Version:")
        self.edit_version = QLineEdit("")
        self.edit_version.setReadOnly(True)

        label_install = QLabel("Installation Location:")
        self.edit_install = QLineEdit("")
        self.edit_install.setReadOnly(True)
        self.button_set_loc = QPushButton("Set Location")

        self.grid.addWidget(label_version, 1, 0)
        self.grid.addWidget(self.edit_version, 1, 1, 1, 2)
        self.grid.addWidget(label_install, 1, 3)
        self.grid.addWidget(self.edit_install, 1, 4, 1, 3)
        self.grid.addWidget(self.button_set_loc, 1, 7)

        #
        # Row 2: Status, Availability, Players, Upgrade/Verify
        #
        self.label_status = QLabel("Status: Stopped")
        self.label_availability = QLabel("Availability: Unavailable")
        self.label_players = QLabel("Players: 0 / 25")
        self.button_upgrade = QPushButton("Upgrade / Verify")

        self.grid.addWidget(self.label_status,       2, 0, 1, 2)
        self.grid.addWidget(self.label_availability, 2, 2, 1, 3)
        self.grid.addWidget(self.label_players,      2, 5, 1, 2)
        self.grid.addWidget(self.button_upgrade,     2, 7)

        #
        # Row 3: Automatic Management (Scheduler)
        #
        self.scheduler_group = QGroupBox("Automatic Management")
        scheduler_layout = QVBoxLayout()
        self.scheduler_group.setLayout(scheduler_layout)

        # 3A: Row for day checkboxes
        days_layout = QHBoxLayout()
        self.shutdown_days = []
        for day in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]:
            cb = QCheckBox(day)
            days_layout.addWidget(cb)
            self.shutdown_days.append(cb)
        scheduler_layout.addLayout(days_layout)

        # 3B: Time + update/restart checkboxes
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Shutdown at:"))
        self.shutdown_time_edit = QTimeEdit()
        self.shutdown_time_edit.setDisplayFormat("HH:mm")
        self.shutdown_time_edit.setTime(QTime(8,0))  # default 08:00
        time_layout.addWidget(self.shutdown_time_edit)

        self.checkbox_perform_update = QCheckBox("Perform update")
        self.checkbox_then_restart = QCheckBox("Then restart")

        time_layout.addWidget(self.checkbox_perform_update)
        time_layout.addWidget(self.checkbox_then_restart)
        scheduler_layout.addLayout(time_layout)

        self.grid.addWidget(self.scheduler_group, 3, 0, 1, -1)

        # Connect buttons
        self.button_import.clicked.connect(self.import_server)
        self.button_start.clicked.connect(self.start_server)
        self.button_backup.clicked.connect(self.backup_saves)

    # -------------------------
    # Scheduler Timer
    # -------------------------
    def init_scheduler_timer(self):
        """Sets up a QTimer that checks every minute if it's time to shutdown/update/restart."""
        self.schedule_timer = QTimer(self)
        self.schedule_timer.setInterval(60_000)  # every 60 seconds
        self.schedule_timer.timeout.connect(self.check_scheduled_shutdown)
        self.schedule_timer.start()

    def check_scheduled_shutdown(self):
        """
        Checks if it's one of the selected days and the current time >= scheduled time.
        If so, triggers the 'shutdown' -> optional update -> optional restart.
        This is a placeholder logic. You might want a more robust approach.
        """
        if not self.server_folder:
            return  # no server to manage

        now = QTime.currentTime()
        current_day = QDate.currentDate().dayOfWeek()  # 1=Mon, 7=Sun

        # Map dayOfWeek to index in [Sun,Mon,Tue,Wed,Thu,Fri,Sat]
        # By default, QDate().dayOfWeek() => Monday=1, Sunday=7
        # We want [Sun=7, Mon=1, Tue=2 ...]
        # Let's define a small helper:
        def dayIndexToCheckBoxIndex(day_of_week):
            # Sunday=7 => index=0
            # Monday=1 => index=1
            # ...
            mapping = {7:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6}
            return mapping.get(day_of_week, -1)

        idx = dayIndexToCheckBoxIndex(current_day)
        if idx < 0:
            return

        # If today is not selected, reset the daily trigger
        if not self.shutdown_days[idx].isChecked():
            self.shutdown_triggered_today = False
            return

        # Check if time is >= user-specified shutdown time
        scheduled_time = self.shutdown_time_edit.time()
        if now.hour() == scheduled_time.hour() and now.minute() == scheduled_time.minute():
            # Only trigger once per day
            if not self.shutdown_triggered_today:
                self.shutdown_triggered_today = True
                self.perform_scheduled_actions()
        else:
            # If time has passed or not reached, we might reset if it's a new day
            # This is simplistic logic. If the time is already past for the day, it won't trigger again until next day
            pass

    def perform_scheduled_actions(self):
        """
        Placeholder logic for the actual scheduled actions:
          - Stop server
          - If "Perform update", do update
          - If "Then restart", start server
        """
        # 1) Stop server
        self.stop_server()

        # 2) If update checkbox is checked
        if self.checkbox_perform_update.isChecked():
            self.update_server()

        # 3) If restart checkbox is checked
        if self.checkbox_then_restart.isChecked():
            self.start_server()

        QMessageBox.information(self, "Scheduled Action", "Scheduled shutdown/update/restart complete.")

    def stop_server(self):
        """Placeholder for stopping the server. If you have a process handle, you can terminate it."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None
            self.label_status.setText("Status: Stopped")

    def update_server(self):
        """Placeholder for updating the server (SteamCMD logic or similar)."""
        # Real logic: run SteamCMD update, etc.
        QMessageBox.information(self, "Update Server", "Updating server... (placeholder)")

    # -------------------------
    # Backup Saves
    # -------------------------
    def backup_saves(self):
        """
        Backs up the server's 'ShooterGame/Saved' folder into a ZIP named with a timestamp,
        stored in a folder named <profile>_Backups
        """
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return

        saves_path = os.path.join(self.server_folder, "ShooterGame", "Saved")
        if not os.path.exists(saves_path):
            QMessageBox.warning(self, "No Saves Folder", f"Saves folder not found: {saves_path}")
            return

        profile_name = self.edit_profile.text()
        backups_folder = f"{profile_name}_Backups"
        if not os.path.exists(backups_folder):
            os.makedirs(backups_folder)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"{profile_name}_backup_{timestamp}.zip"
        zip_path = os.path.join(backups_folder, zip_name)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(saves_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=saves_path)
                        zipf.write(file_path, arcname=arcname)
            QMessageBox.information(self, "Backup Complete", f"Saved backup to {zip_path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", str(e))

    # -------------------------
    # Import / Start
    # -------------------------
    def import_server(self):
        folder = QFileDialog.getExistingDirectory(self, "Select ARK Server Folder")
        if folder:
            self.server_folder = folder
            self.edit_profile.setText(os.path.basename(folder))
            self.edit_install.setText(folder)
            self.edit_version.setText("358.24")  # Example placeholder

    def start_server(self):
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return
        exe = os.path.join(self.server_folder, "ShooterGame", "Binaries", "Win64", "ShooterGameServer.exe")
        if not os.path.exists(exe):
            QMessageBox.critical(self, "Error", "Server executable not found.")
            return
        try:
            self.server_process = subprocess.Popen([exe])
            self.label_status.setText("Status: Running")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------------
    # For Saving/Loading Config
    # -------------------------
    def get_server_info(self):
        """
        Return current server info, including scheduler settings,
        so it can be saved in config.json.
        """
        # Convert days to a list of booleans
        day_bools = [cb.isChecked() for cb in self.shutdown_days]
        return {
            "profile": self.edit_profile.text(),
            "folder": self.server_folder,
            "version": self.edit_version.text(),
            "install": self.edit_install.text(),
            # Scheduler
            "shutdown_days": day_bools,
            "shutdown_time": self.shutdown_time_edit.time().toString("HH:mm"),
            "perform_update": self.checkbox_perform_update.isChecked(),
            "then_restart": self.checkbox_then_restart.isChecked()
        }

    def set_server_info(self, info):
        """
        Load server info, including scheduler settings, from config.
        """
        self.edit_profile.setText(info.get("profile", "New Server"))
        self.server_folder = info.get("folder", "")
        self.edit_version.setText(info.get("version", ""))
        self.edit_install.setText(info.get("install", ""))

        # Scheduler
        day_bools = info.get("shutdown_days", [])
        for i, cb in enumerate(self.shutdown_days):
            if i < len(day_bools):
                cb.setChecked(day_bools[i])
        shutdown_str = info.get("shutdown_time", "08:00")
        h, m = shutdown_str.split(":")
        self.shutdown_time_edit.setTime(QTime(int(h), int(m)))
        self.checkbox_perform_update.setChecked(info.get("perform_update", False))
        self.checkbox_then_restart.setChecked(info.get("then_restart", False))

# ---------------------------
# 3) Main Window with Config + "Save All"
# ---------------------------
class ArkServerManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARK Server Manager")
        self.resize(1200, 700)

        self.config_manager = ConfigManager()

        # Light styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ebe7db;
            }
            QTabWidget::pane {
                background: #f2eee4;
                border: 1px solid #ccc;
            }
            QTabBar::tab {
                background: #dcd8cc;
                padding: 4px 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                font-weight: bold;
            }
            QLabel {
                font-size: 14px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ccc;
                padding: 3px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #bfbfbf;
                padding: 6px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        # Let the tab bar resize with text
        tab_bar = self.tabs.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(Qt.ElideNone)

        # "+" button
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedWidth(30)
        self.plus_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.plus_button, Qt.TopRightCorner)

        # Toolbar: "Save All"
        self.toolbar = self.addToolBar("Main Toolbar")
        save_action = QAction("Save All", self)
        save_action.triggered.connect(self.save_all_tabs)
        self.toolbar.addAction(save_action)

        # Load tabs from config or create one tab if empty
        self.load_tabs_from_config()

    def load_tabs_from_config(self):
        servers = self.config_manager.data.get("servers", [])
        if servers:
            for info in servers:
                new_tab = ServerTab()
                new_tab.set_server_info(info)
                index = self.tabs.addTab(new_tab, info.get("profile", "New Server"))
                # Sync tab name with Profile field
                new_tab.edit_profile.textChanged.connect(
                    lambda _, tab=new_tab: self.sync_tab_name(tab)
                )
            self.tabs.setCurrentIndex(0)
        else:
            self.add_new_tab()

    def add_new_tab(self):
        new_tab = ServerTab()
        index = self.tabs.addTab(new_tab, "New Server")
        self.tabs.setCurrentIndex(index)
        new_tab.edit_profile.textChanged.connect(
            lambda _, tab=new_tab: self.sync_tab_name(tab)
        )

    def sync_tab_name(self, tab):
        i = self.tabs.indexOf(tab)
        if i >= 0:
            self.tabs.setTabText(i, tab.edit_profile.text())

    def close_tab(self, index):
        if self.tabs.count() == 1:
            QMessageBox.warning(self, "Cannot Close", "At least one server tab must remain open.")
            return
        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)

    def save_all_tabs(self):
        servers = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            servers.append(tab.get_server_info())
        self.config_manager.data["servers"] = servers
        self.config_manager.save_config()
        QMessageBox.information(self, "Saved", "All server information saved to config.")

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArkServerManager()
    window.show()
    sys.exit(app.exec_())
