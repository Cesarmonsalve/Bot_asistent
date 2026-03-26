import re

with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the create_channel condition to support create_category directly
content = content.replace('if act == "create_channel":', 'if act in ["create_channel", "create_category"]:')

# Add explicit support for create_category without relying entirely on type 4 trick
ch_creation = """                    ctype = act_data.get("type", 0)
                    if act == "create_category": ctype = 4"""

content = content.replace('ctype = act_data.get("type", 0)', ch_creation)

# Also support delete_category and edit_category
content = content.replace('elif act == "delete_channel":', 'elif act in ["delete_channel", "delete_category"]:')
content = content.replace('elif act == "edit_channel":', 'elif act in ["edit_channel", "edit_category"]:')

# Support clear_messages
content = content.replace('elif act == "purge_channel":', 'elif act in ["purge_channel", "clear_messages", "clear_channel"]:')

# Support unban_user
ban_user_code = """                elif act == "ban_user":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m: await m.ban(reason=act_data.get("reason")); exec_msgs.append(f"🔨 {m} baneado.")"""

unban_user_code = """                elif act == "ban_user":
                    m = guild.get_member(int(act_data.get("user_id", 0)))
                    if m: await m.ban(reason=act_data.get("reason")); exec_msgs.append(f"🔨 {m} baneado.")

                elif act == "unban_user":
                    uid = int(act_data.get("user_id", 0))
                    try:
                        user = await bot.fetch_user(uid)
                        await guild.unban(user)
                        exec_msgs.append(f"🔓 Usuario {user.name} desbaneado.")
                    except Exception as e:
                        exec_msgs.append(f"❌ Error al desbanear: no encontrado.")"""

content = content.replace(ban_user_code, unban_user_code)

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patching aliases complete!")
