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

_DASHBOARD_HTML = r"""<!DOCTYPE html>
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

    /* Granular Subscription Popover (Phase 3) */
    .sub-popover-container {
      position: relative;
      display: inline-block;
    }
    .sub-popover {
      display: none;
      position: absolute;
      bottom: calc(100% + 8px);
      left: 50%;
      transform: translateX(-50%);
      width: 250px;
      background: rgba(15, 23, 42, 0.96);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.16);
      border-radius: var(--radius-md);
      padding: 0.85rem;
      box-shadow: 0 14px 35px -5px rgba(0, 0, 0, 0.7), 0 8px 12px -6px rgba(0, 0, 0, 0.5);
      z-index: 1000;
      pointer-events: auto;
      text-align: left;
    }
    .sub-popover::after {
      content: "";
      position: absolute;
      top: 100%;
      left: 50%;
      transform: translateX(-50%);
      border-width: 6px;
      border-style: solid;
      border-color: rgba(15, 23, 42, 0.96) transparent transparent transparent;
    }
    .sub-popover-container:hover .sub-popover,
    .sub-popover-container:focus-within .sub-popover,
    .sub-popover-container.popover-open .sub-popover {
      display: block;
      animation: popoverFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes popoverFadeIn {
      from { opacity: 0; transform: translate(-50%, 6px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }
    .sub-bar-bg {
      width: 100%;
      height: 5px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      margin-top: 4px;
      overflow: hidden;
    }
    .sub-bar-fill {
      height: 100%;
      border-radius: 999px;
      transition: width 0.3s ease;
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      background: #10b981;
      border-radius: 50%;
      display: inline-block;
      box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
      animation: pulse-green 2s infinite;
      flex-shrink: 0;
    }
    @keyframes pulse-green {
      0% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
      }
      70% {
        transform: scale(1);
        box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
      }
      100% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
      }
    }

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

    /* View Switcher */
    .view-switcher {
      display: inline-flex;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      overflow: hidden;
      background: var(--bg-secondary);
    }
    .view-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      padding: 0.45rem 0.85rem;
      font-size: 0.8rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s ease;
      font-family: inherit;
    }
    .view-btn:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.05);
    }
    .view-btn.active {
      background: var(--accent-blue);
      color: #ffffff;
      font-weight: 600;
    }

    /* BSE-Style Data Table */
    .table-container {
      width: 100%;
      overflow-x: auto;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      backdrop-filter: blur(12px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
      margin-top: 1rem;
    }
    .market-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
      white-space: nowrap;
    }
    .market-table th {
      background: rgba(20, 27, 45, 0.95);
      color: var(--text-secondary);
      font-weight: 600;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .market-table td {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--text-primary);
      vertical-align: middle;
    }
    .market-table tbody tr {
      transition: background 0.15s ease;
    }
    .market-table tbody tr:hover {
      background: rgba(59, 130, 246, 0.06);
    }
    .market-table tbody tr:last-child td {
      border-bottom: none;
    }
    .col-company-title {
      font-weight: 600;
      color: var(--text-primary);
      font-size: 0.88rem;
    }
    .col-company-sub {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 2px;
      display: flex;
      gap: 0.4rem;
      align-items: center;
    }
    .col-date {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.82rem;
      color: var(--text-secondary);
    }
    .col-price {
      font-weight: 600;
      color: #38bdf8;
    }
    .status-pulse {
      display: inline-block;
      width: 7px;
      height: 7px;
      border-radius: 50%;
      margin-right: 5px;
    }
    .pulse-green {
      background: #10b981;
      box-shadow: 0 0 8px rgba(16, 185, 129, 0.8);
      animation: pulse 2s infinite;
    }

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

    /* Segmented Section Switcher Pills & Section Blocks */
    .ipo-sec-pill {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-color);
      color: var(--text-secondary);
      padding: 0.42rem 0.95rem;
      border-radius: var(--radius-sm);
      font-size: 0.83rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-family: inherit;
    }
    .ipo-sec-pill:hover {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-primary);
      border-color: rgba(255, 255, 255, 0.2);
    }
    .ipo-sec-pill.active {
      background: rgba(59, 130, 246, 0.16);
      color: #93c5fd;
      border-color: rgba(59, 130, 246, 0.45);
      font-weight: 600;
      box-shadow: 0 0 12px rgba(59, 130, 246, 0.2);
    }
    .ipo-section-block {
      transition: opacity 0.2s ease;
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

    /* Upstream Feed Health Badges (Phase 2) */
    .feed-health-bar {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(255, 255, 255, 0.03);
      padding: 0.25rem 0.65rem;
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      margin: 0 auto;
    }
    .feed-chip {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.76rem;
      font-weight: 500;
      padding: 0.2rem 0.6rem;
      border-radius: 12px;
      transition: all 0.2s ease;
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }
    .feed-chip:hover {
      transform: translateY(-1px);
    }
    .chip-healthy {
      background: rgba(16, 185, 129, 0.12);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .chip-unhealthy {
      background: rgba(239, 68, 68, 0.16);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .chip-degraded {
      background: rgba(245, 158, 11, 0.16);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .chip-loading {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
    }
    .chip-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      display: inline-block;
    }
    .dot-green {
      background-color: #10b981;
      box-shadow: 0 0 6px rgba(16, 185, 129, 0.8);
    }
    .dot-red {
      background-color: #ef4444;
      box-shadow: 0 0 6px rgba(239, 68, 68, 0.8);
      animation: pulse-red 1.5s infinite;
    }
    .dot-yellow {
      background-color: #f59e0b;
      box-shadow: 0 0 6px rgba(245, 158, 11, 0.8);
    }
    .dot-gray {
      background-color: #64748b;
    }
    @keyframes pulse-red {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.2); }
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

    <!-- Upstream Feeds Live Health & Latency Badges (Phase 2) -->
    <div id="feedHealthChips" class="feed-health-bar" title="Real-time Upstream Feed Connectivity & Latency">
      <span id="chipBSE" class="feed-chip chip-loading" onclick="pollFeedHealth(true)" title="BSE India Public Issue API">
        <span class="chip-dot dot-gray"></span> BSE: <span class="chip-latency">--ms</span>
      </span>
      <span id="chipNSE" class="feed-chip chip-loading" onclick="pollFeedHealth(true)" title="NSE India IPO Live Feed">
        <span class="chip-dot dot-gray"></span> NSE: <span class="chip-latency">--ms</span>
      </span>
      <span id="chipGMP" class="feed-chip chip-loading" onclick="pollFeedHealth(true)" title="InvestorGain Live GMP Discovery">
        <span class="chip-dot dot-gray"></span> GMP: <span class="chip-latency">--ms</span>
      </span>
      <button class="btn btn-secondary" onclick="pollFeedHealth(true)" title="Force refresh live feed pings" style="padding: 2px 7px; font-size: 0.72rem; border-radius: 12px; height: 24px; cursor: pointer;">🔄</button>
    </div>

    <div class="auth-toolbar">
      <div id="authStatusIndicator" style="display: flex; align-items: center; gap: 0.5rem;">
        <span id="userStatusBadge" class="brand-badge" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border-color: rgba(16, 185, 129, 0.3);">🟢 Admin Access</span>
        <button class="btn btn-secondary" onclick="signOutPlatform()" id="signOutBtn" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;">Sign Out</button>
      </div>
      <button class="btn" id="signInHeaderBtn" onclick="openLoginModal()" style="display: none; font-size: 0.75rem; padding: 0.35rem 0.65rem;">Sign In</button>
    </div>
  </header>

  <!-- Feed Disruption Alert Banner (Surfaced if BSE/NSE/GMP fails or throttles) -->
  <div id="feedAlertBanner" class="alert alert-error" style="display: none; margin: 0.75rem 2rem 0; border-radius: var(--radius-sm); border: 1px solid rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.12); color: #fca5a5; font-size: 0.82rem; padding: 0.6rem 1rem; align-items: center; justify-content: space-between;">
    <div style="display: flex; align-items: center; gap: 0.6rem;">
      <span style="font-size: 1.1rem;">⚠️</span>
      <span id="feedAlertMessage"></span>
    </div>
    <button style="background: none; border: none; color: inherit; cursor: pointer; font-size: 1rem;" onclick="dismissFeedAlert()">✕</button>
  </div>

  <!-- Login Gate Modal for Personal Production Deployment -->
  <div id="loginModal" style="display: none; position: fixed; inset: 0; background: rgba(10, 14, 23, 0.88); backdrop-filter: blur(8px); z-index: 9999; align-items: center; justify-content: center;">
    <div class="card" style="width: 100%; max-width: 420px; padding: 2rem; border: 1px solid rgba(59, 130, 246, 0.3); box-shadow: 0 20px 40px rgba(0,0,0,0.7); text-align: center;">
      <div class="brand-logo" style="margin: 0 auto 0.75rem auto; width: 44px; height: 44px; font-size: 1.25rem;">₹</div>
      <h2 style="font-size: 1.2rem; font-weight: 600; color: var(--text-primary);">Personal IPO Platform</h2>
      <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.35rem; margin-bottom: 1.5rem;">Enter your Admin Key or Master Password to unlock your personal workspace</p>
      
      <div style="text-align: left; margin-bottom: 1rem;">
        <label style="display: block; font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 0.35rem; font-weight: 500;">Access Key / Password</label>
        <input type="password" id="modalKeyInput" class="auth-input" style="width: 100%; padding: 0.6rem 0.8rem; font-size: 0.85rem;" placeholder="e.g. key-admin-789 or personal password" onkeydown="if(event.key==='Enter') executeSignIn()">
      </div>
      <div id="loginModalError" style="display: none; color: var(--accent-red); font-size: 0.78rem; margin-bottom: 0.75rem; text-align: left;"></div>
      <button class="btn" style="width: 100%; justify-content: center; padding: 0.6rem; font-size: 0.85rem;" onclick="executeSignIn()" id="modalSignInBtn">Unlock Platform</button>
      <div style="margin-top: 1.25rem; font-size: 0.72rem; color: var(--text-muted);">
        Protected by JWT HMAC-SHA256 & RBAC authorization
      </div>
    </div>
  </div>

  <!-- Navigation Tabs -->
  <nav class="main-nav">
    <button class="nav-tab active" onclick="switchTab('iposTab', this)">IPO Offerings</button>
    <button class="nav-tab" id="wishlistNavTab" onclick="switchTab('wishlistTab', this); loadWishlist();">⭐ My Wishlist <span id="wishlistNavCount" class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; margin-left: 4px;">0</span></button>
    <button class="nav-tab" onclick="switchTab('recommendationTab', this)">Recommendation Engine</button>
    <button class="nav-tab" onclick="switchTab('portfolioTab', this)">Portfolio Allocator</button>
    <button class="nav-tab" onclick="switchTab('rhpTab', this)">Prospectus & Ingestion</button>
    <button class="nav-tab" onclick="switchTab('systemTab', this)">System Health & Telemetry</button>
  </nav>

  <!-- Main Content -->
  <main>
    <!-- SEBI Compliance Notice -->
    <div id="sebiDisclaimer" class="card" style="margin-bottom: 1.25rem; background: rgba(59, 130, 246, 0.08); border-left: 4px solid var(--accent-blue); padding: 0.85rem 1.25rem;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
        <div>
          <strong style="color: var(--accent-blue); font-size: 0.85rem;">⚖️ SEBI (Research Analysts) Regulations 2014 Compliance Notice:</strong>
          <p style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px; line-height: 1.4;">
            This platform delivers strictly quantitative factor scores, mathematical valuation multiples, and conditional scenario evaluations for research and analytical purposes only. It does NOT offer SEBI-registered investment advice, stock recommendations, or return guarantees. Investing in capital markets carries inherent risk of loss. Always consult a qualified SEBI-registered financial advisor and review the Red Herring Prospectus (RHP) filed with SEBI before making investment decisions.
          </p>
        </div>
        <button class="btn btn-secondary" style="font-size: 0.75rem; white-space: nowrap;" onclick="document.getElementById('sebiDisclaimer').style.display='none'">Acknowledge</button>
      </div>
    </div>

    <div id="alertBanner" class="alert alert-info" style="display: none;">
      <span id="alertMessage"></span>
      <button style="background:none;border:none;color:inherit;cursor:pointer;" onclick="hideAlert()">✕</button>
    </div>

    <!-- TAB 1: IPO Offerings -->
    <section id="iposTab" class="tab-content active">
      <div class="toolbar" style="gap: 0.6rem; align-items: center; flex-wrap: wrap;">
        <input type="text" id="ipoSearchInput" class="search-input" placeholder="Search company, symbol..." oninput="applyAllFilters()" style="min-width: 190px;">
        
        <select id="ipoStatusFilter" class="select-input" onchange="applyAllFilters()">
          <option value="">Status: All Open & Upcoming</option>
          <option value="Currently Open">Currently Open</option>
          <option value="Closing Today">Closing Today</option>
          <option value="Upcoming">Upcoming</option>
          <option value="wishlist_only">⭐ Wishlist Only</option>
        </select>

        <!-- 1. End Date Filter -->
        <select id="ipoEndDateFilter" class="select-input" onchange="applyAllFilters()" title="Filter by IPO Close / End Date">
          <option value="">📅 End Date: All</option>
          <option value="closing_today">⚡ Closing Today</option>
          <option value="next_3_days">⏳ Closing in Next 3 Days</option>
          <option value="next_7_days">🗓️ Closing in Next 7 Days</option>
          <option value="this_month">📅 Closing This Month</option>
          <option value="sort_asc">⬆️ Sort: End Date (Earliest)</option>
          <option value="sort_desc">⬇️ Sort: End Date (Latest)</option>
        </select>

        <!-- 2. Subscription Filter -->
        <select id="ipoSubFilter" class="select-input" onchange="applyAllFilters()" title="Filter by Subscription Multiple">
          <option value="">📊 Subscription: All</option>
          <option value="high_demand">🔥 High Demand (>= 3.0x)</option>
          <option value="oversubscribed">✅ Oversubscribed (>= 1.0x)</option>
          <option value="undersubscribed">⏳ Undersubscribed (&lt; 1.0x)</option>
          <option value="pre_apply">🟣 Pre-Apply Only</option>
          <option value="sort_desc">⬇️ Sort: Sub Multiple (High to Low)</option>
          <option value="sort_asc">⬆️ Sort: Sub Multiple (Low to High)</option>
        </select>

        <!-- 3. Grey Market (GMP) Filter -->
        <select id="ipoGmpFilter" class="select-input" onchange="applyAllFilters()" title="Filter by Grey Market Premium (GMP)">
          <option value="">💹 GMP: All</option>
          <option value="gmp_25_plus">🚀 High GMP (>= 25%)</option>
          <option value="gmp_15_plus">📈 Positive GMP (>= 15%)</option>
          <option value="has_gmp">🟢 Active GMP Available</option>
          <option value="no_gmp">⚪ GMP Not Active</option>
          <option value="sort_desc">⬇️ Sort: GMP % (High to Low)</option>
          <option value="sort_asc">⬆️ Sort: GMP % (Low to High)</option>
        </select>

        <button class="btn btn-secondary" onclick="resetAllFilters()" title="Reset all filters to default" style="padding: 0.45rem 0.75rem;">✕ Clear</button>
        <button class="btn btn-secondary" onclick="loadIPOs()" title="Refresh offerings">🔄 Refresh</button>
        <button class="btn" id="syncLiveBtn" onclick="syncLiveMarketData()" title="Fetch newest market feeds from NSE, BSE & GMP">⚡ Sync Feeds</button>
        
        <div id="lastSyncedContainer" style="display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.4rem 0.8rem; border-radius: var(--radius-sm); background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; font-size: 0.82rem; font-weight: 500; white-space: nowrap;">
          <span class="pulse-dot"></span>
          <span id="lastSyncedText">Updated at --:--:-- (-- offerings)</span>
        </div>
        <span id="offeringsCountBadge" style="display: none;">10 Offerings</span>

        <div class="view-switcher" style="margin-left: auto;">
          <button id="viewBtnTable" class="view-btn active" onclick="setViewMode('table')">📋 BSE Table</button>
          <button id="viewBtnCards" class="view-btn" onclick="setViewMode('cards')">🗂️ Cards</button>
        </div>
      </div>

      <!-- Segmented Section Switcher (All / Current IPOs / Pre-Apply) -->
      <div class="ipo-section-nav" style="display: flex; gap: 0.5rem; align-items: center; margin: 1rem 0 1.25rem 0; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border-color); flex-wrap: wrap;">
        <button id="ipoSecAllBtn" class="ipo-sec-pill active" onclick="switchIpoSection('all')">
          🔥 All Offerings (<span id="secCountAll">0</span>)
        </button>
        <button id="ipoSecCurrentBtn" class="ipo-sec-pill" onclick="switchIpoSection('current')">
          🟢 Current IPOs (<span id="secCountCurrent">0</span>)
        </button>
        <button id="ipoSecPreApplyBtn" class="ipo-sec-pill" onclick="switchIpoSection('pre_apply')">
          🟣 Pre-Apply (<span id="secCountPreApply">0</span>)
        </button>
      </div>

      <div id="iposLoading" style="text-align: center; padding: 3rem; color: var(--text-secondary);">Loading offerings from API...</div>

      <!-- SECTION 1: Current IPOs (Bidding Open) -->
      <div id="sectionCurrentIposBlock" class="ipo-section-block" style="margin-bottom: 2rem;">
        <div class="section-banner" style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 1rem; background: linear-gradient(90deg, rgba(16, 185, 129, 0.12) 0%, rgba(16, 185, 129, 0.03) 100%); border-left: 4px solid var(--accent-green); border-radius: var(--radius-sm); margin-bottom: 0.75rem; border: 1px solid rgba(16, 185, 129, 0.2); border-left-width: 4px;">
          <div style="display: flex; align-items: center; gap: 0.65rem;">
            <span style="font-size: 1.2rem;">🟢</span>
            <div>
              <div style="font-weight: 700; font-size: 0.98rem; color: #f8fafc; letter-spacing: -0.2px; display: flex; align-items: center; gap: 0.5rem;">
                Current IPOs
                <span class="badge badge-green" style="font-size: 0.68rem; padding: 0.15rem 0.45rem;"><span class="status-pulse pulse-green"></span>Bidding Open</span>
              </div>
              <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 1px;">
                Active public issues currently open for bidding on NSE &amp; BSE exchanges.
              </div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span id="currentIposHeaderBadge" class="brand-badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 0.78rem; font-weight: 600;">0 Open</span>
          </div>
        </div>

        <!-- Current IPOs BSE Table -->
        <div id="currentTableContainer" class="table-container" style="margin-top: 0;">
          <table class="market-table">
            <thead>
              <tr>
                <th onclick="toggleSort('company')" style="cursor: pointer;" title="Sort by Company Name">Security / Company Name <span data-sort-icon="company" id="sort_icon_company" style="font-size: 0.75rem; opacity: 0.7;">↕</span></th>
                <th>Platform</th>
                <th>Start Date</th>
                <th onclick="toggleSort('close_date')" style="cursor: pointer; color: #93c5fd;" title="Sort by Close / End Date">End Date <span data-sort-icon="close_date" id="sort_icon_close_date" style="font-size: 0.75rem; color: var(--accent-blue);">↕</span></th>
                <th>Allotment Date</th>
                <th>Listing Date</th>
                <th>Offer Price (₹)</th>
                <th onclick="toggleSort('size')" style="cursor: pointer;" title="Sort by Issue Size">Issue Size <span data-sort-icon="size" id="sort_icon_size" style="font-size: 0.75rem; opacity: 0.7;">↕</span></th>
                <th onclick="toggleSort('sub')" style="cursor: pointer; color: #93c5fd;" title="Sort by Subscription Multiple">Subscription <span data-sort-icon="sub" id="sort_icon_sub" style="font-size: 0.75rem; color: var(--accent-blue);">↕</span></th>
                <th onclick="toggleSort('gmp')" style="cursor: pointer; color: #93c5fd;" title="Sort by Grey Market (GMP)">Grey Market (GMP) <span data-sort-icon="gmp" id="sort_icon_gmp" style="font-size: 0.75rem; color: var(--accent-blue);">↕</span></th>
                <th>Issue Status</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="currentTableBody">
              <!-- Populated via renderIPOs -->
            </tbody>
          </table>
        </div>

        <!-- Current IPOs Cards Grid -->
        <div id="currentGrid" class="grid" style="display: none; margin-top: 0.75rem;"></div>

        <div id="currentEmpty" style="display: none; text-align: center; padding: 2.5rem 1.5rem; background: rgba(255, 255, 255, 0.02); border: 1px dashed var(--border-color); border-radius: var(--radius-md); color: var(--text-muted); margin-top: 0.5rem;">
          No open IPOs match the active filter criteria.
        </div>
      </div>

      <!-- SECTION 2: Pre-Apply (Upcoming Offerings) -->
      <div id="sectionPreApplyBlock" class="ipo-section-block" style="margin-top: 1.5rem; margin-bottom: 1.5rem;">
        <div class="section-banner" style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 1rem; background: linear-gradient(90deg, rgba(139, 92, 246, 0.12) 0%, rgba(139, 92, 246, 0.03) 100%); border-left: 4px solid var(--accent-purple); border-radius: var(--radius-sm); margin-bottom: 0.75rem; border: 1px solid rgba(139, 92, 246, 0.2); border-left-width: 4px;">
          <div style="display: flex; align-items: center; gap: 0.65rem;">
            <span style="font-size: 1.2rem;">🟣</span>
            <div>
              <div style="font-weight: 700; font-size: 0.98rem; color: #f8fafc; letter-spacing: -0.2px; display: flex; align-items: center; gap: 0.5rem;">
                Pre-Apply IPOs
                <span class="badge badge-purple" style="font-size: 0.68rem; padding: 0.15rem 0.45rem; font-weight: 600;">Advance Orders</span>
              </div>
              <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 1px;">
                Forthcoming offerings opening soon. Place pre-orders early before bidding opens on exchange.
              </div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span id="preApplyHeaderBadge" class="brand-badge" style="background: rgba(139, 92, 246, 0.2); color: #c4b5fd; font-size: 0.78rem; font-weight: 600;">0 Pre-Apply</span>
          </div>
        </div>

        <!-- Pre-Apply BSE Table -->
        <div id="preApplyTableContainer" class="table-container" style="margin-top: 0;">
          <table class="market-table">
            <thead>
              <tr>
                <th onclick="toggleSort('company')" style="cursor: pointer;" title="Sort by Company Name">Security / Company Name <span data-sort-icon="company" style="font-size: 0.75rem; opacity: 0.7;">↕</span></th>
                <th>Platform</th>
                <th>Start Date</th>
                <th onclick="toggleSort('close_date')" style="cursor: pointer; color: #93c5fd;" title="Sort by Close / End Date">End Date <span data-sort-icon="close_date" style="font-size: 0.75rem; color: var(--accent-blue);">↕</span></th>
                <th>Allotment Date</th>
                <th>Listing Date</th>
                <th>Offer Price (₹)</th>
                <th onclick="toggleSort('size')" style="cursor: pointer;" title="Sort by Issue Size">Issue Size <span data-sort-icon="size" style="font-size: 0.75rem; opacity: 0.7;">↕</span></th>
                <th onclick="toggleSort('sub')" style="cursor: pointer; color: #93c5fd;" title="Sort by Subscription Multiple">Subscription <span data-sort-icon="sub" style="font-size: 0.75rem; color: var(--accent-blue);">↕</span></th>
                <th onclick="toggleSort('gmp')" style="cursor: pointer; color: #93c5fd;" title="Sort by Grey Market (GMP)">Grey Market (GMP) <span data-sort-icon="gmp" style="font-size: 0.75rem; color: var(--accent-blue);">↕</span></th>
                <th>Issue Status</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="preApplyTableBody">
              <!-- Populated via renderIPOs -->
            </tbody>
          </table>
        </div>

        <!-- Pre-Apply Cards Grid -->
        <div id="preApplyGrid" class="grid" style="display: none; margin-top: 0.75rem;"></div>

        <div id="preApplyEmpty" style="display: none; text-align: center; padding: 2.5rem 1.5rem; background: rgba(255, 255, 255, 0.02); border: 1px dashed var(--border-color); border-radius: var(--radius-md); color: var(--text-muted); margin-top: 0.5rem;">
          No upcoming / pre-apply offerings match the active filter criteria.
        </div>
      </div>

      <!-- Hidden fallback containers to guarantee backwards compatibility -->
      <div id="iposTableContainer" style="display: none;"></div>
      <div id="iposTableBody" style="display: none;"></div>
      <div id="iposGrid" style="display: none;"></div>

      <div id="iposEmpty" style="display: none; text-align: center; padding: 3rem; color: var(--text-secondary);">No active offerings matched the filter.</div>
    </section>

    <!-- TAB: My Wishlist & Post-Listing History (Saved in Database) -->
    <section id="wishlistTab" class="tab-content">
      <div class="card" style="margin-bottom: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div>
            <h3 style="display: flex; align-items: center; gap: 0.5rem; font-size: 1.2rem; font-weight: 600;">
              <span>⭐</span> Wishlist &amp; Post-Listing History
            </h3>
            <p style="color: var(--text-secondary); font-size: 0.82rem; margin-top: 3px;">
              Track bookmarked offerings and post-listing returns in MySQL (<code style="color: #60a5fa;">user_wishlist</code> &amp; <code style="color: #34d399;">user_wishlist_history</code> tables).
            </p>
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
            <button class="btn btn-secondary" onclick="syncWishlistHistoryAndNotify()">🔄 Sync Listed IPOs</button>
            <button class="btn btn-secondary" onclick="refreshCurrentWishlistView()">🔄 Refresh</button>
            <button class="btn" onclick="openRecordListingPricePrompt()">➕ Record Listing Price</button>
          </div>
        </div>

        <!-- Sub-view navigation pills: Active Wishlist vs Listed History -->
        <div style="display: flex; gap: 0.5rem; margin-top: 1.25rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
          <button 
            id="pillActiveWishlist" 
            class="btn" 
            style="padding: 0.45rem 1rem; font-size: 0.85rem; display: flex; align-items: center; gap: 0.4rem;" 
            onclick="switchWishlistView('active')">
            📌 Active Tracked IPOs <span id="activeWishlistBadge" class="badge" style="background: rgba(255,255,255,0.15); color: #fff; padding: 0.15rem 0.45rem;">0</span>
          </button>
          <button 
            id="pillListedHistory" 
            class="btn btn-secondary" 
            style="padding: 0.45rem 1rem; font-size: 0.85rem; display: flex; align-items: center; gap: 0.4rem;" 
            onclick="switchWishlistView('history')">
            📜 Post-Listing History <span id="listedHistoryBadge" class="badge badge-green" style="padding: 0.15rem 0.45rem;">0</span>
          </button>
        </div>
      </div>

      <!-- Loading Indicator -->
      <div id="wishlistLoading" style="text-align: center; padding: 2.5rem; color: var(--text-secondary); display: none;">Loading data from database...</div>

      <!-- VIEW 1: Active Wishlist Data Table -->
      <div id="activeWishlistView">
        <div id="wishlistTableContainer" class="table-container" style="display: none;">
          <table class="market-table">
            <thead>
              <tr>
                <th>Security / Company Name</th>
                <th>Platform</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Allotment Date</th>
                <th>Listing Date</th>
                <th>Offer Price (₹)</th>
                <th>Issue Size</th>
                <th>Subscription</th>
                <th>Grey Market (GMP)</th>
                <th>Status</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="wishlistTableBody">
              <!-- Populated via renderWishlist -->
            </tbody>
          </table>
        </div>

        <!-- Empty state for Active Wishlist -->
        <div id="wishlistEmpty" class="card" style="display: none; text-align: center; padding: 3rem 1.5rem; margin-top: 1rem;">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">⭐</div>
          <h4 style="font-size: 1.1rem; margin-bottom: 0.35rem;">Your Active Wishlist is Empty</h4>
          <p style="color: var(--text-secondary); font-size: 0.85rem; max-width: 480px; margin: 0 auto 1.25rem auto;">
            Click the <strong>☆ Add to Wish</strong> button on any offering in the IPO Offerings tab to save it directly into the MySQL database.
          </p>
          <button class="btn" onclick="switchTab('iposTab', document.querySelectorAll('.nav-tab')[0])">Browse IPO Offerings</button>
        </div>
      </div>

      <!-- VIEW 2: Post-Listing History Table with Listing Price & Gains -->
      <div id="listedHistoryView" style="display: none;">
        <div id="historyTableContainer" class="table-container" style="display: none;">
          <table class="market-table">
            <thead>
              <tr>
                <th>Security / Company Name</th>
                <th>Listing Date</th>
                <th>Issue Price (₹)</th>
                <th style="color: #60a5fa;">Listing Price (₹)</th>
                <th style="color: #34d399;">Listing Gain / Return (%)</th>
                <th>Day Close (₹)</th>
                <th>Status</th>
                <th>Bookmarked On</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="historyTableBody">
              <!-- Populated via renderWishlistHistory -->
            </tbody>
          </table>
        </div>

        <!-- Empty state for History -->
        <div id="historyEmpty" class="card" style="display: none; text-align: center; padding: 3rem 1.5rem; margin-top: 1rem;">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📜</div>
          <h4 style="font-size: 1.1rem; margin-bottom: 0.35rem;">No Post-Listing History Recorded Yet</h4>
          <p style="color: var(--text-secondary); font-size: 0.85rem; max-width: 520px; margin: 0 auto 1.25rem auto;">
            When IPO offerings you've added to your wishlist reach their listing date or are closed and listed, they are saved here automatically with their actual listing prices and gain percentages.
          </p>
          <div style="display: flex; justify-content: center; gap: 0.75rem;">
            <button class="btn" onclick="syncWishlistHistoryAndNotify()">🔄 Scan &amp; Sync Listed Offerings</button>
            <button class="btn btn-secondary" onclick="openRecordListingPricePrompt()">➕ Enter Listing Price Manually</button>
          </div>
        </div>
      </div>
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

    <!-- TAB 4: System Health & Market Scheduler -->
    <section id="systemTab" class="tab-content">
      <!-- 1. Live Feed Health & Network Latency Card (Phase 2) -->
      <div class="card" style="margin-bottom: 1.5rem;">
        <div class="card-header">
          <div>
            <h3 class="card-title">📡 Upstream Market Feeds & Network Latency</h3>
            <div class="card-subtitle">Live real-time connectivity probes and round-trip ping latency</div>
          </div>
          <button class="btn btn-secondary" onclick="pollFeedHealth(true); loadFeedHealthTab();">⚡ Ping Feeds Now</button>
        </div>
        
        <div id="feedHealthCardsGrid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin-top: 1rem;">
          <!-- BSE India -->
          <div class="card" style="padding: 1rem; border: 1px solid var(--border-color); background: rgba(255,255,255,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <strong style="font-size: 0.95rem;">BSE India</strong>
              <span id="tabFeedBadgeBSE" class="badge badge-green">ONLINE</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 700; color: #34d399;" id="tabFeedLatencyBSE">-- ms</div>
            <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 0.25rem;" id="tabFeedDetailsBSE">Public Issue API • HTTP 200</div>
            <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.5rem;" id="tabFeedCheckBSE">Last probed: Just now</div>
          </div>

          <!-- NSE India -->
          <div class="card" style="padding: 1rem; border: 1px solid var(--border-color); background: rgba(255,255,255,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <strong style="font-size: 0.95rem;">NSE India</strong>
              <span id="tabFeedBadgeNSE" class="badge badge-green">ONLINE</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 700; color: #34d399;" id="tabFeedLatencyNSE">-- ms</div>
            <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 0.25rem;" id="tabFeedDetailsNSE">Current Issues API • HTTP 200</div>
            <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.5rem;" id="tabFeedCheckNSE">Last probed: Just now</div>
          </div>

          <!-- InvestorGain GMP -->
          <div class="card" style="padding: 1rem; border: 1px solid var(--border-color); background: rgba(255,255,255,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <strong style="font-size: 0.95rem;">InvestorGain GMP</strong>
              <span id="tabFeedBadgeGMP" class="badge badge-green">ONLINE</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 700; color: #34d399;" id="tabFeedLatencyGMP">-- ms</div>
            <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 0.25rem;" id="tabFeedDetailsGMP">Grey Market Discovery • HTTP 200</div>
            <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.5rem;" id="tabFeedCheckGMP">Last probed: Just now</div>
          </div>
        </div>
      </div>

      <!-- 2. Market Hours Auto-Scheduler & Audit History (Phase 1) -->
      <div class="card" style="margin-bottom: 1.5rem;">
        <div class="card-header">
          <div>
            <h3 class="card-title">⏰ Market Hours Auto-Scheduler (09:15, 13:00, 17:00 IST)</h3>
            <div class="card-subtitle">Automated multi-source sync runs 3 times daily on market trading days with database audit trails</div>
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <button class="btn" onclick="triggerManualMarketSync()" id="btnTriggerMarketSync">⚡ Trigger Sync Now</button>
            <button class="btn btn-secondary" onclick="loadSchedulerHistory()">🔄 Refresh History</button>
          </div>
        </div>

        <div style="display: flex; gap: 0.75rem; margin: 1rem 0; flex-wrap: wrap;">
          <div style="display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.4rem 0.8rem; border-radius: var(--radius-sm); background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); color: #93c5fd; font-size: 0.8rem; font-weight: 500;">
            <span class="chip-dot dot-green"></span> Slot 1: 09:15 IST (Market Open)
          </div>
          <div style="display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.4rem 0.8rem; border-radius: var(--radius-sm); background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); color: #93c5fd; font-size: 0.8rem; font-weight: 500;">
            <span class="chip-dot dot-green"></span> Slot 2: 13:00 IST (Mid-Day Momentum)
          </div>
          <div style="display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.4rem 0.8rem; border-radius: var(--radius-sm); background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); color: #93c5fd; font-size: 0.8rem; font-weight: 500;">
            <span class="chip-dot dot-green"></span> Slot 3: 17:00 IST (Market Close Final)
          </div>
        </div>

        <div id="schedulerSyncStatusMsg" style="display: none; padding: 0.6rem 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem; font-size: 0.82rem;"></div>

        <div style="font-size: 0.88rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Execution Audit Log (Table: scheduled_job_executions)</div>
        <div class="table-container" style="max-height: 280px; overflow-y: auto;">
          <table class="market-table">
            <thead>
              <tr>
                <th>Job Identifier</th>
                <th>Execution Date</th>
                <th>Started At</th>
                <th>Completed At</th>
                <th>Status</th>
                <th>Node ID</th>
                <th>Error Details</th>
              </tr>
            </thead>
            <tbody id="schedulerHistoryTableBody">
              <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Loading execution history...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. Subsystem Diagnostic Probes -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">System Diagnostic Health Probes</h3>
            <div class="card-subtitle">Platform infrastructure, memory, disk, and database connectivity</div>
          </div>
          <button class="btn btn-secondary" onclick="loadHealth()">Run Subsystem Probes</button>
        </div>
        <div id="healthStatusBanner" style="margin: 1rem 0; font-size: 0.9rem;"></div>
        <div id="healthChecksList"></div>
      </div>
    </section>

    <!-- TAB 5: Prospectus (RHP) & Ingestion -->
    <section id="rhpTab" class="tab-content">
      <div class="card" style="margin-bottom: 1.5rem;">
        <h3 style="margin-bottom: 0.75rem;">SEBI Prospectus (DRHP / RHP) Automated Parser & Ingestion</h3>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
          Paste raw document excerpt or text from an official SEBI filing to automatically extract corporate identity, price bands, issue size, 3-year restated financials, objects of the issue, and primary risk factors.
        </p>
        <textarea id="rhpTextInput" class="search-input" style="width: 100%; height: 160px; font-family: monospace; font-size: 0.8rem; padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 1rem;" placeholder="Paste DRHP / RHP text excerpt here..."></textarea>
        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
          <label style="font-size: 0.85rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
            <input type="checkbox" id="rhpDirectIngest" checked> Persist Directly into Relational Database (MySQL)
          </label>
          <button class="btn" onclick="parseRhpFiling()">Parse & Extract Prospectus</button>
          <button class="btn btn-secondary" onclick="loadSampleRhp()">Load Sample Filing Text</button>
        </div>
      </div>

      <div id="rhpResultCard" class="card" style="display: none;">
        <div class="card-header">
          <div>
            <h2 id="rhpCompanyName" class="card-title"></h2>
            <div id="rhpIpoId" class="card-subtitle"></div>
          </div>
          <span id="rhpBadge" class="badge badge-green">EXTRACTED & VALIDATED</span>
        </div>
        <div id="rhpDetailsContent"></div>
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

  <!-- Listing Price & History Modal -->
  <div id="listingPriceModal" class="modal-overlay" onclick="closeListingPriceModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()" style="max-width: 520px;">
      <div class="modal-header">
        <div>
          <h2 id="lpModalTitle" style="font-size: 1.25rem; font-weight: 600;">Record Listing Price</h2>
          <div id="lpModalSubtitle" style="font-size: 0.8rem; color: var(--text-secondary);">Save actual market outcome in MySQL history</div>
        </div>
        <button class="modal-close" onclick="closeListingPriceModalDirect()">&times;</button>
      </div>
      <div style="padding: 1rem 0 0 0;">
        <input type="hidden" id="lpHiddenIpoId">
        
        <div style="margin-bottom: 1rem;">
          <label style="display: block; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Company Name / Offering</label>
          <input type="text" id="lpCompanyName" readonly style="width: 100%; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(255,255,255,0.03); color: var(--text-primary); font-size: 0.9rem;" />
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 1rem;">
          <div>
            <label style="display: block; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Issue Price (₹)</label>
            <input type="number" step="0.05" id="lpIssuePrice" placeholder="e.g. 289.00" oninput="calculateModalGain()" style="width: 100%; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary); font-size: 0.9rem;" />
          </div>
          <div>
            <label style="display: block; font-size: 0.8rem; color: #60a5fa; font-weight: 600; margin-bottom: 0.35rem;">Listing Price (₹) *</label>
            <input type="number" step="0.05" id="lpListingPrice" placeholder="e.g. 345.00" oninput="calculateModalGain()" style="width: 100%; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid #3b82f6; background: var(--bg-card); color: #93c5fd; font-weight: 600; font-size: 0.95rem;" />
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 1rem;">
          <div>
            <label style="display: block; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Day Close Price (₹)</label>
            <input type="number" step="0.05" id="lpDayClose" placeholder="e.g. 352.00" style="width: 100%; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary); font-size: 0.9rem;" />
          </div>
          <div>
            <label style="display: block; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Listing Date</label>
            <input type="date" id="lpListingDate" style="width: 100%; padding: 0.55rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary); font-size: 0.85rem;" />
          </div>
        </div>

        <!-- Live Gain Preview Pill -->
        <div id="lpGainPreviewCard" class="card" style="padding: 0.75rem 1rem; margin-bottom: 1rem; background: rgba(59, 130, 246, 0.08); border-color: rgba(59, 130, 246, 0.25); display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.85rem; color: var(--text-secondary);">Calculated Listing Gain / Return:</span>
          <span id="lpCalculatedGainBadge" class="badge badge-green" style="font-size: 0.9rem; padding: 0.35rem 0.75rem;">+0.00%</span>
        </div>

        <div style="margin-bottom: 1rem;">
          <label style="display: block; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Notes & Observations</label>
          <textarea id="lpNotes" rows="2" placeholder="e.g. Strong institutional demand, listed at 19% premium above issue price." style="width: 100%; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary); font-size: 0.85rem; resize: vertical;"></textarea>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.25rem;">
          <button class="btn btn-secondary" onclick="closeListingPriceModalDirect()">Cancel</button>
          <button class="btn" onclick="submitListingPriceModal()" id="lpSubmitBtn">💾 Save to History Database</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Disclaimer Footer -->
  <footer>
    <strong>MANDATORY DISCLAIMER:</strong> This platform is strictly an independent analytical decision-support and research engine. 
    It does not execute automated trading, guarantee returns, or provide financial investment advice. Public IPO investments involve substantial market risk.
  </footer>

  <!-- Dashboard JavaScript -->
  <script>
    let activeToken = localStorage.getItem("ipo_platform_auth") || "key-admin-789";
    let cachedIPOs = [];
    let currentViewMode = localStorage.getItem("ipo_view_mode") || "table";
    let lastSyncedTimeStr = "";

    document.addEventListener("DOMContentLoaded", () => {
      setViewMode(currentViewMode);
      checkAuthAndInit();
      pollFeedHealth();
      setInterval(() => pollFeedHealth(false), 30000);
    });

    async function checkAuthAndInit() {
      setViewMode(currentViewMode);
      if (!activeToken) {
        openLoginModal();
        return;
      }
      try {
        const resp = await fetch("/auth/me", { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          document.getElementById("userStatusBadge").innerText = `🟢 ${data.role} Access`;
          document.getElementById("authStatusIndicator").style.display = "flex";
          document.getElementById("signInHeaderBtn").style.display = "none";
          closeLoginModal();
          loadIPOs();
          loadHealth();
          pollFeedHealth();
          loadSchedulerHistory();
          syncWishlistFromDb();
          loadWishlist();
        } else {
          openLoginModal();
        }
      } catch (e) {
        // Fallback for isolated local testing
        loadIPOs();
        loadHealth();
        pollFeedHealth();
        loadSchedulerHistory();
        syncWishlistFromDb();
        loadWishlist();
      }
    }

    function openLoginModal() {
      const modal = document.getElementById("loginModal");
      if (modal) {
        modal.style.display = "flex";
        document.getElementById("authStatusIndicator").style.display = "none";
        document.getElementById("signInHeaderBtn").style.display = "inline-flex";
        setTimeout(() => document.getElementById("modalKeyInput")?.focus(), 100);
      }
    }

    function closeLoginModal() {
      const modal = document.getElementById("loginModal");
      if (modal) modal.style.display = "none";
    }

    async function executeSignIn() {
      const keyVal = document.getElementById("modalKeyInput").value.trim();
      const errBox = document.getElementById("loginModalError");
      if (!keyVal) {
        errBox.innerText = "Please enter an access key or password.";
        errBox.style.display = "block";
        return;
      }
      errBox.style.display = "none";
      try {
        const resp = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key_or_password: keyVal }),
        });
        if (resp.ok) {
          const data = await resp.json();
          activeToken = data.access_token;
          localStorage.setItem("ipo_platform_auth", activeToken);
          document.getElementById("userStatusBadge").innerText = `🟢 ${data.role} Access`;
          document.getElementById("authStatusIndicator").style.display = "flex";
          document.getElementById("signInHeaderBtn").style.display = "none";
          closeLoginModal();
          showAlert(`Welcome! Authenticated with ${data.role} permissions.`, "success");
          loadIPOs();
          loadHealth();
        } else {
          const errData = await resp.json().catch(() => ({}));
          errBox.innerText = errData.detail || "Authentication failed: Invalid credentials.";
          errBox.style.display = "block";
        }
      } catch (err) {
        errBox.innerText = `Network error: ${err.message}`;
        errBox.style.display = "block";
      }
    }

    function signOutPlatform() {
      activeToken = "";
      localStorage.removeItem("ipo_platform_auth");
      openLoginModal();
      showAlert("You have signed out from the platform.", "info");
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
      if (tabId === "systemTab") {
        pollFeedHealth(false);
        loadSchedulerHistory();
        loadHealth();
      }
    }

    /* Upstream Feeds Health & Latency Logic (Phase 2) */
    async function pollFeedHealth(forceRefresh = false) {
      try {
        const url = `/health/feeds${forceRefresh ? '?force_refresh=true' : ''}`;
        const resp = await fetch(url);
        if (!resp.ok) {
          updateFeedChip('chipBSE', 'BSE', 'unhealthy', null, `HTTP ${resp.status}`);
          updateFeedChip('chipNSE', 'NSE', 'unhealthy', null, `HTTP ${resp.status}`);
          updateFeedChip('chipGMP', 'GMP', 'unhealthy', null, `HTTP ${resp.status}`);
          showFeedAlert(`Upstream feed health endpoint returned HTTP ${resp.status}`);
          return;
        }
        const data = await resp.json();
        const feeds = data.feeds || {};
        let errors = [];

        if (feeds.bse) {
          const f = feeds.bse;
          updateFeedChip('chipBSE', 'BSE', f.status, f.latency_ms, f.error, f.http_code, f.last_check);
          if (f.status !== 'healthy') errors.push(`BSE India: ${f.error || 'Connection Failed'}`);
        }
        if (feeds.nse) {
          const f = feeds.nse;
          updateFeedChip('chipNSE', 'NSE', f.status, f.latency_ms, f.error, f.http_code, f.last_check);
          if (f.status !== 'healthy') errors.push(`NSE India: ${f.error || 'Connection Failed'}`);
        }
        if (feeds.gmp) {
          const f = feeds.gmp;
          updateFeedChip('chipGMP', 'GMP', f.status, f.latency_ms, f.error, f.http_code, f.last_check);
          if (f.status !== 'healthy') errors.push(`InvestorGain GMP: ${f.error || 'Connection Failed'}`);
        }

        if (errors.length > 0) {
          showFeedAlert(`Upstream Feed Warning: ${errors.join(' | ')}`);
        } else {
          dismissFeedAlert();
        }

        updateSystemTabFeedCards(feeds);
      } catch (err) {
        console.warn('Feed health polling error:', err);
      }
    }

    function updateFeedChip(chipId, label, status, latencyMs, errorMsg, httpCode, lastCheck) {
      const el = document.getElementById(chipId);
      if (!el) return;
      el.className = 'feed-chip';
      if (status === 'healthy') {
        el.classList.add('chip-healthy');
        el.innerHTML = `<span class="chip-dot dot-green"></span> ${label}: <span class="chip-latency">${Math.round(latencyMs)}ms</span>`;
        el.title = `${label} Live (200 OK) • Latency: ${latencyMs}ms • Last checked: ${lastCheck || 'Just now'}`;
      } else {
        el.classList.add('chip-unhealthy');
        const codeSuffix = httpCode ? ` (${httpCode})` : '';
        el.innerHTML = `<span class="chip-dot dot-red"></span> ${label}: Offline${codeSuffix}`;
        el.title = `${label} Offline • ${errorMsg || 'Timeout/Error'} • Click to re-probe`;
      }
    }

    function updateSystemTabFeedCards(feeds) {
      if (feeds.bse) {
        const f = feeds.bse;
        const latEl = document.getElementById('tabFeedLatencyBSE');
        const badgeEl = document.getElementById('tabFeedBadgeBSE');
        const detEl = document.getElementById('tabFeedDetailsBSE');
        const chkEl = document.getElementById('tabFeedCheckBSE');
        if (latEl) latEl.innerText = `${Math.round(f.latency_ms)} ms`;
        if (badgeEl) {
          badgeEl.className = f.status === 'healthy' ? 'badge badge-green' : 'badge badge-red';
          badgeEl.innerText = f.status === 'healthy' ? 'ONLINE (200 OK)' : (f.http_code ? `HTTP ${f.http_code}` : 'OFFLINE');
        }
        if (detEl) detEl.innerText = `Public Issue API • ${f.items_count || 0} issues detected`;
        if (chkEl) chkEl.innerText = `Last probed: ${f.last_check || 'Just now'}`;
      }
      if (feeds.nse) {
        const f = feeds.nse;
        const latEl = document.getElementById('tabFeedLatencyNSE');
        const badgeEl = document.getElementById('tabFeedBadgeNSE');
        const detEl = document.getElementById('tabFeedDetailsNSE');
        const chkEl = document.getElementById('tabFeedCheckNSE');
        if (latEl) latEl.innerText = `${Math.round(f.latency_ms)} ms`;
        if (badgeEl) {
          badgeEl.className = f.status === 'healthy' ? 'badge badge-green' : 'badge badge-red';
          badgeEl.innerText = f.status === 'healthy' ? 'ONLINE (200 OK)' : (f.http_code ? `HTTP ${f.http_code}` : 'OFFLINE');
        }
        if (detEl) detEl.innerText = `Current Issues API • ${f.items_count || 0} issues detected`;
        if (chkEl) chkEl.innerText = `Last probed: ${f.last_check || 'Just now'}`;
      }
      if (feeds.gmp) {
        const f = feeds.gmp;
        const latEl = document.getElementById('tabFeedLatencyGMP');
        const badgeEl = document.getElementById('tabFeedBadgeGMP');
        const detEl = document.getElementById('tabFeedDetailsGMP');
        const chkEl = document.getElementById('tabFeedCheckGMP');
        if (latEl) latEl.innerText = `${Math.round(f.latency_ms)} ms`;
        if (badgeEl) {
          badgeEl.className = f.status === 'healthy' ? 'badge badge-green' : 'badge badge-red';
          badgeEl.innerText = f.status === 'healthy' ? 'ONLINE (200 OK)' : (f.http_code ? `HTTP ${f.http_code}` : 'OFFLINE');
        }
        if (detEl) detEl.innerText = `Grey Market Discovery • ${f.items_count || 0} quotes scraped`;
        if (chkEl) chkEl.innerText = `Last probed: ${f.last_check || 'Just now'}`;
      }
    }

    function showFeedAlert(msg) {
      const banner = document.getElementById('feedAlertBanner');
      const text = document.getElementById('feedAlertMessage');
      if (banner && text) {
        text.innerText = msg;
        banner.style.display = 'flex';
      }
    }

    function dismissFeedAlert() {
      const banner = document.getElementById('feedAlertBanner');
      if (banner) banner.style.display = 'none';
    }

    function loadFeedHealthTab() {
      pollFeedHealth(false);
    }

    /* Market Hours Auto-Scheduler History & Triggers (Phase 1) */
    async function loadSchedulerHistory() {
      const tbody = document.getElementById('schedulerHistoryTableBody');
      if (!tbody) return;
      try {
        const resp = await fetch('/scheduler/history?limit=15', { headers: getAuthHeaders() });
        if (!resp.ok) {
          tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--accent-red); padding: 1rem;">Failed to load scheduler history (${resp.status})</td></tr>`;
          return;
        }
        const data = await resp.json();
        const execs = data.executions || [];
        if (execs.length === 0) {
          tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No scheduled execution records found in scheduled_job_executions. Trigger one above!</td></tr>`;
          return;
        }
        tbody.innerHTML = execs.map(e => {
          let badgeClass = 'badge-yellow';
          if (e.execution_status === 'COMPLETED') badgeClass = 'badge-green';
          else if (e.execution_status === 'FAILED') badgeClass = 'badge-red';
          else if (e.execution_status === 'SKIPPED') badgeClass = 'badge-purple';

          return `
            <tr>
              <td><strong style="color: #93c5fd;">${escapeHtml(e.job_name)}</strong></td>
              <td>${escapeHtml(e.execution_date)}</td>
              <td style="font-size: 0.76rem; color: var(--text-secondary);">${escapeHtml(e.started_at ? e.started_at.replace('T', ' ').substring(0, 19) : '--')}</td>
              <td style="font-size: 0.76rem; color: var(--text-secondary);">${escapeHtml(e.completed_at ? e.completed_at.replace('T', ' ').substring(0, 19) : '--')}</td>
              <td><span class="badge ${badgeClass}">${escapeHtml(e.execution_status)}</span></td>
              <td style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(e.node_id)}</td>
              <td style="font-size: 0.75rem; color: ${e.error_message ? 'var(--accent-red)' : 'var(--text-muted)'}; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(e.error_message || '')}">${escapeHtml(e.error_message || 'None')}</td>
            </tr>
          `;
        }).join('');
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--accent-red); padding: 1rem;">Error: ${escapeHtml(err.message)}</td></tr>`;
      }
    }

    async function triggerManualMarketSync() {
      const btn = document.getElementById('btnTriggerMarketSync');
      const msgBox = document.getElementById('schedulerSyncStatusMsg');
      if (btn) {
        btn.disabled = true;
        btn.innerText = '⏳ Syncing Live Feeds...';
      }
      if (msgBox) {
        msgBox.style.display = 'block';
        msgBox.style.background = 'rgba(59, 130, 246, 0.12)';
        msgBox.style.color = '#93c5fd';
        msgBox.style.border = '1px solid rgba(59, 130, 246, 0.3)';
        msgBox.innerText = 'Triggering on-demand market hours sync across BSE, NSE, and GMP...';
      }
      try {
        const resp = await fetch('/scheduler/trigger-sync?force_weekend=true', {
          method: 'POST',
          headers: getAuthHeaders(),
        });
        const res = await resp.json();
        if (resp.ok && res.status === 'COMPLETED') {
          msgBox.style.background = 'rgba(16, 185, 129, 0.12)';
          msgBox.style.color = '#34d399';
          msgBox.style.border = '1px solid rgba(16, 185, 129, 0.3)';
          msgBox.innerText = `✅ Sync COMPLETED in ${res.duration_seconds}s! Ingested/updated ${res.master_records_ingested} offerings, recorded ${res.gmp_quotes_recorded} GMP quotes. Saved to MySQL.`;
          loadSchedulerHistory();
          loadIPOs(false);
          pollFeedHealth(true);
        } else {
          msgBox.style.background = 'rgba(239, 68, 68, 0.12)';
          msgBox.style.color = '#fca5a5';
          msgBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
          msgBox.innerText = `⚠️ Sync finished with status: ${res.status}. ${res.errors ? res.errors.join('; ') : ''}`;
          loadSchedulerHistory();
        }
      } catch (err) {
        if (msgBox) {
          msgBox.style.background = 'rgba(239, 68, 68, 0.12)';
          msgBox.style.color = '#fca5a5';
          msgBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
          msgBox.innerText = `Error triggering sync: ${err.message}`;
        }
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = '⚡ Trigger Sync Now';
        }
      }
    }

    async function loadIPOs(showLoading = true) {
      const loading = document.getElementById("iposLoading");
      const empty = document.getElementById("iposEmpty");
      const statusFilter = document.getElementById("ipoStatusFilter").value;

      if (showLoading) {
        if (loading) loading.style.display = "block";
        const curBlock = document.getElementById("sectionCurrentIposBlock");
        const preBlock = document.getElementById("sectionPreApplyBlock");
        if (curBlock) curBlock.style.display = "none";
        if (preBlock) preBlock.style.display = "none";
        if (empty) empty.style.display = "none";
      }

      try {
        let url = `/ipos?limit=100`;
        if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;
        
        const res = await fetch(url, { headers: getAuthHeaders() });
        if (!res.ok) {
          if (res.status === 401) {
            openLoginModal();
            return;
          }
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`Failed to fetch IPOs: ${err.detail || res.statusText}`, "error");
          loading.style.display = "none";
          return;
        }

        const data = await res.json();
        const rawItems = data.items || [];
        const marketTodayStr = (new Date().getFullYear() >= 2026) ? new Date().toISOString().split("T")[0] : "2026-10-19";
        cachedIPOs = rawItems.filter(ipo => {
          const s = (ipo.status || "").toLowerCase();
          if (s.includes("closed") || s.includes("listed")) return false;
          if (ipo.close_date && String(ipo.close_date).split("T")[0] < marketTodayStr) return false;
          if (ipo.allotment_date && String(ipo.allotment_date).split("T")[0] < marketTodayStr && (!ipo.close_date || String(ipo.close_date).split("T")[0] <= marketTodayStr)) return false;
          if (ipo.listing_date && String(ipo.listing_date).split("T")[0] <= marketTodayStr) return false;
          return true;
        });
        lastSyncedTimeStr = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }).toLowerCase();
        applyAllFilters();

        const lastSyncElem = document.getElementById("lastSyncedText");
        if (lastSyncElem) {
          lastSyncElem.innerText = `Updated at ${lastSyncedTimeStr} (${cachedIPOs.length} offerings)`;
        }
      } catch (e) {
        if (showLoading) showAlert(`Network error loading IPOs: ${e.message}`, "error");
      } finally {
        loading.style.display = "none";
      }
    }

    async function syncLiveMarketData() {
      const btn = document.getElementById("syncLiveBtn");
      if (btn) {
        btn.disabled = true;
        btn.innerText = "⏳ Syncing NSE/BSE/GMP...";
      }
      try {
        const resp = await fetch("/ipos/sync", {
          method: "POST",
          headers: getAuthHeaders(),
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.errors && data.errors.length > 0) {
            showAlert(`Live Market Sync Notice (${data.records_persisted} updated): ${data.errors.join('; ')}`, "error");
          } else {
            showAlert(`Live Market Sync Completed! ${data.records_persisted} offerings updated from NSE/BSE/GMP with 0 errors.`, "success");
          }
          await loadIPOs(false);
        } else if (resp.status === 401) {
          openLoginModal();
        } else {
          const errData = await resp.json().catch(() => ({}));
          showAlert(`Sync issue: ${errData.detail || 'Could not fetch live feeds'}`, "error");
        }
      } catch (err) {
        showAlert(`Sync failed: ${err.message}`, "error");
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = "🔄 Sync Live Market Feeds";
        }
      }
    }

    // Auto-refresh data when user switches back to the tab or periodically every 60s
    window.addEventListener("focus", () => {
      if (activeToken) {
        loadIPOs(false);
      }
    });

    setInterval(() => {
      if (activeToken && document.visibilityState === "visible") {
        loadIPOs(false);
      }
    }, 60000);

    function setViewMode(mode) {
      currentViewMode = mode;
      localStorage.setItem("ipo_view_mode", mode);

      const btnTable = document.getElementById("viewBtnTable");
      const btnCards = document.getElementById("viewBtnCards");
      const curTable = document.getElementById("currentTableContainer");
      const curGrid = document.getElementById("currentGrid");
      const preTable = document.getElementById("preApplyTableContainer");
      const preGrid = document.getElementById("preApplyGrid");

      if (btnTable && btnCards) {
        if (mode === "table") {
          btnTable.classList.add("active");
          btnCards.classList.remove("active");
        } else {
          btnCards.classList.add("active");
          btnTable.classList.remove("active");
        }
      }

      if (curTable && curGrid) {
        if (mode === "table") {
          curTable.style.display = "block";
          curGrid.style.display = "none";
        } else {
          curTable.style.display = "none";
          curGrid.style.display = "grid";
        }
      }

      if (preTable && preGrid) {
        if (mode === "table") {
          preTable.style.display = "block";
          preGrid.style.display = "none";
        } else {
          preTable.style.display = "none";
          preGrid.style.display = "grid";
        }
      }
    }

    const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    function formatMarketDate(dStr) {
      if (!dStr) return "TBA";
      const clean = String(dStr).split("T")[0].trim();
      const ymd = clean.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (ymd) {
        const d = parseInt(ymd[3], 10);
        const m = parseInt(ymd[2], 10) - 1;
        const y = ymd[1];
        return `${d} ${MONTH_NAMES[m] || ymd[2]} ${y}`;
      }
      return clean;
    }

    function getStatusBadge(status) {
      const s = (status || "").toLowerCase();
      if (s.includes("open") || s === "live") {
        return `<span class="badge badge-green"><span class="status-pulse pulse-green"></span>Live</span>`;
      } else if (s.includes("closing")) {
        return `<span class="badge badge-yellow"><span class="status-pulse" style="background:#f59e0b;"></span>Closing Today</span>`;
      } else if (s.includes("opening")) {
        return `<span class="badge badge-yellow">Opening Today</span>`;
      } else if (s.includes("upcoming") || s.includes("forthcoming")) {
        return `<span class="badge badge-blue">Forthcoming</span>`;
      } else if (s.includes("closed") || s.includes("listed")) {
        return `<span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);">Closed</span>`;
      }
      return `<span class="badge badge-blue">${escapeHtml(status || 'Active')}</span>`;
    }

    function getSegmentBadge(ipo) {
      const isSme = (ipo.segment && ipo.segment.toUpperCase().includes("SME")) ||
                    (ipo.company_name && ipo.company_name.toUpperCase().includes("SME")) ||
                    (ipo.issue_size_cr && ipo.issue_size_cr < 50 && ipo.issue_size_cr > 0);
      if (isSme) {
        return `<span class="badge" style="background: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.3);">SME</span>`;
      }
      return `<span class="badge badge-purple">MAINBOARD</span>`;
    }

    function getSubscriptionBadge(ipo) {
      const s = (ipo.status || "").toLowerCase();
      const isUpcoming = s.includes("upcoming") || s.includes("forthcoming");
      if (isUpcoming || ipo.subscription_times === null || ipo.subscription_times === undefined) {
        if (isUpcoming) {
          return `<span class="badge badge-purple" style="font-weight: 600;">PRE-APPLY</span>`;
        }
        return `<span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);">Data TBA</span>`;
      }
      const sub = ipo.subscription_times;
      let badgeClass = "badge-blue";
      if (sub >= 5.0) badgeClass = "badge-green";
      else if (sub >= 1.0) badgeClass = "badge-blue";
      else badgeClass = "badge-yellow";

      const displayVal = Number.isInteger(sub) ? `${sub}.0x` : `${sub}x`;

      const qib = (ipo.qib_subscription !== null && ipo.qib_subscription !== undefined) ? ipo.qib_subscription : null;
      const nii = (ipo.nii_subscription !== null && ipo.nii_subscription !== undefined) ? ipo.nii_subscription : null;
      const ret = (ipo.retail_subscription !== null && ipo.retail_subscription !== undefined) ? ipo.retail_subscription : null;

      let verdictText = "⚡ Moderate Demand";
      let verdictColor = "#60a5fa";
      if (qib !== null && qib >= 10.0) {
        verdictText = "🔥 Strong QIB Demand";
        verdictColor = "#34d399";
      } else if (qib !== null && qib < 1.0) {
        verdictText = "⚠️ Institutional Undersubscribed";
        verdictColor = "#f87171";
      } else if (sub >= 5.0) {
        verdictText = "✨ High Overall Demand";
        verdictColor = "#34d399";
      }

      const qibPct = qib !== null ? Math.min(100, Math.max(8, (qib / 30) * 100)) : 0;
      const niiPct = nii !== null ? Math.min(100, Math.max(8, (nii / 20) * 100)) : 0;
      const retPct = ret !== null ? Math.min(100, Math.max(8, (ret / 10) * 100)) : 0;

      return `
        <div class="sub-popover-container" onclick="event.stopPropagation(); this.classList.toggle('popover-open');">
          <span class="badge ${badgeClass}" style="cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="Click or hover to view QIB/NII/Retail breakdown">
            ${displayVal} <span style="font-size: 0.6rem; opacity: 0.85;">▼</span>
          </span>
          <div class="sub-popover" onclick="event.stopPropagation();">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.4rem; margin-bottom: 0.55rem;">
              <span style="font-size: 0.72rem; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.04em;">Subscription Split</span>
              <span style="font-size: 0.65rem; font-weight: 600; color: ${verdictColor}; background: rgba(255,255,255,0.06); padding: 1px 6px; border-radius: 4px;">${verdictText}</span>
            </div>

            <!-- QIB Row -->
            <div style="margin-bottom: 0.5rem;">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; align-items: center;">
                <span style="color: #93c5fd; font-weight: 600;">🏛️ QIB (Institutions)</span>
                <span style="font-weight: 700; color: ${qib !== null && qib >= 1.0 ? '#34d399' : (qib !== null ? '#f87171' : 'var(--text-muted)')};">
                  ${qib !== null ? (Number.isInteger(qib) ? `${qib}.0x` : `${qib.toFixed(2)}x`) : 'N/A'}
                </span>
              </div>
              <div class="sub-bar-bg"><div class="sub-bar-fill" style="width: ${qibPct}%; background: #3b82f6;"></div></div>
            </div>

            <!-- NII Row -->
            <div style="margin-bottom: 0.5rem;">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; align-items: center;">
                <span style="color: #c084fc; font-weight: 600;">💼 NII / HNI</span>
                <span style="font-weight: 700; color: ${nii !== null && nii >= 1.0 ? '#34d399' : (nii !== null ? '#f87171' : 'var(--text-muted)')};">
                  ${nii !== null ? (Number.isInteger(nii) ? `${nii}.0x` : `${nii.toFixed(2)}x`) : 'N/A'}
                </span>
              </div>
              <div class="sub-bar-bg"><div class="sub-bar-fill" style="width: ${niiPct}%; background: #a855f7;"></div></div>
            </div>

            <!-- Retail Row -->
            <div style="margin-bottom: 0.5rem;">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; align-items: center;">
                <span style="color: #fde047; font-weight: 600;">👥 Retail (RII)</span>
                <span style="font-weight: 700; color: ${ret !== null && ret >= 1.0 ? '#34d399' : (ret !== null ? '#f87171' : 'var(--text-muted)')};">
                  ${ret !== null ? (Number.isInteger(ret) ? `${ret}.0x` : `${ret.toFixed(2)}x`) : 'N/A'}
                </span>
              </div>
              <div class="sub-bar-bg"><div class="sub-bar-fill" style="width: ${retPct}%; background: #eab308;"></div></div>
            </div>

            <!-- Total Bids Summary -->
            <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.45rem; display: flex; justify-content: space-between; font-size: 0.78rem; align-items: center;">
              <span style="color: var(--text-secondary); font-weight: 600;">Overall Bidding:</span>
              <span style="color: #60a5fa; font-weight: 800; font-size: 0.85rem;">${displayVal}</span>
            </div>
          </div>
        </div>
      `;
    }

    function getCompanyLogo(name) {
      const n = (name || "").toLowerCase();
      if (n.includes("jio")) {
        return `<div style="width: 38px; height: 38px; border-radius: 50%; background: #0078d7; color: #fff; font-weight: 800; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0, 120, 215, 0.4); flex-shrink: 0;">Jio</div>`;
      } else if (n.includes("zetwerk")) {
        return `<div style="width: 38px; height: 38px; border-radius: 8px; background: #ffffff; color: #0f172a; font-weight: 800; font-size: 0.72rem; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.2); letter-spacing: -0.5px; flex-shrink: 0;">ZET</div>`;
      } else if (n.includes("bonfiglioli")) {
        return `<div style="width: 38px; height: 38px; border-radius: 8px; background: #ffffff; color: #0f172a; font-weight: 800; font-size: 0.72rem; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.2); flex-shrink: 0;">BON</div>`;
      } else if (n.includes("tonbo")) {
        return `<div style="width: 38px; height: 38px; border-radius: 8px; background: #e11d48; color: #fff; font-weight: 800; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">TNB</div>`;
      } else if (n.includes("sahajanand") || n.includes("smt")) {
        return `<div style="width: 38px; height: 38px; border-radius: 8px; background: #0284c7; color: #fff; font-weight: 800; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">SMT</div>`;
      } else if (n.includes("shellz")) {
        return `<div style="width: 38px; height: 38px; border-radius: 8px; background: #d97706; color: #fff; font-weight: 800; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">SHZ</div>`;
      }
      const initial = (name || "IP").slice(0, 2).toUpperCase();
      return `<div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); color: #60a5fa; font-weight: 700; font-size: 0.82rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${initial}</div>`;
    }

    let currentIpoSection = "all";

    function switchIpoSection(sec) {
      currentIpoSection = sec;
      const allBtn = document.getElementById("ipoSecAllBtn");
      const curBtn = document.getElementById("ipoSecCurrentBtn");
      const preBtn = document.getElementById("ipoSecPreApplyBtn");

      if (allBtn) allBtn.classList.toggle("active", sec === "all");
      if (curBtn) curBtn.classList.toggle("active", sec === "current");
      if (preBtn) preBtn.classList.toggle("active", sec === "pre_apply");

      const curBlock = document.getElementById("sectionCurrentIposBlock");
      const preBlock = document.getElementById("sectionPreApplyBlock");

      if (curBlock) {
        curBlock.style.display = (sec === "all" || sec === "current") ? "block" : "none";
      }
      if (preBlock) {
        preBlock.style.display = (sec === "all" || sec === "pre_apply") ? "block" : "none";
      }
    }

    function isPreApplyIpo(ipo) {
      const s = (ipo.status || "").toLowerCase();
      if (s.includes("closed") || s.includes("listed")) return false;
      const todayStr = (new Date().getFullYear() >= 2026) ? new Date().toISOString().split("T")[0] : "2026-10-19";
      if (ipo.close_date && String(ipo.close_date).split("T")[0] < todayStr) return false;
      if (ipo.allotment_date && String(ipo.allotment_date).split("T")[0] < todayStr) return false;
      if (ipo.listing_date && String(ipo.listing_date).split("T")[0] <= todayStr) return false;

      if (s.includes("upcoming") || s.includes("forthcoming") || s.includes("pre-apply")) return true;
      if (ipo.open_date) {
        const oDate = String(ipo.open_date).split("T")[0];
        if (oDate > todayStr) return true;
      }
      return false;
    }

    function createIpoTableRow(ipo, isPre) {
      const gmpBadge = (ipo.gmp_percentage !== null && ipo.gmp_percentage !== undefined)
        ? `<span class="badge ${ipo.gmp_percentage >= 20 ? 'badge-green' : (ipo.gmp_percentage > 0 ? 'badge-yellow' : 'badge-red')}">GMP ${ipo.gmp_percentage >= 0 ? '+' : ''}${ipo.gmp_percentage.toFixed(1)}%</span>`
        : `<span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);">GMP N/A</span>`;

      const priceDisplay = ipo.price_band ? `₹${escapeHtml(ipo.price_band)}` : 'Fixed / TBA';
      const sizeDisplay = ipo.issue_size_cr ? `₹${ipo.issue_size_cr.toLocaleString('en-IN')} Cr` : 'Not disclosed';
      const inWish = isWishlisted(ipo.ipo_id);

      const subBadge = isPre 
        ? `<span class="badge badge-purple" style="font-weight: 600;">PRE-APPLY</span>`
        : getSubscriptionBadge(ipo);

      const statusBadge = isPre
        ? `<span class="badge badge-purple"><span class="status-pulse" style="background:#a855f7;"></span>Pre-Apply</span>`
        : getStatusBadge(ipo.status);

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            ${getCompanyLogo(ipo.company_name)}
            <div>
              <div class="col-company-title" style="cursor: pointer;" onclick="openIpoDetails('${escapeHtml(ipo.ipo_id)}')" title="Click to view details: ${escapeHtml(ipo.company_name)}">${escapeHtml(ipo.company_name)}</div>
              <div class="col-company-sub">
                <span>${escapeHtml(ipo.ticker_symbol || ipo.ipo_id)}</span>
                <span>•</span>
                <span>${escapeHtml(ipo.sector || 'General')}</span>
              </div>
            </div>
          </div>
        </td>
        <td>${getSegmentBadge(ipo)}</td>
        <td class="col-date" style="${isPre ? 'color: #c084fc; font-weight: 600;' : ''}">${formatMarketDate(ipo.open_date)}</td>
        <td class="col-date">${formatMarketDate(ipo.close_date)}</td>
        <td class="col-date" style="color: #60a5fa; font-weight: 500;">${formatMarketDate(ipo.allotment_date)}</td>
        <td class="col-date" style="color: #34d399; font-weight: 500;">${formatMarketDate(ipo.listing_date)}</td>
        <td class="col-price">${priceDisplay}</td>
        <td style="font-weight: 500;">${sizeDisplay}</td>
        <td>${subBadge}</td>
        <td>${gmpBadge}</td>
        <td>${statusBadge}</td>
        <td style="text-align: right;">
          <div style="display: inline-flex; gap: 0.4rem; justify-content: flex-end; align-items: center;">
            <button 
              class="btn btn-secondary" 
              style="padding: 0.35rem 0.65rem; font-size: 0.75rem; border-color: ${inWish ? 'rgba(245, 158, 11, 0.6)' : 'var(--border-color)'}; color: ${inWish ? '#fbbf24' : 'var(--text-secondary)'}; background: ${inWish ? 'rgba(245, 158, 11, 0.15)' : 'rgba(255, 255, 255, 0.05)'}; font-weight: ${inWish ? '600' : 'normal'};" 
              onclick="toggleWishlist('${escapeHtml(ipo.ipo_id)}', '${escapeHtml(ipo.company_name)}')"
              title="${inWish ? 'Remove from Wishlist' : 'Add to Wishlist'}">
              ${inWish ? '★ Wishlisted' : '☆ Add to Wish'}
            </button>
            <button 
              class="btn" 
              style="padding: 0.35rem 0.75rem; font-size: 0.75rem; font-weight: 600;" 
              onclick="quickEvaluate('${escapeHtml(ipo.ipo_id)}')"
              title="Run Recommendation Engine Evaluation">
              Evaluate
            </button>
          </div>
        </td>
      `;
      return tr;
    }

    function createIpoCard(ipo, isPre) {
      const gmpBadge = (ipo.gmp_percentage !== null && ipo.gmp_percentage !== undefined)
        ? `<span class="badge ${ipo.gmp_percentage >= 20 ? 'badge-green' : (ipo.gmp_percentage > 0 ? 'badge-yellow' : 'badge-red')}">GMP ${ipo.gmp_percentage >= 0 ? '+' : ''}${ipo.gmp_percentage.toFixed(1)}%</span>`
        : `<span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);">GMP N/A</span>`;

      const priceDisplay = ipo.price_band ? `₹${escapeHtml(ipo.price_band)}` : 'Fixed / TBA';
      const sizeDisplay = ipo.issue_size_cr ? `₹${ipo.issue_size_cr.toLocaleString('en-IN')} Cr` : 'Not disclosed';
      const inWish = isWishlisted(ipo.ipo_id);

      const subBadge = isPre 
        ? `<span class="badge badge-purple" style="font-weight: 600;">PRE-APPLY</span>`
        : getSubscriptionBadge(ipo);

      const card = document.createElement("div");
      card.className = "card";
      card.style = `display: flex; flex-direction: column; justify-content: space-between; border: 1px solid ${isPre ? 'rgba(139, 92, 246, 0.35)' : 'var(--border-color)'}; background: ${isPre ? 'rgba(26, 21, 46, 0.65)' : 'var(--bg-card)'};`;
      card.innerHTML = `
        <div>
          <div style="display: flex; align-items: center; gap: 0.85rem; margin-bottom: 0.85rem;">
            ${getCompanyLogo(ipo.company_name)}
            <div style="flex: 1; min-width: 0;">
              <div class="card-title" style="cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" onclick="openIpoDetails('${escapeHtml(ipo.ipo_id)}')" title="Click to view details: ${escapeHtml(ipo.company_name)}">${escapeHtml(ipo.company_name)}</div>
              <div style="margin-top: 3px; display: flex; align-items: center; gap: 0.4rem;">
                ${getSegmentBadge(ipo)}
                ${isPre ? '<span class="badge badge-purple" style="font-size: 0.68rem; padding: 0.1rem 0.4rem;">Pre-Apply</span>' : ''}
              </div>
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
              ${gmpBadge}
            </div>
          </div>

          <!-- Info Box -->
          <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.75rem; margin-bottom: 0.85rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase;">${isPre ? 'Opens On' : 'Closes On'}</div>
              <div style="font-size: 0.95rem; font-weight: 600; color: ${isPre ? '#c084fc' : 'var(--text-primary)'}; margin-top: 2px;">${formatMarketDate(isPre ? ipo.open_date : ipo.close_date)}</div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase;">${isPre ? 'Bid Stage' : 'Subscription'}</div>
              <div style="font-size: 0.95rem; font-weight: 600; margin-top: 2px;">${subBadge}</div>
            </div>
          </div>

          <!-- Dates & Issue Parameters -->
          <div class="metric-row">
            <span class="metric-label">${isPre ? 'Closes On' : 'Start Date'}</span>
            <span class="metric-value col-date">${formatMarketDate(isPre ? ipo.close_date : ipo.open_date)}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Allotment Date</span>
            <span class="metric-value col-date" style="color: #60a5fa; font-weight: 500;">${formatMarketDate(ipo.allotment_date)}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Listing Date</span>
            <span class="metric-value col-date" style="color: #34d399; font-weight: 500;">${formatMarketDate(ipo.listing_date)}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Issue Size</span>
            <span class="metric-value">${sizeDisplay}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Price Band</span>
            <span class="metric-value col-price">${priceDisplay}</span>
          </div>
        </div>

        <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
          <button 
            class="btn btn-secondary" 
            style="flex: 1; border-color: ${inWish ? 'rgba(245, 158, 11, 0.6)' : 'var(--border-color)'}; color: ${inWish ? '#fbbf24' : 'var(--text-secondary)'}; background: ${inWish ? 'rgba(245, 158, 11, 0.15)' : 'rgba(255, 255, 255, 0.05)'}; font-weight: ${inWish ? '600' : 'normal'};" 
            onclick="toggleWishlist('${escapeHtml(ipo.ipo_id)}', '${escapeHtml(ipo.company_name)}')">
            ${inWish ? '★ Wishlisted' : '☆ Add to Wish'}
          </button>
          <button class="btn" style="flex: 1; font-weight: 600;" onclick="quickEvaluate('${escapeHtml(ipo.ipo_id)}')">Evaluate</button>
        </div>
      `;
      return card;
    }

    function renderIPOs(items) {
      const currentBody = document.getElementById("currentTableBody");
      const currentGrid = document.getElementById("currentGrid");
      const currentTableContainer = document.getElementById("currentTableContainer");
      const currentEmpty = document.getElementById("currentEmpty");

      const preApplyBody = document.getElementById("preApplyTableBody");
      const preApplyGrid = document.getElementById("preApplyGrid");
      const preApplyTableContainer = document.getElementById("preApplyTableContainer");
      const preApplyEmpty = document.getElementById("preApplyEmpty");

      const curBlock = document.getElementById("sectionCurrentIposBlock");
      const preBlock = document.getElementById("sectionPreApplyBlock");
      const iposEmpty = document.getElementById("iposEmpty");

      if (currentBody) currentBody.innerHTML = "";
      if (currentGrid) currentGrid.innerHTML = "";
      if (preApplyBody) preApplyBody.innerHTML = "";
      if (preApplyGrid) preApplyGrid.innerHTML = "";

      // Filter out any closed or listed IPOs from the dashboard
      const marketTodayStr = (new Date().getFullYear() >= 2026) ? new Date().toISOString().split("T")[0] : "2026-10-19";
      const activeItems = (items || []).filter(ipo => {
        const s = (ipo.status || "").toLowerCase();
        if (s.includes("closed") || s.includes("listed")) return false;
        if (ipo.close_date && String(ipo.close_date).split("T")[0] < marketTodayStr) return false;
        if (ipo.allotment_date && String(ipo.allotment_date).split("T")[0] < marketTodayStr && (!ipo.close_date || String(ipo.close_date).split("T")[0] <= marketTodayStr)) return false;
        if (ipo.listing_date && String(ipo.listing_date).split("T")[0] <= marketTodayStr) return false;
        return true;
      });

      // Split into Current IPOs and Pre-Apply IPOs
      const currentItems = activeItems.filter(ipo => !isPreApplyIpo(ipo));
      const preApplyItems = activeItems.filter(ipo => isPreApplyIpo(ipo));

      // Update section switcher counters and header badges
      const cntAll = document.getElementById("secCountAll");
      const cntCur = document.getElementById("secCountCurrent");
      const cntPre = document.getElementById("secCountPreApply");
      const curHeadBadge = document.getElementById("currentIposHeaderBadge");
      const preHeadBadge = document.getElementById("preApplyHeaderBadge");

      if (cntAll) cntAll.innerText = activeItems.length;
      if (cntCur) cntCur.innerText = currentItems.length;
      if (cntPre) cntPre.innerText = preApplyItems.length;
      if (curHeadBadge) curHeadBadge.innerText = `${currentItems.length} Open`;
      if (preHeadBadge) preHeadBadge.innerText = `${preApplyItems.length} Upcoming`;

      // Check if completely empty
      if (activeItems.length === 0) {
        if (iposEmpty) iposEmpty.style.display = "block";
        if (curBlock) curBlock.style.display = "none";
        if (preBlock) preBlock.style.display = "none";
        return;
      }
      if (iposEmpty) iposEmpty.style.display = "none";

      // Restore block visibility based on current section selection
      if (curBlock) {
        curBlock.style.display = (currentIpoSection === "all" || currentIpoSection === "current") ? "block" : "none";
      }
      if (preBlock) {
        preBlock.style.display = (currentIpoSection === "all" || currentIpoSection === "pre_apply") ? "block" : "none";
      }

      // 1. Populate Current IPOs
      if (currentItems.length === 0) {
        if (currentEmpty) currentEmpty.style.display = "block";
        if (currentTableContainer) currentTableContainer.style.display = "none";
        if (currentGrid) currentGrid.style.display = "none";
      } else {
        if (currentEmpty) currentEmpty.style.display = "none";
        currentItems.forEach(ipo => {
          if (currentBody) currentBody.appendChild(createIpoTableRow(ipo, false));
          if (currentGrid) currentGrid.appendChild(createIpoCard(ipo, false));
        });
        if (currentViewMode === "cards") {
          if (currentTableContainer) currentTableContainer.style.display = "none";
          if (currentGrid) currentGrid.style.display = "grid";
        } else {
          if (currentTableContainer) currentTableContainer.style.display = "block";
          if (currentGrid) currentGrid.style.display = "none";
        }
      }

      // 2. Populate Pre-Apply IPOs
      if (preApplyItems.length === 0) {
        if (preApplyEmpty) preApplyEmpty.style.display = "block";
        if (preApplyTableContainer) preApplyTableContainer.style.display = "none";
        if (preApplyGrid) preApplyGrid.style.display = "none";
      } else {
        if (preApplyEmpty) preApplyEmpty.style.display = "none";
        preApplyItems.forEach(ipo => {
          if (preApplyBody) preApplyBody.appendChild(createIpoTableRow(ipo, true));
          if (preApplyGrid) preApplyGrid.appendChild(createIpoCard(ipo, true));
        });
        if (currentViewMode === "cards") {
          if (preApplyTableContainer) preApplyTableContainer.style.display = "none";
          if (preApplyGrid) preApplyGrid.style.display = "grid";
        } else {
          if (preApplyTableContainer) preApplyTableContainer.style.display = "block";
          if (preApplyGrid) preApplyGrid.style.display = "none";
        }
      }
    }

    let cachedWishlistIds = [];
    let cachedWishlistItems = [];
    let cachedHistoryItems = [];
    let currentWishlistView = "active";

    async function syncWishlistFromDb() {
      try {
        const resp = await fetch("/wishlist/ids", { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          cachedWishlistIds = data.wishlist || [];
          localStorage.setItem("ipo_wishlist", JSON.stringify(cachedWishlistIds));
          updateWishlistNavBadge();
        }
      } catch (e) {
        cachedWishlistIds = getWishlist();
        updateWishlistNavBadge();
      }

      // Also refresh history counts in background
      try {
        const hResp = await fetch("/wishlist/history", { headers: getAuthHeaders() });
        if (hResp.ok) {
          const hData = await hResp.json();
          cachedHistoryItems = hData.items || [];
          const hBadge = document.getElementById("listedHistoryBadge");
          if (hBadge) hBadge.innerText = cachedHistoryItems.length;
        }
      } catch (e) {}
    }

    function updateWishlistNavBadge() {
      const badge = document.getElementById("wishlistNavCount");
      if (badge) {
        badge.innerText = cachedWishlistIds.length;
      }
      const activeBadge = document.getElementById("activeWishlistBadge");
      if (activeBadge) {
        activeBadge.innerText = cachedWishlistIds.length;
      }
    }

    function getWishlist() {
      try {
        return JSON.parse(localStorage.getItem("ipo_wishlist") || "[]");
      } catch (e) {
        return [];
      }
    }

    function isWishlisted(ipoId) {
      if (cachedWishlistIds && cachedWishlistIds.length > 0) {
        return cachedWishlistIds.includes(ipoId);
      }
      return getWishlist().includes(ipoId);
    }

    async function toggleWishlist(ipoId, companyName) {
      const already = isWishlisted(ipoId);
      const method = already ? "DELETE" : "POST";
      const url = `/wishlist/${encodeURIComponent(ipoId)}`;

      // Optimistic update
      if (already) {
        cachedWishlistIds = cachedWishlistIds.filter(id => id !== ipoId);
      } else {
        if (!cachedWishlistIds.includes(ipoId)) cachedWishlistIds.push(ipoId);
      }
      localStorage.setItem("ipo_wishlist", JSON.stringify(cachedWishlistIds));
      updateWishlistNavBadge();
      applyAllFilters();

      try {
        const resp = await fetch(url, {
          method: method,
          headers: getAuthHeaders(),
        });
        if (resp.ok) {
          if (already) {
            showAlert(`Removed "${companyName || ipoId}" from database wishlist.`, "info");
          } else {
            showAlert(`⭐ Successfully saved "${companyName || ipoId}" to database wishlist table!`, "success");
          }
          await loadWishlist();
          // Check if it was listed and also update history
          await loadWishlistHistory();
        } else {
          showAlert(`Could not update wishlist in database: HTTP ${resp.status}`, "error");
          await syncWishlistFromDb();
          applyAllFilters();
        }
      } catch (err) {
        showAlert(`Network error updating database wishlist: ${err.message}`, "error");
      }
    }

    function switchWishlistView(view) {
      currentWishlistView = view;
      const activeView = document.getElementById("activeWishlistView");
      const historyView = document.getElementById("listedHistoryView");
      const pillActive = document.getElementById("pillActiveWishlist");
      const pillHistory = document.getElementById("pillListedHistory");

      if (view === "active") {
        if (activeView) activeView.style.display = "block";
        if (historyView) historyView.style.display = "none";
        if (pillActive) { pillActive.className = "btn"; }
        if (pillHistory) { pillHistory.className = "btn btn-secondary"; }
        loadWishlist();
      } else {
        if (activeView) activeView.style.display = "none";
        if (historyView) historyView.style.display = "block";
        if (pillActive) { pillActive.className = "btn btn-secondary"; }
        if (pillHistory) { pillHistory.className = "btn"; }
        loadWishlistHistory();
      }
    }

    function refreshCurrentWishlistView() {
      if (currentWishlistView === "history") {
        loadWishlistHistory();
      } else {
        loadWishlist();
      }
    }

    async function loadWishlist() {
      const loading = document.getElementById("wishlistLoading");
      const container = document.getElementById("wishlistTableContainer");
      const empty = document.getElementById("wishlistEmpty");
      const tbody = document.getElementById("wishlistTableBody");

      if (loading) loading.style.display = "block";
      if (container) container.style.display = "none";
      if (empty) empty.style.display = "none";

      try {
        const resp = await fetch("/wishlist", { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          cachedWishlistItems = data.items || [];
          cachedWishlistIds = cachedWishlistItems.map(i => i.ipo_id);
          localStorage.setItem("ipo_wishlist", JSON.stringify(cachedWishlistIds));
          updateWishlistNavBadge();
          renderWishlist(cachedWishlistItems);
        } else {
          const items = cachedIPOs.filter(i => cachedWishlistIds.includes(i.ipo_id));
          renderWishlist(items);
        }
      } catch (e) {
        const items = cachedIPOs.filter(i => cachedWishlistIds.includes(i.ipo_id));
        renderWishlist(items);
      } finally {
        if (loading) loading.style.display = "none";
      }
    }

    function renderWishlist(items) {
      const container = document.getElementById("wishlistTableContainer");
      const empty = document.getElementById("wishlistEmpty");
      const tbody = document.getElementById("wishlistTableBody");
      const activeBadge = document.getElementById("activeWishlistBadge");

      if (activeBadge) activeBadge.innerText = (items || []).length;
      if (!tbody) return;
      tbody.innerHTML = "";

      if (!items || items.length === 0) {
        if (empty) empty.style.display = "block";
        if (container) container.style.display = "none";
        return;
      }

      if (empty) empty.style.display = "none";
      if (container) container.style.display = "block";

      items.forEach(ipo => {
        const priceDisplay = ipo.price_band ? `₹${escapeHtml(ipo.price_band)}` : 'Fixed / TBA';
        const sizeDisplay = ipo.issue_size_cr ? `₹${ipo.issue_size_cr.toLocaleString('en-IN')} Cr` : 'Not disclosed';
        const gmpBadge = (ipo.gmp_percentage !== null && ipo.gmp_percentage !== undefined)
          ? `<span class="badge ${ipo.gmp_percentage >= 20 ? 'badge-green' : (ipo.gmp_percentage > 0 ? 'badge-yellow' : 'badge-red')}">GMP ${ipo.gmp_percentage >= 0 ? '+' : ''}${ipo.gmp_percentage.toFixed(1)}%</span>`
          : `<span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);">GMP N/A</span>`;

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              ${getCompanyLogo(ipo.company_name)}
              <div>
                <div class="col-company-title" style="cursor: pointer;" onclick="openIpoDetails('${escapeHtml(ipo.ipo_id)}')">${escapeHtml(ipo.company_name)}</div>
                <div class="col-company-sub">
                  <span>${escapeHtml(ipo.ticker_symbol || ipo.ipo_id)}</span>
                  <span>•</span>
                  <span>${escapeHtml(ipo.sector || 'General')}</span>
                </div>
              </div>
            </div>
          </td>
          <td>${getSegmentBadge(ipo)}</td>
          <td class="col-date">${formatMarketDate(ipo.open_date)}</td>
          <td class="col-date">${formatMarketDate(ipo.close_date)}</td>
          <td class="col-date" style="color: #60a5fa; font-weight: 500;">${formatMarketDate(ipo.allotment_date)}</td>
          <td class="col-date" style="color: #34d399; font-weight: 500;">${formatMarketDate(ipo.listing_date)}</td>
          <td class="col-price">${priceDisplay}</td>
          <td style="font-weight: 500;">${sizeDisplay}</td>
          <td>${getSubscriptionBadge(ipo)}</td>
          <td>${gmpBadge}</td>
          <td>${getStatusBadge(ipo.status)}</td>
          <td style="text-align: right;">
            <div style="display: inline-flex; gap: 0.4rem; justify-content: flex-end;">
              <button 
                class="btn btn-secondary" 
                style="padding: 0.35rem 0.65rem; font-size: 0.75rem; border-color: rgba(239, 68, 68, 0.4); color: #f87171;" 
                onclick="toggleWishlist('${escapeHtml(ipo.ipo_id)}', '${escapeHtml(ipo.company_name)}')"
                title="Remove from Database Wishlist">
                ✕ Remove
              </button>
              <button 
                class="btn" 
                style="padding: 0.35rem 0.75rem; font-size: 0.75rem; font-weight: 600;" 
                onclick="quickEvaluate('${escapeHtml(ipo.ipo_id)}')">
                Evaluate
              </button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function loadWishlistHistory() {
      const loading = document.getElementById("wishlistLoading");
      const container = document.getElementById("historyTableContainer");
      const empty = document.getElementById("historyEmpty");

      if (loading) loading.style.display = "block";
      if (container) container.style.display = "none";
      if (empty) empty.style.display = "none";

      try {
        const resp = await fetch("/wishlist/history", { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          cachedHistoryItems = data.items || [];
          const badge = document.getElementById("listedHistoryBadge");
          if (badge) badge.innerText = cachedHistoryItems.length;
          renderWishlistHistory(cachedHistoryItems);
        } else {
          renderWishlistHistory([]);
        }
      } catch (e) {
        renderWishlistHistory([]);
      } finally {
        if (loading) loading.style.display = "none";
      }
    }

    function renderWishlistHistory(items) {
      const container = document.getElementById("historyTableContainer");
      const empty = document.getElementById("historyEmpty");
      const tbody = document.getElementById("historyTableBody");
      const badge = document.getElementById("listedHistoryBadge");

      if (badge) badge.innerText = (items || []).length;
      if (!tbody) return;
      tbody.innerHTML = "";

      if (!items || items.length === 0) {
        if (empty) empty.style.display = "block";
        if (container) container.style.display = "none";
        return;
      }

      if (empty) empty.style.display = "none";
      if (container) container.style.display = "block";

      items.forEach(ipo => {
        const issuePriceStr = (ipo.issue_price !== null && ipo.issue_price !== undefined)
          ? `₹${ipo.issue_price.toFixed(2)}`
          : 'TBA';

        let listingPriceHtml = '';
        if (ipo.listing_price !== null && ipo.listing_price !== undefined) {
          listingPriceHtml = `<span style="font-size: 0.95rem; font-weight: 700; color: #60a5fa;">₹${ipo.listing_price.toFixed(2)}</span>`;
        } else {
          listingPriceHtml = `<span style="color: var(--text-muted); font-size: 0.8rem; font-style: italic;">Pending quote</span> 
            <button class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.72rem; margin-left: 0.35rem;" 
              onclick="openEditListingPriceModal('${escapeHtml(ipo.ipo_id)}', '${escapeHtml(ipo.company_name)}', ${ipo.issue_price || 'null'}, null, null, '${ipo.listing_date || ''}')">Set Price</button>`;
        }

        let gainBadge = '';
        if (ipo.listing_gain_pct !== null && ipo.listing_gain_pct !== undefined) {
          const isPos = ipo.listing_gain_pct >= 0;
          const cls = isPos ? (ipo.listing_gain_pct >= 15 ? 'badge-green' : 'badge-yellow') : 'badge-red';
          gainBadge = `<span class="badge ${cls}" style="font-size: 0.82rem; padding: 0.25rem 0.55rem; font-weight: 700;">${isPos ? '+' : ''}${ipo.listing_gain_pct.toFixed(2)}%</span>`;
        } else {
          gainBadge = `<span class="badge" style="background: rgba(255,255,255,0.06); color: var(--text-muted);">N/A</span>`;
        }

        const dayCloseStr = (ipo.listing_day_close !== null && ipo.listing_day_close !== undefined)
          ? `₹${ipo.listing_day_close.toFixed(2)}`
          : '-';

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              ${getCompanyLogo(ipo.company_name)}
              <div>
                <div class="col-company-title" style="cursor: pointer;" onclick="openIpoDetails('${escapeHtml(ipo.ipo_id)}')">${escapeHtml(ipo.company_name)}</div>
                <div class="col-company-sub">
                  <span>${escapeHtml(ipo.ipo_id)}</span>
                  <span>•</span>
                  <span class="badge ${ipo.segment === 'SME' ? 'badge-yellow' : 'badge-blue'}" style="font-size: 0.68rem; padding: 0.1rem 0.4rem;">${escapeHtml(ipo.segment || 'Mainboard')}</span>
                </div>
              </div>
            </div>
          </td>
          <td class="col-date" style="color: #34d399; font-weight: 500;">${formatMarketDate(ipo.listing_date)}</td>
          <td class="col-price">${issuePriceStr}</td>
          <td>${listingPriceHtml}</td>
          <td>${gainBadge}</td>
          <td style="font-weight: 500;">${dayCloseStr}</td>
          <td><span class="badge badge-green">Listed</span></td>
          <td class="col-date" style="font-size: 0.8rem; color: var(--text-muted);">${formatMarketDate(ipo.wishlist_added_at)}</td>
          <td style="text-align: right;">
            <div style="display: inline-flex; gap: 0.4rem; justify-content: flex-end;">
              <button 
                class="btn btn-secondary" 
                style="padding: 0.35rem 0.65rem; font-size: 0.75rem; border-color: rgba(96, 165, 250, 0.4); color: #93c5fd;" 
                onclick="openEditListingPriceModal('${escapeHtml(ipo.ipo_id)}', '${escapeHtml(ipo.company_name)}', ${ipo.issue_price || 'null'}, ${ipo.listing_price || 'null'}, ${ipo.listing_day_close || 'null'}, '${ipo.listing_date || ''}', '${escapeHtml(ipo.notes || '')}')"
                title="Edit or Update Listing Price">
                ✏️ Edit Price
              </button>
              <button 
                class="btn" 
                style="padding: 0.35rem 0.75rem; font-size: 0.75rem; font-weight: 600;" 
                onclick="quickEvaluate('${escapeHtml(ipo.ipo_id)}')">
                Evaluate
              </button>
              <button 
                class="btn btn-secondary" 
                style="padding: 0.35rem 0.55rem; font-size: 0.75rem; border-color: rgba(239, 68, 68, 0.3); color: #f87171;" 
                onclick="removeWishlistHistoryItem('${escapeHtml(ipo.ipo_id)}', '${escapeHtml(ipo.company_name)}')"
                title="Remove from Post-Listing History">
                ✕
              </button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function syncWishlistHistoryAndNotify() {
      showAlert("Scanning wishlisted offerings for listing events...", "info");
      try {
        const resp = await fetch("/wishlist/history/sync", {
          method: "POST",
          headers: getAuthHeaders(),
        });
        if (resp.ok) {
          const data = await resp.json();
          showAlert(`⭐ Sync complete! ${data.total} wishlisted offerings recorded in database post-listing history.`, "success");
          cachedHistoryItems = data.items || [];
          const badge = document.getElementById("listedHistoryBadge");
          if (badge) badge.innerText = cachedHistoryItems.length;
          if (currentWishlistView === "history") {
            renderWishlistHistory(cachedHistoryItems);
          }
        } else {
          showAlert(`Sync failed: HTTP ${resp.status}`, "error");
        }
      } catch (e) {
        showAlert(`Network error during sync: ${e.message}`, "error");
      }
    }

    async function removeWishlistHistoryItem(ipoId, companyName) {
      if (!confirm(`Remove "${companyName || ipoId}" from post-listing history?`)) return;
      try {
        const resp = await fetch(`/wishlist/history/${encodeURIComponent(ipoId)}`, {
          method: "DELETE",
          headers: getAuthHeaders(),
        });
        if (resp.ok) {
          showAlert(`Removed "${companyName || ipoId}" from database history.`, "info");
          await loadWishlistHistory();
        } else {
          showAlert(`Could not remove history item: HTTP ${resp.status}`, "error");
        }
      } catch (e) {
        showAlert(`Network error: ${e.message}`, "error");
      }
    }

    function openRecordListingPricePrompt() {
      let defaultIpoId = "";
      let defaultName = "";
      let defaultIssue = "";
      if (cachedWishlistItems && cachedWishlistItems.length > 0) {
        defaultIpoId = cachedWishlistItems[0].ipo_id;
        defaultName = cachedWishlistItems[0].company_name;
        defaultIssue = cachedWishlistItems[0].issue_price || (cachedWishlistItems[0].price_band ? parseFloat(cachedWishlistItems[0].price_band.split("-").pop()) : "");
      }
      openEditListingPriceModal(defaultIpoId, defaultName, defaultIssue, null, null, new Date().toISOString().split("T")[0]);
    }

    function openEditListingPriceModal(ipoId, companyName, issuePrice, listingPrice, dayClose, listingDate, notes) {
      document.getElementById("lpHiddenIpoId").value = ipoId || "";
      document.getElementById("lpCompanyName").value = companyName || ipoId || "";
      document.getElementById("lpIssuePrice").value = (issuePrice !== null && issuePrice !== undefined) ? issuePrice : "";
      document.getElementById("lpListingPrice").value = (listingPrice !== null && listingPrice !== undefined) ? listingPrice : "";
      document.getElementById("lpDayClose").value = (dayClose !== null && dayClose !== undefined) ? dayClose : "";
      document.getElementById("lpListingDate").value = listingDate || new Date().toISOString().split("T")[0];
      document.getElementById("lpNotes").value = notes || "";
      
      document.getElementById("lpModalTitle").innerText = listingPrice ? "Update Listing Price" : "Record Listing Price";
      calculateModalGain();

      const modal = document.getElementById("listingPriceModal");
      if (modal) modal.classList.add("active");
    }

    function closeListingPriceModalDirect() {
      const modal = document.getElementById("listingPriceModal");
      if (modal) modal.classList.remove("active");
    }

    function closeListingPriceModal(e) {
      if (e.target.id === "listingPriceModal") {
        closeListingPriceModalDirect();
      }
    }

    function calculateModalGain() {
      const issue = parseFloat(document.getElementById("lpIssuePrice").value);
      const listing = parseFloat(document.getElementById("lpListingPrice").value);
      const badge = document.getElementById("lpCalculatedGainBadge");
      if (!badge) return;

      if (!isNaN(issue) && !isNaN(listing) && issue > 0) {
        const gainPct = ((listing - issue) / issue) * 100;
        const isPos = gainPct >= 0;
        badge.innerText = `${isPos ? '+' : ''}${gainPct.toFixed(2)}%`;
        badge.className = `badge ${isPos ? (gainPct >= 15 ? 'badge-green' : 'badge-yellow') : 'badge-red'}`;
      } else {
        badge.innerText = "-- %";
        badge.className = "badge";
      }
    }

    async function submitListingPriceModal() {
      const ipoId = document.getElementById("lpHiddenIpoId").value.trim();
      const listingPrice = parseFloat(document.getElementById("lpListingPrice").value);
      const issuePrice = parseFloat(document.getElementById("lpIssuePrice").value);
      const dayClose = parseFloat(document.getElementById("lpDayClose").value);
      const listingDate = document.getElementById("lpListingDate").value;
      const notes = document.getElementById("lpNotes").value.trim();

      if (!ipoId) {
        showAlert("IPO Identifier is missing.", "error");
        return;
      }
      if (isNaN(listingPrice) || listingPrice <= 0) {
        showAlert("Please enter a valid listing price in INR.", "error");
        return;
      }

      const payload = {
        listing_price: listingPrice,
        issue_price: !isNaN(issuePrice) ? issuePrice : null,
        listing_day_close: !isNaN(dayClose) ? dayClose : null,
        listing_date: listingDate || null,
        notes: notes || null,
      };

      const submitBtn = document.getElementById("lpSubmitBtn");
      if (submitBtn) submitBtn.disabled = true;

      try {
        const resp = await fetch(`/wishlist/history/${encodeURIComponent(ipoId)}`, {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify(payload),
        });

        if (resp.ok) {
          const saved = await resp.json();
          showAlert(`⭐ Saved listing price ₹${saved.listing_price.toFixed(2)} (${saved.listing_gain_pct >= 0 ? '+' : ''}${saved.listing_gain_pct.toFixed(2)}%) for ${saved.company_name} to database history!`, "success");
          closeListingPriceModalDirect();
          await loadWishlistHistory();
          switchWishlistView("history");
        } else {
          const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
          showAlert(`Error saving listing price: ${err.detail || resp.statusText}`, "error");
        }
      } catch (e) {
        showAlert(`Network error: ${e.message}`, "error");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    }

    function evaluateFirstWishlistItem() {
      if (cachedWishlistItems && cachedWishlistItems.length > 0) {
        quickEvaluate(cachedWishlistItems[0].ipo_id);
      } else if (cachedWishlistIds && cachedWishlistIds.length > 0) {
        quickEvaluate(cachedWishlistIds[0]);
      } else {
        showAlert("No offerings in your wishlist to evaluate.", "info");
      }
    }

    let currentSortCol = null;
    let currentSortDir = "asc";

    function toggleSort(col) {
      if (currentSortCol === col) {
        currentSortDir = (currentSortDir === "asc") ? "desc" : "asc";
      } else {
        currentSortCol = col;
        currentSortDir = (col === "sub" || col === "gmp" || col === "size") ? "desc" : "asc";
      }
      updateSortIcons();
      applyAllFilters();
    }

    function updateSortIcons() {
      ["company", "close_date", "size", "sub", "gmp"].forEach(col => {
        const els = document.querySelectorAll(`[data-sort-icon="${col}"]`);
        els.forEach(el => {
          if (currentSortCol === col) {
            el.innerText = currentSortDir === "asc" ? "▲" : "▼";
            el.style.color = "var(--accent-blue)";
            el.style.opacity = "1";
          } else {
            el.innerText = "↕";
            el.style.color = "var(--text-muted)";
            el.style.opacity = "0.7";
          }
        });
      });
    }

    function resetAllFilters() {
      const s = document.getElementById("ipoSearchInput"); if (s) s.value = "";
      const st = document.getElementById("ipoStatusFilter"); if (st) st.value = "";
      const ed = document.getElementById("ipoEndDateFilter"); if (ed) ed.value = "";
      const sb = document.getElementById("ipoSubFilter"); if (sb) sb.value = "";
      const gm = document.getElementById("ipoGmpFilter"); if (gm) gm.value = "";
      currentSortCol = null;
      currentSortDir = "asc";
      updateSortIcons();
      applyAllFilters();
    }

    function applyAllFilters() {
      const q = (document.getElementById("ipoSearchInput")?.value || "").toLowerCase().trim();
      const statusFilter = document.getElementById("ipoStatusFilter")?.value || "";
      const endDateFilter = document.getElementById("ipoEndDateFilter")?.value || "";
      const subFilter = document.getElementById("ipoSubFilter")?.value || "";
      const gmpFilter = document.getElementById("ipoGmpFilter")?.value || "";

      // Dynamic reference timeline: uses current real date or aligns with active catalog offerings
      const realToday = new Date();
      const realTodayStr = realToday.toISOString().split("T")[0];
      const activeCloseDates = (cachedIPOs || []).map(i => i.close_date ? String(i.close_date).split("T")[0] : "").filter(Boolean).sort();
      let todayStr = realTodayStr;
      if (activeCloseDates.length > 0 && activeCloseDates[activeCloseDates.length - 1] < realTodayStr) {
        todayStr = activeCloseDates[0];
      }

      const tRef = new Date(todayStr);
      const dPlus3 = new Date(tRef);
      dPlus3.setDate(dPlus3.getDate() + 3);
      const dPlus3Str = dPlus3.toISOString().split("T")[0];

      const dPlus7 = new Date(tRef);
      dPlus7.setDate(dPlus7.getDate() + 7);
      const dPlus7Str = dPlus7.toISOString().split("T")[0];

      const dMonthEnd = new Date(tRef.getFullYear(), tRef.getMonth() + 1, 0);
      const dMonthEndStr = dMonthEnd.toISOString().split("T")[0];

      let filtered = (cachedIPOs || []).filter(ipo => {
        const s = (ipo.status || "").toLowerCase();
        if (s.includes("closed") || s.includes("listed")) return false;
        if (ipo.close_date && String(ipo.close_date).split("T")[0] < todayStr) return false;
        if (ipo.allotment_date && String(ipo.allotment_date).split("T")[0] < todayStr && (!ipo.close_date || String(ipo.close_date).split("T")[0] <= todayStr)) return false;
        if (ipo.listing_date && String(ipo.listing_date).split("T")[0] <= todayStr) return false;

        // Search text
        if (q) {
          const match = (ipo.company_name && ipo.company_name.toLowerCase().includes(q)) ||
                        (ipo.ipo_id && ipo.ipo_id.toLowerCase().includes(q)) ||
                        (ipo.ticker_symbol && ipo.ticker_symbol.toLowerCase().includes(q)) ||
                        (ipo.sector && ipo.sector.toLowerCase().includes(q));
          if (!match) return false;
        }

        // Status filter
        if (statusFilter) {
          if (statusFilter === "Currently Open" && !s.includes("open") && s !== "live") return false;
          if (statusFilter === "Closing Today" && !s.includes("closing") && ipo.close_date !== todayStr) return false;
          if (statusFilter === "Upcoming" && !s.includes("upcoming") && !s.includes("forthcoming")) return false;
          if (statusFilter === "wishlist_only" && !isWishlisted(ipo.ipo_id)) return false;
        }

        // 1. End Date Filter
        if (endDateFilter && !endDateFilter.startsWith("sort_")) {
          const cDate = ipo.close_date ? String(ipo.close_date).split("T")[0] : "";
          if (endDateFilter === "closing_today") {
            if (cDate !== todayStr && !s.includes("closing")) return false;
          } else if (endDateFilter === "next_3_days") {
            if (!cDate || cDate > dPlus3Str || cDate < todayStr) return false;
          } else if (endDateFilter === "next_7_days") {
            if (!cDate || cDate > dPlus7Str || cDate < todayStr) return false;
          } else if (endDateFilter === "this_month") {
            if (!cDate || cDate > dMonthEndStr || cDate < todayStr) return false;
          }
        }

        // 2. Subscription Filter
        if (subFilter && !subFilter.startsWith("sort_")) {
          const sub = ipo.subscription_times;
          const isPre = s.includes("upcoming") || s.includes("forthcoming") || sub === null || sub === undefined;
          if (subFilter === "pre_apply") {
            if (!isPre) return false;
          } else if (subFilter === "oversubscribed") {
            if (isPre || sub < 1.0) return false;
          } else if (subFilter === "high_demand") {
            if (isPre || sub < 3.0) return false;
          } else if (subFilter === "undersubscribed") {
            if (isPre || sub >= 1.0) return false;
          }
        }

        // 3. Grey Market (GMP) Filter
        if (gmpFilter && !gmpFilter.startsWith("sort_")) {
          const gmp = ipo.gmp_percentage;
          if (gmpFilter === "has_gmp") {
            if (gmp === null || gmp === undefined) return false;
          } else if (gmpFilter === "gmp_25_plus") {
            if (gmp === null || gmp < 25.0) return false;
          } else if (gmpFilter === "gmp_15_plus") {
            if (gmp === null || gmp < 15.0) return false;
          } else if (gmpFilter === "no_gmp") {
            if (gmp !== null && gmp !== undefined) return false;
          }
        }

        return true;
      });

      // Sorting
      let activeCol = currentSortCol;
      let activeDir = currentSortDir;

      if (endDateFilter === "sort_asc") { activeCol = "close_date"; activeDir = "asc"; }
      else if (endDateFilter === "sort_desc") { activeCol = "close_date"; activeDir = "desc"; }
      else if (subFilter === "sort_desc") { activeCol = "sub"; activeDir = "desc"; }
      else if (subFilter === "sort_asc") { activeCol = "sub"; activeDir = "asc"; }
      else if (gmpFilter === "sort_desc") { activeCol = "gmp"; activeDir = "desc"; }
      else if (gmpFilter === "sort_asc") { activeCol = "gmp"; activeDir = "asc"; }

      if (activeCol) {
        filtered.sort((a, b) => {
          if (activeCol === "close_date") {
            const vA = a.close_date || "9999-99-99";
            const vB = b.close_date || "9999-99-99";
            return activeDir === "asc" ? vA.localeCompare(vB) : vB.localeCompare(vA);
          } else if (activeCol === "sub") {
            const vA = (a.subscription_times !== null && a.subscription_times !== undefined) ? a.subscription_times : -1;
            const vB = (b.subscription_times !== null && b.subscription_times !== undefined) ? b.subscription_times : -1;
            return activeDir === "asc" ? vA - vB : vB - vA;
          } else if (activeCol === "gmp") {
            const vA = (a.gmp_percentage !== null && a.gmp_percentage !== undefined) ? a.gmp_percentage : -999;
            const vB = (b.gmp_percentage !== null && b.gmp_percentage !== undefined) ? b.gmp_percentage : -999;
            return activeDir === "asc" ? vA - vB : vB - vA;
          } else if (activeCol === "company") {
            const vA = (a.company_name || "").toLowerCase();
            const vB = (b.company_name || "").toLowerCase();
            return activeDir === "asc" ? vA.localeCompare(vB) : vB.localeCompare(vA);
          } else if (activeCol === "size") {
            const vA = a.issue_size_cr || 0;
            const vB = b.issue_size_cr || 0;
            return activeDir === "asc" ? vA - vB : vB - vA;
          }
          return 0;
        });
      }

      // Update badge & live timestamp indicator
      if (!lastSyncedTimeStr) {
        lastSyncedTimeStr = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }).toLowerCase();
      }
      const lastSyncElem = document.getElementById("lastSyncedText");
      if (lastSyncElem) {
        lastSyncElem.innerText = `Updated at ${lastSyncedTimeStr} (${filtered.length} offerings)`;
      }

      const badge = document.getElementById("offeringsCountBadge");
      if (badge) {
        badge.innerText = `${filtered.length} Offerings`;
      }

      renderIPOs(filtered);
    }

    function filterIPOs() {
      applyAllFilters();
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

        const qibSub = r.subscription_data?.QIB?.subscription_multiple;
        const niiSub = r.subscription_data?.NII?.subscription_multiple;
        const retSub = r.subscription_data?.Retail?.subscription_multiple;
        const totalSub = r.subscription_data?.Total?.subscription_multiple;

        const subDisplay = totalSub !== undefined ? `${totalSub.toFixed(2)}x` : 'Data pending update';

        let finTableHtml = '';
        const fins = r.financial_data || [];
        if (fins.length > 0) {
          const rows = fins.map(f => {
            const rev = (f.revenue?.value !== undefined && f.revenue?.value !== null) ? `₹${Number(f.revenue.value).toFixed(1)} Cr` : '-';
            const pat = (f.PAT?.value !== undefined && f.PAT?.value !== null) ? `₹${Number(f.PAT.value).toFixed(1)} Cr` : '-';
            const roe = (f.ROE?.value !== undefined && f.ROE?.value !== null) ? `${Number(f.ROE.value).toFixed(1)}%` : '-';
            const de = (f.debt_equity?.value !== undefined && f.debt_equity?.value !== null) ? `${Number(f.debt_equity.value).toFixed(2)}x` : '-';
            const patGrowth = (f.PAT_growth?.value !== undefined && f.PAT_growth?.value !== null)
              ? `<span style="color: ${f.PAT_growth.value >= 0 ? '#34d399' : '#f87171'}; font-weight: 600;">${f.PAT_growth.value >= 0 ? '+' : ''}${Number(f.PAT_growth.value).toFixed(1)}%</span>`
              : '-';
            return `
              <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 0.45rem 0.5rem; font-weight: 600; color: #60a5fa;">${escapeHtml(f.financial_period || 'FY')}</td>
                <td style="padding: 0.45rem 0.5rem;">${rev}</td>
                <td style="padding: 0.45rem 0.5rem; color: #34d399; font-weight: 500;">${pat}</td>
                <td style="padding: 0.45rem 0.5rem; color: #fbbf24;">${roe}</td>
                <td style="padding: 0.45rem 0.5rem;">${de}</td>
                <td style="padding: 0.45rem 0.5rem;">${patGrowth}</td>
              </tr>
            `;
          }).join("");

          finTableHtml = `
            <div style="overflow-x: auto; margin-top: 0.5rem;">
              <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; text-align: left;">
                <thead>
                  <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase;">
                    <th style="padding: 0.4rem 0.5rem;">Period</th>
                    <th style="padding: 0.4rem 0.5rem;">Revenue</th>
                    <th style="padding: 0.4rem 0.5rem;">PAT (Profit)</th>
                    <th style="padding: 0.4rem 0.5rem;">ROE</th>
                    <th style="padding: 0.4rem 0.5rem;">D/E Ratio</th>
                    <th style="padding: 0.4rem 0.5rem;">PAT Growth</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          `;
        } else {
          finTableHtml = `
            <div style="padding: 0.85rem; background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.12); border-radius: var(--radius-sm); font-size: 0.82rem; color: var(--text-secondary); text-align: center; margin-top: 0.5rem;">
              ⚠️ 3-Year restated financials not yet loaded for this offering.<br>
              Click <strong>"Auto-Sync 3-Year Financials"</strong> below to scrape from Chittorgarh / SEBI RHP.
            </div>
          `;
        }

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
            <div class="metric-row"><span class="metric-label">Open Date</span><span class="metric-value">${formatMarketDate(r.ipo_status?.open_date)}</span></div>
            <div class="metric-row"><span class="metric-label">Close Date</span><span class="metric-value">${formatMarketDate(r.ipo_status?.close_date)}</span></div>
            <div class="metric-row"><span class="metric-label">Allotment Date</span><span class="metric-value" style="color: #60a5fa; font-weight: 600;">${formatMarketDate(r.ipo_status?.allotment_date)}</span></div>
            <div class="metric-row"><span class="metric-label">Listing Date</span><span class="metric-value" style="color: #34d399; font-weight: 600;">${formatMarketDate(r.ipo_status?.listing_date)}</span></div>
          </div>

          <!-- Phase 3: Granular Subscription Card -->
          <div class="card" style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <h4 style="margin: 0;">Institutional & Retail Demand</h4>
              <span class="badge badge-blue">Overall: ${subDisplay}</span>
            </div>
            <div class="metric-row"><span class="metric-label">🏛️ Qualified Institutional Buyers (QIB)</span><span class="metric-value" style="color: #60a5fa; font-weight: 700;">${qibSub !== undefined && qibSub !== null ? qibSub.toFixed(2) + 'x' : 'Data TBA'}</span></div>
            <div class="metric-row"><span class="metric-label">💼 Non-Institutional / HNI (NII)</span><span class="metric-value" style="color: #c084fc; font-weight: 700;">${niiSub !== undefined && niiSub !== null ? niiSub.toFixed(2) + 'x' : 'Data TBA'}</span></div>
            <div class="metric-row"><span class="metric-label">👥 Retail Individual Investors (RII)</span><span class="metric-value" style="color: #fbbf24; font-weight: 700;">${retSub !== undefined && retSub !== null ? retSub.toFixed(2) + 'x' : 'Data TBA'}</span></div>
          </div>

          <!-- Phase 4: 3-Year Financials Card -->
          <div class="card" style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
              <h4 style="margin: 0;">3-Year Restated Financials</h4>
              <span style="font-size: 0.72rem; color: var(--text-muted);">Source: Chittorgarh / SEBI RHP</span>
            </div>
            ${finTableHtml}
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end; align-items: center; margin-top: 1rem;">
            <button 
              id="syncFinBtn"
              class="btn btn-secondary" 
              onclick="triggerSyncFinancials('${escapeHtml(data.ipo_id)}', '${escapeHtml(data.company_name)}')"
              title="Scrape and calculate 3-year financials & ratios">
              🔄 Auto-Sync 3-Year Financials
            </button>
            <button 
              class="btn" 
              onclick="closeModalDirect(); quickEvaluate('${escapeHtml(data.ipo_id)}')"
              title="Execute Recommendation Intelligence Engine">
              Run Recommendation Evaluation
            </button>
          </div>
        `;

        document.getElementById("detailModal").classList.add("active");
      } catch (e) {
        showAlert(`Error loading details: ${e.message}`, "error");
      }
    }

    async function triggerSyncFinancials(ipoId, companyName) {
      const syncBtn = document.getElementById("syncFinBtn");
      if (syncBtn) {
        syncBtn.disabled = true;
        syncBtn.innerText = "⏳ Scraping Chittorgarh / RHP...";
      }
      try {
        const res = await fetch(`/ipos/${encodeURIComponent(ipoId)}/sync-financials`, {
          method: "POST",
          headers: getAuthHeaders()
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`Financial sync failed: ${err.detail || res.statusText}`, "error");
          if (syncBtn) {
            syncBtn.disabled = false;
            syncBtn.innerText = "🔄 Auto-Sync 3-Year Financials";
          }
          return;
        }
        const data = await res.json();
        showAlert(`Successfully synced 3-year financials for ${companyName}! Recommendation updated.`, "info");
        // Reopen modal with updated financials
        openIpoDetails(ipoId);
      } catch (e) {
        showAlert(`Network error syncing financials: ${e.message}`, "error");
        if (syncBtn) {
          syncBtn.disabled = false;
          syncBtn.innerText = "🔄 Auto-Sync 3-Year Financials";
        }
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

    function loadSampleRhp() {
      const sample = `Company Name: SolarGrid Infrastructure Technologies Limited
CIN: U40106DL2018PLC339482
Price Band: ₹315 to ₹330 per Equity Share
Total Issue Size: Aggregating up to ₹850.00 Crore
Fresh Issue: Aggregating up to ₹550.00 Crore
Offer for Sale: Aggregating up to ₹300.00 Crore
Minimum Bid Quantity: 45 Equity Shares
Bid/Offer Opens on: 2026-10-20
Bid/Offer Closes on: 2026-10-23
Revenue from Operations: ₹940.50 Crore
Profit After Tax: ₹112.40 Crore
EBITDA: ₹235.80 Crore
Total Borrowings: ₹180.20 Crore
Net Worth: ₹620.00 Crore
Implied P/E: 27.50

Objects of the Issue:
- Funding capital expenditure for grid expansion: ₹280.00 Crore
- Prepayment of term loan borrowings: ₹150.00 Crore
- General corporate purposes: ₹120.00 Crore

Key Risk Factors:
- Revenues are dependent on long-term power purchase agreements (PPAs) with state discoms.
- Material regulatory litigations pending before appellate tribunals.
- Counterparty credit risk associated with delayed receivables from government entities.`;
      document.getElementById("rhpTextInput").value = sample;
    }

    async function parseRhpFiling() {
      const text = document.getElementById("rhpTextInput").value.trim();
      if (!text) {
        showAlert("Please paste filing text or click 'Load Sample Filing Text'", "error");
        return;
      }
      const directIngest = document.getElementById("rhpDirectIngest").checked;
      showAlert("Parsing and validating prospectus document...", "info");

      try {
        const res = await fetch("/ipos/parse-rhp", {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            text: text,
            source_id: "SRC-SEBI-RHP-DASHBOARD",
            ingest: directIngest
          })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showAlert(`RHP Parsing Error: ${err.detail || res.statusText}`, "error");
          return;
        }

        const data = await res.json();
        document.getElementById("rhpResultCard").style.display = "block";
        document.getElementById("rhpCompanyName").innerText = data.company_name;
        document.getElementById("rhpIpoId").innerText = `${data.ipo_id} (${data.symbol})`;
        document.getElementById("rhpBadge").innerText = directIngest ? "INGESTED INTO MYSQL" : "EXTRACTED (DRY-RUN)";
        document.getElementById("rhpBadge").className = `badge ${directIngest ? 'badge-green' : 'badge-blue'}`;

        const content = document.getElementById("rhpDetailsContent");
        content.innerHTML = `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0;">
            <div class="card" style="padding: 0.75rem;"><div style="font-size: 0.75rem; color: var(--text-secondary);">Price Band</div><div style="font-size: 1.1rem; font-weight: 600;">${escapeHtml(data.price_band)}</div></div>
            <div class="card" style="padding: 0.75rem;"><div style="font-size: 0.75rem; color: var(--text-secondary);">Issue Size</div><div style="font-size: 1.1rem; font-weight: 600;">₹${data.issue_size_cr.toFixed(2)} Cr</div></div>
            <div class="card" style="padding: 0.75rem;"><div style="font-size: 0.75rem; color: var(--text-secondary);">Revenue / PAT</div><div style="font-size: 1.1rem; font-weight: 600;">₹${data.financials.revenue_cr.toFixed(0)}Cr / ₹${data.financials.pat_cr.toFixed(1)}Cr</div></div>
            <div class="card" style="padding: 0.75rem;"><div style="font-size: 0.75rem; color: var(--text-secondary);">Return on Equity (ROE)</div><div style="font-size: 1.1rem; font-weight: 600; color: var(--accent-green);">${data.financials.roe.toFixed(1)}%</div></div>
          </div>
          <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
            <button class="btn" onclick="quickEvaluate('${escapeHtml(data.ipo_id)}')">Evaluate in Recommendation Engine</button>
            <button class="btn btn-secondary" onclick="loadIPOs(); switchTab('iposTab', document.querySelectorAll('.nav-tab')[0])">View in All Offerings</button>
          </div>
        `;

        showAlert(directIngest ? "Prospectus extracted and successfully persisted into database!" : "Prospectus extracted successfully!", "success");
        if (directIngest) {
          loadIPOs();
        }
      } catch (e) {
        showAlert(`Network error: ${e.message}`, "error");
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
