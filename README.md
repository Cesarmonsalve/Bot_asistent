# ⚡ The Family Bot

Bot completo para el servidor de Discord de Cesar Monsalve.

## Funciones
- 👋 Bienvenida automática con imagen
- 🎭 Reaction roles automáticos
- ⭐ Sistema de XP y niveles
- 🔴 Alertas de stream (Kick y TikTok)
- 🛡️ Moderación (anti-links)
- 🎉 Sorteos con /sorteo
- 🎛️ Panel web para configurar todo

---

## Deploy en Railway (gratis, 24/7)

### 1. Crear cuenta en Railway
→ railway.app → Sign up with GitHub

### 2. Subir el proyecto a GitHub
```bash
git init
git add .
git commit -m "The Family Bot"
git remote add origin https://github.com/TU_USUARIO/the-family-bot.git
git push -u origin main
```

### 3. Crear proyecto en Railway
1. railway.app → New Project → Deploy from GitHub repo
2. Elegí el repo `the-family-bot`

### 4. Configurar variables de entorno
En Railway → tu proyecto → Variables → Add:

| Variable | Valor |
|---|---|
| BOT_TOKEN | Tu token de Discord |
| GUILD_ID | 1486498876503494707 |
| PANEL_PASSWORD | La contraseña que quieras para el panel |
| PANEL_SECRET | Cualquier string random largo |

### 5. Agregar dos servicios
Railway necesita correr el bot Y el panel por separado:
- Servicio 1: usa el comando `python bot.py`
- Servicio 2: usa el comando `gunicorn panel:app`

O simplemente dejá el Procfile como está — Railway lo detecta solo.

### 6. Listo 🎉
- El bot va a estar online 24/7
- El panel va a estar en la URL que Railway te da (algo como `the-family-bot.up.railway.app`)

---

## Comandos de Discord

| Comando | Descripción | Permisos |
|---|---|---|
| /ping | Ver latencia | Todos |
| /rank | Ver tu XP y nivel | Todos |
| /leaderboard | Top 10 | Todos |
| /sorteo | Iniciar sorteo | Admin |
| /say | Bot habla | Admin |
| /embed | Embed personalizado | Admin |
| /warn | Advertir usuario | Staff |
| /clear | Borrar mensajes | Staff |
| /panel | Link al panel web | Admin |

---

## Panel Web

El panel web permite configurar todo sin tocar código:
- Bienvenida automática
- Reaction roles
- Sistema XP
- Alertas de stream
- Moderación

Accedé con la contraseña que pusiste en PANEL_PASSWORD.
