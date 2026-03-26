from flask import Flask, render_template_string, request, jsonify, redirect, session
import json, os, requests as req_lib

# ══════════════════════════════════════════════════════════════
#  HTML — UI COMPLETA EMBEBIDA
# ══════════════════════════════════════════════════════════════
PANEL_HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>The Family — Panel</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #04080f;
  --bg2:      #070d1a;
  --bg3:      #0b1325;
  --card:     rgba(11,19,37,0.85);
  --border:   rgba(59,130,246,0.12);
  --border2:  rgba(59,130,246,0.22);
  --blue:     #3b82f6;
  --blue-l:   #60a5fa;
  --purple:   #8b5cf6;
  --purple-l: #a78bfa;
  --green:    #22c55e;
  --yellow:   #f59e0b;
  --red:      #ef4444;
  --text:     #e2e8f0;
  --muted:    #64748b;
  --muted2:   #94a3b8;
  --mono:     'JetBrains Mono', monospace;
  --sans:     'Plus Jakarta Sans', sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--sans)}

/* ── BACKGROUND ── */
body::before{
  content:'';position:fixed;inset:0;z-index:0;
  background:
    radial-gradient(ellipse 60% 50% at 10% 20%, rgba(59,130,246,0.07) 0%, transparent 70%),
    radial-gradient(ellipse 50% 60% at 90% 80%, rgba(139,92,246,0.06) 0%, transparent 70%);
  pointer-events:none;
}

/* ── LAYOUT ── */
.layout{display:flex;height:100vh;position:relative;z-index:1}

/* ── SIDEBAR ── */
.sidebar{
  width:240px;flex-shrink:0;
  background:rgba(7,13,26,0.95);
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;
  padding:0 0 16px 0;
  overflow-y:auto;
}
.sidebar-brand{
  padding:22px 20px 18px;
  border-bottom:1px solid var(--border);
  margin-bottom:8px;
}
.brand-logo{
  font-size:18px;font-weight:800;
  background:linear-gradient(135deg,var(--blue-l),var(--purple-l));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  display:flex;align-items:center;gap:8px;
}
.brand-sub{font-size:11px;color:var(--muted);margin-top:3px;font-family:var(--mono)}
.nav-section-label{
  font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--muted);padding:14px 20px 6px;
}
.nav-item{
  display:flex;align-items:center;gap:10px;
  padding:9px 16px 9px 20px;
  font-size:13px;font-weight:600;color:var(--muted2);
  cursor:pointer;border:none;background:none;width:100%;text-align:left;
  border-radius:0;transition:all .15s;position:relative;
}
.nav-item:hover{color:var(--text);background:rgba(59,130,246,0.06)}
.nav-item.active{color:var(--blue-l);background:rgba(59,130,246,0.1)}
.nav-item.active::before{
  content:'';position:absolute;left:0;top:4px;bottom:4px;
  width:3px;background:var(--blue);border-radius:0 3px 3px 0;
}
.nav-icon{font-size:15px;width:18px;text-align:center}
.nav-badge{
  margin-left:auto;background:var(--red);color:#fff;
  font-size:10px;font-weight:700;padding:2px 6px;border-radius:20px;
}
.sidebar-bottom{margin-top:auto;padding:0 12px}
.btn-logout{
  width:100%;padding:10px 16px;border-radius:10px;border:1px solid rgba(239,68,68,0.2);
  background:rgba(239,68,68,0.06);color:#f87171;font-family:var(--sans);
  font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:8px;
  transition:all .15s;
}
.btn-logout:hover{background:rgba(239,68,68,0.12);border-color:rgba(239,68,68,0.35)}

/* ── TOPBAR ── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{
  height:60px;flex-shrink:0;
  background:rgba(7,13,26,0.8);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;
  padding:0 28px;gap:16px;
  backdrop-filter:blur(12px);
}
.topbar-title{font-size:15px;font-weight:700;flex:1}
.topbar-badge{
  display:flex;align-items:center;gap:6px;
  background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.2);
  color:var(--green);font-size:12px;font-weight:600;
  padding:5px 12px;border-radius:20px;
}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.guild-info{display:flex;align-items:center;gap:10px}
.guild-icon{width:32px;height:32px;border-radius:50%;object-fit:cover;border:2px solid var(--border2)}
.guild-icon-placeholder{
  width:32px;height:32px;border-radius:50%;
  background:linear-gradient(135deg,var(--blue),var(--purple));
  display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;
}
.guild-name{font-size:13px;font-weight:700}
.guild-members{font-size:11px;color:var(--muted);font-family:var(--mono)}

/* ── CONTENT ── */
.content{flex:1;overflow-y:auto;padding:28px 28px 40px}
.page{display:none;animation:fadeIn .2s ease}
.page.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* ── PAGE HEADER ── */
.page-header{margin-bottom:24px}
.page-title{font-size:22px;font-weight:800}
.page-sub{font-size:13px;color:var(--muted);margin-top:4px}

/* ── STATS GRID ── */
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}
.stat-card{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:18px 20px;position:relative;overflow:hidden;
}
.stat-card::after{
  content:'';position:absolute;top:-20px;right:-20px;
  width:70px;height:70px;border-radius:50%;
  background:var(--accent-color, var(--blue));opacity:.06;
}
.stat-label{font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.stat-value{font-size:28px;font-weight:800;font-family:var(--mono)}
.stat-sub{font-size:11px;color:var(--muted);margin-top:4px}
.accent-blue{--accent-color:var(--blue);color:var(--blue-l)}
.accent-green{--accent-color:var(--green);color:var(--green)}
.accent-purple{--accent-color:var(--purple);color:var(--purple-l)}
.accent-yellow{--accent-color:var(--yellow);color:var(--yellow)}

/* ── CARDS ── */
.card{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:22px 24px;margin-bottom:18px;
  backdrop-filter:blur(8px);
}
.card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.card-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}
.card-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.card-grid.cols3{grid-template-columns:1fr 1fr 1fr}
.card-grid.full{grid-template-columns:1fr}

/* ── FORM ── */
.form-group{display:flex;flex-direction:column;gap:6px}
.form-label{font-size:12px;font-weight:600;color:var(--muted2)}
input[type=text],input[type=url],input[type=password],input[type=number],select,textarea{
  background:rgba(255,255,255,0.04);
  border:1px solid var(--border2);
  border-radius:10px;color:var(--text);
  font-family:var(--mono);font-size:13px;
  padding:10px 13px;outline:none;
  transition:border .2s,background .2s;width:100%;
}
input:focus,select:focus,textarea:focus{
  border-color:var(--blue);background:rgba(59,130,246,0.05);
}
select option{background:var(--bg3)}
textarea{resize:vertical;min-height:80px;font-family:var(--sans)}

/* ── TOGGLE ── */
.toggle-row{display:flex;align-items:center;justify-content:space-between;padding:4px 0;margin-bottom:18px}
.toggle-label{font-size:14px;font-weight:600}
.toggle-desc{font-size:12px;color:var(--muted);margin-top:2px}
.toggle{position:relative;width:44px;height:24px;flex-shrink:0}
.toggle input{opacity:0;width:0;height:0}
.slider{
  position:absolute;inset:0;border-radius:24px;
  background:rgba(255,255,255,0.1);cursor:pointer;transition:.25s;
}
.slider:before{
  content:'';position:absolute;
  height:18px;width:18px;left:3px;bottom:3px;
  background:#fff;border-radius:50%;transition:.25s;
}
input:checked+.slider{background:var(--blue)}
input:checked+.slider:before{transform:translateX(20px)}

/* ── BUTTONS ── */
.btn{
  display:inline-flex;align-items:center;gap:7px;
  background:linear-gradient(135deg,var(--blue),var(--purple));
  border:none;border-radius:10px;color:#fff;
  font-family:var(--sans);font-size:13px;font-weight:700;
  padding:10px 20px;cursor:pointer;transition:opacity .2s,transform .1s;
}
.btn:hover{opacity:.88}
.btn:active{transform:scale(.98)}
.btn-sm{padding:7px 14px;font-size:12px;border-radius:8px}
.btn-danger{background:linear-gradient(135deg,#dc2626,#b91c1c)}
.btn-ghost{background:rgba(255,255,255,0.06);border:1px solid var(--border2);color:var(--text)}
.btn-ghost:hover{background:rgba(255,255,255,0.1)}
.btn-success{background:linear-gradient(135deg,#16a34a,#15803d)}
.btn-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}

/* ── TABLE ── */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);padding:10px 14px;border-bottom:1px solid var(--border)}
td{padding:11px 14px;border-bottom:1px solid rgba(59,130,246,0.05);color:var(--muted2)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(59,130,246,0.03)}
.tag{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
.tag-blue{background:rgba(59,130,246,0.15);color:var(--blue-l)}
.tag-green{background:rgba(34,197,94,0.12);color:var(--green)}
.tag-red{background:rgba(239,68,68,0.12);color:#f87171}
.tag-yellow{background:rgba(245,158,11,0.12);color:var(--yellow)}
.tag-purple{background:rgba(139,92,246,0.15);color:var(--purple-l)}

/* ── MEMBER LIST ── */
.member-item{
  display:flex;align-items:center;gap:12px;
  padding:10px 14px;border-radius:10px;
  transition:background .15s;cursor:default;
}
.member-item:hover{background:rgba(59,130,246,0.05)}
.member-avatar{
  width:36px;height:36px;border-radius:50%;object-fit:cover;
  border:2px solid var(--border2);flex-shrink:0;
}
.member-avatar-placeholder{
  width:36px;height:36px;border-radius:50%;flex-shrink:0;
  background:linear-gradient(135deg,var(--blue),var(--purple));
  display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;
}
.member-name{font-size:13px;font-weight:600}
.member-tag{font-size:11px;color:var(--muted);font-family:var(--mono)}
.member-actions{margin-left:auto;display:flex;gap:6px;opacity:0;transition:opacity .15s}
.member-item:hover .member-actions{opacity:1}

/* ── CHANNEL LIST ── */
.channel-item{
  display:flex;align-items:center;gap:10px;
  padding:9px 12px;border-radius:8px;
  font-size:13px;font-weight:500;color:var(--muted2);
  transition:background .15s;
}
.channel-item:hover{background:rgba(59,130,246,0.06);color:var(--text)}
.channel-actions{margin-left:auto;display:flex;gap:6px;opacity:0;transition:opacity .15s}
.channel-item:hover .channel-actions{opacity:1}

/* ── TOAST ── */
.toast{
  position:fixed;bottom:24px;right:24px;z-index:9999;
  background:rgba(11,19,37,0.98);border:1px solid var(--border2);
  border-radius:12px;padding:12px 18px;
  font-size:13px;font-weight:600;
  display:flex;align-items:center;gap:8px;
  transform:translateY(80px);opacity:0;
  transition:all .3s cubic-bezier(.34,1.56,.64,1);
  backdrop-filter:blur(12px);
  box-shadow:0 8px 32px rgba(0,0,0,.4);
}
.toast.show{transform:translateY(0);opacity:1}
.toast.success{border-color:rgba(34,197,94,.3);color:var(--green)}
.toast.error{border-color:rgba(239,68,68,.3);color:#f87171}

/* ── MODAL ── */
.modal-overlay{
  position:fixed;inset:0;z-index:1000;
  background:rgba(0,0,0,.6);backdrop-filter:blur(6px);
  display:none;align-items:center;justify-content:center;
}
.modal-overlay.open{display:flex}
.modal{
  background:var(--bg3);border:1px solid var(--border2);
  border-radius:18px;padding:28px;width:100%;max-width:440px;
  box-shadow:0 24px 60px rgba(0,0,0,.5);
}
.modal-title{font-size:16px;font-weight:800;margin-bottom:18px}

/* ── HELP ── */
.help{
  background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,.15);
  border-radius:10px;padding:12px 16px;font-size:12px;
  color:var(--muted2);margin-bottom:16px;line-height:1.7;
}
.help b{color:var(--blue-l)}

/* ── SEARCH ── */
.search-input{
  background:rgba(255,255,255,0.04);border:1px solid var(--border2);
  border-radius:10px;color:var(--text);font-family:var(--sans);font-size:13px;
  padding:9px 14px;outline:none;transition:border .2s;width:100%;max-width:260px;
}
.search-input:focus{border-color:var(--blue)}

/* ── PROGRESS ── */
.progress-bar{height:6px;border-radius:6px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:10px}
.progress-fill{height:100%;border-radius:6px;background:linear-gradient(90deg,var(--blue),var(--purple));transition:width .4s}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(59,130,246,.2);border-radius:6px}
::-webkit-scrollbar-thumb:hover{background:rgba(59,130,246,.35)}

/* ── DIVIDER ── */
.sep{height:1px;background:var(--border);margin:20px 0}

/* ── WORD CHIP ── */
.chip-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);
  color:#f87171;font-size:12px;font-weight:600;
  padding:4px 10px;border-radius:20px;
}
.chip-del{cursor:pointer;font-size:14px;line-height:1;opacity:.7}
.chip-del:hover{opacity:1}

/* ── CUSTOM CMD ── */
.cmd-item{
  display:flex;align-items:center;gap:12px;
  padding:10px 14px;border-radius:10px;
  background:rgba(255,255,255,.03);border:1px solid var(--border);
  margin-bottom:8px;
}
.cmd-trigger{font-family:var(--mono);font-size:12px;color:var(--blue-l);background:rgba(59,130,246,.1);padding:3px 8px;border-radius:6px}
.cmd-response{font-size:12px;color:var(--muted2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ── LOGIN ── */
.login-wrap{
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:var(--bg);position:relative;overflow:hidden;
}
.login-wrap::before{
  content:'';position:absolute;inset:0;
  background:
    radial-gradient(ellipse 70% 60% at 30% 30%,rgba(59,130,246,.1) 0%,transparent 60%),
    radial-gradient(ellipse 60% 70% at 80% 80%,rgba(139,92,246,.08) 0%,transparent 60%);
}
.login-card{
  background:rgba(11,19,37,.9);border:1px solid var(--border2);
  border-radius:22px;padding:44px 40px;width:100%;max-width:400px;
  backdrop-filter:blur(20px);position:relative;z-index:1;
  box-shadow:0 24px 60px rgba(0,0,0,.5);
}
.login-logo{
  font-size:28px;font-weight:800;text-align:center;
  background:linear-gradient(135deg,var(--blue-l),var(--purple-l));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  margin-bottom:6px;
}
.login-sub{text-align:center;font-size:13px;color:var(--muted);margin-bottom:32px;font-family:var(--mono)}
.login-error{
  background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);
  color:#f87171;font-size:13px;text-align:center;
  padding:10px 16px;border-radius:10px;margin-bottom:16px;
}
.login-input{
  width:100%;background:rgba(255,255,255,.05);border:1px solid var(--border2);
  border-radius:12px;color:var(--text);font-family:var(--sans);font-size:14px;
  padding:14px 16px;outline:none;margin-bottom:12px;transition:border .2s;
}
.login-input:focus{border-color:var(--blue);background:rgba(59,130,246,.05)}
.login-btn{
  width:100%;background:linear-gradient(135deg,var(--blue),var(--purple));
  border:none;border-radius:12px;color:#fff;font-family:var(--sans);
  font-size:15px;font-weight:700;padding:14px;cursor:pointer;transition:opacity .2s;
}
.login-btn:hover{opacity:.88}
</style>
</head>

{% if not logged_in %}
<body>
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">⚡ The Family</div>
    <div class="login-sub">Panel de Administración</div>
    {% if error %}<div class="login-error">{{ error }}</div>{% endif %}
    <form method="POST" action="/login">
      <input class="login-input" type="password" name="password" placeholder="Contraseña del panel" autofocus>
      <button class="login-btn" type="submit">Entrar al Panel</button>
    </form>
  </div>
</div>
</body>
{% else %}
<body>
<div class="layout">

<!-- ── SIDEBAR ── -->
<nav class="sidebar">
  <div class="sidebar-brand">
    <div class="brand-logo">⚡ The Family</div>
    <div class="brand-sub" id="guild-name-brand">Cargando...</div>
  </div>

  <div class="nav-section-label">General</div>
  <button class="nav-item active" data-page="dashboard"><span class="nav-icon">🏠</span> Dashboard</button>
  <button class="nav-item" data-page="members"><span class="nav-icon">👥</span> Miembros</button>
  <button class="nav-item" data-page="channels"><span class="nav-icon">📢</span> Canales</button>
  <button class="nav-item" data-page="roles"><span class="nav-icon">🏷️</span> Roles</button>

  <div class="nav-section-label">Configuración</div>
  <button class="nav-item" data-page="welcome"><span class="nav-icon">👋</span> Bienvenida</button>
  <button class="nav-item" data-page="xp"><span class="nav-icon">⭐</span> Sistema XP</button>
  <button class="nav-item" data-page="reaction_roles"><span class="nav-icon">🎭</span> Reaction Roles</button>
  <button class="nav-item" data-page="stream"><span class="nav-icon">🔴</span> Stream Alerts</button>
  <button class="nav-item" data-page="moderation"><span class="nav-icon">🛡️</span> Moderación</button>
  <button class="nav-item" data-page="logs"><span class="nav-icon">📋</span> Logs</button>

  <div class="nav-section-label">Herramientas</div>
  <button class="nav-item" data-page="announce"><span class="nav-icon">📣</span> Anunciar</button>
  <button class="nav-item" data-page="custom_cmds"><span class="nav-icon">⚡</span> Comandos Custom</button>
  <button class="nav-item" data-page="leaderboard"><span class="nav-icon">🏆</span> Leaderboard</button>

  <div class="sidebar-bottom">
    <a href="/logout"><button class="btn-logout">🚪 Cerrar sesión</button></a>
  </div>
</nav>

<!-- ── MAIN ── -->
<div class="main">

  <!-- TOPBAR -->
  <div class="topbar">
    <div class="topbar-title" id="topbar-title">Dashboard</div>
    <div class="topbar-badge"><span class="dot"></span> Bot Online</div>
    <div class="guild-info" id="guild-info-topbar">
      <div class="guild-icon-placeholder" id="guild-icon-ph">?</div>
      <div>
        <div class="guild-name" id="guild-name-top">—</div>
        <div class="guild-members" id="guild-members-top">— miembros</div>
      </div>
    </div>
  </div>

  <!-- CONTENT -->
  <div class="content">

    <!-- ════════════ DASHBOARD ════════════ -->
    <div class="page active" id="page-dashboard">
      <div class="page-header">
        <div class="page-title">Dashboard</div>
        <div class="page-sub">Vista general de tu servidor</div>
      </div>
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">Miembros</div><div class="stat-value accent-blue" id="stat-members">—</div><div class="stat-sub">Total en el servidor</div></div>
        <div class="stat-card"><div class="stat-label">Canales</div><div class="stat-value accent-purple" id="stat-channels">—</div><div class="stat-sub">Texto + voz</div></div>
        <div class="stat-card"><div class="stat-label">Roles</div><div class="stat-value accent-yellow" id="stat-roles">—</div><div class="stat-sub">Roles configurados</div></div>
        <div class="stat-card"><div class="stat-label">Emojis</div><div class="stat-value accent-green" id="stat-emojis">—</div><div class="stat-sub">Emojis personalizados</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div class="card">
          <div class="card-header"><div class="card-title">Módulos Activos</div></div>
          <div id="modules-status"></div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">Comandos Slash</div></div>
          <table>
            <tr><th>Comando</th><th>Acceso</th></tr>
            <tr><td>/ping</td><td><span class="tag tag-green">Todos</span></td></tr>
            <tr><td>/rank</td><td><span class="tag tag-green">Todos</span></td></tr>
            <tr><td>/leaderboard</td><td><span class="tag tag-green">Todos</span></td></tr>
            <tr><td>/serverinfo</td><td><span class="tag tag-green">Todos</span></td></tr>
            <tr><td>/userinfo</td><td><span class="tag tag-green">Todos</span></td></tr>
            <tr><td>/warn /warns</td><td><span class="tag tag-yellow">Staff</span></td></tr>
            <tr><td>/clear /kick /timeout</td><td><span class="tag tag-yellow">Staff</span></td></tr>
            <tr><td>/ban /say /embed</td><td><span class="tag tag-red">Admin</span></td></tr>
            <tr><td>/sorteo /panel</td><td><span class="tag tag-red">Admin</span></td></tr>
          </table>
        </div>
      </div>
    </div>

    <!-- ════════════ MIEMBROS ════════════ -->
    <div class="page" id="page-members">
      <div class="page-header">
        <div class="page-title">Miembros</div>
        <div class="page-sub">Gestiona los miembros de tu servidor</div>
      </div>
      <div class="card">
        <div class="card-header">
          <div class="card-title">Lista de Miembros</div>
          <input class="search-input" id="member-search" placeholder="🔍 Buscar miembro..." oninput="filterMembers(this.value)">
        </div>
        <div id="members-list">
          <div style="color:var(--muted);font-size:13px;padding:12px 0">Cargando miembros...</div>
        </div>
      </div>
    </div>

    <!-- ════════════ CANALES ════════════ -->
    <div class="page" id="page-channels">
      <div class="page-header">
        <div class="page-title">Canales</div>
        <div class="page-sub">Crear y eliminar canales directamente desde el panel</div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Crear Canal</div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Nombre del canal</div><input type="text" id="new-ch-name" placeholder="general"></div>
          <div class="form-group"><div class="form-label">Tipo</div>
            <select id="new-ch-type">
              <option value="0">💬 Texto</option>
              <option value="2">🔊 Voz</option>
              <option value="5">📢 Anuncio</option>
            </select>
          </div>
        </div>
        <div class="card-grid" style="margin-top:12px">
          <div class="form-group"><div class="form-label">Categoría (opcional)</div><select id="new-ch-category"><option value="">Sin categoría</option></select></div>
          <div class="form-group"><div class="form-label">Tema / Descripción</div><input type="text" id="new-ch-topic" placeholder="Descripción del canal"></div>
        </div>
        <div class="btn-row"><button class="btn" onclick="createChannel()">➕ Crear Canal</button></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Canales Actuales</div></div>
        <div id="channels-list">Cargando...</div>
      </div>
    </div>

    <!-- ════════════ ROLES ════════════ -->
    <div class="page" id="page-roles">
      <div class="page-header">
        <div class="page-title">Roles</div>
        <div class="page-sub">Crear y administrar roles del servidor</div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Crear Rol</div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Nombre del rol</div><input type="text" id="new-role-name" placeholder="Miembro VIP"></div>
          <div class="form-group"><div class="form-label">Color (hex)</div><input type="text" id="new-role-color" placeholder="e.g. 3b82f6" maxlength="6"></div>
        </div>
        <div class="card-grid" style="margin-top:12px">
          <div class="form-group" style="flex-direction:row;align-items:center;gap:10px;padding-top:8px">
            <label class="toggle"><input type="checkbox" id="new-role-hoist"><span class="slider"></span></label>
            <span style="font-size:13px;font-weight:600">Mostrar separado en la lista</span>
          </div>
          <div class="form-group" style="flex-direction:row;align-items:center;gap:10px;padding-top:8px">
            <label class="toggle"><input type="checkbox" id="new-role-mentionable"><span class="slider"></span></label>
            <span style="font-size:13px;font-weight:600">Mencionable</span>
          </div>
        </div>
        <div class="btn-row"><button class="btn" onclick="createRole()">➕ Crear Rol</button></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Roles Actuales</div></div>
        <div id="roles-list">Cargando...</div>
      </div>
    </div>

    <!-- ════════════ BIENVENIDA ════════════ -->
    <div class="page" id="page-welcome">
      <div class="page-header">
        <div class="page-title">Bienvenida y Despedida</div>
        <div class="page-sub">Configura los mensajes automáticos para nuevos miembros</div>
      </div>
      <div class="card">
        <div class="toggle-row">
          <div><div class="toggle-label">Bienvenida automática</div><div class="toggle-desc">Mensaje al entrar un miembro</div></div>
          <label class="toggle"><input type="checkbox" id="welcome-enabled"><span class="slider"></span></label>
        </div>
        <div class="help"><b>Variables:</b> {user} menciona, {username} nombre, {server} servidor, {count} total miembros</div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Canal de bienvenida</div>
            <select id="welcome-channel"><option value="">— Elegir canal —</option></select>
          </div>
          <div class="form-group"><div class="form-label">Rol automático al entrar</div>
            <select id="welcome-role"><option value="">— Sin rol automático —</option></select>
          </div>
        </div>
        <div class="card-grid full" style="margin-top:12px">
          <div class="form-group"><div class="form-label">Mensaje de bienvenida</div>
            <textarea id="welcome-message" placeholder="👋 Bienvenido/a {user} a **{server}**!"></textarea>
          </div>
        </div>
        <div class="card-grid full" style="margin-top:12px">
          <div class="form-group"><div class="form-label">URL del banner de bienvenida</div>
            <input type="url" id="welcome-banner" placeholder="https://imagen.com/banner.png">
          </div>
        </div>
        <div class="btn-row"><button class="btn" onclick="saveWelcome()">💾 Guardar Bienvenida</button></div>
      </div>
      <div class="card">
        <div class="toggle-row">
          <div><div class="toggle-label">Despedida automática</div><div class="toggle-desc">Mensaje al salir un miembro</div></div>
          <label class="toggle"><input type="checkbox" id="goodbye-enabled"><span class="slider"></span></label>
        </div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Canal de despedida</div>
            <select id="goodbye-channel"><option value="">— Elegir canal —</option></select>
          </div>
          <div class="form-group"><div class="form-label">Mensaje de despedida</div>
            <input type="text" id="goodbye-message" placeholder="👋 {username} salió del servidor.">
          </div>
        </div>
        <div class="btn-row"><button class="btn" onclick="saveGoodbye()">💾 Guardar Despedida</button></div>
      </div>
    </div>

    <!-- ════════════ XP ════════════ -->
    <div class="page" id="page-xp">
      <div class="page-header">
        <div class="page-title">Sistema de XP</div>
        <div class="page-sub">Los usuarios ganan 15 XP por mensaje (cooldown 60s)</div>
      </div>
      <div class="card">
        <div class="toggle-row">
          <div><div class="toggle-label">Activar sistema de XP y niveles</div></div>
          <label class="toggle"><input type="checkbox" id="xp-enabled"><span class="slider"></span></label>
        </div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Canal para anunciar subidas de nivel</div>
            <select id="xp-channel"><option value="">— Mismo canal del mensaje —</option></select>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn" onclick="saveXP()">💾 Guardar</button>
          <button class="btn btn-danger" onclick="if(confirm('¿Reiniciar todo el XP?')) resetXP()">🗑️ Resetear todo el XP</button>
        </div>
      </div>
    </div>

    <!-- ════════════ REACTION ROLES ════════════ -->
    <div class="page" id="page-reaction_roles">
      <div class="page-header">
        <div class="page-title">Reaction Roles</div>
        <div class="page-sub">Asigna roles automáticamente al reaccionar a un mensaje</div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Agregar Reaction Role</div>
        <div class="help">
          1. Envía un mensaje en Discord con <b>/embed</b> o <b>/say</b><br>
          2. Click derecho → <b>Copiar ID del mensaje</b> (activa modo desarrollador en Ajustes → Avanzado)<br>
          3. Completa los campos y agrega
        </div>
        <div class="card-grid cols3">
          <div class="form-group"><div class="form-label">ID del mensaje</div><input type="text" id="rr-msg-id" placeholder="123456789012345678"></div>
          <div class="form-group"><div class="form-label">Emoji</div><input type="text" id="rr-emoji" placeholder="🎮"></div>
          <div class="form-group"><div class="form-label">Rol a asignar</div>
            <select id="rr-role"><option value="">— Elegir rol —</option></select>
          </div>
        </div>
        <div class="btn-row"><button class="btn" onclick="addRR()">➕ Agregar</button></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Reaction Roles Activos</div></div>
        <div class="table-wrap">
          <table id="rr-table">
            <tr><th>Mensaje ID</th><th>Emoji</th><th>Rol ID</th><th>Acción</th></tr>
          </table>
        </div>
        <div id="rr-empty" style="color:var(--muted);font-size:13px;padding:12px 0;display:none">No hay reaction roles configurados.</div>
      </div>
    </div>

    <!-- ════════════ STREAM ════════════ -->
    <div class="page" id="page-stream">
      <div class="page-header">
        <div class="page-title">Stream Alerts</div>
        <div class="page-sub">El bot avisa cuando estás en vivo (verificación cada 5 min)</div>
      </div>
      <div class="card">
        <div class="toggle-row">
          <div><div class="toggle-label">Activar alertas de stream</div></div>
          <label class="toggle"><input type="checkbox" id="stream-enabled"><span class="slider"></span></label>
        </div>
        <div class="help"><b>Variables:</b> {username} tu usuario, {url} link al stream, {title} título del stream</div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Canal de alertas</div>
            <select id="stream-channel"><option value="">— Elegir canal —</option></select>
          </div>
        </div>
        <div class="card-grid" style="margin-top:12px">
          <div class="form-group"><div class="form-label">Usuario de Kick</div><input type="text" id="stream-kick" placeholder="tuusuario"></div>
          <div class="form-group"><div class="form-label">Usuario de TikTok</div><input type="text" id="stream-tiktok" placeholder="@tuusuario"></div>
        </div>
        <div class="card-grid full" style="margin-top:12px">
          <div class="form-group"><div class="form-label">Mensaje de alerta</div>
            <textarea id="stream-message" placeholder="🔴 {username} está en vivo! → {url}"></textarea>
          </div>
        </div>
        <div class="btn-row"><button class="btn" onclick="saveStream()">💾 Guardar</button></div>
      </div>
    </div>

    <!-- ════════════ MODERACIÓN ════════════ -->
    <div class="page" id="page-moderation">
      <div class="page-header">
        <div class="page-title">Moderación</div>
        <div class="page-sub">Protección automática del servidor</div>
      </div>
      <div class="card">
        <div class="toggle-row">
          <div><div class="toggle-label">Anti-Links</div><div class="toggle-desc">Borra links de usuarios sin permisos</div></div>
          <label class="toggle"><input type="checkbox" id="mod-antilinks"><span class="slider"></span></label>
        </div>
        <div class="sep"></div>
        <div class="toggle-row">
          <div><div class="toggle-label">Anti-Spam</div><div class="toggle-desc">Detecta mensajes repetidos</div></div>
          <label class="toggle"><input type="checkbox" id="mod-antispam"><span class="slider"></span></label>
        </div>
        <div class="btn-row"><button class="btn" onclick="saveMod()">💾 Guardar</button></div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Filtro de Palabras</div>
        <div class="toggle-row">
          <div><div class="toggle-label">Activar filtro</div></div>
          <label class="toggle"><input type="checkbox" id="wf-enabled"><span class="slider"></span></label>
        </div>
        <div style="display:flex;gap:10px;margin-top:4px">
          <input type="text" id="wf-input" placeholder="Agregar palabra prohibida..." style="flex:1">
          <button class="btn btn-sm btn-danger" onclick="addWord()">Agregar</button>
        </div>
        <div class="chip-list" id="word-chips"></div>
        <div class="btn-row"><button class="btn" onclick="saveWordFilter()">💾 Guardar filtro</button></div>
      </div>
    </div>

    <!-- ════════════ LOGS ════════════ -->
    <div class="page" id="page-logs">
      <div class="page-header">
        <div class="page-title">Sistema de Logs</div>
        <div class="page-sub">Registra automáticamente eventos del servidor</div>
      </div>
      <div class="card">
        <div class="toggle-row">
          <div><div class="toggle-label">Activar logs</div></div>
          <label class="toggle"><input type="checkbox" id="logs-enabled"><span class="slider"></span></label>
        </div>
        <div class="form-group" style="margin-bottom:18px">
          <div class="form-label">Canal de logs</div>
          <select id="logs-channel"><option value="">— Elegir canal —</option></select>
        </div>
        <div class="card-title" style="margin-bottom:14px">Eventos a registrar</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <label style="display:flex;align-items:center;gap:10px;font-size:13px;cursor:pointer">
            <input type="checkbox" id="log-member_join"> Entradas de miembros
          </label>
          <label style="display:flex;align-items:center;gap:10px;font-size:13px;cursor:pointer">
            <input type="checkbox" id="log-member_leave"> Salidas de miembros
          </label>
          <label style="display:flex;align-items:center;gap:10px;font-size:13px;cursor:pointer">
            <input type="checkbox" id="log-message_delete"> Mensajes eliminados
          </label>
          <label style="display:flex;align-items:center;gap:10px;font-size:13px;cursor:pointer">
            <input type="checkbox" id="log-moderation"> Acciones de moderación
          </label>
          <label style="display:flex;align-items:center;gap:10px;font-size:13px;cursor:pointer">
            <input type="checkbox" id="log-role_update"> Cambios de roles
          </label>
        </div>
        <div class="btn-row"><button class="btn" onclick="saveLogs()">💾 Guardar</button></div>
      </div>
    </div>

    <!-- ════════════ ANUNCIAR ════════════ -->
    <div class="page" id="page-announce">
      <div class="page-header">
        <div class="page-title">Anuncios</div>
        <div class="page-sub">Envía mensajes o embeds a cualquier canal desde aquí</div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Enviar Mensaje</div>
        <div class="card-grid">
          <div class="form-group"><div class="form-label">Canal destino</div>
            <select id="announce-channel"><option value="">— Elegir canal —</option></select>
          </div>
          <div class="form-group"><div class="form-label">Tipo</div>
            <select id="announce-type">
              <option value="text">Texto simple</option>
              <option value="embed">Embed</option>
            </select>
          </div>
        </div>
        <div id="announce-embed-fields" style="display:none;margin-top:12px">
          <div class="card-grid">
            <div class="form-group"><div class="form-label">Título del embed</div><input type="text" id="announce-title" placeholder="Título"></div>
            <div class="form-group"><div class="form-label">Color (hex)</div><input type="text" id="announce-color" placeholder="3b82f6" maxlength="6"></div>
          </div>
        </div>
        <div class="card-grid full" style="margin-top:12px">
          <div class="form-group">
            <div class="form-label">Mensaje / Descripción</div>
            <textarea id="announce-content" rows="4" placeholder="Escribe tu mensaje aquí..."></textarea>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn" onclick="sendAnnounce()">📣 Enviar</button>
          <button class="btn btn-ghost" onclick="previewAnnounce()">👁️ Preview</button>
        </div>
        <div id="announce-preview" style="display:none;margin-top:16px"></div>
      </div>
    </div>

    <!-- ════════════ CUSTOM COMMANDS ════════════ -->
    <div class="page" id="page-custom_cmds">
      <div class="page-header">
        <div class="page-title">Comandos Custom</div>
        <div class="page-sub">Crea respuestas automáticas con <b>!comando</b></div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Agregar Comando</div>
        <div class="card-grid">
          <div class="form-group">
            <div class="form-label">Trigger (!trigger)</div>
            <input type="text" id="cmd-trigger" placeholder="ej: reglas">
          </div>
          <div class="form-group">
            <div class="form-label">Respuesta</div>
            <input type="text" id="cmd-response" placeholder="Aquí están las reglas: ...">
          </div>
        </div>
        <div class="btn-row"><button class="btn" onclick="addCmd()">➕ Agregar comando</button></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Comandos Actuales</div></div>
        <div id="cmd-list"></div>
        <div id="cmd-empty" style="color:var(--muted);font-size:13px;padding:8px 0">No hay comandos custom.</div>
      </div>
    </div>

    <!-- ════════════ LEADERBOARD ════════════ -->
    <div class="page" id="page-leaderboard">
      <div class="page-header">
        <div class="page-title">Leaderboard</div>
        <div class="page-sub">Top usuarios por XP en el servidor</div>
      </div>
      <div class="card">
        <div class="card-header">
          <div class="card-title">Top 20 — XP</div>
          <button class="btn btn-sm btn-ghost" onclick="loadLeaderboard()">🔄 Actualizar</button>
        </div>
        <div id="lb-content">
          <div style="color:var(--muted);font-size:13px;padding:8px 0">Activa el sistema de XP para ver el leaderboard.</div>
        </div>
      </div>
    </div>

  </div><!-- /content -->
</div><!-- /main -->
</div><!-- /layout -->

<!-- MODAL MEMBER ACTIONS -->
<div class="modal-overlay" id="member-modal">
  <div class="modal">
    <div class="modal-title" id="modal-member-name">Acciones</div>
    <input type="hidden" id="modal-member-id">
    <div class="card-grid full">
      <div class="form-group"><div class="form-label">Razón</div><input type="text" id="modal-reason" placeholder="Razón (opcional)"></div>
    </div>
    <div class="btn-row" style="margin-top:16px;flex-wrap:wrap">
      <button class="btn btn-sm" onclick="memberAction('warn')">⚠️ Warn</button>
      <button class="btn btn-sm btn-danger" onclick="memberAction('kick')">👢 Kick</button>
      <button class="btn btn-sm btn-danger" onclick="memberAction('ban')">🔨 Ban</button>
      <button class="btn btn-sm" style="background:var(--yellow);color:#000" onclick="memberAction('timeout')">🔇 Timeout 10min</button>
      <button class="btn btn-sm btn-ghost" onclick="closeModal('member-modal')">Cancelar</button>
    </div>
  </div>
</div>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<script>
const CFG = {{ cfg | tojson }};
let _channels = [];
let _roles = [];
let _members = [];

// ── NAVIGATION ────────────────────────────────────────────────
document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const page = btn.dataset.page;
    document.getElementById('page-' + page).classList.add('active');
    document.querySelector('.topbar-title').textContent = btn.textContent.trim();
    if (page === 'members') loadMembers();
    if (page === 'channels') loadChannels();
    if (page === 'roles') loadRoles();
    if (page === 'reaction_roles') loadRR();
    if (page === 'leaderboard') loadLeaderboard();
  });
});

// ── TOAST ────────────────────────────────────────────────────
function toast(msg, type='success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── POST ─────────────────────────────────────────────────────
async function post(url, data) {
  const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
  return r.json();
}

// ── MODAL ─────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('open') }
function closeModal(id) { document.getElementById(id).classList.remove('open') }
document.querySelectorAll('.modal-overlay').forEach(o => o.addEventListener('click', e => { if(e.target===o) o.classList.remove('open') }));

// ── INIT ─────────────────────────────────────────────────────
async function init() {
  try {
    const g = await (await fetch('/api/guild')).json();
    document.getElementById('guild-name-brand').textContent = g.name || '—';
    document.getElementById('guild-name-top').textContent = g.name || '—';
    document.getElementById('guild-members-top').textContent = (g.approximate_member_count || g.member_count || '—') + ' miembros';
    document.getElementById('guild-icon-ph').textContent = (g.name||'?')[0].toUpperCase();
    document.getElementById('stat-members').textContent = g.approximate_member_count || g.member_count || '—';
    document.getElementById('stat-channels').textContent = g.channels || '—';
    document.getElementById('stat-roles').textContent = g.roles || '—';
    document.getElementById('stat-emojis').textContent = g.emojis || '—';
  } catch(e) {}

  // Load channels & roles for selects
  try {
    _channels = await (await fetch('/api/channels')).json();
    _roles    = await (await fetch('/api/roles')).json();
    populateSelects();
  } catch(e) {}

  loadConfig();
  loadModulesStatus();
}

function populateSelects() {
  const chSelects = ['welcome-channel','goodbye-channel','xp-channel','stream-channel','logs-channel','announce-channel'];
  chSelects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const cur = el.value;
    el.innerHTML = '<option value="">— Elegir canal —</option>';
    _channels.filter(c => c.type === 0 || c.type === 5).forEach(c => {
      el.innerHTML += `<option value="${c.id}"># ${c.name}</option>`;
    });
    if (cur) el.value = cur;
  });

  const roleSelects = ['welcome-role','rr-role'];
  roleSelects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = id === 'welcome-role' ? '<option value="">— Sin rol automático —</option>' : '<option value="">— Elegir rol —</option>';
    _roles.forEach(r => { el.innerHTML += `<option value="${r.id}">${r.name}</option>` });
  });

  // Category select
  const catEl = document.getElementById('new-ch-category');
  if (catEl) {
    catEl.innerHTML = '<option value="">Sin categoría</option>';
    _channels.filter(c => c.type === 4).forEach(c => {
      catEl.innerHTML += `<option value="${c.id}">${c.name}</option>`;
    });
  }
}

function loadConfig() {
  const w = CFG.welcome || {};
  setV('welcome-enabled', w.enabled, 'check');
  setV('welcome-channel', w.channel_id||'');
  setV('welcome-role', w.auto_role_id||'');
  setV('welcome-message', w.message||'');
  setV('welcome-banner', w.banner_url||'');

  const g = CFG.goodbye || {};
  setV('goodbye-enabled', g.enabled, 'check');
  setV('goodbye-channel', g.channel_id||'');
  setV('goodbye-message', g.message||'');

  const x = CFG.xp || {};
  setV('xp-enabled', x.enabled, 'check');
  setV('xp-channel', x.levelup_channel_id||'');

  const s = CFG.stream_alert || {};
  setV('stream-enabled', s.enabled, 'check');
  setV('stream-channel', s.channel_id||'');
  setV('stream-kick', s.kick_username||'');
  setV('stream-tiktok', s.tiktok_username||'');
  setV('stream-message', s.message||'');

  const m = CFG.moderation || {};
  setV('mod-antilinks', m.anti_links, 'check');
  setV('mod-antispam', m.anti_spam, 'check');

  const wf = CFG.word_filter || {};
  setV('wf-enabled', wf.enabled, 'check');
  renderWordChips(wf.words || []);

  const l = CFG.logs || {};
  setV('logs-enabled', l.enabled, 'check');
  setV('logs-channel', l.channel_id||'');
  const events = l.events || [];
  ['member_join','member_leave','message_delete','moderation','role_update'].forEach(e => {
    const el = document.getElementById('log-'+e);
    if (el) el.checked = events.includes(e);
  });

  loadCmds();
}

function setV(id, val, type='val') {
  const el = document.getElementById(id);
  if (!el) return;
  if (type === 'check') el.checked = !!val;
  else el.value = val || '';
}

function loadModulesStatus() {
  const modules = [
    { name:'Bienvenida', key:'welcome', icon:'👋' },
    { name:'Despedida', key:'goodbye', icon:'👋' },
    { name:'Sistema XP', key:'xp', icon:'⭐' },
    { name:'Stream Alerts', key:'stream_alert', icon:'🔴' },
    { name:'Anti-Links', key:'moderation.anti_links', icon:'🔗' },
    { name:'Filtro Palabras', key:'word_filter', icon:'🚫' },
    { name:'Logs', key:'logs', icon:'📋' },
  ];
  const el = document.getElementById('modules-status');
  el.innerHTML = '';
  modules.forEach(m => {
    const keys = m.key.split('.');
    let val = CFG;
    keys.forEach(k => val = val?.[k]);
    const on = !!val;
    el.innerHTML += `<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:13px">${m.icon} ${m.name}</span>
      <span class="tag ${on?'tag-green':'tag-red'}">${on?'ON':'OFF'}</span>
    </div>`;
  });
}

// ── GUILD ─────────────────────────────────────────────────────
// ── MEMBERS ──────────────────────────────────────────────────
async function loadMembers() {
  const el = document.getElementById('members-list');
  el.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:12px 0">Cargando...</div>';
  try {
    const members = await (await fetch('/api/members')).json();
    _members = members;
    renderMembers(members);
  } catch(e) {
    el.innerHTML = '<div style="color:var(--red);font-size:13px">Error al cargar miembros</div>';
  }
}

function renderMembers(list) {
  const el = document.getElementById('members-list');
  if (!list.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">Sin miembros</div>'; return; }
  el.innerHTML = list.slice(0,100).map(m => `
    <div class="member-item">
      <div class="member-avatar-placeholder">${(m.display_name||m.username||'?')[0].toUpperCase()}</div>
      <div>
        <div class="member-name">${escHtml(m.display_name||m.username)}</div>
        <div class="member-tag">${escHtml(m.username)} · ${m.top_role||'@everyone'}</div>
      </div>
      <div class="member-actions">
        <button class="btn btn-sm btn-ghost" onclick="openMemberModal('${m.id}','${escHtml(m.display_name||m.username)}')">⚡ Acciones</button>
      </div>
    </div>`).join('');
}

function filterMembers(q) {
  if (!q) { renderMembers(_members); return; }
  renderMembers(_members.filter(m =>
    (m.display_name||'').toLowerCase().includes(q.toLowerCase()) ||
    (m.username||'').toLowerCase().includes(q.toLowerCase())
  ));
}

function openMemberModal(id, name) {
  document.getElementById('modal-member-id').value = id;
  document.getElementById('modal-member-name').textContent = '⚡ ' + name;
  document.getElementById('modal-reason').value = '';
  openModal('member-modal');
}

async function memberAction(action) {
  const id = document.getElementById('modal-member-id').value;
  const reason = document.getElementById('modal-reason').value || 'Sin razón';
  const r = await post('/api/member/action', { action, user_id: id, reason });
  closeModal('member-modal');
  toast(r.ok ? `✅ ${action} ejecutado` : '❌ Error: ' + (r.error||''), r.ok?'success':'error');
}

// ── CHANNELS ─────────────────────────────────────────────────
async function loadChannels() {
  const el = document.getElementById('channels-list');
  el.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:8px 0">Cargando...</div>';
  const channels = await (await fetch('/api/channels')).json();
  _channels = channels;
  populateSelects();
  const typeIcon = {0:'💬',2:'🔊',4:'📁',5:'📢',13:'🎙️'};
  // Group by category
  const cats = {};
  channels.filter(c=>c.type===4).forEach(c => cats[c.id] = {cat:c, children:[]});
  const noCat = [];
  channels.filter(c=>c.type!==4).forEach(c => {
    if (c.parent_id && cats[c.parent_id]) cats[c.parent_id].children.push(c);
    else noCat.push(c);
  });

  let html = '';
  // No category channels
  noCat.forEach(c => {
    html += channelItemHtml(c, typeIcon);
  });
  // Categorized
  Object.values(cats).forEach(({cat, children}) => {
    html += `<div style="padding:8px 0 4px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted)">📁 ${escHtml(cat.name)}</div>`;
    children.forEach(c => html += channelItemHtml(c, typeIcon, true));
  });
  el.innerHTML = html || '<div style="color:var(--muted);font-size:13px">Sin canales</div>';
}

function channelItemHtml(c, typeIcon, indent=false) {
  return `<div class="channel-item" style="${indent?'padding-left:24px':''}">
    <span>${typeIcon[c.type]||'📢'}</span>
    <span>${escHtml(c.name)}</span>
    <span style="margin-left:6px;font-size:11px;color:var(--muted);font-family:var(--mono)">${c.id}</span>
    <div class="channel-actions">
      <button class="btn btn-sm btn-danger" onclick="deleteChannel('${c.id}','${escHtml(c.name)}')">🗑️</button>
    </div>
  </div>`;
}

async function createChannel() {
  const name = document.getElementById('new-ch-name').value.trim();
  if (!name) { toast('Ingresa un nombre','error'); return; }
  const r = await post('/api/channels/create', {
    name,
    type: parseInt(document.getElementById('new-ch-type').value),
    parent_id: document.getElementById('new-ch-category').value||null,
    topic: document.getElementById('new-ch-topic').value||null,
  });
  if (r.ok) { toast('✅ Canal creado'); loadChannels(); document.getElementById('new-ch-name').value=''; }
  else toast('❌ ' + (r.error||'Error'),'error');
}

async function deleteChannel(id, name) {
  if (!confirm(`¿Eliminar #${name}? Esto es permanente.`)) return;
  const r = await post('/api/channels/delete', { channel_id: id });
  if (r.ok) { toast('🗑️ Canal eliminado'); loadChannels(); }
  else toast('❌ ' + (r.error||'Error'),'error');
}

// ── ROLES ─────────────────────────────────────────────────────
async function loadRoles() {
  const el = document.getElementById('roles-list');
  const roles = await (await fetch('/api/roles')).json();
  _roles = roles;
  populateSelects();
  el.innerHTML = `<div class="table-wrap"><table>
    <tr><th>Nombre</th><th>Color</th><th>Posición</th><th>Miembros</th><th>Acción</th></tr>
    ${roles.map(r => `<tr>
      <td><span style="display:inline-flex;align-items:center;gap:8px">
        <span style="width:12px;height:12px;border-radius:50%;background:#${r.color?.toString(16).padStart(6,'0')||'aaaaaa'};display:inline-block"></span>
        ${escHtml(r.name)}
      </span></td>
      <td><span style="font-family:var(--mono);font-size:12px">#${r.color?.toString(16).padStart(6,'0')||'aaaaaa'}</span></td>
      <td>${r.position}</td>
      <td>${r.member_count||'—'}</td>
      <td><button class="btn btn-sm btn-danger" onclick="deleteRole('${r.id}','${escHtml(r.name)}')">🗑️</button></td>
    </tr>`).join('')}
  </table></div>`;
}

async function createRole() {
  const name = document.getElementById('new-role-name').value.trim();
  if (!name) { toast('Ingresa un nombre','error'); return; }
  const color = document.getElementById('new-role-color').value.trim();
  const r = await post('/api/roles/create', {
    name,
    color: color ? parseInt(color, 16) : 0,
    hoist: document.getElementById('new-role-hoist').checked,
    mentionable: document.getElementById('new-role-mentionable').checked,
  });
  if (r.ok) { toast('✅ Rol creado'); loadRoles(); document.getElementById('new-role-name').value=''; }
  else toast('❌ ' + (r.error||'Error'),'error');
}

async function deleteRole(id, name) {
  if (!confirm(`¿Eliminar el rol "${name}"?`)) return;
  const r = await post('/api/roles/delete', { role_id: id });
  if (r.ok) { toast('🗑️ Rol eliminado'); loadRoles(); }
  else toast('❌ ' + (r.error||'Error'),'error');
}

// ── CONFIG SAVES ──────────────────────────────────────────────
async function saveWelcome() {
  await post('/api/welcome', {
    enabled: document.getElementById('welcome-enabled').checked,
    channel_id: document.getElementById('welcome-channel').value||null,
    auto_role_id: document.getElementById('welcome-role').value||null,
    message: document.getElementById('welcome-message').value,
    banner_url: document.getElementById('welcome-banner').value,
  });
  toast('✅ Bienvenida guardada');
}

async function saveGoodbye() {
  await post('/api/goodbye', {
    enabled: document.getElementById('goodbye-enabled').checked,
    channel_id: document.getElementById('goodbye-channel').value||null,
    message: document.getElementById('goodbye-message').value,
  });
  toast('✅ Despedida guardada');
}

async function saveXP() {
  await post('/api/xp', {
    enabled: document.getElementById('xp-enabled').checked,
    levelup_channel_id: document.getElementById('xp-channel').value||null,
  });
  toast('✅ XP guardado');
}

async function resetXP() {
  await post('/api/xp/reset', {});
  toast('🗑️ XP reseteado');
}

async function saveStream() {
  await post('/api/stream_alert', {
    enabled: document.getElementById('stream-enabled').checked,
    channel_id: document.getElementById('stream-channel').value||null,
    kick_username: document.getElementById('stream-kick').value,
    tiktok_username: document.getElementById('stream-tiktok').value,
    message: document.getElementById('stream-message').value,
  });
  toast('✅ Stream guardado');
}

async function saveMod() {
  await post('/api/moderation', {
    anti_links: document.getElementById('mod-antilinks').checked,
    anti_spam: document.getElementById('mod-antispam').checked,
  });
  toast('✅ Moderación guardada');
}

// ── WORD FILTER ───────────────────────────────────────────────
let _words = [...(CFG.word_filter?.words||[])];
function renderWordChips(words) {
  _words = [...words];
  const el = document.getElementById('word-chips');
  el.innerHTML = _words.map((w,i) => `<span class="chip">${escHtml(w)}<span class="chip-del" onclick="removeWord(${i})">×</span></span>`).join('');
}
function addWord() {
  const v = document.getElementById('wf-input').value.trim();
  if (!v || _words.includes(v)) return;
  _words.push(v);
  renderWordChips(_words);
  document.getElementById('wf-input').value = '';
}
function removeWord(i) { _words.splice(i,1); renderWordChips(_words); }
async function saveWordFilter() {
  await post('/api/word_filter', { enabled: document.getElementById('wf-enabled').checked, words: _words });
  toast('✅ Filtro guardado');
}

// ── LOGS ─────────────────────────────────────────────────────
async function saveLogs() {
  const events = ['member_join','member_leave','message_delete','moderation','role_update']
    .filter(e => document.getElementById('log-'+e)?.checked);
  await post('/api/logs', {
    enabled: document.getElementById('logs-enabled').checked,
    channel_id: document.getElementById('logs-channel').value||null,
    events,
  });
  toast('✅ Logs guardados');
}

// ── ANNOUNCE ─────────────────────────────────────────────────
document.getElementById('announce-type').addEventListener('change', function() {
  document.getElementById('announce-embed-fields').style.display = this.value==='embed'?'block':'none';
});
async function sendAnnounce() {
  const ch = document.getElementById('announce-channel').value;
  if (!ch) { toast('Elige un canal','error'); return; }
  const type = document.getElementById('announce-type').value;
  const content = document.getElementById('announce-content').value.trim();
  if (!content) { toast('Escribe un mensaje','error'); return; }
  const r = await post('/api/announce', {
    channel_id: ch, type, content,
    title: document.getElementById('announce-title').value,
    color: document.getElementById('announce-color').value||'3b82f6',
  });
  if (r.ok) toast('✅ Anuncio enviado');
  else toast('❌ ' + (r.error||'Error'),'error');
}
function previewAnnounce() {
  const type = document.getElementById('announce-type').value;
  const content = document.getElementById('announce-content').value;
  const title = document.getElementById('announce-title').value;
  const color = '#' + (document.getElementById('announce-color').value||'3b82f6');
  const el = document.getElementById('announce-preview');
  el.style.display = 'block';
  if (type === 'embed') {
    el.innerHTML = `<div style="border-left:4px solid ${color};background:rgba(255,255,255,.04);padding:14px 16px;border-radius:0 10px 10px 0">
      ${title?`<div style="font-weight:700;margin-bottom:6px">${escHtml(title)}</div>`:''}
      <div style="font-size:13px;color:var(--muted2)">${escHtml(content)}</div>
    </div>`;
  } else {
    el.innerHTML = `<div style="background:rgba(255,255,255,.04);padding:14px 16px;border-radius:10px;font-size:13px">${escHtml(content)}</div>`;
  }
}

// ── REACTION ROLES ────────────────────────────────────────────
async function loadRR() {
  const rrs = await (await fetch('/api/reaction_roles')).json();
  const table = document.getElementById('rr-table');
  const empty = document.getElementById('rr-empty');
  Array.from(table.querySelectorAll('tr')).slice(1).forEach(r=>r.remove());
  empty.style.display = rrs.length ? 'none' : 'block';
  rrs.forEach((rr,i) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span style="font-family:var(--mono);font-size:12px">${rr.message_id}</span></td>
      <td>${rr.emoji}</td>
      <td><span style="font-family:var(--mono);font-size:12px">${rr.role_id}</span></td>
      <td><button class="btn btn-sm btn-danger" onclick="deleteRR(${i})">🗑️ Eliminar</button></td>`;
    table.appendChild(tr);
  });
}
async function addRR() {
  const msg_id=document.getElementById('rr-msg-id').value.trim();
  const emoji=document.getElementById('rr-emoji').value.trim();
  const role=document.getElementById('rr-role').value;
  if(!msg_id||!emoji||!role){toast('Completa todos los campos','error');return}
  await post('/api/reaction_roles',{message_id:msg_id,emoji,role_id:role});
  document.getElementById('rr-msg-id').value='';
  document.getElementById('rr-emoji').value='';
  loadRR();toast('✅ Reaction role agregado');
}
async function deleteRR(i) {
  await fetch(`/api/reaction_roles/${i}`,{method:'DELETE'});
  loadRR();toast('🗑️ Eliminado');
}

// ── CUSTOM COMMANDS ───────────────────────────────────────────
function loadCmds() {
  const cmds = CFG.custom_commands || {};
  const el = document.getElementById('cmd-list');
  const empty = document.getElementById('cmd-empty');
  const entries = Object.entries(cmds);
  empty.style.display = entries.length ? 'none' : 'block';
  el.innerHTML = entries.map(([t,r]) => `<div class="cmd-item">
    <span class="cmd-trigger">!${escHtml(t)}</span>
    <span class="cmd-response">${escHtml(r)}</span>
    <button class="btn btn-sm btn-danger" onclick="deleteCmd('${escHtml(t)}')">🗑️</button>
  </div>`).join('');
}
async function addCmd() {
  const t = document.getElementById('cmd-trigger').value.trim().replace(/^!/,'');
  const r = document.getElementById('cmd-response').value.trim();
  if(!t||!r){toast('Completa los campos','error');return}
  const res = await post('/api/custom_commands', {trigger:t,response:r});
  if(res.ok){
    CFG.custom_commands = res.commands;
    loadCmds();
    document.getElementById('cmd-trigger').value='';
    document.getElementById('cmd-response').value='';
    toast('✅ Comando agregado');
  }
}
async function deleteCmd(t) {
  const res = await fetch('/api/custom_commands/'+t,{method:'DELETE'});
  const data = await res.json();
  if(data.ok){CFG.custom_commands=data.commands;loadCmds();toast('🗑️ Eliminado')}
}

// ── LEADERBOARD ───────────────────────────────────────────────
async function loadLeaderboard() {
  const el = document.getElementById('lb-content');
  el.innerHTML = '<div style="color:var(--muted);font-size:13px">Cargando...</div>';
  const data = await (await fetch('/api/leaderboard')).json();
  if (!data.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">Sin datos de XP aún.</div>'; return; }
  const medals = ['🥇','🥈','🥉'];
  el.innerHTML = data.map((u,i) => `
    <div style="display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:18px;width:30px;text-align:center">${medals[i]||`#${i+1}`}</span>
      <div style="flex:1">
        <div style="font-size:13px;font-weight:700">${escHtml(u.name)}</div>
        <div style="font-size:11px;color:var(--muted)">Nivel ${u.level}</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:14px;font-weight:800;font-family:var(--mono);color:var(--yellow)">${u.xp} XP</div>
      </div>
    </div>`).join('');
}

// ── UTILS ─────────────────────────────────────────────────────
function escHtml(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') }

// ── START ─────────────────────────────────────────────────────
init();
</script>
</body>
{% endif %}
</html>'''

# ══════════════════════════════════════════════════════════════
#  FLASK APP
# ══════════════════════════════════════════════════════════════
app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET", "thefamily2024secret")

BOT_TOKEN      = (os.environ.get("BOT_TOKEN") or "").strip()
GUILD_ID       = (os.environ.get("GUILD_ID") or "0").strip()
PANEL_PASSWORD = (os.environ.get("PANEL_PASSWORD") or "cesar2024").strip()

DISCORD = "https://discord.com/api/v10"
HEADERS = lambda: {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}

def load_config():
    try:
        with open("config.json") as f: return json.load(f)
    except Exception: return {}

def save_config(data):
    with open("config.json", "w") as f: json.dump(data, f, indent=2)

def discord_get(path):
    try:
        r = req_lib.get(f"{DISCORD}{path}", headers=HEADERS(), timeout=6)
        if r.status_code != 200:
            print(f"[DISCORD API ERROR] GET {path} returned {r.status_code}: {r.text}", flush=True)
        return r.json() if r.status_code == 200 else {}
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] GET {path}: {e}", flush=True)
        return {}

def discord_post(path, data):
    try:
        r = req_lib.post(f"{DISCORD}{path}", headers=HEADERS(), json=data, timeout=6)
        if r.status_code not in (200, 201, 204):
            print(f"[DISCORD API ERROR] POST {path} returned {r.status_code}: {r.text}", flush=True)
        return r.json() if hasattr(r, 'json') and r.text else {}
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] POST {path}: {e}", flush=True)
        return {}

def discord_delete(path):
    try:
        r = req_lib.delete(f"{DISCORD}{path}", headers=HEADERS(), timeout=6)
        if r.status_code not in (200, 204):
            print(f"[DISCORD API ERROR] DELETE {path} returned {r.status_code}: {r.text}", flush=True)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] DELETE {path}: {e}", flush=True)
        return False

def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# ── AUTH ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PANEL_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return render_template_string(PANEL_HTML, logged_in=False, error="Contraseña incorrecta")
    return render_template_string(PANEL_HTML, logged_in=False, error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ── PANEL ─────────────────────────────────────────────────────
@app.route("/")
@auth_required
def index():
    return render_template_string(PANEL_HTML, logged_in=True, cfg=load_config())

# ── GUILD INFO ────────────────────────────────────────────────
@app.route("/api/guild")
@auth_required
def api_guild():
    g = discord_get(f"/guilds/{GUILD_ID}?with_counts=true")
    channels = discord_get(f"/guilds/{GUILD_ID}/channels")
    roles    = discord_get(f"/guilds/{GUILD_ID}/roles")
    emojis   = discord_get(f"/guilds/{GUILD_ID}/emojis")
    return {
        "name": g.get("name",""),
        "icon": g.get("icon",""),
        "member_count": g.get("member_count", g.get("approximate_member_count",0)),
        "approximate_member_count": g.get("approximate_member_count",0),
        "channels": len(channels) if isinstance(channels, list) else 0,
        "roles": len(roles) if isinstance(roles, list) else 0,
        "emojis": len(emojis) if isinstance(emojis, list) else 0,
    }

# ── MEMBERS ───────────────────────────────────────────────────
@app.route("/api/members")
@auth_required
def api_members():
    members = discord_get(f"/guilds/{GUILD_ID}/members?limit=100")
    if not isinstance(members, list): return []
    result = []
    for m in members:
        user = m.get("user", {})
        roles = m.get("roles", [])
        result.append({
            "id": user.get("id"),
            "username": user.get("username",""),
            "display_name": m.get("nick") or user.get("global_name") or user.get("username",""),
            "avatar": user.get("avatar"),
            "top_role": roles[-1] if roles else None,
            "bot": user.get("bot", False),
        })
    return result

# ── CHANNELS ─────────────────────────────────────────────────
@app.route("/api/channels")
@auth_required
def api_channels():
    channels = discord_get(f"/guilds/{GUILD_ID}/channels")
    if not isinstance(channels, list): return []
    return sorted([{"id":c["id"],"name":c["name"],"type":c["type"],"parent_id":c.get("parent_id")} for c in channels],
                  key=lambda c: c["name"])

@app.route("/api/channels/create", methods=["POST"])
@auth_required
def api_channel_create():
    data = request.json
    payload = {"name": data["name"].lower().replace(" ","-"), "type": data.get("type",0)}
    if data.get("parent_id"): payload["parent_id"] = data["parent_id"]
    if data.get("topic"):     payload["topic"] = data["topic"]
    r = discord_post(f"/guilds/{GUILD_ID}/channels", payload)
    if "id" in r: return {"ok": True, "id": r["id"]}
    return {"ok": False, "error": r.get("message","Error de Discord")}

@app.route("/api/channels/delete", methods=["POST"])
@auth_required
def api_channel_delete():
    ch_id = request.json.get("channel_id")
    ok = discord_delete(f"/channels/{ch_id}")
    return {"ok": ok}

# ── ROLES ─────────────────────────────────────────────────────
@app.route("/api/roles")
@auth_required
def api_roles():
    roles = discord_get(f"/guilds/{GUILD_ID}/roles")
    if not isinstance(roles, list): return []
    return [{"id":r["id"],"name":r["name"],"color":r["color"],"position":r["position"]} for r in roles if r["name"]!="@everyone"]

@app.route("/api/roles/create", methods=["POST"])
@auth_required
def api_role_create():
    data = request.json
    payload = {"name": data["name"], "color": data.get("color",0),
               "hoist": data.get("hoist",False), "mentionable": data.get("mentionable",False)}
    r = discord_post(f"/guilds/{GUILD_ID}/roles", payload)
    if "id" in r: return {"ok": True}
    return {"ok": False, "error": r.get("message","Error")}

@app.route("/api/roles/delete", methods=["POST"])
@auth_required
def api_role_delete():
    role_id = request.json.get("role_id")
    ok = discord_delete(f"/guilds/{GUILD_ID}/roles/{role_id}")
    return {"ok": ok}

# ── MEMBER ACTIONS ────────────────────────────────────────────
@app.route("/api/member/action", methods=["POST"])
@auth_required
def api_member_action():
    data   = request.json
    action = data.get("action")
    uid    = data.get("user_id")
    reason = data.get("reason","Sin razón")
    try:
        if action == "kick":
            r = req_lib.delete(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}",
                               headers={**HEADERS(), "X-Audit-Log-Reason": reason})
            return {"ok": r.status_code in (200,204)}
        elif action == "ban":
            r = req_lib.put(f"{DISCORD}/guilds/{GUILD_ID}/bans/{uid}",
                            headers={**HEADERS(), "X-Audit-Log-Reason": reason}, json={})
            return {"ok": r.status_code in (200,204)}
        elif action == "warn":
            cfg = load_config()
            warns = cfg.get("warns", {})
            warns[uid] = warns.get(uid, [])
            warns[uid].append({"razon": reason, "fecha": str(__import__("datetime").datetime.now()), "by": "Panel"})
            cfg["warns"] = warns
            save_config(cfg)
            return {"ok": True}
        elif action == "timeout":
            from datetime import datetime, timedelta, timezone
            until = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            r = req_lib.patch(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}",
                              headers={**HEADERS(), "X-Audit-Log-Reason": reason},
                              json={"communication_disabled_until": until})
            return {"ok": r.status_code in (200,204)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "Acción desconocida"}

# ── ANNOUNCE ─────────────────────────────────────────────────
@app.route("/api/announce", methods=["POST"])
@auth_required
def api_announce():
    data    = request.json
    ch_id   = data.get("channel_id")
    type_   = data.get("type","text")
    content = data.get("content","")
    try:
        if type_ == "embed":
            color_hex = data.get("color","3b82f6")
            color_int = int(color_hex.strip("#"), 16)
            payload = {"embeds": [{"title": data.get("title",""), "description": content, "color": color_int}]}
        else:
            payload = {"content": content}
        r = discord_post(f"/channels/{ch_id}/messages", payload)
        if "id" in r: return {"ok": True}
        return {"ok": False, "error": r.get("message","Error")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── LEADERBOARD ───────────────────────────────────────────────
@app.route("/api/leaderboard")
@auth_required
def api_leaderboard():
    cfg = load_config()
    xp_data = cfg.get("xp_data", {})
    members = discord_get(f"/guilds/{GUILD_ID}/members?limit=100")
    member_names = {}
    if isinstance(members, list):
        for m in members:
            u = m.get("user",{})
            member_names[u.get("id","")] = m.get("nick") or u.get("global_name") or u.get("username","?")
    sorted_users = sorted(xp_data.items(), key=lambda x: x[1].get("xp",0), reverse=True)[:20]
    return [{"id":uid,"name":member_names.get(uid,f"#{uid[:6]}"),"xp":d.get("xp",0),"level":d.get("level",0)}
            for uid, d in sorted_users]

# ── CUSTOM COMMANDS ───────────────────────────────────────────
@app.route("/api/custom_commands", methods=["POST"])
@auth_required
def api_cmd_add():
    data = request.json
    cfg  = load_config()
    cmds = cfg.get("custom_commands", {})
    cmds[data["trigger"].lower()] = data["response"]
    cfg["custom_commands"] = cmds
    save_config(cfg)
    return {"ok": True, "commands": cmds}

@app.route("/api/custom_commands/<trigger>", methods=["DELETE"])
@auth_required
def api_cmd_delete(trigger):
    cfg  = load_config()
    cmds = cfg.get("custom_commands", {})
    cmds.pop(trigger, None)
    cfg["custom_commands"] = cmds
    save_config(cfg)
    return {"ok": True, "commands": cmds}

# ── CONFIG ENDPOINTS ──────────────────────────────────────────
def cfg_patch(key, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    return {"ok": True}

@app.route("/api/welcome", methods=["POST"])
@auth_required
def api_welcome(): return cfg_patch("welcome", request.json)

@app.route("/api/goodbye", methods=["POST"])
@auth_required
def api_goodbye(): return cfg_patch("goodbye", request.json)

@app.route("/api/xp", methods=["POST"])
@auth_required
def api_xp(): return cfg_patch("xp", request.json)

@app.route("/api/xp/reset", methods=["POST"])
@auth_required
def api_xp_reset():
    cfg = load_config()
    cfg["xp_data"] = {}
    save_config(cfg)
    return {"ok": True}

@app.route("/api/moderation", methods=["POST"])
@auth_required
def api_moderation(): return cfg_patch("moderation", request.json)

@app.route("/api/word_filter", methods=["POST"])
@auth_required
def api_word_filter(): return cfg_patch("word_filter", request.json)

@app.route("/api/stream_alert", methods=["POST"])
@auth_required
def api_stream(): return cfg_patch("stream_alert", request.json)

@app.route("/api/logs", methods=["POST"])
@auth_required
def api_logs(): return cfg_patch("logs", request.json)

@app.route("/api/reaction_roles", methods=["GET"])
@auth_required
def api_rr_get(): return load_config().get("reaction_roles", [])

@app.route("/api/reaction_roles", methods=["POST"])
@auth_required
def api_rr_add():
    cfg = load_config()
    rr  = cfg.get("reaction_roles", [])
    rr.append(request.json)
    cfg["reaction_roles"] = rr
    save_config(cfg)
    return {"ok": True}

@app.route("/api/reaction_roles/<int:index>", methods=["DELETE"])
@auth_required
def api_rr_delete(index):
    cfg = load_config()
    rr  = cfg.get("reaction_roles", [])
    if 0 <= index < len(rr): rr.pop(index)
    cfg["reaction_roles"] = rr
    save_config(cfg)
    return {"ok": True}

@app.route("/api/config", methods=["GET"])
@auth_required
def api_config(): return load_config()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
