import sys
import os
import uuid
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox,
    QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt

class ServerTab(QWidget):
    """
    A single tab that contains the ARK server settings.
    Each tab starts empty, and users can import a server.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_folder = ""
        self.server_process = None
        self.init_ui()

    def init_ui(self):
        # Create a grid layout to match the ARK Server Manager layout
        grid = QGridLayout(self)
        grid.setSpacing(8)
        grid.setContentsMargins(10, 10, 10, 10)

        # Row 0: Profile ID and "Find" button
        self.profile_id = str(uuid.uuid4())[:18]
        self.label_profile_id = QLabel(f"Profile ID: {self.profile_id}")
        self.button_find = QPushButton("Find")

        grid.addWidget(self.label_profile_id, 0, 0, 1, 1)
        grid.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 1)
        grid.addWidget(self.button_find, 0, 2, 1, 1, alignment=Qt.AlignRight)

        # Row 1: Profile name, Create Support Zip, Sync, Import, Start, RCON
        label_profile = QLabel("Profile:")
        self.edit_profile = QLineEdit("New Server")

        self.button_support = QPushButton("Create Support Zip")
        self.button_sync = QPushButton("Sync")
        self.button_import = QPushButton("Import Server")
        self.button_start = QPushButton("Start")
        self.button_rcon = QPushButton("RCON")

        grid.addWidget(label_profile, 1, 0)
        grid.addWidget(self.edit_profile, 1, 1)
        grid.addWidget(self.button_support, 1, 2)
        grid.addWidget(self.button_sync, 1, 3)
        grid.addWidget(self.button_import, 1, 4)
        grid.addWidget(self.button_start, 1, 5)
        grid.addWidget(self.button_rcon, 1, 6)

        # Row 2: Installed Version & Installation Location
        label_version = QLabel("Installed Version:")
        self.edit_version = QLineEdit("")
        self.edit_version.setReadOnly(True)

        label_install = QLabel("Installation Location:")
        self.edit_install = QLineEdit("")
        self.edit_install.setReadOnly(True)

        self.button_set_loc = QPushButton("Set Location")

        grid.addWidget(label_version, 2, 0)
        grid.addWidget(self.edit_version, 2, 1)
        grid.addWidget(label_install, 2, 2)
        grid.addWidget(self.edit_install, 2, 3, 1, 2)
        grid.addWidget(self.button_set_loc, 2, 5)

        # Row 3: Status, Availability, Players, Upgrade/Verify
        self.label_status = QLabel("Status: Stopped")
        self.label_availability = QLabel("Availability: Unavailable")
        self.label_players = QLabel("Players: 0 / 25")
        self.button_upgrade = QPushButton("Upgrade / Verify")

        grid.addWidget(self.label_status, 3, 0)
        grid.addWidget(self.label_availability, 3, 1)
        grid.addWidget(self.label_players, 3, 2)
        grid.addWidget(self.button_upgrade, 3, 6)

        # Connect buttons
        self.button_import.clicked.connect(self.import_server)
        self.button_start.clicked.connect(self.start_server)

    def import_server(self):
        """Opens a file dialog to select the ARK server folder and populates fields."""
        folder = QFileDialog.getExistingDirectory(self, "Select ARK Server Folder")
        if folder:
            self.server_folder = folder
            self.edit_profile.setText(os.path.basename(folder))
            self.edit_install.setText(folder)
            self.edit_version.setText("358.24")  # Placeholder version

    def start_server(self):
        """Starts the ARK server process (placeholder logic)."""
        if not self.server_folder:
            QMessageBox.warning(self, "No Server Folder", "Please Import a server first.")
            return

        server_exe = os.path.join(self.server_folder, "ShooterGame", "Binaries", "Win64", "ShooterGameServer.exe")
        if not os.path.exists(server_exe):
            QMessageBox.critical(self, "Error", "Server executable not found.")
            return

        try:
            self.server_process = subprocess.Popen([server_exe])
            self.label_status.setText("Status: Running")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class ArkServerManager(QMainWindow):
    """
    Main window with a QTabWidget. A "+" button in the corner adds a new ServerTab.
    The first tab is always created by default so the window is never empty.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARK Server Manager")
        self.resize(1200, 700)

        # Apply light theme to match the original ARK Server Manager screenshot
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
                padding: 6px 12px;
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

        # Create the tab widget (start with one empty tab)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.setCentralWidget(self.tabs)

        # Create a "+" button to add new tabs
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedWidth(30)
        self.plus_button.clicked.connect(self.add_new_tab)

        # Put the "+" in the top-right corner of the tab bar
        self.tabs.setCornerWidget(self.plus_button, Qt.TopRightCorner)

        # Always start with one tab to prevent a blank screen
        self.add_new_tab()

    def add_new_tab(self):
        """Creates a new tab that starts with the ARK Server layout but empty fields."""
        new_tab = ServerTab()
        index = self.tabs.addTab(new_tab, "New Server")
        self.tabs.setCurrentIndex(index)

    def close_tab(self, index):
        """Closes the tab at 'index'. If only one tab remains, prevent closing."""
        if self.tabs.count() == 1:
            QMessageBox.warning(self, "Cannot Close", "At least one server tab must remain open.")
            return

        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)

# ---------------------------
# Application Entry Point
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArkServerManager()
    window.show()
    sys.exit(app.exec_())
