import customtkinter as ctk
import psycopg2
from psycopg2.extras import Json
import json, os, threading, requests
import tkinter as tk
from tkinter import messagebox

# ─── CONFIGURACIÓN VISUAL ───
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ─── DISCORD REST API CLIENT ───
class DiscordAPI:
    def __init__(self, token, guild_id):
        self.token = token.strip()
        self.guild_id = str(guild_id).strip()
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

    def get_guild(self):
        r = requests.get(f"{self.base_url}/guilds/{self.guild_id}?with_counts=true", headers=self.headers)
        if r.status_code == 200: return r.json()
        raise Exception(f"Error {r.status_code}: {r.text}")

    def get_channels(self):
        r = requests.get(f"{self.base_url}/guilds/{self.guild_id}/channels", headers=self.headers)
        if r.status_code == 200: return r.json()
        raise Exception("Error cargando canales")

    def create_channel(self, name, type_id, parent_id=None):
        data = {"name": name, "type": type_id}
        if parent_id: data["parent_id"] = str(parent_id)
        r = requests.post(f"{self.base_url}/guilds/{self.guild_id}/channels", headers=self.headers, json=data)
        if r.status_code not in [200, 201]: raise Exception(r.text)

    def delete_channel(self, channel_id):
        r = requests.delete(f"{self.base_url}/channels/{channel_id}", headers=self.headers)
        if r.status_code != 200: raise Exception(r.text)

    def get_roles(self):
        r = requests.get(f"{self.base_url}/guilds/{self.guild_id}/roles", headers=self.headers)
        if r.status_code == 200: return r.json()
        raise Exception("Error cargando roles")

    def create_role(self, name, color_hex):
        color_int = int(color_hex.lstrip('#'), 16) if color_hex else 0
        r = requests.post(f"{self.base_url}/guilds/{self.guild_id}/roles", headers=self.headers, json={"name": name, "color": color_int})
        if r.status_code != 200: raise Exception(r.text)

    def send_embed(self, channel_id, title, desc, color_hex, image_url):
        color_int = int(color_hex.lstrip('#'), 16) if color_hex else 0x4f46e5
        embed = {"title": title, "description": desc, "color": color_int}
        if image_url: embed["image"] = {"url": image_url}
        r = requests.post(f"{self.base_url}/channels/{channel_id}/messages", headers=self.headers, json={"embeds": [embed]})
        if r.status_code != 200: raise Exception(r.text)

# ─── APLICACIÓN PRINCIPAL ───
class OmegaAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("👑 OMEGA ASSISTANT - Control Maestro del Servidor")
        self.geometry("1300x800")
        
        self.config_data = {}
        self.api = None
        self.cached_channels = []
        self.cached_roles = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ─── STORAGE LOCAL (Credenciales) ───
        self.creds_file = ".env.omega"
        self.db_url, self.bot_token, self.guild_id = self.load_local_creds()

        # ─── SIDEBAR ───
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(self.sidebar, text="🛡️ OMEGA", font=ctk.CTkFont(size=26, weight="bold"), text_color="#3b82f6").grid(row=0, column=0, pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="ASSISTANT", font=ctk.CTkFont(size=14)).grid(row=1, column=0, pady=(0, 20))

        # Botones Menú
        menus = [
            ("🔌 Conexión Maestra", "Credenciales"),
            ("📊 Análisis en Vivo", "Dashboard"),
            ("🏗️ Arquitectura (Canales)", "Arquitectura"),
            ("🏷️ Gestión de Roles", "Roles"),
            ("📢 Anuncios Directos", "Notificaciones"),
            ("⚙️ Configuración del Bot", "ConfigBot")
        ]
        
        self.nav_btns = {}
        for i, (text, name) in enumerate(menus, start=2):
            btn = ctk.CTkButton(self.sidebar, text=text, anchor="w", command=lambda n=name: self.show_frame(n), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"))
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=5)
            self.nav_btns[name] = btn

        # ─── FRAMES ───
        self.frames = {}
        
        self.init_creds_frame()
        self.init_dashboard_frame()
        self.init_architecture_frame()
        self.init_roles_frame()
        self.init_notifications_frame()
        self.init_configbot_frame()

        self.btn_save_db = ctk.CTkButton(self, text="💾 GUARDAR CONFIGURACIÓN DB", fg_color="#22c55e", hover_color="#16a34a", height=50, font=ctk.CTkFont(weight="bold"), command=self.save_to_db)
        self.btn_save_db.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        # Iniciar validando credenciales
        if self.db_url and self.bot_token and self.guild_id:
            self.connect_all()
            self.show_frame("Dashboard")
        else:
            self.show_frame("Credenciales")

    # ─── HELPERS ───
    def load_local_creds(self):
        if os.path.exists(self.creds_file):
            try:
                with open(self.creds_file, "r") as f:
                    d = json.load(f)
                    return d.get("db", ""), d.get("token", ""), d.get("guild", "")
            except: pass
        return "", "", ""

    def save_local_creds(self):
        with open(self.creds_file, "w") as f:
            json.dump({"db": self.db_url, "token": self.bot_token, "guild": self.guild_id}, f)

    def show_frame(self, name):
        for btn in self.nav_btns.values(): btn.configure(fg_color="transparent")
        self.nav_btns[name].configure(fg_color=("gray75", "gray25"))
        for frame in self.frames.values(): frame.grid_forget()
        self.frames[name].grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    # ─── FRAMES INIT ───
    def init_creds_frame(self):
        f = ctk.CTkFrame(self)
        self.frames["Credenciales"] = f
        
        ctk.CTkLabel(f, text="🔑 Credenciales de Poder Absoluto", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=30)
        
        ctk.CTkLabel(f, text="URL Externa Base de Datos (PostgreSQL):").pack(pady=5)
        self.e_db = ctk.CTkEntry(f, width=500)
        self.e_db.insert(0, self.db_url)
        self.e_db.pack(pady=5)

        ctk.CTkLabel(f, text="Discord Bot Token:").pack(pady=5)
        self.e_tok = ctk.CTkEntry(f, width=500, show="*")
        self.e_tok.insert(0, self.bot_token)
        self.e_tok.pack(pady=5)

        ctk.CTkLabel(f, text="ID del Servidor (Guild ID):").pack(pady=5)
        self.e_gui = ctk.CTkEntry(f, width=300)
        self.e_gui.insert(0, self.guild_id)
        self.e_gui.pack(pady=5)

        ctk.CTkButton(f, text="Conectar y Guardar", command=self.action_connect_all).pack(pady=20)
        self.lbl_conn_status = ctk.CTkLabel(f, text="", font=ctk.CTkFont(weight="bold"))
        self.lbl_conn_status.pack(pady=10)

    def init_dashboard_frame(self):
        f = ctk.CTkFrame(self)
        self.frames["Dashboard"] = f
        
        self.dash_title = ctk.CTkLabel(f, text="Estadísticas de [Conecta primero]", font=ctk.CTkFont(size=28, weight="bold"), text_color="#3b82f6")
        self.dash_title.pack(pady=20)

        stats_frame = ctk.CTkFrame(f, fg_color="transparent")
        stats_frame.pack(pady=20, fill="x", padx=50)

        self.l_members = ctk.CTkLabel(stats_frame, text="👥 Miembros\n--", font=ctk.CTkFont(size=20))
        self.l_members.pack(side="left", expand=True)
        
        self.l_channels = ctk.CTkLabel(stats_frame, text="💬 Canales\n--", font=ctk.CTkFont(size=20))
        self.l_channels.pack(side="left", expand=True)
        
        self.l_roles = ctk.CTkLabel(stats_frame, text="🏷️ Roles\n--", font=ctk.CTkFont(size=20))
        self.l_roles.pack(side="left", expand=True)

        ctk.CTkButton(f, text="🔄 Actualizar Datos", command=self.refresh_dashboard).pack(pady=40)

    def init_architecture_frame(self):
        f = ctk.CTkFrame(self)
        self.frames["Arquitectura"] = f
        
        ctk.CTkLabel(f, text="🏗️ Arquitectura del Servidor", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)
        
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=10)
        
        self.c_type = ctk.CTkOptionMenu(top, values=["Canal de Texto", "Canal de Voz", "Categoría"])
        self.c_type.pack(side="left", padx=10)
        
        self.c_name = ctk.CTkEntry(top, placeholder_text="Nombre...", width=200)
        self.c_name.pack(side="left", padx=10)
        
        ctk.CTkButton(top, text="➕ Crear Mágicamente", fg_color="#3b82f6", hover_color="#2563eb", command=self.action_create_channel).pack(side="left", padx=10)
        ctk.CTkButton(top, text="🔄 Recargar Lista", command=self.refresh_channels).pack(side="right", padx=10)

        self.ch_scroll = ctk.CTkScrollableFrame(f)
        self.ch_scroll.pack(fill="both", expand=True, padx=20, pady=10)

    def init_roles_frame(self):
        f = ctk.CTkFrame(self)
        self.frames["Roles"] = f
        
        ctk.CTkLabel(f, text="🏷️ Gestión de Roles Suprema", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)
        
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=10)
        
        self.r_name = ctk.CTkEntry(top, placeholder_text="Nombre del nuevo rol...", width=200)
        self.r_name.pack(side="left", padx=10)
        
        self.r_color = ctk.CTkEntry(top, placeholder_text="HexColor (Ej: #ff0000)", width=150)
        self.r_color.pack(side="left", padx=10)
        
        ctk.CTkButton(top, text="➕ Crear Rol", fg_color="#a855f7", hover_color="#9333ea", command=self.action_create_role).pack(side="left", padx=10)
        ctk.CTkButton(top, text="🔄 Recargar Lista", command=self.refresh_roles).pack(side="right", padx=10)

        self.rl_scroll = ctk.CTkScrollableFrame(f)
        self.rl_scroll.pack(fill="both", expand=True, padx=20, pady=10)

    def init_notifications_frame(self):
        f = ctk.CTkFrame(self)
        self.frames["Notificaciones"] = f
        
        ctk.CTkLabel(f, text="📢 Enviar Anuncio Mundial", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(f, text="Selecciona el Canal Destino:").pack()
        self.n_channel = ctk.CTkOptionMenu(f, values=["Cargando canales..."], width=300)
        self.n_channel.pack(pady=5)
        
        ctk.CTkLabel(f, text="Título del Embed:").pack(pady=(10, 0))
        self.n_title = ctk.CTkEntry(f, width=400)
        self.n_title.pack(pady=5)
        
        ctk.CTkLabel(f, text="Descripción del Mensaje:").pack(pady=(10, 0))
        self.n_desc = ctk.CTkTextbox(f, width=400, height=150)
        self.n_desc.pack(pady=5)
        
        ctk.CTkLabel(f, text="Color Hexadecimal (Ej: #22c55e):").pack(pady=(10, 0))
        self.n_color = ctk.CTkEntry(f, width=200)
        self.n_color.pack(pady=5)
        
        ctk.CTkLabel(f, text="URL de Imagen (Opcional):").pack(pady=(10, 0))
        self.n_img = ctk.CTkEntry(f, width=400)
        self.n_img.pack(pady=5)

        ctk.CTkButton(f, text="🚀 ENVIAR ANUNCIO A DISCORD", fg_color="#f59e0b", hover_color="#d97706", height=40, command=self.action_send_embed).pack(pady=20)

    def init_configbot_frame(self):
        f = ctk.CTkScrollableFrame(self)
        self.frames["ConfigBot"] = f
        
        ctk.CTkLabel(f, text="⚙️ Configuración DB Interna del Bot", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        # Mod
        ctk.CTkLabel(f, text="🛡 Moderación Automática", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5))
        self.mod_anti_links = ctk.CTkSwitch(f, text="Anti-Links")
        self.mod_anti_links.pack()
        self.mod_anti_spam = ctk.CTkSwitch(f, text="Anti-Spam")
        self.mod_anti_spam.pack(pady=5)
        self.mod_words = ctk.CTkEntry(f, width=400, placeholder_text="Palabras prohibidas (separadas por coma)")
        self.mod_words.pack()

        # Onboarding
        ctk.CTkLabel(f, text="✅ Onboarding Inteligente", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5))
        self.onb_enabled = ctk.CTkSwitch(f, text="Activar Onboarding")
        self.onb_enabled.pack()
        self.onb_role = ctk.CTkEntry(f, width=300, placeholder_text="ID del Rol de Verificado")
        self.onb_role.pack(pady=5)

        # Welcome
        ctk.CTkLabel(f, text="👋 Bienvenidas y Logros", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5))
        self.welc_enabled = ctk.CTkSwitch(f, text="Mensajes de Bienvenida por IA")
        self.welc_enabled.pack()
        self.welc_channel = ctk.CTkEntry(f, width=300, placeholder_text="ID del Canal de Bienvenida")
        self.welc_channel.pack(pady=5)
        
        self.xp_enabled = ctk.CTkSwitch(f, text="Activar Sistema de XP y Leaderboard")
        self.xp_enabled.pack(pady=5)

    # ─── LOGIC & DB ───
    def action_connect_all(self):
        self.db_url = self.e_db.get().strip()
        self.bot_token = self.e_tok.get().strip()
        self.guild_id = self.e_gui.get().strip()
        self.save_local_creds()
        self.connect_all()

    def connect_all(self):
        self.api = DiscordAPI(self.bot_token, self.guild_id)
        self.lbl_conn_status.configure(text="Sincronizando con Universo Discord...", text_color="#f59e0b")
        self.run_in_thread(self._thread_connect)

    def _thread_connect(self):
        try:
            # Test Discord API
            guild = self.api.get_guild()
            server_name = guild.get('name', 'Servidor')
            
            # Test Database
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS bot_settings (id VARCHAR(10) PRIMARY KEY, data JSONB)")
            conn.commit()
            cur.execute("SELECT data FROM bot_settings WHERE id = 'main'")
            row = cur.fetchone()
            if row: self.config_data = row[0]
            else: self.config_data = {}
            cur.close()
            conn.close()

            # Success
            self.after(0, lambda: self.lbl_conn_status.configure(text=f"✅ CONEXIÓN ESTABLECIDA CON ÉXITO", text_color="#22c55e"))
            self.after(0, lambda: self.dash_title.configure(text=f"Estadísticas de {server_name}"))
            self.after(0, self.populate_ui)
            self.after(0, self.refresh_dashboard)
            self.after(0, self.refresh_channels)
            self.after(0, self.refresh_roles)

        except Exception as e:
            self.after(0, lambda: self.lbl_conn_status.configure(text=f"❌ Error CRÍTICO:\n{e}", text_color="#ef4444"))

    def populate_ui(self):
        c = self.config_data
        mod = c.get("moderation", {})
        self.mod_anti_links.select() if mod.get("anti_links") else self.mod_anti_links.deselect()
        self.mod_anti_spam.select() if mod.get("anti_spam") else self.mod_anti_spam.deselect()
        self.mod_words.delete(0, 'end')
        self.mod_words.insert(0, ", ".join(c.get("word_filter", {}).get("words", [])))
        
        onb = c.get("onboarding", {})
        self.onb_enabled.select() if onb.get("enabled") else self.onb_enabled.deselect()
        self.onb_role.delete(0, 'end')
        self.onb_role.insert(0, str(onb.get("verified_role_id", "")))
        
        welc = c.get("welcome", {})
        self.welc_enabled.select() if welc.get("enabled") else self.welc_enabled.deselect()
        self.welc_channel.delete(0, 'end')
        self.welc_channel.insert(0, str(welc.get("channel_id", "")))
        
        self.xp_enabled.select() if c.get("xp", {}).get("enabled") else self.xp_enabled.deselect()

    def save_to_db(self):
        if not self.db_url: return messagebox.showerror("Error", "No has colocado la URL de DB")
        c = self.config_data
        
        if "moderation" not in c: c["moderation"] = {}
        c["moderation"]["anti_links"] = bool(self.mod_anti_links.get())
        c["moderation"]["anti_spam"] = bool(self.mod_anti_spam.get())
        
        if "word_filter" not in c: c["word_filter"] = {}
        c["word_filter"]["enabled"] = len(self.mod_words.get().strip()) > 0
        c["word_filter"]["words"] = [w.strip() for w in self.mod_words.get().split(",") if w.strip()]
        
        if "onboarding" not in c: c["onboarding"] = {}
        c["onboarding"]["enabled"] = bool(self.onb_enabled.get())
        c["onboarding"]["verified_role_id"] = self.onb_role.get().strip()
        
        if "welcome" not in c: c["welcome"] = {}
        c["welcome"]["enabled"] = bool(self.welc_enabled.get())
        c["welcome"]["channel_id"] = self.welc_channel.get().strip()
        
        if "xp" not in c: c["xp"] = {}
        c["xp"]["enabled"] = bool(self.xp_enabled.get())

        def _save():
            try:
                conn = psycopg2.connect(self.db_url)
                cur = conn.cursor()
                cur.execute("INSERT INTO bot_settings (id, data) VALUES ('main', %s) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data", (Json(c),))
                conn.commit()
                cur.close()
                conn.close()
                self.after(0, lambda: messagebox.showinfo("Guardado", "Configuración Puesta en Orbita. Bot actualizado."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        self.run_in_thread(_save)

    # ─── DISCORD API ACTIONS ───
    def refresh_dashboard(self):
        def _fetch():
            try:
                g = self.api.get_guild()
                c = self.api.get_channels()
                r = self.api.get_roles()
                members = g.get("approximate_member_count", 0)
                self.after(0, lambda: self.l_members.configure(text=f"👥 Miembros\n{members}"))
                self.after(0, lambda: self.l_channels.configure(text=f"💬 Canales\n{len(c)}"))
                self.after(0, lambda: self.l_roles.configure(text=f"🏷️ Roles\n{len(r)}"))
            except: pass
        self.run_in_thread(_fetch)

    def refresh_channels(self):
        def _fetch():
            try:
                self.cached_channels = self.api.get_channels()
                self.after(0, self._render_channels)
            except Exception as e: print("Channel fetch error:", e)
        self.run_in_thread(_fetch)

    def _render_channels(self):
        for widget in self.ch_scroll.winfo_children(): widget.destroy()
        
        # Opciones para el Notificador
        text_channels = [f"{c['name']} ({c['id']})" for c in self.cached_channels if c['type'] == 0]
        self.n_channel.configure(values=text_channels if text_channels else ["Sin Canales"])
        if text_channels: self.n_channel.set(text_channels[0])

        categories = sorted([c for c in self.cached_channels if c['type'] == 4], key=lambda x: x.get('position', 0))
        others = [c for c in self.cached_channels if c['type'] != 4]

        # Render categories and their children
        for cat in categories:
            cat_frame = ctk.CTkFrame(self.ch_scroll, fg_color="gray20")
            cat_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(cat_frame, text=f"📁 {cat['name']}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=5)
            ctk.CTkButton(cat_frame, text="Eliminar", width=60, fg_color="#ef4444", hover_color="#b91c1c", command=lambda cid=cat['id']: self.action_delete_channel(cid)).pack(side="right", padx=5, pady=5)
            
            children = sorted([c for c in others if c.get('parent_id') == cat['id']], key=lambda x: x.get('position', 0))
            for child in children:
                ch_frame = ctk.CTkFrame(self.ch_scroll, fg_color="transparent")
                ch_frame.pack(fill="x", pady=1, padx=(30, 0))
                icon = "💬" if child['type'] == 0 else "🔊"
                ctk.CTkLabel(ch_frame, text=f"{icon} {child['name']}").pack(side="left", padx=10)
                ctk.CTkButton(ch_frame, text="Eliminar", width=50, fg_color="#ef4444", hover_color="#b91c1c", height=20, command=lambda cid=child['id']: self.action_delete_channel(cid)).pack(side="right", padx=5)

    def action_create_channel(self):
        name = self.c_name.get().strip()
        if not name: return
        t_str = self.c_type.get()
        t_id = 0 if t_str == "Canal de Texto" else 2 if t_str == "Canal de Voz" else 4
        def _create():
            try:
                self.api.create_channel(name, t_id)
                self.after(0, lambda: self.c_name.delete(0, 'end'))
                self.refresh_channels()
                self.refresh_dashboard()
            except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))
        self.run_in_thread(_create)

    def action_delete_channel(self, channel_id):
        if not messagebox.askyesno("Confirmar", "¿Eliminar esto de Discord irrevocablemente?"): return
        def _delete():
            try:
                self.api.delete_channel(channel_id)
                self.refresh_channels()
                self.refresh_dashboard()
            except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))
        self.run_in_thread(_delete)

    def refresh_roles(self):
        def _fetch():
            try:
                self.cached_roles = self.api.get_roles()
                self.after(0, self._render_roles)
            except: pass
        self.run_in_thread(_fetch)

    def _render_roles(self):
        for widget in self.rl_scroll.winfo_children(): widget.destroy()
        roles = sorted(self.cached_roles, key=lambda x: x.get('position', 0), reverse=True)
        for r in roles:
            if r['name'] == "@everyone": continue
            f = ctk.CTkFrame(self.rl_scroll)
            f.pack(fill="x", pady=2)
            color_hex = f"#{r['color']:06x}" if r.get('color') else "gray"
            ctk.CTkLabel(f, text="●", text_color=color_hex, font=ctk.CTkFont(size=20)).pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"{r['name']} (ID: {r['id']})").pack(side="left", padx=5)

    def action_create_role(self):
        name = self.r_name.get().strip()
        color = self.r_color.get().strip()
        if not name: return
        def _create():
            try:
                self.api.create_role(name, color)
                self.after(0, lambda: self.r_name.delete(0, 'end'))
                self.after(0, lambda: self.r_color.delete(0, 'end'))
                self.refresh_roles()
                self.refresh_dashboard()
            except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))
        self.run_in_thread(_create)

    def action_send_embed(self):
        ch_str = self.n_channel.get()
        if "Cargando" in ch_str or "Sin Canales" in ch_str: return
        try:
            ch_id = ch_str.split("(")[-1].replace(")", "").strip()
            title = self.n_title.get()
            desc = self.n_desc.get("1.0", "end").strip()
            color = self.n_color.get()
            img = self.n_img.get().strip()
            if not desc: return messagebox.showerror("Error", "La descripción está vacía.")
            
            def _send():
                try:
                    self.api.send_embed(ch_id, title, desc, color, img)
                    self.after(0, lambda: messagebox.showinfo("Enviado", "Anuncio enviado exitosamente con poder de Administrador API."))
                    self.after(0, lambda: self.n_desc.delete("1.0", "end"))
                except Exception as e: self.after(0, lambda: messagebox.showerror("Error al enviar", str(e)))
            self.run_in_thread(_send)
        except Exception as e:
            messagebox.showerror("Error", "Error procesando el canal destino.")

if __name__ == "__main__":
    app = OmegaAssistantApp()
    app.mainloop()
