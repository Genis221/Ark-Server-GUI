import sys
import os
import json
import uuid
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QAction
)
from PyQt5.QtCore import Qt

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
# 2) ServerTab (No ID, No “Find,” “Create Support Zip,” or “Sync”)
# ---------------------------
class ServerTab(QWidget):
    """
    Layout:
      - QVBoxLayout (top-aligned)
      - Row 0: Horizontal box (Profile label, text field, Import, Start, RCON), left-aligned
      - Row 1: Installed Version & Installation Location
      - Row 2: Status, Availability, Players, Upgrade/Verify
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_folder = ""
        self.server_process = None
        self.init_ui()

    def init_ui(self):
        # Outer vertical layout (aligned top)
        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(10, 10, 10, 10)
        outerLayout.setSpacing(5)
        outerLayout.setAlignment(Qt.AlignTop)

        # Inner grid for rows 1 and 2
        grid = QGridLayout()
        grid.setSpacing(5)

        # Add the grid to the outer layout
        outerLayout.addLayout(grid)

        #
        # Row 0: Horizontal layout for Profile & buttons, left-aligned
        #
        row0Layout = QHBoxLayout()
        row0Layout.setSpacing(5)

        label_profile = QLabel("Profile:")
        self.edit_profile = QLineEdit("New Server")

        # Only these buttons remain:
        self.button_import = QPushButton("Import")
        self.button_start = QPushButton("Start")
        self.button_rcon = QPushButton("RCON")

        # Add them all in one row
        row0Layout.addWidget(label_profile)
        row0Layout.addWidget(self.edit_profile)
        row0Layout.addWidget(self.button_import)
        row0Layout.addWidget(self.button_start)
        row0Layout.addWidget(self.button_rcon)

        # Place row0Layout in row 0 of the grid, spanning all columns
        grid.addLayout(row0Layout, 0, 0, 1, -1, alignment=Qt.AlignLeft)

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

        grid.addWidget(label_version, 1, 0)
        grid.addWidget(self.edit_version, 1, 1, 1, 2)
        grid.addWidget(label_install, 1, 3)
        grid.addWidget(self.edit_install, 1, 4, 1, 3)
        grid.addWidget(self.button_set_loc, 1, 7)

        #
        # Row 2: Status, Availability, Players, Upgrade/Verify
        #
        self.label_status = QLabel("Status: Stopped")
        self.label_availability = QLabel("Availability: Unavailable")
        self.label_players = QLabel("Players: 0 / 25")
        self.button_upgrade = QPushButton("Upgrade / Verify")

        grid.addWidget(self.label_status,       2, 0, 1, 2)
        grid.addWidget(self.label_availability, 2, 2, 1, 3)
        grid.addWidget(self.label_players,      2, 5, 1, 2)
        grid.addWidget(self.button_upgrade,     2, 7)

        # Connect buttons
        self.button_import.clicked.connect(self.import_server)
        self.button_start.clicked.connect(self.start_server)

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
        return {
            "profile": self.edit_profile.text(),
            "folder": self.server_folder,
            "version": self.edit_version.text(),
            "install": self.edit_install.text()
        }

    def set_server_info(self, info):
        self.edit_profile.setText(info.get("profile", "New Server"))
        self.server_folder = info.get("folder", "")
        self.edit_version.setText(info.get("version", ""))
        self.edit_install.setText(info.get("install", ""))

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
