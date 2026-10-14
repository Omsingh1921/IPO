"""
Web Dashboard Route Handler for Indian IPO Recommendation Platform (Phase 10 - Stage 6).
Serves a self-contained, responsive Vanilla HTML5/CSS/JavaScript single-page interface
at GET / and GET /dashboard for interactive exploration, recommendation analysis,
portfolio capital allocation, and system observability.
Requires zero external npm or Node.js dependencies.
"""

from fastapi import APIRouter, status
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="", tags=["Dashboard"])

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Indian IPO Intelligence & Recommendation Platform</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-secondary: #121826;
      --bg-card: rgba(22, 30, 46, 0.75);
      --bg-card-hover: rgba(30, 41, 64, 0.85);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-focus: #3b82f6;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-blue: #3b82f6;
      --accent-blue-hover: #2563eb;
      --accent-green: #10b981;
      --accent-yellow: #f59e0b;
      --accent-red: #ef4444;
      --accent-purple: #8b5cf6;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-family);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Header & Navigation */
    header {
      background: rgba(18, 24, 38, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.75rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
    }
    .brand-logo {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      color: #fff;
    }
    .brand-title {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--text-primary);
      letter-spacing: -0.02em;
    }
    .brand-badge {
      font-size: 0.7rem;
      background: rgba(59, 130, 246, 0.15);
      color: var(--accent-blue);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(59, 130, 246, 0.3);
      font-weight: 500;
    }

    /* Auth Toolbar */
    .auth-toolbar {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
    }
    .auth-input {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.4rem 0.75rem;
      border-radius: var(--radius-sm);
      font-size: 0.8rem;
      width: 220px;
      font-family: inherit;
    }
    .auth-input:focus {
      outline: none;
      border-color: var(--border-focus);
    }
    .btn {
      background: var(--accent-blue);
      color: #fff;
      border: none;
      padding: 0.45rem 0.9rem;
      border-radius: var(--radius-sm);
      font-size: 0.82rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }
    .btn:hover { background: var(--accent-blue-hover); transform: translateY(-1px); }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.12);
      color: var(--text-primary);
    }

    /* Layout & Tabs */
    .main-nav {
      display: flex;
      gap: 0.5rem;
      padding: 1rem 2rem 0;
      border-bottom: 1px solid var(--border-color);
      background: var(--bg-secondary);
    }
    .nav-tab {
      padding: 0.65rem 1.25rem;
      font-size: 0.9rem;
      font-weight: 500;
      color: var(--text-secondary);
      border: none;
      background: none;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s ease;
    }
    .nav-tab:hover { color: var(--text-primary); }
    .nav-tab.active {
      color: var(--accent-blue);
      border-bottom-color: var(--accent-blue);
    }

    main {
      flex: 1;
      padding: 1.5rem 2rem;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
    }

    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Alert / Banner */
    .alert {
      padding: 0.85rem 1.25rem;
      border-radius: var(--radius-md);
      margin-bottom: 1.5rem;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border: 1px solid transparent;
    }
    .alert-error {
      background: rgba(239, 68, 68, 0.12);
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.3);
    }
    .alert-info {
      background: rgba(59, 130, 246, 0.12);
      color: #93c5fd;
      border-color: rgba(59, 130, 246, 0.3);
    }

    /* Cards & Grid */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1.25rem;
      margin-top: 1rem;
    }
    .card {
      background: var(--bg-card);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      transition: all 0.2s ease;
    }
    .card:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-2px);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--text-primary);
    }
    .card-subtitle {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 2px;
    }

    /* Badges */
    .badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .badge-green { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-yellow { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-red { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-purple { background: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }

    /* Key-Value Metrics */
    .metric-row {
      display: flex;
      justify-content: space-between;
      padding: 0.4rem 0;
      font-size: 0.85rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .metric-row:last-child { border-bottom: none; }
    .metric-label { color: var(--text-secondary); }
    .metric-value { font-weight: 500; color: var(--text-primary); }

    /* Filters Toolbar */
    .toolbar {
      display: flex;
      gap: 0.75rem;
      align-items: center;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }
    .search-input {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.5rem 0.9rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      min-width: 260px;
      font-family: inherit;
    }
    .select-input {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.5rem 0.9rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-family: inherit;
    }

    /* Progress bar */
    .progress-bar-bg {
      background: rgba(255, 255, 255, 0.08);
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 4px;
    }
    .progress-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      border-radius: 4px;
    }

    /* Modal / Overlay */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 200;
      padding: 1rem;
    }
    .modal-overlay.active { display: flex; }
    .modal-content {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      width: 100%;
      max-width: 760px;
      max-height: 85vh;
      overflow-y: auto;
      padding: 1.75rem;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 0.75rem;
    }
    .modal-close {
      background: none;
      border: none;
      color: var(--text-secondary);
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
    }

    /* Disclaimer Footer */
    footer {
      border-top: 1px solid var(--border-color);
      padding: 1.25rem 2rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      text-align: center;
      background: var(--bg-secondary);
      margin-top: 2rem;
    }
  </style>
</head>
<body>
  <!-- Header -->
  <header>
    <a href="#" class="brand">
      <div class="brand-logo">₹</div>
      <span class="brand-title">Indian IPO Intelligence Platform</span>
      <span class="brand-badge">Phase 10 Stage 6</span>
    </a>
    <div class="auth-toolbar">
      <input type="password" id="authKeyInput" class="auth-input" placeholder="Enter API Key or Bearer Token">
      <button class="btn btn-secondary" onclick="applyCredentials()" id="authBtn">Authenticate</button>
      <button class="btn btn-secondary" onclick="setQuickRole('key-operator-456')" title="Set Dev Operator Key">Operator Mode</button>
      <button class="btn btn-secondary" onclick="setQuickRole('key-admin-789')" title="Set Dev Admin Key">Admin Mode</button>
    </div>
  </header>

  <!-- Navigation Tabs -->
  <nav class="main-nav">
    <button class="nav-tab active" onclick="switchTab('iposTab', this)">IPO Offerings</button>
    <button class="nav-tab" onclick="switchTab('recommendationTab', this)">Recommendation Engine</button>
    <button class="nav-tab" onclick="switchTab('portfolioTab', this)">Portfolio Allocator</button>
    <button class="nav-tab" onclick="switchTab('systemTab', this)">System Health & Telemetry</button>
  </nav>

  <!-- Main Content -->
  <main>
    <div id="alertBanner" class="alert alert-info" style="display: none;">
      <span id="alertMessage"></span>
      <button style="background:none;border:none;color:inherit;cursor:pointer;" onclick="hideAlert()">✕</button>
    </div>

    <!-- TAB 1: IPO Offerings -->
    <section id="iposTab" class="tab-content active">
      <div class="toolbar">
        <input type="text" id="ipoSearchInput" class="search-input" placeholder="Search by company or IPO ID..." oninput="filterIPOs()">
        <select id="ipoStatusFilter" class="select-input" onchange="loadIPOs()">
          <option value="">All Offerings</option>
          <option value="Currently Open">Currently Open</option>
          <option value="Closing Today">Closing Today</option>
          <option value="Upcoming">Upcoming</option>
          <option value="Closed / Listed">Closed / Listed</option>
        </select>
        <button class="btn" onclick="loadIPOs()">Refresh Offerings</button>
      </div>

      <div id="iposLoading" style="text-align: center; padding: 3rem; color: var(--text-secondary);">Loading offerings from API...</div>
      <div id="iposGrid" class="grid" style="display: none;"></div>
      <div id="iposEmpty" style="display: none; text-align: center; padding: 3rem; color: var(--text-secondary);">No active offerings matched the filter.</div>
    </section>

    <!-- TAB 2: Recommendation Engine -->
    <section id="recommendationTab" class="tab-content">
      <div class="card" style="margin-bottom: 1.5rem;">
        <h3 style="margin-bottom: 0.75rem;">Evaluate IPO Recommendation</h3>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
          Executes multi-factor recommendation engine (0-100 composite score, conviction tiers, veto constraints).
        </p>
        <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
          <input type="text" id="recIpoIdInput" class="search-input" placeholder="Enter IPO ID (e.g. TEST-IPO-001)">
          <button class="btn" onclick="runRecommendation()">Evaluate Recommendation</button>
        </div>
      </div>

      <div id="recResultCard" class="card" style="display: none;">
        <div class="card-header">
          <div>
            <h2 id="recCompanyName" class="card-title"></h2>
            <div id="recIpoId" class="card-subtitle"></div>
          </div>
          <span id="recBadge" class="badge"></span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.25rem 0;">
          <div class="card" style="padding: 1rem; text-align: center;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Composite Score</div>
            <div id="recScore" style="font-size: 2.2rem; font-weight: 700; color: var(--accent-blue); margin: 0.25rem 0;"></div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Scale 0 to 100</div>
          </div>
          <div class="card" style="padding: 1rem; text-align: center;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Confidence</div>
            <div id="recConfidence" style="font-size: 2.2rem; font-weight: 700; color: var(--accent-green); margin: 0.25rem 0;"></div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Data Completeness</div>
          </div>
          <div class="card" style="padding: 1rem; text-align: center;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Risk Level</div>
            <div id="recRiskLevel" style="font-size: 2.2rem; font-weight: 700; margin: 0.25rem 0;"></div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Calculated Risk Tier</div>
          </div>
        </div>

        <h4 style="margin: 1.25rem 0 0.5rem;">Factor Breakdown</h4>
        <div id="recFactorsList"></div>

        <h4 style="margin: 1.25rem 0 0.5rem;">Key Strengths</h4>
        <ul id="recStrengths" style="padding-left: 1.25rem; font-size: 0.85rem; color: var(--text-secondary);"></ul>

        <h4 style="margin: 1.25rem 0 0.5rem;">Disclosed Risks</h4>
        <ul id="recRisks" style="padding-left: 1.25rem; font-size: 0.85rem; color: var(--text-secondary);"></ul>

        <div style="margin-top: 1.25rem; padding: 0.75rem; background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); font-size: 0.8rem; color: var(--text-muted);">
          <strong>Summary Rationale:</strong> <span id="recRationale"></span>
        </div>
      </div>
    </section>

    <!-- TAB 3: Portfolio Allocator -->
    <section id="portfolioTab" class="tab-content">
      <div class="card" style="margin-bottom: 1.5rem;">
        <h3 style="margin-bottom: 0.75rem;">Portfolio Capital Allocation</h3>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
          Executes institutional capital allocation with strict risk constraints (max 35% single-IPO cap, max 40% sector cap).
        </p>
        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
          <div>
            <label style="font-size: 0.75rem; color: var(--text-secondary); display: block; margin-bottom: 4px;">Available Capital (₹)</label>
            <input type="number" id="allocCapitalInput" class="search-input" value="500000" min="10000" step="10000">
          </div>
          <div>
            <label style="font-size: 0.75rem; color: var(--text-secondary); display: block; margin-bottom: 4px;">Risk Profile</label>
            <select id="allocProfileInput" class="select-input">
              <option value="CONSERVATIVE">Conservative</option>
              <option value="MODERATE" selected>Moderate</option>
              <option value="AGGRESSIVE">Aggressive</option>
            </select>
          </div>
          <div style="align-self: flex-end;">
            <button class="btn" onclick="runAllocation()">Compute Allocation</button>
          </div>
        </div>
      </div>

      <div id="allocResultCard" class="card" style="display: none;">
        <h3>Capital Allocation Summary</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0;">
          <div class="card" style="padding: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Total Capital</div>
            <div id="allocTotalCap" style="font-size: 1.25rem; font-weight: 700;"></div>
          </div>
          <div class="card" style="padding: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Allocated Capital</div>
            <div id="allocDeployedCap" style="font-size: 1.25rem; font-weight: 700; color: var(--accent-green);"></div>
          </div>
          <div class="card" style="padding: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Unallocated Cash</div>
            <div id="allocCash" style="font-size: 1.25rem; font-weight: 700; color: var(--accent-yellow);"></div>
          </div>
          <div class="card" style="padding: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary);">Total Allocation %</div>
            <div id="allocPct" style="font-size: 1.25rem; font-weight: 700; color: var(--accent-blue);"></div>
          </div>
        </div>

        <h4 style="margin: 1.25rem 0 0.5rem;">Recommended Positions</h4>
        <div id="allocPositionsGrid" class="grid" style="margin-top: 0.5rem;"></div>

        <div id="allocNotes" style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted);"></div>
      </div>
    </section>

    <!-- TAB 4: System Health -->
    <section id="systemTab" class="tab-content">
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">System Diagnostic Health Probes</h3>
            <div class="card-subtitle">Real-time telemetry and subsystem status</div>
          </div>
          <button class="btn btn-secondary" onclick="loadHealth()">Run Health Probes</button>
        </div>
        <div id="healthStatusBanner" style="margin: 1rem 0; font-size: 0.9rem;"></div>
        <div id="healthChecksList"></div>
      </div>
    </section>
  </main>

  <!-- Detail Modal -->
  <div id="detailModal" class="modal-overlay" onclick="closeModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
      <div class="modal-header">
        <div>
          <h2 id="modalCompanyName" style="font-size: 1.25rem; font-weight: 600;"></h2>
          <div id="modalIpoId" style="font-size: 0.8rem; color: var(--text-secondary);"></div>
        </div>
        <button class="modal-close" onclick="closeModalDirect()">&times;</button>
      </div>
      <div id="modalBody"></div>
    </div>
  </div>

  <!-- Disclaimer Footer -->
  <footer>
    <strong>MANDATORY DISCLAIMER:</strong> This platform is strictly an independent analytical decision-support and research engine. 
    It does not execute automated trading, guarantee returns, or provide financial investment advice. Public IPO investments involve substantial market risk.
  </footer>

  <!-- Dashboard JavaScript -->
  <script>
    let activeToken = localStorage.getItem("ipo_platform_auth") || "";
    let cachedIPOs = [];

    document.addEventListener("DOMContentLoaded", () => {
      if (activeToken) {
        document.getElementById("authKeyInput").value = activeToken;
      }
      loadIPOs();
      loadHealth();
    });

    function applyCredentials() {
      const val = document.getElementById("authKeyInput").value.trim();
      activeToken = val;
      localStorage.setItem("ipo_platform_auth", val);
      showAlert("Credentials updated. Refreshing views...", "info");
      loadIPOs();
    }

    function setQuickRole(key) {
      document.getElementById("authKeyInput").value = key;
      applyCredentials();
    }

    function getAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (activeToken) {
        if (activeToken.startsWith("Bearer ") || activeToken.startsWith("eyJ")) {
          headers["Authorization"] = activeToken.startsWith("Bearer ") ? activeToken : `Bearer ${activeToken}`;
        } else {
          headers["X-API-Key"] = activeToken;
        }
      }
      return headers;
    }

    function showAlert(msg, type = "error") {
      const b = document.getElementById("alertBanner");
      const m = document.getElementById("alertMessage");
      b.className = `alert alert-${type}`;
      m.innerText = msg;
      b.style.display = "flex";
    }

    function hideAlert() {
      document.getElementById("alertBanner").style.display = "none";
    }

    function switchTab(tabId, el) {
      document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      document.getElementById(tabId).classList.add("active");
      el.classList.add("active");
    }

    async function loadIPOs() {
      const grid = document.getElementById("iposGrid");
      const loading = document.getElementById("iposLoading");
      const empty = document.getElementById("iposEmpty");
      const statusFilter = document.getElementById("ipoStatusFilter").value;

      loading.style.display = "block";
      grid.style.display = "none";
      empty.style.display = "none";

      try {
        let url = `/ipos?limit=100`;
        if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;
        
        const res = await fetch(url, { headers: getAuthHeaders() });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`Failed to fetch IPOs: ${err.detail || res.statusText}`, "error");
          loading.style.display = "none";
          return;
        }

        const data = await res.json();
        cachedIPOs = data.items || [];
        renderIPOs(cachedIPOs);
      } catch (e) {
        showAlert(`Network error loading IPOs: ${e.message}`, "error");
      } finally {
        loading.style.display = "none";
      }
    }

    function renderIPOs(items) {
      const grid = document.getElementById("iposGrid");
      const empty = document.getElementById("iposEmpty");
      grid.innerHTML = "";

      if (!items || items.length === 0) {
        empty.style.display = "block";
        grid.style.display = "none";
        return;
      }

      empty.style.display = "none";
      grid.style.display = "grid";

      items.forEach(ipo => {
        const card = document.createElement("div");
        card.className = "card";
        const gmpBadge = ipo.gmp_percentage !== null 
          ? `<span class="badge ${ipo.gmp_percentage >= 20 ? 'badge-green' : 'badge-yellow'}">GMP +${ipo.gmp_percentage.toFixed(1)}%</span>`
          : `<span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);">GMP N/A</span>`;

        card.innerHTML = `
          <div class="card-header">
            <div>
              <div class="card-title">${escapeHtml(ipo.company_name)}</div>
              <div class="card-subtitle">${escapeHtml(ipo.ipo_id)} • ${escapeHtml(ipo.sector || 'General')}</div>
            </div>
            ${gmpBadge}
          </div>
          <div class="metric-row">
            <span class="metric-label">Status</span>
            <span class="metric-value">${escapeHtml(ipo.status || 'Active')}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Issue Size</span>
            <span class="metric-value">${ipo.issue_size_cr ? `₹${ipo.issue_size_cr.toLocaleString('en-IN')} Cr` : 'Not disclosed'}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Price Band</span>
            <span class="metric-value">${ipo.price_band ? `₹${ipo.price_band}` : 'Fixed / TBA'}</span>
          </div>
          <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary" style="flex: 1;" onclick="openIpoDetails('${escapeHtml(ipo.ipo_id)}')">Details</button>
            <button class="btn" style="flex: 1;" onclick="quickEvaluate('${escapeHtml(ipo.ipo_id)}')">Evaluate</button>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function filterIPOs() {
      const q = document.getElementById("ipoSearchInput").value.toLowerCase();
      const filtered = cachedIPOs.filter(i => 
        (i.company_name && i.company_name.toLowerCase().includes(q)) ||
        (i.ipo_id && i.ipo_id.toLowerCase().includes(q)) ||
        (i.sector && i.sector.toLowerCase().includes(q))
      );
      renderIPOs(filtered);
    }

    async function openIpoDetails(ipoId) {
      try {
        const res = await fetch(`/ipos/${encodeURIComponent(ipoId)}`, { headers: getAuthHeaders() });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`Failed to load details: ${err.detail || res.statusText}`, "error");
          return;
        }
        const data = await res.json();
        const r = data.record || {};

        document.getElementById("modalCompanyName").innerText = data.company_name;
        document.getElementById("modalIpoId").innerText = data.ipo_id;

        const body = document.getElementById("modalBody");
        body.innerHTML = `
          <div class="card" style="margin-bottom: 1rem;">
            <h4 style="margin-bottom: 0.5rem;">Corporate Entity</h4>
            <div class="metric-row"><span class="metric-label">Company</span><span class="metric-value">${escapeHtml(r.ipo_entity?.company_name || 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">Sector</span><span class="metric-value">${escapeHtml(r.ipo_entity?.sector || 'General')}</span></div>
            <div class="metric-row"><span class="metric-label">Exchange Listing</span><span class="metric-value">${escapeHtml(r.ipo_entity?.issue_type || 'Mainboard')}</span></div>
          </div>
          <div class="card" style="margin-bottom: 1rem;">
            <h4 style="margin-bottom: 0.5rem;">Issue Structure & Timeline</h4>
            <div class="metric-row"><span class="metric-label">Issue Size</span><span class="metric-value">${r.issue_structure?.issue_size?.formatted_inr || 'TBA'}</span></div>
            <div class="metric-row"><span class="metric-label">Price Band</span><span class="metric-value">₹${r.issue_structure?.price_band_low?.value || '-'} - ₹${r.issue_structure?.price_band_high?.value || '-'}</span></div>
            <div class="metric-row"><span class="metric-label">Lot Size</span><span class="metric-value">${r.issue_structure?.lot_size?.value || 'TBA'} Shares</span></div>
            <div class="metric-row"><span class="metric-label">Open Date</span><span class="metric-value">${r.ipo_status?.open_date || 'TBA'}</span></div>
            <div class="metric-row"><span class="metric-label">Close Date</span><span class="metric-value">${r.ipo_status?.close_date || 'TBA'}</span></div>
          </div>
          <div style="text-align: right; margin-top: 1rem;">
            <button class="btn" onclick="closeModalDirect(); quickEvaluate('${escapeHtml(data.ipo_id)}')">Run Recommendation Evaluation</button>
          </div>
        `;

        document.getElementById("detailModal").classList.add("active");
      } catch (e) {
        showAlert(`Error loading details: ${e.message}`, "error");
      }
    }

    function closeModal(e) {
      if (e.target.id === "detailModal") closeModalDirect();
    }
    function closeModalDirect() {
      document.getElementById("detailModal").classList.remove("active");
    }

    function quickEvaluate(ipoId) {
      document.getElementById("recIpoIdInput").value = ipoId;
      switchTab('recommendationTab', document.querySelectorAll(".nav-tab")[1]);
      runRecommendation();
    }

    async function runRecommendation() {
      const ipoId = document.getElementById("recIpoIdInput").value.trim();
      if (!ipoId) {
        showAlert("Please enter or select a valid IPO ID to evaluate", "error");
        return;
      }

      try {
        const res = await fetch("/recommendation/evaluate", {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({ ipo_id: ipoId })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`Evaluation failed: ${err.detail || res.statusText}`, "error");
          return;
        }

        const data = await res.json();
        renderRecommendationResult(data);
      } catch (e) {
        showAlert(`Evaluation network error: ${e.message}`, "error");
      }
    }

    function renderRecommendationResult(data) {
      const card = document.getElementById("recResultCard");
      card.style.display = "block";

      document.getElementById("recCompanyName").innerText = data.company_name;
      document.getElementById("recIpoId").innerText = data.ipo_id;

      const badge = document.getElementById("recBadge");
      badge.innerText = data.recommendation;
      if (data.recommendation === "STRONG_SUBSCRIBE") badge.className = "badge badge-green";
      else if (data.recommendation === "SUBSCRIBE") badge.className = "badge badge-blue";
      else if (data.recommendation === "NEUTRAL") badge.className = "badge badge-yellow";
      else badge.className = "badge badge-red";

      document.getElementById("recScore").innerText = Math.round(data.composite_score);
      document.getElementById("recConfidence").innerText = `${Math.round(data.confidence_score * 100)}%`;
      
      const riskEl = document.getElementById("recRiskLevel");
      riskEl.innerText = data.risk_level;
      if (data.risk_level === "LOW") riskEl.style.color = "var(--accent-green)";
      else if (data.risk_level === "MODERATE") riskEl.style.color = "var(--accent-yellow)";
      else riskEl.style.color = "var(--accent-red)";

      // Factors
      const factorsDiv = document.getElementById("recFactorsList");
      factorsDiv.innerHTML = "";
      for (const [name, fs] of Object.entries(data.factor_scores || {})) {
        const row = document.createElement("div");
        row.style.marginBottom = "0.75rem";
        const score = Math.round(fs.score || 0);
        row.innerHTML = `
          <div style="display:flex; justify-content:space-between; font-size:0.82rem;">
            <span>${escapeHtml(fs.description || name)}</span>
            <span style="font-weight:600;">${score}/100</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${score}%;"></div>
          </div>
        `;
        factorsDiv.appendChild(row);
      }

      // Strengths & Risks
      const strengthsList = document.getElementById("recStrengths");
      strengthsList.innerHTML = (data.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join("") || "<li>No primary strengths flagged</li>";

      const risksList = document.getElementById("recRisks");
      risksList.innerHTML = (data.risks || []).map(r => `<li>${escapeHtml(r)}</li>`).join("") || "<li>No material veto risks detected</li>";

      document.getElementById("recRationale").innerText = data.summary_rationale || "Calculated based on quantitative factor weights.";
    }

    async function runAllocation() {
      const capital = parseFloat(document.getElementById("allocCapitalInput").value);
      const profile = document.getElementById("allocProfileInput").value;

      try {
        const res = await fetch("/portfolio/allocate", {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            available_capital: capital,
            risk_profile: profile
          })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`Allocation failed: ${err.detail || res.statusText}`, "error");
          return;
        }

        const data = await res.json();
        renderAllocationResult(data);
      } catch (e) {
        showAlert(`Allocation network error: ${e.message}`, "error");
      }
    }

    function renderAllocationResult(data) {
      const card = document.getElementById("allocResultCard");
      card.style.display = "block";

      document.getElementById("allocTotalCap").innerText = `₹${data.total_capital.toLocaleString('en-IN')}`;
      document.getElementById("allocDeployedCap").innerText = `₹${data.total_allocated_capital.toLocaleString('en-IN')}`;
      document.getElementById("allocCash").innerText = `₹${data.unallocated_cash.toLocaleString('en-IN')}`;
      document.getElementById("allocPct").innerText = `${data.total_allocation_percentage.toFixed(1)}%`;

      const grid = document.getElementById("allocPositionsGrid");
      grid.innerHTML = "";

      (data.allocations || []).forEach(pos => {
        const pCard = document.createElement("div");
        pCard.className = "card";
        pCard.innerHTML = `
          <div class="card-header">
            <div>
              <div class="card-title">${escapeHtml(pos.company_name)}</div>
              <div class="card-subtitle">${escapeHtml(pos.sector)}</div>
            </div>
            <span class="badge badge-green">${pos.allocation_percentage.toFixed(1)}%</span>
          </div>
          <div class="metric-row"><span class="metric-label">Allocated Capital</span><span class="metric-value">₹${pos.allocated_amount.toLocaleString('en-IN')}</span></div>
          <div class="metric-row"><span class="metric-label">Expected Return</span><span class="metric-value">+${(pos.expected_return * 100).toFixed(1)}%</span></div>
          <div class="metric-row"><span class="metric-label">Risk Profile</span><span class="metric-value">${escapeHtml(pos.risk_level)}</span></div>
        `;
        grid.appendChild(pCard);
      });

      const notes = document.getElementById("allocNotes");
      notes.innerHTML = (data.diversification_notes || []).map(n => `<div>• ${escapeHtml(n)}</div>`).join("");
    }

    async function loadHealth() {
      try {
        const res = await fetch("/health");
        const data = await res.json();
        const banner = document.getElementById("healthStatusBanner");
        banner.innerHTML = `Overall System Status: <strong style="color: ${data.status === 'HEALTHY' ? 'var(--accent-green)' : 'var(--accent-yellow)'}">${data.status}</strong> (${data.healthy_count} healthy / ${data.degraded_count} degraded)`;

        const list = document.getElementById("healthChecksList");
        list.innerHTML = "";
        for (const [name, check] of Object.entries(data.checks || {})) {
          const cDiv = document.createElement("div");
          cDiv.className = "metric-row";
          cDiv.innerHTML = `
            <span><strong>${escapeHtml(name.toUpperCase())}</strong>: ${escapeHtml(check.message)}</span>
            <span class="badge ${check.status === 'HEALTHY' ? 'badge-green' : 'badge-yellow'}">${check.status} (${check.duration_ms}ms)</span>
          `;
          list.appendChild(cDiv);
        }
      } catch (e) {
        document.getElementById("healthStatusBanner").innerText = `Failed to load health probes: ${e.message}`;
      }
    }

    function escapeHtml(str) {
      if (!str) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }
  </script>
</body>
</html>
"""


@router.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Interactive IPO Platform Web Dashboard",
)
@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Interactive IPO Platform Web Dashboard",
)
def get_dashboard() -> HTMLResponse:
    """Delivers the native single-page web dashboard."""
    return HTMLResponse(content=_DASHBOARD_HTML, status_code=status.HTTP_200_OK)
