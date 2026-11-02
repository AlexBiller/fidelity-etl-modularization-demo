/* ETL Modularization Workbench - unofficial demo built with Devin, synthetic data only. */
(function () {
  "use strict";
  const SEED = window.SEED;
  const MODS = SEED.modules;
  const BY_ID = Object.fromEntries(MODS.map((m) => [m.id, m]));
  const STORE_KEY = "fid-etl-demo-v1";
  const BAND_COLOR = { Low: "var(--low)", Medium: "var(--med)", High: "var(--high)", Critical: "var(--crit)" };
  const STATUS_LABEL = { queued: "Queued", blocked: "Blocked", running: "Devin coding", testing: "Testing", review: "In review", merged: "Merged" };
  const STEP = 0.5;

  const $app = document.getElementById("app");
  const $drawer = document.getElementById("drawer");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const fmt = (n) => Number(n).toLocaleString("en-US");
  const kloc = (n) => (n >= 1e6 ? (n / 1e6).toFixed(2) + "M" : Math.round(n / 1000) + "k");

  let state = load();
  let ui = { sort: { key: "risk_score", dir: -1 }, q: "", domain: "", band: "", taskMod: 0 };
  let timer = null;

  function load() {
    try { const s = JSON.parse(localStorage.getItem(STORE_KEY)); if (s && s.v === 1) return s; } catch (e) { /* ignore */ }
    return { v: 1, params: { sessions: 6, perTask: 2, isolateCritical: true }, plan: null, sim: null };
  }
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { /* ignore */ } }

  // ------------------------------------------------------------------ plan
  function depth(id, memo = {}) {
    if (id in memo) return memo[id];
    const ups = BY_ID[id].upstream;
    return (memo[id] = ups.length ? 1 + Math.max(...ups.map((u) => depth(u, memo))) : 0);
  }

  function generatePlan(params) {
    const memo = {};
    const phases = [];
    MODS.forEach((m) => { const d = depth(m.id, memo); (phases[d] = phases[d] || []).push(m); });
    const tasks = {};
    const order = [];
    phases.forEach((mods, p) => {
      mods.sort((a, b) => a.domain.localeCompare(b.domain) || b.risk_score - a.risk_score);
      const groups = [];
      const byDomain = {};
      mods.forEach((m) => {
        if (params.isolateCritical && m.risk_band === "Critical") { groups.push([m]); return; }
        (byDomain[m.domain] = byDomain[m.domain] || []).push(m);
      });
      Object.values(byDomain).forEach((list) => { for (let i = 0; i < list.length; i += params.perTask) groups.push(list.slice(i, i + params.perTask)); });
      groups.sort((a, b) => Math.max(...b.map((m) => m.risk_score)) - Math.max(...a.map((m) => m.risk_score)));
      groups.forEach((g, i) => {
        const id = `T-${p + 1}.${String(i + 1).padStart(2, "0")}`;
        const ids = g.map((m) => m.id);
        const hours = g.reduce((s, m) => s + m.devin_hours, 0) * (g.length > 1 ? 0.85 : 1);
        tasks[id] = {
          id, phase: p, modules: ids,
          hours: Math.round(hours * 2) / 2,
          review: Math.max(...g.map((m) => m.review_hours)),
          risk: Math.max(...g.map((m) => m.risk_score)),
          band: g.slice().sort((a, b) => b.risk_score - a.risk_score)[0].risk_band,
          loc: g.reduce((s, m) => s + m.loc, 0),
          pr: 0,
        };
        order.push(id);
      });
    });
    const modTask = {};
    order.forEach((id) => tasks[id].modules.forEach((m) => (modTask[m] = id)));
    order.forEach((id, i) => {
      const t = tasks[id];
      t.pr = 4100 + i * 3 + (i % 2);
      t.deps = [...new Set(t.modules.flatMap((m) => BY_ID[m].upstream).map((u) => modTask[u]).filter((x) => x !== id))].sort();
    });
    return { params: { ...params }, phases: phases.map((_, p) => order.filter((id) => tasks[id].phase === p)), tasks, order, modTask };
  }

  // ------------------------------------------------------------------ simulation
  function newSim(plan) {
    const ts = {};
    plan.order.forEach((id) => (ts[id] = { status: "queued", elapsed: 0, startedAt: null, mergedAt: null }));
    return { t: 0, tasks: ts, history: [{ t: 0, merged: 0, loc: 0 }], log: [{ t: 0, msg: `Plan approved: ${plan.order.length} Devin tasks across ${plan.phases.length} phases, up to ${plan.params.sessions} parallel sessions.` }] };
  }
  const depsMerged = (id) => state.plan.tasks[id].deps.every((d) => state.sim.tasks[d].status === "merged");
  function displayStatus(id) {
    const s = state.sim ? state.sim.tasks[id].status : "queued";
    return s === "queued" && !depsMerged(id) ? "blocked" : s;
  }
  function logMsg(msg) { state.sim.log.unshift({ t: state.sim.t, msg }); if (state.sim.log.length > 120) state.sim.log.length = 120; }

  function advanceTask(id, dt) {
    const t = state.plan.tasks[id], s = state.sim.tasks[id];
    s.elapsed += dt;
    const code = t.hours * 0.65, test = t.hours, total = t.hours + t.review;
    if (s.status === "running" && s.elapsed >= code) { s.status = "testing"; logMsg(`${id}: running ${t.modules.reduce((n, m) => n + BY_ID[m].tests.length, 0)} tests incl. parity on golden snapshots ${SEED.meta.golden_snapshots.join(", ")}`); }
    if (s.status === "testing" && s.elapsed >= test) { s.status = "review"; logMsg(`${id}: all tests passing, opened PR #${t.pr} for review by ${BY_ID[t.modules[0]].owner}`); }
    if (s.status === "review" && s.elapsed >= total) merge(id);
  }
  function merge(id) {
    const t = state.plan.tasks[id], s = state.sim.tasks[id];
    s.status = "merged"; s.mergedAt = state.sim.t;
    logMsg(`${id}: PR #${t.pr} merged, ${t.modules.map((m) => BY_ID[m].submodule).join(", ")} now a standalone sub-module`);
  }
  function startEligible() {
    const cap = state.plan.params.sessions;
    let active = state.plan.order.filter((id) => ["running", "testing"].includes(state.sim.tasks[id].status)).length;
    const ready = state.plan.order.filter((id) => state.sim.tasks[id].status === "queued" && depsMerged(id))
      .sort((a, b) => state.plan.tasks[a].phase - state.plan.tasks[b].phase || state.plan.tasks[b].risk - state.plan.tasks[a].risk);
    for (const id of ready) {
      if (active >= cap) break;
      const s = state.sim.tasks[id];
      s.status = "running"; s.startedAt = state.sim.t; active++;
      logMsg(`${id}: Devin session started on ${state.plan.tasks[id].modules.join(", ")}`);
    }
  }
  function step(hours) {
    if (!state.sim) return;
    for (let h = 0; h < hours; h += STEP) {
      if (allMerged()) break;
      startEligible();
      state.sim.t += STEP;
      state.plan.order.forEach((id) => { if (["running", "testing", "review"].includes(state.sim.tasks[id].status)) advanceTask(id, STEP); });
      startEligible();
      recordHistory();
    }
    save();
  }
  function recordHistory() {
    const merged = mergedModules();
    const last = state.sim.history[state.sim.history.length - 1];
    if (last.merged !== merged.length || state.sim.t - last.t >= 4) state.sim.history.push({ t: state.sim.t, merged: merged.length, loc: merged.reduce((s, m) => s + m.loc, 0) });
  }
  const mergedModules = () => (state.sim ? state.plan.order.filter((id) => state.sim.tasks[id].status === "merged").flatMap((id) => state.plan.tasks[id].modules.map((m) => BY_ID[m])) : []);
  const allMerged = () => state.plan.order.every((id) => state.sim.tasks[id].status === "merged");
  function fastForward(id) {
    const t = state.plan.tasks[id], s = state.sim.tasks[id];
    if (!depsMerged(id) || ["review", "merged"].includes(s.status)) return;
    if (s.status === "queued") { s.startedAt = state.sim.t; logMsg(`${id}: Devin session started on ${t.modules.join(", ")}`); s.status = "running"; }
    s.elapsed = Math.max(s.elapsed, t.hours * 0.65); s.status = "testing"; advanceTask(id, t.hours - s.elapsed);
    save();
  }
  function approve(id) { if (state.sim.tasks[id].status === "review") { merge(id); recordHistory(); save(); } }
  function setRunning(on) {
    clearInterval(timer); timer = null;
    if (on) timer = setInterval(() => { step(1); if (allMerged()) setRunning(false); render(); }, 160);
  }
  const ensurePlan = () => { if (!state.plan) { state.plan = generatePlan(state.params); state.sim = newSim(state.plan); save(); } };
  const simTime = (t) => `T+${Math.floor(t / 24)}d ${String(Math.floor(t % 24)).padStart(2, "0")}h`;

  // ------------------------------------------------------------------ helpers
  const pill = (band) => `<span class="pill b-${band}">${band}</span>`;
  const status = (s) => `<span class="status s-${s}">${STATUS_LABEL[s]}</span>`;
  const riskCell = (m) => `<span class="riskbar"><i style="width:${m.risk_score}%;background:${BAND_COLOR[m.risk_band]}"></i></span><b>${m.risk_score}</b> ${pill(m.risk_band)}`;
  const kpi = (label, value, sub = "") => `<div class="card kpi"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${sub}</div></div>`;
  const modStatus = (mid) => (state.plan && state.sim ? displayStatus(state.plan.modTask[mid]) : null);

  // ------------------------------------------------------------------ views
  function viewInventory() {
    const totalLoc = SEED.meta.total_loc;
    const avgCov = Math.round(MODS.reduce((s, m) => s + m.test_coverage * m.loc, 0) / totalLoc);
    const hi = MODS.filter((m) => m.risk_band === "Critical" || m.risk_band === "High").length;
    const domains = [...new Set(MODS.map((m) => m.domain))].sort();
    let rows = MODS.filter((m) => (!ui.q || m.id.includes(ui.q.toLowerCase()) || m.kind.toLowerCase().includes(ui.q.toLowerCase())) && (!ui.domain || m.domain === ui.domain) && (!ui.band || m.risk_band === ui.band));
    const { key, dir } = ui.sort;
    rows = rows.slice().sort((a, b) => (typeof a[key] === "string" ? a[key].localeCompare(b[key]) : a[key] - b[key]) * dir);
    const th = (k, label, cls = "") => `<th class="${cls}" data-sort="${k}">${label}${key === k ? (dir > 0 ? " ▲" : " ▼") : ""}</th>`;
    return `
      <h2>Legacy module inventory</h2>
      <p class="lede">Devin indexed the fictional <code>${SEED.meta.monolith}</code> monolith (${SEED.meta.monolith_age_years} years old, ${kloc(totalLoc)} lines) and scored every module for migration risk based on size, test coverage, fan-in, complexity, reach-ins to private state and sensitive data. Click a module to see what drives its score.</p>
      <div class="proof"><b>Industry example:</b> ${esc(SEED.meta.proof_point.text)} <a href="${SEED.meta.proof_point.source}" target="_blank" rel="noopener">Public customer story</a></div>
      <div class="grid kpis">
        ${kpi("Modules", MODS.length, `${domains.length} business domains`)}
        ${kpi("Legacy lines", kloc(totalLoc), `${fmt(MODS.reduce((s, m) => s + m.files, 0))} files`)}
        ${kpi("Weighted test coverage", avgCov + "%", "parity tests added per task")}
        ${kpi("High / critical risk", hi, `${MODS.filter((m) => m.risk_band === "Critical").length} critical`)}
        ${kpi("Cross-module call sites", fmt(MODS.reduce((s, m) => s + m.call_sites, 0)), "to rewire onto contracts")}
      </div>
      <div class="toolbar">
        <input type="search" id="q" placeholder="Search modules…" value="${esc(ui.q)}">
        <select id="fdomain"><option value="">All domains</option>${domains.map((d) => `<option ${d === ui.domain ? "selected" : ""}>${d}</option>`).join("")}</select>
        <select id="fband"><option value="">All risk bands</option>${["Critical", "High", "Medium", "Low"].map((b) => `<option ${b === ui.band ? "selected" : ""}>${b}</option>`).join("")}</select>
        <span class="muted">${rows.length} of ${MODS.length} modules</span>
        <span style="flex:1"></span>
        <a class="btn" href="#/plan">Next: generate migration plan →</a>
      </div>
      <div class="tablewrap"><table>
        <thead><tr>${th("id", "Module")}${th("domain", "Domain")}${th("kind", "Kind")}${th("loc", "Lines", "num")}${th("test_coverage", "Coverage", "num")}${th("fan_in", "Fan-in", "num")}${th("call_sites", "Call sites", "num")}${th("risk_score", "Migration risk")}<th>Status</th></tr></thead>
        <tbody>${rows.map((m) => {
          const st = modStatus(m.id);
          return `<tr data-mod="${m.id}"><td class="mod">${m.id}</td><td>${m.domain}</td><td class="muted">${m.kind}</td><td class="num">${fmt(m.loc)}</td><td class="num">${m.test_coverage}%</td><td class="num">${m.fan_in}</td><td class="num">${m.call_sites}</td><td>${riskCell(m)}</td><td>${st ? status(st) : '<span class="muted">Not planned</span>'}</td></tr>`;
        }).join("")}</tbody>
      </table></div>`;
  }

  function openDrawer(mid) {
    const m = BY_ID[mid];
    const st = modStatus(mid);
    const tid = state.plan && state.plan.modTask[mid];
    $drawer.innerHTML = `
      <button class="btn ghost small close" id="dclose">Close ✕</button>
      <div class="mod" style="font-size:16px">${m.id}</div>
      <div class="muted">${m.domain} · ${m.kind} · owned by ${m.owner}</div>
      <div style="margin:14px 0;display:flex;align-items:center;gap:12px"><div style="font-size:40px;font-weight:800;color:${BAND_COLOR[m.risk_band]}">${m.risk_score}</div><div>${pill(m.risk_band)}<div class="muted" style="font-size:12px">migration risk score (0-100)</div></div></div>
      <h3>What drives the score</h3>
      <div class="drivers">${m.risk_drivers.map((d) => `<div class="row"><span>${d.factor}</span><div><div class="bar"><i style="width:${Math.round(d.value * 100)}%"></i></div><div class="muted" style="font-size:11.5px">${esc(d.detail)}</div></div><b style="text-align:right">+${d.contribution}</b></div>`).join("")}</div>
      <h3 style="margin-top:16px">Facts</h3>
      <table style="font-size:13px"><tbody>
        <tr><td class="muted">Lines / files</td><td>${fmt(m.loc)} / ${m.files}</td></tr>
        <tr><td class="muted">Test coverage</td><td>${m.test_coverage}%</td></tr>
        <tr><td class="muted">Avg cyclomatic complexity</td><td>${m.avg_complexity}</td></tr>
        <tr><td class="muted">Last major rewrite</td><td>${m.years_since_rewrite} years ago</td></tr>
        <tr><td class="muted">Target sub-module</td><td><code>${m.submodule}</code></td></tr>
        <tr><td class="muted">Migration task</td><td>${tid ? `<a href="#/task/${tid}">${tid}</a> ${status(st)}` : '<span class="muted">generate a plan first</span>'}</td></tr>
      </tbody></table>
      <h3 style="margin-top:16px">Upstream (${m.upstream.length})</h3>
      <div class="chips">${m.upstream.map((u) => `<span class="chip" data-mod="${u}">${u}</span>`).join("") || '<span class="muted">none: foundation module</span>'}</div>
      <h3 style="margin-top:14px">Downstream (${m.downstream.length})</h3>
      <div class="chips">${m.downstream.map((u) => `<span class="chip" data-mod="${u}">${u}</span>`).join("") || '<span class="muted">none</span>'}</div>
      <h3 style="margin-top:16px">Legacy code excerpt</h3>
      <pre class="code">${esc(m.code_before)}</pre>`;
    $drawer.hidden = false;
  }

  function viewPlan() {
    const p = state.params;
    const plan = state.plan;
    let body = `<div class="card empty">Choose how many Devin sessions can run in parallel and how modules are grouped, then generate the plan.</div>`;
    if (plan) {
      const tasks = plan.order.map((id) => plan.tasks[id]);
      const devinH = tasks.reduce((s, t) => s + t.hours, 0);
      const manualH = MODS.reduce((s, m) => s + m.manual_hours, 0);
      const engH = MODS.reduce((s, m) => s + m.engineer_hours, 0);
      body = `
        <div class="grid kpis">
          ${kpi("Phases", plan.phases.length, "ordered by dependency depth")}
          ${kpi("Parallel Devin tasks", tasks.length, `max ${plan.params.sessions} sessions at once`)}
          ${kpi("Devin session hours", Math.round(devinH), "estimated, all tasks")}
          ${kpi("Engineer hours", `~${fmt(Math.round(engH))}h`, `with Devin, vs ~${fmt(manualH)}h manual (${(manualH / engH).toFixed(1)}x)`)}
          ${kpi("Widest phase", Math.max(...plan.phases.map((ph) => ph.length)) + " tasks", "no intra-phase dependencies")}
        </div>
        <div class="toolbar"><span class="muted">Each column is a phase. Tasks within a phase have no dependencies on each other, so Devin runs them in parallel. Click a task to review it.</span><span style="flex:1"></span><a class="btn" href="#/dashboard">Start migration → dashboard</a></div>
        <div class="phases">${plan.phases.map((ids, i) => `
          <div class="phase"><h4><span>Phase ${i + 1}</span><span class="muted">${ids.length} tasks · ${kloc(ids.reduce((s, id) => s + plan.tasks[id].loc, 0))} lines</span></h4>
          ${ids.map((id) => taskCard(plan.tasks[id])).join("")}</div>`).join("")}
        </div>`;
    }
    return `
      <h2>Phased migration plan</h2>
      <p class="lede">Modules are ordered into phases by dependency depth: foundation modules (reference and market data) are extracted first so downstream jobs can depend on their published contracts. Each phase is split into independent tasks, one Devin session and one pull request each.</p>
      <div class="card" style="margin-bottom:16px"><div class="controls">
        <label>Parallel Devin sessions: <b id="vs">${p.sessions}</b><input type="range" id="sessions" min="2" max="12" value="${p.sessions}"></label>
        <label>Max modules per task: <b id="vp">${p.perTask}</b><input type="range" id="perTask" min="1" max="4" value="${p.perTask}"></label>
        <label style="flex-direction:row;align-items:center;gap:6px;padding-bottom:6px"><input type="checkbox" id="iso" ${p.isolateCritical ? "checked" : ""}> Critical-risk modules get their own task</label>
        <button class="btn" id="gen">${plan ? "Regenerate plan" : "Generate migration plan"}</button>
        ${plan ? '<span class="muted" style="padding-bottom:8px">Regenerating resets progress on the dashboard.</span>' : ""}
      </div></div>
      ${body}`;
  }

  function taskCard(t, compact) {
    const st = displayStatus(t.id);
    return `<div class="task" data-task="${t.id}">
      <div class="tid"><span>${t.id}</span>${state.sim ? status(st) : pill(t.band)}</div>
      ${compact ? `<div class="meta">${t.modules.map((m) => m.split(".")[1]).join(", ")}</div>` : `<ul>${t.modules.map((m) => `<li>${m}</li>`).join("")}</ul>
      <div class="meta">${kloc(t.loc)} lines · ~${t.hours}h Devin · risk ${t.risk}${t.deps.length ? ` · after ${t.deps.length} task${t.deps.length > 1 ? "s" : ""}` : ""}</div>`}
    </div>`;
  }

  function diffLines(a, b) {
    const n = a.length, m = b.length;
    const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
    for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i].trim() === b[j].trim() ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    const ops = [];
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (a[i].trim() === b[j].trim()) { ops.push(["eq", i++, j++]); }
      else if (dp[i + 1][j] >= dp[i][j + 1]) ops.push(["del", i++, null]);
      else ops.push(["add", null, j++]);
    }
    while (i < n) ops.push(["del", i++, null]);
    while (j < m) ops.push(["add", null, j++]);
    const rows = [];
    for (let k = 0; k < ops.length;) {
      if (ops[k][0] === "eq") { rows.push([ops[k][1], ops[k][2], "eq"]); k++; continue; }
      const dels = [], adds = [];
      while (k < ops.length && ops[k][0] !== "eq") { (ops[k][0] === "del" ? dels : adds).push(ops[k]); k++; }
      for (let x = 0; x < Math.max(dels.length, adds.length); x++) rows.push([dels[x] ? dels[x][1] : null, adds[x] ? adds[x][2] : null, "chg"]);
    }
    return { rows, added: ops.filter((o) => o[0] === "add").length, removed: ops.filter((o) => o[0] === "del").length };
  }

  function renderDiff(m) {
    const a = m.code_before.replace(/\n$/, "").split("\n"), b = m.code_after.replace(/\n$/, "").split("\n");
    const d = diffLines(a, b);
    const cell = (lines, idx, cls) => idx === null ? `<div class="dl pad"><span class="n"></span><span class="t"></span></div>` : `<div class="dl ${cls}"><span class="n">${idx + 1}</span><span class="t">${esc(lines[idx])}</span></div>`;
    return `<div class="legend" style="margin-bottom:6px"><span><i style="background:#fde8e8"></i>removed from monolith (${d.removed})</span><span><i style="background:#e3f6e6"></i>added in sub-module (${d.added})</span></div>
      <div class="diff"><div class="hdr">Before · <code>ledger_etl/jobs/${m.id.replace(".", "/")}.py</code></div><div class="hdr r">After · <code>${m.submodule}</code></div>
      <div class="pane" style="grid-column:1/3"><div class="rows">${d.rows.map(([l, r, k]) => `${cell(a, l, k === "chg" ? "del" : "")}<div class="rcell">${cell(b, r, k === "chg" ? "add" : "")}</div>`).join("")}</div></div></div>`;
  }

  function viewTask(tid) {
    if (!state.plan) return `<h2>Task review</h2><div class="card empty">No migration plan yet.<br><br><button class="btn" id="genDefault">Generate default plan</button> <a class="btn ghost" href="#/plan">Configure plan</a></div>`;
    const plan = state.plan;
    if (!tid || !plan.tasks[tid]) tid = plan.order.find((id) => ["review", "testing", "running"].includes(state.sim.tasks[id].status)) || plan.order[0];
    const t = plan.tasks[tid], s = state.sim.tasks[tid], st = displayStatus(tid);
    if (ui.taskMod >= t.modules.length) ui.taskMod = 0;
    const m = BY_ID[t.modules[ui.taskMod]];
    const testsDone = ["review", "merged"].includes(s.status);
    const allTests = t.modules.flatMap((x) => BY_ID[x].tests);
    const logLines = state.sim.log.filter((l) => l.msg.startsWith(tid + ":")).slice().reverse();
    const pct = Math.min(100, Math.round((s.elapsed / (t.hours + t.review)) * 100));
    return `
      <div class="split">
        <div class="card tasklist"><h3>Tasks (${plan.order.length})</h3>
          ${plan.phases.map((ids, i) => `<div class="muted" style="font-size:11px;font-weight:700;margin:10px 4px 4px">PHASE ${i + 1}</div>` + ids.map((id) => `<div class="item ${id === tid ? "sel" : ""}" data-goto="${id}"><span>${id} <span class="muted">${plan.tasks[id].modules.length > 1 ? "×" + plan.tasks[id].modules.length : ""}</span></span>${status(displayStatus(id))}</div>`).join("")).join("")}
        </div>
        <div>
          <div class="card" style="margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-start">
              <div><h2 style="font-family:var(--mono)">${tid} ${status(st)}</h2>
              <div class="muted">Phase ${t.phase + 1} · ${t.modules.length} module${t.modules.length > 1 ? "s" : ""} · ${fmt(t.loc)} legacy lines · ~${t.hours}h Devin + ${t.review}h engineer review · risk ${t.risk} ${pill(t.band)}</div>
              <div class="muted" style="margin-top:4px">${t.deps.length ? `Depends on: ${t.deps.map((d) => `<a href="#/task/${d}">${d}</a> ${state.sim.tasks[d].status === "merged" ? "✓" : "…"}`).join(", ")}` : "No upstream tasks: can start immediately"}</div></div>
              <div style="display:flex;gap:8px;align-items:center">
                ${s.status === "review" ? `<button class="btn" id="approve" data-task="${tid}">Approve &amp; merge PR #${t.pr}</button>` : ""}
                ${["queued", "running", "testing"].includes(s.status) ? `<button class="btn ${st === "blocked" ? "ghost" : ""}" id="ff" data-task="${tid}" ${st === "blocked" ? "disabled title='Upstream tasks must merge first'" : ""}>Fast-forward to review</button>` : ""}
                ${s.status === "merged" ? `<span class="status s-merged">PR #${t.pr} merged at ${simTime(s.mergedAt)}</span>` : ""}
              </div>
            </div>
            <div class="progress" style="margin-top:12px"><i style="width:${pct}%;background:${s.status === "merged" ? "var(--low)" : "var(--blue)"}"></i></div>
          </div>
          ${t.modules.length > 1 ? `<div class="subtabs">${t.modules.map((x, i) => `<button class="${i === ui.taskMod ? "on" : ""}" data-tm="${i}">${x}</button>`).join("")}</div>` : ""}
          <div class="card" style="margin-bottom:14px"><h3>Before / after: <span class="mod">${m.id}</span> → <code>${m.submodule}</code></h3>${renderDiff(m)}</div>
          <div class="grid two">
            <div class="card"><h3>Tests ${testsDone ? `<span class="status s-merged">${allTests.length}/${allTests.length} passing</span>` : s.status === "testing" ? '<span class="status s-testing">running…</span>' : '<span class="status">not run yet</span>'}</h3>
              <div class="tests">${m.tests.map((x) => `<div class="t"><span>${testsDone ? '<span class="ok">✓</span>' : '<span class="pend">○</span>'} ${esc(x.name)} <span class="muted">${x.type}${x.rows_compared ? `, ${fmt(x.rows_compared)} synthetic rows, 0 diffs` : ""}</span></span><span class="muted">${testsDone ? (x.ms / 1000).toFixed(2) + "s" : ""}</span></div>`).join("")}</div>
              <h3 style="margin-top:14px">Parity test (generated)</h3><pre class="code">${esc(m.test_code)}</pre></div>
            <div class="card"><h3>What Devin changed</h3><ul style="padding-left:18px;margin-top:0">${m.changes.map((c) => `<li>${esc(c).replace(/`([^`]+)`/g, "<code>$1</code>")}</li>`).join("")}</ul>
              <h3>Pull request</h3><div class="muted" style="margin-bottom:10px">#${t.pr} · <code>devin/migrate-${t.modules[0].replace(".", "-")}</code> · reviewer: ${m.owner} · ${m.call_sites} call sites rewired via compat shim</div>
              <h3>Session log</h3><div class="log">${logLines.length ? logLines.map((l) => `<div><b>${simTime(l.t)}</b>${esc(l.msg.slice(tid.length + 2))}</div>`).join("") : '<span class="muted">Not started. Start the simulation on the dashboard or fast-forward this task.</span>'}</div></div>
          </div>
        </div>
      </div>`;
  }

  function burnup() {
    const h = state.sim.history, W = 640, H = 220, P = 34;
    const plan = state.plan;
    const est = Math.max(24, h[h.length - 1].t, plan.order.reduce((s, id) => s + plan.tasks[id].hours + plan.tasks[id].review, 0) / plan.params.sessions * 1.3);
    const x = (t) => P + (t / est) * (W - P - 10), y = (v) => H - P + 6 - (v / MODS.length) * (H - P - 10);
    const pts = h.map((p) => `${x(p.t).toFixed(1)},${y(p.merged).toFixed(1)}`).join(" ");
    const area = `${x(0)},${y(0)} ${pts} ${x(h[h.length - 1].t)},${y(0)}`;
    const ticks = [0, 8, 16, 24, 32].map((v) => `<line x1="${P}" x2="${W - 10}" y1="${y(v)}" y2="${y(v)}" stroke="#e5e9e6"/><text x="${P - 6}" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="#7a867f">${v}</text>`).join("");
    const days = []; for (let d = 0; d <= est; d += 24) days.push(`<text x="${x(d)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="#7a867f">d${d / 24}</text>`);
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Burn-up chart">${ticks}${days.join("")}
      <line x1="${P}" x2="${W - 10}" y1="${y(MODS.length)}" y2="${y(MODS.length)}" stroke="#2f7a3b" stroke-dasharray="4 4"/><text x="${W - 12}" y="${y(MODS.length) - 5}" text-anchor="end" font-size="10" fill="#2f7a3b">scope: ${MODS.length} modules</text>
      <polygon points="${area}" fill="rgba(47,122,59,.15)"/><polyline points="${pts}" fill="none" stroke="#2f7a3b" stroke-width="2.5"/>
      <circle cx="${x(h[h.length - 1].t)}" cy="${y(h[h.length - 1].merged)}" r="4" fill="#2f7a3b"/></svg>`;
  }

  function viewDashboard() {
    if (!state.plan) return `<h2>Migration dashboard</h2><div class="card empty">No migration plan yet.<br><br><button class="btn" id="genDefault">Generate default plan</button> <a class="btn ghost" href="#/plan">Configure plan</a></div>`;
    const plan = state.plan, sim = state.sim;
    const merged = mergedModules();
    const mergedLoc = merged.reduce((s, m) => s + m.loc, 0);
    const counts = { blocked: 0, queued: 0, running: 0, testing: 0, review: 0, merged: 0 };
    plan.order.forEach((id) => counts[displayStatus(id)]++);
    const manual = merged.reduce((s, m) => s + m.manual_hours, 0);
    const eng = merged.reduce((s, m) => s + m.engineer_hours, 0);
    const done = allMerged();
    const cols = [["Queued", ["blocked", "queued"]], ["Devin coding", ["running"]], ["Testing", ["testing"]], ["In review", ["review"]], ["Merged", ["merged"]]];
    return `
      <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:14px">
        <div><h2>Migration dashboard</h2><p class="lede" style="margin:0">Simulated clock <b>${simTime(sim.t)}</b>. A task starts once its upstream PRs merge and a Devin session is free (max ${plan.params.sessions}).</p></div>
        <div style="display:flex;gap:8px">
          <button class="btn" id="run" ${done ? "disabled" : ""}>${timer ? "❚❚ Pause" : "▶ Run simulation"}</button>
          <button class="btn ghost" id="adv" ${done ? "disabled" : ""}>Advance 4h</button>
          <button class="btn ghost" id="finish" ${done ? "disabled" : ""}>Complete all</button>
        </div>
      </div>
      <div class="grid kpis">
        ${kpi("Modules migrated", `${merged.length}/${MODS.length}`, `${Math.round((merged.length / MODS.length) * 100)}% of scope`)}
        ${kpi("Lines migrated", kloc(mergedLoc), `${Math.round((mergedLoc / SEED.meta.total_loc) * 100)}% of ${kloc(SEED.meta.total_loc)}`)}
        ${kpi("PRs merged", `${counts.merged}/${plan.order.length}`, `${counts.review} awaiting review`)}
        ${kpi("Active Devin sessions", `${counts.running + counts.testing}/${plan.params.sessions}`, `${counts.blocked} tasks blocked on upstream`)}
        ${kpi("Engineer hours spent", `${fmt(Math.round(eng))}h`, manual ? `vs ~${fmt(manual)}h manual estimate (${(manual / eng).toFixed(1)}x)` : "scoping + review on merged PRs")}
      </div>
      <div class="grid two" style="margin-bottom:14px">
        <div class="card"><h3>Burn-up: modules migrated</h3>${burnup()}</div>
        <div class="card"><h3>Phase progress</h3>${plan.phases.map((ids, i) => {
          const c = (s) => ids.filter((id) => sim.tasks[id].status === s).length;
          const seg = (n, col) => `<i style="width:${(n / ids.length) * 100}%;background:${col}"></i>`;
          return `<div style="margin:8px 0"><div style="display:flex;justify-content:space-between;font-size:12.5px"><b>Phase ${i + 1}</b><span class="muted">${c("merged")}/${ids.length} merged</span></div><div class="progress">${seg(c("merged"), "var(--low)")}${seg(c("review"), "var(--med)")}${seg(c("testing"), "var(--purple)")}${seg(c("running"), "var(--blue)")}</div></div>`;
        }).join("")}
          <div class="legend" style="margin-top:10px"><span><i style="background:var(--blue)"></i>coding</span><span><i style="background:var(--purple)"></i>testing</span><span><i style="background:var(--med)"></i>review</span><span><i style="background:var(--low)"></i>merged</span></div></div>
      </div>
      <div class="grid board" style="margin-bottom:14px">${cols.map(([label, ss]) => {
        const ids = plan.order.filter((id) => ss.includes(displayStatus(id)));
        return `<div class="col"><h4><span>${label}</span><span>${ids.length}</span></h4>${ids.map((id) => taskCard(plan.tasks[id], true)).join("")}</div>`;
      }).join("")}</div>
      <div class="card"><h3>Activity</h3><div class="log" style="max-height:240px;overflow:auto">${sim.log.slice(0, 60).map((l) => `<div><b>${simTime(l.t)}</b>${esc(l.msg)}</div>`).join("")}</div></div>`;
  }

  // ------------------------------------------------------------------ router
  function route() { const parts = (location.hash || "#/inventory").slice(2).split("/"); return { view: parts[0] || "inventory", arg: parts[1] }; }
  function render() {
    const { view, arg } = route();
    document.querySelectorAll("#tabs a").forEach((a) => a.classList.toggle("active", a.dataset.view === view));
    const scrollY = window.scrollY;
    const focus = document.activeElement && document.activeElement.id;
    $app.innerHTML = view === "plan" ? viewPlan() : view === "task" ? viewTask(arg) : view === "dashboard" ? viewDashboard() : viewInventory();
    if (focus === "q") { const q = document.getElementById("q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
    window.scrollTo(0, scrollY);
  }
  window.addEventListener("hashchange", () => { $drawer.hidden = true; ui.taskMod = 0; render(); window.scrollTo(0, 0); });

  document.addEventListener("click", (e) => {
    const el = (sel) => e.target.closest(sel);
    let n;
    if ((n = el("th[data-sort]"))) { const k = n.dataset.sort; ui.sort = { key: k, dir: ui.sort.key === k ? -ui.sort.dir : (typeof MODS[0][k] === "string" ? 1 : -1) }; render(); }
    else if ((n = el("[data-mod]"))) openDrawer(n.dataset.mod);
    else if (el("#dclose")) $drawer.hidden = true;
    else if ((n = el("[data-task]")) && !el("button")) location.hash = `#/task/${n.dataset.task}`;
    else if ((n = el("[data-goto]"))) location.hash = `#/task/${n.dataset.goto}`;
    else if ((n = el("[data-tm]"))) { ui.taskMod = +n.dataset.tm; render(); }
    else if (el("#gen")) { setRunning(false); state.plan = generatePlan(state.params); state.sim = newSim(state.plan); save(); render(); }
    else if (el("#genDefault")) { ensurePlan(); render(); }
    else if ((n = el("#ff"))) { fastForward(n.dataset.task); render(); }
    else if ((n = el("#approve"))) { approve(n.dataset.task); render(); }
    else if (el("#run")) { setRunning(!timer); render(); }
    else if (el("#adv")) { step(4); render(); }
    else if (el("#finish")) { setRunning(false); step(24 * 60); render(); }
    else if (el("#reset")) { setRunning(false); localStorage.removeItem(STORE_KEY); state = load(); $drawer.hidden = true; location.hash = "#/inventory"; render(); }
  });
  document.addEventListener("input", (e) => {
    const id = e.target.id;
    if (id === "q") { ui.q = e.target.value; render(); }
    else if (id === "fdomain") { ui.domain = e.target.value; render(); }
    else if (id === "fband") { ui.band = e.target.value; render(); }
    else if (id === "sessions" || id === "perTask") { state.params[id] = +e.target.value; document.getElementById(id === "sessions" ? "vs" : "vp").textContent = e.target.value; save(); }
    else if (id === "iso") { state.params.isolateCritical = e.target.checked; save(); }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $drawer.hidden = true; });

  window.__demo = { generatePlan, state: () => state };
  render();
})();
