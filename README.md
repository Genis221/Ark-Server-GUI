V 1.0 Patch Notes:
Initial Release 

Note: please dont use this in any other setting, developing it, without my consent, and also if you do get permission from me, please credit me as i worked really hard on this :)

ARK: Survival Ascended Server Manager

1. Purpose
This SOP outlines the process for installing, configuring, and managing ARK: Survival Ascended servers using the custom Server Manager GUI. It covers server setup, automation, updates, backups, and general operation.

2. System Overview

The Server Manager is a standalone GUI application that allows users to:
	• Manage multiple server profiles 
	• Configure launch arguments 
	• Automate server start/restart/update cycles 
	• Perform backups 
	• Manage logs and server files 
	• Integrate SteamCMD installation 
	• Automatically configure firewall rules 

3. Installation
3.1 Server Manager Installation
	1. Download or obtain the Server Manager .exe file. 
	2. Place it in your desired directory. 
	3. Run the .exe file. 
	4. A configuration file will automatically be created in the same directory as the executable. 
	⚠️ No installer is required — execution initializes the application.

3.2 SteamCMD Installation
	1. Click “Download SteamCMD” in the GUI. 
	2. The tool will download SteamCMD from the official source. 
	3. Default install location:

Documents\SteamCMD
	4. You may manually set or browse to a different location if needed. 

3.3 Server Files Installation
	• Server files are installed separately from the manager. 
	• Use “Update / Verify” to: 
		○ Install server files if missing 
		○ Update existing server files 
	• Installation directory is user-defined. 

4. Creating & Managing Server Profiles
4.1 Profile Creation
	• Click “New Server” 
	• Enter a Profile Name 
	✅ The profile name automatically becomes the server name

4.2 Profile Configuration
Each profile includes:
	• Installation Location 
	• SteamCMD Location 
	• Launch Arguments 
	• Cluster Settings (optional) 

4.3 Launch Arguments
	• Fully customizable 
	• Used to define: 
		○ Map 
		○ Player count 
		○ Mods 
		○ Cluster settings 
		○ Gameplay rules 
	⚠️ Firewall rules are automatically derived from these arguments

5. Server Controls
5.1 Start / Stop Server
	• Click Start (Green Button) to launch server 
	• Button changes to Stop (Red Button) while running 
	• Clicking Stop: 
		○ Safely shuts down the server 
		○ Returns button to green “Start” 

5.2 Server Status Indicators
	• Status: Running / Stopped 
	• Availability: (WIP) 
	• Players Online: (WIP) 
	• RCON: (WIP) 

6. Updates & Verification
6.1 Update / Verify
	• Ensures all server files are: 
		○ Installed 
		○ Up to date 
		○ Not corrupted 

6.2 Automatic Updates
	• Can be triggered: 
		○ Before server start 
		○ During scheduled restarts 

7. Automation Features
7.1 Automatic Start
Configure:
	• Days of the week 
	• Start time 
	• Optional update before start 

7.2 Automatic Shutdown / Restart
Options include:
	• Scheduled shutdown times 
	• Auto-restart intervals 
	• Update on restart 
	✅ Designed for stability and uptime management

8. Firewall Management
	• Automatically opens required ports 
	• Reads: 
		○ Launch arguments 
		○ Config files 
	• Ensures proper server connectivity 
	🔒 No manual port forwarding needed (for local firewall)

9. Backup System
9.1 Backup Intervals
Selectable options:
	• 30 minutes 
	• 1 hour 
	• 3 hours 
	• 6 hours 
	• 12 hours 
	• 24 hours 

9.2 Backup Features
	• Automatic world saves 
	• Manual “Backup Now” option 
	• Configurable backup directory 
	• Retention limit (e.g., keep last 20 backups) 

10. Configuration Management
10.1 Editing Config Files
From GUI:
	• Edit Game.ini 
	• Edit GameUserSettings.ini 
	✅ Opens files directly for quick edits

10.2 Log Management
	• Custom log file location 
	• Separate: 
		○ Game logs 
		○ Update logs 

11. Multi-Server Management
	• Multiple profiles supported simultaneously 
	• Each profile: 
		○ Has independent settings 
		○ Uses its own install directory 
		○ Maintains separate logs and backups 

12. Known Work-in-Progress Features
The following are currently under development:
	• RCON integration 
	• Player monitoring 
	• Availability tracking 
	• Advanced server analytics 

13. Best Practices
	• Keep server files on a dedicated drive (if possible) 
	• Regularly verify server files 
	• Use automated backups with retention limits 
	• Schedule restarts to maintain performance 
	• Keep SteamCMD updated 

14. Notes
	• The system is functional and stable 
	• Some features are still being refined 
	• Designed for scalability and ease of use 
	• GUI prioritizes simplicity and automation 

15. Summary
This Server Manager provides:
	• Full lifecycle server control 
	• Automation for uptime and maintenance 
	• Built-in safety systems (firewall, backups) 

