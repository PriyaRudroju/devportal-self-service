const DATA = {
  user: "Vishwak",
  infra: [
    { resource: "ec2", resource_name: "idp-demo-bastion", aws_region: "us-west-2", environment: "dev", requestor: "priya", approval_status: "pending", created_at: "2026-09-08 09:14" },
    { resource: "ec2", resource_name: "claims-worker-qa", aws_region: "us-east-1", environment: "qa", requestor: "alex", approval_status: "pending", created_at: "2026-09-08 11:02" },
    { resource: "ec2", resource_name: "patient-cache-dev", aws_region: "us-west-2", environment: "dev", requestor: "alex", approval_status: "pending", created_at: "2026-09-07 16:40" },
    { resource: "ec2", resource_name: "analytics-scratch", aws_region: "us-east-1", environment: "dev", requestor: "jordan", approval_status: "approved", created_at: "2026-09-06 08:21" },
    { resource: "ec2", resource_name: "tfc-runner-prod", aws_region: "us-west-2", environment: "prod", requestor: "priya", approval_status: "rejected", created_at: "2026-09-05 13:55" },
    { resource: "s3", resource_name: "bh-claims-logs-qa", aws_region: "us-east-1", environment: "qa", requestor: "alex", approval_status: "pending", created_at: "2026-09-08 10:18" },
    { resource: "s3", resource_name: "bh-idp-artifacts-dev", aws_region: "us-west-2", environment: "dev", requestor: "priya", approval_status: "pending", created_at: "2026-09-07 14:03" },
    { resource: "s3", resource_name: "bh-analytics-raw-prod", aws_region: "us-east-1", environment: "prod", requestor: "jordan", approval_status: "approved", created_at: "2026-09-04 09:47" },
    { resource: "s3", resource_name: "bh-app-backups-dev", aws_region: "us-west-2", environment: "dev", requestor: "alex", approval_status: "rejected", created_at: "2026-09-03 17:12" },
  ],
  runs: [
    { name: "change-ec2-instance.yml #1024", conclusion: "success", status: "completed", createdAt: "2026-09-08 12:01", link: "github.com/BHGitOps/…" },
    { name: "change-ec2-instance.yml #1041", conclusion: "in_progress", status: "queued", createdAt: "2026-09-08 12:22", link: "github.com/BHGitOps/…" },
    { name: "change-ec2-instance.yml #998", conclusion: "success", status: "completed", createdAt: "2026-09-07 18:44", link: "github.com/BHGitOps/…" },
    { name: "provision-s3-bucket.yml #1033", conclusion: "failure", status: "completed", createdAt: "2026-09-08 08:19", link: "github.com/BHGitOps/…" },
    { name: "provision-s3-bucket.yml #1011", conclusion: "success", status: "completed", createdAt: "2026-09-06 15:02", link: "github.com/BHGitOps/…" },
    { name: "terraform-plan.yml #880", conclusion: "failure", status: "completed", createdAt: "2026-09-05 11:36", link: "github.com/BHGitOps/…" },
  ],
  jira: [
    { key: "IDP-73182", issueType: "Story", priority: "High", status: "Done", assignee: "Priya", updated: "2026-09-08" },
    { key: "IDP-73201", issueType: "Task", priority: "Medium", status: "In Progress", assignee: "Alex", updated: "2026-09-08" },
    { key: "IDP-73218", issueType: "Story", priority: "Low", status: "To Do", assignee: "Jordan", updated: "2026-09-07" },
    { key: "IDP-73190", issueType: "Bug", priority: "High", status: "Done", assignee: "Alex", updated: "2026-09-07" },
    { key: "IDP-73155", issueType: "Task", priority: "Medium", status: "Done", assignee: "Priya", updated: "2026-09-06" },
  ],
};

const COLORS = {
  pending: "#f59e0b",
  approved: "#10b981",
  rejected: "#ef4444",
  success: "#10b981",
  failure: "#ef4444",
  in_progress: "#2f6bff",
  Done: "#10b981",
};

function hourGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function query() {
  return (document.getElementById("globalSearch").value || "").toLowerCase();
}

function match(row) {
  const q = query();
  if (!q) return true;
  return JSON.stringify(row).toLowerCase().includes(q);
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
    return `<div class="empty">No data for this widget</div>`;
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
  return `<div class="pie-wrap"><div class="pie" style="background:conic-gradient(${stops.join(",")})"></div><div class="legend">${legend}</div></div>`;
}

function badge(v) {
  const cls = ["approved", "success", "Done"].includes(v)
    ? "ok"
    : ["rejected", "failure"].includes(v)
      ? "bad"
      : ["pending", "To Do"].includes(v)
        ? "warn"
        : "info";
  return `<span class="badge ${cls}">${v}</span>`;
}

function rowsHtml(list, cols) {
  if (!list.length) return `<div class="empty">No rows for this filter</div>`;
  return `<table><thead><tr>${cols.map((c) => `<th>${c.label}</th>`).join("")}</tr></thead>
    <tbody>${list
      .map(
        (r) =>
          `<tr>${cols
            .map((c) => `<td>${c.badge ? badge(r[c.key]) : r[c.key]}</td>`)
            .join("")}</tr>`
      )
      .join("")}</tbody></table>`;
}

function render() {
  const org = document.getElementById("orgSwitch").value;
  const orgLabel = { dev: "Dev", qa: "QA", prod: "Prod" }[org];
  document.getElementById("greeting").textContent = `${hourGreeting()}, ${DATA.user}  ·  ${orgLabel} preview`;

  const infra = DATA.infra.filter(match);
  const runs = DATA.runs.filter(match);
  const jira = DATA.jira.filter(match);
  const ec2 = infra.filter((r) => r.resource === "ec2");
  const s3 = infra.filter((r) => r.resource === "s3");
  const pendingEc2 = ec2.filter((r) => r.approval_status === "pending");
  const pendingS3 = s3.filter((r) => r.approval_status === "pending");
  const failedRuns = runs.filter((r) => r.conclusion === "failure");
  const doneJira = jira.filter((r) => r.status === "Done");

  document.getElementById("quickLinks").innerHTML = `
    <article class="card">
      <h3>Quick view</h3>
      <div class="card-b quick-chips">
        <button class="chip">Self-service hub</button>
        <button class="chip" data-table="ec2">Terraform-managed EC2</button>
        <button class="chip" data-table="runs">GitHub Workflow Runs</button>
        <button class="chip">Users and teams</button>
      </div>
    </article>`;

  document.getElementById("kpis").innerHTML = `
    <div class="kpi warn">
      <div class="label">Pending EC2 Requests</div>
      <div class="hint">Awaiting approval · resource = ec2</div>
      <div class="value">${pendingEc2.length}</div>
    </div>
    <div class="kpi warn">
      <div class="label">Pending S3 Requests</div>
      <div class="hint">Awaiting approval · resource = s3</div>
      <div class="value">${pendingS3.length}</div>
    </div>
    <div class="kpi bad">
      <div class="label">Failed Workflow Runs</div>
      <div class="hint">conclusion = failure</div>
      <div class="value">${failedRuns.length}</div>
    </div>
    <div class="kpi good">
      <div class="label">Completed Tasks</div>
      <div class="hint">Jira status = Done</div>
      <div class="value">${doneJira.length}</div>
    </div>`;

  document.getElementById("pies").innerHTML = `
    <article class="card">
      <h3>EC2 Requests by Status</h3>
      <p class="sub">Distribution of approval states</p>
      <div class="card-b">${pie(counts(ec2, "approval_status"))}</div>
    </article>
    <article class="card">
      <h3>S3 Requests by Status</h3>
      <p class="sub">Distribution of approval states</p>
      <div class="card-b">${pie(counts(s3, "approval_status"))}</div>
    </article>
    <article class="card">
      <h3>Workflow Runs by Status</h3>
      <p class="sub">Distribution of run conclusions</p>
      <div class="card-b">${pie(counts(runs, "conclusion"))}</div>
    </article>`;

  document.getElementById("actions").innerHTML = `
    <article class="card">
      <h3>Quick Actions</h3>
      <p class="sub">Common self-service operations</p>
      <div class="card-b action-row">
        <button class="btn">Create EC2 Instance</button>
        <button class="btn">Create S3 Bucket</button>
        <button class="btn">Submit Feedback</button>
      </div>
    </article>`;

  document.getElementById("tables").innerHTML = `
    <article class="card" id="table-ec2">
      <h3>Pending EC2 Requests</h3>
      <p class="sub">Awaiting approval · sample rows</p>
      <div class="card-b">${rowsHtml(pendingEc2, [
        { key: "resource_name", label: "resource_name" },
        { key: "aws_region", label: "aws_region" },
        { key: "environment", label: "environment" },
        { key: "requestor", label: "requestor" },
        { key: "approval_status", label: "approval_status", badge: true },
        { key: "created_at", label: "created_at" },
      ])}</div>
    </article>
    <article class="card" id="table-s3">
      <h3>Pending S3 Requests</h3>
      <p class="sub">Awaiting approval · sample rows</p>
      <div class="card-b">${rowsHtml(pendingS3, [
        { key: "resource_name", label: "resource_name" },
        { key: "aws_region", label: "aws_region" },
        { key: "environment", label: "environment" },
        { key: "requestor", label: "requestor" },
        { key: "approval_status", label: "approval_status", badge: true },
        { key: "created_at", label: "created_at" },
      ])}</div>
    </article>
    <article class="card" id="table-runs">
      <h3>Recent Failed Workflow Runs</h3>
      <p class="sub">Investigation needed</p>
      <div class="card-b">${rowsHtml(failedRuns, [
        { key: "name", label: "name" },
        { key: "conclusion", label: "conclusion", badge: true },
        { key: "status", label: "status" },
        { key: "createdAt", label: "createdAt" },
        { key: "link", label: "link" },
      ])}</div>
    </article>
    <article class="card" id="table-jira">
      <h3>Recently Completed Tasks</h3>
      <p class="sub">Jira issues marked Done</p>
      <div class="card-b">${rowsHtml(doneJira, [
        { key: "key", label: "key" },
        { key: "issueType", label: "issueType" },
        { key: "priority", label: "priority" },
        { key: "status", label: "status", badge: true },
        { key: "assignee", label: "assignee" },
        { key: "updated", label: "updated" },
      ])}</div>
    </article>`;
}

document.getElementById("orgSwitch").onchange = render;
document.getElementById("globalSearch").oninput = render;
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-table]");
  if (!btn) return;
  document.getElementById("table-" + btn.dataset.table)?.scrollIntoView({ behavior: "smooth" });
});
render();
