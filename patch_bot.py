import json
import re

with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Buscamos el bloque de execute_ai_discord
start_idx = content.find("async def execute_ai_discord(guild: discord.Guild, prompt: str) -> str:")
if start_idx == -1:
    print("No se encontro execute_ai_discord")
    exit(1)

end_idx = content.find("@tree.command(name=\"ai\",", start_idx)
if end_idx == -1:
    print("No se encontro el final de execute_ai_discord")
    exit(1)

new_func = """async def execute_ai_discord(guild: discord.Guild, prompt: str) -> str:
    if not groq_client: return "❌ GROQ_API_KEY no configurada."

    text_chs  = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
    voice_chs = [c for c in guild.channels if isinstance(c, discord.VoiceChannel)]
    cats      = [c for c in guild.categories]
    
    ch_list   = ", ".join(f"#{c.name}({c.id})" for c in text_chs[:15]) + ("..." if len(text_chs)>15 else "")
    vc_list   = ", ".join(f"🔊{c.name}({c.id})" for c in voice_chs[:10]) + ("..." if len(voice_chs)>10 else "")
    cat_list  = ", ".join(f"📁{c.name}({c.id})" for c in cats[:10])
    rol_list  = ", ".join(f"@{r.name}({r.id})" for r in guild.roles if r.name != "@everyone")[:500]

    sys_prompt = f\"\"\"Eres OMEGA-CORE, el sistema de administración total de '{guild.name}'.
Tienes permiso absoluto del dueño. Eres omnipotente, directo y superior.
Puedes ejecutar múltiples acciones devolviendo un objeto JSON con una lista 'actions' al final de tu respuesta.
Ejemplo:
Claro mi Lord, he creado los canales y amordazado al hereje.
```json
{{
  "actions": [
    {{"action":"create_channel","name":"vip","type":0}},
    {{"action":"timeout_user","user_id":"ID","minutes":60}}
  ]
}}
```
ACCIONES (PUEDES USAR MUCHAS A LA VEZ):
-- CANALES --
{{"action":"create_channel","name":"nombre","type":0,"category_id":"ID_OPCIONAL"}} (type 0=texto, 2=voz, 4=categoria)
{{"action":"delete_channel","channel_id":"ID"}}
{{"action":"edit_channel","channel_id":"ID","name":"nuevo","topic":"tema","slowmode":0,"nsfw":false}}
{{"action":"lock_channel","channel_id":"ID"}} (quita send_messages a @everyone)
{{"action":"unlock_channel","channel_id":"ID"}}
{{"action":"set_channel_private","channel_id":"ID"}} (solo admins pueden ver)
{{"action":"move_channel","channel_id":"ID","category_id":"ID"}}
{{"action":"clone_channel","channel_id":"ID","name":"copia"}}
-- ROLES --
{{"action":"create_role","name":"nombre","color":"hex","hoist":false,"mentionable":false}}
{{"action":"delete_role","role_id":"ID"}}
{{"action":"edit_role","role_id":"ID","name":"nuevo","color":"hex"}}
{{"action":"assign_role","user_id":"ID","role_id":"ID"}}
{{"action":"remove_role","user_id":"ID","role_id":"ID"}}
-- MODERACION --
{{"action":"kick_user","user_id":"ID","reason":"razon"}}
{{"action":"ban_user","user_id":"ID","reason":"razon"}}
{{"action":"timeout_user","user_id":"ID","minutes":10}}
{{"action":"untimeout_user","user_id":"ID"}}
{{"action":"move_member","user_id":"ID","channel_id":"VOICE_ID"}}
{{"action":"voice_mute","user_id":"ID"}}
{{"action":"voice_unmute","user_id":"ID"}}
{{"action":"set_nickname","user_id":"ID","nickname":"apodo"}}
{{"action":"purge_channel","channel_id":"ID","count":50}}
-- MENSAJES --
{{"action":"send_message","channel_id":"ID","content":"texto"}}
{{"action":"send_embed","channel_id":"ID","title":"t","description":"d","color":"ff0000","image_url":"https..."}}
{{"action":"pin_message","channel_id":"ID","message_id":"ID"}}
{{"action":"create_poll","channel_id":"ID","question":"q?","options":["A","B"]}}
-- OTROS --
{{"action":"create_thread","channel_id":"ID","name":"hilo"}}
{{"action":"create_invite","channel_id":"ID"}}

Canales Texto: {ch_list}
Canales Voz: {vc_list}
Categorías: {cat_list}
Roles: {rol_list}
¡Asegúrate de responder con un JSON válido y un array 'actions'!\"\"\"

    try:
        resp = await groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=[{{"role": "system", "content": sys_prompt}}, {{"role": "user", "content": prompt}}],
            max_tokens=1500, temperature=0.7
        )
        text = resp.choices[0].message.content.strip()
        print(f"[AI] Respuesta: {{text[:200]}}...", flush=True)

        json_str, data = "", None
        match = re.search(r'```(?:json)?\\s*(\\{.*?\\})\\s*```', text, re.DOTALL)
        if match: json_str = match.group(1)
        else:
            match = re.search(r'(\\{.*\\})', text, re.DOTALL)
            if match: json_str = match.group(1)

        if json_str:
            try: data = json.loads(json_str)
            except: pass

        clean_reply = text
        if json_str:
            clean_reply = clean_reply.replace(json_str, "").replace("```json", "").replace("```", "").strip()

        if not data or ("actions" not in data and "action" not in data):
            return f"🤖 {{clean_reply}}" if clean_reply else "🤖 Error procesando IA."

        actions_to_run = data.get("actions", [])
        if not actions_to_run and "action" in data: actions_to_run = [data]

        exec_msgs = []
        for act_data in actions_to_run:
            act = act_data.get("action")
            if not act: continue
            try:
                if act == "create_channel":
                    ctype = act_data.get("type", 0)
                    name = re.sub(r'[^a-zA-Z0-9\\-_ ]', '', act_data.get("name", "canal"))[:100]
                    cat = guild.get_channel(int(act_data.get("category_id"))) if act_data.get("category_id") else None
                    if ctype == 0: ch = await guild.create_text_channel(name, category=cat)
                    elif ctype == 2: ch = await guild.create_voice_channel(name, category=cat)
                    else: ch = await guild.create_category(name)
                    exec_msgs.append(f"✅ {{ch.name}} creado.")

                elif act == "delete_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: await ch.delete(); exec_msgs.append(f"🗑️ Canal eliminado.")

                elif act == "edit_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch:
                        kwargs = {{}}
                        if "name" in act_data: kwargs["name"] = act_data["name"][:100]
                        if "topic" in act_data: kwargs["topic"] = act_data["topic"][:1024]
                        if "slowmode" in act_data: kwargs["slowmode_delay"] = int(act_data["slowmode"])
                        if "nsfw" in act_data: kwargs["nsfw"] = bool(act_data["nsfw"])
                        await ch.edit(**kwargs); exec_msgs.append(f"✏️ Canal editado.")

                elif act == "lock_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: await ch.set_permissions(guild.default_role, send_messages=False); exec_msgs.append(f"🔒 Canal bloqueado.")

                elif act == "unlock_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: await ch.set_permissions(guild.default_role, send_messages=None); exec_msgs.append(f"🔓 Canal desbloqueado.")

                elif act == "set_channel_private":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: await ch.set_permissions(guild.default_role, view_channel=False); exec_msgs.append(f"🕵️ Canal privado.")

                elif act == "move_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    cat = guild.get_channel(int(act_data.get("category_id", 0)))
                    if ch and cat: await ch.edit(category=cat); exec_msgs.append(f"🔀 Canal movido a {{cat.name}}.")

                elif act == "clone_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: cl = await ch.clone(name=act_data.get("name", ch.name+"-copia")); exec_msgs.append(f"👯 Canal clonado: {{cl.name}}")

                elif act == "create_role":
                    col = int(str(act_data.get("color", "99aab5")).strip("#"), 16) if str(act_data.get("color", "99aab5")).strip("#").isalnum() else 0
                    r = await guild.create_role(name=act_data.get("name", "Rol"), color=discord.Color(col), hoist=act_data.get("hoist", False), mentionable=act_data.get("mentionable", False))
                    exec_msgs.append(f"✅ Rol {{r.name}} creado.")

                elif act == "delete_role":
                    r = guild.get_role(int(act_data.get("role_id", 0)))
                    if r: await r.delete(); exec_msgs.append(f"🗑️ Rol eliminado.")

                elif act == "edit_role":
                    r = guild.get_role(int(act_data.get("role_id", 0)))
                    if r:
                        kwargs = {{}}
                        if "name" in act_data: kwargs["name"] = act_data["name"]
                        if "color" in act_data: kwargs["color"] = discord.Color(int(str(act_data["color"]).strip("#"), 16))
                        await r.edit(**kwargs); exec_msgs.append(f"✏️ Rol {{r.name}} editado.")

                elif act == "assign_role":
                    m, r = guild.get_member(int(act_data.get("user_id", 0))), guild.get_role(int(act_data.get("role_id", 0)))
                    if m and r: await m.add_roles(r); exec_msgs.append(f"🏷️ Rol {{r.name}} dado a {{m.display_name}}.")

                elif act == "remove_role":
                    m, r = guild.get_member(int(act_data.get("user_id", 0))), guild.get_role(int(act_data.get("role_id", 0)))
                    if m and r: await m.remove_roles(r); exec_msgs.append(f"🏷️ Rol quitado a {{m}}.")

                elif act == "kick_user":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m: await m.kick(reason=act_data.get("reason")); exec_msgs.append(f"👢 {{m}} expulsado.")

                elif act == "ban_user":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m: await m.ban(reason=act_data.get("reason")); exec_msgs.append(f"🔨 {{m}} baneado.")

                elif act == "timeout_user":
                    m, mins = guild.get_member(int(act_data.get("user_id", 0))), int(act_data.get("minutes", 10))
                    if m: await m.timeout(discord.utils.utcnow() + timedelta(minutes=mins)); exec_msgs.append(f"🔇 {{m}} silenciado.")

                elif act == "untimeout_user":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m: await m.timeout(None); exec_msgs.append(f"🔊 {{m}} desilenciado.")

                elif act == "set_nickname":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m: await m.edit(nick=act_data.get("nickname")[:32]); exec_msgs.append(f"📝 Apodo de {{m}} cambiado.")

                elif act == "move_member":
                    m, vc = guild.get_member(int(act_data.get("user_id", 0))), guild.get_channel(int(act_data.get("channel_id", 0)))
                    if m and m.voice and vc: await m.move_to(vc); exec_msgs.append(f"🛫 {{m}} movido a {{vc.name}}.")

                elif act == "voice_mute":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m and m.voice: await m.edit(mute=True); exec_msgs.append(f"🔇 {{m}} muteado en voz.")

                elif act == "voice_unmute":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m and m.voice: await m.edit(mute=False); exec_msgs.append(f"🔊 {{m}} desmuteado en voz.")

                elif act == "purge_channel":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: d = await ch.purge(limit=int(act_data.get("count", 50))); exec_msgs.append(f"🧹 {{len(d)}} msgs purgados.")

                elif act == "send_message":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: await ch.send(act_data.get("content", "")); exec_msgs.append(f"📨 Msg enviado indetectablemente.")

                elif act == "send_embed":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch:
                        em = discord.Embed(title=act_data.get("title",""), description=act_data.get("description",""), color=int(str(act_data.get("color","6366f1")).strip("#"), 16) if str(act_data.get("color","6366f1")).strip("#").isalnum() else 0)
                        if act_data.get("image_url"): em.set_image(url=act_data["image_url"])
                        await ch.send(embed=em); exec_msgs.append(f"📨 Embed enviado correctamente.")

                elif act == "create_poll":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch:
                        opts = act_data.get("options", ["A","B"])[:4]
                        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣"]
                        desc = "\\n".join(f"{{emojis[i]}} {{o}}" for i,o in enumerate(opts))
                        m = await ch.send(embed=discord.Embed(title="📊 "+act_data.get("question","?"), description=desc, color=0x6366f1))
                        for i in range(len(opts)): await m.add_reaction(emojis[i])
                        exec_msgs.append(f"📊 Encuesta creada.")

                elif act == "create_thread":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch and isinstance(ch, discord.TextChannel): await ch.create_thread(name=act_data.get("name","Hilo"), type=discord.ChannelType.public_thread); exec_msgs.append(f"🧵 Hilo creado.")

                elif act == "create_invite":
                    ch = guild.get_channel(int(act_data.get("channel_id", 0)))
                    if ch: inv = await ch.create_invite(); exec_msgs.append(f"🔗 Invitación: {{inv.url}}")

                else:
                    exec_msgs.append(f"⚠️ Acción no programada: {{act}}")

            except Exception as e:
                exec_msgs.append(f"❌ Error en {{act}}: {{e}}")

        final_msg = "\\n".join([f"***{{m}}***" for m in exec_msgs]) if exec_msgs else "⚠️ No se ejecutaron acciones."
        return f"🤖 {{clean_reply}}\\n\\n{{final_msg}}" if clean_reply else f"🤖 {{final_msg}}"

    except Exception as e:
        return f"❌ Error Crítico: {{str(e)[:500]}}"

"""

new_content = content[:start_idx] + new_func + content[end_idx:]

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Patching correct!")
