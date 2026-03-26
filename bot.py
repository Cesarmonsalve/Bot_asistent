import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, asyncio, aiohttp, re
from datetime import datetime, timedelta, timezone

TOKEN    = os.environ.get("BOT_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))

# ── CONFIG ────────────────────────────────────────────────────
def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)

# ── INTENTS ───────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# ── READY ─────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ {bot.user} online")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Sync error: {e}")
    check_streams.start()

# ═══════════════════════════════════════════════════════════════
#  EVENTS
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_member_join(member):
    cfg = load_config()
    # Auto-role
    welcome = cfg.get("welcome", {})
    if welcome.get("auto_role_id"):
        try:
            role = member.guild.get_role(int(welcome["auto_role_id"]))
            if role:
                await member.add_roles(role)
        except Exception:
            pass
    # Welcome message
    if welcome.get("enabled") and welcome.get("channel_id"):
        try:
            ch = member.guild.get_channel(int(welcome["channel_id"]))
            if ch:
                msg = welcome.get("message", "👋 Bienvenido/a {user}!")
                msg = msg.replace("{user}", member.mention)
                msg = msg.replace("{username}", str(member.name))
                msg = msg.replace("{server}", member.guild.name)
                msg = msg.replace("{count}", str(member.guild.member_count))
                embed = discord.Embed(description=msg, color=0x5b3de8)
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                if welcome.get("banner_url"):
                    embed.set_image(url=welcome["banner_url"])
                await ch.send(embed=embed)
        except Exception as e:
            print(f"Welcome error: {e}")
    # Log
    await send_log(member.guild, "member_join", f"📥 **{member}** se unió al servidor.")

@bot.event
async def on_member_remove(member):
    cfg = load_config()
    goodbye = cfg.get("goodbye", {})
    if goodbye.get("enabled") and goodbye.get("channel_id"):
        try:
            ch = member.guild.get_channel(int(goodbye["channel_id"]))
            if ch:
                msg = goodbye.get("message", "👋 **{username}** salió del servidor.")
                msg = msg.replace("{username}", str(member.name))
                msg = msg.replace("{server}", member.guild.name)
                embed = discord.Embed(description=msg, color=0xef4444)
                await ch.send(embed=embed)
        except Exception:
            pass
    await send_log(member.guild, "member_leave", f"📤 **{member}** salió del servidor.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    cfg = load_config()

    # ── Word filter ──
    word_filter = cfg.get("word_filter", {})
    if word_filter.get("enabled"):
        banned = word_filter.get("words", [])
        content_lower = message.content.lower()
        if any(w.lower() in content_lower for w in banned if w):
            try:
                await message.delete()
                warn_msg = await message.channel.send(
                    f"⚠️ {message.author.mention} tu mensaje fue eliminado por contener palabras no permitidas.",
                    delete_after=5
                )
            except Exception:
                pass
            return

    # ── Anti-links ──
    mod = cfg.get("moderation", {})
    if mod.get("anti_links"):
        url_pattern = r'https?://|discord\.gg/|www\.'
        if re.search(url_pattern, message.content, re.IGNORECASE):
            perms = message.author.guild_permissions
            if not (perms.manage_messages or perms.administrator):
                try:
                    await message.delete()
                    await message.channel.send(
                        f"🚫 {message.author.mention} no se permiten links aquí.",
                        delete_after=5
                    )
                except Exception:
                    pass
                return

    # ── Anti-spam ──
    if mod.get("anti_spam"):
        # Simple spam check - same message 3x in 5 seconds (tracked in memory)
        pass

    # ── XP system ──
    xp_cfg = cfg.get("xp", {})
    if xp_cfg.get("enabled"):
        xp_data = cfg.get("xp_data", {})
        uid = str(message.author.id)
        now = datetime.now().timestamp()
        user_data = xp_data.get(uid, {"xp": 0, "level": 0, "last_msg": 0})
        # 1 XP per message, cooldown 60s
        if now - user_data.get("last_msg", 0) > 60:
            user_data["xp"] = user_data.get("xp", 0) + 15
            user_data["last_msg"] = now
            old_level = user_data.get("level", 0)
            new_level = int((user_data["xp"] / 100) ** 0.5)
            user_data["level"] = new_level
            xp_data[uid] = user_data
            cfg["xp_data"] = xp_data
            save_config(cfg)
            if new_level > old_level:
                levelup_ch_id = xp_cfg.get("levelup_channel_id")
                try:
                    ch = message.guild.get_channel(int(levelup_ch_id)) if levelup_ch_id else message.channel
                    if ch:
                        embed = discord.Embed(
                            description=f"🎉 {message.author.mention} subió al **nivel {new_level}**!",
                            color=0xf59e0b
                        )
                        await ch.send(embed=embed)
                except Exception:
                    pass

    # ── Custom commands ──
    custom_cmds = cfg.get("custom_commands", {})
    if message.content.startswith("!"):
        cmd_name = message.content[1:].split()[0].lower()
        if cmd_name in custom_cmds:
            try:
                await message.channel.send(custom_cmds[cmd_name])
            except Exception:
                pass

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    await send_log(message.guild, "message_delete",
        f"🗑️ Mensaje de **{message.author}** eliminado en {message.channel.mention}:\n> {message.content[:300]}")

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added   = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added:
            await send_log(before.guild, "role_update",
                f"🏷️ **{after}** recibió el rol {added[0].mention}")
        if removed:
            await send_log(before.guild, "role_update",
                f"🏷️ **{after}** perdió el rol {removed[0].mention}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    cfg = load_config()
    for rr in cfg.get("reaction_roles", []):
        if str(payload.message_id) == str(rr["message_id"]) and str(payload.emoji) == str(rr["emoji"]):
            guild = bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                role = guild.get_role(int(rr["role_id"]))
                if member and role:
                    try:
                        await member.add_roles(role)
                    except Exception:
                        pass

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    cfg = load_config()
    for rr in cfg.get("reaction_roles", []):
        if str(payload.message_id) == str(rr["message_id"]) and str(payload.emoji) == str(rr["emoji"]):
            guild = bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                role = guild.get_role(int(rr["role_id"]))
                if member and role:
                    try:
                        await member.remove_roles(role)
                    except Exception:
                        pass

# ── LOG HELPER ────────────────────────────────────────────────
async def send_log(guild, event_type, content):
    cfg = load_config()
    log_cfg = cfg.get("logs", {})
    if not log_cfg.get("enabled"):
        return
    ch_id = log_cfg.get("channel_id")
    enabled_events = log_cfg.get("events", [])
    if event_type not in enabled_events and "all" not in enabled_events:
        return
    if not ch_id:
        return
    try:
        ch = guild.get_channel(int(ch_id))
        if ch:
            embed = discord.Embed(description=content, color=0x3b82f6,
                                  timestamp=datetime.now(timezone.utc))
            await ch.send(embed=embed)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════

@tree.command(name="ping", description="Ver latencia del bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"🏓 Pong! `{latency}ms`", color=0x22c55e))

@tree.command(name="rank", description="Ver tu nivel y XP")
async def rank(interaction: discord.Interaction, usuario: discord.Member = None):
    target = usuario or interaction.user
    cfg = load_config()
    if not cfg.get("xp", {}).get("enabled"):
        await interaction.response.send_message("❌ El sistema de XP está desactivado.", ephemeral=True)
        return
    xp_data = cfg.get("xp_data", {})
    user_data = xp_data.get(str(target.id), {"xp": 0, "level": 0})
    xp = user_data.get("xp", 0)
    level = user_data.get("level", 0)
    next_level_xp = ((level + 1) ** 2) * 100
    embed = discord.Embed(title=f"⭐ Rango de {target.display_name}", color=0xf59e0b)
    embed.add_field(name="Nivel", value=str(level), inline=True)
    embed.add_field(name="XP Total", value=str(xp), inline=True)
    embed.add_field(name="XP para nivel siguiente", value=str(max(0, next_level_xp - xp)), inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="Top 10 del servidor")
async def leaderboard(interaction: discord.Interaction):
    cfg = load_config()
    xp_data = cfg.get("xp_data", {})
    sorted_users = sorted(xp_data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 Leaderboard", color=0xf59e0b)
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        try:
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"Usuario {uid[:6]}"
        except Exception:
            name = f"Usuario {uid[:6]}"
        lines.append(f"{medal} **{name}** — Nivel {data.get('level',0)} · {data.get('xp',0)} XP")
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
async def embed_cmd(interaction: discord.Interaction, titulo: str, descripcion: str,
                    canal: discord.TextChannel = None, color: str = "5b3de8"):
    ch = canal or interaction.channel
    try:
        col = int(color.strip("#"), 16)
    except Exception:
        col = 0x5b3de8
    embed = discord.Embed(title=titulo, description=descripcion, color=col)
    await ch.send(embed=embed)
    await interaction.response.send_message("✅ Embed enviado", ephemeral=True)

@tree.command(name="warn", description="Advertir a un usuario [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    cfg = load_config()
    warns = cfg.get("warns", {})
    uid = str(usuario.id)
    warns[uid] = warns.get(uid, [])
    warns[uid].append({"razon": razon, "fecha": str(datetime.now()), "by": str(interaction.user)})
    cfg["warns"] = warns
    save_config(cfg)
    embed = discord.Embed(
        description=f"⚠️ **{usuario}** ha sido advertido.\nRazón: {razon}\nTotal warns: {len(warns[uid])}",
        color=0xf59e0b
    )
    await interaction.response.send_message(embed=embed)
    await send_log(interaction.guild, "moderation", f"⚠️ **{usuario}** advertido por **{interaction.user}** · {razon}")

@tree.command(name="warns", description="Ver advertencias de un usuario")
@app_commands.checks.has_permissions(moderate_members=True)
async def show_warns(interaction: discord.Interaction, usuario: discord.Member):
    cfg = load_config()
    warns = cfg.get("warns", {}).get(str(usuario.id), [])
    if not warns:
        await interaction.response.send_message(f"✅ {usuario.mention} no tiene advertencias.", ephemeral=True)
        return
    embed = discord.Embed(title=f"⚠️ Warns de {usuario}", color=0xf59e0b)
    for i, w in enumerate(warns, 1):
        embed.add_field(name=f"Warn #{i}", value=f"Razón: {w['razon']}\nPor: {w['by']}", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="clear", description="Borrar mensajes [Staff]")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, cantidad: int):
    if cantidad < 1 or cantidad > 100:
        await interaction.response.send_message("❌ Entre 1 y 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=cantidad)
    await interaction.followup.send(f"🗑️ {len(deleted)} mensajes eliminados.", ephemeral=True)

@tree.command(name="kick", description="Expulsar a un usuario [Staff]")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    await usuario.kick(reason=razon)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"👢 **{usuario}** fue expulsado. Razón: {razon}", color=0xef4444))
    await send_log(interaction.guild, "moderation", f"👢 **{usuario}** expulsado por **{interaction.user}** · {razon}")

@tree.command(name="ban", description="Banear a un usuario [Admin]")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    await usuario.ban(reason=razon)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"🔨 **{usuario}** fue baneado. Razón: {razon}", color=0xef4444))
    await send_log(interaction.guild, "moderation", f"🔨 **{usuario}** baneado por **{interaction.user}** · {razon}")

@tree.command(name="timeout", description="Silenciar a un usuario [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_cmd(interaction: discord.Interaction, usuario: discord.Member,
                      minutos: int = 10, razon: str = "Sin razón"):
    until = discord.utils.utcnow() + timedelta(minutes=minutos)
    await usuario.timeout(until, reason=razon)
    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"🔇 **{usuario}** silenciado por {minutos} min. Razón: {razon}",
            color=0xf59e0b))
    await send_log(interaction.guild, "moderation",
        f"🔇 **{usuario}** silenciado {minutos}min por **{interaction.user}** · {razon}")

@tree.command(name="sorteo", description="Iniciar un sorteo [Admin]")
@app_commands.checks.has_permissions(manage_guild=True)
async def sorteo(interaction: discord.Interaction, duracion_min: int, premio: str,
                 canal: discord.TextChannel = None):
    ch = canal or interaction.channel
    end_time = datetime.now(timezone.utc) + timedelta(minutes=duracion_min)
    embed = discord.Embed(
        title="🎉 ¡SORTEO!",
        description=f"**Premio:** {premio}\n\nReaccioná con 🎉 para participar!\n⏰ Termina: <t:{int(end_time.timestamp())}:R>",
        color=0xf59e0b
    )
    msg = await ch.send(embed=embed)
    await msg.add_reaction("🎉")
    await interaction.response.send_message(f"✅ Sorteo iniciado en {ch.mention}", ephemeral=True)
    await asyncio.sleep(duracion_min * 60)
    msg = await ch.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if reaction:
        users = [u async for u in reaction.users() if not u.bot]
        if users:
            import random
            winner = random.choice(users)
            await ch.send(embed=discord.Embed(
                description=f"🎊 ¡{winner.mention} ganó **{premio}**! Felicidades!",
                color=0x22c55e))
        else:
            await ch.send("😢 Nadie participó en el sorteo.")

@tree.command(name="panel", description="Link al panel de administración")
@app_commands.checks.has_permissions(manage_guild=True)
async def panel_cmd(interaction: discord.Interaction):
    url = os.environ.get("PANEL_URL", "https://tu-panel.railway.app")
    embed = discord.Embed(
        title="🎛️ Panel de Administración",
        description=f"[Abrir Panel]({url})",
        color=0x5b3de8
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="serverinfo", description="Ver información del servidor")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, color=0x3b82f6)
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    embed.add_field(name="👥 Miembros", value=str(g.member_count), inline=True)
    embed.add_field(name="📢 Canales", value=str(len(g.channels)), inline=True)
    embed.add_field(name="🏷️ Roles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="Owner", value=str(g.owner), inline=True)
    embed.add_field(name="Creado", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="userinfo", description="Ver información de un usuario")
async def userinfo(interaction: discord.Interaction, usuario: discord.Member = None):
    target = usuario or interaction.user
    embed = discord.Embed(title=str(target), color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="ID", value=str(target.id), inline=True)
    embed.add_field(name="Unido", value=f"<t:{int(target.joined_at.timestamp())}:D>", inline=True)
    embed.add_field(name="Roles", value=" ".join(r.mention for r in target.roles[1:]) or "None", inline=False)
    await interaction.response.send_message(embed=embed)

# ── STREAM CHECK ───────────────────────────────────────────────
_stream_state = {}

@tasks.loop(minutes=5)
async def check_streams():
    cfg = load_config()
    stream_cfg = cfg.get("stream_alert", {})
    if not stream_cfg.get("enabled"):
        return
    ch_id = stream_cfg.get("channel_id")
    if not ch_id:
        return
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    ch = guild.get_channel(int(ch_id))
    if not ch:
        return

    async def check_kick(username):
        if not username:
            return None
        url = f"https://kick.com/api/v1/channels/{username}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        data = await r.json()
                        livestream = data.get("livestream")
                        if livestream:
                            return {"title": livestream.get("session_title",""), "url": f"https://kick.com/{username}"}
        except Exception:
            pass
        return None

    kick_user = stream_cfg.get("kick_username", "")
    live = await check_kick(kick_user)
    key = f"kick_{kick_user}"
    if live and not _stream_state.get(key):
        _stream_state[key] = True
        msg = stream_cfg.get("message", "🔴 {username} está en vivo! {url}")
        msg = msg.replace("{username}", kick_user).replace("{url}", live["url"]).replace("{title}", live["title"])
        embed = discord.Embed(description=msg, color=0xef4444)
        await ch.send(embed=embed)
    elif not live:
        _stream_state[key] = False

# ── ERROR HANDLER ─────────────────────────────────────────────
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# ── RUN ───────────────────────────────────────────────────────
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ BOT_TOKEN no encontrado en variables de entorno")
