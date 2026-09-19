const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const INTERVALS = ["30 mins", "1 hr", "2 hrs", "4 hrs", "6 hrs", "12 hrs", "24 hrs"];
const ASA_MAPS = [
  { value: "TheIsland_WP", label: "The Island" },
  { value: "ScorchedEarth_WP", label: "Scorched Earth" },
  { value: "Aberration_WP", label: "Aberration" },
  { value: "Extinction_WP", label: "Extinction" },
  { value: "TheCenter_WP", label: "The Center" },
  { value: "Ragnarok_WP", label: "Ragnarok" },
  { value: "Valguero_WP", label: "Valguero" },
  { value: "LostColony_WP", label: "Lost Colony" },
  { value: "Genesis_WP", label: "Genesis" },
  { value: "Gen2_WP", label: "Genesis Part 2" },
  { value: "Astraeos_WP", label: "Astraeos" },
  { value: "Custom", label: "Custom map…" }
];

const KNOWN_QUERY_KEYS = new Set([
  "listen",
  "port",
  "queryport",
  "rconenabled",
  "rconport",
  "overrideofficialdifficulty",
  "ballowflyerspeedleveling",
  "allowteksuitpowersingenesis"
]);

const KNOWN_FLAG_KEYS = new Set([
  "mods",
  "forceallowcaveflyers",
  "ballowflyerspeedleveling",
  "winlivemaxplayers",
  "clusterid",
  "clusterdiroverride"
]);

function defaultLaunchParts() {
  return {
    map: "TheIsland_WP",
    customMap: "",
    port: "7777",
    queryPort: "27015",
    rconEnabled: true,
    rconPort: "32300",
    difficulty: "10.0",
    allowFlyerSpeed: true,
    allowTekGenesis: false,
    mods: "",
    forceCaveFlyers: false,
    maxPlayers: "25",
    clusterId: "",
    clusterDir: "",
    extraQuery: "",
    extraFlags: ""
  };
}

function parseFlagTokens(flagPart) {
  const tokens = [];
  // Quoted values may include Windows backslashes (e.g. ClusterDirOverride="D:\").
  const re = /(?:^|\s)-([A-Za-z_][\w]*)(?:=(?:"([^"]*)"|(\S+)))?/g;
  let match;
  while ((match = re.exec(String(flagPart || "")))) {
    tokens.push({
      key: match[1],
      value: match[2] != null ? match[2] : (match[3] ?? true)
    });
  }
  return tokens;
}

function parseLaunchArgs(raw) {
  const parts = defaultLaunchParts();
  const text = String(raw || "").trim();
  if (!text) return parts;

  const flagStart = text.search(/\s+-[A-Za-z_]/);
  let queryPart = text;
  let flagPart = "";
  if (flagStart >= 0) {
    queryPart = text.slice(0, flagStart).trim();
    flagPart = text.slice(flagStart).trim();
  }

  const qBits = queryPart.split("?");
  const mapToken = (qBits[0] || "").trim();
  if (mapToken) {
    if (ASA_MAPS.some(m => m.value === mapToken)) parts.map = mapToken;
    else {
      parts.map = "Custom";
      parts.customMap = mapToken;
    }
  }

  const extras = [];
  for (let i = 1; i < qBits.length; i++) {
    const bit = qBits[i].trim();
    if (!bit || bit.toLowerCase() === "listen") continue;
    const eq = bit.indexOf("=");
    const key = eq >= 0 ? bit.slice(0, eq) : bit;
    const val = eq >= 0 ? bit.slice(eq + 1) : "True";
    const kl = key.toLowerCase();
    if (kl === "port") parts.port = val;
    else if (kl === "queryport") parts.queryPort = val;
    else if (kl === "rconenabled") parts.rconEnabled = /^true$/i.test(val);
    else if (kl === "rconport") parts.rconPort = val;
    else if (kl === "overrideofficialdifficulty") parts.difficulty = val;
    else if (kl === "ballowflyerspeedleveling") parts.allowFlyerSpeed = /^true$/i.test(val);
    else if (kl === "allowteksuitpowersingenesis") parts.allowTekGenesis = /^true$/i.test(val);
    else if (!KNOWN_QUERY_KEYS.has(kl)) extras.push(bit);
  }
  parts.extraQuery = extras.join("?");

  const unknownFlags = [];
  for (const token of parseFlagTokens(flagPart)) {
    const kl = token.key.toLowerCase();
    if (kl === "mods") parts.mods = String(token.value === true ? "" : token.value);
    else if (kl === "forceallowcaveflyers") parts.forceCaveFlyers = true;
    else if (kl === "ballowflyerspeedleveling") parts.allowFlyerSpeed = /^true$/i.test(String(token.value));
    else if (kl === "winlivemaxplayers") parts.maxPlayers = String(token.value);
    else if (kl === "clusterid") parts.clusterId = String(token.value === true ? "" : token.value);
    else if (kl === "clusterdiroverride") parts.clusterDir = String(token.value === true ? "" : token.value);
    else if (!KNOWN_FLAG_KEYS.has(kl)) {
      unknownFlags.push(token.value === true ? `-${token.key}` : `-${token.key}=${token.value}`);
    }
  }
  parts.extraFlags = unknownFlags.join(" ");
  return parts;
}

function buildLaunchArgs(parts) {
  const p = { ...defaultLaunchParts(), ...parts };
  const mapName = p.map === "Custom" ? (p.customMap || "TheIsland_WP") : p.map;
  const query = [mapName, "listen"];
  if (p.rconEnabled) {
    query.push("RCONEnabled=True");
    if (p.rconPort) query.push(`RCONPort=${String(p.rconPort).trim()}`);
  }
  if (p.port) query.push(`Port=${String(p.port).trim()}`);
  if (p.queryPort) query.push(`QueryPort=${String(p.queryPort).trim()}`);
  if (p.difficulty !== "" && p.difficulty != null) {
    query.push(`OverrideOfficialDifficulty=${String(p.difficulty).trim()}`);
  }
  if (p.allowFlyerSpeed) query.push("bAllowFlyerSpeedLeveling=true");
  if (p.allowTekGenesis) query.push("AllowTekSuitPowersInGenesis=True");
  const extraQuery = String(p.extraQuery || "").trim();
  if (extraQuery) {
    for (const bit of extraQuery.split("?")) {
      if (bit.trim()) query.push(bit.trim());
    }
  }

  let out = query.join("?");
  const flags = [];
  if (String(p.mods || "").trim()) flags.push(`-Mods=${String(p.mods).trim()}`);
  if (p.forceCaveFlyers) flags.push("-ForceAllowCaveFlyers");
  if (p.allowFlyerSpeed) flags.push("-bAllowFlyerSpeedLeveling=true");
  if (p.maxPlayers !== "" && p.maxPlayers != null) flags.push(`-WinLiveMaxPlayers=${String(p.maxPlayers).trim()}`);
  if (String(p.clusterId || "").trim()) flags.push(`-clusterID=${String(p.clusterId).trim()}`);
  if (String(p.clusterDir || "").trim()) {
    const dir = String(p.clusterDir).trim().replace(/"/g, "");
    flags.push(`-ClusterDirOverride="${dir}"`);
  }
  if (String(p.extraFlags || "").trim()) flags.push(String(p.extraFlags).trim());
  if (flags.length) out += ` ${flags.join(" ")}`;
  return out;
}

function launchMapOptions(selected, customMap) {
  const values = ASA_MAPS.map(m => m.value);
  const opts = ASA_MAPS.map(m => (
    `<option value="${m.value}" ${selected === m.value ? "selected" : ""}>${escapeHtml(m.label)} (${escapeHtml(m.value)})</option>`
  ));
  if (selected && selected !== "Custom" && !values.includes(selected)) {
    opts.unshift(`<option value="${escapeHtml(selected)}" selected>${escapeHtml(selected)}</option>`);
  }
  return opts.join("") + (selected === "Custom" && customMap
    ? ""
    : "");
}

function renderLaunchArgsEditor(server) {
  const parts = parseLaunchArgs(server.launchArgs);
  const showCustom = parts.map === "Custom";
  return `
    <div class="launch-builder" data-launch-builder>
      <div class="launch-builder-head">
        <strong>Launch Arguments</strong>
        <span class="muted">Per-server settings — map, ports, mods, cluster</span>
      </div>
      <div class="launch-grid">
        <label class="field">
          <span>Map</span>
          <select data-launch="map">${launchMapOptions(parts.map, parts.customMap)}</select>
        </label>
        <label class="field launch-custom-map" ${showCustom ? "" : "hidden"}>
          <span>Custom map file</span>
          <input data-launch="customMap" value="${escapeHtml(parts.customMap)}" placeholder="MyMap_WP" />
        </label>
        <label class="field">
          <span>Game Port</span>
          <input data-launch="port" type="number" min="1" max="65535" value="${escapeHtml(parts.port)}" />
        </label>
        <label class="field">
          <span>Query Port</span>
          <input data-launch="queryPort" type="number" min="1" max="65535" value="${escapeHtml(parts.queryPort)}" />
        </label>
        <label class="field">
          <span>RCON</span>
          <select data-launch="rconEnabled">
            <option value="true" ${parts.rconEnabled ? "selected" : ""}>Enabled</option>
            <option value="false" ${!parts.rconEnabled ? "selected" : ""}>Disabled</option>
          </select>
        </label>
        <label class="field">
          <span>RCON Port</span>
          <input data-launch="rconPort" type="number" min="1" max="65535" value="${escapeHtml(parts.rconPort)}" />
        </label>
        <label class="field">
          <span>Max Players</span>
          <input data-launch="maxPlayers" type="number" min="1" max="200" value="${escapeHtml(parts.maxPlayers)}" />
        </label>
        <label class="field">
          <span>Official Difficulty</span>
          <input data-launch="difficulty" value="${escapeHtml(parts.difficulty)}" placeholder="10.0" />
        </label>
        <label class="field">
          <span>Cluster ID</span>
          <input data-launch="clusterId" value="${escapeHtml(parts.clusterId)}" placeholder="221221221221" />
        </label>
        <label class="field">
          <span>Cluster Dir Override</span>
          <input data-launch="clusterDir" value="${escapeHtml(parts.clusterDir)}" placeholder="D:\\" />
        </label>
      </div>
      <div class="launch-checks">
        <label class="check-line"><input type="checkbox" data-launch="allowFlyerSpeed" ${parts.allowFlyerSpeed ? "checked" : ""} /> Allow flyer speed leveling</label>
        <label class="check-line"><input type="checkbox" data-launch="forceCaveFlyers" ${parts.forceCaveFlyers ? "checked" : ""} /> Force allow cave flyers</label>
        <label class="check-line"><input type="checkbox" data-launch="allowTekGenesis" ${parts.allowTekGenesis ? "checked" : ""} /> Allow Tek suit powers in Genesis</label>
      </div>
      <label class="field">
        <span>Mods (comma-separated CurseForge IDs)</span>
        <textarea data-launch="mods" rows="2" placeholder="931874,930829,930404,...">${escapeHtml(parts.mods)}</textarea>
      </label>
      <details class="launch-advanced">
        <summary>Advanced / raw launch string</summary>
        <label class="field">
          <span>Extra ?query options (optional, joined with ?)</span>
          <input data-launch="extraQuery" value="${escapeHtml(parts.extraQuery)}" placeholder="SomeOption=Value" />
        </label>
        <label class="field">
          <span>Extra -flags (optional)</span>
          <input data-launch="extraFlags" value="${escapeHtml(parts.extraFlags)}" placeholder="-NoBattlEye" />
        </label>
        <label class="field">
          <span>Raw launch arguments</span>
          <textarea data-field="launchArgs" rows="3">${escapeHtml(server.launchArgs || "")}</textarea>
        </label>
      </details>
    </div>
  `;
}

function readLaunchPartsFromDom(root) {
  const parts = defaultLaunchParts();
  if (!root) return parts;
  const get = name => root.querySelector(`[data-launch="${name}"]`);
  parts.map = get("map")?.value || parts.map;
  parts.customMap = get("customMap")?.value || "";
  parts.port = get("port")?.value || "";
  parts.queryPort = get("queryPort")?.value || "";
  parts.rconEnabled = get("rconEnabled")?.value !== "false";
  parts.rconPort = get("rconPort")?.value || "";
  parts.maxPlayers = get("maxPlayers")?.value || "";
  parts.difficulty = get("difficulty")?.value || "";
  parts.clusterId = get("clusterId")?.value || "";
  parts.clusterDir = get("clusterDir")?.value || "";
  parts.allowFlyerSpeed = Boolean(get("allowFlyerSpeed")?.checked);
  parts.forceCaveFlyers = Boolean(get("forceCaveFlyers")?.checked);
  parts.allowTekGenesis = Boolean(get("allowTekGenesis")?.checked);
  parts.mods = get("mods")?.value || "";
  parts.extraQuery = get("extraQuery")?.value || "";
  parts.extraFlags = get("extraFlags")?.value || "";
  return parts;
}

function syncLaunchBuilderToArgs(serverId) {
  const page = workspace.querySelector(`[data-server-id="${serverId}"]`);
  const builder = page?.querySelector("[data-launch-builder]");
  if (!builder) return;
  const customWrap = builder.querySelector(".launch-custom-map");
  const mapEl = builder.querySelector('[data-launch="map"]');
  if (customWrap && mapEl) customWrap.hidden = mapEl.value !== "Custom";

  const built = buildLaunchArgs(readLaunchPartsFromDom(builder));
  const raw = builder.querySelector('[data-field="launchArgs"]');
  if (raw && raw !== document.activeElement) raw.value = built;
  schedulePatch(serverId, { launchArgs: built });
  const server = state.servers.find(s => s.id === serverId);
  if (server) server.launchArgs = built;
}

const state = {
  servers: [],
  activity: [],
  activeId: null,
  pollTimer: null,
  saveTimers: new Map(),
  pendingPatches: new Map(),
  openSections: new Set(),
  busy: new Set(),
  repairPrompted: new Set(),
  consoleSource: null,
  consoleServerId: null
};

const workspace = document.getElementById("workspace");
const tabsEl = document.getElementById("tabs");
const toastStack = document.getElementById("toast-stack");
const infoDialog = document.getElementById("info-dialog");
const copyDialog = document.getElementById("copy-dialog");
const confirmDialog = document.getElementById("confirm-dialog");
const firewallDialog = document.getElementById("firewall-dialog");
const repairDialog = document.getElementById("repair-dialog");
const playersDialog = document.getElementById("players-dialog");
const playerContextMenu = document.getElementById("player-context-menu");

let playersDialogServerId = null;
let contextPlayer = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatPingMs(ms) {
  if (ms == null || ms === "") return "";
  const n = Number(ms);
  if (!Number.isFinite(n) || n < 0) return "";
  return `${Math.round(n)} ms`;
}

function playerRosterEntries(server) {
  if (Array.isArray(server.playerList) && server.playerList.length) {
    return server.playerList.map(p => ({
      name: p?.name || "Unknown",
      pingMs: p?.pingMs ?? server.serverPingMs ?? null
    }));
  }
  const names = Array.isArray(server.playerNames) ? server.playerNames : [];
  return names.map(name => ({
    name,
    pingMs: server.serverPingMs ?? null
  }));
}

function playerNameHtml(name, pingMs) {
  const ping = formatPingMs(pingMs);
  const pingPart = ping
    ? ` <span class="player-name-sep">·</span> <span class="player-ping">${escapeHtml(ping)}</span>`
    : "";
  return `<div class="player-name">${escapeHtml(name || "Unknown")}${pingPart}</div>`;
}

function playerRosterHtml(server) {
  const entries = playerRosterEntries(server);
  if (!entries.length) {
    return `<div class="player-names-empty">${Number(server.players) > 0 ? "Names updating…" : "No players online"}</div>`;
  }
  return entries.map(p => playerNameHtml(p.name, p.pingMs)).join("");
}

function toast(message, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<p>${escapeHtml(message)}</p>`;
  toastStack.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function activeServer() {
  return state.servers.find(s => s.id === state.activeId) || state.servers[0] || null;
}

function schedulePatch(id, patch) {
  const server = state.servers.find(s => s.id === id);
  if (!server) return;
  Object.assign(server, patch);
  if (patch.profile !== undefined) renderTabs();
  const pending = { ...(state.pendingPatches.get(id) || {}), ...patch };
  state.pendingPatches.set(id, pending);
  if (state.saveTimers.has(id)) clearTimeout(state.saveTimers.get(id));
  state.saveTimers.set(id, setTimeout(async () => {
    const body = state.pendingPatches.get(id) || {};
    state.pendingPatches.delete(id);
    try {
      const updated = await api(`/api/servers/${id}`, { method: "PATCH", body });
      const idx = state.servers.findIndex(s => s.id === id);
      if (idx >= 0) state.servers[idx] = { ...state.servers[idx], ...updated };
    } catch (err) {
      toast(err.message, "error");
    }
  }, 500));
}

function statusClass(server) {
  const status = String(server.status || "").toLowerCase();
  const availability = String(server.availability || "").toLowerCase();
  if (status === "updating" || availability.includes("start")) return "starting";
  if (status === "running") return "running";
  return "stopped";
}

function statusDisplay(server) {
  const status = String(server?.status || "").toLowerCase();
  const availability = String(server?.availability || "").toLowerCase();
  if (status === "updating") return { label: "Updating", tone: "warn" };
  if (availability.includes("start") || status.includes("start")) {
    return { label: "Starting…", tone: "warn" };
  }
  if (status === "running") return { label: "Running", tone: "good" };
  return { label: "Offline", tone: "bad" };
}

function availabilityClass(value) {
  const v = String(value || "").toLowerCase();
  if (v === "online") return "good";
  if (v.includes("start") || v === "unreachable") return "warn";
  return "bad";
}

function firewallClass(value) {
  const v = String(value || "").toLowerCase();
  if (v === "good") return "good";
  if (v.includes("admin") || v.includes("no port")) return "bad";
  return "warn";
}

function renderTabs() {
  const servers = [...state.servers].sort((a, b) => a.order - b.order);
  if (!state.activeId && servers[0]) state.activeId = servers[0].id;
  tabsEl.innerHTML = servers.map(server => `
    <button type="button" class="tab ${statusClass(server)} ${server.id === state.activeId ? "active" : ""}"
      data-id="${server.id}" draggable="true" role="tab" aria-selected="${server.id === state.activeId}">
      <span>${escapeHtml(server.profile || "New Server")}</span>
      <span class="close" data-close="${server.id}" title="Close">×</span>
    </button>
  `).join("");
}

function dayChecks(name, values) {
  return DAYS.map((day, i) => `
    <label><input type="checkbox" data-field="${name}" data-index="${i}" ${values?.[i] ? "checked" : ""} /> ${day}</label>
  `).join("");
}

function disconnectConsole() {
  if (state.consoleSource) {
    state.consoleSource.close();
    state.consoleSource = null;
  }
  state.consoleServerId = null;
}

function connectConsole(serverId) {
  if (state.consoleServerId === serverId && state.consoleSource) return;
  disconnectConsole();
  state.consoleServerId = serverId;
  const source = new EventSource(`/api/servers/${serverId}/console-stream`);
  state.consoleSource = source;
  source.onmessage = event => {
    try {
      const entry = JSON.parse(event.data);
      appendConsoleLine(entry);
      const el = document.getElementById("console-output");
      if (el) el.scrollTop = el.scrollHeight;
    } catch { /* ignore */ }
  };
  source.onerror = () => {
    const status = document.getElementById("console-live-status");
    if (status) {
      status.dataset.state = "reconnecting";
      const label = status.querySelector("b");
      if (label) label.textContent = "Reconnecting";
    }
  };
  source.onopen = () => {
    const status = document.getElementById("console-live-status");
    if (status) {
      status.dataset.state = "live";
      const label = status.querySelector("b");
      if (label) label.textContent = "Live";
    }
  };
}

function appendConsoleLine(entry) {
  const el = document.getElementById("console-output");
  if (!el) return;
  const empty = el.querySelector(".console-empty");
  if (empty) empty.remove();
  const line = document.createElement("div");
  line.className = `console-line ${entry.level || "info"}`;
  const time = new Date(entry.time || Date.now()).toLocaleTimeString();
  line.innerHTML = `<time>${escapeHtml(time)}</time><span>${escapeHtml(entry.message || "")}</span>`;
  el.appendChild(line);
  while (el.children.length > 600) el.removeChild(el.firstChild);
}

function rconHint(server) {
  const rcon = server.rcon || {};
  if (!rcon.enabled) return "RCON disabled — set RCONEnabled=True in GameUserSettings.ini";
  if (!rcon.hasPassword) return "Set ServerAdminPassword in GameUserSettings.ini to use commands/chat";
  if (String(server.status).toLowerCase() !== "running") return "Start the server to send commands and chat";
  return `RCON ready on TCP ${rcon.port || "?"} · players auto-refresh`;
}

function renderServer(server) {
  if (!server) {
    workspace.innerHTML = `<div class="empty-view"><p>No server profiles yet.</p></div>`;
    return;
  }
  const running = String(server.status).toLowerCase() === "running";
  const updating = String(server.status).toLowerCase() === "updating";
  const busy = state.busy.has(server.id) || updating;
  const open = key => state.openSections.has(`${server.id}:${key}`) ? "open" : "";
  const statusUi = statusDisplay(server);

  workspace.innerHTML = `
    <div class="server-page" data-server-id="${server.id}">
      <div class="server-main">
        <section class="header-card">
          <div class="header-top">
            <label class="field">
              <span>Profile</span>
              <input data-field="profile" value="${escapeHtml(server.profile)}" maxlength="80" />
            </label>
            <div class="controls-row">
              <button type="button" class="btn ${running ? "stop" : "start"}" data-action="toggle" ${busy ? "disabled" : ""}>
                ${running ? "Stop" : "Start"}
              </button>
              <button type="button" class="btn primary" data-action="update" ${busy ? "disabled" : ""}>Update / Verify</button>
            </div>
          </div>

          <div class="grid-2">
            <label class="field">
              <span>Installed Version</span>
              <input data-field="version" value="${escapeHtml(server.version || "")}" readonly />
            </label>
            <div class="field">
              <span class="field-label">Install Location</span>
              <div class="path-row">
                <input class="inline-input" data-field="install" value="${escapeHtml(server.install || "")}" placeholder="C:\\path\\to\\ARK Survival Ascended Dedicated Server" />
                <button type="button" class="btn secondary" data-action="validate-install">Set Location</button>
              </div>
            </div>
          </div>

          <div class="field">
            <span class="field-label">SteamCMD</span>
            <div class="path-row">
              <input class="inline-input" data-field="steamcmd" value="${escapeHtml(server.steamcmd || "")}" placeholder="C:\\Users\\...\\Documents\\SteamCMD" />
              <button type="button" class="btn secondary" data-action="validate-steamcmd">Browse</button>
              <button type="button" class="btn primary" data-action="download-steamcmd">Download SteamCMD</button>
            </div>
          </div>

          <div class="stats">
            <article class="stat-card ${statusUi.tone}">
              <span>Status</span>
              <strong>${escapeHtml(statusUi.label)}</strong>
            </article>
            <article class="stat-card ${availabilityClass(server.availability)}">
              <span>Availability</span>
              <strong>${escapeHtml(server.availability || "Offline")}</strong>
            </article>
            <article class="stat-card players-card ${Number(server.players) > 0 ? "good" : ""}">
              <span>Players</span>
              <strong>${Number(server.players) || 0} / ${Number(server.maxPlayers) || 70}</strong>
              <div class="player-names" data-player-names>
                ${playerRosterHtml(server)}
              </div>
            </article>
            <article class="stat-card ${firewallClass(server.firewallStatus)}">
              <span>Firewall</span>
              <strong>${escapeHtml(server.firewallStatus || "Not Checked")}</strong>
            </article>
          </div>

          ${renderLaunchArgsEditor(server)}

        </section>

        <div class="configs-heading">
          <h2>Server Configs</h2>
          <p>Schedules, backups, INI files, and log paths</p>
        </div>

        <div class="scroll-sections">
          <section class="section ${open("autostart")}" data-section="autostart">
            <button type="button" class="section-toggle"><span class="chev">▶</span> Automatic Start</button>
            <div class="section-body">
              <div class="day-row">${dayChecks("autostartDays", server.autostartDays)}</div>
              <label class="field"><span>Start Server at</span><input type="time" data-field="autostartTime" value="${escapeHtml(toTimeInput(server.autostartTime))}" /></label>
              <label class="check-line"><input type="checkbox" data-field="autostartUpdate" ${server.autostartUpdate ? "checked" : ""} /> Perform update (Prior to Server Starting)</label>
            </div>
          </section>

          <section class="section ${open("shutdown")}" data-section="shutdown">
            <button type="button" class="section-toggle"><span class="chev">▶</span> Automatic Shutdown / Restart</button>
            <div class="section-body">
              <div class="day-row">${dayChecks("shutdownDays", server.shutdownDays)}</div>
              <label class="field"><span>Shutdown at</span><input type="time" data-field="shutdownTime" value="${escapeHtml(toTimeInput(server.shutdownTime))}" /></label>
              <label class="check-line"><input type="checkbox" data-field="performUpdate" ${server.performUpdate ? "checked" : ""} /> Perform update</label>
              <label class="check-line"><input type="checkbox" data-field="thenRestart" ${server.thenRestart ? "checked" : ""} /> Then restart</label>
            </div>
          </section>

          <section class="section ${open("config")}" data-section="config">
            <button type="button" class="section-toggle"><span class="chev">▶</span> Server Configuration</button>
            <div class="section-body">
            <div class="action-row">
              <button type="button" class="btn secondary" data-action="open-game-ini">Edit Game.ini</button>
              <button type="button" class="btn secondary" data-action="open-gus-ini">Edit GameUserSettings.ini</button>
            </div>
            </div>
          </section>

          <section class="section ${open("backup")}" data-section="backup">
            <button type="button" class="section-toggle"><span class="chev">▶</span> Automatic World Save Backup</button>
            <div class="section-body">
              <label class="field">
                <span>Interval</span>
                <select data-field="autoBackupInterval">
                  ${INTERVALS.map(v => `<option value="${v}" ${server.autoBackupInterval === v ? "selected" : ""}>${v}</option>`).join("")}
                </select>
              </label>
              <label class="field">
                <span>Keep last N backups</span>
                <input type="number" min="10" max="100" data-field="backupLimit" value="${escapeHtml(server.backupLimit || "10")}" />
              </label>
              <div class="field">
                <span class="field-label">Backup Folder</span>
                <div class="path-row">
                  <input class="inline-input" data-field="autoBackupDest" value="${escapeHtml(server.autoBackupDest || "")}" />
                  <button type="button" class="btn secondary" data-action="validate-backup">Browse</button>
                </div>
              </div>
              <div class="action-row">
                <button type="button" class="btn primary" data-action="backup" ${server.backupInProgress ? "disabled" : ""}>Backup Now</button>
                <label class="check-line"><input type="checkbox" data-field="autoBackupEnabled" ${server.autoBackupEnabled ? "checked" : ""} /> Enable Auto Backup</label>
              </div>
            </div>
          </section>

          <section class="section ${open("logs")}" data-section="logs">
            <button type="button" class="section-toggle"><span class="chev">▶</span> Logs</button>
            <div class="section-body">
              <div class="field">
                <span class="field-label">Game Log Location</span>
                <div class="path-row">
                  <input class="inline-input" data-field="logLocation" value="${escapeHtml(server.logLocation || "")}" />
                  <button type="button" class="btn secondary" data-action="validate-logs">Browse</button>
                </div>
              </div>
              <div class="field">
                <span class="field-label">Update Log Location</span>
                <div class="path-row">
                  <input class="inline-input" data-field="updateLogLocation" value="${escapeHtml(server.updateLogLocation || "")}" />
                  <button type="button" class="btn secondary" data-action="validate-update-logs">Browse</button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <aside class="server-console">
        <section class="console-panel">
          <div class="console-toolbar">
            <strong class="console-title">Console</strong>
            <div class="console-live-status" id="console-live-status" data-state="live"><i></i><b>Live</b></div>
            <span class="console-hint">${escapeHtml(rconHint(server))}</span>
            <div class="console-tools">
              <button type="button" class="btn secondary" data-action="console-clear">Clear</button>
              <button type="button" class="btn secondary" data-action="console-players">ListPlayers</button>
              <button type="button" class="btn secondary" data-action="console-getchat">GetChat</button>
            </div>
          </div>
          <div class="console-output" id="console-output"><div class="console-empty">Live log and RCON output will appear here…</div></div>
          <form class="console-command" id="console-form">
            <label class="chat-toggle" title="Send as ServerChat"><input type="checkbox" id="console-as-chat" /> Chat</label>
            <input id="console-input" type="text" autocomplete="off" spellcheck="false" placeholder="RCON command or chat message" />
            <button type="submit" class="btn primary">Send</button>
          </form>
        </section>
      </aside>
    </div>
  `;

  connectConsole(server.id);
}

function toTimeInput(value) {
  const text = String(value || "09:00");
  const match = text.match(/^(\d{1,2}):(\d{2})/);
  if (!match) return "09:00";
  return `${String(match[1]).padStart(2, "0")}:${match[2]}`;
}

function fromTimeInput(value) {
  return String(value || "09:00").slice(0, 5);
}

function render() {
  renderTabs();
  renderServer(activeServer());
}

async function refreshState({ silent = false } = {}) {
  try {
    const data = await api("/api/state");
    const prevFocus = document.activeElement;
    const focusKey = prevFocus?.dataset?.field
      ? `${prevFocus.closest("[data-server-id]")?.dataset.serverId}:${prevFocus.dataset.field}:${prevFocus.dataset.index ?? ""}`
      : null;
    const selectionStart = prevFocus?.selectionStart;
    const selectionEnd = prevFocus?.selectionEnd;

    state.servers = data.servers || [];
    state.activity = data.activity || [];
    window.__arkHost = data.host || null;
    if (!state.servers.find(s => s.id === state.activeId)) {
      state.activeId = state.servers[0]?.id || null;
    }

    // Keep the live console mounted — only refresh chrome/stats on poll
    const page = workspace.querySelector(`[data-server-id="${state.activeId}"]`);
    const consoleMounted = Boolean(page && document.getElementById("console-output"));
    if (consoleMounted || (focusKey && prevFocus && ["INPUT", "SELECT", "TEXTAREA"].includes(prevFocus.tagName))) {
      renderTabs();
      updateLiveStats(activeServer());
      const hint = document.querySelector(".console-hint");
      if (hint && activeServer()) hint.textContent = rconHint(activeServer());
      if (state.activeId) connectConsole(state.activeId);
    } else {
      render();
    }

    if (focusKey) {
      const [id, field, index] = focusKey.split(":");
      const el = workspace.querySelector(
        index !== ""
          ? `[data-server-id="${id}"] [data-field="${field}"][data-index="${index}"]`
          : `[data-server-id="${id}"] [data-field="${field}"]`
      );
      if (el) {
        el.focus();
        if (typeof selectionStart === "number" && el.setSelectionRange) {
          try { el.setSelectionRange(selectionStart, selectionEnd); } catch { /* ignore */ }
        }
      }
    }
  } catch (err) {
    if (!silent) {
      workspace.innerHTML = `<div class="empty-view"><p>Could not reach manager API.<br>${escapeHtml(err.message)}</p></div>`;
    }
  }
}

function setStatTone(card, tone) {
  if (!card) return;
  card.classList.remove("good", "warn", "bad");
  if (tone) card.classList.add(tone);
}

function updateLiveStats(server) {
  if (!server) return;
  const page = workspace.querySelector(`[data-server-id="${server.id}"]`);
  if (!page) return;
  const cards = [...page.querySelectorAll(".stats .stat-card")];
  const updating = String(server.status).toLowerCase() === "updating";
  const busy = state.busy.has(server.id) || updating;
  const running = String(server.status).toLowerCase() === "running";
  const playerCount = Number(server.players) || 0;
  const statusUi = statusDisplay(server);

  if (cards[0]) {
    const strong = cards[0].querySelector("strong");
    if (strong) strong.textContent = statusUi.label;
    setStatTone(cards[0], statusUi.tone);
  }
  if (cards[1]) {
    const strong = cards[1].querySelector("strong");
    if (strong) strong.textContent = server.availability || "Offline";
    setStatTone(cards[1], availabilityClass(server.availability));
  }
  if (cards[2]) {
    const strong = cards[2].querySelector("strong");
    if (strong) strong.textContent = `${playerCount} / ${Number(server.maxPlayers) || 70}`;
    setStatTone(cards[2], playerCount > 0 ? "good" : "");
    const namesEl = cards[2].querySelector("[data-player-names]");
    if (namesEl) namesEl.innerHTML = playerRosterHtml(server);
  }
  if (cards[3]) {
    const strong = cards[3].querySelector("strong");
    if (strong) strong.textContent = server.firewallStatus || "Not Checked";
    setStatTone(cards[3], firewallClass(server.firewallStatus));
  }

  const toggle = page.querySelector("[data-action='toggle']");
  if (toggle) {
    toggle.textContent = running ? "Stop" : "Start";
    toggle.classList.toggle("stop", running);
    toggle.classList.toggle("start", !running);
    toggle.disabled = busy;
  }
  const updateBtn = page.querySelector("[data-action='update']");
  if (updateBtn) updateBtn.disabled = busy;
  renderTabs();
  maybePromptRepair(server);
}

async function askRepairConsent(server) {
  return new Promise(resolve => {
    const message = document.getElementById("repair-message");
    if (message) {
      message.textContent =
        `SteamCMD reported app state 0x6 for "${server.profile}". This usually means a stuck or corrupt install. Repair will delete everything under the install folder except ShooterGame\\Saved (worlds and configs), then redownload the server.`;
    }
    repairDialog.showModal();
    const onOk = () => { cleanup(); resolve(true); };
    const onCancel = () => { cleanup(); resolve(false); };
    function cleanup() {
      repairDialog.close();
      document.getElementById("repair-ok").removeEventListener("click", onOk);
      document.getElementById("repair-cancel").removeEventListener("click", onCancel);
    }
    document.getElementById("repair-ok").addEventListener("click", onOk);
    document.getElementById("repair-cancel").addEventListener("click", onCancel);
  });
}

async function maybePromptRepair(server) {
  if (!server) return;
  if (!server.needsRepair || server.updating) {
    if (!server.needsRepair) state.repairPrompted.delete(server.id);
    return;
  }
  if (state.repairPrompted.has(server.id) || repairDialog?.open) return;
  state.repairPrompted.add(server.id);
  const ok = await askRepairConsent(server);
  if (!ok) return;
  state.repairPrompted.delete(server.id);
  toast("Repair & redownload started — watch the Console", "success");
  connectConsole(server.id);
  await api(`/api/servers/${server.id}/update`, { method: "POST", body: { repair: true } });
  await refreshState({ silent: true });
}

async function confirmDanger(title, message, okLabel = "Delete") {
  return new Promise(resolve => {
    document.getElementById("confirm-title").textContent = title;
    document.getElementById("confirm-message").textContent = message;
    const okBtn = document.getElementById("confirm-ok");
    okBtn.textContent = okLabel;
    confirmDialog.showModal();
    const onOk = () => { cleanup(); resolve(true); };
    const onCancel = () => { cleanup(); resolve(false); };
    function cleanup() {
      confirmDialog.close();
      okBtn.textContent = "Delete";
      okBtn.removeEventListener("click", onOk);
      document.getElementById("confirm-cancel").removeEventListener("click", onCancel);
    }
    okBtn.addEventListener("click", onOk);
    document.getElementById("confirm-cancel").addEventListener("click", onCancel);
  });
}

async function confirmDelete(server) {
  return confirmDanger(
    "Delete Server Profile",
    `Delete profile "${server.profile}"? This does not delete server files on disk.`,
    "Delete"
  );
}

async function waitForManagerBack(timeoutMs = 120000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    await new Promise(r => setTimeout(r, 1500));
    try {
      const res = await fetch("/api/state", { cache: "no-store" });
      if (res.ok) return true;
    } catch { /* still down */ }
  }
  return false;
}

async function askFirewallConsent(server) {
  return new Promise(resolve => {
    const message = document.getElementById("firewall-message");
    if (message) {
      message.textContent =
        `Allow Ark Manager to add Windows firewall rules for "${server.profile}" (game, query, and RCON ports) when this server starts? Choose "Allow & start" once and you will not be asked again for this profile. "Start without firewall" or "Cancel start" will ask again next time.`;
    }
    firewallDialog.showModal();
    const onAllow = () => { cleanup(); resolve("allow"); };
    const onSkip = () => { cleanup(); resolve("skip"); };
    const onCancel = () => { cleanup(); resolve("cancel"); };
    function cleanup() {
      firewallDialog.close();
      document.getElementById("firewall-allow").removeEventListener("click", onAllow);
      document.getElementById("firewall-skip").removeEventListener("click", onSkip);
      document.getElementById("firewall-cancel").removeEventListener("click", onCancel);
    }
    document.getElementById("firewall-allow").addEventListener("click", onAllow);
    document.getElementById("firewall-skip").addEventListener("click", onSkip);
    document.getElementById("firewall-cancel").addEventListener("click", onCancel);
  });
}

async function startServerWithFirewallPrompt(server) {
  let applyFirewall = Boolean(server.firewallAutoApproved);
  if (!applyFirewall) {
    const choice = await askFirewallConsent(server);
    if (choice === "cancel") return false;
    applyFirewall = choice === "allow";
    // skip / allow both leave approved only when allow — skip asks again next start
  }
  await withBusy(server.id, async () => {
    await api(`/api/servers/${server.id}/start`, {
      method: "POST",
      body: { applyFirewall }
    });
  });
  if (applyFirewall) {
    server.firewallAutoApproved = true;
    toast("Approve the Windows admin prompt if it appears — firewall rules will auto-apply after that", "success");
  }
  return true;
}

async function withBusy(id, fn) {
  state.busy.add(id);
  render();
  try {
    return await fn();
  } finally {
    state.busy.delete(id);
    await refreshState({ silent: true });
  }
}

async function validatePath(field, label) {
  const server = activeServer();
  if (!server) return;
  const value = String(server[field] || "").trim();
  if (!value) {
    toast(`Enter a ${label} path first`, "error");
    return;
  }
  try {
    const result = await api("/api/path/validate", { method: "POST", body: { path: value } });
    if (result.exists) toast(`${label} path is valid`, "success");
    else toast(`${label} path was not found on this machine`, "error");
  } catch (err) {
    toast(err.message, "error");
  }
}

tabsEl.addEventListener("click", async event => {
  const closeId = event.target.closest("[data-close]")?.dataset.close;
  if (closeId) {
    event.stopPropagation();
    const server = state.servers.find(s => s.id === closeId);
    if (!server) return;
    if (!(await confirmDelete(server))) return;
    try {
      await api(`/api/servers/${closeId}`, { method: "DELETE" });
      if (state.activeId === closeId) state.activeId = null;
      toast(`Deleted ${server.profile}`);
      await refreshState();
    } catch (err) {
      toast(err.message, "error");
    }
    return;
  }
  const tab = event.target.closest(".tab");
  if (!tab) return;
  state.activeId = tab.dataset.id;
  render();
});

let dragId = null;
tabsEl.addEventListener("dragstart", event => {
  const tab = event.target.closest(".tab");
  if (!tab) return;
  dragId = tab.dataset.id;
  event.dataTransfer.effectAllowed = "move";
});
tabsEl.addEventListener("dragover", event => {
  event.preventDefault();
});
tabsEl.addEventListener("drop", async event => {
  event.preventDefault();
  const tab = event.target.closest(".tab");
  if (!tab || !dragId || dragId === tab.dataset.id) return;
  const ids = [...state.servers].sort((a, b) => a.order - b.order).map(s => s.id);
  const from = ids.indexOf(dragId);
  const to = ids.indexOf(tab.dataset.id);
  if (from < 0 || to < 0) return;
  ids.splice(to, 0, ids.splice(from, 1)[0]);
  try {
    const data = await api("/api/servers/reorder", { method: "POST", body: { ids } });
    state.servers = data.servers || state.servers;
    render();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    dragId = null;
  }
});

document.getElementById("btn-add").addEventListener("click", async () => {
  try {
    const server = await api("/api/servers", { method: "POST", body: { profile: "New Server" } });
    state.activeId = server.id;
    toast("Created New Server", "success");
    await refreshState();
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("btn-theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  applyTheme(next);
});

function applyTheme(theme) {
  const value = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = value;
  localStorage.setItem("ark-theme", value);
  const btn = document.getElementById("btn-theme");
  if (btn) btn.textContent = value === "light" ? "Dark" : "Light";
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = value === "light" ? "#f4f1ea" : "#10141c";
}

applyTheme(localStorage.getItem("ark-theme") === "light" ? "light" : "dark");

document.getElementById("btn-restart-manager").addEventListener("click", async () => {
  const ok = await confirmDanger(
    "Restart Ark Manager",
    "This restarts Ark Server Manager and checks GitHub for updates (same as Start Ark Manager.cmd). Your ARK game servers are left running. Continue?",
    "Restart"
  );
  if (!ok) return;
  const btn = document.getElementById("btn-restart-manager");
  if (btn) btn.disabled = true;
  toast("Restarting manager — pulling updates, then coming back…", "info");
  try {
    await api("/api/manager/restart", { method: "POST", body: {} });
  } catch (err) {
    // Expected once the process exits mid-request; keep waiting for it to return.
    if (!/failed to fetch|networkerror|load failed|fetch/i.test(String(err.message || err))) {
      if (btn) btn.disabled = false;
      toast(err.message, "error");
      return;
    }
  }
  const back = await waitForManagerBack();
  if (btn) btn.disabled = false;
  if (back) {
    toast("Manager is back — reloading", "success");
    location.reload();
    return;
  }
  toast("Manager has not come back yet. Check the server console, then refresh this page.", "error");
});

document.getElementById("btn-info").addEventListener("click", () => {
  const lans = (window.__arkHost?.lanAddresses || []).map(ip => `http://${ip}:${window.__arkHost.managerPort || 3220}`);
  const p = infoDialog.querySelector(".muted");
  if (p) {
    p.textContent = lans.length
      ? `Any IP can connect. Examples: ${lans.join(" · ")}`
      : "Listening on all interfaces (0.0.0.0). Use this PC's IP and port 3220 from other devices.";
  }
  infoDialog.showModal();
});
document.getElementById("btn-copy-settings").addEventListener("click", () => {
  if (state.servers.length < 2) {
    toast("You need at least two server profiles to copy settings", "error");
    return;
  }
  const from = document.getElementById("copy-from");
  const to = document.getElementById("copy-to");
  const options = state.servers.map(s => `<option value="${s.id}">${escapeHtml(s.profile)}</option>`).join("");
  from.innerHTML = options;
  to.innerHTML = options;
  if (state.servers[1]) to.value = state.servers[1].id;
  copyDialog.showModal();
});

document.querySelectorAll("[data-close]").forEach(btn => {
  btn.addEventListener("click", () => btn.closest("dialog")?.close());
});

document.getElementById("copy-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const body = {
    fromId: form.fromId.value,
    toId: form.toId.value,
    flags: {
      launchArgs: form.launchArgs.checked,
      autoStart: form.autoStart.checked,
      shutdown: form.shutdown.checked,
      backup: form.backup.checked,
      logs: form.logs.checked,
      configFiles: form.configFiles.checked
    }
  };
  try {
    await api("/api/servers/copy-settings", { method: "POST", body });
    copyDialog.close();
    toast("Settings copied", "success");
    await refreshState();
  } catch (err) {
    toast(err.message, "error");
  }
});

workspace.addEventListener("click", async event => {
  const toggle = event.target.closest(".section-toggle");
  if (toggle) {
    const section = toggle.closest(".section");
    const key = section?.dataset.section;
    const server = activeServer();
    if (!server || !key) return;
    const full = `${server.id}:${key}`;
    if (state.openSections.has(full)) state.openSections.delete(full);
    else state.openSections.add(full);
    section.classList.toggle("open");
    return;
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  if (!action) return;
  const server = activeServer();
  if (!server) return;

  try {
    if (action === "toggle") {
      if (String(server.status).toLowerCase() === "running") {
        await withBusy(server.id, async () => {
          await api(`/api/servers/${server.id}/stop`, { method: "POST" });
          toast(`Stopped ${server.profile}`);
        });
      } else {
        const started = await startServerWithFirewallPrompt(server);
        if (started) toast(`Started ${server.profile}`, "success");
      }
    } else if (action === "update") {
      state.repairPrompted.delete(server.id);
      await api(`/api/servers/${server.id}/update`, { method: "POST", body: {} });
      toast("Update / Verify started — watch the Console panel", "success");
      connectConsole(server.id);
      await refreshState({ silent: true });
    } else if (action === "download-steamcmd") {
      toast("Downloading SteamCMD…");
      const result = await api("/api/steamcmd/download", { method: "POST", body: {} });
      schedulePatch(server.id, { steamcmd: result.path });
      toast(`SteamCMD ready at ${result.path}`, "success");
      await refreshState();
    } else if (action === "backup") {
      await withBusy(server.id, async () => {
        await api(`/api/servers/${server.id}/backup`, { method: "POST" });
        toast("Backup complete", "success");
      });
    } else if (action === "open-game-ini") {
      await api(`/api/servers/${server.id}/open-ini`, { method: "POST", body: { kind: "game" } });
      toast("Opened Game.ini");
    } else if (action === "open-gus-ini") {
      await api(`/api/servers/${server.id}/open-ini`, { method: "POST", body: { kind: "gus" } });
      toast("Opened GameUserSettings.ini");
    } else if (action === "validate-install") {
      await validatePath("install", "Install");
    } else if (action === "validate-steamcmd") {
      await validatePath("steamcmd", "SteamCMD");
    } else if (action === "validate-backup") {
      await validatePath("autoBackupDest", "Backup");
    } else if (action === "validate-logs") {
      await validatePath("logLocation", "Game log");
    } else if (action === "validate-update-logs") {
      await validatePath("updateLogLocation", "Update log");
    } else if (action === "console-clear") {
      const el = document.getElementById("console-output");
      if (el) el.innerHTML = `<div class="console-empty">Live log and RCON output will appear here…</div>`;
    } else if (action === "console-players") {
      await openPlayersDialog(server);
    } else if (action === "console-getchat") {
      await sendConsoleCommand(server.id, "GetChat", false);
    }
  } catch (err) {
    toast(err.message, "error");
    await refreshState({ silent: true });
  }
});

async function sendConsoleCommand(serverId, command, asChat) {
  await api(`/api/servers/${serverId}/command`, {
    method: "POST",
    body: { command, asChat: Boolean(asChat) }
  });
}

function hidePlayerContextMenu() {
  if (!playerContextMenu) return;
  playerContextMenu.hidden = true;
  contextPlayer = null;
  document.querySelectorAll(".player-row.active").forEach(el => el.classList.remove("active"));
}

function renderPlayersDialogList(players) {
  const list = document.getElementById("players-dialog-list");
  const sub = document.getElementById("players-dialog-sub");
  if (!list) return;
  const rows = Array.isArray(players) ? players : [];
  if (sub) {
    sub.textContent = rows.length
      ? `${rows.length} online — right-click a player for Kick, Ban, Admin, and more`
      : "No players online right now";
  }
  if (!rows.length) {
    list.innerHTML = `<div class="players-dialog-empty">No players online</div>`;
    return;
  }
  list.innerHTML = rows.map((player, idx) => {
    const ping = formatPingMs(player.pingMs);
    const pingPart = ping
      ? ` <span class="player-name-sep">·</span> <span class="player-ping">${escapeHtml(ping)}</span>`
      : "";
    return `
    <div class="player-row" data-player-index="${idx}" data-player-id="${escapeHtml(player.id || "")}" data-player-name="${escapeHtml(player.name || "")}">
      <div class="player-row-name">${escapeHtml(player.name || "Unknown")}${pingPart}</div>
      <div class="player-row-id">${escapeHtml(player.id || "No EOS/Steam ID in ListPlayers reply")}</div>
    </div>
  `;
  }).join("");
}

async function refreshPlayersDialog() {
  const server = state.servers.find(s => s.id === playersDialogServerId) || activeServer();
  if (!server) return;
  const data = await api(`/api/servers/${server.id}/players`);
  const idx = state.servers.findIndex(s => s.id === server.id);
  if (idx >= 0) {
    state.servers[idx] = {
      ...state.servers[idx],
      players: data.count || 0,
      playerNames: (data.players || []).map(p => p.name),
      playerList: data.players || [],
      serverPingMs: data.serverPingMs == null ? state.servers[idx].serverPingMs : data.serverPingMs
    };
    updateLiveStats(state.servers[idx]);
  }
  renderPlayersDialogList(data.players || []);
}

async function openPlayersDialog(server) {
  playersDialogServerId = server.id;
  const title = document.getElementById("players-dialog-title");
  if (title) title.textContent = `Online Players — ${server.profile}`;
  renderPlayersDialogList(server.playerList || []);
  playersDialog?.showModal();
  hidePlayerContextMenu();
  try {
    await refreshPlayersDialog();
  } catch (err) {
    toast(err.message, "error");
  }
}

function showPlayerContextMenu(event, row) {
  if (!playerContextMenu) return;
  contextPlayer = {
    id: row.dataset.playerId || "",
    name: row.dataset.playerName || ""
  };
  document.querySelectorAll(".player-row.active").forEach(el => el.classList.remove("active"));
  row.classList.add("active");
  playerContextMenu.hidden = false;
  const menuW = playerContextMenu.offsetWidth || 200;
  const menuH = playerContextMenu.offsetHeight || 280;
  let left = event.clientX;
  let top = event.clientY;
  if (left + menuW > window.innerWidth - 8) left = window.innerWidth - menuW - 8;
  if (top + menuH > window.innerHeight - 8) top = window.innerHeight - menuH - 8;
  playerContextMenu.style.left = `${Math.max(8, left)}px`;
  playerContextMenu.style.top = `${Math.max(8, top)}px`;
}

async function runPlayerContextAction(cmd) {
  const server = state.servers.find(s => s.id === playersDialogServerId) || activeServer();
  const player = contextPlayer;
  hidePlayerContextMenu();
  if (!server || !player) return;

  try {
    if (cmd === "copyid") {
      if (!player.id) throw new Error("No player ID available");
      await navigator.clipboard.writeText(player.id);
      toast("Copied player ID", "success");
      return;
    }
    if (cmd === "copyname") {
      await navigator.clipboard.writeText(player.name || "");
      toast("Copied player name", "success");
      return;
    }
    if (cmd === "message") {
      const message = window.prompt(`Message to ${player.name || "player"}:`, "");
      if (message == null || !String(message).trim()) return;
      await api(`/api/servers/${server.id}/player-action`, {
        method: "POST",
        body: { action: "message", playerId: player.id, playerName: player.name, message: String(message).trim() }
      });
      toast(`Message sent to ${player.name}`, "success");
      return;
    }
    if (cmd === "ban" || cmd === "kick" || cmd === "kill") {
      const label = cmd === "ban" ? "Ban" : cmd === "kick" ? "Kick" : "Kill";
      if (!window.confirm(`${label} ${player.name || player.id}?`)) return;
    }
    let ue4Id = "";
    if (cmd === "kill") {
      // ListPlayers gives EOS IDs on ASA; KillPlayer needs numeric UE4 IDs.
      if (!/^\d{3,12}$/.test(player.id || "")) {
        ue4Id = window.prompt(
          `KillPlayer needs the numeric UE4 player ID (not the EOS ID).\n\n${player.name}\nEOS: ${player.id}\n\nEnter UE4 ID to kill in-world, or Cancel and use Kick to disconnect:`,
          ""
        );
        if (ue4Id == null || !String(ue4Id).trim()) return;
        if (!/^\d{3,12}$/.test(String(ue4Id).trim())) {
          throw new Error("UE4 player ID must be numeric");
        }
      }
    }
    if (!player.id && cmd !== "copyname") {
      throw new Error("This player has no EOS/Steam ID in ListPlayers — cannot run that action");
    }
    const result = await api(`/api/servers/${server.id}/player-action`, {
      method: "POST",
      body: {
        action: cmd,
        playerId: player.id,
        playerName: player.name,
        ...(ue4Id ? { ue4Id: String(ue4Id).trim() } : {})
      }
    });
    if (cmd === "makeadmin") {
      toast(`${player.name} added to AllowedCheaterSteamIDs.txt`, "success");
    } else if (result?.silentAck || /accepted by the server/i.test(result?.reply || "")) {
      toast(`${cmd} accepted by server (no ARK output is normal)`, "success");
    } else {
      toast(`${cmd} sent for ${player.name || player.id}`, "success");
    }
    if (["kick", "ban", "kill"].includes(cmd)) await refreshPlayersDialog();
  } catch (err) {
    toast(err.message, "error");
  }
}

playersDialog?.addEventListener("close", () => hidePlayerContextMenu());

document.getElementById("players-refresh")?.addEventListener("click", async () => {
  try {
    await refreshPlayersDialog();
    toast("Player list refreshed", "success");
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("players-dialog-list")?.addEventListener("contextmenu", event => {
  const row = event.target.closest(".player-row");
  if (!row) return;
  event.preventDefault();
  showPlayerContextMenu(event, row);
});

playerContextMenu?.addEventListener("click", async event => {
  const btn = event.target.closest("[data-player-cmd]");
  if (!btn) return;
  await runPlayerContextAction(btn.dataset.playerCmd);
});

document.addEventListener("click", event => {
  if (playerContextMenu && !playerContextMenu.hidden && !event.target.closest("#player-context-menu")) {
    hidePlayerContextMenu();
  }
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape") hidePlayerContextMenu();
});

workspace.addEventListener("submit", async event => {
  if (event.target?.id !== "console-form") return;
  event.preventDefault();
  const server = activeServer();
  if (!server) return;
  const input = document.getElementById("console-input");
  const asChat = document.getElementById("console-as-chat")?.checked;
  const command = input?.value?.trim();
  if (!command) return;
  input.value = "";
  try {
    await sendConsoleCommand(server.id, command, asChat);
  } catch (err) {
    toast(err.message, "error");
  }
});

workspace.addEventListener("input", event => {
  const el = event.target;
  const server = activeServer();
  if (!server) return;

  if (el.closest("[data-launch-builder]") && el.hasAttribute("data-launch")) {
    syncLaunchBuilderToArgs(server.id);
    return;
  }

  const field = el.dataset.field;
  if (!field) return;

  if (field === "autostartDays" || field === "shutdownDays") {
    const index = Number(el.dataset.index);
    const next = [...(server[field] || [false, false, false, false, false, false, false])];
    next[index] = el.checked;
    schedulePatch(server.id, { [field]: next });
    return;
  }

  if (el.type === "checkbox") {
    schedulePatch(server.id, { [field]: el.checked });
    return;
  }

  let value = el.value;
  if (field === "autostartTime" || field === "shutdownTime") value = fromTimeInput(value);
  schedulePatch(server.id, { [field]: value });
});

workspace.addEventListener("change", event => {
  const el = event.target;
  const server = activeServer();
  if (!server) return;
  if (el.closest("[data-launch-builder]") && el.hasAttribute("data-launch")) {
    syncLaunchBuilderToArgs(server.id);
  }
});

await refreshState();
state.busy.clear();
state.pollTimer = setInterval(() => refreshState({ silent: true }), 2000);
