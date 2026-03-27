import customtkinter as ctk
import psycopg2
from psycopg2.extras import Json
import json
import tkinter as tk
from tkinter import messagebox
import threading

# Configuración Inicial Premium
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🚀 The Family - Mega Admin PC Panel")
        self.geometry("1100x700")
        self.config_data = {}
        
        # Grid general
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ─── SIDEBAR NAVEGACIÓN ───
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🛡️ OMEGA CORE", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="📊 Dashboard", command=lambda: self.select_frame("Dashboard"))
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)

        self.btn_mod = ctk.CTkButton(self.sidebar_frame, text="⚔️ Moderación", command=lambda: self.select_frame("Moderacion"))
        self.btn_mod.grid(row=2, column=0, padx=20, pady=10)

        self.btn_onboard = ctk.CTkButton(self.sidebar_frame, text="✅ Onboarding", command=lambda: self.select_frame("Onboarding"))
        self.btn_onboard.grid(row=3, column=0, padx=20, pady=10)

        self.btn_welcome = ctk.CTkButton(self.sidebar_frame, text="👋 Bienvenidas/XP", command=lambda: self.select_frame("Welcome"))
        self.btn_welcome.grid(row=4, column=0, padx=20, pady=10)

        # Configurar Conexión DB en la UI
        self.db_label = ctk.CTkLabel(self.sidebar_frame, text="Database External URL:", font=ctk.CTkFont(size=12))
        self.db_label.grid(row=8, column=0, padx=20, pady=(0, 5))
        
        self.db_entry = ctk.CTkEntry(self.sidebar_frame, width=180, placeholder_text="Pega la URL de Postgres (External/Public)")
        self.db_entry.grid(row=9, column=0, padx=20, pady=(0, 10))
        
        self.btn_connect = ctk.CTkButton(self.sidebar_frame, text="🔗 Conectar BD", fg_color="#22c55e", hover_color="#16a34a", command=self.load_from_db)
        self.btn_connect.grid(row=10, column=0, padx=20, pady=(0, 20))

        # ─── FRAMES PRINCIPALES ───
        self.frames = {}

        # 1. Dashboard
        frame_dash = ctk.CTkFrame(self, corner_radius=10)
        ctk.CTkLabel(frame_dash, text="Bienvenido al Panel de Control Supremo", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=40)
        ctk.CTkLabel(frame_dash, text="Este programa conecta directamente con tu Bot en Railway las 24/7.\nUsa el menú lateral para modificar las reglas y sistemas del servidor.", font=ctk.CTkFont(size=16)).pack(pady=10)
        
        self.status_label = ctk.CTkLabel(frame_dash, text="🔴 Estado: Desconectado de la Base de Datos", text_color="#ef4444", font=ctk.CTkFont(size=18, weight="bold"))
        self.status_label.pack(pady=30)

        self.frames["Dashboard"] = frame_dash

        # 2. Moderación
        frame_mod = ctk.CTkFrame(self, corner_radius=10)
        ctk.CTkLabel(frame_mod, text="Ajustes de Moderación", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        self.mod_anti_links = ctk.CTkSwitch(frame_mod, text="Activar Anti-Links")
        self.mod_anti_links.pack(pady=10)
        self.mod_anti_spam = ctk.CTkSwitch(frame_mod, text="Activar Anti-Spam")
        self.mod_anti_spam.pack(pady=10)

        ctk.CTkLabel(frame_mod, text="Palabras Baneadas (separadas por comas)").pack(pady=(20, 5))
        self.mod_words = ctk.CTkEntry(frame_mod, width=400, placeholder_text="ejemplo: palabra1, palabra2")
        self.mod_words.pack(pady=5)

        self.frames["Moderacion"] = frame_mod

        # 3. Onboarding
        frame_onb = ctk.CTkFrame(self, corner_radius=10)
        ctk.CTkLabel(frame_onb, text="Sistema de Verificación Autónoma", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        self.onb_enabled = ctk.CTkSwitch(frame_onb, text="Habilitar Onboarding")
        self.onb_enabled.pack(pady=10)

        ctk.CTkLabel(frame_onb, text="Rol de Verificado (ID)").pack(pady=5)
        self.onb_role = ctk.CTkEntry(frame_onb, width=300)
        self.onb_role.pack(pady=5)

        self.frames["Onboarding"] = frame_onb
        
        # 4. Welcomes
        frame_welc = ctk.CTkFrame(self, corner_radius=10)
        ctk.CTkLabel(frame_welc, text="Bienvenidas y Sistema XP", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        self.welc_enabled = ctk.CTkSwitch(frame_welc, text="Habilitar Bienvenidas de Inteligencia Artificial")
        self.welc_enabled.pack(pady=10)
        ctk.CTkLabel(frame_welc, text="Canal de Bienvenidas (ID)").pack(pady=5)
        self.welc_channel = ctk.CTkEntry(frame_welc, width=300)
        self.welc_channel.pack(pady=5)
        
        self.xp_enabled = ctk.CTkSwitch(frame_welc, text="Habilitar Sistema de XP / Niveles")
        self.xp_enabled.pack(pady=(30, 10))

        self.frames["Welcome"] = frame_welc

        # Botón Universal Guardar Cambios
        self.btn_save_all = ctk.CTkButton(self, text="💾 GUARDAR Y APLICAR AL BOT", fg_color="#4f46e5", hover_color="#4338ca", font=ctk.CTkFont(weight="bold", size=16), height=50, command=self.save_to_db)
        self.btn_save_all.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        # Iniciar en Home
        self.select_frame("Dashboard")

    def select_frame(self, name):
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    def get_db_connection(self):
        url = self.db_entry.get().strip()
        if not url:
            raise ValueError("Por favor, ingresa la URL de la base de datos.")
        return psycopg2.connect(url)

    def load_from_db(self):
        try:
            self.btn_connect.configure(text="Conectando...", state="disabled")
            self.update()
            
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT data FROM bot_settings WHERE id = 'main'")
            row = cur.fetchone()
            if row:
                self.config_data = row[0]
                self.populate_ui()
                self.status_label.configure(text="🟢 Estado: Conectado a la Nube (Bot 100% Sincronizado)", text_color="#22c55e")
                messagebox.showinfo("Éxito", "Configuración descargada de la nube correctamente.")
            else:
                messagebox.showwarning("Advertencia", "La base de datos está vacía. Guarda cambios para inicializarla.")
            cur.close()
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar a PostgreSQL:\n{e}\n\nAsegúrate de usar la URL PÚBLICA (External) que te da Railway.")
            self.status_label.configure(text="🔴 Estado: Error de Conexión", text_color="#ef4444")
        finally:
            self.btn_connect.configure(text="🔗 Conectar BD", state="normal")

    def populate_ui(self):
        c = self.config_data
        
        # Moderation
        mod = c.get("moderation", {})
        self.mod_anti_links.select() if mod.get("anti_links") else self.mod_anti_links.deselect()
        self.mod_anti_spam.select() if mod.get("anti_spam") else self.mod_anti_spam.deselect()
        
        wf = c.get("word_filter", {})
        self.mod_words.delete(0, 'end')
        self.mod_words.insert(0, ", ".join(wf.get("words", [])))
        
        # Onboarding
        onb = c.get("onboarding", {})
        self.onb_enabled.select() if onb.get("enabled") else self.onb_enabled.deselect()
        self.onb_role.delete(0, 'end')
        self.onb_role.insert(0, str(onb.get("verified_role_id", "")))
        
        # Welcome / XP
        welc = c.get("welcome", {})
        self.welc_enabled.select() if welc.get("enabled") else self.welc_enabled.deselect()
        self.welc_channel.delete(0, 'end')
        self.welc_channel.insert(0, str(welc.get("channel_id", "")))
        
        xp = c.get("xp", {})
        self.xp_enabled.select() if xp.get("enabled") else self.xp_enabled.deselect()

    def save_to_db(self):
        try:
            url = self.db_entry.get().strip()
            if not url: return messagebox.showerror("Error", "Conecta la BD primero.")
            
            c = self.config_data
            
            # Moderation updates
            if "moderation" not in c: c["moderation"] = {}
            c["moderation"]["anti_links"] = bool(self.mod_anti_links.get())
            c["moderation"]["anti_spam"] = bool(self.mod_anti_spam.get())
            
            if "word_filter" not in c: c["word_filter"] = {}
            c["word_filter"]["enabled"] = len(self.mod_words.get().strip()) > 0
            c["word_filter"]["words"] = [w.strip() for w in self.mod_words.get().split(",") if w.strip()]
            
            # Onboarding
            if "onboarding" not in c: c["onboarding"] = {}
            c["onboarding"]["enabled"] = bool(self.onb_enabled.get())
            c["onboarding"]["verified_role_id"] = self.onb_role.get().strip()
            
            # Welcome/XP
            if "welcome" not in c: c["welcome"] = {}
            c["welcome"]["enabled"] = bool(self.welc_enabled.get())
            c["welcome"]["channel_id"] = self.welc_channel.get().strip()
            
            if "xp" not in c: c["xp"] = {}
            c["xp"]["enabled"] = bool(self.xp_enabled.get())
            
            # Subir a la DB
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO bot_settings (id, data) VALUES ('main', %s)
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data
            """, (Json(c),))
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("✅ Mega Cambios Aplicados", "Configuración subida a la nube exitosamente.\n\nEl Bot en Railway detectará los cambios en máximo 15 segundos y los aplicará al instante sin reiniciarse.")
            
        except Exception as e:
            messagebox.showerror("Error al Guardar", f"Hubo un problema:\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
