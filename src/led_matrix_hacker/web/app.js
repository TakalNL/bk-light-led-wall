"use strict";
const $ = id => document.getElementById(id);
let token = location.hash.slice(1) || sessionStorage.getItem("led-wall-access") || "";
if (location.hash) history.replaceState(null, "", location.pathname);
let ws, clientId, state = {}, panels = [], dirty = false, previewURL, reconnectTimer;
const held = new Set();
const pointers = new Map();
const keyboard = new Set();
let own = false;
let initialClaimPending = false;
let phoneQR;
let panelBusy = false, savedLayout = "";

async function loadPhoneAccess() {
  const headers = {Authorization: `Bearer ${token}`};
  const response = await fetch('/api/access', {headers});
  if (!response.ok) return;
  const access = await response.json();
  $("phone-code").textContent = access.code;
  $("phone-details").hidden = access.urls.length === 0;
  if (!access.urls.length) { $("phone-help").textContent = "Phone access is off. Start LED Wall with local-network access enabled."; return; }
  $("phone-address").replaceChildren();
  access.urls.forEach((url,index) => {const option=document.createElement('option');option.value=index;option.textContent=url;$("phone-address").append(option);});
  $("phone-address").onchange = async () => {
    const index = Number($("phone-address").value);
    $("phone-link").href = access.urls[index];
    $("phone-link").textContent = access.urls[index];
    const qr = await fetch(`/api/access/${index}/qr.png`, {headers});
    if (qr.ok) {if(phoneQR)URL.revokeObjectURL(phoneQR);phoneQR=URL.createObjectURL(await qr.blob());$("phone-qr").src=phoneQR;}
  };
  await $("phone-address").onchange();
}

function showError(error) {
  $("error").textContent = String(error.message || error);
  $("error").hidden = false;
}
function send(data) {
  if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
}
async function api(action, data = {}, raw = false) {
  $("error").hidden = true;
  const headers = {Authorization: `Bearer ${token}`, "X-LED-Controller": clientId || ""};
  if (!raw) headers["Content-Type"] = "application/json";
  const result = await fetch(`/api/${action}`, {method:"POST", headers, body:raw ? data : JSON.stringify(data)});
  const text = await result.text();
  let body;
  try { body = JSON.parse(text); } catch { throw new Error(text || "Access denied. Open the server access link."); }
  if (!result.ok) throw new Error(body.error || "The request could not be completed.");
  return body;
}
function run(action) { return Promise.resolve().then(action).catch(showError); }
function neutral(release = false) {
  held.clear(); pointers.clear(); keyboard.clear();
  document.querySelectorAll("[data-key]").forEach(button => button.classList.remove("pressed"));
  if (own) send({type:release ? "release" : "input", keys:[]});
}
function updateKeys() {
  held.clear();
  for (const key of keyboard) held.add(key);
  for (const key of pointers.values()) held.add(key);
  document.querySelectorAll("[data-key]").forEach(button => button.classList.toggle("pressed", held.has(button.dataset.key)));
  if (own) send({type:"input", keys:[...held]});
}
function openSocket() {
  clearTimeout(reconnectTimer);
  if (!token) { $("access").hidden = false; $("workspace").hidden = true; return; }
  $("access").hidden = true; $("workspace").hidden = false;
  sessionStorage.setItem("led-wall-access", token);
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws`);
  ws.binaryType = "blob";
  ws.onopen = () => send({token});
  ws.onmessage = event => {
    if (event.data instanceof Blob) {
      const old = previewURL;
      previewURL = URL.createObjectURL(new Blob([event.data], {type:"image/png"}));
      $("preview").src = previewURL;
      if (old) URL.revokeObjectURL(old);
      return;
    }
    const message = JSON.parse(event.data);
    if (message.type === "ready") { clientId = message.client_id; initialClaimPending = true; run(loadPhoneAccess); }
    else if (message.type === "state") update(message);
    else if (message.type === "error") showError(message.message);
  };
  ws.onclose = event => {
    own = false; neutral(); $("connection").textContent = "Service disconnected";
    $("control-status").textContent = "Browser connection lost. Game input has been released.";
    document.querySelectorAll("button[data-mode], [data-key], #play, #restart, #connect, #disconnect, #save, #alignment, #media-file, #panels button, #panels input, #panels select").forEach(el => el.disabled = true);
    if (event.code === 1008) { token = ""; sessionStorage.removeItem("led-wall-access"); $("access").hidden = false; }
    else reconnectTimer = setTimeout(openSocket, 1500);
  };
}
function update(next) {
  state = next;
  if (initialClaimPending) {
    initialClaimPending = false;
    if (!next.controller && !document.hidden) send({type:"claim"});
  }
  const wasOwn = own;
  own = next.controller === clientId;
  if (wasOwn && !own) neutral();
  $("connection").textContent = next.connection;
  $("connection").classList.toggle("connected", next.connection === "connected");
  $("progress").textContent = next.progress;
  $("dimensions").textContent = `${next.size[0]} × ${next.size[1]}`;
  $("content-title").textContent = ({identify:"Identify your panels",demo:"Across the seam",snake:"Snake",micromaze:"Micromaze",starfall:"Starfall",clear:"A blank canvas",media:"Your media"})[next.mode];
  $("control-status").textContent = own ? "You have control. Other browsers can watch." : "Viewing only. Take control to change playback or play.";
  $("claim").hidden = own;
  $("claim").textContent = next.controller ? "Take control" : "Start controlling";
  const game = ["snake", "micromaze", "starfall"].includes(next.mode);
  $("game-controls").hidden = !(game || next.mode === "media");
  document.querySelector(".controller").hidden = !game;
  $("game-status").textContent = game ? `${next.game_phase} · score ${next.score}` : (next.media_playing ? "Playing" : "Paused");
  $("fire").hidden = next.mode !== "starfall";
  $("strafe-left").hidden = $("strafe-right").hidden = next.mode !== "micromaze";
  document.querySelectorAll("[data-mode]").forEach(button => {button.classList.toggle("active", button.dataset.mode === next.mode); button.disabled = !own;});
  document.querySelectorAll("[data-key], #play, #restart, #save, #alignment, #media-file").forEach(el => el.disabled = !own);
  $("connect").disabled = !own || panelBusy || !next.configured || next.connection !== "disconnected" || next.layout.panels.every(p => (next.excluded_panels || []).includes(p.device));
  $("disconnect").disabled = !own || panelBusy || next.connection === "disconnected";
  $("scan").disabled = next.scanning || next.connection !== "disconnected";
  $("scan").textContent = next.scanning ? "Looking for panels…" : "Find nearby panels";
  $("alignment").checked = next.timing_alignment;
  $("save").disabled = !own || next.connection !== "disconnected";
  $("timing").textContent = next.stats.frames ? `${next.stats.frames} frames sent · reply gap ${Math.round(next.stats.completion_skew_ms)} ms` : "";
  if (next.error) showError(next.error);
  const signature = JSON.stringify(next.layout);
  if (!dirty && signature !== savedLayout) {
    savedLayout = signature;
    panels = (next.layout?.panels || []).map(p => ({...p})); inferGap(); renderPanels();
  }
  lockLayout();
}
function lockLayout() {
  const editable = own && !panelBusy && state.connection === 'disconnected' && !state.scanning;
  document.querySelectorAll('#panels input, #panels select, #stack, #row, #reverse, #gap').forEach(el => el.disabled = !editable);
  document.querySelectorAll('[data-add-panel]').forEach(el => el.disabled = !editable || panels.length >= 16 || panels.some(p => p.device === el.dataset.addPanel));
  document.querySelectorAll('#panels .panel').forEach(card => {
    const device = card.dataset.device;
    const saved = state.layout?.panels.some(p => p.device === device);
    const excluded = (state.excluded_panels || []).includes(device);
    const connected = saved && !excluded && state.connection === 'connected';
    const busy = panelBusy || ['connecting','disconnecting'].includes(state.connection);
    card.querySelector('.panel-status').textContent = !saved ? 'Not saved yet' : excluded ? 'Disconnected · kept in layout' : connected ? 'Connected' : state.connection === 'connecting' ? 'Connecting…' : 'Ready to connect';
    const toggle = card.querySelector('.panel-toggle');
    toggle.textContent = connected ? 'Disconnect' : 'Connect';
    toggle.dataset.action = connected ? 'disconnect' : 'connect';
    toggle.disabled = !own || busy || state.scanning || dirty || !saved;
    card.querySelector('.remove').disabled = !own || busy || state.scanning || (dirty && saved);
  });
}
async function changePanel(device, action) {
  panelBusy = true; neutral(); lockLayout();
  try { update(await api('panel', {device, action})); }
  finally { panelBusy = false; update(state); }
}
function inferGap() {
  if (panels.length > 1) {
    const a = panels[0], b = panels[1];
    const vertical = a.x === b.x;
    const length = vertical ? ([90,270].includes(a.rotation) ? 64 : 16) : ([90,270].includes(a.rotation) ? 16 : 64);
    $("gap").value = Math.max(0, Math.min(32, (vertical ? b.y-a.y : b.x-a.x)-length));
  }
}
function renderPanels() {
  $("panels").replaceChildren(); $("empty-panels").hidden = panels.length > 0;
  $("panel-count").textContent = panels.length === 0 ? 'No panels selected.' : panels.length === 1 ? '1 panel · standalone display' : `${panels.length} panels · shared canvas${panels.length > 2 ? ' · experimental hardware configuration' : ''}`;
  panels.forEach((panel, i) => {
    const card = document.createElement("div"); card.className = "panel"; card.dataset.device = panel.device;
    const head = document.createElement("div"); head.className = "panel-head";
    const number = document.createElement("span"); number.className = "panel-number"; number.textContent = i+1;
    const name = document.createElement("span"); name.className = "panel-name"; name.textContent = panel.device;
    head.append(number, name); card.append(head);
    const status = document.createElement('p'); status.className = 'panel-status muted'; card.append(status);
    const actions = document.createElement('div'); actions.className = 'toolbar panel-actions';
    const toggle = document.createElement('button'); toggle.className = 'panel-toggle secondary';
    toggle.onclick = () => run(() => changePanel(panel.device, toggle.dataset.action));
    const remove = document.createElement('button'); remove.textContent = 'Remove'; remove.className = 'remove secondary';
    remove.onclick = () => run(async () => {
      if (state.layout?.panels.some(p => p.device === panel.device)) await changePanel(panel.device, 'remove');
      else {panels.splice(i,1); dirty = true; arrange(true);}
    });
    actions.append(toggle, remove); card.append(actions);
    const fields = document.createElement("div"); fields.className = "panel-fields";
    for (const [key, title] of [["x","X"],["y","Y"],["rotation","Rotation"]]) {
      const label = document.createElement("label"); label.textContent = title;
      const input = document.createElement(key === "rotation" ? "select" : "input");
      if (key === "rotation") for (const angle of [0,90,180,270]) { const option = document.createElement("option"); option.value = angle; option.textContent = `${angle}°`; input.append(option); }
      else {input.type = "number"; input.min = "0"; input.max = "511";}
      input.value = panel[key]; input.onchange = () => {panel[key] = Number(input.value); dirty = true; lockLayout();};
      label.append(input); fields.append(label);
    }
    card.append(fields); $("panels").append(card);
  });
  lockLayout();
}
function arrange(vertical) {
  let offset = 0; const gap = Number($("gap").value);
  panels.forEach(p => {p.x = vertical ? 0 : offset; p.y = vertical ? offset : 0; offset += (vertical ? ([90,270].includes(p.rotation)?64:16) : ([90,270].includes(p.rotation)?16:64))+gap;});
  dirty = true; renderPanels();
}
$("access-form").onsubmit = async event => {
  event.preventDefault(); $("access-error").hidden = true;
  try {
    const response = await fetch('/api/pair', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:$("access-code").value.trim()})});
    if (!response.ok) throw new Error(await response.text());
    token = (await response.json()).token; $("access-code").value = ''; openSocket();
  } catch(error) {$("access-error").textContent=error.message;$("access-error").hidden=false;}
};
$("claim").onclick = () => send({type:"claim", takeover:true});
$("connect").onclick = () => run(() => api("connect"));
$("disconnect").onclick = () => run(() => api("disconnect"));
$("scan").onclick = () => run(async () => {
  const report = await api("scan"); $("devices").replaceChildren();
  const devices = report.devices.filter(d => /led|pixel/i.test(`${d.name || ""} ${d.advertised_name || ""}`) || d.service_uuids.some(u => u.includes("00fa")));
  if (!devices.length) { $("devices").textContent = "No panel advertisements found. Check power, Bluetooth, range, and close the vendor app."; return; }
  for (const device of devices) {
    const row = document.createElement("div"); row.className = "device";
    const details = document.createElement("div"), name = document.createElement("strong"), id = document.createElement("small");
    name.textContent = device.advertised_name || device.name || "LED panel"; id.textContent = device.identifier; details.append(name,id);
    const add = document.createElement("button"); add.textContent = panels.some(p => p.device === device.identifier) ? "Added" : "Add";
    add.dataset.addPanel = device.identifier;
    add.disabled = panels.some(p => p.device === device.identifier);
    add.onclick = () => {panels.push({device:device.identifier,x:0,y:0,rotation:0}); arrange(true); add.textContent="Added"; add.disabled=true;};
    row.append(details,add); $("devices").append(row);
  }
  lockLayout();
});
$("stack").onclick = () => arrange(true); $("row").onclick = () => arrange(false);
$("reverse").onclick = () => {const vertical = panels.length < 2 || panels[0].x === panels[1].x; panels.reverse(); arrange(vertical);};
$("gap").onchange = () => arrange(panels.length < 2 || panels[0].x === panels[1].x);
$("save").onclick = () => run(async () => {const next=await api("layout", {version:1,panels}); dirty=false; update(next);});
$("alignment").onchange = () => run(() => api("timing", {enabled:$("alignment").checked}));
document.querySelectorAll("[data-mode]").forEach(button => button.onclick = () => run(() => {neutral(); return api("mode", {mode:button.dataset.mode});}));
$("play").onclick = () => {neutral(); send({type:"playback",action:"toggle"});};
$("restart").onclick = () => {neutral(); send({type:"playback",action:"restart"});};
$("media-file").onchange = () => run(async () => {
  const file = $("media-file").files[0]; if (!file) return;
  if (file.size > 8*1024*1024) throw new Error("Choose a file smaller than 8 MB.");
  $("media-status").textContent = "Opening your media…";
  await api(`media?fit=${encodeURIComponent($("fit").value)}`, file, true);
  $("media-status").textContent = `${file.name} · host must remain running during playback`;
});
document.querySelectorAll("[data-key]").forEach(button => {
  button.addEventListener("pointerdown", event => {if(!own)return; event.preventDefault(); button.setPointerCapture(event.pointerId); pointers.set(event.pointerId,button.dataset.key); updateKeys();});
  for (const type of ["pointerup","pointercancel","lostpointercapture"]) button.addEventListener(type, event => {pointers.delete(event.pointerId); updateKeys();});
  button.addEventListener("contextmenu", event => event.preventDefault());
});
const keyMap = {ArrowUp:"up",w:"up",ArrowDown:"down",s:"down",ArrowLeft:"left",a:"left",ArrowRight:"right",d:"right",f:"fire",q:"strafe_left",e:"strafe_right"};
window.addEventListener("keydown", event => {
  if (!own || /INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) return;
  if (!event.repeat && [" ","Enter","p"].includes(event.key)) {event.preventDefault(); neutral(); send({type:"playback",action:"toggle"});}
  else if (!event.repeat && event.key.toLowerCase() === "r") {neutral();send({type:"playback",action:"restart"});}
  const key = keyMap[event.key] || keyMap[event.key.toLowerCase()];
  if (key) {event.preventDefault();keyboard.add(key);updateKeys();}
});
window.addEventListener("keyup", event => {const key=keyMap[event.key]||keyMap[event.key.toLowerCase()];if(key){keyboard.delete(key);updateKeys();}});
window.addEventListener("blur", () => {
  neutral();
  if (own && ["snake","micromaze","starfall"].includes(state.mode)) send({type:"playback",action:"pause"});
});
document.addEventListener("visibilitychange", () => {if(document.hidden)neutral(true);});
window.addEventListener("pagehide", () => neutral(true));
setInterval(() => {if(own && !document.hidden)send({type:"input",keys:[...held]});},250);
openSocket();
