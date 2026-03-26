from flask import Flask, render_template_string, request, jsonify, redirect, session
import json, os, re, requests as req_lib
from google import genai

# ══════════════════════════════════════════════════════════════
#  FLASK BACKEND
# ══════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("PANEL_SECRET", "thefamily2024secret")

BOT_TOKEN      = (os.environ.get("BOT_TOKEN") or "").strip()
GUILD_ID       = (os.environ.get("GUILD_ID") or "0").strip()
PANEL_PASSWORD = (os.environ.get("PANEL_PASSWORD") or "cesar2024").strip()
GEMINI_KEY     = (os.environ.get("GEMINI_API_KEY") or "").strip()

gemini_client = None
if GEMINI_KEY:
    gemini_client = genai.Client(api_key=GEMINI_KEY)

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

# ── AI CONSOLE ──────────────────────────────────────────────
@app.route("/api/gemini/console", methods=["POST"])
@auth_required
def api_ai_console():
    prompt = request.json.get("prompt", "")
    if not prompt: return jsonify({"ok": False, "error": "No prompt provided"})
    if not GEMINI_KEY: return jsonify({"ok": False, "error": "GEMINI_API_KEY no configurada."})

    try:
        # 1. Fetch live context
        g = discord_get(f"/guilds/{GUILD_ID}?with_counts=true") or {}
        m_count = g.get("approximate_member_count", g.get("member_count","?"))
        s_name  = g.get("name","The Family")
        ch_list = discord_get(f"/guilds/{GUILD_ID}/channels") or []
        rol_list = discord_get(f"/guilds/{GUILD_ID}/roles") or []
        ch_ctx  = ", ".join(f"#{c.get('name')}({c.get('id')})" for c in ch_list if c.get("type") == 0)[:600]
        rol_ctx = ", ".join(f"{r.get('name')}({r.get('id')})" for r in rol_list if r.get("name") != "@everyone")[:500]
        
        sys_prompt = f'''Eres "THE FAMILY OMEGA", la IA Omnipotente del servidor "{s_name}".
TIENES CONTROL TOTAL SOBRE {m_count} MIEMBROS.
Canales reales: {ch_ctx}
Roles reales: {rol_ctx}

Tu misión es la excelencia. Habla de forma SUPERIOR y CONVERSACIONAL.
Si la orden requiere interactuar con el servidor, añade al final un bloque JSON:
```json
{{"action": "...", ...}}
```
Acciones: create_channel, delete_channel, modify_channel, create_poll, update_config, manage_role, create_role, purge_messages, ban_user, kick_user, timeout_user, send_message.
'''
        
        # 2. Generate content
        resp = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"{sys_prompt}\n\nOrden del Comandante: {prompt}"
        )
        text = resp.text.strip()
        
        # 3. Robust Extraction
        data = None
        json_text = ""
        if "```json" in text: json_text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:   json_text = text.split("```")[1].split("```")[0].strip()
        
        if json_text:
            idx = json_text.find("{")
            last = json_text.rfind("}")
            if idx >= 0 and last > idx: json_text = json_text[idx:last+1]
            try: data = json.loads(json_text, strict=False)
            except: pass
        else:
            idx = text.find("{")
            last = text.rfind("}")
            if idx >= 0 and last > idx:
                try: data = json.loads(text[idx:last+1], strict=False)
                except: pass

        # 4. Clean spoken text
        clean_reply = text
        if json_text: clean_reply = text.replace(f"```json\n{json_text}\n```", "").replace(f"```json\n{json_text}```", "").replace(f"```{json_text}```", "").strip()
        elif data: clean_reply = text[:text.find("{")].strip()
        
        # 5. Handle Action
        if not data or not data.get("action"):
            return jsonify({"ok": True, "type": "reply", "msg": clean_reply or "Entendido."})
            
        act = data.get("action")
        exec_info = ""
        success = True

        try:
            if act == "create_channel":
                r = discord_post(f"/guilds/{GUILD_ID}/channels", {"name": data.get("name"), "type": data.get("type", 0)})
                if "id" in r: exec_info = f"✅ Canal '{data.get('name')}' creado."
                else: success = False; exec_info = f"❌ Error API: {r.get('message','?')}"
            elif act in ("delete_channel", "modify_channel"):
                target = data.get("name", "").lower()
                cid = next((c["id"] for c in ch_list if target in c.get("name","").lower()), None)
                if not cid: success=False; exec_info = f"❌ No encuentro el canal '{target}'."
                else:
                    if act == "delete_channel":
                        discord_delete(f"/channels/{cid}")
                        exec_info = f"🗑️ Canal '{target}' purgado."
                    else:
                        p = {}
                        if "new_name" in data: p["name"] = data["new_name"]
                        if "topic" in data: p["topic"] = data["topic"]
                        discord_patch(f"/channels/{cid}", p)
                        exec_info = f"⚙️ Canal '{target}' modificado."
            elif act == "create_role":
                r = discord_post(f"/guilds/{GUILD_ID}/roles", {"name": data.get("name")})
                if "id" in r: exec_info = f"✅ Rol '{data.get('name')}' creado."
                else: success=False; exec_info = f"❌ Error API: {r.get('message','?')}"
            elif act == "send_message":
                target_id = data.get("channel_id")
                if not target_id: # fallback to first text channel
                    target_id = next((c["id"] for c in ch_list if c.get("type") == 0), None)
                if target_id:
                    discord_post(f"/channels/{target_id}/messages", {"content": data.get("content")})
                    exec_info = "📨 Mensaje inyectado."
                else: success=False; exec_info = "❌ Sin canal de salida."
            elif act == "create_poll":
                cid = next((c["id"] for c in ch_list if c.get("type") == 0), None)
                if cid:
                    p = {"poll": {"question": {"text": data.get("question", "Votación")}, "answers": [{"poll_media": {"text": o}} for o in data.get("options",["Sí","No"])], "duration": 24, "layout_type": 1}}
                    discord_post(f"/channels/{cid}/messages", p)
                    exec_info = "📊 Encuesta desplegada."
                else: success=False; exec_info = "❌ Sin canal para encuesta."
            elif act == "update_config":
                c = load_config(); c[data.get("key")] = data.get("value")
                save_config(c); exec_info = f"⚙️ Parámetro '{data.get('key')}' actualizado."
            elif act == "manage_role":
                uid = "".join(filter(str.isdigit, str(data.get("user",""))))
                rid = "".join(filter(str.isdigit, str(data.get("role",""))))
                if not rid:
                    rname = str(data.get("role","")).lower()
                    rid = next((r["id"] for r in rol_list if rname in r["name"].lower()), None)
                if uid and rid:
                    if data.get("type") == "add": discord_put(f"/guilds/{GUILD_ID}/members/{uid}/roles/{rid}", {})
                    else: discord_delete(f"/guilds/{GUILD_ID}/members/{uid}/roles/{rid}")
                    exec_info = f"🛡️ Jerarquía de roles aplicada a {uid}."
                else: success=False; exec_info = "❌ Usuario/Rol no detectado."
            elif act == "purge_messages":
                target = data.get("channel", "").lower()
                cid = next((c["id"] for c in ch_list if target in c.get("name","").lower()), None)
                if cid:
                    msgs = discord_get(f"/channels/{cid}/messages?limit={data.get('count',20)}")
                    if isinstance(msgs, list) and len(msgs)>0:
                        mids = [m["id"] for m in msgs]
                        if len(mids) == 1: discord_delete(f"/channels/{cid}/messages/{mids[0]}")
                        else: discord_post(f"/channels/{cid}/messages/bulk-delete", {"messages": mids})
                        exec_info = f"🧹 {len(mids)} mensajes purgados de #{target}."
                    else: exec_info = "🧹 Canal ya optimizado."
                else: success=False; exec_info = "❌ Canal no localizado."
            elif act in ("ban_user", "kick_user", "timeout_user"):
                uid = "".join(filter(str.isdigit, str(data.get("user",""))))
                if not uid: success=False; exec_info = "❌ ID de usuario inválido."
                else:
                    reason = data.get("reason", "Protocolo OMEGA.")
                    headers = {**HEADERS(), "X-Audit-Log-Reason": reason}
                    if act == "ban_user": req_lib.put(f"{DISCORD}/guilds/{GUILD_ID}/bans/{uid}", headers=headers, json={})
                    elif act == "kick_user": req_lib.delete(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}", headers=headers)
                    elif act == "timeout_user":
                        from datetime import datetime, timedelta, timezone
                        until = (datetime.now(timezone.utc) + timedelta(minutes=data.get("duration",10))).isoformat()
                        req_lib.patch(f"{DISCORD}/guilds/{GUILD_ID}/members/{uid}", headers=headers, json={"communication_disabled_until": until})
                    exec_info = f"💥 Protocolo {act} ejecutado sobre {uid}."
        except Exception as e:
            success = False
            exec_info = f"⚠️ Fallo: {str(e)}"

        combined = clean_reply
        if exec_info:
            combined = f"{clean_reply}\n\n*__{exec_info}__*" if clean_reply else exec_info
            
        return jsonify({"ok": success, "type": "success", "msg": combined})

    except Exception as e:
        return jsonify({"ok": False, "error": f"OMEGA-CORE Critical Error: {str(e)}"})

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
