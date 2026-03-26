from flask import Flask, render_template_string, request, jsonify, redirect, session
import json, os, requests as req_lib

# ══════════════════════════════════════════════════════════════
#  FLASK BACKEND
# ══════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder='static')
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
        if not session.get("logged_in"): return redirect("/login")
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

@app.route("/api/logs",methods=["POST"])
@auth_required
def api_logs(): return cfg_patch("logs",request.json)

@app.route("/api/tickets",methods=["POST"])
@auth_required
def api_tickets(): return cfg_patch("tickets",request.json)

@app.route("/api/config",methods=["GET"])
@auth_required
def api_config(): return jsonify(load_config())

if __name__ == "__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
