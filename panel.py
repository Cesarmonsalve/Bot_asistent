from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json, os, requests as req_lib

app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET", "thefamily2024secret")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GUILD_ID  = os.environ.get("GUILD_ID", "1486498876503494707")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "cesar2024")

def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)

def get_guild_channels():
    r = req_lib.get(
        f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels",
        headers={"Authorization": f"Bot {BOT_TOKEN}"}
    )
    return [c for c in r.json() if isinstance(c, dict) and c.get("type") == 0]

def get_guild_roles():
    r = req_lib.get(
        f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles",
        headers={"Authorization": f"Bot {BOT_TOKEN}"}
    )
    return [ro for ro in r.json() if isinstance(ro, dict) and ro.get("name") != "@everyone"]

# ─── AUTH ───────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PANEL_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return render_template("login.html", error="Contraseña incorrecta")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# ─── PANEL PRINCIPAL ────────────────────────────────────────
@app.route("/")
@auth_required
def index():
    cfg = load_config()
    channels = get_guild_channels()
    roles = get_guild_roles()
    return render_template("index.html", cfg=cfg, channels=channels, roles=roles)

# ─── API ENDPOINTS ──────────────────────────────────────────
@app.route("/api/welcome", methods=["POST"])
@auth_required
def api_welcome():
    cfg = load_config()
    data = request.json
    cfg["welcome"] = {
        "enabled": data.get("enabled", False),
        "channel_id": data.get("channel_id"),
        "message": data.get("message", "👋 Bienvenido/a {user} a **{server}**!"),
        "banner_url": data.get("banner_url", ""),
        "auto_role_id": data.get("auto_role_id"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/goodbye", methods=["POST"])
@auth_required
def api_goodbye():
    cfg = load_config()
    data = request.json
    cfg["goodbye"] = {
        "enabled": data.get("enabled", False),
        "channel_id": data.get("channel_id"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/xp", methods=["POST"])
@auth_required
def api_xp():
    cfg = load_config()
    data = request.json
    cfg["xp"] = {
        "enabled": data.get("enabled", False),
        "levelup_channel_id": data.get("levelup_channel_id"),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/moderation", methods=["POST"])
@auth_required
def api_moderation():
    cfg = load_config()
    data = request.json
    cfg["moderation"] = {
        "anti_links": data.get("anti_links", False),
    }
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/reaction_roles", methods=["GET"])
@auth_required
def api_rr_get():
    cfg = load_config()
    return jsonify(cfg.get("reaction_roles", []))

@app.route("/api/reaction_roles", methods=["POST"])
@auth_required
def api_rr_add():
    cfg = load_config()
    data = request.json
    rr = cfg.get("reaction_roles", [])
    rr.append({
        "message_id": data["message_id"],
        "emoji": data["emoji"],
        "role_id": data["role_id"],
    })
    cfg["reaction_roles"] = rr
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/reaction_roles/<int:index>", methods=["DELETE"])
@auth_required
def api_rr_delete(index):
    cfg = load_config()
    rr = cfg.get("reaction_roles", [])
    if 0 <= index < len(rr):
        rr.pop(index)
    cfg["reaction_roles"] = rr
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/stream_alert", methods=["POST"])
@auth_required
def api_stream():
    cfg = load_config()
    data = request.json
    cfg["stream_alert"] = {
        "enabled": data.get("enabled", False),
        "channel_id": data.get("channel_id"),
        "kick_username": data.get("kick_username", ""),
        "tiktok_username": data.get("tiktok_username", ""),
        "message": data.get("message", "🔴 {username} está en vivo! {url}"),
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
