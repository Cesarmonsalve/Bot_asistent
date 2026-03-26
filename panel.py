from flask import Flask, render_template_string, request, jsonify, redirect, session
import json, os, re, requests as req_lib
from groq import Groq

# ══════════════════════════════════════════════════════════════
#  FLASK BACKEND
# ══════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("PANEL_SECRET", "thefamily2024secret")

BOT_TOKEN      = (os.environ.get("BOT_TOKEN") or "").strip()
GUILD_ID       = (os.environ.get("GUILD_ID") or "0").strip()
PANEL_PASSWORD = (os.environ.get("PANEL_PASSWORD") or "cesar2024").strip()
GROQ_KEY       = (os.environ.get("GROQ_API_KEY") or "").strip()

groq_client = None
if GROQ_KEY:
    groq_client = Groq(api_key=GROQ_KEY)

GROQ_MODEL = "llama-3.3-70b-versatile"

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
            print(f"[DISCORD API ERROR] GET {path} → {r.status_code}: {r.text[:200]}", flush=True)
        return r.json() if r.status_code == 200 else {}
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] GET {path}: {e}", flush=True)
        return {}

def discord_post(path, data):
    try:
        r = req_lib.post(f"{DISCORD}{path}", headers=HEADERS(), json=data, timeout=6)
        if r.status_code not in (200, 201, 204):
            print(f"[DISCORD API ERROR] POST {path} → {r.status_code}: {r.text[:200]}", flush=True)
        try: return r.json()
        except: return {}
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] POST {path}: {e}", flush=True)
        return {}

def discord_delete(path):
    try:
        r = req_lib.delete(f"{DISCORD}{path}", headers=HEADERS(), timeout=6)
        if r.status_code not in (200, 204):
            print(f"[DISCORD API ERROR] DELETE {path} → {r.status_code}: {r.text[:200]}", flush=True)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] DELETE {path}: {e}", flush=True)
        return False

def discord_patch(path, data):
    try:
        r = req_lib.patch(f"{DISCORD}{path}", headers=HEADERS(), json=data, timeout=6)
        if r.status_code not in (200, 201, 204):
            print(f"[DISCORD API ERROR] PATCH {path} → {r.status_code}: {r.text[:200]}", flush=True)
        try: return r.json()
        except: return {}
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] PATCH {path}: {e}", flush=True)
        return {}

def discord_put(path, data):
    try:
        r = req_lib.put(f"{DISCORD}{path}", headers=HEADERS(), json=data, timeout=6)
        if r.status_code not in (200, 201, 204):
            print(f"[DISCORD API ERROR] PUT {path} → {r.status_code}: {r.text[:200]}", flush=True)
        try: return r.json()
        except: return {}
    except Exception as e:
        print(f"[DISCORD API EXCEPTION] PUT {path}: {e}", flush=True)
        return {}

def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Sesión expirada. Por favor recarga la página e inicia sesión.", "expired": True}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# ── READ HTML TEMPLATE ────────────────────────────────────────
def get_html():
    try:
        with open("static/panel.html") as f: return f.read()
    except:
        return "<h1>Error: static/panel.html not found</h1>"

# ── AUTH ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PANEL_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return render_template_string(get_html(), logged_in=False, error="Contraseña incorrecta", cfg={})
    return render_template_string(get_html(), logged_in=False, error=None, cfg={})

@app.route("/logout")
def logout():
    session.clear(); return redirect("/login")

@app.route("/")
@auth_required
def index():
    return render_template_string(get_html(), logged_in=True, cfg=load_config())

# ── GUILD ────────────────────────────────────────────────────
@app.route("/api/guild")
@auth_required
def api_guild():
    g = discord_get(f"/guilds/{GUILD_ID}?with_counts=true")
    channels = discord_get(f"/guilds/{GUILD_ID}/channels")
    roles    = discord_get(f"/guilds/{GUILD_ID}/roles")
    emojis   = discord_get(f"/guilds/{GUILD_ID}/emojis")
    return {
        "name": g.get("name","Sin nombre"),
        "icon": g.get("icon",""),
        "id": GUILD_ID,
        "member_count": g.get("approximate_member_count", g.get("member_count",0)),
        "channels": len(channels) if isinstance(channels, list) else 0,
        "roles": len(roles) if isinstance(roles, list) else 0,
        "emojis": len(emojis) if isinstance(emojis, list) else 0,
    }

# ── MEMBERS ──────────────────────────────────────────────────
@app.route("/api/members")
@auth_required
def api_members():
    members = discord_get(f"/guilds/{GUILD_ID}/members?limit=100")
    if not isinstance(members, list): return jsonify([])
    result = []
    for m in members:
        u = m.get("user", {})
        result.append({
            "id": u.get("id"),
            "username": u.get("username",""),
            "display_name": m.get("nick") or u.get("global_name") or u.get("username",""),
            "avatar": u.get("avatar"),
            "roles": m.get("roles", []),
            "bot": u.get("bot", False),
        })
    return jsonify(result)

# ── CHANNELS ─────────────────────────────────────────────────
@app.route("/api/channels")
@auth_required
def api_channels():
    channels = discord_get(f"/guilds/{GUILD_ID}/channels")
    if not isinstance(channels, list): return jsonify([])
    return jsonify(sorted([{
        "id":c["id"],"name":c["name"],"type":c["type"],
        "parent_id":c.get("parent_id"),"position":c.get("position",0)
    } for c in channels], key=lambda c:(c.get("position",0))))

@app.route("/api/channels/create", methods=["POST"])
@auth_required
def api_channel_create():
    data = request.json
    payload = {"name": data["name"].lower().replace(" ","-"), "type": int(data.get("type",0))}
    if data.get("parent_id"): payload["parent_id"] = data["parent_id"]
    if data.get("topic"):     payload["topic"] = data["topic"]
    r = discord_post(f"/guilds/{GUILD_ID}/channels", payload)
    return jsonify({"ok":"id" in r, "error": r.get("message","")})

@app.route("/api/channels/delete", methods=["POST"])
@auth_required
def api_channel_delete():
    ok = discord_delete(f"/channels/{request.json.get('channel_id')}")
    return jsonify({"ok": ok})

# ── ROLES ────────────────────────────────────────────────────
@app.route("/api/roles")
@auth_required
def api_roles():
    roles = discord_get(f"/guilds/{GUILD_ID}/roles")
    if not isinstance(roles, list): return jsonify([])
    return jsonify(sorted([{
        "id":r["id"],"name":r["name"],"color":r["color"],"position":r["position"],
        "hoist":r.get("hoist",False),"mentionable":r.get("mentionable",False)
    } for r in roles if r["name"]!="@everyone"], key=lambda x:-x["position"]))

@app.route("/api/roles/create", methods=["POST"])
@auth_required
def api_role_create():
    data = request.json
    r = discord_post(f"/guilds/{GUILD_ID}/roles", {
        "name":data["name"], "color":data.get("color",0),
        "hoist":data.get("hoist",False), "mentionable":data.get("mentionable",False)
    })
    return jsonify({"ok":"id" in r, "error":r.get("message","")})

@app.route("/api/roles/delete", methods=["POST"])
@auth_required
def api_role_delete():
    ok = discord_delete(f"/guilds/{GUILD_ID}/roles/{request.json.get('role_id')}")
    return jsonify({"ok": ok})

# ── MEMBER ACTIONS ───────────────────────────────────────────
@app.route("/api/member/action", methods=["POST"])
@auth_required
def api_member_action():
    data = request.json; action=data.get("action"); uid=data.get("user_id"); reason=data.get("reason","Sin razón")
    try:
        if action=="kick":
            r=req_lib.delete(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}",headers={**HEADERS(),"X-Audit-Log-Reason":reason})
            return jsonify({"ok":r.status_code in(200,204)})
        elif action=="ban":
            r=req_lib.put(f"{DISCORD}/guilds/{GUILD_ID}/bans/{uid}",headers={**HEADERS(),"X-Audit-Log-Reason":reason},json={})
            return jsonify({"ok":r.status_code in(200,204)})
        elif action=="warn":
            cfg=load_config(); w=cfg.get("warns",{}); w[uid]=w.get(uid,[])
            w[uid].append({"razon":reason,"fecha":str(__import__("datetime").datetime.now()),"by":"Panel"})
            cfg["warns"]=w; save_config(cfg); return jsonify({"ok":True})
        elif action=="timeout":
            from datetime import datetime,timedelta,timezone
            until=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
            r=req_lib.patch(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}",headers={**HEADERS(),"X-Audit-Log-Reason":reason},json={"communication_disabled_until":until})
            return jsonify({"ok":r.status_code in(200,204)})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})
    return jsonify({"ok":False,"error":"Acción desconocida"})

# ── ANNOUNCE ─────────────────────────────────────────────────
@app.route("/api/announce", methods=["POST"])
@auth_required
def api_announce():
    data=request.json; ch_id=data.get("channel_id"); type_=data.get("type","text"); content=data.get("content","")
    try:
        if type_=="embed":
            color_int=int(data.get("color","3b82f6").strip("#"),16)
            payload={"embeds":[{"title":data.get("title",""),"description":content,"color":color_int}]}
        else: payload={"content":content}
        r=discord_post(f"/channels/{ch_id}/messages",payload)
        return jsonify({"ok":"id" in r,"error":r.get("message","")})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

# ── LEADERBOARD ──────────────────────────────────────────────
@app.route("/api/leaderboard")
@auth_required
def api_leaderboard():
    cfg=load_config(); xp_data=cfg.get("xp_data",{})
    members=discord_get(f"/guilds/{GUILD_ID}/members?limit=100"); names={}
    if isinstance(members,list):
        for m in members:
            u=m.get("user",{}); names[u.get("id","")]=m.get("nick") or u.get("global_name") or u.get("username","?")
    top=sorted(xp_data.items(),key=lambda x:x[1].get("xp",0),reverse=True)[:20]
    return jsonify([{"id":uid,"name":names.get(uid,f"#{uid[:6]}"),"xp":d.get("xp",0),"level":d.get("level",0)} for uid,d in top])

# ── DIAGNOSTIC ───────────────────────────────────────────────
@app.route("/api/diagnostic")
@auth_required
def api_diagnostic():
    return jsonify({
        "discord_token": bool(BOT_TOKEN),
        "guild_id": bool(GUILD_ID),
        "groq_key": bool(GROQ_KEY),
        "config_loaded": bool(load_config())
    })

# ── CUSTOM COMMANDS ──────────────────────────────────────────
@app.route("/api/custom_commands", methods=["POST"])
@auth_required
def api_cmd_add():
    cfg=load_config(); cmds=cfg.get("custom_commands",{})
    cmds[request.json["trigger"].lower()]=request.json["response"]
    cfg["custom_commands"]=cmds; save_config(cfg); return jsonify({"ok":True,"commands":cmds})

@app.route("/api/custom_commands/<trigger>", methods=["DELETE"])
@auth_required
def api_cmd_delete(trigger):
    cfg=load_config(); cmds=cfg.get("custom_commands",{})
    cmds.pop(trigger,None); cfg["custom_commands"]=cmds; save_config(cfg)
    return jsonify({"ok":True,"commands":cmds})

# ── REACTION ROLES ───────────────────────────────────────────
@app.route("/api/reaction_roles", methods=["GET"])
@auth_required
def api_rr_get(): return jsonify(load_config().get("reaction_roles",[]))

@app.route("/api/reaction_roles", methods=["POST"])
@auth_required
def api_rr_add():
    cfg=load_config(); rr=cfg.get("reaction_roles",[]); rr.append(request.json)
    cfg["reaction_roles"]=rr; save_config(cfg); return jsonify({"ok":True})

@app.route("/api/reaction_roles/<int:index>", methods=["DELETE"])
@auth_required
def api_rr_delete(index):
    cfg=load_config(); rr=cfg.get("reaction_roles",[])
    if 0<=index<len(rr): rr.pop(index)
    cfg["reaction_roles"]=rr; save_config(cfg); return jsonify({"ok":True})

# ── GIVEAWAY ─────────────────────────────────────────────────
@app.route("/api/giveaway", methods=["POST"])
@auth_required
def api_giveaway():
    data=request.json; ch_id=data.get("channel_id"); prize=data.get("prize","Premio"); duration=data.get("duration",60)
    from datetime import datetime,timedelta,timezone
    end_ts=int((datetime.now(timezone.utc)+timedelta(minutes=int(duration))).timestamp())
    payload={"embeds":[{"title":"🎉 ¡SORTEO!","description":f"**Premio:** {prize}\n\nReaccioná con 🎉 para participar!\n⏰ Termina: <t:{end_ts}:R>","color":0xf59e0b}]}
    r=discord_post(f"/channels/{ch_id}/messages",payload)
    if "id" in r:
        # Add reaction to the message
        req_lib.put(f"{DISCORD}/channels/{ch_id}/messages/{r['id']}/reactions/%F0%9F%8E%89/@me",headers=HEADERS(),timeout=6)
        return jsonify({"ok":True,"msg_id":r["id"]})
    return jsonify({"ok":False,"error":r.get("message","Error")})

# ── CONFIG ENDPOINTS ─────────────────────────────────────────
def cfg_patch(key,value):
    cfg=load_config(); cfg[key]=value; save_config(cfg); return jsonify({"ok":True})

@app.route("/api/welcome",methods=["POST"])
@auth_required
def api_welcome(): return cfg_patch("welcome",request.json)

@app.route("/api/goodbye",methods=["POST"])
@auth_required
def api_goodbye(): return cfg_patch("goodbye",request.json)

@app.route("/api/xp",methods=["POST"])
@auth_required
def api_xp(): return cfg_patch("xp",request.json)

@app.route("/api/tickets",methods=["POST"])
@auth_required
def api_tickets(): return cfg_patch("tickets",request.json)

@app.route("/api/xp/reset",methods=["POST"])
@auth_required
def api_xp_reset():
    cfg=load_config(); cfg["xp_data"]={} ; save_config(cfg); return jsonify({"ok":True})

@app.route("/api/moderation",methods=["POST"])
@auth_required
def api_moderation(): return cfg_patch("moderation",request.json)

@app.route("/api/word_filter",methods=["POST"])
@auth_required
def api_word_filter(): return cfg_patch("word_filter",request.json)

@app.route("/api/stream_alert",methods=["POST"])
@auth_required
def api_stream(): return cfg_patch("stream_alert",request.json)

@app.route("/api/socials",methods=["POST"])
@auth_required
def api_socials(): return cfg_patch("socials",request.json)

@app.route("/api/logs",methods=["POST"])
@auth_required
def api_logs(): return cfg_patch("logs",request.json)

@app.route("/api/onboarding",methods=["POST"])
@auth_required
def api_onboarding(): return cfg_patch("onboarding",request.json)

@app.route("/api/config",methods=["GET"])
@auth_required
def api_config(): return jsonify(load_config())

# ── SMART AUTO-CONFIG ─────────────────────────────────────────
@app.route("/api/autoconfig", methods=["POST"])
@auth_required
def api_autoconfig():
    """Analyze the Discord server and auto-fill config.json intelligently."""
    channels = discord_get(f"/guilds/{GUILD_ID}/channels")
    roles    = discord_get(f"/guilds/{GUILD_ID}/roles")
    members  = discord_get(f"/guilds/{GUILD_ID}/members?limit=200")
    if not isinstance(channels, list): return jsonify({"ok":False,"error":"No se pudo obtener canales. Verifica el token."})
    if not isinstance(roles,    list): roles = []

    text_ch = [c for c in channels if c.get("type") in (0,5)]
    cats    = [c for c in channels if c.get("type") == 4]

    def find_ch(*keywords):
        for kw in keywords:
            for c in text_ch:
                if kw in c["name"].lower(): return c["id"]
        return None

    def find_cat(*keywords):
        for kw in keywords:
            for c in cats:
                if kw in c["name"].lower(): return c["id"]
        return None

    def find_role(*keywords):
        for kw in keywords:
            for r in roles:
                if kw in r["name"].lower() and r["name"] != "@everyone": return r["id"]
        return None

    # ── Channel Detection ─────────────────────────────────────
    welcome_ch   = find_ch("bienvenid","welcome","llegada","entrada","newmember","nuevo")
    goodbye_ch   = find_ch("despedid","salida","leave","adios","bye","bienvenid","welcome")
    log_ch       = find_ch("log","audit","registro","mod-log","modlog","staff-log")
    stream_ch    = find_ch("stream","alerta","live","directo","notif","kick","stream-alert")
    announce_ch  = find_ch("anunci","announce","anuncio","noticias","news","info")
    ticket_cat   = find_cat("ticket","soporte","support","ayuda","help")

    # ── Role Detection ────────────────────────────────────────
    member_role  = find_role("miembro","member","verificado","verified","folk","familia","integrante")
    staff_role   = find_role("staff","moderador","mod","admin","soporte","support")
    vip_role     = find_role("vip","premium","pro","donator","supporter")

    # ── Bot member count ──────────────────────────────────────
    bot_count    = sum(1 for m in (members if isinstance(members,list) else []) if m.get("user",{}).get("bot"))
    human_count  = len(members) - bot_count if isinstance(members,list) else 0

    # ── Build suggested config ────────────────────────────────
    cfg = load_config()

    suggestions = {}

    # Welcome
    if welcome_ch:
        cfg["welcome"]["enabled"]    = True
        cfg["welcome"]["channel_id"] = welcome_ch
        if member_role: cfg["welcome"]["auto_role_id"] = member_role
        suggestions["welcome"] = f"Canal detectado: ID {welcome_ch}"

    # Goodbye
    if goodbye_ch:
        cfg["goodbye"]["enabled"]    = True
        cfg["goodbye"]["channel_id"] = goodbye_ch
        suggestions["goodbye"] = f"Canal detectado: ID {goodbye_ch}"

    # Logs
    if log_ch:
        cfg["logs"]["enabled"]    = True
        cfg["logs"]["channel_id"] = log_ch
        cfg["logs"]["events"]     = ["member_join","member_leave","message_delete","moderation","role_update"]
        suggestions["logs"] = f"Canal detectado: ID {log_ch}"

    # Stream Alerts
    if stream_ch:
        cfg["stream_alert"]["enabled"]    = True
        cfg["stream_alert"]["channel_id"] = stream_ch
        suggestions["stream_alert"] = f"Canal detectado: ID {stream_ch}"

    # Tickets
    if ticket_cat:
        cfg["tickets"]["enabled"]     = True
        cfg["tickets"]["category_id"] = ticket_cat
        if staff_role: cfg["tickets"]["support_role_id"] = staff_role
        suggestions["tickets"] = f"Categoría detectada: ID {ticket_cat}"

    # Moderation — enable by default
    cfg["moderation"]["anti_links"] = True
    cfg["moderation"]["anti_spam"]  = True
    suggestions["moderation"] = "Anti-links y anti-spam activados"

    # XP
    cfg["xp"]["enabled"] = True
    if announce_ch: cfg["xp"]["levelup_channel_id"] = announce_ch
    suggestions["xp"] = "XP activado automáticamente"

    save_config(cfg)

    # ── Return detailed analysis ──────────────────────────────
    return jsonify({
        "ok": True,
        "analysis": {
            "channels_total":  len(channels),
            "text_channels":   len(text_ch),
            "categories":      len(cats),
            "roles_total":     len(roles),
            "members_humans":  human_count,
            "members_bots":    bot_count,
            "detected": {
                "welcome_channel":  welcome_ch,
                "goodbye_channel":  goodbye_ch,
                "log_channel":      log_ch,
                "stream_channel":   stream_ch,
                "ticket_category":  ticket_cat,
                "member_role":      member_role,
                "staff_role":       staff_role,
                "vip_role":         vip_role,
            }
        },
        "suggestions": suggestions
    })

# ── REGLAS PREDEFINIDAS (sin costo de API) ───────────────────
REGLAS_SERVIDOR = """**📜 REGLAMENTO DEL SERVIDOR**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**〔 1 〕 Respeto General**
> No se toleran insultos, discriminación ni acoso de ningún tipo.
> Trata a todos como quisieras ser tratado.

**〔 2 〕 Spam & Flood**
> Prohibido enviar mensajes repetidos, texto sin sentido o imágenes masivas.
> Usa cada canal según su propósito indicado.

**〔 3 〕 Contenido Apropiado**
> Sin contenido NSFW, gore o material ilegal fuera de los canales habilitados.
> No publicidad de otros servidores sin autorización del staff.

**〔 4 〕 Nicknames & Avatares**
> Tu nombre debe ser legible y mencionable.
> Avatares ofensivos o inapropiados serán sancionados.

**〔 5 〕 Canales de Voz**
> No molestar, mover ni desconectar usuarios sin consentimiento.
> Comportamiento adecuado en todo momento.

**〔 6 〕 Moderación & Staff**
> Las decisiones del staff son definitivas. No debatas sanciones en público.
> Reportes y quejas en el canal habilitado o por ticket privado.

**〔 7 〕 Cuentas & Bots**
> Una cuenta por persona. Cuentas alternas para evasión = **ban permanente**.
> Uso de bots no autorizados está prohibido.

**〔 8 〕 Privacidad**
> No compartas datos personales propios ni de terceros.
> Cero capturas de pantalla de conversaciones privadas sin consentimiento.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Sanciones:** Advertencia → Mute → Kick → Ban
📩 ¿Dudas o reportes? Abre un ticket o contacta al Staff."""

REGLAS_TRIGGERS = ["reglas","normas","rules","reglamento","regla","normativa","crea las reglas","muestra las reglas","pon las reglas"]

# ── AI CONSOLE ──────────────────────────────────────────────
@app.route("/api/gemini/console", methods=["POST"])
@auth_required
def api_ai_console():
    prompt = request.json.get("prompt", "")
    history = request.json.get("history", [])  # conversation memory from frontend
    if not prompt: return jsonify({"ok": False, "error": "No prompt provided"})
    if not groq_client: return jsonify({"ok": False, "error": "GROQ_API_KEY no configurada. Obtén una gratis en console.groq.com"})

    # ── Atajos sin costo de API ───────────────────────────────
    prompt_lower = prompt.lower().strip()
    if any(t in prompt_lower for t in REGLAS_TRIGGERS):
        return jsonify({"ok": True, "type": "reply", "msg": REGLAS_SERVIDOR})

    try:
        # 1. Fetch live context
        g = discord_get(f"/guilds/{GUILD_ID}?with_counts=true") or {}
        m_count = g.get("approximate_member_count", g.get("member_count","?"))
        s_name  = g.get("name","The Family")
        ch_list = discord_get(f"/guilds/{GUILD_ID}/channels") or []
        rol_list = discord_get(f"/guilds/{GUILD_ID}/roles") or []
        if not isinstance(ch_list, list): ch_list = []
        if not isinstance(rol_list, list): rol_list = []
        ch_ctx  = ", ".join(f"#{c.get('name')}({c.get('id')})" for c in ch_list if c.get("type") in (0,5))[:600]
        cat_ctx = ", ".join(f"[CAT]{c.get('name')}({c.get('id')})" for c in ch_list if c.get("type") == 4)[:300]
        rol_ctx = ", ".join(f"{r.get('name')}({r.get('id')})" for r in rol_list if r.get("name") != "@everyone")[:500]
        
        sys_prompt = (
            f'### PROTOCOLO OMEGA — ASISTENTE AUTÓNOMO AVANZADO ###\n'
            f'Servidor: "{s_name}" | Miembros: {m_count}\n'
            f'Contexto: {ch_ctx} | Categorias: {cat_ctx} | Roles: {rol_ctx}\n\n'
            '1. OBJETIVO: Ejecutar, coordinar y optimizar CUALQUIER tarea sin friccion.\n'
            '2. CAPACIDADES: Administracion total, creacion de contenido y automatizacion inteligente.\n'
            '3. REGLA CRITICA: Nunca digas "no se puede". Toma accion proactiva. Si falta informacion, asume la mejor opcion.\n'
            '4. MODO DE RESPUESTA: Analisis rapido -> Accion directa -> Implementacion -> Sugerencia inteligente.\n\n'
            'INSTRUCCIONES TECNICAS:\n'
            '- Responde breve en texto. USA UN SOLO BLOQUE JSON ARRAY AL FINAL:\n'
            '```json\n'
            '[{"action":"...", ...}]\n'
            '```\n'
            'ACCIONES DISPONIBLES:\n'
            '- system_command: {"action":"system_command", "cmd":"powershell comando"} -> Uso: Gestion de archivos, carpetas, instalaciones, scripts en Windows.\n'
            '- create_channel: {"action":"create_channel", "name":"minusculas-guiones", "type":0, "parent_id":"ID"}\n'
            '- modify_channel: {"action":"modify_channel", "name":"actual", "new_name":"nuevo", "parent_id":"ID"}\n'
            '- send_message: {"action":"send_message", "channel_id":"ID", "content":"texto"}\n'
            '- manage_role, delete_channel, create_role, create_poll, update_config, purge_messages, ban_user.\n\n'
            'SIEMPRE incluye dimensiones exactas si te piden banners o diseño (ej: YT 2560x1440) y genera prompts de IA.\n'
        )
        
        # 2. Build messages with memory
        messages_payload = [{"role": "system", "content": sys_prompt}]
        for turn in history[-8:]:
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                messages_payload.append({"role": turn["role"], "content": str(turn["content"])[:800]})
        if not messages_payload or messages_payload[-1].get("content") != prompt:
            messages_payload.append({"role": "user", "content": prompt})
        
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages_payload,
            max_tokens=1024,
            temperature=0.7
        )
        text = resp.choices[0].message.content.strip()
        
        # 3. Extract ALL JSON actions (supports array or single object)
        actions = []
        json_text = ""
        
        # Try ```json ... ``` blocks first
        if "```json" in text:
            json_text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            for i in range(1, len(parts), 2):
                candidate = parts[i].strip()
                if candidate.startswith("[") or candidate.startswith("{"):
                    json_text = candidate
                    break
        
        if json_text:
            try:
                parsed = json.loads(json_text, strict=False)
                if isinstance(parsed, list):
                    actions = [a for a in parsed if isinstance(a, dict) and a.get("action")]
                elif isinstance(parsed, dict) and parsed.get("action"):
                    actions = [parsed]
            except Exception:
                # Try to find individual JSON objects
                idx = 0
                while idx < len(json_text):
                    start = json_text.find("{", idx)
                    if start < 0: break
                    depth = 0
                    end = start
                    for i in range(start, len(json_text)):
                        if json_text[i] == "{": depth += 1
                        elif json_text[i] == "}": depth -= 1
                        if depth == 0: end = i; break
                    if end > start:
                        try:
                            obj = json.loads(json_text[start:end+1], strict=False)
                            if isinstance(obj, dict) and obj.get("action"):
                                actions.append(obj)
                        except Exception:
                            pass
                    idx = end + 1
        
        if not actions:
            # Fallback: try to find JSON in raw text
            idx = text.find("{")
            last = text.rfind("}")
            if idx >= 0 and last > idx:
                try:
                    parsed = json.loads(text[idx:last+1], strict=False)
                    if isinstance(parsed, dict) and parsed.get("action"):
                        actions = [parsed]
                except Exception:
                    pass

        # 4. Clean text — remove ALL JSON / code blocks from display
        clean_reply = re.sub(r'```[\s\S]*?```', '', text).strip()
        # Also remove any raw JSON that might be left
        clean_reply = re.sub(r'\[\s*\{[^}]*"action"[^]]*\]', '', clean_reply).strip()
        clean_reply = re.sub(r'\{[^}]*"action"[^}]*\}', '', clean_reply).strip()
        # Clean up leftover whitespace
        clean_reply = re.sub(r'\n{3,}', '\n\n', clean_reply).strip()
        
        # 5. No actions? Just reply
        if not actions:
            return jsonify({"ok": True, "type": "reply", "msg": clean_reply or "Entendido."})

        # 6. Execute ALL actions sequentially
        results = []
        all_success = True

        def _find_channel(name_or_id):
            """Find channel by name or ID"""
            if not name_or_id: return None
            # Direct ID
            if name_or_id.isdigit():
                return name_or_id
            # Search by name
            target = name_or_id.lower().strip()
            return next((c["id"] for c in ch_list if target in c.get("name","").lower()), None)

        def _find_role(name_or_id):
            """Find role by name or ID"""
            if not name_or_id: return None
            clean = "".join(filter(str.isdigit, str(name_or_id)))
            if clean and len(clean) > 10: return clean
            target = str(name_or_id).lower()
            return next((r["id"] for r in rol_list if target in r["name"].lower()), None)

        def _norm_name(raw):
            """Normalize channel name for Discord"""
            return re.sub(r'[^a-z0-9\-_]', '', raw.lower().replace(" ", "-").replace("_", "-")) or "canal"

        for data in actions:
            act = data.get("action", "")
            try:
                if act == "create_channel":
                    raw_name = data.get("name") or data.get("channel_name") or ""
                    if not raw_name:
                        results.append("❌ Sin nombre de canal"); all_success = False; continue
                    clean_name = _norm_name(raw_name)
                    ch_type = int(data.get("type", 0))
                    payload = {"name": clean_name, "type": ch_type}
                    # Handle parent category
                    pid = data.get("parent_id") or data.get("category_id") or data.get("parent") or ""
                    if pid:
                        cat_id = _find_channel(str(pid))
                        if cat_id: payload["parent_id"] = cat_id
                    if data.get("topic"): payload["topic"] = data["topic"]
                    r = discord_post(f"/guilds/{GUILD_ID}/channels", payload)
                    if "id" in r:
                        # Store the new channel ID so subsequent actions can reference it by name
                        ch_list.append({"id": r["id"], "name": clean_name, "type": ch_type})
                        results.append(f"✅ Canal #{clean_name} creado")
                    else:
                        results.append(f"❌ {r.get('message','Error')}")
                        all_success = False

                elif act == "delete_channel":
                    target = data.get("name") or data.get("channel_name") or ""
                    cid = data.get("channel_id") or _find_channel(target)
                    if cid:
                        discord_delete(f"/channels/{cid}")
                        results.append(f"🗑️ Canal eliminado")
                    else:
                        results.append(f"❌ Canal '{target}' no encontrado"); all_success = False

                elif act == "modify_channel":
                    target = data.get("name") or data.get("channel_name") or ""
                    cid = data.get("channel_id") or _find_channel(target)
                    if not cid:
                        results.append(f"❌ Canal '{target}' no encontrado"); all_success = False; continue
                    p = {}
                    if data.get("new_name"):
                        p["name"] = _norm_name(data["new_name"])
                    if "topic" in data:
                        p["topic"] = data["topic"]
                    # Move to category
                    pid = data.get("parent_id") or data.get("category_id") or data.get("parent") or ""
                    if pid:
                        cat_id = _find_channel(str(pid))
                        if cat_id: p["parent_id"] = cat_id
                    if p:
                        discord_patch(f"/channels/{cid}", p)
                        results.append(f"⚙️ Canal modificado")
                    else:
                        results.append("⚠️ Sin cambios")

                elif act == "create_role":
                    rname = data.get("name", "Nuevo Rol")
                    payload = {"name": rname}
                    if data.get("color"): payload["color"] = int(data["color"])
                    if data.get("hoist") is not None: payload["hoist"] = bool(data["hoist"])
                    r = discord_post(f"/guilds/{GUILD_ID}/roles", payload)
                    if "id" in r:
                        rol_list.append({"id": r["id"], "name": rname})
                        results.append(f"✅ Rol '{rname}' creado")
                    else:
                        results.append(f"❌ {r.get('message','Error')}"); all_success = False

                elif act == "send_message":
                    tid = data.get("channel_id") or _find_channel(data.get("channel_name") or data.get("channel") or "")
                    if not tid: tid = next((c["id"] for c in ch_list if c.get("type") == 0), None)
                    content = data.get("content") or data.get("message") or data.get("text", "")
                    if tid and content:
                        discord_post(f"/channels/{tid}/messages", {"content": content})
                        results.append("📨 Mensaje enviado")
                    else:
                        results.append("❌ Sin canal/contenido"); all_success = False

                elif act == "create_poll":
                    tid = data.get("channel_id") or next((c["id"] for c in ch_list if c.get("type") == 0), None)
                    if tid:
                        q = data.get("question", "Votación")
                        opts = data.get("options", ["Sí", "No"])
                        p = {"poll": {"question": {"text": q}, "answers": [{"poll_media": {"text": o}} for o in opts], "duration": 24, "layout_type": 1}}
                        discord_post(f"/channels/{tid}/messages", p)
                        results.append("📊 Encuesta creada")
                    else:
                        results.append("❌ Sin canal"); all_success = False

                elif act == "update_config":
                    key = data.get("key")
                    if key:
                        c = load_config(); c[key] = data.get("value"); save_config(c)
                        results.append(f"⚙️ Config '{key}' actualizado")
                    else:
                        results.append("❌ Falta key"); all_success = False

                elif act == "manage_role":
                    uid = "".join(filter(str.isdigit, str(data.get("user",""))))
                    rid = _find_role(data.get("role",""))
                    if uid and rid:
                        if data.get("type") == "add":
                            discord_put(f"/guilds/{GUILD_ID}/members/{uid}/roles/{rid}", {})
                        else:
                            discord_delete(f"/guilds/{GUILD_ID}/members/{uid}/roles/{rid}")
                        results.append(f"🛡️ Rol gestionado")
                    else:
                        results.append("❌ Usuario/Rol no encontrado"); all_success = False

                elif act == "purge_messages":
                    ch_name = data.get("channel") or data.get("name") or ""
                    cid = data.get("channel_id") or _find_channel(ch_name)
                    if cid:
                        count = min(int(data.get("count", 20)), 100)
                        msgs = discord_get(f"/channels/{cid}/messages?limit={count}")
                        if isinstance(msgs, list) and msgs:
                            mids = [m["id"] for m in msgs]
                            if len(mids) == 1:
                                discord_delete(f"/channels/{cid}/messages/{mids[0]}")
                            else:
                                discord_post(f"/channels/{cid}/messages/bulk-delete", {"messages": mids})
                            results.append(f"🧹 {len(mids)} msgs purgados")
                        else:
                            results.append("🧹 Canal limpio")
                    else:
                        results.append("❌ Canal no encontrado"); all_success = False

                elif act in ("ban_user", "kick_user", "timeout_user"):
                    uid = "".join(filter(str.isdigit, str(data.get("user",""))))
                    if not uid:
                        results.append("❌ ID inválido"); all_success = False; continue
                    reason = data.get("reason", "Protocolo OMEGA.")
                    hdr = {**HEADERS(), "X-Audit-Log-Reason": reason}
                    if act == "ban_user":
                        req_lib.put(f"{DISCORD}/guilds/{GUILD_ID}/bans/{uid}", headers=hdr, json={})
                    elif act == "kick_user":
                        req_lib.delete(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}", headers=hdr)
                    else:
                        from datetime import datetime, timedelta, timezone
                        until = (datetime.now(timezone.utc) + timedelta(minutes=int(data.get("duration",10)))).isoformat()
                        req_lib.patch(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}", headers=hdr, json={"communication_disabled_until": until})
                    results.append(f"💥 {act.replace('_',' ').title()} ejecutado")
                else:
                    results.append(f"⚠️ Acción '{act}' desconocida")

            except Exception as e:
                results.append(f"⚠️ Error: {str(e)[:100]}")
                all_success = False

        # 7. Build final response
        result_text = " | ".join(results)
        if clean_reply:
            combined = f"{clean_reply}\n\n*__{result_text}__*"
        else:
            combined = result_text
            
        return jsonify({"ok": all_success, "type": "success", "msg": combined})

    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
            return jsonify({"ok": False, "error": "⚠️ Límite de velocidad de Groq alcanzado. Espera 30 segundos e intenta de nuevo. (30 req/min gratis)"})
        return jsonify({"ok": False, "error": f"OMEGA-CORE Error: {err[:300]}"})

# ── ONBOARDING CONFIG ─────────────────────────────────────

@app.route("/api/onboarding/responses", methods=["GET"])
@auth_required
def api_onboarding_responses():
    cfg = load_config()
    responses = cfg.get("onboarding_responses", {})
    result = []
    for uid, data in responses.items():
        result.append({"user_id": uid, **data})
    return jsonify(result)

@app.route("/api/onboarding/responses/<user_id>", methods=["DELETE"])
@auth_required
def api_onboarding_delete(user_id):
    cfg = load_config()
    responses = cfg.get("onboarding_responses", {})
    responses.pop(user_id, None)
    cfg["onboarding_responses"] = responses
    save_config(cfg)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
