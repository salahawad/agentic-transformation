"use strict";
const $ = (s, root = document) => root.querySelector(s);
const app = $("#app");
const modal = $("#modal");
const paths = {
  nodes: "M4 4h6v6H4zM14 14h6v6h-6zM14 4h6v6h-6zM7 10v7h7M10 7h4",
  spark: "M12 2v20M2 12h20M5 5l14 14M5 19 19 5",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  people:
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  building: "M4 22V3h12v19M16 10h4v12M2 22h20M8 7h4M8 11h4M8 15h4M8 19h4",
  tools: "m12 3 9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 16l9 5 9-5",
  route:
    "M4 6a3 3 0 1 0 6 0 3 3 0 0 0-6 0M14 18a3 3 0 1 0 6 0 3 3 0 0 0-6 0M10 6h5a4 4 0 0 1 0 8H9a4 4 0 0 0-4 4h9",
  plus: "M12 5v14M5 12h14",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  chevron: "m9 5 7 7-7 7",
  check: "m5 12 4 4L19 6",
  close: "m6 6 12 12M6 18 18 6",
  clock: "M12 8v4l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  robot: "M9 3h6M12 3v3M5 7h14v14H5zM8 11h1M15 11h1M9 17h6M2 11v6M22 11v6",
  link: "m10 13 4-4M8 16l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0M16 8l1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0",
  copy: "M9 9h12v12H9zM5 15H3V3h12v2",
  edit: "m15 4 5 5M4 16 17 3l4 4L8 20l-5 1 1-5z",
  logout: "M9 4H3v16h6M10 12h11m-5-5 5 5-5 5",
  search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  info: "M12 11v6M12 7h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
  up: "m6 15 6-6 6 6",
  down: "m6 9 6 6 6-6",
  trash: "M3 6h18M5 6l1 15h12l1-15M9 6V3h6v3M10 10v7M14 10v7",
  shield: "m12 3 8 3v6c0 5-8 10-8 10S4 17 4 12V6l8-3zM8 12l3 3 5-5",
  refresh: "M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 3M18 18a8 8 0 0 1-13-3",
  menu: "M3 6h18M3 12h18M3 18h18",
  mail: "M3 5h18v14H3zM3 5l9 8 9-8",
  text: "M4 5h16M4 10h16M4 15h10M4 20h10",
  diagram: "M3 8h6v8H3zM15 8h6v8h-6zM9 12h6m-3-3 3 3-3 3",
};
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.spark}"/></svg>`;
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const initials = (name) =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0])
    .join("")
    .toUpperCase();
const plural = (n, noun) => {
  const many = { person: "people", opportunity: "opportunities" }[noun] || `${noun}s`;
  return `${formatNumber(n)} ${tr(n === 1 ? noun : many)}`;
};
const brand = () => `<div class="brand"><span class="brand-mark">${icon("nodes")}</span>${tr("Agent Atlas")}<span class="screen-reader">${tr("Transformation workspace")}</span></div>`;
const state = {
  data: null,
  page: "overview",
  entity: "",
  team: "",
  search: "",
  intake: null,
  stage: 0,
  token: "",
  savedAt: null,
  savedRest: "",
};
function opportunityName(opportunity) {
  return tr("{0} assistant", opportunity.workflow_name);
}
function categoryLabel(category) {
  const defaults = ["Communication", "Documents & knowledge", "Projects & operations",
    "Business systems", "Design & development", "AI assistants"];
  return defaults.includes(category) ? tr(category) : category;
}
function changeLanguage(value) {
  if (state.saving || modal.open) {
    $("#language-select").value = language;
    return;
  }
  const fields = [...app.querySelectorAll("input[id], textarea[id], select[id]")]
    .filter((node) => node.id !== "language-select")
    .map((node) => ({ id: node.id, value: node.value, checked: node.checked }));
  const focus = document.activeElement.id;
  const scroll = window.scrollY;
  setLanguage(value);
  if (state.screen === "workspace") renderShell();
  else if (state.screen === "intake") renderIntake();
  else if (state.screen === "success") renderSuccess();
  else if (state.screen === "error") renderStartError(state.startError, state.intakeError);
  else renderLogin();
  for (const field of fields) {
    const node = document.getElementById(field.id);
    if (node) {
      node.value = field.value;
      if (node.type === "checkbox") node.checked = field.checked;
    }
  }
  if ($("#tool-search")) renderToolOptions($("#tool-search").value);
  $("#toast").hidden = true;
  document.getElementById(focus)?.focus({ preventScroll: true });
  window.scrollTo(0, scroll);
}
function renderStartError(error, intake = false) {
  state.screen = "error";
  state.startError = error;
  state.intakeError = intake;
  app.innerHTML = `${intakeHeader()}<main class="intake-error"><span class="empty-icon">${icon("shield")}</span><h1>${tr(intake ? "Let’s get you the right link." : "We couldn’t open the workspace.")}</h1><p>${esc(localizeError(error.detail || error.message))}</p>${intake ? "" : `<button class="button" data-action="reload">${tr("Try reloading the page")}</button>`}</main>`;
}
const workflowViews = new WeakMap();
function workflowView(workflow) {
  if (!workflowViews.has(workflow))
    workflowViews.set(workflow, { mode: "text", selected: 0 });
  return workflowViews.get(workflow);
}
// Last saved JSON of each workflow, so one workflow can be saved without the others.
const savedWorkflows = new WeakMap();
function rememberSaved() {
  const a = state.intake.assessment;
  a.workflows.forEach((w) => savedWorkflows.set(w, JSON.stringify(w)));
  state.savedRest = JSON.stringify({ tools: a.tools, notes: a.notes });
}
function workflowSaveState(w) {
  const saved = savedWorkflows.get(w);
  return saved === undefined
    ? "new"
    : saved === JSON.stringify(w)
      ? "saved"
      : "changed";
}
function unsavedParts() {
  const a = state.intake.assessment;
  const rest = JSON.parse(state.savedRest);
  return [
    JSON.stringify(a.tools) !== JSON.stringify(rest.tools) && tr("tools"),
    ...a.workflows.map(
      (w, i) => workflowSaveState(w) !== "saved" && tr("workflow {0}", i + 1),
    ),
    a.notes !== rest.notes && tr("notes"),
  ].filter(Boolean);
}
function workflowSaveBadge(w) {
  const status = workflowSaveState(w);
  return status === "saved"
    ? `<span class="tag green">${tr("{0}Saved", icon("check"))}</span>`
    : `<span class="tag amber">${status === "new" ? tr("Not saved yet") : tr("Unsaved changes")}</span>`;
}
function saveNote() {
  const unsaved = unsavedParts();
  if (unsaved.length) return tr("Not saved yet: {0}", unsaved.join(", "));
  if (state.savedAt)
    return tr("All changes saved {0}", new Date(state.savedAt * 1000).toLocaleTimeString(currentLocale(), { hour: "2-digit", minute: "2-digit" }));
  return state.intake.assessment.revision
    ? tr("All changes saved")
    : tr("Your progress is saved when you continue.");
}
function showSaveStatus() {
  document.querySelectorAll("[data-workflow-saved]").forEach((node) => {
    node.innerHTML = workflowSaveBadge(
      state.intake.assessment.workflows[+node.dataset.workflowSaved],
    );
  });
  const note = $("#save-status");
  if (note) note.textContent = saveNote();
}
let toastTimer;
function toast(message, error = false) {
  const node = $("#toast");
  node.textContent = message;
  node.className = `toast${error ? " error" : ""}`;
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    node.hidden = true;
  }, 5000);
}
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (path === "/api/intake") headers.Authorization = `Bearer ${state.token}`;
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch {
    const error = new Error(tr("Unable to connect. Please try again."));
    error.detail = "Unable to connect. Please try again.";
    throw error;
  }
  const raw = await response.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    data = { detail: raw };
  }
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map(validationMessage)
          .join("; ")
      : data.detail;
    const error = new Error(localizeError(detail) || tr("Request failed ({0})", response.status));
    error.detail = detail;
    error.status = response.status;
    throw error;
  }
  return data;
}
const post = (path, data = {}) =>
  api(path, { method: "POST", body: JSON.stringify(data) });
function filterData() {
  const employees = state.data.employees.filter(
    (p) =>
      (!state.entity || p.entity_id === +state.entity) &&
      (!state.team || p.team_id === +state.team),
  );
  const opportunities = state.data.opportunities.filter(
    (o) =>
      (!state.entity || o.entity_id === +state.entity) &&
      (!state.team || o.team_id === +state.team),
  );
  return { employees, opportunities };
}
function statusTag(status) {
  return `<span class="tag ${status === "submitted" ? "green" : status === "draft" ? "amber" : "blue"}">${status === "submitted" ? icon("check") : ""}${status === "submitted" ? tr("Completed") : status === "draft" ? tr("In progress") : tr("Invited")}</span>`;
}
function empty(title, description, action = "", symbol = "spark") {
  return `<div class="empty"><span class="empty-icon">${icon(symbol)}</span><h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
}
function filters() {
  const teams = state.data.teams.filter(
    (t) => !state.entity || t.entity_id === +state.entity,
  );
  return `<div class="filter-row"><label class="screen-reader" for="entity-filter">${tr("Filter by entity")}</label><select id="entity-filter"><option value="">${tr("All entities")}</option>${state.data.entities.map((e) => `<option value="${e.id}" ${String(e.id) === state.entity ? "selected" : ""}>${esc(e.name)}</option>`).join("")}</select><label class="screen-reader" for="team-filter">${tr("Filter by team")}</label><select id="team-filter"><option value="">${tr("All teams")}</option>${teams.map((t) => `<option value="${t.id}" ${String(t.id) === state.team ? "selected" : ""}>${esc(t.name)}</option>`).join("")}</select></div>`;
}
function pageHeading(eyebrow, title, subtitle, button = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div>${button}</div>`;
}
const inviteButton = () => `<button class="button primary" data-action="add-person">${tr("{0}Invite employee", icon("plus"))}</button>`;
const navItems = [
  ["overview", "grid", "Overview"],
  ["people", "people", "People & assessments"],
  ["organization", "building", "Organization"],
  ["tools", "tools", "Digital tools"],
  ["roadmap", "spark", "Agent opportunities"],
];
// Collaborators see only their entities; the server enforces this, the interface just hides admin-only controls.
const isAdmin = () => !state.data?.viewer;
function renderShell() {
  state.screen = "workspace";
  const viewer = state.data.viewer;
  const avatar = viewer ? esc(initials(viewer.name)) : tr("WA");
  if (!navItems.some((n) => n[0] === state.page)) state.page = "overview";
  const title = tr(navItems.find((n) => n[0] === state.page)[2]);
  const completed = state.data.employees.filter((p) => p.status === "submitted").length;
  const percent = state.data.employees.length
    ? Math.round((completed / state.data.employees.length) * 100) : 0;
  app.innerHTML = `
    <a class="skip-link" href="#content">${tr("Skip to content")}</a>
    <aside class="sidebar" id="sidebar">
      ${brand()}
      <div class="workspace-context"><span class="workspace-icon">${icon("building")}</span><div><strong>${tr("Company workspace")}</strong><span>${tr("Agentic transformation")}</span></div></div>
      <div class="workspace-label">${tr("Workspace")}</div>
      <nav class="nav" aria-label="${tr("Main navigation")}">${navItems.map(([id, symbol, label]) => `${id === "tools" ? `<div class="workspace-label nav-label">${tr("Intelligence")}</div>` : ""}<a href="#${id}" class="${state.page === id ? "active" : ""}" ${state.page === id ? 'aria-current="page"' : ""}>${icon(symbol)}<span>${tr(label)}</span>${id === "people" || id === "roadmap" ? `<span class="count" aria-hidden="true">${id === "people" ? state.data.employees.length : state.data.opportunities.length}</span>` : ""}</a>`).join("")}</nav>
      <div class="sidebar-bottom">
        <a class="sidebar-note" href="#people"><div class="sidebar-note-heading">${tr("Discovery progress")}<span>${percent}%</span></div><progress value="${completed}" max="${Math.max(state.data.employees.length, 1)}" aria-label="${tr("Workspace assessment completion")}"></progress><span>${tr("{0} of {1} assessments completed", completed, state.data.employees.length)}</span><strong>${tr("Keep the discovery moving {0}", icon("arrow"))}</strong></a>
        <div class="user-badge"><span class="avatar">${avatar}</span><div><strong class="small">${viewer ? esc(viewer.name) : tr("Workspace admin")}</strong><div class="small muted">${viewer ? tr("Collaborator") : tr("Transformation lead")}</div></div><button class="icon-button" data-action="logout" aria-label="${tr("Sign out")}" title="${tr("Sign out")}">${icon("logout")}</button></div>
      </div>
    </aside>
    <main class="main"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-menu" data-action="menu" aria-label="${tr("Toggle navigation")}" aria-controls="sidebar" aria-expanded="false">${icon("menu")}</button><span class="workspace-crumb">${tr("Workspace")}</span><span class="workspace-crumb">/</span><strong>${title}</strong></div><div class="topbar-right">${languagePicker()}<span class="live-label">${tr("{0}Private workspace", icon("shield"))}</span><span class="topbar-divider"></span><button class="icon-button" data-action="refresh" aria-label="${tr("Refresh workspace")}" title="${tr("Refresh workspace")}">${icon("refresh")}</button><span class="avatar">${avatar}</span></div></header><div class="content" id="content" tabindex="-1"></div></main>`;
  renderContent();
}
function renderContent() {
  (
    ({
      overview: renderOverview,
      people: renderPeople,
      organization: renderOrganization,
      tools: renderTools,
      roadmap: renderRoadmap,
    })[state.page] || renderOverview
  )();
}
function renderOverview() {
  const { employees, opportunities } = filterData();
  const completed = employees.filter((p) => p.status === "submitted").length;
  const workflows = employees.filter((p) => p.status === "submitted")
    .reduce((n, p) => n + p.workflow_count, 0);
  const hours = opportunities.reduce((n, o) => n + o.estimated_hours, 0);
  const percent = employees.length ? Math.round((completed / employees.length) * 100) : 0;
  const hasTeams = state.data.teams.length > 0;
  const nextPage = !hasTeams ? "organization" : opportunities.length ? "roadmap" : "people";
  const nextLabel = !hasTeams ? tr("Set up your organization") : opportunities.length ? tr("Explore opportunities") : tr("Manage assessments");
  $("#content").innerHTML = `
    ${pageHeading(tr("Discover. Design. Transform."), tr("Transformation overview"), tr("A clearer picture of your work. A practical path to your next agent."), inviteButton())}
    <section class="workspace-hero" aria-labelledby="hero-title">
      <div class="hero-copy"><span class="hero-kicker"><span class="dot"></span>${tr("YOUR AGENTIC TRANSFORMATION STARTS HERE")}</span><h2 id="hero-title">${tr("Great agents start")}<br>${tr("with everyday work.")}</h2><p>${tr("Find the repetitive work. Connect the right tools.")}<br>${tr("Put your people at the center of every pilot.")}</p><a class="button primary" href="#${nextPage}">${nextLabel}${icon("arrow")}</a></div>
      <div class="hero-canvas" aria-label="${tr("Discovery process: map workflows, identify opportunities, then validate with people")}"><span class="canvas-caption">${tr("FROM WORKFLOW TO OPPORTUNITY")}</span><div class="hero-flow"><div class="hero-node"><span class="hero-node-icon">${icon("route")}</span><strong>${tr("Map the work")}</strong><span>${tr("{0} shared", plural(workflows, "workflow"))}</span></div><span class="hero-connector">${icon("arrow")}</span><div class="hero-node featured"><span class="hero-node-icon">${icon("nodes")}</span><strong>${tr("Find the agent")}</strong><span>${plural(opportunities.length, "opportunity")}</span></div><span class="hero-connector">${icon("arrow")}</span><div class="hero-node"><span class="hero-node-icon">${icon("shield")}</span><strong>${tr("Keep people in")}</strong><span>${tr("Validate in a pilot")}</span></div></div><span class="canvas-note">${tr("{0}Grounded in your team’s tools and workflows", icon("link"))}</span></div>
    </section>
    <div class="overview-toolbar"><h2>${tr("Workspace at a glance")}</h2>${filters()}</div>
    <div class="stats">${[
      ["people", tr("People invited"), employees.length, "", tr("{0} completed · {1}% coverage", completed, percent)],
      ["route", tr("Workflows mapped"), workflows, "", tr("From completed assessments")],
      ["nodes", tr("Agent opportunities"), opportunities.length, "", tr("Grounded in submitted workflows")],
      ["clock", tr("Potential time back"), formatNumber(hours, 1), tr("h / week"), tr("Planning estimate · validate in a pilot")],
    ].map(([i, label, value, unit, caption]) => `<div class="stat"><div class="stat-head">${label}<span class="stat-icon">${icon(i)}</span></div><div class="stat-value">${value}<span>${unit}</span></div><div class="stat-caption">${esc(caption)}</div></div>`).join("")}</div>
    <div class="section-heading"><div><h2>${tr("Agent opportunities")} <span class="tag outline">${opportunities.length}</span></h2><p>${tr("Your next pilots, ranked by potential weekly impact.")}</p></div><a href="#roadmap" class="text-link">${tr("View all opportunities {0}", icon("arrow"))}</a></div>
    ${opportunities.length ? `<div class="opportunity-grid">${opportunities.slice(0, 4).map(agentCard).join("")}</div><p class="method-note">${tr("{0}Estimates use 50% of assisted or human-reviewed steps and 70% of automated steps. These are planning assumptions, not measured savings.", icon("info"))}</p>` : `<div class="panel">${empty(tr("Your next helpful agent starts here"), tr("Opportunities appear when employees submit workflows. Each proposal includes its source evidence, tools, and potential impact."), `<a class="button" href="#people">${tr("View people & assessments")}` + icon("arrow") + `</a>`, "nodes")}</div>`}
    <div class="section-heading"><div><h2>${tr("Discovery coverage")}</h2><p>${tr("See where your organization is ready for the next step.")}</p></div><a href="#organization" class="text-link">${tr("Manage organization {0}", icon("arrow"))}</a></div>
    <div class="coverage-grid"><section class="panel"><div class="panel-header"><div><h3>${tr("Assessment coverage by entity")}</h3><p>${tr("Completion for the selected people and teams")}</p></div><span class="tag blue">${tr("{0}% complete", percent)}</span></div>${state.data.entities.length ? state.data.entities.filter((e) => !state.entity || e.id === +state.entity).map((e) => {
      const people = employees.filter((p) => p.entity_id === e.id);
      const done = people.filter((p) => p.status === "submitted").length;
      return `<div class="entity-row"><span class="entity-icon">${icon("building")}</span><div><h3>${esc(e.name)}</h3><small>${plural(state.data.teams.filter((t) => t.entity_id === e.id).length, "team")} · ${plural(people.length, "person")}</small></div><div class="entity-data">${done}<span class="muted"> / ${people.length}</span><small>${tr("completed")}</small></div><div class="entity-progress"><progress value="${done}" max="${Math.max(people.length, 1)}" aria-label="${tr("{0} assessment completion", esc(e.name))}"></progress></div></div>`;
    }).join("") : empty(tr("Give your workspace a shape"), tr("Create an entity and team to start discovering how work happens."), isAdmin() ? `<button class="button small" data-action="add-entity">` + icon("plus") + `${tr("Add entity")}</button>` : "", "building")}</section>
    <section class="panel next-steps"><div class="panel-header"><div><h3>${tr("Your path to a pilot")}</h3><p>${tr("Three steps to a useful agent")}</p></div>${icon("route")}</div><ol class="discovery-steps">${[
      [hasTeams, tr("Map your organization"), tr("Connect entities, teams, and people."), "organization"],
      [completed > 0, tr("Understand the work"), tr("Collect tools, workflows, and friction."), "people"],
      [opportunities.length > 0, tr("Discover agent opportunities"), tr("Review the evidence and potential impact."), "roadmap"],
    ].map(([done, title, description, route], i) => `<li class="${done ? "done" : ""}"><span class="step-dot">${done ? icon("check") : String(i + 1).padStart(2, "0")}</span><a href="#${route}"><strong>${title}</strong><span>${description}</span></a>${icon("chevron")}</li>`).join("")}</ol></section></div>
    <div class="section-heading"><div><h2>${tr("People & assessments")}</h2><p>${tr("The people bringing your workflows into focus.")}</p></div><a href="#people" class="text-link">${tr("View all people {0}", icon("arrow"))}</a></div>${peopleTable(employees.slice(0, 5))}`;
}
function agentCard(o) {
  return `<article class="agent-card"><div class="agent-top"><span class="agent-symbol">${icon("nodes")}</span><span class="tag ${o.priority === "High" ? "green" : o.priority === "Medium" ? "amber" : "blue"}"><i class="priority-dot"></i>${tr("{0} priority", esc(tr(o.priority)))}</span></div><h3>${esc(opportunityName(o))}</h3><div class="agent-meta">${esc(o.entity_name)} / ${esc(o.team_name)}</div><p class="agent-description">${tr("Help with {0}.", esc(o.actions.slice(0, 3).join(", ")))}</p><div class="tool-chips">${o.tools.slice(0, 4).map((t) => `<span class="tool-chip"><span class="tool-letter">${esc(t[0])}</span>${esc(t)}</span>`).join("")}${o.tools.length > 4 ? `<span class="tool-chip">+${o.tools.length - 4}</span>` : ""}${!o.tools.length ? `<span class="tag">${tr("Integration to explore")}</span>` : ""}</div><div class="agent-evidence"><span>${icon("route")}${plural(o.evidence.length, "source workflow")}</span><span>${icon(o.human_review ? "shield" : "people")}${o.human_review ? tr("Human review required") : tr("People supported: {0}", formatNumber(o.people.length))}</span></div><div class="agent-footer"><div class="agent-impact"><strong>~${formatNumber(o.estimated_hours, 1)}<span>${tr("h")}</span></strong><span> ${tr("/ week potential")}</span></div><button class="text-link" data-action="agent-detail" data-id="${o.id}">${tr("Explore opportunity {0}", icon("arrow"))}</button></div></article>`;
}
function peopleTable(people) {
  if (!people.length)
    return `<div class="panel">${empty(tr("Bring your people into the picture"), tr("Invite an employee, assign their team, and share their private assessment link."), inviteButton(), "people")}</div>`;
  return `<div class="panel table-panel"><div class="table-wrap"><table><thead><tr><th>${tr("Employee")}</th><th>${tr("Entity / team")}</th><th>${tr("Assessment")}</th><th>${tr("Workflows")}</th><th>${tr("Actions")}</th></tr></thead><tbody>${people.map((p) => `<tr><td><div class="person-cell"><span class="avatar">${esc(initials(p.name))}</span><div><strong>${esc(p.name)}</strong><small>${esc(p.role)}</small></div></div></td><td>${esc(p.entity_name)}<div class="small muted">${esc(p.team_name)}</div></td><td>${statusTag(p.status)}</td><td>${p.workflow_count || "—"}</td><td><div class="table-actions"><button class="icon-button" data-action="edit-person" data-id="${p.id}" title="${tr("Edit employee")}" aria-label="${tr("Edit {0}", esc(p.name))}">${icon("edit")}</button>${p.status !== "invited" ? `<button class="icon-button" data-action="view-assessment" data-id="${p.id}" title="${tr("View assessment")}" aria-label="${tr("View assessment for {0}", esc(p.name))}">${icon("route")}</button>` : ""}<button class="button small" data-action="issue-invite" data-id="${p.id}">${tr("{0}Invite link", icon("link"))}</button></div></td></tr>`).join("")}</tbody></table></div><div class="table-footer"><span>${plural(people.length, "employee")}</span><span>${tr("Private assessment links · Valid for 30 days")}</span></div></div>`;
}
function renderPeople() {
  const { employees } = filterData();
  const found = employees.filter((p) =>
    `${p.name} ${p.email} ${p.role}`
      .toLowerCase()
      .includes(state.search.toLowerCase()),
  );
  $("#content").innerHTML =
    `${pageHeading(tr("Listen to your people"), tr("People & assessments"), tr("Invite each employee to share their tools and workflows. Keep everyone connected to the right team."), inviteButton())}<div class="section-heading"><div class="search"><label class="screen-reader" for="people-search">${tr("Search employees")}</label>${icon("search")}<input id="people-search" placeholder="${tr("Search name, role, or email…")}" value="${esc(state.search)}"></div>${filters()}</div><div id="people-results">${peopleTable(found)}</div>`;
}
function renderOrganization() {
  const { entities, teams, employees } = state.data;
  const admin = isAdmin();
  $("#content").innerHTML =
    `${pageHeading(tr("The structure behind the work"), tr("Your organization"), tr("Create entities and their teams, then connect every employee to the people they work with."), admin ? `<button class="button primary" data-action="add-entity">` + icon("plus") + `${tr("Add entity")}</button>` : "")}
  ${entities.length
      ? `<div class="organization-grid">${entities
          .map(
            (e) =>
              `<section class="panel"><div class="panel-header"><div class="org-entity-name"><span class="entity-icon">${icon("building")}</span><div><h2>${esc(e.name)}</h2><p>${plural(employees.filter((p) => p.entity_id === e.id).length, "employee")}</p></div></div><div class="table-actions">${admin ? `<button class="icon-button" data-action="edit-entity" data-id="${e.id}" title="${tr("Rename entity")}" aria-label="${tr("Rename {0}", esc(e.name))}">${icon("edit")}</button>${deleteButton(`/api/admin/entities/${e.id}`, e.name, tr("Delete the {0} entity?", e.name))}` : ""}<button class="button small" data-action="add-team" data-id="${e.id}">${tr("{0}Add team", icon("plus"))}</button></div></div>${teams
                  .filter((t) => t.entity_id === e.id)
                  .map(
                    (t) =>
                      `<div class="team-row"><span>${esc(t.name)}</span><div class="table-actions"><span class="tag">${plural(employees.filter((p) => p.team_id === t.id).length, "person")}</span><button class="icon-button" data-action="edit-team" data-id="${t.id}" title="${tr("Edit team")}" aria-label="${tr("Edit {0}", esc(t.name))}">${icon("edit")}</button>${deleteButton(`/api/admin/teams/${t.id}`, t.name, tr("Delete the {0} team?", t.name))}</div></div>`,
                  )
                  .join("") ||
                `<p class="muted small">${tr("No teams yet. Add a team to invite your first employee.")}</p>`}</section>`,
          )
          .join("")}</div>${admin ? collaboratorsPanel() : ""}`
      : !admin
        ? `<div class="panel">${empty(tr("No entities shared with you yet"), tr("Ask the workspace administrator to give you access to an entity."), "", "building")}</div>`
        : `<div class="onboarding-list">${[
          [
            "01",
            tr("Create an entity"),
            tr("An entity can be a business unit, department, or legal company."),
            "add-entity",
            tr("Add your first entity"),
          ],
          [
            "02",
            tr("Build your teams"),
            tr("Group people into the teams where their day-to-day work happens."),
            "add-team",
            tr("Add a team"),
          ],
          [
            "03",
            tr("Start the conversation"),
            tr("Invite your people to share their digital tools and simple workflows."),
            "add-person",
            tr("Invite an employee"),
          ],
        ]
          .map(
            ([n, t, d, a, l]) =>
              `<div class="onboard-step"><div class="number">${tr("{0} / GET STARTED", n)}</div><h3>${t}</h3><p>${d}</p><button class="button small" data-action="${a}">${icon("plus")}${l}</button></div>`,
          )
          .join("")}</div>`}`;
}
function collaboratorsPanel() {
  const { collaborators, entities } = state.data;
  const names = (ids) => entities.filter((e) => ids.includes(e.id)).map((e) => esc(e.name)).join(", ");
  return `<div class="section-heading"><div><h2>${tr("Collaborators")}</h2><p>${tr("People who help manage selected entities: their teams, employees, invitations, and results. They cannot see other entities.")}</p></div><button class="button" data-action="collaborator">${tr("{0}Invite collaborator", icon("plus"))}</button></div><div class="panel">${
    collaborators
      .map(
        (c) =>
          `<div class="team-row"><span><strong>${esc(c.name)}</strong> <span class="muted">${esc(c.email)}</span><span class="small muted collaborator-entities">${names(c.entity_ids) || tr("No entities")}</span></span><div class="table-actions"><button class="icon-button" data-action="collaborator" data-id="${c.id}" title="${tr("Edit collaborator")}" aria-label="${tr("Edit {0}", esc(c.name))}">${icon("edit")}</button><button class="icon-button" data-action="collaborator-link" data-id="${c.id}" title="${tr("New sign-in link")}" aria-label="${tr("New sign-in link for {0}", esc(c.name))}">${icon("link")}</button>${deleteButton(`/api/admin/collaborators/${c.id}`, c.name, tr("Remove {0}? They lose access immediately.", c.name))}</div></div>`,
      )
      .join("") || `<p class="muted small">${tr("No collaborators yet.")}</p>`
  }</div>`;
}
function renderTools() {
  const { employees } = filterData();
  const usage = new Map();
  employees.forEach((p) =>
    p.tools.forEach((t) => usage.set(t, (usage.get(t) || 0) + 1)),
  );
  const catalog = [...state.data.catalog];
  const known = new Set(catalog.map((t) => t.name.toLowerCase()));
  for (const t of usage.keys())
    if (!known.has(t.toLowerCase()))
      catalog.push({ name: t, category: tr("Custom tools") });
  const groups = [...new Set(catalog.map((t) => t.category))];
  $("#content").innerHTML =
    `${pageHeading(tr("Understand your digital ecosystem"), tr("The tools behind the work"), tr("See which digital tools your people use and where future agents will need to connect. Edit the list employees choose from."), isAdmin() ? `<button class="button primary" data-action="new-tool">${tr("{0}Add tool", icon("plus"))}</button>` : "")}<div class="section-heading"><div><h2>${tr("{0} tools reported", usage.size)}</h2><p>${tr("Usage includes saved drafts and completed assessments.")}</p></div>${filters()}</div><div class="catalog-grid">${groups
      .map(
        (g) =>
          `<section class="panel"><h3>${esc(categoryLabel(g))}</h3>${catalog
            .filter((t) => t.category === g)
            .map(
              (t) =>
                `<div class="catalog-tool"><span class="tool-letter">${esc(t.name[0])}</span><span>${esc(t.name)}</span><span class="tag ${usage.has(t.name) ? "green" : ""}">${plural(usage.get(t.name) || 0, "person")}</span>${!isAdmin() ? "" : t.id
                    ? `<button class="icon-button" data-action="edit-tool" data-id="${t.id}" title="${tr("Edit tool")}" aria-label="${tr("Edit {0}", esc(t.name))}">${icon("edit")}</button>${deleteButton(`/api/admin/tools/${t.id}`, t.name, tr("Remove {0} from the tools list? Employees who already chose it keep it in their answers.", t.name))}`
                    : `<button class="icon-button" data-action="new-tool" data-name="${esc(t.name)}" title="${tr("Add to the tools list")}" aria-label="${tr("Add {0} to the tools list", esc(t.name))}">${icon("plus")}</button>`}</div>`,
            )
            .join("")}</section>`,
      )
      .join("")}</div>`;
}
function renderRoadmap() {
  const { opportunities } = filterData();
  $("#content").innerHTML =
    `${pageHeading(tr("Turn understanding into action"), tr("Your next agent opportunities"), tr("Explore the work an agent could support, who it would help, and the tools it would need."), `<button class="button" data-action="export">` + icon("download") + `${tr("Export opportunities")}</button>`)}<div class="section-heading"><div><h2>${plural(opportunities.length, "opportunity")}</h2><p>${tr("Ranked by estimated weekly time that could be returned to your teams.")}</p></div>${filters()}</div>${opportunities.length ? `<div class="opportunity-grid">${opportunities.map(agentCard).join("")}</div><div class="panel"><p class="method-note">${tr("{0}Planning estimates: 50% of assisted step time, 70% of automated step time, and 50% when human review is required. Manual steps contribute no estimated savings. Matching workflow names within a team are grouped. These proposals need integration, permission, and feasibility checks before implementation.", icon("info"))}</p></div>` : `<div class="panel">${empty(tr("A roadmap built from real work"), tr("Completed employee assessments will create suggestions here. Steps marked “Human only” stay with your people."), `<a class="button" href="#people">${tr("View assessments")}` + icon("arrow") + `</a>`, "robot")}</div>`}`;
}
function showModal(title, subtitle, body, footer = "") {
  modal.innerHTML = `<div class="modal-head"><div><h2 id="modal-title">${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="icon-button" data-action="close-modal" aria-label="${tr("Close dialog")}">${icon("close")}</button></div>${body}${footer}`;
  if (!modal.open) modal.showModal();
}
const modalError =
  `<div class="alert error" id="modal-error" role="alert" hidden></div>`;
const formFooter = (label = tr("Save"), extra = "") =>
  `<div class="modal-footer">${extra}<button class="button" type="button" data-action="close-modal">${tr("Cancel")}</button><button class="button primary" type="submit">${label}${icon("arrow")}</button></div>`;
const deleteButton = (path, name, question) =>
  `<button class="icon-button" type="button" data-action="delete" data-path="${path}" data-confirm="${esc(question)}" title="${tr("Delete")}" aria-label="${tr("Delete {0}", esc(name))}">${icon("trash")}</button>`;
function entityModal(id) {
  const entity = state.data?.entities.find((e) => e.id === +id);
  showModal(
    entity ? tr("Rename entity") : tr("Add an entity"),
    tr("A business unit, department, or company within your organization."),
    `<form id="entity-form" data-id="${entity?.id || ""}"><div class="modal-body">${modalError}<div class="field"><label for="entity-name">${tr("Entity name")}</label><input id="entity-name" name="name" value="${esc(entity?.name)}" placeholder="${tr("e.g. Operations")}" required maxlength="160" autofocus></div></div>${formFooter(entity ? tr("Save entity") : tr("Create entity"))}</form>`,
  );
}
function teamModal(entityId = "", id) {
  if (!state.data.entities.length) {
    toast(tr("Create an entity first, then add its teams."));
    entityModal();
    return;
  }
  const team = state.data.teams.find((t) => t.id === +id);
  if (team) entityId = team.entity_id;
  showModal(
    team ? tr("Edit team") : tr("Add a team"),
    team
      ? tr("Rename the team or move it to another entity. Its employees move with it.")
      : tr("Every employee will be assigned to a team within an entity."),
    `<form id="team-form" data-id="${team?.id || ""}"><div class="modal-body">${modalError}<div class="field"><label for="team-entity">${tr("Entity")}</label><select id="team-entity" name="entity_id" required>${state.data.entities.map((e) => `<option value="${e.id}" ${e.id === +entityId ? "selected" : ""}>${esc(e.name)}</option>`).join("")}</select></div><div class="field"><label for="team-name">${tr("Team name")}</label><input id="team-name" name="name" value="${esc(team?.name)}" placeholder="${tr("e.g. Customer Success")}" required maxlength="160"></div></div>${formFooter(team ? tr("Save team") : tr("Create team"))}</form>`,
  );
}
function personModal(id) {
  if (!state.data.teams.length) {
    toast(tr("Create an entity and a team before adding employees."));
    teamModal();
    return;
  }
  const person = state.data.employees.find((p) => p.id === +id);
  const entityId = person?.entity_id || state.data.teams[0].entity_id;
  showModal(
    person ? tr("Edit employee") : tr("Invite an employee"),
    tr("Match this person to their entity and team. Then share their private assessment link."),
    `<form id="person-form" data-id="${person?.id || ""}"><div class="modal-body">${modalError}<div class="form-grid"><div class="field full"><label for="person-name">${tr("Full name")}</label><input id="person-name" name="name" value="${esc(person?.name)}" placeholder="${tr("e.g. Alex Morgan")}" required maxlength="160"></div><div class="field"><label for="person-email">${tr("Work email")}</label><input id="person-email" name="email" type="email" value="${esc(person?.email)}" placeholder="${tr("alex@company.com")}" required maxlength="254"></div><div class="field"><label for="person-role">${tr("Role / job title")}</label><input id="person-role" name="role" value="${esc(person?.role)}" placeholder="${tr("e.g. Operations manager")}" required maxlength="160"></div><div class="field"><label for="person-entity">${tr("Entity")}</label><select id="person-entity" required>${state.data.entities.map((e) => `<option value="${e.id}" ${e.id === entityId ? "selected" : ""}>${esc(e.name)}</option>`).join("")}</select></div><div class="field"><label for="person-team">${tr("Team")}</label><select id="person-team" name="team_id" required>${teamOptions(entityId, person?.team_id)}</select></div></div><div class="readonly-note">${person ? tr("Saved workflows follow this employee if their team changes.") : tr("You’ll get a private link to copy and share with this employee. No email is sent automatically.")}</div></div>${formFooter(person ? tr("Save employee") : tr("Create invitation"), person ? `<button class="button danger" type="button" data-action="delete" data-path="/api/admin/employees/${person.id}" data-confirm="${esc(tr("Delete {0} and their saved assessment? This cannot be undone.", person.name))}">${tr("{0}Delete employee", icon("trash"))}</button>` : "")}</form>`,
  );
}
function toolModal(id, name = "") {
  const tool = state.data.catalog.find((t) => t.id === +id);
  const categories = [...new Set(state.data.catalog.map((t) => t.category))];
  showModal(
    tool ? tr("Edit tool") : tr("Add a tool"),
    tool
      ? tr("Renaming also updates the answers employees already saved.")
      : tr("Employees will see it in the list of tools they choose from."),
    `<form id="tool-form" data-id="${tool?.id || ""}"><div class="modal-body">${modalError}<div class="field"><label for="tool-name">${tr("Tool name")}</label><input id="tool-name" name="name" value="${esc(tool?.name ?? name)}" placeholder="${tr("e.g. Zendesk")}" required maxlength="160" autofocus></div><div class="field"><label for="tool-category">${tr("Category")}</label><input id="tool-category" name="category" list="tool-categories" value="${esc(tool?.category)}" placeholder="${tr("e.g. Business systems")}" required maxlength="160"><datalist id="tool-categories">${categories.map((c) => `<option value="${esc(c)}"></option>`).join("")}</datalist></div></div>${formFooter(tool ? tr("Save tool") : tr("Add tool"))}</form>`,
  );
}
function collaboratorModal(id) {
  const collaborator = state.data.collaborators.find((c) => c.id === +id);
  showModal(
    collaborator ? tr("Edit collaborator") : tr("Invite a collaborator"),
    tr("Choose the entities this person can manage. They will not see the others."),
    `<form id="collaborator-form" data-id="${collaborator?.id || ""}"><div class="modal-body">${modalError}<div class="form-grid"><div class="field"><label for="collaborator-name">${tr("Full name")}</label><input id="collaborator-name" name="name" value="${esc(collaborator?.name)}" required maxlength="160" autofocus></div><div class="field"><label for="collaborator-email">${tr("Work email")}</label><input id="collaborator-email" name="email" type="email" value="${esc(collaborator?.email)}" required maxlength="254"></div></div><fieldset class="entity-choices"><legend>${tr("Entities they can manage")}</legend>${state.data.entities.map((e) => `<label class="checkbox-label"><input type="checkbox" name="entity_ids" value="${e.id}" ${collaborator?.entity_ids.includes(e.id) ? "checked" : ""}>${esc(e.name)}</label>`).join("")}</fieldset></div>${formFooter(collaborator ? tr("Save collaborator") : tr("Create sign-in link"))}</form>`,
  );
}
function collaboratorLinkModal(name, invitation) {
  const link = `${location.origin}/join#${invitation.token}`;
  showModal(
    tr("Sign-in link for {0}", name),
    tr("Copy this private link and share it directly with the collaborator."),
    `<div class="modal-body"><div class="alert">${tr("{0} This link signs in to the selected entities only. Keep it private.", icon("shield"))}</div><label for="invite-url">${tr("Collaborator sign-in link")}</label><input id="invite-url" class="invite-link" readonly value="${esc(link)}"><p class="small muted">${tr("Valid until {0}. Creating another link revokes the previous one.", new Date(invitation.expires_at * 1000).toLocaleDateString(currentLocale(), { dateStyle: "medium" }))}</p><div class="button-row"><button class="button primary" data-action="copy-invite">${tr("{0}Copy link", icon("copy"))}</button></div></div><div class="modal-footer"><button class="button" data-action="close-modal">${tr("Done")}</button></div>`,
  );
}
// Admin forms that create with POST /api/admin/<path> and edit with PUT /api/admin/<path>/<id>.
const adminForms = {
  "entity-form": ["entities", "Entity", "Entity created. Add a team to invite your people."],
  "team-form": ["teams", "Team", "Team created. You can now invite employees."],
  "tool-form": ["tools", "Tool", "Tool added. Employees can now choose it."],
  "collaborator-form": ["collaborators", "Collaborator"],
};
function teamOptions(entityId, selected) {
  const teams = state.data.teams.filter((t) => t.entity_id === +entityId);
  return teams.length
    ? teams
        .map(
          (t) =>
            `<option value="${t.id}" ${t.id === selected ? "selected" : ""}>${esc(t.name)}</option>`,
        )
        .join("")
    : `<option value="">${tr("No teams in this entity")}</option>`;
}
function invitationModal(personId, invitation) {
  const person = state.data.employees.find((p) => p.id === +personId);
  const link = `${location.origin}/intake#${invitation.token}`;
  showModal(
    tr("An invitation for {0}", person?.name || tr("your employee")),
    tr("Copy this private link and share it directly with the employee."),
    `<div class="modal-body"><div class="alert">${tr("{0} This link opens only this person’s assessment. Keep it private.", icon("shield"))}</div><label for="invite-url">${tr("Employee assessment link")}</label><input id="invite-url" class="invite-link" readonly value="${esc(link)}"><p class="small muted">${tr("Valid until {0}. Creating another link revokes the previous one.", new Date(invitation.expires_at * 1000).toLocaleDateString(currentLocale(), { dateStyle: "medium" }))}</p><div class="button-row"><button class="button primary" data-action="copy-invite">${tr("{0}Copy link", icon("copy"))}</button><a class="button" href="${esc(link)}" target="_blank" rel="noreferrer">${tr("Open assessment {0}", icon("arrow"))}</a></div></div><div class="modal-footer"><button class="button" data-action="close-modal">${tr("Done")}</button></div>`,
  );
}
function issueInviteModal(id) {
  const person = state.data.employees.find((p) => p.id === +id);
  showModal(
    tr("Manage private invitation"),
    tr("Invitation for {0}", person.name),
    `<div class="modal-body"><p class="small muted">${tr("Create a fresh private link to share. The previous link will stop working immediately. Saved answers are preserved.")}</p><div class="alert info">${person.invite_expires ? tr("Current link {0} on {1}.", person.invite_expires * 1000 > Date.now() ? tr("expires") : tr("expired"), new Date(person.invite_expires * 1000).toLocaleDateString(currentLocale())) : tr("No active invitation.")}</div>${modalError}</div><div class="modal-footer">${person.invite_expires ? `<button class="button danger" data-action="revoke-invite" data-id="${id}">${tr("Revoke access")}</button>` : ""}<button class="button primary" data-action="confirm-invite" data-id="${id}">${tr("{0}Create new link", icon("link"))}</button></div>`,
  );
}
const frequencyFactors = { day: 5, week: 1, month: 12 / 52, year: 1 / 52 };
function workflowFrequency(w) {
  return {
    count: w.frequency_count ?? w.runs_per_week,
    unit: w.frequency_unit || "week",
  };
}
function frequencyLabel(w) {
  const { count, unit } = workflowFrequency(w);
  return tr("{0} {1} per {2}", formatNumber(count), tr(count === 1 ? "time" : "times"), tr(unit === "day" ? "workday" : unit));
}
function frequencyControl(w, i) {
  const { count, unit } = workflowFrequency(w);
  return `<fieldset class="field frequency-field"><legend>${tr("How often do you do this?")}</legend><div class="frequency-control"><label class="screen-reader" for="wf-${i}-frequency">${tr("Number of times")}</label><input id="wf-${i}-frequency" type="number" data-frequency="count" data-w="${i}" value="${count}" min="0.01" max="${1000 / frequencyFactors[unit]}" step="any" inputmode="decimal" required><label class="screen-reader" for="wf-${i}-period">${tr("Frequency period")}</label><select id="wf-${i}-period" data-frequency="unit" data-w="${i}">${Object.keys(
    frequencyFactors,
  )
    .map(
      (value) =>
        `<option value="${value}" ${value === unit ? "selected" : ""}>${tr("per {0}", tr(value === "day" ? "workday" : value))}</option>`,
    )
    .join(
      "",
    )}</select></div><p class="field-hint">${tr("Use your typical schedule. A workday assumes 5 days a week.")}</p></fieldset>`;
}
function workflowSummary(w) {
  return `<div class="workflow-summary"><h3>${esc(w.name || tr("Untitled workflow"))}</h3><p>${tr("{0} · {1} min / run", esc(frequencyLabel(w)), formatNumber(w.steps.reduce((n, s) => n + Number(s.minutes || 0), 0)))}</p>${w.trigger ? `<p><strong>${tr("Starts when:")}</strong> ${esc(w.trigger)}</p>` : ""}<div class="flow-line">${w.steps.map((s, i) => `${i ? icon("arrow") : ""}<span class="flow-node">${i + 1}. ${esc(s.action || tr("Untitled step"))}</span>`).join("")}</div>${w.outcome ? `<p><strong>${tr("Outcome:")}</strong> ${esc(w.outcome)}</p>` : ""}${w.pain_points ? `<p><strong>${tr("Friction:")}</strong> ${esc(w.pain_points)}</p>` : ""}</div>`;
}
function agentDetail(id) {
  const o = state.data.opportunities.find((o) => o.id === +id);
  showModal(
    opportunityName(o),
    `${o.entity_name} / ${o.team_name}`,
    `<div class="modal-body"><div class="button-row"><span class="tag green">${tr("{0} priority", tr(o.priority))}</span><span class="tag outline">${tr("{0} supported", plural(o.people.length, "employee"))}</span></div><p class="agent-impact">${tr("Potential time back:")} <strong>${tr("~{0}h / week", formatNumber(o.estimated_hours, 1))}</strong></p><p class="small muted">${tr("Current workflow effort: {0}h / week. {1}", formatNumber(o.weekly_hours, 1), esc(tr(o.rationale)))}</p><hr class="divider"><h3>${tr("What this agent could help with")}</h3><ul class="detail-list">${o.actions.map((a) => `<li>${esc(a)}</li>`).join("")}</ul><h3>${tr("Tools to connect")}</h3><div class="tool-chips">${o.tools.map((t) => `<span class="tool-chip">${esc(t)}</span>`).join("") || `<span class="muted small">${tr("To explore with the team")}</span>`}</div><div class="alert ${o.human_review ? "info" : ""}">${icon("shield")} ${o.human_review ? tr("Human review is part of the source workflow. Preserve it in the pilot.") : tr("Start with a human-reviewed pilot before allowing independent actions.")}</div><h3>${tr("Supporting workflows")}</h3>${o.evidence.map((w) => `<div class="review-title">${tr("Shared by {0}", esc(w.employee))}</div>${workflowSummary(w)}`).join("")}<p class="readonly-note">${tr("Estimate = run frequency × step minutes × assistance factor. Assisted and human-review steps: 50%. Automated steps: 70%. Human-only steps: 0%. Equal workflow names in the same team are grouped. Validate access, integration availability, and quality with the team.")}</p></div><div class="modal-footer"><button class="button primary" data-action="close-modal">${tr("Done")}</button></div>`,
  );
}
async function viewAssessment(id) {
  const p = state.data.employees.find((p) => p.id === +id);
  const a = await api(`/api/admin/employees/${id}/assessment`);
  showModal(
    tr("{0}’s workflows", p.name),
    `${p.entity_name} / ${p.team_name}`,
    `<div class="modal-body">${statusTag(a.status)}<div class="tool-chips">${a.tools.map((t) => `<span class="tool-chip">${esc(t)}</span>`).join("")}</div>${a.workflows.map(workflowSummary).join("") || `<p class="muted small">${tr("No workflows saved yet.")}</p>`}${a.notes ? `<h3>${tr("Additional context")}</h3><p class="small muted">${esc(a.notes)}</p>` : ""}<p class="readonly-note">${tr("Last saved {0}", new Date(a.updated_at * 1000).toLocaleString(currentLocale()))}</p></div><div class="modal-footer"><button class="button" data-action="close-modal">${tr("Close")}</button></div>`,
  );
}
function exportOpportunities() {
  const { opportunities } = filterData();
  if (!opportunities.length) {
    toast(tr("There are no opportunities to export yet."));
    return;
  }
  const rows = [
    [
      tr("Suggested agent"),
      tr("Entity"),
      tr("Team"),
      tr("Priority"),
      tr("Potential hours / week"),
      tr("Employees"),
      tr("Tools"),
      tr("Human review"),
      tr("Suggested actions"),
    ],
    ...opportunities.map((o) => [
      opportunityName(o),
      o.entity_name,
      o.team_name,
      tr(o.priority),
      o.estimated_hours,
      o.people.join("; "),
      o.tools.join("; "),
      o.human_review ? tr("Yes") : tr("Pilot recommended"),
      o.actions.join("; "),
    ]),
  ];
  const csv = rows
    .map((r) =>
      r
        .map(
          (v) =>
            `"${String(v)
              .replace(/^[=+@\-\t\r]/, "'$&")
              .replace(/"/g, '""')}"`,
        )
        .join(","),
    )
    .join("\r\n");
  const url = URL.createObjectURL(
    new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "agent-atlas-opportunities.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(tr("Opportunities exported. Estimates are planning assumptions."));
}
function renderLogin() {
  state.screen = "login";
  app.innerHTML = `<main class="login-shell"><section class="login-story">${brand()}<div><div class="eyebrow">${tr("A clearer path from work to agents.")}</div><h1>${tr("Every workflow.")}<br>${tr("A new")} <span>${tr("possibility.")}</span></h1><p>${tr("Connect everyday workflows to a practical roadmap for agents that help your teams thrive.")}</p></div><footer>${tr("MAP THE WORK. FIND THE OPPORTUNITY.")}</footer></section><section class="login-form-side"><div class="login-card"><div class="login-language">${languagePicker()}</div><h2>${tr("Welcome back.")}</h2><p>${tr("Your next agent starts with a better understanding of the work.")}</p><form id="login-form"><div id="login-error" class="alert error" role="alert" hidden></div><div class="field"><label for="password">${tr("Workspace password")}</label><input id="password" name="password" type="password" autocomplete="current-password" placeholder="${tr("Enter your admin password")}" required><p class="field-hint">${tr("Use the workspace password provided by your administrator.")}</p></div><button class="button primary" type="submit">${tr("Open workspace {0}", icon("arrow"))}</button></form><footer>${tr("{0} Your company’s workflows stay in your own workspace.", icon("shield"))}<br>${tr("Have an employee invitation? Open your private assessment link.")}</footer></div></section></main>`;
}
async function loadWorkspace() {
  state.data = await api("/api/admin/workspace");
}
async function refresh() {
  await loadWorkspace();
  renderShell();
}
function intakeHeader() {
  return `<header class="intake-top">${brand()}<div class="intake-header-actions">${languagePicker()}<span class="tag outline">${tr("{0}Your private assessment", icon("shield"))}</span></div></header>`;
}
function renderIntake() {
  state.screen = "intake";
  const p = state.intake.employee;
  app.innerHTML = `${intakeHeader()}<main class="intake-container"><div class="intake-intro"><div class="eyebrow">${tr("Your work. Your perspective.")}</div><h1>${tr("Help shape a better workday, {0}.", esc(p.name.split(" ")[0]))}</h1><p>${tr("Share the tools you use and the tasks you repeat. Together, we’ll find where helpful agents could give your team time back.")}</p><div class="employee-context"><span class="tag outline">${icon("people")}${esc(p.name)}</span><span class="tag outline">${esc(p.entity_name)} / ${esc(p.team_name)}</span><span class="tag outline">${esc(p.role)}</span></div></div><div class="wizard-progress" aria-label="${tr("Assessment progress")}">${[tr("Your tools"), tr("Your workflows"), tr("Review & share")].map((l, i) => `${i ? `<div class="wizard-line"></div>` : ""}<div class="wizard-stop ${i === state.stage ? "active" : i < state.stage ? "done" : ""}" ${i === state.stage ? 'aria-current="step"' : ""}><span>${i < state.stage ? icon("check") : i + 1}</span>${l}</div>`).join("")}</div><form id="intake-form"><div id="intake-errors" class="alert error" role="alert" hidden></div><div id="intake-stage"></div></form></main>`;
  renderIntakeStage();
}
function renderIntakeStage() {
  const a = state.intake.assessment;
  if (state.stage === 0) {
    $("#intake-stage").innerHTML =
      `<section class="panel intake-panel"><h2>${tr("Which tools are part of your workday?")}</h2><p>${tr("Select everything you use regularly. You can add a tool if it isn’t listed.")}</p><div class="selected-tools" id="selected-tools"></div><div class="search"><label class="screen-reader" for="tool-search">${tr("Search digital tools")}</label>${icon("search")}<input id="tool-search" placeholder="${tr("Find a tool…")}" type="search"></div><div id="tool-options"></div><div class="custom-tool"><label class="screen-reader" for="custom-tool">${tr("Custom digital tool")}</label><input id="custom-tool" placeholder="${tr("Another tool you use…")}" maxlength="160"><button type="button" class="button" data-action="add-tool">${tr("{0}Add tool", icon("plus"))}</button></div></section>${wizardFooter()}`;
    renderToolOptions();
  } else if (state.stage === 1) {
    $("#intake-stage").innerHTML =
      `<div class="panel intake-panel"><h2>${tr("Walk us through your repeatable work.")}</h2><p>${tr("Think of a task you do regularly: preparing a report, processing a request, or following up with a customer. Describe it as a simple sequence of steps.")}</p><div class="alert info">${tr("{0} Use everyday language. Share the process, and keep passwords, customer records, and other sensitive details out of your examples.", icon("info"))}</div></div>${a.workflows.map(workflowEditor).join("")}<button type="button" class="button add-workflow" data-action="add-workflow">${icon("plus")}${a.workflows.length ? tr("Add another workflow") : tr("Describe your first workflow")}</button>${wizardFooter()}`;
  } else {
    $("#intake-stage").innerHTML =
      `<section class="panel intake-panel"><h2>${tr("A little context. A lot of possibility.")}</h2><p>${tr("Review what you’ve shared. Your team will use this to explore helpful agents and choose practical pilots.")}</p><div class="review-title"><strong>${tr("Your digital tools")}</strong><button type="button" class="text-link" data-action="go-tools">${tr("Edit {0}", icon("edit"))}</button></div><div class="tool-chips">${a.tools.map((t) => `<span class="tool-chip">${esc(t)}</span>`).join("") || `<span class="muted small">${tr("No tools selected")}</span>`}</div><div class="review-title"><strong>${plural(a.workflows.length, "workflow")}</strong><button type="button" class="text-link" data-action="go-workflows">${tr("Edit {0}", icon("edit"))}</button></div>${a.workflows.map(workflowSummary).join("") || `<p class="small muted">${tr("Add at least one workflow before submitting.")}</p>`}<div class="field"><label for="assessment-notes">${tr("Anything else you’d like your team to know?")} <span class="muted">${tr("(optional)")}</span></label><textarea id="assessment-notes" data-field="notes" maxlength="2000" placeholder="${tr("What would make the biggest difference in your day?")}">${esc(a.notes)}</textarea></div><div class="alert">${tr("{0} Your workspace administrator can see your answers. You can return using this link to update them.", icon("shield"))}</div></section>${wizardFooter()}`;
  }
}
function renderToolOptions(search = "") {
  const a = state.intake.assessment;
  const catalog = [...state.intake.catalog];
  const known = new Set(catalog.map((t) => t.name.toLowerCase()));
  a.tools
    .filter((t) => !known.has(t.toLowerCase()))
    .forEach((t) => catalog.push({ name: t, category: tr("Your other tools") }));
  const filtered = catalog.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()),
  );
  $("#selected-tools").innerHTML =
    `<span class="tag green">${tr("{0} selected", a.tools.length)}</span>${a.tools
      .slice(0, 7)
      .map((t) => `<span class="tag">${esc(t)}</span>`)
      .join(
        "",
      )}${a.tools.length > 7 ? `<span class="tag">+${a.tools.length - 7}</span>` : ""}`;
  $("#tool-options").innerHTML = filtered.length
    ? [...new Set(filtered.map((t) => t.category))]
        .map(
          (g) =>
            `<div class="tool-category">${esc(categoryLabel(g))}</div><div class="tools-grid">${filtered
              .filter((t) => t.category === g)
              .map(
                (t) =>
                  `<label class="tool-check ${a.tools.includes(t.name) ? "selected" : ""}"><input type="checkbox" data-tool="${esc(t.name)}" ${a.tools.includes(t.name) ? "checked" : ""}><span>${esc(t.name)}</span></label>`,
              )
              .join("")}</div>`,
        )
        .join("")
    : `<p class="search-count">${tr("No matching tool. Add your own below.")}</p>`;
}
function workflowEditor(w, i) {
  const field = (key) => `workflows.${i}.${key}`;
  return `<section class="workflow-editor"><div class="workflow-title-row"><span class="workflow-number">${tr("WORKFLOW {0}", String(i + 1).padStart(2, "0"))}</span><strong data-workflow-title="${i}">${esc(w.name || tr("Your everyday process"))}</strong><span data-workflow-saved="${i}">${workflowSaveBadge(w)}</span><button class="icon-button" type="button" data-action="remove-workflow" data-w="${i}" aria-label="${tr("Remove workflow {0}", i + 1)}" title="${tr("Remove workflow")}">${icon("trash")}</button></div><div class="workflow-body"><div class="form-grid"><div class="field"><label for="wf-${i}-name">${tr("Workflow name")}</label><input id="wf-${i}-name" data-field="${field("name")}" value="${esc(w.name)}" placeholder="${tr("e.g. Prepare the weekly sales report")}" maxlength="160" required></div>${frequencyControl(w, i)}<div class="field"><label for="wf-${i}-trigger">${tr("What starts this workflow?")}</label><input id="wf-${i}-trigger" data-field="${field("trigger")}" value="${esc(w.trigger)}" maxlength="2000" placeholder="${tr("e.g. Every Monday morning")}"></div><div class="field"><label for="wf-${i}-outcome">${tr("What is the end result?")}</label><input id="wf-${i}-outcome" data-field="${field("outcome")}" value="${esc(w.outcome)}" maxlength="2000" placeholder="${tr("e.g. Report shared with the team")}"></div></div><div id="workflow-steps-${i}">${workflowSteps(w, i)}</div><button class="button small" type="button" data-action="add-step" data-w="${i}">${tr("{0}Add a step", icon("plus"))}</button><div class="field"><label for="wf-${i}-pain">${tr("Where does this workflow get frustrating?")} <span class="muted">${tr("(optional)")}</span></label><textarea id="wf-${i}-pain" data-field="${field("pain_points")}" maxlength="2000" placeholder="${tr("e.g. Copying information between systems takes a lot of time.")}">${esc(w.pain_points)}</textarea></div><div class="button-row workflow-save-row"><button class="button small" type="button" data-action="save-workflow" data-w="${i}">${tr("{0}Save workflow {1}", icon("check"), i + 1)}</button></div></div></section>`;
}
function stepEditor(s, i, j, count, connector = true) {
  const field = (k) => `workflows.${i}.steps.${j}.${k}`;
  return `${connector && j ? `<div class="workflow-connector">${icon("down")}</div>` : ""}<div class="step-card"><div class="step-card-header"><span class="step-number">${j + 1}</span><strong>${tr("Step {0}", j + 1)}</strong><button type="button" class="icon-button" data-action="move-up" data-w="${i}" data-s="${j}" ${j === 0 ? "disabled" : ""} aria-label="${tr("Move step {0} up", j + 1)}">${icon("up")}</button><button type="button" class="icon-button" data-action="move-down" data-w="${i}" data-s="${j}" ${j === count - 1 ? "disabled" : ""} aria-label="${tr("Move step {0} down", j + 1)}">${icon("down")}</button><button type="button" class="icon-button" data-action="remove-step" data-w="${i}" data-s="${j}" ${count === 1 ? "disabled" : ""} aria-label="${tr("Remove step {0}", j + 1)}">${icon("trash")}</button></div><div class="field"><label for="s-${i}-${j}-action">${tr("What do you do?")}</label><input id="s-${i}-${j}-action" data-field="${field("action")}" value="${esc(s.action)}" placeholder="${tr("e.g. Export this week’s sales from the CRM")}" maxlength="160" required></div><div class="step-fields"><div class="field"><label for="s-${i}-${j}-tool">${tr("Tool used")}</label><select id="s-${i}-${j}-tool" data-field="${field("tool")}"><option value="">${tr("No digital tool")}</option>${state.intake.assessment.tools.map((t) => `<option ${t === s.tool ? "selected" : ""} value="${esc(t)}">${esc(t)}</option>`).join("")}</select></div><div class="field"><label for="s-${i}-${j}-time">${tr("Minutes / run")}</label><input id="s-${i}-${j}-time" data-field="${field("minutes")}" type="number" min="0" max="10080" step="any" value="${s.minutes}" required></div><div class="field"><label for="s-${i}-${j}-support">${tr("How could an agent help?")}</label><select id="s-${i}-${j}-support" data-field="${field("support")}">${[
    ["assist", tr("Help me do it")],
    ["automate", tr("Do it for me")],
    ["manual", tr("Human only")],
  ]
    .map(
      ([v, l]) =>
        `<option value="${v}" ${s.support === v ? "selected" : ""}>${l}</option>`,
    )
    .join(
      "",
    )}</select></div></div><label class="checkbox-label"><input type="checkbox" data-field="${field("human_review")}" ${s.human_review ? "checked" : ""}>${tr("A person must review or approve this step")}</label></div>`;
}
function workflowSteps(w, i) {
  const view = workflowView(w);
  view.selected = Math.max(0, Math.min(view.selected, w.steps.length - 1));
  return `<div class="workflow-steps-toolbar"><div class="step-label">${tr("THE STEPS, IN ORDER")}</div><div class="workflow-view-switch" role="group" aria-label="${tr("Workflow {0} view", i + 1)}">${["text", "diagram"].map((mode) => `<button type="button" class="workflow-view-button" data-action="workflow-view" data-mode="${mode}" data-w="${i}" aria-pressed="${view.mode === mode}" aria-controls="workflow-step-content-${i}">${icon(mode)}${mode === "text" ? tr("Text") : tr("Diagram")}</button>`).join("")}</div></div><div id="workflow-step-content-${i}">${view.mode === "diagram" ? workflowDiagram(w, i, view.selected) : w.steps.map((step, j) => stepEditor(step, i, j, w.steps.length)).join("")}</div>`;
}
function stepSupportLabel(step) {
  if (!step.action.trim()) return tr("Needs description");
  return step.support === "manual"
    ? tr("Human only")
    : step.support === "automate"
      ? tr("Automated")
      : tr("Assisted");
}
function workflowDiagram(w, i, selected) {
  const described = w.steps.filter((step) => step.action.trim()).length;
  return `<div class="diagram-map-heading"><p class="diagram-hint">${tr("Select a step to edit its details.")}</p><span class="tag" data-workflow-completion>${tr("{0} of {1} described", described, w.steps.length)}</span></div><div class="workflow-diagram-layout"><div class="workflow-diagram" role="group" aria-label="${tr("Workflow {0} diagram", i + 1)}"><div class="diagram-terminal"><span class="diagram-terminal-dot"></span><div><strong>${tr("Start")}</strong><span data-diagram-trigger>${esc(w.trigger || tr("Workflow begins"))}</span></div></div><ol class="diagram-sequence">${w.steps.map((step, j) => `<li><span class="diagram-arrow">${icon("down")}</span><button type="button" class="diagram-node ${step.action.trim() ? "" : "is-incomplete"}" data-action="select-step" data-w="${i}" data-s="${j}" data-step-node="${j}" data-support="${esc(step.support)}" aria-pressed="${j === selected}" aria-label="${tr("Edit step {0}: {1}", j + 1, esc(step.action.trim() || tr("Needs description")))}"><span class="diagram-node-header"><span class="step-number">${j + 1}</span><span data-node-support>${stepSupportLabel(step)}</span><span data-node-review ${step.human_review ? "" : "hidden"} title="${tr("Human review required")}">${icon("shield")}</span></span><strong data-node-action>${esc(step.action.trim() || tr("Describe this step"))}</strong><span class="diagram-node-meta" ${step.action.trim() ? "" : "hidden"}><span data-node-tool>${esc(step.tool || tr("No digital tool"))}</span><span data-node-minutes>${tr("{0} min", step.minutes == null ? "—" : formatNumber(step.minutes))}</span></span></button></li>`).join("")}</ol><span class="diagram-arrow">${icon("down")}</span><button type="button" class="diagram-add" data-action="add-step" data-w="${i}" aria-label="${tr("Add a diagram step")}">${tr("{0}Add step", icon("plus"))}</button><span class="diagram-arrow">${icon("down")}</span><div class="diagram-terminal end"><span class="diagram-terminal-dot">${icon("check")}</span><div><strong>${tr("Done")}</strong><span data-diagram-outcome>${esc(w.outcome || tr("Workflow complete"))}</span></div></div></div>${w.steps[selected] ? `<section class="diagram-inspector" aria-label="${tr("Selected step details")}"><div class="diagram-inspector-heading"><h3>${tr("Step details")}</h3><span>${tr("Step {0} of {1}", selected + 1, w.steps.length)}</span></div>${stepEditor(w.steps[selected], i, selected, w.steps.length, false)}</section>` : ""}</div>`;
}
function renderWorkflowSteps(i) {
  const region = $(`#workflow-steps-${i}`);
  const scroll = $(".workflow-diagram", region)?.scrollTop || 0;
  region.innerHTML = workflowSteps(state.intake.assessment.workflows[i], i);
  const diagram = $(".workflow-diagram", region);
  if (diagram) diagram.scrollTop = scroll;
}
function revealDiagramStep(i) {
  const selected = $(`#workflow-steps-${i} .diagram-node[aria-pressed="true"]`);
  if (selected)
    selected.scrollIntoView({ block: "nearest", inline: "nearest" });
  return selected;
}
function updateDiagramPreview(i) {
  const w = state.intake.assessment.workflows[i];
  const region = $(`#workflow-steps-${i}`);
  const diagram = $(".workflow-diagram", region);
  if (!diagram) return;
  $("[data-diagram-trigger]", diagram).textContent =
    w.trigger || tr("Workflow begins");
  $("[data-diagram-outcome]", diagram).textContent =
    w.outcome || tr("Workflow complete");
  $("[data-workflow-completion]", region).textContent =
    tr("{0} of {1} described", w.steps.filter((step) => step.action.trim()).length, w.steps.length);
  diagram.querySelectorAll("[data-step-node]").forEach((node) => {
    const j = +node.dataset.stepNode;
    const step = w.steps[j];
    const complete = !!step.action.trim();
    node.dataset.support = step.support;
    $("[data-node-action]", node).textContent =
      step.action.trim() || tr("Describe this step");
    $("[data-node-tool]", node).textContent = step.tool || tr("No digital tool");
    $("[data-node-minutes]", node).textContent = tr("{0} min", step.minutes == null ? "—" : formatNumber(step.minutes));
    $("[data-node-support]", node).textContent = stepSupportLabel(step);
    $("[data-node-review]", node).hidden = !step.human_review;
    $(".diagram-node-meta", node).hidden = !complete;
    node.classList.toggle("is-incomplete", !complete);
    node.setAttribute(
      "aria-label",
      tr("Edit step {0}: {1}", j + 1, step.action.trim() || tr("Needs description")),
    );
  });
}
// Drafts may leave step descriptions empty, but numbers must be valid to save.
function validateWorkflowSteps(
  indexes = state.intake.assessment.workflows.keys(),
  draft = false,
) {
  for (const i of indexes) {
    const workflow = state.intake.assessment.workflows[i];
    if (!workflow.steps.length)
      throw new Error(tr("Add at least one step to workflow {0}.", i + 1));
    if (!$(`#wf-${i}-frequency`).reportValidity()) return false;
    for (const [j, step] of workflow.steps.entries()) {
      const field = !draft && !step.action.trim()
        ? "action"
        : !Number.isFinite(step.minutes) ||
            step.minutes < 0 ||
            step.minutes > 10080
          ? "time"
          : null;
      if (!field) continue;
      workflowView(workflow).selected = j;
      renderWorkflowSteps(i);
      revealDiagramStep(i);
      const input = $(`#s-${i}-${j}-${field}`);
      input.setCustomValidity(
        field === "action"
          ? tr("Describe what you do in this step.")
          : tr("Enter minutes between 0 and 10080."),
      );
      input.scrollIntoView({ block: "center" });
      input.focus({ preventScroll: true });
      input.reportValidity();
      return false;
    }
  }
  return true;
}
function wizardFooter() {
  return `<div class="wizard-footer"><button type="button" class="button" data-action="${state.stage ? "back-stage" : "save-draft"}">${state.stage ? tr("Back") : tr("Save draft")}</button><span class="save-note" id="save-status">${esc(saveNote())}</span><div class="button-row">${state.stage ? `<button type="button" class="button" data-action="save-draft">${tr("Save draft")}</button>` : ""}<button type="submit" class="button primary">${state.stage === 2 ? tr("Share my assessment") : tr("Save & continue")}${icon("arrow")}</button></div></div>`;
}
function newStep() {
  return {
    action: "",
    details: "",
    tool: "",
    minutes: 5,
    support: "assist",
    human_review: false,
  };
}
// With a target workflow, everything else is sent as last saved, so other unsaved edits stay unsaved.
async function saveIntake(status = "draft", target = null, remove = false) {
  if (state.saving)
    throw new Error(tr("Your assessment is still saving. Please wait a moment."));
  const a = state.intake.assessment;
  const body = target
    ? {
        ...JSON.parse(state.savedRest),
        workflows: a.workflows
          .filter((w) => (w === target ? !remove : savedWorkflows.has(w)))
          .map((w) => (w === target ? w : JSON.parse(savedWorkflows.get(w)))),
        status,
        revision: a.revision,
      }
    : { ...a, status };
  const form = $("#intake-form");
  state.saving = true;
  if (form) {
    form.inert = true;
    form.setAttribute("aria-busy", "true");
  }
  const note = $("#save-status");
  if (note) note.textContent = tr("Saving your progress…");
  try {
    const result = await api("/api/intake", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    a.revision = result.revision;
    a.status = result.status;
    state.savedAt = result.updated_at;
    if (!target) rememberSaved();
    else if (remove) savedWorkflows.delete(target);
    else savedWorkflows.set(target, JSON.stringify(target));
    $("#intake-errors")?.setAttribute("hidden", "");
  } finally {
    state.saving = false;
    if (form) {
      form.inert = false;
      form.removeAttribute("aria-busy");
    }
    showSaveStatus();
  }
}
function renderSuccess() {
  state.screen = "success";
  const p = state.intake.employee;
  app.innerHTML = `${intakeHeader()}<main class="intake-container"><section class="success-panel"><span class="success-icon">${icon("check")}</span><div class="eyebrow">${tr("Your perspective makes a difference")}</div><h1>${tr("Thanks for sharing your work, {0}.", esc(p.name.split(" ")[0]))}</h1><p>${tr("Your assessment is ready for your team. Your workflows will help identify practical agent opportunities for {0} and {1}.", esc(p.entity_name), esc(p.team_name))}</p><div class="button-row"><button class="button primary" data-action="edit-assessment">${tr("Review or update my answers {0}", icon("arrow"))}</button></div><p class="small muted">${tr("You can return using your private link while it remains valid.")}</p></section></main>`;
}
function intakeError(error) {
  const node = $("#intake-errors");
  if (node) {
    node.textContent = error.message;
    node.hidden = false;
    node.scrollIntoView({ block: "center", behavior: "smooth" });
  } else toast(error.message, true);
}

// Single event boundary keeps the interface functional as views are replaced.
document.addEventListener("click", async (event) => {
  if (event.target.closest(".skip-link")) {
    event.preventDefault();
    $("#content").focus();
    return;
  }
  if (event.target.closest(".nav a")) {
    $("#sidebar")?.classList.remove("mobile-open");
    $('[aria-controls="sidebar"]')?.setAttribute("aria-expanded", "false");
  }
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const id = button.dataset.id;
  const i = +button.dataset.w;
  const j = +button.dataset.s;
  try {
    if (action === "close-modal") {
      modal.close();
      return;
    }
    if (action === "reload") {
      location.reload();
      return;
    }
    if (action === "refresh") {
      button.disabled = true;
      await refresh();
      toast(tr("Workspace updated."));
      return;
    }
    if (action === "menu") {
      const open = $("#sidebar").classList.toggle("mobile-open");
      button.setAttribute("aria-expanded", String(open));
      return;
    }
    if (action === "logout") {
      await post("/api/logout");
      state.data = null;
      renderLogin();
      return;
    }
    if (action === "add-entity") {
      entityModal();
      return;
    }
    if (action === "add-team") {
      teamModal(id);
      return;
    }
    if (action === "edit-entity") {
      entityModal(id);
      return;
    }
    if (action === "new-tool" || action === "edit-tool") {
      toolModal(id, button.dataset.name);
      return;
    }
    if (action === "edit-team") {
      teamModal("", id);
      return;
    }
    if (action === "collaborator") {
      collaboratorModal(id);
      return;
    }
    if (action === "collaborator-link") {
      const collaborator = state.data.collaborators.find((c) => c.id === +id);
      if (!confirm(tr("Create a new sign-in link for {0}? The previous link stops working.", collaborator.name))) return;
      button.disabled = true;
      collaboratorLinkModal(collaborator.name, await post(`/api/admin/collaborators/${id}/invite`));
      return;
    }
    if (action === "delete") {
      if (!confirm(button.dataset.confirm)) return;
      button.disabled = true;
      await api(button.dataset.path, { method: "DELETE" });
      if (modal.open) modal.close();
      // A deleted entity or team must not stay selected as a filter.
      state.entity = state.team = "";
      await refresh();
      toast(tr("Deleted from your workspace."));
      return;
    }
    if (action === "add-person") {
      personModal();
      return;
    }
    if (action === "edit-person") {
      personModal(id);
      return;
    }
    if (action === "issue-invite") {
      issueInviteModal(id);
      return;
    }
    if (action === "confirm-invite") {
      button.disabled = true;
      const invite = await post(`/api/admin/employees/${id}/invite`);
      await refresh();
      invitationModal(id, invite);
      return;
    }
    if (action === "revoke-invite") {
      button.disabled = true;
      await api(`/api/admin/employees/${id}/invite`, { method: "DELETE" });
      modal.close();
      await refresh();
      toast(tr("Invitation revoked. Saved answers preserved."));
      return;
    }
    if (action === "copy-invite") {
      const input = $("#invite-url");
      input.select();
      try {
        if (!navigator.clipboard) throw new Error();
        await navigator.clipboard.writeText(input.value);
        toast(tr("Private invitation link copied."));
      } catch {
        toast(tr("Link selected. Use your device’s Copy command."));
      }
      return;
    }
    if (action === "agent-detail") {
      agentDetail(id);
      return;
    }
    if (action === "view-assessment") {
      button.disabled = true;
      await viewAssessment(id);
      return;
    }
    if (action === "export") {
      exportOpportunities();
      return;
    }
    if (!state.intake) return;
    if (action === "add-tool") {
      const input = $("#custom-tool");
      const t = input.value.trim();
      if (!t) return;
      const existing = [
        ...state.intake.catalog.map((t) => t.name),
        ...state.intake.assessment.tools,
      ].find((n) => n.toLowerCase() === t.toLowerCase());
      if (!state.intake.assessment.tools.includes(existing || t))
        state.intake.assessment.tools.push(existing || t);
      input.value = "";
      showSaveStatus();
      renderToolOptions($("#tool-search").value);
      return;
    }
    if (action === "save-draft") {
      button.disabled = true;
      await saveIntake("draft");
      toast(tr("Your draft is saved. You can return using this private link."));
      return;
    }
    if (action === "edit-assessment") {
      state.stage = 2;
      renderIntake();
      return;
    }
    if (action === "back-stage") {
      state.stage--;
      renderIntake();
      window.scrollTo(0, 0);
      return;
    }
    if (action === "go-tools" || action === "go-workflows") {
      state.stage = action === "go-tools" ? 0 : 1;
      renderIntake();
      window.scrollTo(0, 0);
      return;
    }
    const workflows = state.intake.assessment.workflows;
    if (action === "save-workflow") {
      if (!validateWorkflowSteps([i], true)) return;
      button.disabled = true;
      await saveIntake("draft", workflows[i]);
      toast(tr("{0} is saved.", workflows[i].name.trim() || tr("Workflow {0}", i + 1)));
      return;
    }
    if (action === "workflow-view" || action === "select-step") {
      const view = workflowView(workflows[i]);
      if (action === "workflow-view") view.mode = button.dataset.mode;
      else view.selected = j;
      renderWorkflowSteps(i);
      revealDiagramStep(i);
      const next =
        action === "workflow-view"
          ? $(`#workflow-steps-${i} [data-mode="${view.mode}"]`)
          : $(`#workflow-steps-${i} [data-step-node="${j}"]`);
      next.focus({ preventScroll: true });
      if (action === "select-step")
        $(`#s-${i}-${j}-action`).scrollIntoView({ block: "nearest" });
      return;
    }
    if (action === "add-workflow") {
      if (workflows.length >= 30) {
        toast(tr("You can share up to 30 workflows."), true);
        return;
      }
      workflows.push({
        name: "",
        trigger: "",
        outcome: "",
        runs_per_week: 1,
        frequency_count: 1,
        frequency_unit: "week",
        pain_points: "",
        steps: [newStep()],
      });
    } else if (action === "remove-workflow") {
      if (!confirm(tr("Remove this workflow from your assessment?"))) return;
      // A saved workflow is deleted right away so it cannot reappear on the next visit.
      if (savedWorkflows.has(workflows[i]))
        await saveIntake("draft", workflows[i], true);
      workflows.splice(i, 1);
    } else if (action === "add-step") {
      if (workflows[i].steps.length >= 50) {
        toast(tr("You can add up to 50 steps per workflow."), true);
        return;
      }
      workflows[i].steps.push(newStep());
      workflowView(workflows[i]).selected = workflows[i].steps.length - 1;
    } else if (action === "remove-step") {
      if (workflows[i].steps.length > 1) {
        workflows[i].steps.splice(j, 1);
        workflowView(workflows[i]).selected = Math.min(
          j,
          workflows[i].steps.length - 1,
        );
      }
    } else if (action === "move-up" || action === "move-down") {
      const next = j + (action === "move-up" ? -1 : 1);
      if (next < 0 || next >= workflows[i].steps.length) return;
      [workflows[i].steps[j], workflows[i].steps[next]] = [
        workflows[i].steps[next],
        workflows[i].steps[j],
      ];
      workflowView(workflows[i]).selected = next;
    } else return;
    showSaveStatus();
    if (["add-step", "remove-step", "move-up", "move-down"].includes(action)) {
      renderWorkflowSteps(i);
      const selected = revealDiagramStep(i);
      if (action === "add-step")
        $(`#s-${i}-${workflows[i].steps.length - 1}-action`).focus();
      else selected?.focus({ preventScroll: true });
    } else renderIntakeStage();
  } catch (error) {
    if (state.intake) intakeError(error);
    else {
      // A closed dialog keeps its markup; an error placed there would be invisible.
      const e = modal.open && $("#modal-error");
      if (e) {
        e.textContent = error.message;
        e.hidden = false;
      } else toast(error.message, true);
    }
  } finally {
    if (button.isConnected) button.disabled = false;
  }
});
document.addEventListener("keydown", (event) => {
  const node = event.target.closest(".diagram-node");
  if (node && ["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) {
    event.preventDefault();
    const nodes = [
      ...node.closest(".workflow-diagram").querySelectorAll(".diagram-node"),
    ];
    const current = nodes.indexOf(node);
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? nodes.length - 1
          : Math.max(
              0,
              Math.min(
                nodes.length - 1,
                current + (event.key === "ArrowDown" ? 1 : -1),
              ),
            );
    nodes[next].click();
    return;
  }
  // Enter in a wizard field must not submit the stage and skip ahead.
  const input = event.target;
  if (
    event.key !== "Enter" ||
    input.tagName !== "INPUT" ||
    !input.closest("#intake-form")
  )
    return;
  event.preventDefault();
  if (input.id === "custom-tool") $('[data-action="add-tool"]').click();
});
document.addEventListener("input", (event) => {
  const input = event.target;
  if (input.id === "people-search") {
    state.search = input.value;
    const { employees } = filterData();
    $("#people-results").innerHTML = peopleTable(
      employees.filter((p) =>
        `${p.name} ${p.email} ${p.role}`
          .toLowerCase()
          .includes(state.search.toLowerCase()),
      ),
    );
    return;
  }
  if (input.id === "tool-search") {
    renderToolOptions(input.value);
    return;
  }
  if (input.dataset.frequency && state.intake) {
    const workflow = state.intake.assessment.workflows[+input.dataset.w];
    const current = workflowFrequency(workflow);
    const count =
      input.dataset.frequency === "count"
        ? input.value === ""
          ? null
          : Number(input.value)
        : current.count;
    const unit =
      input.dataset.frequency === "unit" ? input.value : current.unit;
    workflow.frequency_count = count;
    workflow.frequency_unit = unit;
    workflow.runs_per_week =
      count === null ? null : count * frequencyFactors[unit];
    $(`#wf-${input.dataset.w}-frequency`).max = 1000 / frequencyFactors[unit];
    showSaveStatus();
    return;
  }
  if (!input.dataset.field || !state.intake) return;
  input.setCustomValidity("");
  const keys = input.dataset.field.split(".");
  let target = state.intake.assessment;
  keys.slice(0, -1).forEach((k) => (target = target[k]));
  target[keys.at(-1)] =
    input.type === "checkbox"
      ? input.checked
      : input.type === "number"
        ? input.value === ""
          ? null
          : Number(input.value)
        : input.value;
  if (keys[0] === "workflows") {
    if (keys[2] === "name")
      $(`[data-workflow-title="${keys[1]}"]`).textContent =
        input.value.trim() || tr("Your everyday process");
    updateDiagramPreview(+keys[1]);
  }
  showSaveStatus();
});
document.addEventListener("change", (event) => {
  const input = event.target;
  if (input.id === "language-select") {
    changeLanguage(input.value);
    return;
  }
  if (input.id === "entity-filter") {
    state.entity = input.value;
    state.team = "";
    renderContent();
    return;
  }
  if (input.id === "team-filter") {
    state.team = input.value;
    renderContent();
    return;
  }
  if (input.id === "person-entity") {
    $("#person-team").innerHTML = teamOptions(input.value);
    return;
  }
  if (input.dataset.tool && state.intake) {
    const tools = state.intake.assessment.tools;
    const name = input.dataset.tool;
    if (input.checked && !tools.includes(name)) tools.push(name);
    if (!input.checked) {
      const used = state.intake.assessment.workflows.some((w) =>
        w.steps.some((s) => s.tool === name),
      );
      if (used) {
        input.checked = true;
        toast(
          tr("This tool is used in a workflow. Change those steps before removing it."),
          true,
        );
        return;
      }
      tools.splice(tools.indexOf(name), 1);
    }
    showSaveStatus();
    renderToolOptions($("#tool-search").value);
  }
});
document.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const submit = $('button[type="submit"]', form);
  if (submit) submit.disabled = true;
  try {
    if (form.id === "login-form") {
      await post("/api/login", {
        password: new FormData(form).get("password"),
      });
      await loadWorkspace();
      state.page = location.hash.slice(1) || "overview";
      renderShell();
      return;
    }
    if (adminForms[form.id]) {
      const [path, noun, created] = adminForms[form.id];
      const id = form.dataset.id;
      const data = new FormData(form);
      const body = Object.fromEntries(data);
      if (body.entity_id) body.entity_id = +body.entity_id;
      if (form.id === "collaborator-form") {
        body.entity_ids = data.getAll("entity_ids").map(Number);
        if (!body.entity_ids.length) throw new Error(tr("Choose at least one entity."));
      }
      const result = await api(`/api/admin/${path}${id ? `/${id}` : ""}`, {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      await refresh();
      // A new collaborator's response carries their private sign-in link.
      if (result.token) return collaboratorLinkModal(body.name, result);
      modal.close();
      toast(id ? tr("{0} updated.", tr(noun)) : tr(created));
      return;
    }
    if (form.id === "person-form") {
      const body = Object.fromEntries(new FormData(form));
      body.team_id = +body.team_id;
      if (form.dataset.id) {
        await api(`/api/admin/employees/${form.dataset.id}`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
        modal.close();
        await refresh();
        toast(tr("Employee details updated."));
      } else {
        const result = await post("/api/admin/employees", body);
        await refresh();
        invitationModal(result.id, result);
      }
      return;
    }
    if (form.id === "intake-form") {
      if (state.stage === 0 && !state.intake.assessment.tools.length)
        throw new Error(tr("Choose at least one digital tool to continue."));
      if (state.stage === 1 && !state.intake.assessment.workflows.length)
        throw new Error(tr("Describe at least one workflow to continue."));
      if (state.stage === 1 && !validateWorkflowSteps()) return;
      // A submitted record must remain a draft while the employee edits earlier steps.
      await saveIntake(state.stage === 2 ? "submitted" : "draft");
      if (state.stage === 2) {
        renderSuccess();
      } else {
        state.stage++;
        renderIntake();
      }
      window.scrollTo(0, 0);
      return;
    }
  } catch (error) {
    const node =
      form.id === "login-form"
        ? $("#login-error")
        : form.id === "intake-form"
          ? $("#intake-errors")
          : $("#modal-error");
    if (node) {
      node.textContent = error.message;
      node.hidden = false;
      node.scrollIntoView({ block: "center", behavior: "smooth" });
    } else toast(error.message, true);
  } finally {
    if (submit?.isConnected) submit.disabled = false;
  }
});
window.addEventListener("hashchange", async () => {
  // A new invitation pasted into an open intake tab only changes the hash.
  if (location.pathname === "/intake") {
    if (location.hash) location.reload();
    return;
  }
  if (!state.data) return;
  state.page = location.hash.slice(1) || "overview";
  state.search = "";
  try {
    await refresh();
    window.scrollTo(0, 0);
  } catch (error) {
    if (error.status === 401) {
      state.data = null;
      renderLogin();
    } else toast(error.message, true);
  }
});
window.addEventListener("beforeunload", (event) => {
  if (state.intake && unsavedParts().length) {
    event.preventDefault();
    event.returnValue = "";
  }
});
modal.addEventListener("click", (event) => {
  if (event.target === modal) modal.close();
});
async function start() {
  if (location.pathname === "/intake") {
    state.token =
      location.hash.slice(1) ||
      sessionStorage.getItem("atlas_invitation") ||
      "";
    if (location.hash) {
      sessionStorage.setItem("atlas_invitation", state.token);
      history.replaceState(null, "", "/intake");
    }
    try {
      state.intake = await api("/api/intake");
      rememberSaved();
      if (state.intake.assessment.status === "submitted") renderSuccess();
      else renderIntake();
    } catch (error) {
      renderStartError(error, true);
    }
  } else if (location.pathname === "/join") {
    // A collaborator's private link: exchange it for a session, then hide it from the address bar.
    const token = location.hash.slice(1);
    history.replaceState(null, "", "/");
    try {
      await post("/api/join", { token });
      await loadWorkspace();
      state.page = "overview";
      renderShell();
    } catch (error) {
      renderStartError(error, true);
    }
  } else {
    try {
      await loadWorkspace();
      state.page = location.hash.slice(1) || "overview";
      renderShell();
    } catch (error) {
      if (error.status === 401) renderLogin();
      else renderStartError(error);
    }
  }
}
start();
