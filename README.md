# ARK: Survival Ascended Server Manager (Web)

A local web control panel for managing **ARK: Survival Ascended** dedicated servers on Windows.

It replaces the old PyQt desktop GUI with a browser-based manager (same idea as a self-hosted Minecraft panel): start/stop servers, update via SteamCMD, schedules, backups, firewall helpers, and a live console with RCON chat/commands.

---

## Requirements

- **Windows** (process control, SteamCMD, firewall, and path handling are Windows-oriented)
- **[Node.js 20+](https://nodejs.org/)** on your PATH
- ARK Survival Ascended Dedicated Server files (installed via SteamCMD / Steam)
- Optional: SteamCMD for install/update/verify

No `npm install` is required — the app uses only Node built-ins.

---

## Quick start

1. Clone this repo:

```bash
git clone https://github.com/Genis221/Ark-Server-GUI.git
cd Ark-Server-GUI
```

2. Start the manager:

- Double-click **`Start Ark Manager.cmd`**, or
- Run:

```bash
npm start
```

3. Open the UI (it may open automatically):

- Local: `http://127.0.0.1:3220`
- LAN: `http://YOUR-PC-IP:3220`

The start script binds to `0.0.0.0` so other devices on your network can reach it. It also stops any previous manager already using port **3220**.

---

## What you get

### Multi-server profiles (tabs)

Each tab is one server profile:

- Profile name (also used as ASA `SessionName`)
- Install folder
- SteamCMD folder
- Launch arguments (map, ports, mods, cluster flags, etc.)
- Status / availability / players / firewall

Tab top border colors:

- **Green** — running / online
- **Amber** — starting / updating
- **Red** — stopped / offline

### Layout

- **Left:** profile controls + **Server Configs** (schedules, INI editors, backups, log paths)
- **Right:** sticky **Console** (live game log + RCON commands / chat)

### Theme

Use the **Light / Dark** button in the toolbar. Preference is saved in the browser.

---

## Features in detail

### Start / Stop

- Starts `ShooterGame\Binaries\Win64\ArkAscendedServer.exe` with your launch args
- Writes `SessionName` into `GameUserSettings.ini` before launch
- Stop finds the matching `ArkAscendedServer.exe` for that install path and terminates it
- Optionally copies `ShooterGame.log` into your configured game-log folder on stop

### Update / Verify (SteamCMD)

Runs SteamCMD in a visible console window:

```text
+force_install_dir "<install>"
+login anonymous
+app_update 2430930 validate
+quit
```

SteamCMD can be downloaded from the UI into `Documents\SteamCMD` (or set a custom path).

### Availability & players

1. Tries Steam A2S query on the `QueryPort` from launch args  
2. Falls back to reading `ShooterGame.log` for “ready” lines  
3. If the process is up and query isn’t available (common on ASA), shows **Online**

Player counts come from A2S when that works; otherwise max players is parsed from launch args (`WinLiveMaxPlayers` / `MaxPlayers`).

### Server Configs

Collapsible sections for:

- **Automatic Start** — days + time + optional update-before-start
- **Automatic Shutdown / Restart** — days + time + optional update + restart
- **Server Configuration** — open `Game.ini` / `GameUserSettings.ini`, apply firewall rules
- **Automatic World Save Backup** — zip `SavedArks`, retention, schedule
- **Logs** — destinations for game logs and update logs

### Console (live + RCON)

- Streams new lines from `ShooterGame\Saved\Logs\ShooterGame.log`
- Sends RCON commands (Source RCON protocol)
- **Chat** checkbox sends `ServerChat <message>` so you can talk to players
- Polls `GetChat` for player chat when RCON is configured
- Quick actions: `ListPlayers`, `GetChat`, Clear

#### Enable RCON in `GameUserSettings.ini`

```ini
[ServerSettings]
RCONEnabled=True
RCONPort=27020
ServerAdminPassword=YourStrongPassword
```

Restart the ARK server after changing these. Firewall rules should allow the RCON port (TCP) if you use remote tools; the manager talks to RCON on `127.0.0.1`.

Example commands:

```text
ListPlayers
SaveWorld
Broadcast Restart in 5 minutes
ServerChat Hello tribe
GetChat
DoExit
```

Many chat/broadcast commands return an empty RCON body — that is normal.

### Copy Server Settings

Toolbar action to copy selected settings between profiles (launch args, schedules, backup, logs, and optionally INI files with a `.bak` backup).

### Firewall helper

Creates inbound Windows firewall rules (TCP + UDP) for:

- Game `Port` and `Port+1`
- `QueryPort`
- `RCONPort` from the INI (when present)

May require Administrator rights (`Needs Admin` if rules fail).

---

## How it works (architecture)

```text
Browser UI (public/)  --HTTP/SSE-->  Node server (server.mjs)
                                        |
                                        +-- data/state.json   (profiles)
                                        +-- ArkAscendedServer.exe
                                        +-- SteamCMD
                                        +-- Game INIs / SavedArks / logs
                                        +-- RCON (127.0.0.1)
```

| Piece | Role |
|--------|------|
| `server.mjs` | HTTP API, static files, process control, SteamCMD, backups, A2S, RCON, log SSE |
| `public/` | Vanilla SPA (HTML/CSS/JS), no React/Vite |
| `data/state.json` | Saved profiles + activity (created at runtime) |
| `Start Ark Manager.cmd` / `.ps1` | Windows launcher, frees port 3220, prints LAN URL |

### Important API routes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/state` | Profiles + live status (fast path; deep probes in background) |
| `POST` | `/api/servers` | Create profile |
| `PATCH` | `/api/servers/:id` | Update settings (autosaved from UI) |
| `DELETE` | `/api/servers/:id` | Delete profile |
| `POST` | `/api/servers/:id/start\|stop\|update\|backup\|firewall\|command` | Actions |
| `GET` | `/api/servers/:id/console-stream` | SSE live console |

Default bind: `0.0.0.0:3220`  
Env overrides: `ARK_HOST`, `ARK_PORT`, `ARK_DATA_DIR`, `ARK_ALLOW_REMOTE`, `ARK_ALLOW_PUBLIC`

Security defaults:

- LAN / loopback clients allowed
- Public non-private IPs blocked unless `ARK_ALLOW_PUBLIC=true`
- Set `ARK_ALLOW_REMOTE=false` to force loopback-only API access

---

## First-run config import

If `data/state.json` does not exist yet, the manager imports profiles from a root `config.json` (legacy desktop format), if present. After that, only `data/state.json` is used.

`config.json` and `data/` are gitignored so local paths/secrets stay on your machine.

---

## Project layout

```text
Ark-Server-GUI/
├── server.mjs              # Backend
├── package.json
├── Start Ark Manager.cmd
├── Start-ArkManager.ps1
├── public/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── ark-icon.jpg
├── data/                   # Runtime (gitignored)
└── README.md
```

---

## Tips

- Put full ASA launch args in the **Launch Arguments** field (map `?listen?Port=...`, `-mods=...`, `-clusterID=...`, etc.).
- Paths are typed/validated on the host PC (browsers cannot pick arbitrary absolute folders).
- If the page shows “Loading profiles…” forever, another process may be stuck on port 3220 — run `Start Ark Manager.cmd` again (it clears the port), or check Task Manager for `node`.
- Allow inbound TCP **3220** in Windows Firewall if other PCs on the LAN cannot open the UI.
- Keep `ServerAdminPassword` private. Anyone with RCON access can fully control the server.

---

## License / credit

Built for personal / authorized use managing your own ASA dedicated servers. If you redistribute or fork, please credit the original author.
