import sys
import os
import json
import subprocess
import datetime
import zipfile
import psutil
import requests
import zipfile
import datetime
import shutil
import time
import ctypes
import time
import glob
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QAction,
    QGroupBox, QCheckBox, QTimeEdit, QDialog, QVBoxLayout, QComboBox, QScrollArea, QFrame, QSizePolicy,
    QPlainTextEdit, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, QTime, QDate, QDateTime, QProcess, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QColor

# ---------------------------
# 1) Extra Important Rules
# ---------------------------

# Darker green and red (muted tones)
DARK_GREEN = QColor("#228B22")  # forest green
DARK_RED = QColor("#CE2029")    # dark red

class BackupWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, server_folder, backup_dest, profile_name, zip_path):
        super().__init__()
        self.server_folder = server_folder
        self.backup_dest = backup_dest
        self.profile_name = profile_name
        self.zip_path = zip_path

    def run(self):
        try:
            saved_folder = os.path.join(self.server_folder, "ShooterGame", "Saved", "SavedArks")
            with zipfile.ZipFile(self.zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(saved_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=saved_folder)
                        zipf.write(file_path, arcname=arcname)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

def update_session_name(ini_path, new_session_name):
    """
    Updates the 'SessionName=' line in GameUserSettings.ini with the provided new_session_name.
    """
    if not os.path.exists(ini_path):
        print(f"GameUserSettings.ini not found at: {ini_path}")
        return
    with open(ini_path, 'r') as f:
        lines = f.readlines()
    with open(ini_path, 'w') as f:
        for line in lines:
            if line.strip().startswith("SessionName="):
                f.write(f"SessionName={new_session_name}\n")
            else:
                f.write(line)

def get_ark_version_from_logs(server_folder):
    """
    Searches the newest log file in:
      <server_folder>/ShooterGame/Saved/Logs
    for a line like: "ARK Version: 61.74"
    and returns the version number (e.g., "61.74").
    Returns "Unknown" if no version is found.
    """
    logs_dir = os.path.join(server_folder, "ShooterGame", "Saved", "Logs")
    if not os.path.isdir(logs_dir):
        return "Unknown"
    # Find all .log files in the folder
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    if not log_files:
        return "Unknown"
    # Sort by modification time (newest first)
    log_files.sort(key=os.path.getmtime, reverse=True)
    newest_log = log_files[0]
    # Use a case-insensitive regex to capture version numbers
    pattern = re.compile(r"ARK Version:\s*([\d.]+)", re.IGNORECASE)
    try:
        with open(newest_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    return match.group(1)
    except Exception as e:
        print("Error reading log:", e)
    return "Unknown"

def add_firewall_rule(rule_name, protocol, port):
    """
    Adds a firewall rule only if it doesn't already exist.
    Returns True if rule exists or is added; False if adding fails.
    """
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )
        if "No rules match the specified criteria" not in result.stdout:
            print(f"[Firewall] Rule already exists: {rule_name} — Skipping")
            return True  # ✅ Exists = Success
    except Exception as e:
        print(f"[Firewall] Error checking rule: {rule_name} — {e}")
        return False

    try:
        subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=in", "action=allow", f"protocol={protocol}",
            f"localport={port}"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[Firewall] Successfully added: {rule_name}")
        return True  # ✅ Added = Success
    except subprocess.CalledProcessError:
        print(f"[Firewall] ❌ Failed to add: {rule_name} — Need Admin?")
        return False

def add_dynamic_firewall_rules(tab, profile, launch_args, game_user_settings_ini_path):
    # Extract the primary port from launch arguments
    main_port_match = re.search(r"Port=(\d+)", launch_args)
    if main_port_match:
        main_port = int(main_port_match.group(1))
    else:
        print("Main port not found in launch arguments.")
        return

    # Extract the QueryPort value from launch arguments
    query_port_match = re.search(r"QueryPort=(\d+)", launch_args)
    query_port = int(query_port_match.group(1)) if query_port_match else None

    # Calculate the additional port as main_port + 1
    extra_port = main_port + 1

    # Read GameUserSettings.ini to extract the RCONPort
    rcon_port = None
    try:
        with open(game_user_settings_ini_path, "r") as ini_file:
            for line in ini_file:
                if "RCONPort=" in line:
                    parts = line.strip().split("=")
                    if len(parts) == 2 and parts[1].isdigit():
                        rcon_port = int(parts[1])
                        break
    except Exception as e:
        print("Error reading GameUserSettings.ini:", e)

    # List of ports to add
    ports = [main_port, extra_port]
    if query_port is not None:
        ports.append(query_port)
    if rcon_port is not None:
        ports.append(rcon_port)

    # Add rules for both TCP and UDP for each port
    success = True
    
    for port in ports:
        for proto in ["TCP", "UDP"]:
            rule_name = f"Ark Server: {profile} {proto} Port {port}"
            added = add_firewall_rule(rule_name, proto, port)
            if not added:
                success = False
    
    # Update the UI label after all attempts
    if hasattr(tab, "label_firewall"):
        if success:
            tab.label_firewall.setText("Firewall Status: Good")
            tab.label_firewall.setStyleSheet("color: green;")
        else:
            tab.label_firewall.setText("Firewall Status: Bad – Need Admin Permission")
            tab.label_firewall.setStyleSheet("color: red;")

def copy_server_log_on_stop(server_folder, profile_name, log_dest_folder):
    """
    Copies the ShooterGame.log from the Saved\Logs folder, renames it using the profile name and timestamp,
    and saves it in a profile-specific folder at the user-defined log destination.
    """
    if not server_folder or not log_dest_folder:
        print("[ERROR] Missing server folder or log destination.")
        return

    # Path to the current ShooterGame log file
    log_file_path = os.path.join(server_folder, "ShooterGame", "Saved", "Logs", "ShooterGame.log")
    if not os.path.exists(log_file_path):
        print(f"[ERROR] Log file not found: {log_file_path}")
        return

    # Format profile name and build destination folder
    profile_clean = profile_name.strip()
    subfolder_name = profile_clean.replace(" ", "_") + "_Game_Logs"
    full_dest_folder = os.path.join(log_dest_folder, profile_clean, subfolder_name)
    
    os.makedirs(full_dest_folder, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{profile_name.strip().replace(' ', '_')}_log_{timestamp}.log"
    dest_path = os.path.join(full_dest_folder, log_filename)

    try:
        shutil.copyfile(log_file_path, dest_path)
        print(f"[INFO] Log saved to: {dest_path}")
    except Exception as e:
        print(f"[ERROR] Failed to copy log file: {e}")

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
      - Row 4: Collapsible "Server Configuration" Section
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.firewall_status = "Unknown"  # Can be: Good, Bad, Unknown
        self.server_folder = ""
        self.server_process = None

        # We'll store whether we've done today's shutdown
        self.shutdown_triggered_today = False

        self.init_ui()
        self.init_scheduler_timer()
        self.init_auto_start_timer()

    def verify_firewall_status(self):
        """
        Checks all firewall rules again and re-attempts to add them if needed.
        Updates the label and status tracker.
        """
        profile = self.edit_profile.text()
        launch_args = self.edit_launch_args.text()
        ini_path = os.path.join(self.edit_install.text(), "ShooterGame", "Saved", "Config", "WindowsServer", "GameUserSettings.ini")
    
        # Extract ports
        main_port = int(re.search(r"Port=(\d+)", launch_args).group(1)) if "Port=" in launch_args else None
        query_port = int(re.search(r"QueryPort=(\d+)", launch_args).group(1)) if "QueryPort=" in launch_args else None
        extra_port = main_port + 1 if main_port else None
    
        # Try to get RCON port from file
        rcon_port = None
        try:
            with open(ini_path, "r") as f:
                for line in f:
                    if "RCONPort=" in line:
                        rcon_port = int(line.strip().split("=")[1])
                        break
        except:
            pass
    
        ports = [p for p in [main_port, extra_port, query_port, rcon_port] if p]
    
        success = True
        for port in ports:
            for proto in ["TCP", "UDP"]:
                rule_name = f"Ark Server: {profile} {proto} Port {port}"
                added = add_firewall_rule(rule_name, proto, port)
                if not added:
                    success = False
    
        # Update status and UI
        if success:
            self.label_firewall.setText("Firewall Status: Good")
            self.label_firewall.setStyleSheet("color: #006400;")
            self.firewall_status = "Good"
        else:
            self.label_firewall.setText("Firewall Status: Bad – Need Admin Permission")
            self.label_firewall.setStyleSheet("color: red;")
            self.firewall_status = "Bad"

    def update_tab_color(self, is_running: bool):
        """
        Changes the tab color to darker green (online) or darker red (offline).
        """
        main_window = self.window()
        if isinstance(main_window, QMainWindow) and hasattr(main_window, 'tabs'):
            tab_index = main_window.tabs.indexOf(self)
            if tab_index >= 0:
                color = QColor("#228B22") if is_running else QColor("#CE2029")
                main_window.tabs.tabBar().setTabTextColor(tab_index, color)

    
    def browse_backup_destination(self):
        """
        Opens a folder picker dialog for selecting a backup destination,
        then stores it in self.edit_backup_dest.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Destination")
        if folder:
            self.edit_backup_dest.setText(folder)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # ---------------------
        # Fixed Header Layout
        # ---------------------
        self.header_layout = QGridLayout()
        self.header_layout.setSpacing(5)
        main_layout.addLayout(self.header_layout)
    
        #
        # 1) Put rows 0–4 (everything ABOVE the scroll area) in self.header_layout
        #
    
        # Row 0: Profile & buttons
        row0Layout = QHBoxLayout()
        row0Layout.setSpacing(5)
    
        label_profile = QLabel("Profile:")
        self.edit_profile = QLineEdit("New Server")
    
        self.button_start = QPushButton("Start")

    
        # 1) Let the Start button expand if there's space...
        self.button_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # 2) ...but cap its width so it doesn't go "past the red line."
        self.button_start.setMaximumWidth(143)
    
        row0Layout.addWidget(label_profile)
        row0Layout.addWidget(self.edit_profile)
        row0Layout.addWidget(self.button_start)

    
        self.button_start.setStyleSheet("background-color: green; color: white;")
    
        # Keep the row left-aligned; the maxWidth ensures Start doesn't overshoot
        self.header_layout.addLayout(row0Layout, 0, 0, 1, 8, alignment=Qt.AlignLeft)
    
        # Row 1: Installed Version & Installation Location
        label_version = QLabel("Installed Version:")
        self.edit_version = QLineEdit("")
        self.edit_version.setReadOnly(True)
    
        label_install = QLabel("Installation Location:")
        self.edit_install = QLineEdit("")
        self.edit_install.setReadOnly(True)
        self.button_set_loc = QPushButton("Set Location")
        self.button_set_loc.clicked.connect(self.set_install_location)  
    
        self.header_layout.addWidget(label_version, 1, 0)
        self.header_layout.addWidget(self.edit_version, 1, 1, 1, 2)
        self.header_layout.addWidget(label_install, 1, 3)
        self.header_layout.addWidget(self.edit_install, 1, 4, 1, 3)
        self.header_layout.addWidget(self.button_set_loc, 1, 7)
    
        # Row 2: SteamCMD Location + Browse + Download
        label_steamcmd = QLabel("SteamCMD Location:")
        self.edit_steamcmd = QLineEdit("")
        self.button_browse_steamcmd = QPushButton("Browse")
        self.button_download_steamcmd = QPushButton("Download SteamCMD")
        self.button_download_steamcmd.clicked.connect(self.download_steamcmd)
        self.button_browse_steamcmd.clicked.connect(self.browse_steamcmd_location)
    
        self.header_layout.addWidget(label_steamcmd, 2, 0)
        self.header_layout.addWidget(self.edit_steamcmd, 2, 1, 1, 3)
        self.header_layout.addWidget(self.button_browse_steamcmd, 2, 4)
        self.header_layout.addWidget(self.button_download_steamcmd, 2, 5)
    
        # Row 3: Command Line Launch Arguments
        label_launch_args = QLabel("Launch Arguments:")
        self.edit_launch_args = QLineEdit()
        self.header_layout.addWidget(label_launch_args, 3, 0)
        self.header_layout.addWidget(self.edit_launch_args, 3, 1, 1, 6)
    
        # Row 4: Status, Availability, Players, Upgrade/Verify
        self.label_status = QLabel("Status: Stopped")
        self.label_firewall = QLabel("Firewall Status: Not Checked")
        self.label_availability = QLabel("Availability: Offline")
        self.label_players = QLabel("Players: 0 / 25")
        self.button_upgrade = QPushButton("Update / Verify")
    
        status_layout = QVBoxLayout()
        status_layout.addWidget(self.label_status)
        status_layout.addWidget(self.label_firewall)
        self.header_layout.addLayout(status_layout, 4, 0, 1, 2)
        self.header_layout.addWidget(self.label_availability, 4, 2, 1, 3)
        self.header_layout.addWidget(self.label_players,      4, 5, 1, 2)
        self.header_layout.addWidget(self.button_upgrade,     4, 7)

        # Create the RCON button here so we can add it to row 4
        self.button_rcon = QPushButton("RCON")

            # Put RCON at column 6, so it's just left of "Update / Verify" (column 7)
        self.header_layout.addWidget(self.button_rcon,        3, 7)
        self.header_layout.addWidget(self.button_upgrade,     4, 7)
        
        #
        # 2) Create the scrollable area for everything BELOW
        #
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
    
        scroll_content = QWidget()
        self.scroll_area.setWidget(scroll_content)
    
        # Use a QVBoxLayout for the scrollable content
        self.scroll_layout = QVBoxLayout(scroll_content)
    
        # Finally, add the scroll area to the main layout
        main_layout.addWidget(self.scroll_area)
    
        #
        # 3) Place Automatic Start and Automatic Shutdown inside the scroll_layout
        #
    
        # --- Automatic Start ---
        self.auto_start_group = QGroupBox("Automatic Start")
        auto_start_layout = QVBoxLayout()
        self.auto_start_group.setLayout(auto_start_layout)
    
        # Days of the week
        auto_days_layout = QHBoxLayout()
        self.auto_start_days = []
        for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            cb = QCheckBox(day)
            auto_days_layout.addWidget(cb)
            self.auto_start_days.append(cb)
        auto_start_layout.addLayout(auto_days_layout)
    
        # Start Time and optional update
        auto_time_layout = QHBoxLayout()
        auto_time_layout.setAlignment(Qt.AlignLeft)  # shift everything left
        auto_time_layout.addWidget(QLabel("Start Server at:"))
    
        self.auto_start_time_edit = QTimeEdit()
        self.auto_start_time_edit.setDisplayFormat("hh:mm AP")
        self.auto_start_time_edit.setTime(QTime(9, 0))
        self.auto_start_time_edit.setFixedWidth(180)
        auto_time_layout.addWidget(self.auto_start_time_edit)
    
        self.checkbox_auto_start_update = QCheckBox("Perform update (Prior to Server Starting)")
        auto_time_layout.addWidget(self.checkbox_auto_start_update)
        auto_start_layout.addLayout(auto_time_layout)
    
        self.scroll_layout.addWidget(self.auto_start_group)
    
        # --- Automatic Shutdown ---
        self.scheduler_group = QGroupBox("Automatic Shutdown / Restart")
        scheduler_layout = QVBoxLayout()
        self.scheduler_group.setLayout(scheduler_layout)
    
        days_layout = QHBoxLayout()
        self.shutdown_days = []
        for day in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]:
            cb = QCheckBox(day)
            days_layout.addWidget(cb)
            self.shutdown_days.append(cb)
        scheduler_layout.addLayout(days_layout)
    
        time_layout = QHBoxLayout()
        time_layout.setAlignment(Qt.AlignLeft)  # shift everything left
        time_layout.addWidget(QLabel("Shutdown at:"))
    
        self.shutdown_time_edit = QTimeEdit()
        self.shutdown_time_edit.setDisplayFormat("hh:mm AP")
        self.shutdown_time_edit.setTime(QTime(8, 0))
        self.shutdown_time_edit.setFixedWidth(180)
        time_layout.addWidget(self.shutdown_time_edit)
    
        self.checkbox_perform_update = QCheckBox("Perform update")
        self.checkbox_then_restart = QCheckBox("Then restart")
        time_layout.addWidget(self.checkbox_perform_update)
        time_layout.addWidget(self.checkbox_then_restart)
    
        scheduler_layout.addLayout(time_layout)
    
        self.scroll_layout.addWidget(self.scheduler_group)
    
        # Row 6: Server Configuration Collapsible Section
        self.config_group = QGroupBox("Server Configuration")
        self.config_group.setCheckable(False)
    
        config_layout = QVBoxLayout()
        self.button_edit_game_ini = QPushButton("Edit Game")
        self.button_edit_gameusersettings_ini = QPushButton("Edit GameUserSettings")
    
        config_layout.addWidget(self.button_edit_game_ini)
        config_layout.addWidget(self.button_edit_gameusersettings_ini)
        self.config_group.setLayout(config_layout)
    
        self.scroll_layout.addWidget(self.config_group)
    
        self.button_edit_game_ini.clicked.connect(
            lambda: self.edit_config_file("Game.ini")
        )
        self.button_edit_gameusersettings_ini.clicked.connect(
            lambda: self.edit_config_file("GameUserSettings.ini")
        )
        
        # Row 7: Automatic Backup
        self.auto_backup_group = QGroupBox("Automatic World Save Backup")
        auto_backup_layout = QVBoxLayout()
        self.auto_backup_group.setLayout(auto_backup_layout)
    
        # Backup Interval
        interval_layout = QHBoxLayout()
        interval_layout.setAlignment(Qt.AlignLeft)  # shift everything left
        interval_layout.addWidget(QLabel("Backup Interval:"))
    
        self.backup_interval_combo = QComboBox()
        self.backup_interval_combo.addItems([
            "30 mins", "1 hr", "3 hrs", "6 hrs", "12 hrs", "24 hrs"
        ])
        self.backup_interval_combo.setFixedWidth(180)
        interval_layout.addWidget(self.backup_interval_combo)
        auto_backup_layout.addLayout(interval_layout)

        # Backup Folders to Keep
        backup_limit_layout = QHBoxLayout()
        backup_limit_layout.setAlignment(Qt.AlignLeft)
        backup_limit_layout.addWidget(QLabel("Backup Folders to Keep:"))
        
        self.backup_limit_combo = QComboBox()
        self.backup_limit_combo.addItems(["10", "20", "30", "40", "50", "100"])
        self.backup_limit_combo.setFixedWidth(100)
        backup_limit_layout.addWidget(self.backup_limit_combo)
        
        auto_backup_layout.addLayout(backup_limit_layout)
    
        # Backup Destination
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("Backup Folder:"))
        self.edit_backup_dest = QLineEdit("")
        dest_layout.addWidget(self.edit_backup_dest)
        self.button_browse_backup_dest = QPushButton("Browse")
        dest_layout.addWidget(self.button_browse_backup_dest)
        auto_backup_layout.addLayout(dest_layout)
        self.button_browse_backup_dest.clicked.connect(self.browse_backup_destination)
    
        # Manual Backup Button
        self.button_manual_backup = QPushButton("Backup Now")
        auto_backup_layout.addWidget(self.button_manual_backup)
        self.button_manual_backup.clicked.connect(self.perform_auto_backup)
    
        # Enable / Disable Auto Backup
        self.checkbox_enable_backup = QCheckBox("Enable Auto Backup")
        auto_backup_layout.addWidget(self.checkbox_enable_backup)
    
        self.scroll_layout.addWidget(self.auto_backup_group)
    
        # Row: Log Location
        label_log = QLabel("Game Log Location:")
        self.edit_log_location = QLineEdit("")
        self.button_browse_log = QPushButton("Browse")
        self.button_browse_log.clicked.connect(self.browse_log_location)
    
        self.scroll_layout.addWidget(label_log)
        self.scroll_layout.addWidget(self.edit_log_location)
        self.scroll_layout.addWidget(self.button_browse_log)
    
        # Row: Update Log Location
        label_update_log = QLabel("Update Log Location:")
        self.edit_update_log_location = QLineEdit("")
        self.button_browse_update_log = QPushButton("Browse")
        self.button_browse_update_log.clicked.connect(self.browse_update_log_location)
    
        self.scroll_layout.addWidget(label_update_log)
        self.scroll_layout.addWidget(self.edit_update_log_location)
        self.scroll_layout.addWidget(self.button_browse_update_log)
    
        #
        # Connect your signals/slots (start_server, upgrade_server, etc.)
        #
        self.button_start.clicked.connect(self.start_server)
        self.button_upgrade.clicked.connect(self.upgrade_server)
        # etc...
    
        self.last_backup_time = None  # Initialize the timer variable
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.check_auto_backup)
        self.backup_timer.start(60 * 1000)  # every 60 seconds

        self.firewall_timer = QTimer(self)
        self.firewall_timer.timeout.connect(self.verify_firewall_status)
        self.firewall_timer.start(5 * 60 * 1000)  # 5 minutes
        self.verify_firewall_status()

        
        
    def edit_config_file(self, filename):
        """
        Opens the selected server configuration file in Notepad++.
        If Notepad++ is not found, it defaults to regular Notepad.
        If the file does not exist, it prompts the user to create it.
        """

        server_path = self.edit_install.text().strip()
        if not server_path:
            QMessageBox.warning(self, "No Server Folder", "Please set or import a server first.")
            return
        
        config_path = os.path.join(server_path, "ShooterGame", "Saved", "Config", "WindowsServer", filename)

        # Ensure directories exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Check if the file exists
        if not os.path.exists(config_path):
            reply = QMessageBox.question(self, "File Not Found",
                                         f"{filename} does not exist. Would you like to create it?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                with open(config_path, "w") as f:
                    f.write(f"; {filename} - ARK Server Configuration\n")  # Create with a comment header

        # Debugging output
        print(f"Attempting to open: {config_path}")  # Debugging check

        # Ensure the file exists before attempting to open
        if os.path.exists(config_path):
            try:
                # Define Notepad++ path (Modify this path if your Notepad++ is installed elsewhere)
                notepad_plus_path = r"C:\Program Files\Notepad++\notepad++.exe"
                
                if os.path.exists(notepad_plus_path):
                    subprocess.Popen([notepad_plus_path, config_path])  # Open in Notepad++
                else:
                    QMessageBox.warning(self, "Notepad++ Not Found", "Notepad++ not found, opening in default Notepad.")
                    subprocess.Popen(["notepad.exe", config_path])  # Fallback to Notepad
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
        else:
            QMessageBox.critical(self, "Error", f"Could not locate {filename} even after creation.")

    def show_auto_closing_popup(self, message, timeout=10):
        """
        Shows a non-blocking popup with a countdown that auto-closes after X seconds.
        """
        self.popup = QMessageBox(self)
        self.popup.setWindowTitle("Scheduled Task Complete")
        self.remaining_seconds = timeout
        self.popup.setText(f"{message}\n\nThis message will close in {self.remaining_seconds} seconds.")
        self.popup.setStandardButtons(QMessageBox.NoButton)  # No close button
        self.popup.setModal(False)
        self.popup.show()

        self.popup_timer = QTimer(self)
        self.popup_timer.timeout.connect(lambda: self.update_popup_countdown(message))
        self.popup_timer.start(1000)

    def update_popup_countdown(self, message):
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.popup_timer.stop()
            self.popup.close()
        else:
            self.popup.setText(f"{message}\n\nThis message will close in {self.remaining_seconds} seconds.")

    def auto_dismiss_message(self, title, message, timeout=10):
         """
         Displays a message box that automatically closes after 'timeout' seconds.
         The countdown is displayed in the message.
         """
         dialog = QMessageBox(QMessageBox.Information, title, message)
         dialog.setStandardButtons(QMessageBox.NoButton)  # Remove OK button
     
         def update_message():
             nonlocal timeout
             if timeout > 0:
                 dialog.setText(f"{message}\nClosing in {timeout} seconds...")
                 timeout -= 1
             else:
                 dialog.done(0)  # Close message box
     
         timer = QTimer(self)
         timer.timeout.connect(update_message)
         timer.start(1000)  # Update every second
     
         dialog.exec_()
         timer.stop()  # Stop timer when done

    def update_ark_version_from_logs(self):
        """
        Reads the newest log file for a line with "ARK Version:" and updates the version field.
        """
        version = get_ark_version_from_logs(self.server_folder)
        print("Parsed version from log:", version)  # For debugging
        self.edit_version.setText(version)

    def init_auto_backup_timer(self):
        """
        Sets up a QTimer that checks every minute whether it's time for an automatic backup.
        """
        self.last_backup_time = QDateTime.currentDateTime()  # Track last backup
        self.auto_backup_timer = QTimer(self)
        self.auto_backup_timer.setInterval(60_000)  # 1 minute
        self.auto_backup_timer.timeout.connect(self.check_auto_backup)
        self.auto_backup_timer.start()
    
    def check_auto_backup(self):
        if self.label_status.text() != "Status: Running":
            print("[AutoBackup] Skipping backup – server is not running.")
            return
    
        if not self.checkbox_enable_backup.isChecked():
            return
    
        # 2. Ensure we have a backup interval
        selected = self.backup_interval_combo.currentText().strip()
        interval_minutes = {
            "30 mins": 30,
            "1 hr": 60,
            "3 hrs": 180,
            "6 hrs": 360,
            "12 hrs": 720,
            "24 hrs": 1440
        }.get(selected, None)
    
        if interval_minutes is None:
            print("[AutoBackup] Invalid interval selected.")
            return
    
        # 3. Check if we have a last backup time stored
        now = QDateTime.currentDateTime()
    
        if not hasattr(self, 'last_backup_time') or self.last_backup_time is None:
            # First-time run — don’t trigger backup immediately
            self.last_backup_time = now
            print("[AutoBackup] Initialized backup timer.")
            return
    
        # 4. Compare elapsed time
        elapsed_secs = self.last_backup_time.secsTo(now)
        if elapsed_secs >= interval_minutes * 60:
            print(f"[AutoBackup] Performing backup. Elapsed: {elapsed_secs}s")
            self.perform_auto_backup()
            self.last_backup_time = now
        else:
            print(f"[AutoBackup] Not time yet. Elapsed: {elapsed_secs}s")

    

    # -------------------------
    # Scheduler Timer
    # -------------------------

    def init_scheduler_timer(self):
        """Sets up a QTimer that checks every minute if it's time to shutdown/update/restart."""
        self.schedule_timer = QTimer(self)
        self.schedule_timer.setInterval(60_000)  # every 60 seconds
        self.schedule_timer.timeout.connect(self.check_scheduled_shutdown)
        self.schedule_timer.start()

    def init_auto_start_timer(self):
        self.auto_start_timer = QTimer(self)
        self.auto_start_timer.setInterval(60_000)  # 1 minute
        self.auto_start_timer.timeout.connect(self.check_auto_start)
        self.auto_start_timer.start()

    def check_auto_start(self):
        if not self.server_folder:
            return
    
        now = QTime.currentTime()
        current_day = QDate.currentDate().dayOfWeek()  # 1=Mon, 7=Sun
    
        # Map day index to checkbox list index (Sun=7 -> 0, Mon=1 -> 1, ...)
        index_map = {7: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
        idx = index_map.get(current_day, -1)
        if idx == -1 or not self.auto_start_days[idx].isChecked():
            return
    
        target_time = self.auto_start_time_edit.time()
        if now.hour() == target_time.hour() and now.minute() == target_time.minute():
            if not hasattr(self, 'auto_start_triggered_today') or not self.auto_start_triggered_today:
                self.auto_start_triggered_today = True
    
                if self.checkbox_auto_start_update.isChecked():
                    self.upgrade_server(auto_update=True, on_complete=lambda: QTimer.singleShot(5000, self.start_server))
                else:
                    self.start_server()
        else:
            self.auto_start_triggered_today = False

    def check_scheduled_shutdown(self):
        """
        Checks if today is selected and current time is within 2 minutes of the scheduled shutdown time.
        If so, triggers shutdown/update/restart once.
        """
        if not self.server_folder:
            return  # No server loaded
    
        now = QTime.currentTime()
        current_day = QDate.currentDate().dayOfWeek()  # 1 = Monday, 7 = Sunday
    
        # Map to checkbox index: [Sun, Mon, Tue, Wed, Thu, Fri, Sat]
        day_mapping = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 0}
        cb_index = day_mapping.get(current_day, -1)
    
        if cb_index < 0 or not self.shutdown_days[cb_index].isChecked():
            self.shutdown_triggered_today = False
            return
    
        scheduled = self.shutdown_time_edit.time()
    
        # Allow a 2-minute grace window (e.g., trigger if now is within [scheduled, scheduled+2min])
        if scheduled <= now <= scheduled.addSecs(120):
            if not self.shutdown_triggered_today:
                self.shutdown_triggered_today = False
                self.perform_scheduled_actions()
        else:
            # Reset trigger if time window has passed
            if now > scheduled.addSecs(120):
                self.shutdown_triggered_today = False

    def perform_scheduled_actions(self):
        """
        Executes the scheduled shutdown:
          1. Finds and terminates the correct ARK server process.
          2. Optionally updates the server.
          3. Optionally restarts the server after ensuring it's fully terminated.
        """
        if self.server_folder:
            exe_name = "ArkAscendedServer.exe"
            target_folder = os.path.normpath(self.server_folder)
        
            try:
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                    if proc.info['name'] == exe_name:
                        try:
                            exe_path = os.path.normpath(proc.info['exe']) if proc.info['exe'] else ""
                            if target_folder in exe_path:
                                proc.terminate()
                                proc.wait(timeout=5)
                                if proc.is_running():
                                    proc.kill()
        
                                # Reset tracking
                                self.server_process = None
                                self.server_pid = None
        
                                # Update UI
                                self.label_status.setText("Status: Stopped")
                                self.button_start.setText("Start")
                                self.button_start.setStyleSheet("background-color: green; color: white;")
        
                                msg = QMessageBox(self)
                                msg.setIcon(QMessageBox.Information)
                                msg.setWindowTitle("Scheduled Action")
                                profile_name = self.edit_profile.text()
                                msg.setText(f"{profile_name} is being updated. Please wait for it to finish updating...")
                                msg.setStandardButtons(QMessageBox.Ok)
                                msg.show()
        
                                QTimer.singleShot(10_000, msg.accept)
                                break
        
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
        
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Unexpected error while stopping the server: {str(e)}")
        

        def show_countdown_dialog(message):
            self.countdown = 10
            self.dialog = QMessageBox(self)
            self.dialog.setWindowTitle("Scheduled Action Complete")
            self.dialog.setText(f"{message}\n\nClosing in {self.countdown} seconds...")
            self.dialog.setStandardButtons(QMessageBox.Ok)
            self.dialog.setDefaultButton(QMessageBox.Ok)

            def update_dialog():
                self.countdown -= 1
                if self.countdown <= 0:
                    self.dialog.done(0)
                    self.auto_close_timer.stop()
                else:
                    self.dialog.setText(f"{message}\n\nClosing in {self.countdown} seconds...")

            self.auto_close_timer = QTimer()
            self.auto_close_timer.timeout.connect(update_dialog)
            self.auto_close_timer.start(1000)
            self.dialog.show()

        def finish_and_restart():
            if self.checkbox_then_restart.isChecked():
                self.start_server()

            show_countdown_dialog("Server has restarted.")

        def stop_then_update_then_restart():
            self.stop_server()

            # If update checkbox is checked, show a single update message
            if self.checkbox_perform_update.isChecked():
                is_auto_update = True
                if self.checkbox_then_restart.isChecked():
                    self.upgrade_server(is_auto_update, on_complete=finish_and_restart)
                else:
                    self.upgrade_server(is_auto_update, on_complete=lambda: show_countdown_dialog("Server has shut down and updated."))            
                
            else:
                show_countdown_dialog("Server has shut down.")

        stop_then_update_then_restart()

    def stop_server(self):
        """Placeholder for stopping the server. If you have a process handle, you can terminate it."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None
            self.label_status.setText("Status: Stopped")

        def save_log_on_stop(self):
            """
            Copies the latest ShooterGame log into the user-selected log folder,
            and names it with the profile name and timestamp.
            """
            if not self.server_folder or not self.edit_log_location.text().strip():
                print("[ERROR] Missing server folder or log destination.")
                return
        
            log_source_folder = os.path.join(self.server_folder, "ShooterGame", "Saved", "Logs")
            latest_log_path = os.path.join(log_source_folder, "ShooterGame.log")
        
            if not os.path.exists(latest_log_path):
                print(f"[ERROR] ShooterGame.log not found at {latest_log_path}")
                return
        
            profile = self.edit_profile.text().strip().replace(" ", "_")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{profile}_log_{timestamp}.log"
        
            log_dest_folder = os.path.join(self.edit_log_location.text().strip(), f"{profile}_Logs")
            os.makedirs(log_dest_folder, exist_ok=True)
        
            log_dest_path = os.path.join(log_dest_folder, log_filename)
        
            try:
                shutil.copyfile(latest_log_path, log_dest_path)
                print(f"[LOG SAVED] {log_dest_path}")
            except Exception as e:
                print(f"[ERROR] Failed to copy log: {e}")

    def upgrade_server(self, auto_update=False, on_complete=None):
        """
        Runs SteamCMD to install/update ARK server files while logging updates live.
        Ensures administrator privileges, logs output in a structured folder, and delays execution.
        Shows only auto-dismiss messages when auto_update is True.
        """
        
        steamcmd_path = self.edit_steamcmd.text()
        steamcmd_exe = os.path.join(steamcmd_path, "steamcmd.exe")
        if not os.path.exists(steamcmd_exe):
            if not auto_update:
                QMessageBox.critical(self, "Error", "SteamCMD.exe not found. Please set the correct path.")
            return
    
        server_path = self.edit_install.text()
        if not server_path:
            if not auto_update:
                QMessageBox.critical(self, "Error", "No installation path set.")
            return
    
        # Set status to "Updating" and update UI immediately.
        self.label_status.setText("Status: Updating")
        QApplication.processEvents()
        time.sleep(3)
    
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_name = self.edit_profile.text().strip()
        log_base_folder = self.edit_update_log_location.text().strip() or server_path
        profile_clean = self.edit_profile.text().strip()
        subfolder_name = profile_name + "_Update_Logs"
        update_log_folder = os.path.join(log_base_folder, profile_clean, subfolder_name)
        os.makedirs(update_log_folder, exist_ok=True)
        log_file_path = os.path.join(update_log_folder, f"update_log_{timestamp}.log")
    
        arguments = [
            "+login", "anonymous",
            "+force_install_dir", server_path,
            "+app_update", "2430930", "validate",
            "+quit"
        ]
    
        if not auto_update:
            self.auto_dismiss_message("Update Running", "The Ark Server Manager is Verifying Server files and will update if needed...", 10)
    
        terminalDialog = QDialog(self)
        profile_name = self.edit_profile.text().strip()
        terminalDialog.setWindowTitle(f"Updating {profile_name} Server")    
        terminalDialog.setWindowFlag(Qt.WindowCloseButtonHint, False)
        layout = QVBoxLayout(terminalDialog)
        terminalOutput = QPlainTextEdit(terminalDialog)
        terminalOutput.setReadOnly(True)
        layout.addWidget(terminalOutput)
        terminalDialog.resize(600, 400)
    
        log_file = open(log_file_path, "w")
    
        class UpdateWorker(QObject):
            output = pyqtSignal(str)
            finished = pyqtSignal()
            error = pyqtSignal(str)
    
            def run(self):
                try:
                    process = QProcess()
                    process.setProcessChannelMode(QProcess.MergedChannels)
                    process.setReadChannel(QProcess.StandardOutput)
    
                    def handle_output():
                        while process.bytesAvailable() > 0:
                            data = process.readAllStandardOutput().data().decode("utf-8")
                            if data:
                                self.output.emit(data)
    
                    process.readyRead.connect(handle_output)
    
                    def process_done(exitCode, exitStatus):
                        handle_output()
                        self.finished.emit()
    
                    process.finished.connect(process_done)
                    process.start(steamcmd_exe, arguments)
                    process.waitForFinished(-1)
    
                except Exception as e:
                    self.error.emit(str(e))
    
        self.update_thread = QThread(self)  # tied to ServerTab, won't auto-delete
        self.update_worker = UpdateWorker()
        self.update_worker.moveToThread(self.update_thread)
    
        def update_terminal_output(text):
            terminalOutput.appendPlainText(text)
            log_file.write(text)
            log_file.flush()
            QApplication.processEvents()
    
        def update_complete():
            log_file.close()
            terminalDialog.accept()
            self.label_status.setText("Status: Stopped")
            if auto_update:
                self.auto_dismiss_message("Update Complete", f"Update finished!\nLog saved:\n{log_file_path}", 10)
            else:
                self.auto_dismiss_message("Update Complete", f"ARK Server update finished successfully!\nLogs saved at:\n{log_file_path}", 10)
            if on_complete:
                on_complete()
            self.update_thread.quit()
            self.update_worker.deleteLater()
            self.update_thread.deleteLater()
    
        def update_error(err):
            log_file.close()
            terminalDialog.accept()
            QMessageBox.critical(self, "Update Error", err)
            self.label_status.setText("Status: Stopped")
            self.update_thread.quit()
            self.update_worker.deleteLater()
            self.update_thread.deleteLater()
    
        self.update_worker.output.connect(update_terminal_output)
        self.update_worker.finished.connect(update_complete)
        self.update_worker.error.connect(update_error)
    
        self.update_thread.started.connect(self.update_worker.run)
        self.update_thread.start()
        terminalDialog.setModal(False)
        terminalDialog.show()




    def find_real_ark_pid(self):
        """
        Looks at the process we launched. If it spawned children,
        and one is 'ArkAscendedServer.exe', store that child's PID.
        """
        if not self.server_process:
            return  # No process to inspect
    
        try:
            parent = psutil.Process(self.server_process.pid)
            children = parent.children(recursive=True)
            for c in children:
                if 'ArkAscendedServer.exe' in c.name():
                    self.server_pid = c.pid
                    print(f"[DEBUG] Found real ARK server child PID: {self.server_pid}")
                    return
            # If no child found, keep self.server_pid as the parent’s PID
        except Exception as e:
            print(f"[ERROR] Could not find child ARK PID: {e}")

    # -------------------------
    # Backup Saves
    # -------------------------

    def perform_auto_backup(self):
        """
        Zips the 'ShooterGame/Saved' folder into a timestamped ZIP
        and places it into a profile-named folder inside the user-chosen backup destination.
        This now runs in a thread to prevent UI freezing.
        """
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return
    
        backup_dest = self.edit_backup_dest.text().strip()
        if not backup_dest:
            QMessageBox.warning(self, "No Backup Destination", "Please select a backup folder.")
            return
    
        saved_folder = os.path.join(self.server_folder, "ShooterGame", "Saved", "SavedArks")
        if not os.path.exists(saved_folder):
            QMessageBox.warning(self, "Folder Missing", f"Cannot find: {saved_folder}")
            return
    
        profile_name = self.edit_profile.text().strip()
        profile_backup_dir = os.path.join(backup_dest, f"{profile_name} Backups")
        os.makedirs(profile_backup_dir, exist_ok=True)
    
        timestamp = datetime.datetime.now().strftime("%Y%m%d %H%M%S")
        zip_name = f"{profile_name} Backup {timestamp}.zip"
        zip_path = os.path.join(profile_backup_dir, zip_name)
    
        self.label_status.setText("Status: Running, Backing up")
        QApplication.processEvents()
    
        from PyQt5.QtCore import QObject, QThread, pyqtSignal
    
        class BackupWorker(QObject):
            finished = pyqtSignal()
            error = pyqtSignal(str)
    
            def run(self):
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(saved_folder):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, start=saved_folder)
                                zipf.write(file_path, arcname=arcname)
                    self.finished.emit()
                except Exception as e:
                    self.error.emit(str(e))
    
        self.backup_thread = QThread()
        self.backup_worker = BackupWorker()
        self.backup_worker.moveToThread(self.backup_thread)
    
        self.backup_worker.finished.connect(self.backup_thread.quit)
        self.backup_worker.finished.connect(self.backup_worker.deleteLater)
        self.backup_thread.finished.connect(self.backup_thread.deleteLater)
    
        def on_backup_complete():
            msg = QMessageBox(self)
            msg.setWindowTitle("Backup Complete")
            self.label_status.setText("Status: Running")
            QApplication.processEvents()
            msg.setText(f"Backup saved to:\n{zip_path}\n\nThis will close in 10 seconds...")
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.show()
    
            self.backup_countdown = 10
            def update_msg():
                self.backup_countdown -= 1
                if self.backup_countdown <= 0:
                    msg.done(0)
                    timer.stop()
                else:
                    msg.setText(f"Backup saved to:\n{zip_path}\n\nThis will close in {self.backup_countdown} seconds...")
    
            timer = QTimer(self)
            timer.timeout.connect(update_msg)
            timer.start(1000)
    
            try:
                max_backups = int(self.backup_limit_combo.currentText())
                backup_files = sorted(
                    [os.path.join(profile_backup_dir, f) for f in os.listdir(profile_backup_dir) if f.endswith(".zip")],
                    key=os.path.getctime
                )
                while len(backup_files) > max_backups:
                    to_delete = backup_files.pop(0)
                    os.remove(to_delete)
                    print(f"[AutoBackup] Deleted oldest backup: {to_delete}")
            except Exception as e:
                print(f"[AutoBackup] Cleanup error: {e}")
    
        def on_backup_error(msg):
            self.label_status.setText("Status: Running")
            QApplication.processEvents()
            QMessageBox.critical(self, "Backup Failed", msg)
    
        self.backup_worker.finished.connect(on_backup_complete)
        self.backup_worker.error.connect(on_backup_error)
    
        self.backup_thread.started.connect(self.backup_worker.run)
        self.backup_thread.start()


    def set_install_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder")
        if folder:
            self.edit_install.setText(folder)
            # Optionally, if the installation folder is meant to be the server folder:
            self.server_folder = folder

    # -------------------------
    # Import / Start
    # -------------------------

    def import_server(self):
        folder = QFileDialog.getExistingDirectory(self, "Select ARK Server Folder")
        if folder:
            self.server_folder = folder
            self.edit_profile.setText(os.path.basename(folder))
            self.edit_install.setText(folder)
    
            # Dynamically parse logs for Ark version
            version = get_ark_version_from_logs(folder)
            self.edit_version.setText(version)
   
    def start_server(self):
        """
        Starts the ARK server using ArkAscendedServer.exe and custom command-line arguments.
        If the server is already running, this function will stop it instead.
        """
        # If the server is already running, stop it
        if self.server_process is not None:
            self.stop_server()
            return
    
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return
    
        # Construct the correct path to ArkAscendedServer.exe
        exe_file = os.path.join(self.server_folder, "ShooterGame", "Binaries", "Win64", "ArkAscendedServer.exe")
    
        # Construct the path to GameUserSettings.ini
        ini_path = os.path.join(
            self.edit_install.text(),
            "ShooterGame", "Saved", "Config", "WindowsServer", "GameUserSettings.ini"
        )
        
        # Update the session name in the ini file to match the profile name
        update_session_name(ini_path, self.edit_profile.text())
        
        if not os.path.exists(exe_file):
            QMessageBox.critical(self, "Error", f"Server executable not found:\n{exe_file}")
            return
    
        # Get command-line arguments from the GUI textbox
        args = self.edit_launch_args.text().strip()
        full_command = f'"{exe_file}" {args}'
    
        try:
            # Start the server with command-line arguments
            self.server_process = subprocess.Popen(full_command, shell=True)
            self.server_pid = self.server_process.pid
    
            # Update UI
            self.label_status.setText("Status: Running")
            self.button_start.setText("Stop")
            self.button_start.setStyleSheet("background-color: red; color: white;")
            self.update_tab_color(is_running=True)
    
            # Add dynamic firewall rules.
            # Build the path to GameUserSettings.ini:
            game_user_settings_ini_path = os.path.join(
                self.edit_install.text(), "ShooterGame", "Saved", "Config", "WindowsServer", "GameUserSettings.ini"
            )
            if self.firewall_status != "Good":
                add_dynamic_firewall_rules(self, self.edit_profile.text(), self.edit_launch_args.text(), game_user_settings_ini_path)
            else:
                print("[Firewall] Skipping firewall rule check — already marked good.")

    
            # Give ARK a moment to write logs, then update the version
            QTimer.singleShot(15_000, self.update_ark_version_from_logs)
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start the server: {str(e)}")

    def stop_server(self):
        """
        Stops the ARK server process that matches this server tab.
        Only stops the server located in self.server_folder.
        """
        if not self.server_folder:
            return
    
        # Save logs first
        copy_server_log_on_stop(
            self.server_folder,
            self.edit_profile.text(),
            self.edit_log_location.text()
        )
    
        # Update GUI
        self.label_status.setText("Status: Stopped")
        self.button_start.setText("Start")
        self.button_start.setStyleSheet("background-color: green; color: white;")
        self.update_tab_color(is_running=False)
        QApplication.processEvents()
    
        exe_name = "ArkAscendedServer.exe"
        target_folder = os.path.normpath(self.server_folder)
    
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                if proc.info['name'] == exe_name:
                    try:
                        exe_path = os.path.normpath(proc.info['exe']) if proc.info['exe'] else ""
                        if target_folder in exe_path:
                            proc.terminate()
                            proc.wait(timeout=5)
                            if proc.is_running():
                                proc.kill()
                            print(f"[INFO] Stopped server: {exe_path}")
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
    
            self.server_process = None
            self.server_pid = None
    
        except Exception as e:
            print(f"[ERROR] Failed to stop server: {e}")


    def browse_steamcmd_location(self):
        """
        Opens a file dialog to allow the user to select the SteamCMD installation folder.
        Ensures only one dialog appears.
        """
        if hasattr(self, 'steamcmd_dialog_open') and self.steamcmd_dialog_open:
            return  # Prevents multiple popups
    
        self.steamcmd_dialog_open = True  # Lock to prevent re-triggering
        folder = QFileDialog.getExistingDirectory(self, "Select SteamCMD Folder")
        if folder:
            self.edit_steamcmd.setText(folder)  # Set the selected folder path
    
        self.steamcmd_dialog_open = False  # Unlock when finished

    def download_steamcmd(self):
        """
        Downloads SteamCMD zip from Valve's servers, extracts it, and sets the path.
        """
        url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        save_path = os.path.join(os.path.expanduser("~"), "Documents", "SteamCMD")
    
        if not os.path.exists(save_path):
            os.makedirs(save_path)  # Ensure the directory exists
    
        zip_path = os.path.join(save_path, "steamcmd.zip")
    
        try:
            # Download the file
            self.button_download_steamcmd.setText("Downloading...")
            response = requests.get(url, stream=True)
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
    
            # Extract the ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(save_path)
    
            os.remove(zip_path)  # Delete the ZIP after extraction
            self.edit_steamcmd.setText(save_path)  # Set the extracted path
    
            QMessageBox.information(self, "Download Complete", f"SteamCMD downloaded to: {save_path}")
            self.button_download_steamcmd.setText("Download SteamCMD")
    
        except Exception as e:
            QMessageBox.critical(self, "Download Failed", str(e))
            self.button_download_steamcmd.setText("Download SteamCMD")

    def browse_log_location(self):
        """
        Opens a QFileDialog for the user to choose the log destination folder.
        Sets the chosen path in the log location QLineEdit.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Log Folder")
        if folder:
            self.edit_log_location.setText(folder)

    def browse_update_log_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Update Log Folder")
        if folder:
            self.edit_update_log_location.setText(folder)
    
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
            "steamcmd": self.edit_steamcmd.text(),
            "launch_args": self.edit_launch_args.text(),
            "autostart_days": [cb.isChecked() for cb in self.auto_start_days],
            "autostart_time": self.auto_start_time_edit.time().toString("HH:mm"),
            "autostart_update": self.checkbox_auto_start_update.isChecked(),
            "shutdown_days": day_bools,
            "shutdown_time": self.shutdown_time_edit.time().toString("HH:mm"),
            "perform_update": self.checkbox_perform_update.isChecked(),
            "then_restart": self.checkbox_then_restart.isChecked(),
            "auto_backup_enabled": self.checkbox_enable_backup.isChecked(),
            "auto_backup_interval": self.backup_interval_combo.currentText(),
            "auto_backup_dest": self.edit_backup_dest.text(),
            "backup_limit": self.backup_limit_combo.currentText(),
            "log_location": self.edit_log_location.text(),
            "update_log_location": self.edit_update_log_location.text(),
        }

    def set_server_info(self, info):
        """
        Load server info, including scheduler settings, from config.
        """
        self.edit_profile.setText(info.get("profile", "New Server"))
        self.server_folder = info.get("folder", "")
        self.edit_version.setText(info.get("version", ""))
        self.edit_install.setText(info.get("install", ""))
        self.edit_steamcmd.setText(info.get("steamcmd", ""))  # <-- Restore SteamCMD path
        self.edit_launch_args.setText(info.get("launch_args", ""))
        self.checkbox_enable_backup.setChecked(info.get("auto_backup_enabled", False))
        self.backup_interval_combo.setCurrentText(info.get("auto_backup_interval", "30 mins"))
        self.edit_backup_dest.setText(info.get("auto_backup_dest", ""))
        self.backup_limit_combo.setCurrentText(info.get("backup_limit", "10"))
        self.edit_log_location.setText(info.get("log_location", ""))
        self.edit_update_log_location.setText(info.get("update_log_location", ""))

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

        # Auto Start
        autostart_bools = info.get("autostart_days", [])
        for i, cb in enumerate(self.auto_start_days):
            if i < len(autostart_bools):
                cb.setChecked(autostart_bools[i])
        
        autostart_str = info.get("autostart_time", "08:00")
        h, m = autostart_str.split(":")
        self.auto_start_time_edit.setTime(QTime(int(h), int(m)))
        
        self.checkbox_auto_start_update.setChecked(info.get("autostart_update", False))

# ---------------------------
# 3) Main Window with Config + "Save All"
# ---------------------------

class ArkServerManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ark: Survival Ascended Server Manager")
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
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setMovable(True)  # Optional: allow dragging tabs

        
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 4px 8px;
                margin: 1px;
                font-size: 10px;
                max-width: 150px;  /* Optional: enforce width cap */
            }
            QTabBar::tab:selected {
                font-weight: bold;
            }
        """)



        # "+" button
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedWidth(30)
        self.plus_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.plus_button, Qt.TopRightCorner)

        # Toolbar: "Save All"
        self.toolbar = self.addToolBar("Main Toolbar")
        save_action = QAction("Save Config", self)
        save_action.triggered.connect(self.save_all_tabs)
        self.toolbar.addAction(save_action)

        # ✅ NEW: Info Action
        info_action = QAction("Ark Server Manager Info", self)
        info_action.triggered.connect(self.show_info_dialog)
        self.toolbar.addAction(info_action)

        # Load tabs from config or create one tab if empty
        self.load_tabs_from_config()

    def load_tabs_from_config(self):
        servers = self.config_manager.data.get("servers", [])
        if servers:
            for info in servers:
                new_tab = ServerTab()
                new_tab.set_server_info(info)
                index = self.tabs.addTab(new_tab, f"  {info.get('profile', 'New Server')}  ")
                new_tab.update_tab_color(is_running=False)
                new_tab.edit_profile.textChanged.connect(
                    lambda _, tab=new_tab: self.sync_tab_name(tab)
                )
            self.tabs.setCurrentIndex(0)
        else:
            self.add_new_tab()

    def add_new_tab(self):
        new_tab = ServerTab()
        index = self.tabs.addTab(new_tab, "New Server")
        new_tab.update_tab_color(is_running=False)
        self.tabs.setCurrentIndex(index)
        new_tab.edit_profile.textChanged.connect(
            lambda _, tab=new_tab: self.sync_tab_name(tab)
        )

    def sync_tab_name(self, tab):
        i = self.tabs.indexOf(tab)
        if i >= 0:
            profile_name = tab.edit_profile.text()
            # Add two spaces on each side
            text_with_spaces = f"  {profile_name}  "
            self.tabs.setTabText(i, text_with_spaces)


    def close_tab(self, index):
        if self.tabs.count() == 1:
            QMessageBox.warning(self, "Cannot Close", "At least one server tab must remain open.")
            return
    
        widget = self.tabs.widget(index)
        profile_name = widget.edit_profile.text() if widget else "this server"
    
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the '{profile_name}' server tab?",
            QMessageBox.Yes | QMessageBox.No
        )
    
        if reply != QMessageBox.Yes:
            return
    
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

    def show_info_dialog(self):
        QMessageBox.information(
            self,
            "Ark Server Manager Information",
            "ARK Server Manager GUI\nVersion 1.0\n\nManage, start, stop, backup, and update your ARK servers with ease.\n\nDeveloped by Dustin Romero"
        )

# ---------------------------
# Main
# ---------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArkServerManager()
    window.show()
    sys.exit(app.exec_())