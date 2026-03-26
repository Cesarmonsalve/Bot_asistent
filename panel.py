from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import json, os, requests as req_lib

# ── TEMPLATES EMBEBIDOS (sin carpeta templates/) ─────────────
LOGIN_HTML = '<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>The Family — Panel</title>\n<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Mono&display=swap" rel="stylesheet">\n<style>\n* { box-sizing: border-box; margin: 0; padding: 0; }\nbody {\n  background: #09090f;\n  color: #e8e8f0;\n  font-family: \'Syne\', sans-serif;\n  min-height: 100vh;\n  display: flex;\n  align-items: center;\n  justify-content: center;\n}\n.card {\n  background: #0d0d1a;\n  border: 1px solid rgba(255,255,255,0.07);\n  border-radius: 20px;\n  padding: 48px 40px;\n  width: 100%;\n  max-width: 380px;\n  text-align: center;\n}\n.logo { font-size: 32px; font-weight: 800; margin-bottom: 4px;\n  background: linear-gradient(90deg, #7c5ff0, #60a5fa);\n  -webkit-background-clip: text; -webkit-text-fill-color: transparent;\n}\n.sub { color: #6b6b90; font-size: 13px; margin-bottom: 36px; }\ninput {\n  width: 100%;\n  background: rgba(255,255,255,0.05);\n  border: 1px solid rgba(255,255,255,0.1);\n  border-radius: 10px;\n  color: #e8e8f0;\n  font-family: \'DM Mono\', monospace;\n  font-size: 14px;\n  padding: 14px 16px;\n  margin-bottom: 14px;\n  outline: none;\n  transition: border .2s;\n}\ninput:focus { border-color: #5b3de8; }\nbutton {\n  width: 100%;\n  background: linear-gradient(135deg, #5b3de8, #2563eb);\n  border: none;\n  border-radius: 10px;\n  color: #fff;\n  font-family: \'Syne\', sans-serif;\n  font-size: 15px;\n  font-weight: 700;\n  padding: 14px;\n  cursor: pointer;\n  transition: opacity .2s;\n}\nbutton:hover { opacity: .85; }\n.error { color: #ef4444; font-size: 12px; margin-bottom: 12px; }\n</style>\n</head>\n<body>\n<div class="card">\n  <div class="logo">The Family</div>\n  <div class="sub">Panel de administración</div>\n  {% if error %}<div class="error">{{ error }}</div>{% endif %}\n  <form method="POST">\n    <input type="password" name="password" placeholder="Contraseña del panel" autofocus>\n    <button type="submit">Entrar</button>\n  </form>\n</div>\n</body>\n</html>\n'

INDEX_HTML = '<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>The Family — Panel</title>\n<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">\n<style>\n:root {\n  --black: #09090f; --deep: #0d0d1a; --card: #111120;\n  --purple: #5b3de8; --purple-l: #7c5ff0;\n  --blue: #2563eb; --blue-l: #60a5fa;\n  --text: #e8e8f0; --muted: #6b6b90;\n  --border: rgba(255,255,255,0.07);\n  --green: #22c55e; --yellow: #f59e0b; --red: #ef4444;\n}\n* { box-sizing: border-box; margin: 0; padding: 0; }\nbody { background: var(--black); color: var(--text); font-family: \'Syne\', sans-serif; display: flex; min-height: 100vh; }\n\n/* SIDEBAR */\n.sidebar {\n  width: 220px; background: var(--deep); border-right: 1px solid var(--border);\n  padding: 28px 16px; display: flex; flex-direction: column; gap: 4px; flex-shrink: 0;\n  position: fixed; height: 100vh; overflow-y: auto;\n}\n.logo { font-size: 20px; font-weight: 800; margin-bottom: 24px; padding: 0 8px;\n  background: linear-gradient(90deg, var(--purple-l), var(--blue-l));\n  -webkit-background-clip: text; -webkit-text-fill-color: transparent;\n}\n.nav-item {\n  display: flex; align-items: center; gap: 10px;\n  padding: 10px 12px; border-radius: 10px;\n  font-size: 13px; font-weight: 600; color: var(--muted);\n  cursor: pointer; transition: all .15s; border: none; background: none; width: 100%; text-align: left;\n}\n.nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text); }\n.nav-item.active { background: rgba(91,61,232,0.15); color: var(--purple-l); }\n.nav-sep { height: 1px; background: var(--border); margin: 10px 0; }\n.nav-logout { color: var(--red) !important; margin-top: auto; }\n\n/* MAIN */\n.main { margin-left: 220px; flex: 1; padding: 36px 40px; max-width: calc(100% - 220px); }\n.page { display: none; }\n.page.active { display: block; }\n\nh2 { font-size: 22px; font-weight: 800; margin-bottom: 6px; }\n.page-sub { color: var(--muted); font-size: 13px; margin-bottom: 28px; }\n\n/* CARDS */\n.card {\n  background: var(--deep); border: 1px solid var(--border);\n  border-radius: 16px; padding: 24px 28px; margin-bottom: 20px;\n}\n.card-title { font-size: 13px; font-weight: 700; text-transform: uppercase;\n  letter-spacing: 1px; color: var(--muted); margin-bottom: 20px; }\n\n/* STATS */\n.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }\n.stat { background: var(--deep); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; }\n.stat-label { font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }\n.stat-val { font-size: 26px; font-weight: 800; }\n.stat-val.green { color: var(--green); }\n.stat-val.purple { color: var(--purple-l); }\n.stat-val.blue { color: var(--blue-l); }\n.stat-val.yellow { color: var(--yellow); }\n\n/* FORM */\n.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }\n.form-row.full { grid-template-columns: 1fr; }\n.form-group { display: flex; flex-direction: column; gap: 6px; }\nlabel { font-size: 12px; font-weight: 600; color: var(--muted); }\ninput[type=text], input[type=url], select, textarea {\n  background: rgba(255,255,255,0.05); border: 1px solid var(--border);\n  border-radius: 10px; color: var(--text);\n  font-family: \'DM Mono\', monospace; font-size: 13px;\n  padding: 10px 14px; outline: none; transition: border .2s; width: 100%;\n}\ninput:focus, select:focus, textarea:focus { border-color: var(--purple); }\nselect option { background: var(--deep); }\ntextarea { resize: vertical; min-height: 80px; }\n\n/* TOGGLE */\n.toggle-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }\n.toggle-label { font-size: 14px; font-weight: 600; }\n.toggle { position: relative; width: 48px; height: 26px; }\n.toggle input { opacity: 0; width: 0; height: 0; }\n.slider {\n  position: absolute; inset: 0; background: rgba(255,255,255,0.1);\n  border-radius: 26px; cursor: pointer; transition: .3s;\n}\n.slider:before {\n  content: \'\'; position: absolute; height: 18px; width: 18px;\n  left: 4px; bottom: 4px; background: white; border-radius: 50%; transition: .3s;\n}\ninput:checked + .slider { background: var(--purple); }\ninput:checked + .slider:before { transform: translateX(22px); }\n\n/* BUTTON */\n.btn {\n  background: linear-gradient(135deg, var(--purple), var(--blue));\n  border: none; border-radius: 10px; color: white;\n  font-family: \'Syne\', sans-serif; font-size: 13px; font-weight: 700;\n  padding: 10px 24px; cursor: pointer; transition: opacity .2s;\n}\n.btn:hover { opacity: .85; }\n.btn-sm { padding: 7px 16px; font-size: 12px; }\n.btn-red { background: var(--red); }\n.btn-ghost {\n  background: rgba(255,255,255,0.06); border: 1px solid var(--border);\n  color: var(--text);\n}\n\n/* TOAST */\n.toast {\n  position: fixed; bottom: 28px; right: 28px;\n  background: var(--green); color: #000;\n  font-weight: 700; font-size: 13px;\n  padding: 12px 20px; border-radius: 12px;\n  opacity: 0; transition: opacity .3s; pointer-events: none; z-index: 999;\n}\n.toast.show { opacity: 1; }\n\n/* RR TABLE */\n.rr-table { width: 100%; border-collapse: collapse; font-size: 13px; }\n.rr-table th { text-align: left; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; padding: 8px 12px; border-bottom: 1px solid var(--border); }\n.rr-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); font-family: \'DM Mono\', monospace; }\n.rr-table tr:last-child td { border-bottom: none; }\n\n/* HELP */\n.help { background: rgba(91,61,232,0.08); border: 1px solid rgba(91,61,232,0.2); border-radius: 10px; padding: 12px 16px; font-size: 12px; color: var(--muted); margin-bottom: 16px; line-height: 1.6; }\n.help b { color: var(--purple-l); }\n</style>\n</head>\n<body>\n\n<div class="sidebar">\n  <div class="logo">⚡ The Family</div>\n\n  <button class="nav-item active" onclick="showPage(\'dashboard\', this)">🏠 Dashboard</button>\n  <button class="nav-item" onclick="showPage(\'welcome\', this)">👋 Bienvenida</button>\n  <button class="nav-item" onclick="showPage(\'reaction_roles\', this)">🎭 Reaction Roles</button>\n  <button class="nav-item" onclick="showPage(\'xp\', this)">⭐ Sistema XP</button>\n  <button class="nav-item" onclick="showPage(\'stream\', this)">🔴 Stream Alerts</button>\n  <button class="nav-item" onclick="showPage(\'moderation\', this)">🛡️ Moderación</button>\n\n  <div class="nav-sep"></div>\n  <a href="/logout" class="nav-item nav-logout">🚪 Salir</a>\n</div>\n\n<div class="main">\n\n  <!-- DASHBOARD -->\n  <div class="page active" id="page-dashboard">\n    <h2>Dashboard</h2>\n    <p class="page-sub">Resumen del servidor The Family</p>\n    <div class="stats">\n      <div class="stat"><div class="stat-label">Estado</div><div class="stat-val green">Online</div></div>\n      <div class="stat"><div class="stat-label">Reaction Roles</div><div class="stat-val purple" id="stat-rr">—</div></div>\n      <div class="stat"><div class="stat-label">Sistema XP</div><div class="stat-val blue" id="stat-xp">—</div></div>\n      <div class="stat"><div class="stat-label">Bienvenida</div><div class="stat-val yellow" id="stat-welcome">—</div></div>\n    </div>\n    <div class="card">\n      <div class="card-title">Comandos disponibles en Discord</div>\n      <table class="rr-table">\n        <tr><th>Comando</th><th>Descripción</th><th>Quién puede usarlo</th></tr>\n        <tr><td>/ping</td><td>Ver si el bot está vivo</td><td>Todos</td></tr>\n        <tr><td>/rank</td><td>Ver tu nivel y XP</td><td>Todos</td></tr>\n        <tr><td>/leaderboard</td><td>Top 10 del server</td><td>Todos</td></tr>\n        <tr><td>/sorteo</td><td>Iniciar un sorteo</td><td>Admin</td></tr>\n        <tr><td>/say</td><td>Hacer hablar al bot</td><td>Admin</td></tr>\n        <tr><td>/embed</td><td>Enviar embed personalizado</td><td>Admin</td></tr>\n        <tr><td>/warn</td><td>Advertir a un usuario</td><td>Staff</td></tr>\n        <tr><td>/clear</td><td>Borrar mensajes</td><td>Staff</td></tr>\n        <tr><td>/panel</td><td>Link a este panel</td><td>Admin</td></tr>\n      </table>\n    </div>\n  </div>\n\n  <!-- BIENVENIDA -->\n  <div class="page" id="page-welcome">\n    <h2>👋 Bienvenida</h2>\n    <p class="page-sub">Configura el mensaje que ve cada nuevo miembro</p>\n\n    <div class="card">\n      <div class="toggle-row">\n        <span class="toggle-label">Activar bienvenida automática</span>\n        <label class="toggle"><input type="checkbox" id="welcome-enabled"><span class="slider"></span></label>\n      </div>\n\n      <div class="help">\n        Variables disponibles: <b>{user}</b> menciona al usuario, <b>{username}</b> nombre, <b>{server}</b> nombre del server, <b>{count}</b> número de miembros.\n      </div>\n\n      <div class="form-row">\n        <div class="form-group">\n          <label>Canal de bienvenida</label>\n          <select id="welcome-channel">\n            <option value="">— Elegir canal —</option>\n            {% for ch in channels %}\n            <option value="{{ ch.id }}"># {{ ch.name }}</option>\n            {% endfor %}\n          </select>\n        </div>\n        <div class="form-group">\n          <label>Rol automático al entrar</label>\n          <select id="welcome-role">\n            <option value="">— Sin rol automático —</option>\n            {% for r in roles %}\n            <option value="{{ r.id }}">{{ r.name }}</option>\n            {% endfor %}\n          </select>\n        </div>\n      </div>\n\n      <div class="form-row full">\n        <div class="form-group">\n          <label>Mensaje de bienvenida</label>\n          <textarea id="welcome-message" placeholder="👋 Bienvenido/a {user} a **{server}**! Ya somos {count} en la familia."></textarea>\n        </div>\n      </div>\n\n      <div class="form-row full">\n        <div class="form-group">\n          <label>URL del banner (imagen de bienvenida)</label>\n          <input type="url" id="welcome-banner" placeholder="https://tu-imagen.com/banner.png">\n        </div>\n      </div>\n\n      <button class="btn" onclick="saveWelcome()">💾 Guardar</button>\n    </div>\n\n    <div class="card">\n      <div class="card-title">Mensaje de despedida</div>\n      <div class="toggle-row">\n        <span class="toggle-label">Activar despedida automática</span>\n        <label class="toggle"><input type="checkbox" id="goodbye-enabled"><span class="slider"></span></label>\n      </div>\n      <div class="form-row">\n        <div class="form-group">\n          <label>Canal de despedida</label>\n          <select id="goodbye-channel">\n            <option value="">— Elegir canal —</option>\n            {% for ch in channels %}\n            <option value="{{ ch.id }}"># {{ ch.name }}</option>\n            {% endfor %}\n          </select>\n        </div>\n      </div>\n      <button class="btn" onclick="saveGoodbye()">💾 Guardar</button>\n    </div>\n  </div>\n\n  <!-- REACTION ROLES -->\n  <div class="page" id="page-reaction_roles">\n    <h2>🎭 Reaction Roles</h2>\n    <p class="page-sub">Asigná roles automáticamente cuando alguien reacciona a un mensaje</p>\n\n    <div class="card">\n      <div class="card-title">Agregar nuevo reaction role</div>\n      <div class="help">\n        1. Enviá el mensaje de roles en Discord con <b>/embed</b> o <b>/say</b><br>\n        2. Click derecho al mensaje → <b>Copiar ID</b> (necesitás modo desarrollador activado)<br>\n        3. Pegá el ID acá y configurá el emoji y el rol\n      </div>\n      <div class="form-row">\n        <div class="form-group">\n          <label>ID del mensaje</label>\n          <input type="text" id="rr-msg-id" placeholder="1234567890123456789">\n        </div>\n        <div class="form-group">\n          <label>Emoji</label>\n          <input type="text" id="rr-emoji" placeholder="🎮 o :nombre_emoji:">\n        </div>\n      </div>\n      <div class="form-row">\n        <div class="form-group">\n          <label>Rol a asignar</label>\n          <select id="rr-role">\n            <option value="">— Elegir rol —</option>\n            {% for r in roles %}\n            <option value="{{ r.id }}">{{ r.name }}</option>\n            {% endfor %}\n          </select>\n        </div>\n      </div>\n      <button class="btn" onclick="addRR()">➕ Agregar</button>\n    </div>\n\n    <div class="card">\n      <div class="card-title">Reaction roles activos</div>\n      <table class="rr-table">\n        <tr><th>Mensaje ID</th><th>Emoji</th><th>Rol ID</th><th></th></tr>\n      </table>\n      <div id="rr-empty" style="color:var(--muted);font-size:13px;padding:12px 0;">No hay reaction roles configurados.</div>\n    </div>\n  </div>\n\n  <!-- XP -->\n  <div class="page" id="page-xp">\n    <h2>⭐ Sistema de XP</h2>\n    <p class="page-sub">Los usuarios ganan 10 XP por mensaje. Al subir de nivel se anuncia automáticamente.</p>\n\n    <div class="card">\n      <div class="toggle-row">\n        <span class="toggle-label">Activar sistema de XP y niveles</span>\n        <label class="toggle"><input type="checkbox" id="xp-enabled"><span class="slider"></span></label>\n      </div>\n      <div class="form-row">\n        <div class="form-group">\n          <label>Canal para anunciar subidas de nivel</label>\n          <select id="xp-channel">\n            <option value="">— Mismo canal donde escribieron —</option>\n            {% for ch in channels %}\n            <option value="{{ ch.id }}"># {{ ch.name }}</option>\n            {% endfor %}\n          </select>\n        </div>\n      </div>\n      <button class="btn" onclick="saveXP()">💾 Guardar</button>\n    </div>\n  </div>\n\n  <!-- STREAM -->\n  <div class="page" id="page-stream">\n    <h2>🔴 Stream Alerts</h2>\n    <p class="page-sub">El bot avisa automáticamente cuando estás en vivo</p>\n\n    <div class="card">\n      <div class="toggle-row">\n        <span class="toggle-label">Activar alertas de stream</span>\n        <label class="toggle"><input type="checkbox" id="stream-enabled"><span class="slider"></span></label>\n      </div>\n      <div class="help">\n        Variables: <b>{username}</b> tu usuario, <b>{url}</b> link al stream, <b>{title}</b> título del stream.\n      </div>\n      <div class="form-row">\n        <div class="form-group">\n          <label>Canal de alertas</label>\n          <select id="stream-channel">\n            <option value="">— Elegir canal —</option>\n            {% for ch in channels %}\n            <option value="{{ ch.id }}"># {{ ch.name }}</option>\n            {% endfor %}\n          </select>\n        </div>\n      </div>\n      <div class="form-row">\n        <div class="form-group">\n          <label>Usuario de Kick</label>\n          <input type="text" id="stream-kick" placeholder="cesarmonsalve">\n        </div>\n        <div class="form-group">\n          <label>Usuario de TikTok</label>\n          <input type="text" id="stream-tiktok" placeholder="@cesarmonsalve">\n        </div>\n      </div>\n      <div class="form-row full">\n        <div class="form-group">\n          <label>Mensaje de alerta</label>\n          <textarea id="stream-message" placeholder="🔴 {username} está en vivo! Entrá acá → {url}"></textarea>\n        </div>\n      </div>\n      <button class="btn" onclick="saveStream()">💾 Guardar</button>\n    </div>\n  </div>\n\n  <!-- MODERACIÓN -->\n  <div class="page" id="page-moderation">\n    <h2>🛡️ Moderación</h2>\n    <p class="page-sub">Protección automática del servidor</p>\n\n    <div class="card">\n      <div class="toggle-row">\n        <span class="toggle-label">Anti-links (borra links de usuarios sin permisos)</span>\n        <label class="toggle"><input type="checkbox" id="mod-antilinks"><span class="slider"></span></label>\n      </div>\n      <button class="btn" onclick="saveMod()">💾 Guardar</button>\n    </div>\n  </div>\n\n</div>\n\n<div class="toast" id="toast">✅ Guardado</div>\n\n<script>\nconst cfg = {{ cfg | tojson }};\n\nfunction showPage(name, btn) {\n  document.querySelectorAll(\'.page\').forEach(p => p.classList.remove(\'active\'));\n  document.querySelectorAll(\'.nav-item\').forEach(b => b.classList.remove(\'active\'));\n  document.getElementById(\'page-\' + name).classList.add(\'active\');\n  btn.classList.add(\'active\');\n  if (name === \'reaction_roles\') loadRR();\n}\n\nfunction toast(msg = \'✅ Guardado\') {\n  const t = document.getElementById(\'toast\');\n  t.textContent = msg; t.classList.add(\'show\');\n  setTimeout(() => t.classList.remove(\'show\'), 2500);\n}\n\nfunction post(url, data) {\n  return fetch(url, { method: \'POST\', headers: {\'Content-Type\':\'application/json\'}, body: JSON.stringify(data) });\n}\n\n// ─── LOAD CONFIG ────────────────────────────────────────────\nwindow.onload = () => {\n  // Welcome\n  if (cfg.welcome) {\n    document.getElementById(\'welcome-enabled\').checked = cfg.welcome.enabled;\n    document.getElementById(\'welcome-channel\').value = cfg.welcome.channel_id || \'\';\n    document.getElementById(\'welcome-role\').value = cfg.welcome.auto_role_id || \'\';\n    document.getElementById(\'welcome-message\').value = cfg.welcome.message || \'\';\n    document.getElementById(\'welcome-banner\').value = cfg.welcome.banner_url || \'\';\n  }\n  if (cfg.goodbye) {\n    document.getElementById(\'goodbye-enabled\').checked = cfg.goodbye.enabled;\n    document.getElementById(\'goodbye-channel\').value = cfg.goodbye.channel_id || \'\';\n  }\n  if (cfg.xp) {\n    document.getElementById(\'xp-enabled\').checked = cfg.xp.enabled;\n    document.getElementById(\'xp-channel\').value = cfg.xp.levelup_channel_id || \'\';\n  }\n  if (cfg.stream_alert) {\n    document.getElementById(\'stream-enabled\').checked = cfg.stream_alert.enabled;\n    document.getElementById(\'stream-channel\').value = cfg.stream_alert.channel_id || \'\';\n    document.getElementById(\'stream-kick\').value = cfg.stream_alert.kick_username || \'\';\n    document.getElementById(\'stream-tiktok\').value = cfg.stream_alert.tiktok_username || \'\';\n    document.getElementById(\'stream-message\').value = cfg.stream_alert.message || \'\';\n  }\n  if (cfg.moderation) {\n    document.getElementById(\'mod-antilinks\').checked = cfg.moderation.anti_links;\n  }\n\n  // Dashboard stats\n  document.getElementById(\'stat-rr\').textContent = (cfg.reaction_roles || []).length;\n  document.getElementById(\'stat-xp\').textContent = cfg.xp?.enabled ? \'ON\' : \'OFF\';\n  document.getElementById(\'stat-welcome\').textContent = cfg.welcome?.enabled ? \'ON\' : \'OFF\';\n};\n\n// ─── SAVE FUNCTIONS ─────────────────────────────────────────\nasync function saveWelcome() {\n  await post(\'/api/welcome\', {\n    enabled: document.getElementById(\'welcome-enabled\').checked,\n    channel_id: document.getElementById(\'welcome-channel\').value,\n    auto_role_id: document.getElementById(\'welcome-role\').value,\n    message: document.getElementById(\'welcome-message\').value,\n    banner_url: document.getElementById(\'welcome-banner\').value,\n  });\n  toast();\n}\n\nasync function saveGoodbye() {\n  await post(\'/api/goodbye\', {\n    enabled: document.getElementById(\'goodbye-enabled\').checked,\n    channel_id: document.getElementById(\'goodbye-channel\').value,\n  });\n  toast();\n}\n\nasync function saveXP() {\n  await post(\'/api/xp\', {\n    enabled: document.getElementById(\'xp-enabled\').checked,\n    levelup_channel_id: document.getElementById(\'xp-channel\').value,\n  });\n  toast();\n}\n\nasync function saveStream() {\n  await post(\'/api/stream_alert\', {\n    enabled: document.getElementById(\'stream-enabled\').checked,\n    channel_id: document.getElementById(\'stream-channel\').value,\n    kick_username: document.getElementById(\'stream-kick\').value,\n    tiktok_username: document.getElementById(\'stream-tiktok\').value,\n    message: document.getElementById(\'stream-message\').value,\n  });\n  toast();\n}\n\nasync function saveMod() {\n  await post(\'/api/moderation\', {\n    anti_links: document.getElementById(\'mod-antilinks\').checked,\n  });\n  toast();\n}\n\n// ─── REACTION ROLES ─────────────────────────────────────────\nasync function loadRR() {\n  const res = await fetch(\'/api/reaction_roles\');\n  const rrs = await res.json();\n  const tbody = document.querySelector(\'.rr-table\');\n  const empty = document.getElementById(\'rr-empty\');\n  const rows = Array.from(tbody.querySelectorAll(\'tr\')).slice(1);\n  rows.forEach(r => r.remove());\n  if (rrs.length === 0) { empty.style.display = \'block\'; return; }\n  empty.style.display = \'none\';\n  rrs.forEach((rr, i) => {\n    const tr = document.createElement(\'tr\');\n    tr.innerHTML = `<td>${rr.message_id}</td><td>${rr.emoji}</td><td>${rr.role_id}</td>\n      <td><button class="btn btn-sm btn-red" onclick="deleteRR(${i})">Eliminar</button></td>`;\n    tbody.appendChild(tr);\n  });\n}\n\nasync function addRR() {\n  const msg_id = document.getElementById(\'rr-msg-id\').value.trim();\n  const emoji  = document.getElementById(\'rr-emoji\').value.trim();\n  const role   = document.getElementById(\'rr-role\').value;\n  if (!msg_id || !emoji || !role) { alert(\'Completá todos los campos\'); return; }\n  await post(\'/api/reaction_roles\', { message_id: msg_id, emoji, role_id: role });\n  document.getElementById(\'rr-msg-id\').value = \'\';\n  document.getElementById(\'rr-emoji\').value = \'\';\n  document.getElementById(\'rr-role\').value = \'\';\n  loadRR(); toast(\'✅ Reaction role agregado\');\n}\n\nasync function deleteRR(i) {\n  await fetch(`/api/reaction_roles/${i}`, { method: \'DELETE\' });\n  loadRR(); toast(\'🗑️ Eliminado\');\n}\n</script>\n</body>\n</html>\n'

# ── APP ──────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET", "thefamily2024secret")

BOT_TOKEN      = os.environ.get("BOT_TOKEN")
GUILD_ID       = os.environ.get("GUILD_ID", "1486498876503894707")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "cesar2024")

# ── CONFIG ───────────────────────────────────────────────────
def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)

# ── DISCORD API ──────────────────────────────────────────────
def get_guild_channels():
    try:
        r = req_lib.get(
            f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            timeout=5
        )
        return [c for c in r.json() if isinstance(c, dict) and c.get("type") == 0]
    except Exception:
        return []

def get_guild_roles():
    try:
        r = req_lib.get(
            f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            timeout=5
        )
        return [ro for ro in r.json() if isinstance(ro, dict) and ro.get("name") != "@everyone"]
    except Exception:
        return []

# ── AUTH ─────────────────────────────────────────────────────
def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PANEL_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return render_template_string(LOGIN_HTML, error="Contraseña incorrecta")
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ── PANEL ────────────────────────────────────────────────────
@app.route("/")
@auth_required
def index():
    cfg      = load_config()
    channels = get_guild_channels()
    roles    = get_guild_roles()
    return render_template_string(INDEX_HTML, cfg=cfg, channels=channels, roles=roles)

# ── API ──────────────────────────────────────────────────────
@app.route("/api/welcome", methods=["POST"])
@auth_required
def api_welcome():
    cfg  = load_config()
    data = request.json
    cfg["welcome"] = {
        "enabled":      data.get("enabled", False),
        "channel_id":   data.get("channel_id"),
        "message":      data.get("message", "👋 Bienvenido/a {user} a **{server}**!"),
        "banner_url":   data.get("banner_url", ""),
        "auto_role_id": data.get("auto_role_id"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/goodbye", methods=["POST"])
@auth_required
def api_goodbye():
    cfg  = load_config()
    data = request.json
    cfg["goodbye"] = {
        "enabled":    data.get("enabled", False),
        "channel_id": data.get("channel_id"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/xp", methods=["POST"])
@auth_required
def api_xp():
    cfg  = load_config()
    data = request.json
    cfg["xp"] = {
        "enabled":           data.get("enabled", False),
        "levelup_channel_id": data.get("levelup_channel_id"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/moderation", methods=["POST"])
@auth_required
def api_moderation():
    cfg  = load_config()
    data = request.json
    cfg["moderation"] = {"anti_links": data.get("anti_links", False)}
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/reaction_roles", methods=["GET"])
@auth_required
def api_rr_get():
    return jsonify(load_config().get("reaction_roles", []))

@app.route("/api/reaction_roles", methods=["POST"])
@auth_required
def api_rr_add():
    cfg  = load_config()
    data = request.json
    rr   = cfg.get("reaction_roles", [])
    rr.append({"message_id": data["message_id"], "emoji": data["emoji"], "role_id": data["role_id"]})
    cfg["reaction_roles"] = rr
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/reaction_roles/<int:index>", methods=["DELETE"])
@auth_required
def api_rr_delete(index):
    cfg = load_config()
    rr  = cfg.get("reaction_roles", [])
    if 0 <= index < len(rr):
        rr.pop(index)
    cfg["reaction_roles"] = rr
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/stream_alert", methods=["POST"])
@auth_required
def api_stream():
    cfg  = load_config()
    data = request.json
    cfg["stream_alert"] = {
        "enabled":         data.get("enabled", False),
        "channel_id":      data.get("channel_id"),
        "kick_username":   data.get("kick_username", ""),
        "tiktok_username": data.get("tiktok_username", ""),
        "message":         data.get("message", "🔴 {username} está en vivo! {url}"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/config", methods=["GET"])
@auth_required
def api_config_get():
    return jsonify(load_config())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
