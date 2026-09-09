const DATA = {
  user: "Vishwak",
  infra: [
    { resource: "ec2", resource_name: "idp-demo-bastion", aws_region: "us-west-2", environment: "dev", requestor: "priya", provisioning_status: "provisioned", created_at: "2026-09-08 09:14" },
    { resource: "ec2", resource_name: "claims-worker-qa", aws_region: "us-east-1", environment: "qa", requestor: "alex", provisioning_status: "provisioned", created_at: "2026-09-08 11:02" },
    { resource: "ec2", resource_name: "patient-cache-dev", aws_region: "us-west-2", environment: "dev", requestor: "alex", provisioning_status: "provisioned", created_at: "2026-09-07 16:40" },
    { resource: "ec2", resource_name: "analytics-scratch", aws_region: "us-east-1", environment: "dev", requestor: "jordan", provisioning_status: "pending", created_at: "2026-09-06 08:21" },
    { resource: "ec2", resource_name: "tfc-runner-prod", aws_region: "us-west-2", environment: "prod", requestor: "priya", provisioning_status: "failed", created_at: "2026-09-05 13:55" },
    { resource: "s3", resource_name: "bh-idp-artifacts-dev", aws_region: "us-west-2", environment: "dev", requestor: "priya", provisioning_status: "provisioned", created_at: "2026-09-07 14:03" },
    { resource: "s3", resource_name: "bh-claims-logs-qa", aws_region: "us-east-1", environment: "qa", requestor: "alex", provisioning_status: "provisioned", created_at: "2026-09-08 10:18" },
    { resource: "s3", resource_name: "bh-analytics-raw-prod", aws_region: "us-east-1", environment: "prod", requestor: "jordan", provisioning_status: "pending", created_at: "2026-09-04 09:47" },
    { resource: "s3", resource_name: "bh-app-backups-dev", aws_region: "us-west-2", environment: "dev", requestor: "alex", provisioning_status: "failed", created_at: "2026-09-03 17:12" },
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
  provisioned: "#10b981",
  pending: "#f59e0b",
  failed: "#ef4444",
  failure: "#ef4444",
  success: "#10b981",
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
  const cls = ["provisioned", "success", "Done"].includes(v)
    ? "ok"
    : ["failed", "failure"].includes(v)
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
  const provisionedEc2 = ec2.filter((r) => r.provisioning_status === "provisioned");
  const provisionedS3 = s3.filter((r) => r.provisioning_status === "provisioned");
  const failedRuns = runs.filter((r) => r.conclusion === "failure");
  const doneJira = jira.filter((r) => r.status === "Done");

  document.getElementById("quickLinks").innerHTML = `
    <article class="card">
      <h3>Quick view</h3>
      <div class="card-b quick-chips">
        <button class="chip">Self-service hub</button>
        <button class="chip">Self Service Infra Resources</button>
        <button class="chip">GitHub Workflow Runs</button>
        <button class="chip">Users and teams</button>
      </div>
    </article>`;

  document.getElementById("kpis").innerHTML = `
    <div class="kpi good">
      <div class="label">Provisioned EC2</div>
      <div class="hint">Active instances · resource = ec2</div>
      <div class="value">${provisionedEc2.length}</div>
    </div>
    <div class="kpi good">
      <div class="label">Provisioned S3</div>
      <div class="hint">Active buckets · resource = s3</div>
      <div class="value">${provisionedS3.length}</div>
    </div>
    <div class="kpi bad">
      <div class="label">Failed Workflow Runs</div>
      <div class="hint">conclusion = failure</div>
      <div class="value">${failedRuns.length}</div>
    </div>
    <div class="kpi info">
      <div class="label">Completed Tasks</div>
      <div class="hint">Jira status = Done</div>
      <div class="value">${doneJira.length}</div>
    </div>`;

  document.getElementById("pies").innerHTML = `
    <article class="card">
      <h3>EC2 by Status</h3>
      <p class="sub">Distribution of all EC2 resources</p>
      <div class="card-b">${pie(counts(ec2, "provisioning_status"))}</div>
    </article>
    <article class="card">
      <h3>S3 by Status</h3>
      <p class="sub">Distribution of all S3 resources</p>
      <div class="card-b">${pie(counts(s3, "provisioning_status"))}</div>
    </article>
    <article class="card">
      <h3>Workflow Runs by Conclusion</h3>
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

  document.getElementById("recentlyViewed").innerHTML = `
    <article class="card" id="table-viewed">
      <h3>Recently viewed entities</h3>
      <p class="sub">Sample rows — live Port shows each user’s own history</p>
      <div class="card-b">
        <div class="row"><span>idp-demo-bastion</span><span class="type">Self Service Infra Resources</span></div>
        <div class="row"><span>bh-idp-artifacts-dev</span><span class="type">Self Service Infra Resources</span></div>
        <div class="row"><span>change-ec2-instance.yml #1024</span><span class="type">GitHub Workflow Run</span></div>
        <div class="row"><span>IDP-73182</span><span class="type">Jira Issue</span></div>
        <div class="row"><span>S3 Bucket Provisioning</span><span class="type">Service Offering</span></div>
      </div>
    </article>`;
}

document.getElementById("orgSwitch").onchange = render;
document.getElementById("globalSearch").oninput = render;
render();
