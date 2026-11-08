// Stage page: agent transcript (OpenCode events), KG (Cytoscape), structure (3Dmol), 96-well plate (SVG),
// recorded OT-2 video, and the robot status feed replayed in sync with the video.
"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const api = async (path, body) => {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
};

/* ------------------------------------------------------------------ agent transcript */
const parts = new Map();        // partID -> {el, type, text}
let totalCost = 0;

function partEl(p) {
  let rec = parts.get(p.id);
  if (rec) return rec;
  const el = document.createElement("div");
  rec = { el, type: p.type, text: "" };
  parts.set(p.id, rec);
  $("#log").appendChild(el);
  return rec;
}
function scrollLog() { const l = $("#log"); l.scrollTop = l.scrollHeight; }
function sys(text) { const d = document.createElement("div"); d.className = "sys"; d.textContent = text; $("#log").appendChild(d); scrollLog(); }

function renderPart(p, role) {
  if (p.type === "text") {
    const rec = partEl(p);
    rec.el.className = "msg " + (role === "user" ? "user" : "text");
    rec.text = p.text ?? rec.text;
    rec.el.innerHTML = esc(rec.text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
  } else if (p.type === "reasoning") {
    const rec = partEl(p);
    rec.el.className = "msg reasoning"; rec.text = p.text ?? rec.text;
    rec.el.textContent = rec.text ? "thinking… " + rec.text.slice(-400) : "thinking…";
  } else if (p.type === "tool") {
    const rec = partEl(p);
    const st = p.state || {};
    rec.el.className = "tool " + (st.status || "pending");
    const args = st.input && Object.keys(st.input).length ? JSON.stringify(st.input) : "";
    let out = "";
    if (st.status === "completed") out = typeof st.output === "string" ? st.output : JSON.stringify(st.output ?? "");
    if (st.status === "error") out = st.error || "error";
    rec.el.innerHTML = `⚙ <b>${esc(p.tool)}</b> <span class="args">${esc(args.slice(0, 160))}</span>` +
      (out ? `<div class="out">${esc(out.slice(0, 300))}</div>` : "");
  } else if (p.type === "step-finish" && p.cost) {
    totalCost += p.cost; $("#cost").textContent = `$${totalCost.toFixed(4)} · ${p.tokens?.total ?? "?"} tok last step`;
  }
  scrollLog();
}

const roles = new Map();        // messageID -> role
function onOpenCode(ev) {
  const pr = ev.properties || {};
  switch (ev.type) {
    case "message.updated": roles.set(pr.info.id, pr.info.role);
      if (pr.info.error) sys("agent error: " + (pr.info.error.data?.message || pr.info.error.name));
      break;
    case "message.part.updated": renderPart(pr.part, roles.get(pr.part.messageID)); break;
    case "message.part.delta": {
      const rec = parts.get(pr.partID);
      if (rec && pr.field === "text") { rec.text += pr.delta; renderPart({ id: pr.partID, type: rec.type, text: rec.text }); }
      break;
    }
    case "session.status": setRun(pr.status?.type === "busy" ? "busy" : "idle"); break;
    case "session.idle": setRun("idle"); break;
    case "session.error": sys("session error: " + JSON.stringify(pr.error || pr).slice(0, 200)); setRun("idle"); break;
  }
}
function setRun(s) { const t = $("#run-tag"); t.textContent = s === "busy" ? "working" : "idle"; t.className = "tag" + (s === "busy" ? " busy" : ""); }

$("#ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("#q").value.trim(); if (!text) return;
  setRun("busy");
  try { await api("/api/prompt", { text }); } catch (err) { sys("could not send: " + err.message); setRun("idle"); }
});
$("#q").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#ask").requestSubmit(); } });
$("#stop").onclick = () => api("/api/abort", {}).catch((e) => sys(e.message));
$("#new-btn").onclick = () => api("/api/new", {}).catch((e) => sys(e.message));

/* ------------------------------------------------------------------ models and keys */
async function loadModels() {
  try {
    const { models, current } = await api("/api/models");
    const sel = $("#model"); sel.innerHTML = "";
    for (const m of models) {
      const o = document.createElement("option");
      o.value = JSON.stringify({ providerID: m.providerID, modelID: m.modelID });
      o.textContent = (m.providerID === "spark-qwen" ? "Spark · " : "Nebius · ") + m.name;
      if (m.providerID === current.providerID && m.modelID === current.modelID) o.selected = true;
      sel.appendChild(o);
    }
  } catch (e) { /* agent not up yet; retried on reconnect */ }
}
$("#model").onchange = (e) => api("/api/model", JSON.parse(e.target.value));

async function openKeys() {
  const { profiles, active } = await api("/api/keys");
  const box = $("#key-profiles"); box.innerHTML = "";
  for (const name of profiles) {
    const b = document.createElement("button"); b.type = "button"; b.textContent = name;
    if (name === active) b.className = "active";
    b.onclick = () => useKey({ name });
    box.appendChild(b);
  }
  if (!profiles.length) box.innerHTML = '<span class="muted">no saved keys yet</span>';
  $("#key-msg").textContent = ""; $("#key-dlg").showModal();
}
async function useKey(body) {
  $("#key-msg").textContent = "switching…";
  try {
    const r = await api("/api/keys", body);
    $("#key-name").textContent = r.active; $("#key-msg").textContent = `now using ${r.active}'s credits`;
    $("#key-new-key").value = "";
    setTimeout(() => $("#key-dlg").close(), 600);
  } catch (e) { $("#key-msg").textContent = e.message; }
}
$("#key-btn").onclick = openKeys;
$("#key-add").onclick = () => useKey({ name: $("#key-new-name").value, key: $("#key-new-key").value, save: $("#key-save").checked });

/* ------------------------------------------------------------------ knowledge graph */
const TYPE_COLOR = { Compound: "--compound", Target: "--target", TargetClass: "--class", Protocol: "--protocol",
  Format: "--format", Endpoint: "--endpoint", Structure: "--structure" };
let cy, heldOut = [], replaying = false;
async function initKG() {
  const g = await (await fetch("/static/data/kg_seed.json")).json();
  heldOut = (await (await fetch("/static/data/kg_heldout.json")).json()).edges;
  $("#kg-seed").classList.toggle("hidden", !g.seed);
  const els = [
    ...g.nodes.map((n) => ({ data: { id: n.id, label: n.name, type: n.type, color: css(TYPE_COLOR[n.type] || "--muted") } })),
    ...g.edges.map((e, i) => ({ data: { id: "e" + i, source: e.src, target: e.dst, label: e.rel.toLowerCase().replace(/_/g, " ") } })),
  ];
  cy = cytoscape({
    container: $("#cy"), elements: els, minZoom: 0.3, maxZoom: 1.6,
    style: [
      { selector: "node", style: { "background-color": "data(color)", label: "data(label)", color: "#e6edf3", "font-size": 11,
        "text-valign": "bottom", "text-margin-y": 4, width: 22, height: 22, "text-outline-color": "#0d1117", "text-outline-width": 2 } },
      { selector: "edge", style: { width: 1.4, "line-color": "#3a4558", "target-arrow-color": "#3a4558", "target-arrow-shape": "triangle",
        "curve-style": "bezier", label: "data(label)", "font-size": 8, color: "#6e7b8d", "text-rotation": "autorotate" } },
      { selector: ".found", style: { "border-width": 3, "border-color": "#ffffff" } },
      { selector: ".visited", style: { "border-width": 3, "border-color": css("--accent") } },
      { selector: ".focus", style: { width: 34, height: 34, "border-width": 4, "border-color": "#ffffff" } },
      { selector: "edge.lit", style: { "line-color": css("--accent"), "target-arrow-color": css("--accent"), width: 2.6, color: "#a5d6ff" } },
      { selector: ".dim", style: { opacity: 0.25 } },
      { selector: "node.note", style: { shape: "round-rectangle", "background-color": "#2b2410", "border-width": 1.5, "border-color": css("--note"),
        label: "data(label)", color: css("--note"), "text-valign": "center", "text-margin-y": 0, "text-wrap": "wrap", "text-max-width": 150,
        width: "label", height: "label", padding: 6, "font-size": 10 } },
      { selector: "node.note.gap", style: { "border-color": css("--bad"), color: "#ffb3ad", "background-color": "#2d1414" } },
      { selector: "node.note.proposal", style: { "border-color": css("--good"), color: "#aff5b4", "background-color": "#12261a" } },
      { selector: "edge.notelink", style: { "line-style": "dotted", "line-color": css("--note"), "target-arrow-shape": "none", width: 1.2, label: "" } },
      { selector: "edge.heldout", style: { "line-style": "dashed", "line-color": css("--bad"), "target-arrow-color": css("--bad"), width: 3,
        label: "held out: the answer", color: "#ffb3ad", "font-size": 10 } },
    ],
    layout: { name: "preset" },
  });
  startPhysics(true);
  cy.on("tap", "node", (e) => { if (!e.target.hasClass("note")) askNote([e.target.id()], e.target.data("label")); });
  const legend = Object.entries(TYPE_COLOR).map(([t, v]) => `<span><i style="background:${css(v)}"></i>${t}</span>`).join("");
  $("#kg-legend").innerHTML = legend + `<span><i style="background:${css("--note")}"></i>note (click a node to add)</span>`;
}
// Continuous spring physics (WebCola): edges are springs, nodes (with their labels) never overlap, the
// simulation keeps running, so new notes settle in live and dragging a node pulls its neighbours along.
let physics = null;
const SPRING = { notelink: 70, heldout: 160 };
function startPhysics(first = false) {
  if (physics) physics.stop();
  physics = cy.layout({
    name: "cola", infinite: true, fit: false, animate: true, randomize: first,
    nodeDimensionsIncludeLabels: true, avoidOverlap: true, handleDisconnected: true,
    nodeSpacing: (n) => (n.hasClass("note") ? 10 : 22),
    edgeLength: (e) => SPRING[e.classes().find((c) => SPRING[c])] || 130,
    convergenceThreshold: 0.0005,
  });
  physics.run();
  if (first) setTimeout(() => cy.animate({ fit: { eles: cy.elements(), padding: 30 }, duration: 600 }), 1800);
}
let noteN = 0;
function addNote(ids, note, kind = "note") {
  const anchors = ids.map((id) => id.includes("->") ? null : cy.getElementById(id)).filter((n) => n && n.nonempty());
  if (!anchors.length) return;
  const nid = "note" + noteN++;
  const p = anchors[0].position(), k = noteN % 4;
  cy.add({ group: "nodes", data: { id: nid, label: note }, classes: "note " + kind,
    position: { x: p.x + [90, -90, 90, -90][k], y: p.y + [-70, -70, 70, 70][k] } });
  for (const a of anchors) cy.add({ group: "edges", data: { id: nid + a.id(), source: nid, target: a.id() }, classes: "notelink" });
  startPhysics();
}
function highlight(ids, style, focus) {
  // only the agent's current step glows; earlier steps stay as a "visited" outline trail
  cy.elements().removeClass("dim lit focus"); cy.nodes(".found").removeClass("found").addClass("visited");
  const set = cy.collection(ids.map((id) => cy.getElementById(id)).filter((n) => n.nonempty()));
  set.addClass(style || "visited");
  if (focus) {
    const f = cy.getElementById(focus); f.addClass("focus");
    f.connectedEdges().filter((e) => set.contains(e.source()) && set.contains(e.target())).addClass("lit");
  }
  if (set.nonempty() && !replaying) cy.animate({ fit: { eles: set.closedNeighborhood(), padding: 40 }, duration: 500 });
}
function revealHeldOut() {
  for (const [i, e] of heldOut.entries()) {
    if (cy.getElementById("held" + i).nonempty()) continue;
    cy.add({ group: "edges", data: { id: "held" + i, source: e.src, target: e.dst }, classes: "heldout" });
  }
  startPhysics();
  cy.animate({ fit: { eles: cy.elements(), padding: 30 }, duration: 500 });
}
function kgEvent(ev) {
  if (!cy) return;
  if (ev.op === "highlight") highlight(ev.ids || [], ev.style, ev.focus);
  else if (ev.op === "annotate") addNote(ev.ids || [], ev.note, ev.kind);
  else if (ev.op === "reveal") revealHeldOut();
}
function askNote(ids, label) {
  $("#note-target").textContent = label; $("#note-text").value = "";
  const d = $("#note-dlg"); d.showModal();
  d.onclose = () => { if (d.returnValue === "ok" && $("#note-text").value.trim()) addNote(ids, $("#note-text").value.trim(), "note"); };
}
$("#kg-fit").onclick = () => cy.animate({ fit: { eles: cy.elements(), padding: 30 }, duration: 400 });
$("#kg-reveal").onclick = revealHeldOut;

/* ------------------------------------------------------------------ structure */
let viewer;
function showStructure(ev) {
  const pdb = (ev.pdb || "1T46").toUpperCase();
  $("#pdb-tag").textContent = "PDB " + pdb;
  $("#mol-caption").textContent = ev.caption || "";
  if (!viewer) viewer = $3Dmol.createViewer($("#mol"), { backgroundColor: css("--panel") });
  viewer.clear();
  const style = () => {
    viewer.setStyle({}, { cartoon: { color: "spectrum", opacity: 0.9 } });
    viewer.setStyle({ resn: ["HOH"] }, {});
    if (ev.ligand) {
      viewer.setStyle({ resn: ev.ligand }, { stick: { colorscheme: "orangeCarbon", radius: 0.25 } });
      viewer.addSurface($3Dmol.SurfaceType.VDW, { opacity: 0.25, color: "white" }, { within: { distance: 5, sel: { resn: ev.ligand } } });
    }
    for (const r of ev.residues || []) viewer.addStyle({ resi: r }, { stick: { color: "#f0c674" } });
    viewer.zoomTo(ev.ligand ? { resn: ev.ligand } : {}); viewer.zoom(ev.ligand ? 0.6 : 1); viewer.render();
    viewer.spin("y", 0.4);
  };
  const remote = () => $3Dmol.download("pdb:" + pdb, viewer, {}, style);   // needs network
  if (ev.local === false) return remote();
  fetch(`/static/data/${pdb}.pdb`).then((r) => r.ok ? r.text() : Promise.reject())
    .then((data) => { viewer.addModel(data, "pdb"); style(); }).catch(remote);
}

/* ------------------------------------------------------------------ 96-well plate */
const ROWS = "ABCDEFGH";
function plateSVG(cellFn, colLabel) {
  const W = 12, H = 8, s = 30, ox = 26, oy = 30;
  let out = `<svg viewBox="0 0 ${ox + W * s + 8} ${oy + H * s + 6}" xmlns="http://www.w3.org/2000/svg">`;
  out += `<rect x="${ox - 8}" y="${oy - 8}" width="${W * s + 12}" height="${H * s + 12}" rx="10" fill="#10151d" stroke="#2a3242"/>`;
  for (let c = 1; c <= W; c++) out += `<text x="${ox + (c - 0.5) * s}" y="${oy - 13}" fill="#8b96a5" font-size="9" text-anchor="middle">${esc(colLabel(c))}</text>`;
  for (let r = 0; r < H; r++) {
    out += `<text x="${ox - 15}" y="${oy + (r + 0.5) * s + 3}" fill="#8b96a5" font-size="10" text-anchor="middle">${ROWS[r]}</text>`;
    for (let c = 1; c <= W; c++) {
      const { fill, level, stroke } = cellFn(ROWS[r], c);
      const cx = ox + (c - 0.5) * s, cy = oy + (r + 0.5) * s, rad = s * 0.4;
      out += `<circle cx="${cx}" cy="${cy}" r="${rad}" fill="#0d1117" stroke="${stroke || "#3a4558"}" stroke-width="1.3"/>`;
      if (level > 0) {
        const h = 2 * rad * Math.min(1, level), y0 = cy + rad - h;
        out += `<clipPath id="w${r}${c}"><circle cx="${cx}" cy="${cy}" r="${rad - 1}"/></clipPath>` +
          `<rect x="${cx - rad}" y="${y0}" width="${2 * rad}" height="${h}" fill="${fill}" clip-path="url(#w${r}${c})"/>`;
      }
    }
  }
  return out + "</svg>";
}
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
function mix(fracs) {             // fracs: {broth, drug, cells} -> blended colour
  let rgb = [0, 0, 0], tot = 0;
  for (const [k, f] of Object.entries(fracs)) { if (!f) continue; const c = hex(css("--" + k) || "#888888"); rgb = rgb.map((v, i) => v + c[i] * f); tot += f; }
  if (!tot) return "#000";
  return `rgb(${rgb.map((v) => Math.round(v / tot)).join(",")})`;
}
function plateLive(snap, active) {
  $("#plate-mode").textContent = "live from robot feed"; $("#plate-mode").className = "tag live";
  $("#plate-svg").innerHTML = plateSVG((row, c) => {
    const w = snap[c] || { v: 0 };
    return { level: w.v / 200, fill: mix({ broth: w.broth, drug: w.drug, cells: w.cells }), stroke: c === active ? "#ffffff" : null };
  }, (c) => c);
}
let plan = null;
function platePlan(ev) {
  plan = ev;
  $("#plate-mode").textContent = ev.title || "planned"; $("#plate-mode").className = "tag";
  const max = Math.max(...ev.concs_uM), min = Math.min(...ev.concs_uM);
  $("#plate-svg").innerHTML = plateSVG((row, c) => {
    if (!ev.rows.includes(row)) return { level: 0 };
    if (ev.controls?.[c]) return { level: 0.9, fill: "#2f6f4f" };
    const v = ev.concs_uM[c - 1]; if (v === undefined) return { level: 0 };
    const t = max === min ? 1 : (Math.log(v) - Math.log(min)) / (Math.log(max) - Math.log(min));
    return { level: 0.9, fill: `rgba(207,13,13,${0.18 + 0.82 * t})` };
  }, (c) => ev.controls?.[c] ? (c === 11 ? "ctl+" : "ctl–") : (ev.concs_uM[c - 1] !== undefined ? fmtC(ev.concs_uM[c - 1]) : ""));
}
const fmtC = (u) => u >= 1 ? +u.toPrecision(2) + "µ" : +(u * 1000).toPrecision(2) + "n";
function plateLegend() {
  $("#plate-legend").innerHTML = ["broth", "drug", "cells"].map((k) => `<span><i style="background:${css("--" + k)}"></i>${k}</span>`).join(" ");
}

/* ------------------------------------------------------------------ robot feed, synced to the video */
let feed = null, sync = null, lastIdx = -1, simT = null, simStart = 0;
const vid = $("#vid");
async function initFeed() {
  feed = await (await fetch("/static/data/feed_mic.json")).json();
  try { sync = await (await fetch("/static/data/sync.json")).json(); } catch { sync = null; }
  $("#robot-src").textContent = `${feed.protocol} · ${feed.simulator}` + (feed.api_level_original !== feed.api_level_simulated ? ` (simulated at API ${feed.api_level_simulated})` : "");
  const ol = $("#feed");
  ol.innerHTML = feed.steps.map((s) => `<li class="${s.depth ? "sub" : ""}${s.kind === "pause" ? " pause" : ""}">${esc(s.text)}</li>`).join("");
  renderRobot(-1);
}
// video time -> estimated robot time: piecewise-linear cue points [{video, feed}], else scale to the video length
function feedTime(vt) {
  const cues = sync?.cues;
  if (cues?.length >= 2) {
    for (let i = 1; i < cues.length; i++) if (vt <= cues[i].video || i === cues.length - 1) {
      const a = cues[i - 1], b = cues[i], f = (vt - a.video) / ((b.video - a.video) || 1);
      return a.feed + f * (b.feed - a.feed);
    }
  }
  const dur = isFinite(vid.duration) && vid.duration > 0 ? vid.duration : feed.duration_est_s;
  return (vt / dur) * feed.duration_est_s;
}
function idxAt(ft) { let lo = 0, hi = feed.steps.length - 1, ans = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (feed.steps[m].t <= ft) { ans = m; lo = m + 1; } else hi = m - 1; } return ans; }
function renderRobot(i) {
  if (!feed || i === lastIdx) return;
  const lis = $("#feed").children;
  if (lastIdx >= 0 && lis[lastIdx]) lis[lastIdx].classList.remove("now");
  for (let k = Math.max(0, Math.min(i, lastIdx)); k < lis.length; k++) lis[k].classList.toggle("done", k < i);
  lastIdx = i;
  const s = feed.steps[i];
  if (s) { lis[i].classList.add("now"); lis[i].scrollIntoView({ block: "center" }); }
  const tips = feed.steps.slice(0, i + 1).filter((x) => x.kind === "pick_up").length;
  const done = i >= feed.steps.length - 1;
  const state = i < 0 ? "idle" : done ? "complete" : s.kind === "pause" ? "paused (human step)" : "running";
  $("#robot-state").textContent = state; $("#robot-state").className = "tag" + (state === "running" ? " live" : state.startsWith("paused") ? " warn" : "");
  $("#robot-summary").innerHTML = `<div>step<b>${Math.max(0, i + 1)} / ${feed.steps.length}</b></div><div>tips used<b>${tips}</b></div>` +
    `<div>column<b>${s?.col ?? "—"}</b></div><div>action<b>${esc(s ? s.kind.replace("_", " ") : "—")}</b></div>`;
  plateLive(i >= 0 ? feed.plates[i] : {}, s?.col);
}
function tick() {
  if (feed) {
    if (simT !== null) renderRobot(idxAt((performance.now() - simStart) / 1000 * 8));      // 8x without a video
    else if (!vid.paused || vid.seeking) renderRobot(idxAt(feedTime(vid.currentTime)));
  }
  requestAnimationFrame(tick);
}
vid.addEventListener("seeked", () => feed && renderRobot(idxAt(feedTime(vid.currentTime))));
vid.addEventListener("error", () => { vid.classList.add("hidden"); $("#vid-missing").classList.remove("hidden"); });
$("#sim-play").onclick = () => { if (simT === null) { simT = 1; simStart = performance.now(); $("#sim-play").textContent = "stop"; } else { simT = null; $("#sim-play").textContent = "play feed without video"; } };
function robotEvent(ev) {
  if (ev.op === "play") { if (vid.classList.contains("hidden")) { if (simT === null) $("#sim-play").click(); } else vid.play(); }
  else if (ev.op === "pause") { vid.pause(); simT = null; }
  else if (ev.op === "reset") { vid.pause(); vid.currentTime = 0; simT = null; lastIdx = -2; renderRobot(-1); }
}

/* ------------------------------------------------------------------ event stream */
function onPanel(ev) {
  if (ev.panel === "kg") kgEvent(ev);
  else if (ev.panel === "structure") showStructure(ev);
  else if (ev.panel === "plate" && ev.op === "plan") platePlan(ev);
  else if (ev.panel === "robot") robotEvent(ev);
}
function connect() {
  const es = new EventSource("/api/stream");
  es.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.type === "hello") {
      setAgent(ev.opencode); if (ev.key_profile) $("#key-name").textContent = ev.key_profile;
      replaying = true;
      for (const list of Object.values(ev.panels)) for (const p of list) onPanel(p);
      replaying = false; if (cy) setTimeout(() => cy.animate({ fit: { eles: cy.elements(), padding: 30 }, duration: 600 }), 2000);
      if (ev.session) loadTranscript();
    } else if (ev.type === "status") { setAgent(ev.opencode); if (ev.opencode) loadModels(); }
    else if (ev.type === "oc") onOpenCode(ev.event);
    else if (ev.type === "panel") onPanel(ev);
    else if (ev.type === "key") $("#key-name").textContent = ev.active;
    else if (ev.type === "reset") location.reload();
  };
  es.onerror = () => setAgent(false);
}
async function loadTranscript() {
  try {
    for (const m of await api("/api/transcript")) {
      roles.set(m.info.id, m.info.role);
      for (const p of m.parts) renderPart(p, m.info.role);
    }
  } catch (e) { sys("could not load transcript: " + e.message); }
}
function setAgent(ok) { $("#agent-dot").className = "dot" + (ok ? " on" : ""); $("#agent-state").textContent = ok ? "agent ready" : "agent offline"; }

(async function main() {
  plateLegend();
  await Promise.all([initKG(), initFeed()]);
  showStructure({ pdb: "1T46", ligand: "STI", caption: "KIT kinase domain with imatinib (STI-571), PDB 1T46" });
  loadModels(); connect(); tick();
})();
