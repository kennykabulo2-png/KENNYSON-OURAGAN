from flask import Flask, jsonify, request
import requests
import os
import re
import json
from datetime import datetime

app = Flask(__name__)

# ==================================================
# CONFIGURATION
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==================================================
# GLOBALPING API (Diagnostics réseau réels)
# ==================================================
GLOBALPING_URL = "https://api.globalping.io/v1"

class GlobalPing:
    """API Globalping - Diagnostics réseau en temps réel"""
    
    @staticmethod
    def ping(host, limit=3):
        """Exécute un ping vers une cible"""
        try:
            payload = {
                "target": host,
                "type": "ping",
                "measurementOptions": {
                    "packets": limit,
                    "packetSize": 56
                }
            }
            headers = {"Content-Type": "application/json"}
            r = requests.post(f"{GLOBALPING_URL}/measurements", json=payload, headers=headers, timeout=30)
            if r.status_code == 202:
                measurement_id = r.json().get('id')
                # Attendre les résultats
                import time
                time.sleep(2)
                result = requests.get(f"{GLOBALPING_URL}/measurements/{measurement_id}", timeout=30)
                if result.status_code == 200:
                    return result.json()
            return None
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def traceroute(host):
        """Exécute un traceroute vers une cible"""
        try:
            payload = {
                "target": host,
                "type": "traceroute",
                "measurementOptions": {
                    "protocol": "ICMP",
                    "maxHops": 15
                }
            }
            headers = {"Content-Type": "application/json"}
            r = requests.post(f"{GLOBALPING_URL}/measurements", json=payload, headers=headers, timeout=30)
            if r.status_code == 202:
                measurement_id = r.json().get('id')
                import time
                time.sleep(3)
                result = requests.get(f"{GLOBALPING_URL}/measurements/{measurement_id}", timeout=30)
                if result.status_code == 200:
                    return result.json()
            return None
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def dns(host, record_type="A"):
        """Effectue une requête DNS"""
        try:
            payload = {
                "target": host,
                "type": "dns",
                "measurementOptions": {
                    "recordType": record_type
                }
            }
            headers = {"Content-Type": "application/json"}
            r = requests.post(f"{GLOBALPING_URL}/measurements", json=payload, headers=headers, timeout=30)
            if r.status_code == 202:
                measurement_id = r.json().get('id')
                import time
                time.sleep(2)
                result = requests.get(f"{GLOBALPING_URL}/measurements/{measurement_id}", timeout=30)
                if result.status_code == 200:
                    return result.json()
            return None
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def mtr(host):
        """Exécute un MTR (My TraceRoute)"""
        try:
            payload = {
                "target": host,
                "type": "mtr",
                "measurementOptions": {
                    "packets": 5,
                    "protocol": "ICMP"
                }
            }
            headers = {"Content-Type": "application/json"}
            r = requests.post(f"{GLOBALPING_URL}/measurements", json=payload, headers=headers, timeout=30)
            if r.status_code == 202:
                measurement_id = r.json().get('id')
                import time
                time.sleep(4)
                result = requests.get(f"{GLOBALPING_URL}/measurements/{measurement_id}", timeout=30)
                if result.status_code == 200:
                    return result.json()
            return None
        except Exception as e:
            return {"error": str(e)}

# ==================================================
# GATEWAY API (Qualité de service - Simulation)
# ==================================================
class GatewayAPI:
    """API Gateway - Gestion de la qualité de service"""
    
    @staticmethod
    def get_network_quality(ip):
        """Simule la qualité du réseau pour une IP"""
        # En production, appeler une vraie API Open Gateway
        return {
            "ip": ip,
            "quality": "bonne" if ip.startswith("10.") else "moyenne",
            "latency": 25 if ip.startswith("10.") else 85,
            "bandwidth": 100 if ip.startswith("10.") else 35,
            "status": "stable"
        }
    
    @staticmethod
    def request_bandwidth_boost(ip, duration=30):
        """Demande une augmentation de bande passante"""
        return {
            "ip": ip,
            "boost": "active",
            "bandwidth_increase": "+50%",
            "duration": f"{duration} minutes",
            "status": "confirmed"
        }
    
    @staticmethod
    def get_cell_info(phone_number):
        """Simule l'info cellule pour un numéro"""
        return {
            "phone": phone_number,
            "operator": "Orange RDC",
            "signal": "fort" if phone_number.startswith("08") else "moyen",
            "network": "4G+",
            "location": "Kinshasa"
        }

# ==================================================
# AGENT TÉLÉCOM AVEC API RÉELLES
# ==================================================
class TelecomAgent:
    def __init__(self):
        self.gp = GlobalPing()
        self.gw = GatewayAPI()
    
    def process(self, question):
        q = question.lower()
        
        # === 1. PING ===
        ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', q)
        if ip_match:
            ip = ip_match.group(0)
            result = self.gp.ping(ip)
            if result:
                return self.format_ping_result(ip, result)
        
        # === 2. TRACEROUTE ===
        if "traceroute" in q or "trace" in q:
            if ip_match:
                ip = ip_match.group(0)
                result = self.gp.traceroute(ip)
                if result:
                    return self.format_traceroute_result(ip, result)
        
        # === 3. DNS ===
        if "dns" in q or "résolution" in q:
            domain_match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', q)
            if domain_match:
                domain = domain_match.group(1)
                result = self.gp.dns(domain)
                if result:
                    return self.format_dns_result(domain, result)
        
        # === 4. MTR ===
        if "mtr" in q:
            if ip_match:
                ip = ip_match.group(0)
                result = self.gp.mtr(ip)
                if result:
                    return self.format_mtr_result(ip, result)
        
        # === 5. Qualité réseau (Gateway) ===
        if "qualité" in q or "performance" in q:
            if ip_match:
                ip = ip_match.group(0)
                quality = self.gw.get_network_quality(ip)
                return self.format_quality_result(quality)
        
        # === 6. Boost bande passante ===
        if "boost" in q or "bande passante" in q:
            if ip_match:
                ip = ip_match.group(0)
                boost = self.gw.request_bandwidth_boost(ip)
                return self.format_boost_result(boost)
        
        # === 7. IA générale ===
        return self.get_ia_response(question)
    
    def format_ping_result(self, ip, data):
        result = f"📡 **RÉSULTAT PING vers {ip}**\n\n"
        try:
            results = data.get('results', [])
            if results:
                for probe in results[:3]:
                    if 'result' in probe:
                        stats = probe['result']['stats']
                        result += f"📍 {probe.get('probe', {}).get('country', 'N/A')}:\n"
                        result += f"   • Min: {stats.get('min', 0):.2f} ms\n"
                        result += f"   • Max: {stats.get('max', 0):.2f} ms\n"
                        result += f"   • Moy: {stats.get('avg', 0):.2f} ms\n"
                        result += f"   • Perte: {stats.get('loss', 0):.1f}%\n\n"
            else:
                result += "⚠️ Aucun résultat reçu"
        except:
            result += "⚠️ Erreur de parsing des résultats"
        return result
    
    def format_traceroute_result(self, ip, data):
        result = f"🔍 **TRACEROUTE vers {ip}**\n\n"
        try:
            results = data.get('results', [])
            if results:
                for probe in results[:1]:
                    if 'result' in probe:
                        hops = probe['result']
                        result += "Chemin IP:\n"
                        for hop in hops[:10]:
                            result += f"  {hop.get('hop', '?')}. {hop.get('ip', 'N/A')} ({hop.get('rtt', 0):.2f} ms)\n"
            else:
                result += "⚠️ Aucun résultat reçu"
        except:
            result += "⚠️ Erreur de parsing"
        return result
    
    def format_dns_result(self, domain, data):
        result = f"🌐 **RÉSULTAT DNS pour {domain}**\n\n"
        try:
            results = data.get('results', [])
            if results:
                for probe in results[:1]:
                    if 'result' in probe:
                        answers = probe['result'].get('answers', [])
                        if answers:
                            for ans in answers:
                                result += f"• {ans.get('type', '')}: {ans.get('data', 'N/A')}\n"
                        else:
                            result += "⚠️ Aucune réponse DNS"
            else:
                result += "⚠️ Aucun résultat reçu"
        except:
            result += "⚠️ Erreur de parsing"
        return result
    
    def format_mtr_result(self, ip, data):
        result = f"📊 **MTR vers {ip}**\n\n"
        try:
            results = data.get('results', [])
            if results:
                for probe in results[:1]:
                    if 'result' in probe:
                        for hop in probe['result'][:8]:
                            result += f"Hop {hop.get('hop', '?')}: {hop.get('ip', 'N/A')} - {hop.get('rtt', 0):.2f} ms\n"
            else:
                result += "⚠️ Aucun résultat reçu"
        except:
            result += "⚠️ Erreur de parsing"
        return result
    
    def format_quality_result(self, quality):
        result = "📶 **QUALITÉ DE RÉSEAU**\n\n"
        result += f"📍 IP: {quality.get('ip', 'N/A')}\n"
        result += f"📊 Qualité: {quality.get('quality', 'N/A')}\n"
        result += f"⏱️ Latence: {quality.get('latency', 0)} ms\n"
        result += f"📶 Bande passante: {quality.get('bandwidth', 0)} Mbps\n"
        result += f"📡 Statut: {quality.get('status', 'N/A')}\n"
        return result
    
    def format_boost_result(self, boost):
        result = "🚀 **DEMANDE DE BOOST BANDE PASSANTE**\n\n"
        result += f"📍 IP: {boost.get('ip', 'N/A')}\n"
        result += f"📊 Statut: {boost.get('status', 'N/A')}\n"
        result += f"📈 Augmentation: {boost.get('bandwidth_increase', 'N/A')}\n"
        result += f"⏱️ Durée: {boost.get('duration', 'N/A')}\n"
        return result
    
    def get_ia_response(self, question):
        if not GROQ_API_KEY:
            return self.get_help_message()
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Tu es KENNYSON OURAGAN, expert télécom avec accès aux API Globalping et Gateway."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
        except:
            pass
        return self.get_help_message()
    
    def get_help_message(self):
        return """📡 **KENNYSON OURAGAN - AGENT TÉLÉCOM** 

**🔍 Commandes réseau disponibles :**

📊 **Ping** → "ping 8.8.8.8"
🔍 **Traceroute** → "traceroute 8.8.8.8"
🌐 **DNS** → "dns google.com"
📈 **MTR** → "mtr 8.8.8.8"
📶 **Qualité** → "qualité réseau 192.168.1.1"
🚀 **Boost** → "boost bande passante 192.168.1.1"

**💡 Exemples :**
• "ping 8.8.8.8" - Teste la connectivité
• "traceroute google.com" - Chemin réseau
• "dns facebook.com" - Résolution DNS
• "qualité réseau 10.0.0.1" - Performance
• "boost 10.0.0.1" - Augmente débit

**Posez votre commande !** 🔥"""

# ==================================================
# ROUTES
# ==================================================
agent = TelecomAgent()

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    reponse = agent.process(question)
    return jsonify({"reponse": reponse})

@app.route('/api/health')
def health():
    return jsonify({"status": "online"})

# ==================================================
# INTERFACE
# ==================================================
HTML = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Agent Télécom</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto; background: #0A0F1E; color: #ececec; height: 100vh; display: flex; flex-direction: column; }
        .header { background: #1a1a2e; padding: 16px 20px; border-bottom: 1px solid #0085CA; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; background: linear-gradient(135deg, #e94560, #0085CA); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .badge { background: #0085CA; border-radius: 20px; padding: 2px 12px; font-size: 10px; margin-left: 8px; }
        .sub { font-size: 11px; color: #8e8ea0; margin-top: 4px; }
        .chat-container { flex: 1; overflow-y: auto; padding: 20px; max-width: 900px; margin: 0 auto; width: 100%; }
        .message { display: flex; gap: 16px; margin-bottom: 24px; }
        .avatar { width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .avatar.user { background: #10a37f; }
        .avatar.bot { background: #0085CA; }
        .content { flex: 1; line-height: 1.6; white-space: pre-wrap; font-size: 14px; }
        .content strong { color: #0085CA; }
        .input-area { background: #1a1a2e; padding: 16px; border-top: 1px solid #4a4b5a; }
        .input-wrapper { max-width: 800px; margin: 0 auto; display: flex; gap: 12px; }
        textarea { flex: 1; background: #40414f; border: none; border-radius: 12px; padding: 12px 16px; color: white; font-family: inherit; resize: none; font-size: 14px; }
        button { background: #0085CA; border: none; border-radius: 12px; padding: 12px 24px; color: white; cursor: pointer; font-weight: 500; }
        .suggestions { max-width: 800px; margin: 12px auto 0; display: flex; gap: 8px; flex-wrap: wrap; }
        .suggestion { background: #2a2b32; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; border: 1px solid #0085CA; }
        .suggestion:hover { background: #0085CA; }
        .footer { text-align: center; padding: 8px; font-size: 10px; color: #565869; }
        .typing span { display: inline-block; width: 8px; height: 8px; background: #8e8ea0; border-radius: 50%; animation: pulse 1.4s infinite; margin: 0 2px; }
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
    </style>
</head>
<body>
<div class="header">
    <div class="logo">📡 KENNYSON OURAGAN <span class="badge">API RÉSEAU</span></div>
    <div class="sub">Globalping · Gateway · Diagnostics en temps réel</div>
</div>
<div class="chat-container" id="chat"></div>
<div class="input-area">
    <div class="input-wrapper">
        <textarea id="input" rows="1" placeholder="Ex: ping 8.8.8.8..."></textarea>
        <button id="send">Envoyer</button>
    </div>
    <div class="suggestions">
        <div class="suggestion" data-q="ping 8.8.8.8">📊 Ping</div>
        <div class="suggestion" data-q="traceroute google.com">🔍 Traceroute</div>
        <div class="suggestion" data-q="dns facebook.com">🌐 DNS</div>
        <div class="suggestion" data-q="mtr 8.8.8.8">📈 MTR</div>
        <div class="suggestion" data-q="qualité réseau 10.0.0.1">📶 Qualité</div>
    </div>
    <div class="footer">📡 Agent Télécom · Globalping · Gateway · Diagnostics temps réel</div>
</div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');

function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = 'message';
    div.innerHTML = `<div class="avatar ${role}">${role === 'user' ? '👤' : 'K'}</div><div class="content">${text.replace(/\\n/g, '<br>').replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')}</div>`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function send() {
    const q = input.value.trim();
    if (!q) return;
    addMessage(q, 'user');
    input.value = '';
    addMessage('<div class="typing"><span>●</span><span>●</span><span>●</span></div>', 'bot');
    try {
        const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) });
        const data = await res.json();
        chat.lastChild.remove();
        addMessage(data.reponse, 'bot');
    } catch(e) {
        chat.lastChild.remove();
        addMessage("❌ Erreur. Veuillez réessayer.", 'bot');
    }
}

document.getElementById('send').onclick = send;
input.onkeypress = (e) => { if(e.key === 'Enter') { e.preventDefault(); send(); } };
document.querySelectorAll('.suggestion').forEach(s => { s.onclick = () => { input.value = s.dataset.q; send(); }; });

addMessage('📡 **KENNYSON OURAGAN - AGENT TÉLÉCOM**\n\nBonjour ! Je suis votre expert réseau avec **API réelles**.\n\n**🔍 Commandes disponibles :**\n• 📊 **ping 8.8.8.8** - Test de connectivité\n• 🔍 **traceroute google.com** - Chemin réseau\n• 🌐 **dns facebook.com** - Résolution DNS\n• 📈 **mtr 8.8.8.8** - Analyse détaillée\n• 📶 **qualité réseau 10.0.0.1** - Performance\n\n**Exécutez vos commandes réseau !** 🔥', 'bot');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
