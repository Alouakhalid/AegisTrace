export async function renderProjects(container, navigate, state, api, showModal, toast) {
  let projects = [];
  try {
    projects = await api.listProjects();
  } catch (e) {
    console.error("Failed to fetch projects:", e);
  }

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Projects Portfolio & Target Repositories</h1>
          <p class="page-subtitle">Configure application repositories, framework hints, and baseline security twins.</p>
        </div>
        <button class="btn btn-primary" id="btn-open-create-project">
          + Create Project
        </button>
      </div>

      <div class="card">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Project Name</th>
                <th>Repository / Source</th>
                <th>Framework</th>
                <th>Last Scan</th>
                <th>Open Findings</th>
                <th>Security Score</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${projects.map(p => `
                <tr>
                  <td>
                    <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${p.name}</div>
                    <div style="font-size: 9px; color: var(--gold-base); font-family: monospace; letter-spacing: 1px;">${p.id}</div>
                  </td>
                  <td>
                    <div style="font-family: monospace; color: var(--gold-light); font-size: 0.84rem;">
                      ${p.repository_url || "Local Workspace Target"}
                    </div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">branch: ${p.branch || "main"}</div>
                  </td>
                  <td><span class="badge badge-gold">${p.project_type || "FastAPI"}</span></td>
                  <td>${p.last_scan_at || "Recent"}</td>
                  <td><span style="color: var(--critical); font-weight: 700;">${p.open_findings || 0}</span></td>
                  <td>
                    <span class="badge ${p.security_score >= 90 ? 'badge-success' : 'badge-gold'}">
                      ${p.security_score || 94}/100
                    </span>
                  </td>
                  <td>
                    <button class="btn btn-primary btn-sm btn-scan-project" data-id="${p.id}" data-name="${p.name}">
                      Launch Scan
                    </button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  document.getElementById("btn-open-create-project")?.addEventListener("click", () => {
    showModal({
      title: "Initialize New Sovereign Project",
      bodyHtml: `
        <div>
          <div class="form-group">
            <label class="form-label">Project Name *</label>
            <input type="text" class="form-control" id="new-project-name" placeholder="e.g. Sovereign Wealth Core Banking" required>
          </div>
          <div class="form-group">
            <label class="form-label">Repository URL (GitHub or Remote Git)</label>
            <input type="text" class="form-control" id="new-project-repo" placeholder="https://github.com/enterprise/core-service">
            <div class="form-hint">Leave empty to assess a local filesystem path.</div>
          </div>
          <div class="form-group">
            <label class="form-label">Default Branch</label>
            <input type="text" class="form-control" id="new-project-branch" value="main">
          </div>
          <div class="form-group">
            <label class="form-label">Framework / Technology Stack</label>
            <select class="form-select" id="new-project-type">
              <option value="FastAPI / Python">FastAPI / Python</option>
              <option value="Flask / SQLAlchemy">Flask / SQLAlchemy</option>
              <option value="Django REST Framework">Django REST Framework</option>
              <option value="Node.js / Express">Node.js / Express</option>
              <option value="Spring Boot / Java">Spring Boot / Java</option>
            </select>
          </div>
        </div>
      `,
      confirmText: "Create Project",
      onConfirm: async () => {
        const name = document.getElementById("new-project-name").value.trim();
        const repo = document.getElementById("new-project-repo").value.trim();
        const branch = document.getElementById("new-project-branch").value.trim();
        const ptype = document.getElementById("new-project-type").value;
        if (!name) {
          toast("Project name is required", "critical");
          return false;
        }
        try {
          await api.createProject({
            name,
            repository_url: repo,
            branch,
            project_type: ptype
          });
          toast("Project registered in Sovereign Vault!", "success");
          renderProjects(container, navigate, state, api, showModal, toast);
          return true;
        } catch (e) {
          toast("Failed to create project: " + e.message, "critical");
          return false;
        }
      }
    });
  });

  container.querySelectorAll(".btn-scan-project").forEach(btn => {
    btn.addEventListener("click", (e) => {
      state.currentProjectId = e.currentTarget.getAttribute("data-id");
      state.currentProjectName = e.currentTarget.getAttribute("data-name");
      navigate("wizard");
    });
  });
}
