import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, asyncio, aiohttp, re, random
from datetime import datetime, timedelta, timezone

TOKEN    = (os.environ.get("BOT_TOKEN") or "").strip()
GUILD_ID = int((os.environ.get("GUILD_ID") or "0").strip())

# ── CONFIG ────────────────────────────────────────────────────
def load_config():
    try:
        with open("config.json") as f: return json.load(f)
    except Exception: return {}

def save_config(data):
    with open("config.json", "w") as f: json.dump(data, f, indent=2)

# ── INTENTS ───────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# ── READY ─────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ {bot.user} online | Guild: {GUILD_ID}", flush=True)
    try:
        synced = await tree.sync()
        print(f"🔄 Sincronizados {len(synced)} comandos slash", flush=True)
    except Exception as e:
        print(f"❌ Sync error: {e}", flush=True)
    check_streams.start()

# ═══════════════════════════════════════════════════════════════
#  EVENTS
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_member_join(member):
    cfg = load_config()
    # Auto-role
    w = cfg.get("welcome", {})
    if w.get("auto_role_id"):
        try:
            role = member.guild.get_role(int(w["auto_role_id"]))
            if role: await member.add_roles(role)
        except Exception: pass
    # Welcome message
    if w.get("enabled") and w.get("channel_id"):
        try:
            ch = member.guild.get_channel(int(w["channel_id"]))
            if ch:
                msg = (w.get("message") or "👋 Bienvenido/a {user}!").replace("{user}", member.mention).replace("{username}", str(member.name)).replace("{server}", member.guild.name).replace("{count}", str(member.guild.member_count))
                embed = discord.Embed(description=msg, color=0x6366f1)
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                if w.get("banner_url"): embed.set_image(url=w["banner_url"])
                await ch.send(embed=embed)
        except Exception as e:
            print(f"Welcome error: {e}", flush=True)
    await send_log(member.guild, "member_join", f"📥 **{member}** se unió al servidor.")

@bot.event
async def on_member_remove(member):
    cfg = load_config()
    g = cfg.get("goodbye", {})
    if g.get("enabled") and g.get("channel_id"):
        try:
            ch = member.guild.get_channel(int(g["channel_id"]))
            if ch:
                msg = (g.get("message") or "👋 {username} salió.").replace("{username}", str(member.name)).replace("{server}", member.guild.name)
                await ch.send(embed=discord.Embed(description=msg, color=0xef4444))
        except Exception: pass
    await send_log(member.guild, "member_leave", f"📤 **{member}** salió del servidor.")

@bot.event
async def on_message(message):
    if message.author.bot: return
    cfg = load_config()

    # Word filter
    wf = cfg.get("word_filter", {})
    if wf.get("enabled"):
        banned = [w.lower() for w in wf.get("words", []) if w]
        if any(b in message.content.lower() for b in banned):
            try:
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention} tu mensaje fue eliminado.", delete_after=5)
            except Exception: pass
            return

    # Anti-links
    mod = cfg.get("moderation", {})
    if mod.get("anti_links") and re.search(r'https?://|discord\.gg/|www\.', message.content, re.IGNORECASE):
        if not (message.author.guild_permissions.manage_messages or message.author.guild_permissions.administrator):
            try:
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention} no se permiten links.", delete_after=5)
            except Exception: pass
            return

    # XP
    xp_cfg = cfg.get("xp", {})
    if xp_cfg.get("enabled"):
        xp_data = cfg.get("xp_data", {})
        uid = str(message.author.id)
        now = datetime.now().timestamp()
        ud = xp_data.get(uid, {"xp": 0, "level": 0, "last_msg": 0})
        if now - ud.get("last_msg", 0) > 60:
            ud["xp"] = ud.get("xp", 0) + 15
            ud["last_msg"] = now
            old_lv = ud.get("level", 0)
            ud["level"] = int((ud["xp"] / 100) ** 0.5)
            xp_data[uid] = ud
            cfg["xp_data"] = xp_data
            save_config(cfg)
            if ud["level"] > old_lv:
                try:
                    lv_ch = xp_cfg.get("levelup_channel_id")
                    ch = message.guild.get_channel(int(lv_ch)) if lv_ch else message.channel
                    if ch:
                        await ch.send(embed=discord.Embed(description=f"🎉 {message.author.mention} subió al **nivel {ud['level']}**!", color=0xf59e0b))
                except Exception: pass

    # Custom commands
    custom = cfg.get("custom_commands", {})
    if message.content.startswith("!"):
        cmd = message.content[1:].split()[0].lower()
        if cmd in custom:
            try: await message.channel.send(custom[cmd])
            except Exception: pass

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    await send_log(message.guild, "message_delete", f"🗑️ Mensaje de **{message.author}** en {message.channel.mention}:\n> {message.content[:300]}")

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added   = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added:   await send_log(before.guild, "role_update", f"🏷️ **{after}** recibió {added[0].mention}")
        if removed: await send_log(before.guild, "role_update", f"🏷️ **{after}** perdió {removed[0].mention}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    cfg = load_config()
    for rr in cfg.get("reaction_roles", []):
        if str(payload.message_id) == str(rr["message_id"]) and str(payload.emoji) == str(rr["emoji"]):
            guild = bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                role = guild.get_role(int(rr["role_id"]))
                if member and role:
                    try: await member.add_roles(role)
                    except Exception: pass

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id: return
    cfg = load_config()
    for rr in cfg.get("reaction_roles", []):
        if str(payload.message_id) == str(rr["message_id"]) and str(payload.emoji) == str(rr["emoji"]):
            guild = bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                role = guild.get_role(int(rr["role_id"]))
                if member and role:
                    try: await member.remove_roles(role)
                    except Exception: pass

# ── LOG HELPER ────────────────────────────────────────────────
async def send_log(guild, event_type, content):
    cfg = load_config()
    log_cfg = cfg.get("logs", {})
    if not log_cfg.get("enabled"): return
    ch_id = log_cfg.get("channel_id")
    if not ch_id: return
    if event_type not in log_cfg.get("events", []): return
    try:
        ch = guild.get_channel(int(ch_id))
        if ch:
            embed = discord.Embed(description=content, color=0x6366f1, timestamp=datetime.now(timezone.utc))
            await ch.send(embed=embed)
    except Exception: pass

# ═══════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════

@tree.command(name="ping", description="Ver latencia del bot")
async def ping(interaction: discord.Interaction):
    ms = round(bot.latency * 1000)
    await interaction.response.send_message(embed=discord.Embed(description=f"🏓 Pong! `{ms}ms`", color=0x22c55e))

@tree.command(name="rank", description="Ver tu nivel y XP")
async def rank(interaction: discord.Interaction, usuario: discord.Member = None):
    target = usuario or interaction.user
    cfg = load_config()
    if not cfg.get("xp", {}).get("enabled"):
        await interaction.response.send_message("❌ El sistema XP está desactivado.", ephemeral=True); return
    ud = cfg.get("xp_data", {}).get(str(target.id), {"xp": 0, "level": 0})
    xp = ud.get("xp", 0); lv = ud.get("level", 0)
    next_xp = ((lv + 1) ** 2) * 100
    embed = discord.Embed(title=f"⭐ Rango de {target.display_name}", color=0xf59e0b)
    embed.add_field(name="Nivel", value=str(lv), inline=True)
    embed.add_field(name="XP", value=str(xp), inline=True)
    embed.add_field(name="Para nivel siguiente", value=str(max(0, next_xp - xp)), inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="Top 10 del servidor")
async def leaderboard(interaction: discord.Interaction):
    cfg = load_config()
    xp_data = cfg.get("xp_data", {})
    top = sorted(xp_data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 Leaderboard XP", color=0xf59e0b)
    medals = ["🥇","🥈","🥉"]
    lines = []
    for i, (uid, data) in enumerate(top):
        try: member = interaction.guild.get_member(int(uid)); name = member.display_name if member else f"Usuario {uid[:6]}"
        except: name = f"Usuario {uid[:6]}"
        lines.append(f"{medals[i] if i<3 else f'`{i+1}.`'} **{name}** — Nv {data.get('level',0)} · {data.get('xp',0)} XP")
    embed.description = "\n".join(lines) if lines else "No hay datos aún."
    await interaction.response.send_message(embed=embed)

@tree.command(name="say", description="Hacer hablar al bot [Admin]")
@app_commands.checks.has_permissions(manage_messages=True)
async def say(interaction: discord.Interaction, mensaje: str, canal: discord.TextChannel = None):
    ch = canal or interaction.channel
    await ch.send(mensaje)
    await interaction.response.send_message("✅ Enviado", ephemeral=True)

@tree.command(name="embed", description="Enviar embed [Admin]")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction, titulo: str, descripcion: str, canal: discord.TextChannel = None, color: str = "6366f1"):
    ch = canal or interaction.channel
    try: col = int(color.strip("#"), 16)
    except: col = 0x6366f1
    await ch.send(embed=discord.Embed(title=titulo, description=descripcion, color=col))
    await interaction.response.send_message("✅ Embed enviado", ephemeral=True)

@tree.command(name="warn", description="Advertir usuario [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    cfg = load_config(); warns = cfg.get("warns", {}); uid = str(usuario.id)
    warns[uid] = warns.get(uid, [])
    warns[uid].append({"razon": razon, "fecha": str(datetime.now()), "by": str(interaction.user)})
    cfg["warns"] = warns; save_config(cfg)
    embed = discord.Embed(description=f"⚠️ **{usuario}** advertido.\nRazón: {razon}\nTotal warns: {len(warns[uid])}", color=0xf59e0b)
    await interaction.response.send_message(embed=embed)
    await send_log(interaction.guild, "moderation", f"⚠️ **{usuario}** advertido por **{interaction.user}** · {razon}")

@tree.command(name="warns", description="Ver advertencias [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def show_warns(interaction: discord.Interaction, usuario: discord.Member):
    warns = load_config().get("warns", {}).get(str(usuario.id), [])
    if not warns:
        await interaction.response.send_message(f"✅ {usuario.mention} no tiene advertencias.", ephemeral=True); return
    embed = discord.Embed(title=f"⚠️ Warns de {usuario}", color=0xf59e0b)
    for i, w in enumerate(warns, 1):
        embed.add_field(name=f"Warn #{i}", value=f"Razón: {w['razon']}\nPor: {w['by']}", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="clear", description="Borrar mensajes [Staff]")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, cantidad: int):
    if not 1 <= cantidad <= 100:
        await interaction.response.send_message("❌ Entre 1 y 100.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=cantidad)
    await interaction.followup.send(f"🗑️ {len(deleted)} mensajes eliminados.", ephemeral=True)

@tree.command(name="kick", description="Expulsar usuario [Staff]")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    await usuario.kick(reason=razon)
    await interaction.response.send_message(embed=discord.Embed(description=f"👢 **{usuario}** expulsado. Razón: {razon}", color=0xef4444))
    await send_log(interaction.guild, "moderation", f"👢 **{usuario}** expulsado por **{interaction.user}** · {razon}")

@tree.command(name="ban", description="Banear usuario [Admin]")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    await usuario.ban(reason=razon)
    await interaction.response.send_message(embed=discord.Embed(description=f"🔨 **{usuario}** baneado. Razón: {razon}", color=0xef4444))
    await send_log(interaction.guild, "moderation", f"🔨 **{usuario}** baneado por **{interaction.user}** · {razon}")

@tree.command(name="timeout", description="Silenciar usuario [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_cmd(interaction: discord.Interaction, usuario: discord.Member, minutos: int = 10, razon: str = "Sin razón"):
    until = discord.utils.utcnow() + timedelta(minutes=minutos)
    await usuario.timeout(until, reason=razon)
    await interaction.response.send_message(embed=discord.Embed(description=f"🔇 **{usuario}** silenciado {minutos}min. Razón: {razon}", color=0xf59e0b))
    await send_log(interaction.guild, "moderation", f"🔇 **{usuario}** silenciado {minutos}min por **{interaction.user}** · {razon}")

@tree.command(name="poll", description="Crear encuesta [Staff]")
@app_commands.checks.has_permissions(manage_messages=True)
async def poll(interaction: discord.Interaction, pregunta: str, opcion1: str, opcion2: str, opcion3: str = None, opcion4: str = None):
    opciones = [opcion1, opcion2]
    if opcion3: opciones.append(opcion3)
    if opcion4: opciones.append(opcion4)
    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣"]
    desc = "\n".join([f"{emojis[i]} {op}" for i, op in enumerate(opciones)])
    embed = discord.Embed(title=f"📊 {pregunta}", description=desc, color=0x6366f1)
    embed.set_footer(text=f"Encuesta creada por {interaction.user.display_name}")
    await interaction.response.defer()
    msg = await interaction.channel.send(embed=embed)
    for i in range(len(opciones)):
        await msg.add_reaction(emojis[i])
    await interaction.followup.send("✅ Encuesta creada", ephemeral=True)

@tree.command(name="sorteo", description="Iniciar sorteo [Admin]")
@app_commands.checks.has_permissions(manage_guild=True)
async def sorteo(interaction: discord.Interaction, duracion_min: int, premio: str, canal: discord.TextChannel = None):
    ch = canal or interaction.channel
    end_ts = int((datetime.now(timezone.utc) + timedelta(minutes=duracion_min)).timestamp())
    embed = discord.Embed(title="🎉 ¡SORTEO!", description=f"**Premio:** {premio}\n\nReaccioná con 🎉!\n⏰ Termina: <t:{end_ts}:R>", color=0xf59e0b)
    msg = await ch.send(embed=embed)
    await msg.add_reaction("🎉")
    await interaction.response.send_message(f"✅ Sorteo iniciado en {ch.mention}", ephemeral=True)
    await asyncio.sleep(duracion_min * 60)
    msg = await ch.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if reaction:
        users = [u async for u in reaction.users() if not u.bot]
        if users:
            winner = random.choice(users)
            await ch.send(embed=discord.Embed(description=f"🎊 ¡{winner.mention} ganó **{premio}**! Felicidades!", color=0x22c55e))
        else:
            await ch.send("😢 Nadie participó.")

@tree.command(name="serverinfo", description="Ver información del servidor")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, color=0x6366f1)
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="👥 Miembros", value=str(g.member_count), inline=True)
    embed.add_field(name="📢 Canales", value=str(len(g.channels)), inline=True)
    embed.add_field(name="🏷️ Roles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="Owner", value=str(g.owner), inline=True)
    embed.add_field(name="Creado", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="Nivel boost", value=str(g.premium_tier), inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="userinfo", description="Ver información de un usuario")
async def userinfo(interaction: discord.Interaction, usuario: discord.Member = None):
    target = usuario or interaction.user
    embed = discord.Embed(title=str(target), color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="ID", value=str(target.id), inline=True)
    embed.add_field(name="Unido", value=f"<t:{int(target.joined_at.timestamp())}:D>", inline=True)
    embed.add_field(name="Cuenta creada", value=f"<t:{int(target.created_at.timestamp())}:D>", inline=True)
    roles_str = " ".join(r.mention for r in target.roles[1:]) or "Ninguno"
    embed.add_field(name="Roles", value=roles_str[:1024], inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="panel", description="Link al panel de administración [Admin]")
@app_commands.checks.has_permissions(manage_guild=True)
async def panel_cmd(interaction: discord.Interaction):
    url = os.environ.get("PANEL_URL", "https://tu-panel.railway.app")
    embed = discord.Embed(title="🎛️ Panel de Administración", description=f"[🔗 Abrir Panel]({url})", color=0x6366f1)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ── TICKETS (BUTTON-BASED) ───────────────────────────────────
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket 🎫", style=discord.ButtonStyle.primary, custom_id="ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = load_config()
        tk = cfg.get("tickets", {})
        if not tk.get("enabled"):
            await interaction.response.send_message("❌ Los tickets están desactivados.", ephemeral=True); return
        guild = interaction.guild
        cat_id = tk.get("category_id")
        cat = guild.get_channel(int(cat_id)) if cat_id else None
        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.name.lower()[:20]}")
        if existing:
            await interaction.response.send_message(f"❌ Ya tienes un ticket abierto: {existing.mention}", ephemeral=True); return
        support_role_id = tk.get("support_role_id")
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        if support_role: overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        ch = await guild.create_text_channel(f"ticket-{interaction.user.name.lower()[:20]}", overwrites=overwrites, category=cat)
        embed = discord.Embed(title="🎫 Ticket Abierto", description=f"Hola {interaction.user.mention}! Un miembro del staff atenderá tu consulta pronto.\n\nUsa el botón de abajo para cerrar el ticket.", color=0x6366f1)
        await ch.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket creado: {ch.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket 🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando ticket en 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

@tree.command(name="ticket-setup", description="Configurar panel de tickets [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction, canal: discord.TextChannel):
    cfg = load_config()
    tk = cfg.get("tickets", {})
    msg_txt = tk.get("message", "🎫 Haz click para abrir un ticket de soporte.")
    embed = discord.Embed(title="🎫 Sistema de Tickets", description=msg_txt, color=0x6366f1)
    await canal.send(embed=embed, view=TicketButton())
    await interaction.response.send_message(f"✅ Panel de tickets enviado a {canal.mention}", ephemeral=True)

# ── STREAM CHECK ─────────────────────────────────────────────
_stream_state = {}

@tasks.loop(minutes=5)
async def check_streams():
    cfg = load_config()
    st = cfg.get("stream_alert", {})
    if not st.get("enabled") or not st.get("channel_id"): return
    guild = bot.get_guild(GUILD_ID)
    if not guild: return
    ch = guild.get_channel(int(st["channel_id"]))
    if not ch: return

    async def check_kick(username):
        if not username: return None
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://kick.com/api/v1/channels/{username}", timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        data = await r.json()
                        ls = data.get("livestream")
                        if ls: return {"title": ls.get("session_title",""), "url": f"https://kick.com/{username}"}
        except Exception: pass
        return None

    kick_user = st.get("kick_username", "")
    live = await check_kick(kick_user)
    key = f"kick_{kick_user}"
    if live and not _stream_state.get(key):
        _stream_state[key] = True
        msg = st.get("message","🔴 {username} está en vivo! {url}").replace("{username}",kick_user).replace("{url}",live["url"]).replace("{title}",live["title"])
        await ch.send(embed=discord.Embed(description=msg, color=0xef4444))
    elif not live:
        _stream_state[key] = False

@bot.event
async def setup_hook():
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())

# ── ERROR HANDLER ─────────────────────────────────────────────
@tree.error
async def on_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# ── RUN ───────────────────────────────────────────────────────
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ BOT_TOKEN no encontrado. Configúralo en las variables de entorno.", flush=True)
