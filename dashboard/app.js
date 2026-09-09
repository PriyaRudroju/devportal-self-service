const DATA = {
  user: "Vishwak Sena Priya",
  teams: { "Platform-Team": "u-priya", "Application-Team": "u-alex" },
  ec2: [
    { name: "idp-demo-bastion", env: "dev", status: "completed", team: "Platform-Team" },
    { name: "claims-worker-qa", env: "qa", status: "pending", team: "Application-Team" },
    { name: "patient-cache-dev", env: "dev", status: "in_progress", team: "Application-Team" },
    { name: "analytics-scratch", env: "dev", status: "failed", team: "Application-Team" },
    { name: "tfc-runner-prod", env: "prod", status: "completed", team: "Platform-Team" },
  ],
  runs: [
    { name: "change-ec2-instance.yml #1024", conclusion: "success", env: "dev", team: "Platform-Team" },
    { name: "change-ec2-instance.yml #1041", conclusion: "in_progress", env: "dev", team: "Application-Team" },
    { name: "change-ec2-instance.yml #998", conclusion: "success", env: "prod", team: "Platform-Team" },
    { name: "provision-s3-bucket.yml #1033", conclusion: "failure", env: "dev", team: "Application-Team" },
    { name: "provision-s3-bucket.yml #1011", conclusion: "success", env: "dev", team: "Platform-Team" },
  ],
  jira: [
    { key: "IDP-73182", title: "Provision IDP demo bastion", status: "Done", team: "Platform-Team", env: "dev" },
    { key: "IDP-73201", title: "QA claims worker EC2", status: "In Progress", team: "Application-Team", env: "qa" },
    { key: "IDP-73218", title: "Patient portal cache node", status: "To Do", team: "Application-Team", env: "dev" },
    { key: "IDP-73190", title: "Scratch analytics instance", status: "Done", team: "Application-Team", env: "dev" },
    { key: "IDP-73155", title: "TFC runner hardening", status: "Done", team: "Platform-Team", env: "prod" },
  ],
};

const COLORS = {
  completed: "#10b981",
  success: "#10b981",
  Done: "#10b981",
  pending: "#f59e0b",
  in_progress: "#2f6bff",
  "In Progress": "#2f6bff",
  "To Do": "#94a3b8",
  failed: "#ef4444",
  failure: "#ef4444",
};

function hourGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function selected() {
  return {
    team: document.getElementById("team").value,
    env: document.getElementById("env").value,
    q: (document.getElementById("globalSearch").value || "").toLowerCase(),
  };
}

function match(row) {
  const { team, env, q } = selected();
  if (team === "me" && row.team !== "Platform-Team") return false;
  if (team !== "all" && team !== "me" && row.team !== team) return false;
  if (env !== "all" && row.env !== env) return false;
  if (q && !JSON.stringify(row).toLowerCase().includes(q)) return false;
  return true;
}

function counts(list, key) {
  const out = {};
  list.forEach((item) => {
    out[item[key]] = (out[item[key]] || 0) + 1;
  });
  return out;
}

function pie(countsMap) {
  if (!Object.keys(countsMap).length) {
    return `<div style="color:#6b7280;font-size:13px;padding:12px 0">No data for this widget</div>`;
  }
  const total = Object.values(countsMap).reduce((a, b) => a + b, 0) || 1;
  let angle = 0;
  const stops = [];
  Object.entries(countsMap).forEach(([label, n]) => {
    const next = angle + (n / total) * 360;
    stops.push(`${COLORS[label] || "#cbd5e1"} ${angle}deg ${next}deg`);
    angle = next;
  });
  const legend = Object.entries(countsMap)
    .map(
      ([label, n]) =>
        `<div><span class="swatch" style="background:${COLORS[label] || "#cbd5e1"}"></span>${label} · ${n}</div>`
    )
    .join("");
  return `<div class="pie-wrap"><div class="pie" style="background:conic-gradient(${stops.join(",")})"></div><div class="legend">${legend || "No data for this widget"}</div></div>`;
}

function badge(v) {
  const cls = ["completed", "success", "Done"].includes(v)
    ? "ok"
    : ["failed", "failure"].includes(v)
      ? "bad"
      : ["pending", "To Do"].includes(v)
        ? "warn"
        : "info";
  return `<span class="badge ${cls}">${v}</span>`;
}

function render() {
  document.getElementById("greeting").textContent = `${hourGreeting()}, ${DATA.user}`;
  const ec2 = DATA.ec2.filter(match);
  const runs = DATA.runs.filter(match);
  const jira = DATA.jira.filter(match);
  const pending = ec2.filter((r) => r.status === "pending").length;
  const failedRuns = runs.filter((r) => r.conclusion === "failure").length;
  const openJira = jira.filter((r) => r.status !== "Done").length;

  document.getElementById("kpis").innerHTML = `
    <div class="kpi warn"><div class="label">Pending EC2</div><div class="value">${pending}</div></div>
    <div class="kpi good"><div class="label">TFC EC2 total</div><div class="value">${ec2.length}</div></div>
    <div class="kpi bad"><div class="label">Failed GitHub runs</div><div class="value">${failedRuns}</div></div>
    <div class="kpi info"><div class="label">Open Jira</div><div class="value">${openJira}</div></div>
  `;

  document.getElementById("pies").innerHTML = `
    <article class="card"><h3>Terraform-managed EC2 by status</h3><div class="card-b">${pie(counts(ec2, "status"))}</div></article>
    <article class="card"><h3>GitHub Workflow Runs by status</h3><div class="card-b">${pie(counts(runs, "conclusion"))}</div></article>
    <article class="card"><h3>Jira issues by status</h3><div class="card-b">${pie(counts(jira, "status"))}</div></article>
  `;

  document.getElementById("quick").innerHTML = `
    <article class="card">
      <h3>Quick view</h3>
      <div class="card-b">
        <button class="link" data-table="ec2">Terraform-managed EC2</button>
        <button class="link" data-table="runs">GitHub Workflow Runs</button>
        <button class="link">Self-service hub</button>
        <button class="link">Users and teams</button>
      </div>
    </article>
    <article class="card">
      <h3>Self-service</h3>
      <div class="card-b">
        <div class="row"><span>Provision EC2 Instance</span><button class="btn">+ Create</button></div>
        <div class="row"><span>Create S3 Bucket</span><button class="btn">+ Create</button></div>
        <div class="row"><span>Submit Feedback</span><button class="btn">+ Create</button></div>
      </div>
    </article>
  `;

  document.getElementById("personal").innerHTML = `
    <article class="card"><h3>My entities</h3><div class="card-b">
      <div class="row"><span>Jira Issue</span><span class="type">${jira.length}</span></div>
      <div class="row"><span>Terraform-managed EC2</span><span class="type">${ec2.filter((r) => r.team === "Platform-Team").length}</span></div>
    </div></article>
    <article class="card"><h3>Recently viewed entities</h3><div class="card-b">
      <div class="row"><span>S3 Bucket Provisioning</span><span class="type">Service Offering</span></div>
      <div class="row"><span>Marvin Constant Jira Pilot Space</span><span class="type">Jira Project</span></div>
    </div></article>
    <article class="card"><h3>Recently used actions</h3><div class="card-b">
      <div class="row"><span>Submit Feedback</span><span class="type">Action</span></div>
      <div class="row"><span>Provision EC2 Instance</span><span class="type">Action</span></div>
    </div></article>
  `;

  document.getElementById("tables").innerHTML = `
    <article class="card" id="table-ec2"><h3>Terraform-managed EC2</h3><div class="card-b">
      <table><thead><tr><th>Name</th><th>Env</th><th>Status</th><th>Team</th></tr></thead>
      <tbody>${ec2.map((r) => `<tr><td>${r.name}</td><td>${r.env}</td><td>${badge(r.status)}</td><td>${r.team}</td></tr>`).join("")}</tbody></table>
    </div></article>
    <article class="card" id="table-runs"><h3>GitHub Workflow Runs</h3><div class="card-b">
      <table><thead><tr><th>Run</th><th>Env</th><th>Status</th><th>Team</th></tr></thead>
      <tbody>${runs.map((r) => `<tr><td>${r.name}</td><td>${r.env}</td><td>${badge(r.conclusion)}</td><td>${r.team}</td></tr>`).join("")}</tbody></table>
    </div></article>
  `;
}

document.getElementById("team").onchange = render;
document.getElementById("env").onchange = render;
document.getElementById("globalSearch").oninput = render;
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-table]");
  if (btn) document.getElementById("table-" + (btn.dataset.table === "jira" ? "ec2" : btn.dataset.table))?.scrollIntoView({ behavior: "smooth" });
});
render();
