import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, asyncio, aiohttp, re, random
from datetime import datetime, timedelta, timezone
from groq import Groq

TOKEN    = (os.environ.get("BOT_TOKEN") or "").strip()
GUILD_ID = int((os.environ.get("GUILD_ID") or "0").strip())
GROQ_KEY = (os.environ.get("GROQ_API_KEY") or "").strip()

gemini_client = None  # kept as alias for compatibility
groq_client   = None
GROQ_MODEL    = "llama-3.3-70b-versatile"
if GROQ_KEY:
    groq_client   = Groq(api_key=GROQ_KEY)
    gemini_client = groq_client  # so existing checks still work

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
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())
    bot.add_view(StaffPanelView())
    bot.add_view(OnboardingView())
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

    # Welcome message (AI Powered)
    if w.get("enabled") and w.get("channel_id"):
        try:
            ch = member.guild.get_channel(int(w["channel_id"]))
            if ch:
                ai_msg = ""
                if groq_client:
                    try:
                        prompt = f"El usuario '{member.display_name}' acaba de unirse al servidor de Discord '{member.guild.name}'. El servidor tiene {member.guild.member_count} miembros. Escribe un mensaje de bienvenida corto (1 o 2 oraciones), gamer, épico, amigable y muy moderno para él. No uses emojis exagerados pero sé cálido. Usa tú (no usted)."
                        resp = groq_client.chat.completions.create(
                            model=GROQ_MODEL,
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=150
                        )
                        ai_msg = resp.choices[0].message.content.strip()
                    except Exception as e:
                        print(f"Groq API error (fallback to default msg): {e}")

                if not ai_msg:
                    ai_msg = f"👋 ¡Bienvenido/a a la nave, {member.mention}! Somos **{member.guild.name}**."

                embed = discord.Embed(
                    description=f"**{member.mention}** ha aterrizado.\n\n🤖 *Mensaje de IA:*\n> {ai_msg}",
                    color=0xff4747
                )
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                if w.get("banner_url"): embed.set_image(url=w["banner_url"])
                embed.set_footer(text="A.I. Autonomous Welcomes")
                await ch.send(embed=embed)
        except Exception as e:
            print(f"Welcome error: {e}", flush=True)

    # ── Onboarding / Verification DM ────────────────────────────
    ob = cfg.get("onboarding", {})
    if ob.get("enabled"):
        if ob.get("quarantine_role_id"):
            try:
                qr = member.guild.get_role(int(ob["quarantine_role_id"]))
                if qr: await member.add_roles(qr)
            except: pass
        try:
            dm_embed = discord.Embed(
                title=f"🔐 Verificación — {member.guild.name}",
                description=f"Hola **{member.display_name}**! Para acceder al servidor completa una verificación rápida.\nHaz click en el botón de abajo. ¡Toma menos de 1 minuto! 🚀",
                color=0x6366f1
            )
            if member.guild.icon: dm_embed.set_thumbnail(url=member.guild.icon.url)
            dm_embed.set_footer(text=f"{member.guild.name} • Sistema de Verificación")
            await member.send(embed=dm_embed, view=OnboardingView())
        except discord.Forbidden:
            ch_id = ob.get("channel_id")
            if ch_id:
                try:
                    vch = member.guild.get_channel(int(ch_id))
                    if vch: await vch.send(f"{member.mention} completa tu verificación:", view=OnboardingView(), delete_after=86400)
                except: pass
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
                try:
                    rewards = xp_cfg.get("role_rewards", {})
                    str_lv = str(ud["level"])
                    if str_lv in rewards and rewards[str_lv]:
                        role_new = message.guild.get_role(int(rewards[str_lv]))
                        if role_new:
                            await message.author.add_roles(role_new, reason=f"Recompensa Nivel {str_lv}")
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

STAFF_KEYWORDS = ["staff", "moderador", "mod", "admin", "soporte", "support", "helper", "ayudante", "guardian", "guardia"]

def is_staff_role(role_name: str) -> bool:
    name = role_name.lower()
    return any(kw in name for kw in STAFF_KEYWORDS)

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles: return
    added   = [r for r in after.roles if r not in before.roles]
    removed = [r for r in before.roles if r not in after.roles]

    if added:   await send_log(before.guild, "role_update", f"🏷️ **{after}** recibió {added[0].mention}")
    if removed: await send_log(before.guild, "role_update", f"🏷️ **{after}** perdió {removed[0].mention}")

    new_staff_roles = [r for r in added if is_staff_role(r.name)]
    if not new_staff_roles: return

    role_name = new_staff_roles[0].name
    embed = discord.Embed(
        title=f"🛡️ ¡Bienvenido al Staff de {after.guild.name}!",
        description=(
            f"Hola **{after.display_name}**, se te ha asignado el rol **{role_name}**.\n"
            "Ahora tienes acceso a comandos y herramientas de moderación."
        ),
        color=0x6366f1
    )
    embed.add_field(
        name="⚡ Tus Comandos",
        value=(
            "`/warn @usuario razón` — Advertir\n"
            "`/warns @usuario` — Ver advertencias\n"
            "`/clear cantidad` — Borrar mensajes\n"
            "`/kick @usuario razón` — Expulsar\n"
            "`/timeout @usuario min` — Silenciar\n"
            "`/staffpanel` — Panel de Staff con botones\n"
            "`/userinfo @usuario` — Info del usuario"
        ),
        inline=False
    )
    embed.add_field(
        name="📋 Reglas de Staff",
        value=(
            "• Usa los comandos con responsabilidad\n"
            "• Siempre indica una razón válida\n"
            "• Consulta al Admin antes de banear\n"
            "• Reporta cualquier abuso de usuario"
        ),
        inline=False
    )
    embed.set_footer(text=f"The Family • Rol: {role_name}")
    try:
        await after.send(embed=embed)
    except discord.Forbidden:
        pass

    try:
        staff_ch = None
        for ch in after.guild.text_channels:
            if any(kw in ch.name.lower() for kw in ["staff", "mod", "admin", "soporte"]):
                perms = ch.permissions_for(after.guild.me)
                if perms.send_messages:
                    staff_ch = ch
                    break
        if staff_ch:
            notif = discord.Embed(
                description=f"👮 {after.mention} ahora es **{role_name}**. ¡Bienvenido al equipo!",
                color=0x22c55e
            )
            await staff_ch.send(embed=notif)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  STAFF PANEL — DISCORD UI WITH BUTTONS
# ═══════════════════════════════════════════════════════════════

class MemberSelectModal(discord.ui.Modal):
    def __init__(self, action: str):
        super().__init__(title=f"{'⚠️ Warn' if action=='warn' else '👢 Kick' if action=='kick' else '🔨 Ban' if action=='ban' else '🔇 Timeout' if action=='timeout' else '🗑️ Clear'}")
        self.action = action
        if action == "clear":
            self.cantidad = discord.ui.TextInput(label="Cantidad de mensajes (1-100)", placeholder="10", max_length=3)
            self.add_item(self.cantidad)
        else:
            self.target = discord.ui.TextInput(label="ID o @usuario", placeholder="123456789 o nombre del usuario", max_length=50)
            self.razon  = discord.ui.TextInput(label="Razón", placeholder="Comportamiento inadecuado...", required=False, max_length=200)
            self.add_item(self.target)
            self.add_item(self.razon)

    async def on_submit(self, interaction: discord.Interaction):
        if not (interaction.user.guild_permissions.moderate_members or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ No tienes permisos de staff.", ephemeral=True)
            return

        if self.action == "clear":
            try:
                n = min(max(int(self.cantidad.value), 1), 100)
                deleted = await interaction.channel.purge(limit=n)
                await interaction.response.send_message(f"🗑️ {len(deleted)} mensajes eliminados.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            return

        razon = self.razon.value if self.razon.value else "Sin razón"
        target_str = self.target.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        guild = interaction.guild
        member = None
        try:
            member = guild.get_member(int(target_str))
            if not member:
                member = discord.utils.find(lambda m: m.name.lower() == target_str.lower() or m.display_name.lower() == target_str.lower(), guild.members)
        except (ValueError, TypeError):
            member = discord.utils.find(lambda m: m.name.lower() == target_str.lower() or m.display_name.lower() == target_str.lower(), guild.members)

        if not member:
            await interaction.response.send_message(f"❌ No encontré al usuario `{target_str}`.", ephemeral=True)
            return

        try:
            if self.action == "warn":
                cfg = load_config()
                w = cfg.get("warns", {})
                uid = str(member.id)
                w[uid] = w.get(uid, [])
                w[uid].append({"razon": razon, "fecha": str(datetime.now()), "by": str(interaction.user)})
                cfg["warns"] = w
                save_config(cfg)
                result = f"⚠️ **{member}** advertido. Total warns: {len(w[uid])}"
                color = 0xf59e0b
            elif self.action == "kick":
                await member.kick(reason=razon)
                result = f"👢 **{member}** expulsado."
                color = 0xef4444
            elif self.action == "ban":
                await member.ban(reason=razon)
                result = f"🔨 **{member}** baneado."
                color = 0xef4444
            elif self.action == "timeout":
                until = discord.utils.utcnow() + timedelta(minutes=10)
                await member.timeout(until, reason=razon)
                result = f"🔇 **{member}** silenciado 10 min."
                color = 0xf59e0b

            embed = discord.Embed(description=f"{result}\nRazón: *{razon}*\nPor: {interaction.user.mention}", color=color)
            await interaction.response.send_message(embed=embed)
            await send_log(guild, "moderation", f"{result} | Razón: {razon} | Por: {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ No tengo permisos para hacer esa acción.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class StaffPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚠️ Warn", style=discord.ButtonStyle.secondary, custom_id="sp_warn", row=0)
    async def warn_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemberSelectModal("warn"))

    @discord.ui.button(label="👢 Kick", style=discord.ButtonStyle.danger, custom_id="sp_kick", row=0)
    async def kick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemberSelectModal("kick"))

    @discord.ui.button(label="🔨 Ban", style=discord.ButtonStyle.danger, custom_id="sp_ban", row=0)
    async def ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemberSelectModal("ban"))

    @discord.ui.button(label="🔇 Timeout", style=discord.ButtonStyle.secondary, custom_id="sp_timeout", row=1)
    async def timeout_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemberSelectModal("timeout"))

    @discord.ui.button(label="🗑️ Limpiar Chat", style=discord.ButtonStyle.secondary, custom_id="sp_clear", row=1)
    async def clear_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemberSelectModal("clear"))

    @discord.ui.button(label="📋 Warns de Usuario", style=discord.ButtonStyle.primary, custom_id="sp_warns", row=1)
    async def warns_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        class WarnsModal(discord.ui.Modal, title="📋 Ver Warns"):
            target = discord.ui.TextInput(label="ID o nombre del usuario", max_length=50)

            async def on_submit(self_, i2: discord.Interaction):
                t = self_.target.value.strip().replace("<@", "").replace(">", "").replace("!", "")
                guild = i2.guild
                member = None
                try:
                    member = guild.get_member(int(t))
                except: pass
                if not member:
                    member = discord.utils.find(lambda m: m.name.lower() == t.lower() or m.display_name.lower() == t.lower(), guild.members)
                if not member:
                    await i2.response.send_message(f"❌ No encontré `{t}`.", ephemeral=True)
                    return
                warns = load_config().get("warns", {}).get(str(member.id), [])
                if not warns:
                    await i2.response.send_message(f"✅ {member.mention} no tiene warns.", ephemeral=True)
                    return
                embed = discord.Embed(title=f"⚠️ Warns de {member}", color=0xf59e0b)
                for i3, w in enumerate(warns, 1):
                    embed.add_field(name=f"#{i3}", value=f"Razón: {w['razon']}\nPor: {w['by']}", inline=True)
                await i2.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(WarnsModal())

# ═══════════════════════════════════════════════════════════════
#  ONBOARDING SYSTEM — QUESTIONNAIRE
# ═══════════════════════════════════════════════════════════════

class OnboardingModal(discord.ui.Modal, title="✅ Verificación — The Family"):
    def __init__(self):
        super().__init__()
        cfg = load_config()
        ob = cfg.get("onboarding", {})

        self.q1 = discord.ui.TextInput(label=ob.get("q1", "¿De dónde eres?")[:45], placeholder=ob.get("p1", "País / Ciudad")[:95], max_length=50)
        self.q2 = discord.ui.TextInput(label=ob.get("q2", "¿Qué equipo/consola usas?")[:45], placeholder=ob.get("p2", "PC / PS5 / Xbox / Mobile")[:95], max_length=40)
        self.q3 = discord.ui.TextInput(label=ob.get("q3", "¿Qué te trajo al servidor?")[:45], placeholder=ob.get("p3", "Gaming / Torneos / Curioso")[:95], max_length=60)
        self.q4 = discord.ui.TextInput(label=ob.get("q4", "¿Cuántos años tienes?")[:45], placeholder=ob.get("p4", "Ej: 20")[:95], max_length=3)
        self.q5 = discord.ui.TextInput(label=ob.get("q5", "¿Algo más que quieras compartir?")[:45], style=discord.TextStyle.long, required=False, max_length=300, placeholder=ob.get("p5", "Opcional")[:95])

        for q in [self.q1, self.q2, self.q3, self.q4, self.q5]:
            self.add_item(q)

    async def on_submit(self, interaction: discord.Interaction):
        cfg   = load_config()
        ob    = cfg.get("onboarding", {})
        guild = interaction.guild
        added_roles = []

        if ob.get("verified_role_id"):
            r = guild.get_role(int(ob["verified_role_id"]))
            if r:
                try:
                    await interaction.user.add_roles(r)
                    added_roles.append(r.name)
                except: pass

        eq = self.q2.value.lower()
        if any(x in eq for x in ["pc", "computadora", "ordenador", "laptop"]):
            rid = ob.get("role_pc")
        elif any(x in eq for x in ["ps5", "ps4", "playstation", "ps", "xbox", "series"]):
            rid = ob.get("role_console")
        elif any(x in eq for x in ["mobile", "móvil", "movil", "celular", "phone", "android", "ios"]):
            rid = ob.get("role_mobile")
        else:
            rid = ob.get("role_console")
        if rid:
            r = guild.get_role(int(rid))
            if r:
                try:
                    await interaction.user.add_roles(r)
                    added_roles.append(r.name)
                except: pass

        try:
            age = int(re.sub(r"[^0-9]", "", self.q4.value))
            age_rid = ob.get("role_adult") if age >= 18 else ob.get("role_minor")
            if age_rid:
                r = guild.get_role(int(age_rid))
                if r:
                    try:
                        await interaction.user.add_roles(r)
                        added_roles.append(r.name)
                    except: pass
        except: pass

        if ob.get("quarantine_role_id"):
            qr = guild.get_role(int(ob["quarantine_role_id"]))
            if qr and qr in interaction.user.roles:
                try:
                    await interaction.user.remove_roles(qr)
                except: pass

        responses = cfg.get("onboarding_responses", {})
        responses[str(interaction.user.id)] = {
            "nombre": interaction.user.display_name,
            "q1": self.q1.value,
            "q2": self.q2.value,
            "q3": self.q3.value,
            "q4": self.q4.value,
            "q5": self.q5.value or "",
            "roles": added_roles,
            "fecha": str(datetime.now()),
        }
        cfg["onboarding_responses"] = responses
        save_config(cfg)

        embed = discord.Embed(
            title="✅ ¡Verificación Completada!",
            description=f"¡Bienvenido/a al equipo, **{interaction.user.display_name}**! Ya tienes acceso completo.",
            color=0x22c55e
        )
        embed.add_field(name="📍 Origen",  value=self.q1.value, inline=True)
        embed.add_field(name="🎮 Equipo",  value=self.q2.value, inline=True)
        embed.add_field(name="🎯 Motivo", value=self.q3.value, inline=True)
        if added_roles:
            embed.add_field(name="🏷️ Roles Asignados", value=", ".join(f"**{r}**" for r in added_roles), inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"{guild.name} • Onboarding System")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await send_log(guild, "member_join", f"✅ **{interaction.user}** completó el onboarding. Equipo: {self.q2.value} | Edad: {self.q4.value}")


class OnboardingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Completar Verificación", style=discord.ButtonStyle.success, custom_id="onboarding_verify")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = load_config()
        if str(interaction.user.id) in cfg.get("onboarding_responses", {}):
            await interaction.response.send_message("✅ Ya completaste la verificación.", ephemeral=True)
            return
        await interaction.response.send_modal(OnboardingModal())


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
        await interaction.response.send_message("❌ El sistema XP está desactivado.", ephemeral=True)
        return
    ud = cfg.get("xp_data", {}).get(str(target.id), {"xp": 0, "level": 0})
    xp = ud.get("xp", 0)
    lv = ud.get("level", 0)
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
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (uid, data) in enumerate(top):
        try:
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"Usuario {uid[:6]}"
        except:
            name = f"Usuario {uid[:6]}"
        lines.append(f"{medals[i] if i < 3 else f'`{i+1}.`'} **{name}** — Nv {data.get('level', 0)} · {data.get('xp', 0)} XP")
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
    try:
        col = int(color.strip("#"), 16)
    except:
        col = 0x6366f1
    await ch.send(embed=discord.Embed(title=titulo, description=descripcion, color=col))
    await interaction.response.send_message("✅ Embed enviado", ephemeral=True)

@tree.command(name="warn", description="Advertir usuario [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    cfg = load_config()
    warns = cfg.get("warns", {})
    uid = str(usuario.id)
    warns[uid] = warns.get(uid, [])
    warns[uid].append({"razon": razon, "fecha": str(datetime.now()), "by": str(interaction.user)})
    cfg["warns"] = warns
    save_config(cfg)
    embed = discord.Embed(description=f"⚠️ **{usuario}** advertido.\nRazón: {razon}\nTotal warns: {len(warns[uid])}", color=0xf59e0b)
    await interaction.response.send_message(embed=embed)
    await send_log(interaction.guild, "moderation", f"⚠️ **{usuario}** advertido por **{interaction.user}** · {razon}")

@tree.command(name="warns", description="Ver advertencias [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def show_warns(interaction: discord.Interaction, usuario: discord.Member):
    warns = load_config().get("warns", {}).get(str(usuario.id), [])
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
    if not 1 <= cantidad <= 100:
        await interaction.response.send_message("❌ Entre 1 y 100.", ephemeral=True)
        return
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
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
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
            await interaction.response.send_message("❌ Los tickets están desactivados.", ephemeral=True)
            return
        guild = interaction.guild
        cat_id = tk.get("category_id")
        cat = guild.get_channel(int(cat_id)) if cat_id else None
        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.name.lower()[:20]}")
        if existing:
            await interaction.response.send_message(f"❌ Ya tienes un ticket abierto: {existing.mention}", ephemeral=True)
            return
        support_role_id = tk.get("support_role_id")
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        ch = await guild.create_text_channel(f"ticket-{interaction.user.name.lower()[:20]}", overwrites=overwrites, category=cat)
        embed = discord.Embed(title="🎫 Ticket Abierto", description=f"Hola {interaction.user.mention}! Un miembro del staff atenderá tu consulta pronto.\n\nUsa el botón de abajo para cerrar el ticket.", color=0x6366f1)
        await ch.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket creado: {ch.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket 🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Generando transcripción y cerrando ticket en unos segundos...")
        messages = [msg async for msg in interaction.channel.history(limit=100, oldest_first=True)]
        transcript = f"Transcripción del Ticket: {interaction.channel.name}\n\n"
        for m in messages:
            transcript += f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author.name}: {m.content}\n"

        cfg = load_config()
        log_ch_id = cfg.get("logs", {}).get("channel_id")
        if log_ch_id:
            try:
                log_ch = interaction.guild.get_channel(int(log_ch_id))
                if log_ch:
                    import io
                    file = discord.File(io.BytesIO(transcript.encode("utf-8")), filename=f"transcript_{interaction.channel.name}.txt")
                    embed = discord.Embed(title="🎫 Ticket Cerrado", description=f"`{interaction.channel.name}` cerrado por {interaction.user.mention}", color=0xef4444)
                    await log_ch.send(embed=embed, file=file)
            except Exception: pass

        await asyncio.sleep(2)
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
    soc = cfg.get("socials", {})
    if not soc.get("enabled") or not soc.get("channel_id"): return
    guild = bot.get_guild(GUILD_ID)
    if not guild: return
    ch = guild.get_channel(int(soc["channel_id"]))
    if not ch: return

    async def check_kick(username):
        if not username: return None
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://kick.com/api/v1/channels/{username}", timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        data = await r.json()
                        ls = data.get("livestream")
                        if ls: return {"title": ls.get("session_title", ""), "url": f"https://kick.com/{username}"}
        except Exception: pass
        return None

    async def check_twitch(username):
        if not username: return None
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://decapi.me/twitch/uptime/{username}", timeout=8) as r:
                    text = (await r.text()).strip()
                    if "Offline" not in text and "error" not in text.lower() and text:
                        title_req = await s.get(f"https://decapi.me/twitch/title/{username}")
                        title = await title_req.text() if title_req.status == 200 else "Live!"
                        return {"title": title, "url": f"https://twitch.tv/{username}"}
        except Exception: pass
        return None

    async def check_youtube(handle):
        if not handle: return None
        handle = handle.replace("@", "")
        try:
            async with aiohttp.ClientSession() as s:
                url = f"https://www.youtube.com/@{handle}/live"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                async with s.get(url, headers=headers, timeout=8) as r:
                    text = await r.text()
                    if 'itemprop="isLiveBroadcast" content="True"' in text or '"isLive":true' in text or 'ytp-live' in text:
                        title = "Live!"
                        title_match = re.search(r'<title>(.*?)</title>', text)
                        if title_match: title = title_match.group(1).replace(" - YouTube", "")
                        return {"title": title, "url": url}
        except Exception: pass
        return None

    async def check_tiktok(username):
        if not username: return None
        username = username.replace("@", "")
        try:
            async with aiohttp.ClientSession() as s:
                url = f"https://www.tiktok.com/@{username}/live"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                async with s.get(url, headers=headers, timeout=8) as r:
                    text = await r.text()
                    if '"roomId":"' in text:
                        match = re.search(r'"roomId":"(\d+)"', text)
                        if match and match.group(1) and match.group(1) != "0":
                            return {"title": "¡En vivo en TikTok!", "url": url}
        except Exception: pass
        return None

    platforms = {
        "kick":    (soc.get("kick", ""),    check_kick,    0x53fc18, "🟩 Kick"),
        "twitch":  (soc.get("twitch", ""),  check_twitch,  0x9146FF, "🟪 Twitch"),
        "youtube": (soc.get("youtube", ""), check_youtube, 0xFF0000, "🟥 YouTube"),
        "tiktok":  (soc.get("tiktok", ""),  check_tiktok,  0x000000, "📱 TikTok"),
    }

    for plat, (user, func, color, plat_name) in platforms.items():
        if not user: continue
        live = await func(user)
        key = f"{plat}_{user}"
        if live and not _stream_state.get(key):
            _stream_state[key] = True
            embed = discord.Embed(
                title=f"🔴 ¡{user} está en vivo en {plat_name}!",
                description=f"**{live['title']}**\n\n[🎮 Entra a ver el stream aquí]({live['url']})",
                color=color
            )
            embed.set_author(name=user)
            await ch.send(content="@everyone" if plat in ["twitch", "youtube"] else "", embed=embed)
        elif not live:
            _stream_state[key] = False


@tree.command(name="staffpanel", description="Abre el panel interactivo de Staff [Staff]")
@app_commands.checks.has_permissions(moderate_members=True)
async def staffpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ Panel de Control — Staff",
        description="Selecciona una acción para administrar el servidor. Se abrirá una ventana para ingresar los datos del usuario.",
        color=0x6366f1
    )
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, view=StaffPanelView(), ephemeral=True)

@tree.command(name="staffpanel-setup", description="Envía el panel de Staff a un canal fijo [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def staffpanel_setup(interaction: discord.Interaction, canal: discord.TextChannel):
    embed = discord.Embed(
        title="🛡️ Panel de Control — Staff",
        description="Selecciona una acción para usar las herramientas de moderación.",
        color=0x6366f1
    )
    await canal.send(embed=embed, view=StaffPanelView())
    await interaction.response.send_message(f"✅ Panel de staff enviado a {canal.mention}", ephemeral=True)

@bot.event
async def setup_hook():
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())
    bot.add_view(StaffPanelView())
    bot.add_view(OnboardingView())

@tree.command(name="autosetup", description="🤖 Analiza el servidor y configura el bot automáticamente [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def autosetup(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    guild = interaction.guild
    channels = guild.channels
    roles    = guild.roles
    members  = guild.members

    text_ch = [c for c in channels if isinstance(c, (discord.TextChannel, discord.NewsChannel))]
    cats    = [c for c in channels if isinstance(c, discord.CategoryChannel)]

    def find_ch(*kws):
        for kw in kws:
            for c in text_ch:
                if kw in c.name.lower(): return str(c.id)
        return None

    def find_cat(*kws):
        for kw in kws:
            for c in cats:
                if kw in c.name.lower(): return str(c.id)
        return None

    def find_role(*kws):
        for kw in kws:
            for r in roles:
                if kw in r.name.lower() and r.name != "@everyone": return str(r.id)
        return None

    welcome_ch  = find_ch("bienvenid", "welcome", "llegada", "entrada", "newmember")
    goodbye_ch  = find_ch("despedid", "salida", "leave", "adios", "bienvenid", "welcome")
    log_ch      = find_ch("log", "audit", "registro", "modlog", "staff-log")
    stream_ch   = find_ch("stream", "alerta", "live", "directo", "notif", "kick")
    announce_ch = find_ch("anunci", "announcement", "anuncio", "noticias", "news")
    ticket_cat  = find_cat("ticket", "soporte", "support", "ayuda", "help")
    member_role = find_role("miembro", "member", "verificado", "verified", "familia", "integrante")
    staff_role  = find_role("staff", "moderador", "mod", "soporte", "support")

    cfg = load_config()
    applied = []

    if welcome_ch:
        cfg["welcome"]["enabled"] = True
        cfg["welcome"]["channel_id"] = welcome_ch
        if member_role: cfg["welcome"]["auto_role_id"] = member_role
        applied.append(f"✅ Bienvenida → <#{welcome_ch}>")
    else:
        applied.append("⚠️ Bienvenida — canal no detectado (créalo con nombre 'bienvenida')")

    if goodbye_ch:
        cfg["goodbye"]["enabled"] = True
        cfg["goodbye"]["channel_id"] = goodbye_ch
        applied.append(f"✅ Despedida → <#{goodbye_ch}>")

    if log_ch:
        cfg["logs"]["enabled"] = True
        cfg["logs"]["channel_id"] = log_ch
        cfg["logs"]["events"] = ["member_join", "member_leave", "message_delete", "moderation", "role_update"]
        applied.append(f"✅ Logs → <#{log_ch}>")
    else:
        applied.append("⚠️ Logs — canal no detectado (créalo con nombre 'logs')")

    if stream_ch:
        cfg["stream_alert"]["enabled"] = True
        cfg["stream_alert"]["channel_id"] = stream_ch
        applied.append(f"✅ Stream Alerts → <#{stream_ch}>")

    if ticket_cat:
        cfg["tickets"]["enabled"] = True
        cfg["tickets"]["category_id"] = ticket_cat
        if staff_role: cfg["tickets"]["support_role_id"] = staff_role
        applied.append("✅ Tickets configurados")

    cfg["moderation"]["anti_links"] = True
    cfg["moderation"]["anti_spam"] = True
    applied.append("✅ Anti-links + Anti-spam activados")

    cfg["xp"]["enabled"] = True
    if announce_ch: cfg["xp"]["levelup_channel_id"] = announce_ch
    applied.append("✅ Sistema XP activado")

    save_config(cfg)

    human_count = sum(1 for m in members if not m.bot)
    bot_count   = sum(1 for m in members if m.bot)

    embed = discord.Embed(
        title="🤖 Análisis Completado — The Family Bot",
        description="\n".join(applied),
        color=0x6366f1
    )
    embed.add_field(name="📊 Estadísticas", value=f"Canales: **{len(channels)}** | Roles: **{len(roles)}** | Humanos: **{human_count}** | Bots: **{bot_count}**", inline=False)
    embed.add_field(name="💡 Siguiente paso", value="Usa `/ticket-setup #canal` para activar el panel de tickets con botones.", inline=False)
    embed.set_footer(text=f"Configurado por {interaction.user} • {datetime.now().strftime('%H:%M:%S')}")
    await interaction.followup.send(embed=embed)

# ═══════════════════════════════════════════════════════════════
#  MEGA AI — OWNER ONLY
# ═══════════════════════════════════════════════════════════════

async def execute_ai_discord(guild: discord.Guild, prompt: str) -> str:
    if not groq_client:
        return "❌ GROQ_API_KEY no configurada."

    text_chs = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
    voice_chs = [c for c in guild.channels if isinstance(c, discord.VoiceChannel)]
    ch_list  = ", ".join(f"#{c.name}({c.id})" for c in text_chs[:25])
    rol_list = ", ".join(f"{r.name}({r.id})" for r in guild.roles if r.name != "@everyone")[:600]

    sys_prompt = f"""Eres OMEGA-CORE, la IA suprema del servidor "{guild.name}".
Miembros: {guild.member_count} | Canales: {ch_list} | Roles: {rol_list}

COMPÓRTATE DE MANERA CONVERSACIONAL, AMABLE PERO OMNIPOTENTE.
Si el usuario simplemente habla contigo, respóndele normalmente.
Si te pide ejecutar una ACCIÓN ADMINISTRATIVA (crear/eliminar canales, roles, moderar usuarios, enviar mensajes, etc.), escribe tu respuesta conversacional y luego, AL FINAL, incluye un bloque de código JSON con los detalles de la acción. NO pongas texto después del JSON.

Ejemplo:
Claro mi Lord, he procedido a bannear al usuario.
```json
{{"action":"ban_user","user_id":"ID"}}
```

Acciones disponibles:
{{"action":"create_channel","name":"n","type":0}}  (0=texto, 2=voz, 4=categoría)
{{"action":"delete_channel","channel_id":"ID"}}
{{"action":"create_role","name":"n","color":"hex","hoist":false}}
{{"action":"delete_role","role_id":"ID"}}
{{"action":"send_message","channel_id":"ID","content":"msg"}}
{{"action":"send_embed","channel_id":"ID","title":"t","description":"d","color":"ff4747"}}
{{"action":"kick_user","user_id":"ID","reason":"r"}}
{{"action":"ban_user","user_id":"ID","reason":"r"}}
{{"action":"timeout_user","user_id":"ID","minutes":10}}
{{"action":"purge_channel","channel_id":"ID","count":50}}
{{"action":"create_poll","channel_id":"ID","question":"q","options":["o1","o2"]}}

Infiere la mejor opción. Ejecuta directamente sin pedir confirmación."""

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.7
        )
        text = resp.choices[0].message.content.strip()

        data = None
        json_str = ""

        if "```json" in text:
            parts = text.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0].strip()
                start = json_part.find("{")
                end   = json_part.rfind("}")
                if start != -1 and end != -1:
                    json_str = json_part[start:end+1]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) > 1:
                json_part = parts[1].strip()
                start = json_part.find("{")
                end   = json_part.rfind("}")
                if start != -1 and end != -1:
                    json_str = json_part[start:end+1]
        else:
            start = text.find("{")
            end   = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end+1]

        if json_str:
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[AI] Error parseando JSON: {e} -> {json_str[:200]}")

        clean_reply = text
        if json_str:
            clean_reply = text.replace(f"```json\n{json_str}\n```", "")
            clean_reply = clean_reply.replace(f"```json\n{json_str}```", "")
            clean_reply = clean_reply.replace(json_str, "")
            clean_reply = clean_reply.strip()

        if not data or not data.get("action"):
            return f"🤖 {clean_reply}" if clean_reply else "🤖 (Acción completada sin texto)"

        act = data.get("action")
        exec_msg = ""
        success = True

        try:
            if act == "reply":
                return f"🤖 {clean_reply}" if clean_reply else f"🤖 {data.get('content', '...')}"

            elif act == "create_channel":
                ctype = data.get("type", 0)
                name  = data.get("name")
                if not name:
                    success = False; exec_msg = "❌ Falta el nombre del canal."
                else:
                    if ctype == 0:   new_ch = await guild.create_text_channel(name)
                    elif ctype == 2: new_ch = await guild.create_voice_channel(name)
                    else:            new_ch = await guild.create_category(name)
                    exec_msg = f"✅ {new_ch.name} creado (ID: {new_ch.id})"

            elif act == "delete_channel":
                ch_id = data.get("channel_id")
                if not ch_id:
                    success = False; exec_msg = "❌ Falta ID del canal."
                else:
                    target_ch = guild.get_channel(int(ch_id))
                    if not target_ch:
                        success = False; exec_msg = "❌ Canal no encontrado."
                    else:
                        cname = target_ch.name
                        await target_ch.delete()
                        exec_msg = f"🗑️ Canal {cname} eliminado."

            elif act == "create_role":
                name = data.get("name")
                if not name:
                    success = False; exec_msg = "❌ Falta nombre del rol."
                else:
                    col = int(data.get("color", "6366f1").strip("#"), 16)
                    new_role = await guild.create_role(name=name, color=discord.Color(col), hoist=data.get("hoist", False))
                    exec_msg = f"✅ Rol {new_role.name} creado (ID: {new_role.id})"

            elif act == "delete_role":
                role_id = data.get("role_id")
                if not role_id:
                    success = False; exec_msg = "❌ Falta ID del rol."
                else:
                    target_role = guild.get_role(int(role_id))
                    if not target_role:
                        success = False; exec_msg = "❌ Rol no encontrado."
                    else:
                        rname = target_role.name
                        await target_role.delete()
                        exec_msg = f"🗑️ Rol {rname} eliminado."

            elif act == "send_message":
                ch_id   = data.get("channel_id")
                content = data.get("content")
                if not ch_id or not content:
                    success = False; exec_msg = "❌ Falta canal o contenido."
                else:
                    target_ch = guild.get_channel(int(ch_id))
                    if not target_ch:
                        success = False; exec_msg = "❌ Canal no encontrado."
                    else:
                        await target_ch.send(content)
                        exec_msg = f"📨 Mensaje enviado en #{target_ch.name}."

            elif act == "send_embed":
                ch_id = data.get("channel_id")
                title = data.get("title", "")
                desc  = data.get("description", "")
                if not ch_id:
                    success = False; exec_msg = "❌ Falta ID del canal."
                else:
                    target_ch = guild.get_channel(int(ch_id))
                    if not target_ch:
                        success = False; exec_msg = "❌ Canal no encontrado."
                    else:
                        col = int(data.get("color", "6366f1").strip("#"), 16)
                        await target_ch.send(embed=discord.Embed(title=title, description=desc, color=col))
                        exec_msg = f"📨 Embed enviado en #{target_ch.name}."

            elif act == "kick_user":
                user_id = data.get("user_id")
                reason  = data.get("reason", "IA Omega")
                if not user_id:
                    success = False; exec_msg = "❌ Falta ID del usuario."
                else:
                    m = guild.get_member(int(user_id))
                    if not m:
                        success = False; exec_msg = "❌ Miembro no encontrado."
                    else:
                        await m.kick(reason=reason)
                        exec_msg = f"👢 {m} expulsado."

            elif act == "ban_user":
                user_id = data.get("user_id")
                reason  = data.get("reason", "IA Omega")
                if not user_id:
                    success = False; exec_msg = "❌ Falta ID del usuario."
                else:
                    m = guild.get_member(int(user_id))
                    if not m:
                        success = False; exec_msg = "❌ Miembro no encontrado."
                    else:
                        await m.ban(reason=reason)
                        exec_msg = f"🔨 {m} baneado."

            elif act == "timeout_user":
                user_id = data.get("user_id")
                minutes = int(data.get("minutes", 10))
                if not user_id:
                    success = False; exec_msg = "❌ Falta ID del usuario."
                else:
                    m = guild.get_member(int(user_id))
                    if not m:
                        success = False; exec_msg = "❌ Miembro no encontrado."
                    else:
                        until = discord.utils.utcnow() + timedelta(minutes=minutes)
                        await m.timeout(until, reason="IA Omega")
                        exec_msg = f"🔇 {m} silenciado {minutes} min."

            elif act == "purge_channel":
                ch_id = data.get("channel_id")
                count = int(data.get("count", 50))
                if not ch_id:
                    success = False; exec_msg = "❌ Falta ID del canal."
                else:
                    target_ch = guild.get_channel(int(ch_id))
                    if not target_ch:
                        success = False; exec_msg = "❌ Canal no encontrado."
                    else:
                        deleted = await target_ch.purge(limit=count)
                        exec_msg = f"🧹 {len(deleted)} mensajes eliminados en #{target_ch.name}."

            elif act == "create_poll":
                ch_id    = data.get("channel_id")
                question = data.get("question")
                options  = data.get("options", ["Sí", "No"])
                if not ch_id or not question:
                    success = False; exec_msg = "❌ Falta canal o pregunta."
                else:
                    target_ch = guild.get_channel(int(ch_id))
                    if not target_ch:
                        success = False; exec_msg = "❌ Canal no encontrado."
                    else:
                        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
                        poll_desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options[:4]))
                        poll_embed = discord.Embed(title=f"📊 {question}", description=poll_desc, color=0x6366f1)
                        poll_msg = await target_ch.send(embed=poll_embed)
                        for i in range(len(options[:4])):
                            await poll_msg.add_reaction(emojis[i])
                        exec_msg = f"📊 Encuesta creada en #{target_ch.name}."
            else:
                success = False
                exec_msg = f"⚠️ Acción desconocida: {act}"

        except discord.Forbidden as e:
            success = False
            exec_msg = f"❌ Permisos insuficientes para {act}: {e}"
        except Exception as e:
            success = False
            exec_msg = f"❌ Error ejecutando {act}: {e}"

        return f"🤖 {clean_reply}\n\n{exec_msg}" if clean_reply else f"🤖 {exec_msg}"

    except json.JSONDecodeError as e:
        return f"❌ Error de parsing JSON: {e}"
    except Exception as e:
        return f"❌ Error: {e}"


@tree.command(name="ai", description="🤖 Ordena CUALQUIER COSA a la IA — control total [Solo Owner]")
@app_commands.describe(prompt="¿Qué quieres que haga la IA?")
async def ai_cmd(interaction: discord.Interaction, prompt: str):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Este comando es exclusivo del dueño del servidor.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    result = await execute_ai_discord(interaction.guild, prompt)
    embed = discord.Embed(description=result, color=0x6366f1)
    embed.set_author(name="🤖 OMEGA-CORE · IA Suprema", icon_url=bot.user.display_avatar.url)
    embed.set_footer(text=f"Comandante: {interaction.user.display_name} • The Family")
    await interaction.followup.send(embed=embed)


@tree.command(name="ai-analyze", description="🔍 La IA analiza los últimos mensajes del canal [Solo Owner]")
async def ai_analyze(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Solo para el dueño.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    msgs = [m async for m in interaction.channel.history(limit=50)]
    history_txt = "\n".join(f"{m.author.display_name}: {m.content[:100]}" for m in reversed(msgs) if not m.author.bot and m.content)[:2000]
    if groq_client and history_txt:
        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Analiza esta conversación de Discord (canal #{interaction.channel.name}) y da: 1) Resumen de temas, 2) Tono general, 3) Usuarios más activos, 4) Alertas o problemas, 5) Sugerencias. Sé conciso.\n\n{history_txt}"
                }],
                max_tokens=800
            )
            analysis = resp.choices[0].message.content.strip()
        except Exception as e:
            analysis = f"Error IA: {e}"
    else:
        analysis = "No hay mensajes o GROQ_API_KEY no configurada."
    embed = discord.Embed(title=f"🔍 Análisis de #{interaction.channel.name}", description=analysis[:4000], color=0x6366f1)
    embed.set_footer(text="OMEGA-CORE · The Family")
    await interaction.followup.send(embed=embed)


@tree.command(name="ai-report", description="📊 Reporte completo del servidor con IA [Solo Owner]")
async def ai_report(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Solo para el dueño.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    guild = interaction.guild
    cfg   = load_config()
    humans = sum(1 for m in guild.members if not m.bot)
    warns  = cfg.get("warns", {})
    top_warned = sorted(warns.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    pending_ob = len([m for m in guild.members if not m.bot and str(m.id) not in cfg.get("onboarding_responses", {})])
    embed = discord.Embed(title=f"📊 Reporte OMEGA — {guild.name}", color=0x6366f1, timestamp=datetime.now(timezone.utc))
    embed.add_field(name="👥 Miembros", value=f"Humanos: {humans}\nTotal: {guild.member_count}", inline=True)
    embed.add_field(name="📢 Servidor", value=f"Canales: {len(guild.channels)}\nRoles: {len(guild.roles)}\nBoost: Nv {guild.premium_tier}", inline=True)
    embed.add_field(name="⚠️ Más warnados", value="\n".join(f"<@{uid}>: {len(w)} warns" for uid, w in top_warned) or "Ninguno", inline=False)
    embed.add_field(name="❓ Onboarding", value=f"{pending_ob} miembros sin verificar" if pending_ob else "✅ Todos verificados", inline=True)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="OMEGA-CORE · The Family Bot")
    await interaction.followup.send(embed=embed)

# ── ONBOARDING COMMANDS ────────────────────────────────────────
@tree.command(name="onboarding-setup", description="🤖 Auto-configura TODO el sistema de verificación [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def onboarding_setup(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.defer(thinking=True)
    guild = interaction.guild
    steps = []

    async def get_or_create_role(names, color, hoist=False, reason="Onboarding Auto-Setup"):
        for name in names:
            found = discord.utils.find(lambda r: r.name.lower() == name.lower(), guild.roles)
            if found: return found
        return await guild.create_role(name=names[0], color=color, hoist=hoist, reason=reason)

    try:
        r_quarantine = await get_or_create_role(["Cuarentena", "Quarantine"], discord.Color.from_str("#4b5563"))
        steps.append(f"✅ Rol {r_quarantine.name} listo")

        r_verified = await get_or_create_role(["Verificado", "Verified"], discord.Color.from_str("#22c55e"), hoist=True)
        steps.append(f"✅ Rol {r_verified.name} listo")

        r_pc      = await get_or_create_role(["PC Gamer", "PC"],           discord.Color.from_str("#3b82f6"))
        r_console = await get_or_create_role(["Console Player", "Consola"], discord.Color.from_str("#8b5cf6"))
        r_mobile  = await get_or_create_role(["Mobile", "Móvil"],           discord.Color.from_str("#f59e0b"))
        steps.append("✅ Roles de plataformas listos")

        r_adult = await get_or_create_role(["+18", "Mayor"], discord.Color.from_str("#ef4444"))
        r_minor = await get_or_create_role(["-18", "Menor"], discord.Color.from_str("#6366f1"))
        steps.append("✅ Roles de edad listos")

        await canal.set_permissions(guild.default_role, view_channel=False, send_messages=False)
        await canal.set_permissions(r_quarantine, view_channel=True, send_messages=False, read_messages=True)
        await canal.set_permissions(r_verified, view_channel=True)
        await canal.set_permissions(guild.me, view_channel=True, send_messages=True, embed_links=True)
        steps.append(f"✅ Permisos de #{canal.name} configurados")

        cfg = load_config()
        ob  = cfg.get("onboarding", {})
        ob.update({
            "enabled":            True,
            "channel_id":         str(canal.id),
            "quarantine_role_id": str(r_quarantine.id),
            "verified_role_id":   str(r_verified.id),
            "role_pc":            str(r_pc.id),
            "role_console":       str(r_console.id),
            "role_mobile":        str(r_mobile.id),
            "role_adult":         str(r_adult.id),
            "role_minor":         str(r_minor.id),
        })
        cfg["onboarding"] = ob
        save_config(cfg)

        responses = cfg.get("onboarding_responses", {})
        applied = 0
        for m in guild.members:
            if not m.bot and str(m.id) not in responses and r_quarantine not in m.roles:
                try:
                    await m.add_roles(r_quarantine, reason="Onboarding retroactivo")
                    applied += 1
                except: pass
        if applied: steps.append(f"✅ Cuarentena aplicada a {applied} miembros sin verificar")

        banner = ob.get("banner_url", "")
        ob_embed = discord.Embed(
            title=f"🔐 Verificación — {guild.name}",
            description="¡Bienvenido/a! Para acceder al servidor completa una verificación rápida.\n\nContesta las preguntas para asignarte roles automáticamente (PC/Consola/etc) y darte acceso total.",
            color=0x6366f1
        )
        if banner: ob_embed.set_image(url=banner)
        ob_embed.set_footer(text=f"{guild.name} • Onboarding System")
        await canal.send(embed=ob_embed, view=OnboardingView())
        steps.append(f"✅ Panel enviado a {canal.mention}")

        report = discord.Embed(title="🤖 Setup Completo", description="\n".join(steps), color=0x22c55e)
        report.add_field(
            name="Siguiente paso (Opcional)",
            value="Usa /onboarding-banner [url_del_gif] para poner un GIF/Imagen en el panel\ny vuelve a ejecutar este comando para actualizarlo.",
            inline=False
        )
        await interaction.followup.send(embed=report, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error durante el setup: {e}", ephemeral=True)


@tree.command(name="onboarding-banner", description="🖼️ Establece una imagen/GIF para el panel de onboarding [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def onboarding_banner(interaction: discord.Interaction, url: str):
    cfg = load_config()
    ob  = cfg.get("onboarding", {})
    ob["banner_url"] = url
    cfg["onboarding"] = ob
    save_config(cfg)
    await interaction.response.send_message("✅ Banner guardado. Usa /onboarding-setup para recargar el panel con la nueva imagen.", ephemeral=True)


@tree.command(name="onboarding-send", description="📨 Reenvía el cuestionario a un usuario [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def onboarding_send(interaction: discord.Interaction, usuario: discord.Member):
    if not load_config().get("onboarding", {}).get("enabled"):
        await interaction.response.send_message("❌ El onboarding está desactivado.", ephemeral=True)
        return
    try:
        embed = discord.Embed(title="🔐 Verificación Pendiente", description=f"Hola {usuario.display_name}, tienes verificación pendiente.", color=0xff4747)
        await usuario.send(embed=embed, view=OnboardingView())
        await interaction.response.send_message(f"✅ Cuestionario reenviado a {usuario.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {usuario.mention} tiene los DMs cerrados.", ephemeral=True)


@tree.command(name="onboarding-status", description="📋 Usuarios sin verificar [Admin]")
@app_commands.checks.has_permissions(administrator=True)
async def onboarding_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cfg       = load_config()
    responded = cfg.get("onboarding_responses", {})
    pending   = [m for m in interaction.guild.members if not m.bot and str(m.id) not in responded]
    if not pending:
        await interaction.followup.send("✅ ¡Todos los miembros han completado la verificación!", ephemeral=True)
        return
    embed = discord.Embed(title=f"⏳ Sin Verificar ({len(pending)})", color=0xf59e0b)
    embed.description = "\n".join(f"• {m.mention}" for m in pending[:25])
    if len(pending) > 25: embed.set_footer(text=f"... y {len(pending)-25} más")
    await interaction.followup.send(embed=embed, ephemeral=True)

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
