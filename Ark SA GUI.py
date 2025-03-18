import sys
import os
import uuid
import json
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QAction
)
from PyQt5.QtCore import Qt

class ServerTab(QWidget):
    """
    Ensures a top-aligned layout:
      - A QVBoxLayout (aligned to top)
      - Inside it, a QGridLayout for the 3 rows
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_folder = ""
        self.server_process = None
        self.profile_id = str(uuid.uuid4())[:18]
        self.init_ui()

    def init_ui(self):
        # 1) Outer layout (vertical), aligned top
        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(10, 10, 10, 10)
        outerLayout.setSpacing(5)
        outerLayout.setAlignment(Qt.AlignTop)  # <<--- Force everything to the top

        # 2) Inner GridLayout for your 3 rows
        grid = QGridLayout()
        grid.setSpacing(5)
        # We do NOT set alignment on the grid, let the outer layout handle it.

        # Add the grid to the outer layout
        outerLayout.addLayout(grid)

        # Row 0: Profile ID, Profile, Buttons
        self.label_profile_id = QLabel(f"Profile ID: {self.profile_id}")
        label_profile = QLabel("Profile:")
        self.edit_profile = QLineEdit("New Server")

        self.button_find = QPushButton("Find")
        self.button_support = QPushButton("Create Support Zip")
        self.button_sync = QPushButton("Sync")
        self.button_import = QPushButton("Import")
        self.button_start = QPushButton("Start")
        self.button_rcon = QPushButton("RCON")

        grid.addWidget(self.label_profile_id, 0, 0)
        grid.addWidget(label_profile,         0, 1)
        grid.addWidget(self.edit_profile,     0, 2, 1, 2)
        grid.addWidget(self.button_find,      0, 4)
        grid.addWidget(self.button_support,   0, 5)
        grid.addWidget(self.button_sync,      0, 6)
        grid.addWidget(self.button_import,    0, 7)
        grid.addWidget(self.button_start,     0, 8)
        grid.addWidget(self.button_rcon,      0, 9)

        # Row 1: Installed Version & Installation Location
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
        grid.addWidget(self.edit_install, 1, 4, 1, 4)
        grid.addWidget(self.button_set_loc, 1, 8)

        # Row 2: Status, Availability, Players, Upgrade/Verify
        self.label_status = QLabel("Status: Stopped")
        self.label_availability = QLabel("Availability: Unavailable")
        self.label_players = QLabel("Players: 0 / 25")
        self.button_upgrade = QPushButton("Upgrade / Verify")

        grid.addWidget(self.label_status,       2, 0, 1, 2)
        grid.addWidget(self.label_availability, 2, 2, 1, 3)
        grid.addWidget(self.label_players,      2, 5, 1, 2)
        grid.addWidget(self.button_upgrade,     2, 7)

        # Connect some example buttons
        self.button_import.clicked.connect(self.import_server)
        self.button_start.clicked.connect(self.start_server)

    def import_server(self):
        folder = QFileDialog.getExistingDirectory(self, "Select ARK Server Folder")
        if folder:
            self.server_folder = folder
            self.edit_profile.setText(os.path.basename(folder))
            self.edit_install.setText(folder)
            self.edit_version.setText("358.24")

    def start_server(self):
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please Import a server first.")
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

class ArkServerManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARK Server Manager")
        self.resize(1200, 700)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        # Let the tab bar resize with text
        tab_bar = self.tabs.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(Qt.ElideNone)

        # Plus button
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedWidth(30)
        self.plus_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.plus_button, Qt.TopRightCorner)

        # Start with one tab
        self.add_new_tab()

    def add_new_tab(self):
        new_tab = ServerTab()
        index = self.tabs.addTab(new_tab, "New Server")
        self.tabs.setCurrentIndex(index)

    def close_tab(self, index):
        if self.tabs.count() == 1:
            QMessageBox.warning(self, "Cannot Close", "At least one server tab must remain open.")
            return
        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArkServerManager()
    window.show()
    sys.exit(app.exec_())
