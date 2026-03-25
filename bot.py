import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, asyncio, aiohttp
from datetime import datetime

# ─── CONFIG ─────────────────────────────────────────────────
TOKEN    = os.environ.get("BOT_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID", "1486498876503494707"))

def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)

# ─── BOT SETUP ──────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ════════════════════════════════════════════════════════════
#  EVENTOS
# ════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Bot online: {bot.user}")
    print(f"   Servidor: {GUILD_ID}")

@bot.event
async def on_member_join(member):
    cfg = load_config()
    welcome = cfg.get("welcome", {})
    if not welcome.get("enabled", False):
        return

    channel_id = welcome.get("channel_id")
    if not channel_id:
        return

    channel = bot.get_channel(int(channel_id))
    if not channel:
        return

    # Asignar rol automático si está configurado
    auto_role_id = welcome.get("auto_role_id")
    if auto_role_id:
        role = member.guild.get_role(int(auto_role_id))
        if role:
            await member.add_roles(role)

    # Mensaje de bienvenida
    msg = welcome.get("message", "👋 Bienvenido/a a **{server}**, {user}!")
    msg = msg.replace("{user}", member.mention)
    msg = msg.replace("{username}", member.display_name)
    msg = msg.replace("{server}", member.guild.name)
    msg = msg.replace("{count}", str(member.guild.member_count))

    embed = discord.Embed(
        description=msg,
        color=0x5B3DE8,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Miembro #{member.guild.member_count}")

    banner_url = welcome.get("banner_url")
    if banner_url:
        embed.set_image(url=banner_url)

    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    cfg = load_config()
    goodbye = cfg.get("goodbye", {})
    if not goodbye.get("enabled", False):
        return

    channel_id = goodbye.get("channel_id")
    if not channel_id:
        return

    channel = bot.get_channel(int(channel_id))
    if not channel:
        return

    embed = discord.Embed(
        description=f"👋 **{member.display_name}** se fue del servidor.",
        color=0x6B7280,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    cfg = load_config()

    # Anti-spam: slowmode extra por software si está activado
    # XP System
    xp_cfg = cfg.get("xp", {})
    if xp_cfg.get("enabled", False):
        xp_data = cfg.get("xp_data", {})
        uid = str(message.author.id)
        if uid not in xp_data:
            xp_data[uid] = {"xp": 0, "level": 1}
        xp_data[uid]["xp"] += 10
        xp = xp_data[uid]["xp"]
        level = xp_data[uid]["level"]
        next_level_xp = level * 100
        if xp >= next_level_xp:
            xp_data[uid]["level"] += 1
            xp_data[uid]["xp"] = 0
            cfg["xp_data"] = xp_data
            save_config(cfg)
            ch_id = xp_cfg.get("levelup_channel_id")
            ch = bot.get_channel(int(ch_id)) if ch_id else message.channel
            await ch.send(
                f"🎉 {message.author.mention} subió al **nivel {xp_data[uid]['level']}** ⬆️"
            )
        else:
            cfg["xp_data"] = xp_data
            save_config(cfg)

    # Moderación: anti-links
    mod = cfg.get("moderation", {})
    if mod.get("anti_links", False):
        if any(x in message.content for x in ["http://", "https://", "discord.gg/"]):
            # Excepto staff y owner
            staff_role_id = cfg.get("roles", {}).get("staff_id")
            is_staff = any(r.id == int(staff_role_id) for r in message.author.roles) if staff_role_id else False
            if not is_staff and not message.author.guild_permissions.administrator:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} no podés postear links acá.", delete_after=5
                )
                return

    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    cfg = load_config()
    reaction_roles = cfg.get("reaction_roles", [])
    for rr in reaction_roles:
        if (str(payload.message_id) == str(rr.get("message_id")) and
                str(payload.emoji) == str(rr.get("emoji"))):
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rr["role_id"]))
            member = guild.get_member(payload.user_id)
            if role and member and not member.bot:
                await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    cfg = load_config()
    reaction_roles = cfg.get("reaction_roles", [])
    for rr in reaction_roles:
        if (str(payload.message_id) == str(rr.get("message_id")) and
                str(payload.emoji) == str(rr.get("emoji"))):
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rr["role_id"]))
            member = guild.get_member(payload.user_id)
            if role and member and not member.bot:
                await member.remove_roles(role)

# ════════════════════════════════════════════════════════════
#  COMANDOS SLASH
# ════════════════════════════════════════════════════════════

@tree.command(name="ping", description="Ver si el bot está vivo", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`", ephemeral=True)

@tree.command(name="rank", description="Ver tu nivel y XP", guild=discord.Object(id=GUILD_ID))
async def rank(interaction: discord.Interaction):
    cfg = load_config()
    xp_data = cfg.get("xp_data", {})
    uid = str(interaction.user.id)
    data = xp_data.get(uid, {"xp": 0, "level": 1})
    embed = discord.Embed(title=f"📊 Rank de {interaction.user.display_name}", color=0x5B3DE8)
    embed.add_field(name="Nivel", value=f"**{data['level']}**", inline=True)
    embed.add_field(name="XP", value=f"**{data['xp']}** / {data['level'] * 100}", inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="leaderboard", description="Top 10 del servidor", guild=discord.Object(id=GUILD_ID))
async def leaderboard(interaction: discord.Interaction):
    cfg = load_config()
    xp_data = cfg.get("xp_data", {})
    sorted_users = sorted(xp_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]
    embed = discord.Embed(title="🏆 Top 10 — The Family", color=0xF59E0B)
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    desc = ""
    for i, (uid, data) in enumerate(sorted_users):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"Usuario {uid[:4]}"
        desc += f"{medals[i]} **{name}** — Nivel {data['level']} ({data['xp']} XP)\n"
    embed.description = desc or "Nadie tiene XP todavía."
    await interaction.response.send_message(embed=embed)

@tree.command(name="sorteo", description="Iniciar un sorteo", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(premio="¿Qué se sortea?", duracion="Duración en minutos")
async def sorteo(interaction: discord.Interaction, premio: str, duracion: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo admins pueden hacer sorteos.", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎉 SORTEO",
        description=f"**Premio:** {premio}\n\nReaccioná con 🎉 para participar!\n\n⏱️ Termina en **{duracion} minuto(s)**",
        color=0x5B3DE8,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Organizado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")
    await asyncio.sleep(duracion * 60)
    msg = await interaction.channel.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    users = [u async for u in reaction.users() if not u.bot]
    if users:
        import random
        winner = random.choice(users)
        await interaction.channel.send(
            f"🎊 ¡Felicitaciones {winner.mention}! Ganaste **{premio}** 🏆"
        )
    else:
        await interaction.channel.send("😢 Nadie participó en el sorteo.")

@tree.command(name="say", description="El bot habla en un canal", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(mensaje="Mensaje a enviar")
async def say(interaction: discord.Interaction, mensaje: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        return
    await interaction.channel.send(mensaje)
    await interaction.response.send_message("✅ Enviado.", ephemeral=True)

@tree.command(name="embed", description="Enviar un embed personalizado", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(titulo="Título del embed", mensaje="Contenido del embed", color="Color en hex (ej: 5B3DE8)")
async def embed_cmd(interaction: discord.Interaction, titulo: str, mensaje: str, color: str = "5B3DE8"):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        return
    try:
        c = int(color.replace("#", ""), 16)
    except:
        c = 0x5B3DE8
    embed = discord.Embed(title=titulo, description=mensaje, color=c, timestamp=datetime.utcnow())
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Enviado.", ephemeral=True)

@tree.command(name="warn", description="Advertir a un usuario", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(usuario="Usuario a advertir", razon="Razón")
async def warn(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
        return
    embed = discord.Embed(
        title="⚠️ Advertencia",
        description=f"{usuario.mention} recibió una advertencia.\n**Razón:** {razon}",
        color=0xF59E0B
    )
    await interaction.channel.send(embed=embed)
    try:
        await usuario.send(f"⚠️ Recibiste una advertencia en **The Family**.\n**Razón:** {razon}")
    except:
        pass
    await interaction.response.send_message("✅ Advertencia enviada.", ephemeral=True)

@tree.command(name="clear", description="Borrar mensajes", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(cantidad="Cantidad de mensajes a borrar")
async def clear(interaction: discord.Interaction, cantidad: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
        return
    await interaction.channel.purge(limit=cantidad)
    await interaction.response.send_message(f"🗑️ {cantidad} mensajes borrados.", ephemeral=True)

@tree.command(name="panel", description="Link al panel de configuración", guild=discord.Object(id=GUILD_ID))
async def panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        return
    panel_url = os.environ.get("PANEL_URL", "http://localhost:5000")
    await interaction.response.send_message(
        f"🎛️ **Panel de configuración:** {panel_url}\n_Solo accesible para admins._",
        ephemeral=True
    )

# ─── ARRANCAR ───────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(TOKEN)
