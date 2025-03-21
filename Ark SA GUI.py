import sys
import os
import json
import uuid
import subprocess
import datetime
import zipfile
import psutil

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QAction,
    QGroupBox, QCheckBox, QTimeEdit, QDialog, QVBoxLayout
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
      - Row 4: Collapsible "Server Configuration" Section
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
        # Add them all in one row with Start and Import swapped
        row0Layout.addWidget(label_profile)
        row0Layout.addWidget(self.edit_profile)
        row0Layout.addWidget(self.button_start)   # Start button now comes first
        row0Layout.addWidget(self.button_import)  # Then Import button
        row0Layout.addWidget(self.button_rcon)
        row0Layout.addWidget(self.button_backup)

        # Set initial style of the Start button to green
        self.button_start.setStyleSheet("background-color: green; color: white;")


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
        self.shutdown_time_edit.setDisplayFormat("hh:mm AP")
        self.shutdown_time_edit.setTime(QTime(8,0))  # default 08:00
        time_layout.addWidget(self.shutdown_time_edit)

        self.checkbox_perform_update = QCheckBox("Perform update")
        self.checkbox_then_restart = QCheckBox("Then restart")

        time_layout.addWidget(self.checkbox_perform_update)
        time_layout.addWidget(self.checkbox_then_restart)
        scheduler_layout.addLayout(time_layout)

        self.grid.addWidget(self.scheduler_group, 3, 0, 1, -1)
               
        # Row 4: Collapsible "Server Configuration" Section
        #
        self.config_group = QGroupBox("Server Configuration")
        self.config_group.setCheckable(True)  # Enables the collapsible effect
        self.config_group.setChecked(False)  # Initially collapsed

        config_layout = QVBoxLayout()

        # Buttons to Load and Edit Configuration Files
        self.button_edit_game_ini = QPushButton("Edit Game")
        self.button_edit_gameusersettings_ini = QPushButton("Edit GameUserSettings")

        config_layout.addWidget(self.button_edit_game_ini)
        config_layout.addWidget(self.button_edit_gameusersettings_ini)

        self.config_group.setLayout(config_layout)
        self.grid.addWidget(self.config_group, 4, 0, 1, -1)

        # Connect buttons to open config editors
        self.button_edit_game_ini.clicked.connect(lambda: self.edit_config_file("Game.ini"))
        self.button_edit_gameusersettings_ini.clicked.connect(lambda: self.edit_config_file("GameUserSettings.ini"))


        # Connect buttons
        self.button_import.clicked.connect(self.import_server)
        self.button_start.clicked.connect(self.start_server)
        self.button_backup.clicked.connect(self.backup_saves)

    def edit_config_file(self, filename):
        """
        Opens the selected server configuration file in Notepad++.
        If Notepad++ is not found, it defaults to regular Notepad.
        If the file does not exist, it prompts the user to create it.
        """
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return

        # Locate 'steamapps' in the path and extract everything from there onward
        steamapps_index = self.server_folder.lower().find("steamapps")
        if steamapps_index == -1:
            QMessageBox.critical(self, "Error", "Could not find 'steamapps' in the server folder path.")
            return

        # Build the correct path for the config files
        config_path = os.path.join(self.server_folder, "ShooterGame", "Saved", "Config", "WindowsServer", filename)

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
                self.shutdown_triggered_today = True
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
        if self.server_pid is not None:
            try:
                # Check if the process exists before attempting to kill it
                for proc in psutil.process_iter(attrs=['pid', 'name']):
                    if proc.info['pid'] == self.server_pid:
                        proc = psutil.Process(self.server_pid)
                        proc.terminate()  # Try to terminate first
                        proc.wait(timeout=5)  # Wait 5 seconds for clean shutdown

                        # If process is still running, forcefully kill it
                        if proc.is_running():
                            proc.kill()

                        # Reset process tracking
                        self.server_process = None
                        self.server_pid = None

                        # Update UI
                        self.label_status.setText("Status: Stopped")
                        self.button_start.setText("Start")
                        self.button_start.setStyleSheet("background-color: green; color: white;")
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle("Scheduled Action")
                        msg.setText("Scheduled shutdown/update/restart complete.")
                        msg.setStandardButtons(QMessageBox.Ok)
                        msg.show()
                        
                        # Auto-close after 10 seconds (10,000 ms)
                        QTimer.singleShot(10_000, msg.accept)


                        break  # Exit loop after finding and stopping the process

            except psutil.NoSuchProcess:
                self.server_process = None
                self.server_pid = None
                QMessageBox.warning(self, "Scheduled Action", "Server process not found, it may have already stopped.")
            except psutil.AccessDenied:
                QMessageBox.critical(self, "Error", "Access denied when trying to stop the process. Try running as administrator.")
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

            if self.checkbox_perform_update.isChecked():
                self.update_server()
                if self.checkbox_then_restart.isChecked():
                    QTimer.singleShot(12_000, finish_and_restart)
                else:
                    show_countdown_dialog("Server has shut down and updated.")
            elif self.checkbox_then_restart.isChecked():
                QTimer.singleShot(12_000, finish_and_restart)
            else:
                show_countdown_dialog("Server has shut down.")

        stop_then_update_then_restart()

    def stop_server(self):
        """Placeholder for stopping the server. If you have a process handle, you can terminate it."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None
            self.label_status.setText("Status: Stopped")

    def update_server(self):
        """
        Executes a SteamCMD update for the server.
        Assumes SteamCMD is installed and accessible via PATH.
        """
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return

        steamcmd_path = r"C:\Program Files (x86)\Steam\steamcmd.exe"  # Modify path if needed

        if not os.path.exists(steamcmd_path):
            QMessageBox.critical(self, "Error", "SteamCMD not found. Please install it.")
            return

        try:
            QMessageBox.information(self, "Server Update", "Updating server via SteamCMD...")
            
            # Run SteamCMD to update the ARK server
            subprocess.run([steamcmd_path, "+login", "anonymous",
                            "+force_install_dir", self.server_folder,
                            "+app_update", "2430930", "validate", "+quit"],
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update server: {str(e)}")


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
        """
        Starts the ARK server using the 'Ark Server.bat' file from the Win64 directory.
        If the server is already running, this function will stop it instead.
        """
        # If the server is already running, stop it
        if self.server_process is not None:
            self.stop_server()
            return

        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return

        # Locate 'steamapps' in the path and extract everything from there onward
        steamapps_index = self.server_folder.lower().find("steamapps")
        if steamapps_index == -1:
            QMessageBox.critical(self, "Error", "Could not find 'steamapps' in the server folder path.")
            return

        # Construct the correct path for the Win64 folder
        win64_path = os.path.join(self.server_folder, "ShooterGame", "Binaries", "Win64")

        # Path to the batch file and executable
        batch_file = os.path.join(win64_path, "Ark Server.bat")
        exe_file = os.path.join(win64_path, "ArkAscendedServer.exe")

        # Ensure the batch file exists before executing
        if not os.path.exists(batch_file):
            QMessageBox.critical(self, "Error", f"Batch file not found:\n{batch_file}")
            return

        # Ensure the server executable exists before executing
        if not os.path.exists(exe_file):
            QMessageBox.critical(self, "Error", f"Server executable not found:\n{exe_file}")
            return

        try:
            # Start the batch file using subprocess, and track the process
            self.server_process = subprocess.Popen(batch_file, cwd=win64_path, creationflags=subprocess.CREATE_NEW_CONSOLE)

            # Save the process ID (PID)
            self.server_pid = self.server_process.pid  # Track PID to ensure the correct process is stopped

            # Update button and status
            self.label_status.setText("Status: Running")
            self.button_start.setText("Stop")
            self.button_start.setStyleSheet("background-color: red; color: white;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start the server: {str(e)}")

    def stop_server(self):
        """
        Stops the ARK server process by identifying the correct process running the executable.
        Ensures the correct instance of 'ArkAscendedServer.exe' is stopped, even if multiple servers are running.
        Shows a countdown popup after stopping.
        """
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please import a server first.")
            return

        # Locate the correct process based on the server folder path
        win64_path = os.path.join(self.server_folder, "ShooterGame", "Binaries", "Win64")
        exe_name = "ArkAscendedServer.exe"

        try:
            # Use tasklist to find processes running ArkAscendedServer.exe
            result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV"],
                                    capture_output=True, text=True)
            
            process_list = result.stdout.split("\n")
            for line in process_list[1:]:  # Skip header
                if exe_name in line:
                    data = line.split(",")
                    pid = data[1].strip('"')  # Extract the PID from CSV output

                    # Terminate the process
                    subprocess.run(["taskkill", "/PID", pid, "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Reset stored process info
            self.server_process = None
            self.server_pid = None

            # Update UI
            self.label_status.setText("Status: Stopped")
            self.button_start.setText("Start")
            self.button_start.setStyleSheet("background-color: green; color: white;")

            # Countdown auto-close dialog
            self.countdown = 10
            self.dialog = QMessageBox(self)
            self.dialog.setWindowTitle("Server Stopped")
            self.dialog.setText(f"ARK server was stopped.\n\nClosing in {self.countdown} seconds...")
            self.dialog.setStandardButtons(QMessageBox.Ok)
            self.dialog.setDefaultButton(QMessageBox.Ok)

            def update_dialog():
                self.countdown -= 1
                if self.countdown <= 0:
                    self.dialog.done(0)
                    self.auto_close_timer.stop()
                else:
                    self.dialog.setText(f"ARK server was stopped.\n\nClosing in {self.countdown} seconds...")

            self.auto_close_timer = QTimer()
            self.auto_close_timer.timeout.connect(update_dialog)
            self.auto_close_timer.start(1000)
            self.dialog.show()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stop the server: {str(e)}")



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
