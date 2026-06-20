from flask import Flask, jsonify, request
import requests
import os
import json
import re
from datetime import datetime

app = Flask(__name__)

# ==================================================
# CONFIGURATION
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==================================================
# BASE DE CONNAISSANCES TÉLÉCOM
# ==================================================
KNOWLEDGE_BASE = {
    "latence": {
        "def": "Temps de transmission entre deux points (ms)",
        "normal": "< 50ms",
        "causes": ["Congestion réseau", "Distance", "Interférences", "Mauvaise configuration"],
        "solutions": ["QoS", "Fibre optique", "Optimisation routage", "Passer en filaire"]
    },
    "bande_passante": {
        "def": "Capacité de transmission (bits/s)",
        "normal": "> 100 Mbps",
        "causes": ["Saturation", "Matériel obsolète", "Interférences"],
        "solutions": ["Augmenter débit", "Optimiser trafic", "Fibre optique"]
    },
    "ipv6": {
        "def": "Protocole Internet version 6",
        "avantages": ["Adresses illimitées", "Sécurité intégrée", "Meilleure performance"],
        "format": "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    },
    "5g": {
        "def": "Cinquième génération réseau mobile",
        "debit": "Jusqu'à 10 Gbps",
        "latence": "< 1 ms",
        "applications": ["IoT", "Véhicules autonomes", "Smart Cities"]
    },
    "firewall": {
        "def": "Système de sécurité réseau",
        "types": ["Matériel", "Logiciel", "Applicatif"],
        "recommandations": ["Configurer règles", "Mettre à jour", "Journaliser"]
    },
    "vpn": {
        "def": "Réseau privé virtuel",
        "protocoles": ["OpenVPN", "IPsec", "WireGuard"],
        "avantages": ["Confidentialité", "Sécurité"]
    },
    "wifi": {
        "def": "Technologie sans fil",
        "normes": ["802.11n", "802.11ac", "802.11ax (Wi-Fi 6)"],
        "problemes": ["Interférences", "Portée limitée", "Saturation canal"],
        "solutions": ["Changer canal", "5 GHz", "Répéteurs"]
    },
    "cybersecurite": {
        "def": "Protection des systèmes",
        "menaces": ["Malware", "Phishing", "DDoS", "Ransomware"],
        "bonnes_pratiques": ["Mots de passe forts", "MFA", "Mises à jour", "Sauvegardes"]
    },
    "cloud": {
        "def": "Services informatiques à distance",
        "modeles": ["IaaS", "PaaS", "SaaS"],
        "fournisseurs": ["AWS", "Azure", "Google Cloud", "OVH"]
    }
}

# ==================================================
# OUTILS RÉSEAU
# ==================================================
class NetworkTools:
    @staticmethod
    def diagnose_latency(ms):
        if ms < 50:
            return "✅ Excellente"
        elif ms < 100:
            return "⚠️ Modérée"
        else:
            return "❌ Élevée"
    
    @staticmethod
    def diagnose_wifi(signal):
        if signal >= 70:
            return "✅ Excellent"
        elif signal >= 50:
            return "⚠️ Moyen"
        else:
            return "❌ Faible"

# ==================================================
# AGENT TÉLÉCOM
# ==================================================
class TelecomAgent:
    def __init__(self):
        self.knowledge = KNOWLEDGE_BASE
        self.tools = NetworkTools()
    
    def identify_topics(self, question):
        q = question.lower()
        topics = []
        topic_map = {
            "latence": ["latence", "ping", "lent", "ralenti", "temps réponse", "ms"],
            "bande_passante": ["bande passante", "débit", "vitesse", "mbps"],
            "ipv6": ["ipv6", "adresse ipv6"],
            "5g": ["5g", "réseau mobile"],
            "firewall": ["firewall", "pare-feu", "bloque"],
            "vpn": ["vpn", "réseau privé"],
            "wifi": ["wifi", "sans fil", "wireless"],
            "cybersecurite": ["sécurité", "virus", "hack", "malware", "ransomware"],
            "cloud": ["cloud", "nuage", "aws", "azure"]
        }
        for topic, keywords in topic_map.items():
            if any(kw in q for kw in keywords):
                topics.append(topic)
        return topics
    
    def get_knowledge(self, topics):
        context = ""
        for topic in topics:
            if topic in self.knowledge:
                data = self.knowledge[topic]
                context += f"📡 **{topic.upper()}** : {data.get('def', '')}\n"
                if 'causes' in data:
                    context += f"   Causes: {', '.join(data['causes'][:3])}\n"
                if 'solutions' in data:
                    context += f"   Solutions: {', '.join(data['solutions'][:3])}\n"
                context += "\n"
        return context
    
    def analyze_network(self, question):
        q = question.lower()
        analysis = ""
        
        # Détection de latence
        ms_match = re.search(r'(\d+)\s*ms', q)
        if ms_match:
            ms = int(ms_match.group(1))
            status = self.tools.diagnose_latency(ms)
            analysis += f"📊 **Latence :** {ms} ms - {status}\n\n"
        
        # Détection de débit
        mbps_match = re.search(r'(\d+)\s*(?:mbps|mb/s)', q)
        if mbps_match:
            mbps = int(mbps_match.group(1))
            if mbps >= 100:
                status = "✅ Excellent"
            elif mbps >= 50:
                status = "⚠️ Moyen"
            else:
                status = "❌ Faible"
            analysis += f"📊 **Débit :** {mbps} Mbps - {status}\n\n"
        
        # Détection de signal Wi-Fi
        signal_match = re.search(r'(\d+)\s*%', q)
        if signal_match and 'wifi' in q:
            signal = int(signal_match.group(1))
            status = self.tools.diagnose_wifi(signal)
            analysis += f"📊 **Signal Wi-Fi :** {signal}% - {status}\n\n"
        
        return analysis
    
    def process(self, question):
        topics = self.identify_topics(question)
        knowledge = self.get_knowledge(topics)
        analysis = self.analyze_network(question)
        
        if not topics and not analysis:
            return self.get_general_response(question)
        
        if not GROQ_API_KEY:
            return f"{knowledge}{analysis}\n\n💡 Solutions recommandées:\n• Vérifiez la configuration réseau\n• Consultez la documentation technique\n• Contactez le support si nécessaire"
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Tu es un expert en télécommunications. Réponds en français de manière structurée."},
                {"role": "user", "content": f"Contexte:\n{knowledge}{analysis}\n\nQuestion: {question}\n\nDonne un diagnostic et des solutions concrètes."}
            ],
            "temperature": 0.7,
            "max_tokens": 600
        }
        
        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                reponse = r.json()['choices'][0]['message']['content']
                return f"{knowledge}{analysis}\n\n{reponse}"
            return f"{knowledge}{analysis}\n\n💡 Solutions recommandées: Vérifiez la configuration réseau."
        except:
            return f"{knowledge}{analysis}\n\n💡 Solutions recommandées: Vérifiez la configuration réseau."
    
    def get_general_response(self, question):
        if not GROQ_API_KEY:
            return self.get_help_message()
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": "Tu es un expert en télécommunications. Réponds en français."}, {"role": "user", "content": question}],
            "temperature": 0.7,
            "max_tokens": 400
        }
        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            return self.get_help_message()
        except:
            return self.get_help_message()
    
    def get_help_message(self):
        return """📡 **Agent Télécom & Informatique**

Je suis spécialisé en télécommunications et informatique.

**🔍 Ce que je peux faire :**
• Diagnostiquer des problèmes réseau
• Analyser la latence, le débit, le signal Wi-Fi
• Recommander des solutions techniques
• Expliquer les concepts (IPv4, IPv6, DNS, VPN, 5G, IoT, Cloud, Cybersécurité)

**💡 Exemples de questions :**
• "J'ai 200 ms de latence, c'est grave ?"
• "Comment améliorer mon Wi-Fi ?"
• "Qu'est-ce que le 5G ?"
• "Comment sécuriser mon réseau ?"
• "C'est quoi un VPN ?"

**Posez votre question technique !**"""

# ==================================================
# ROUTES API
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
    return jsonify({"status": "online", "groq": bool(GROQ_API_KEY)})

# ==================================================
# FRONTEND
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
    <div class="logo">📡 KENNYSON OURAGAN <span class="badge">AGENT TÉLÉCOM</span></div>
    <div class="sub">Réseaux · Sécurité · 5G · IoT · Cloud · Informatique</div>
</div>
<div class="chat-container" id="chat"></div>
<div class="input-area">
    <div class="input-wrapper">
        <textarea id="input" rows="1" placeholder="Posez votre question technique..."></textarea>
        <button id="send">Envoyer</button>
    </div>
    <div class="suggestions">
        <div class="suggestion" data-q="J'ai 200 ms de latence, c'est grave ?">📊 Latence</div>
        <div class="suggestion" data-q="Comment améliorer mon Wi-Fi ?">📶 Wi-Fi</div>
        <div class="suggestion" data-q="Qu'est-ce que le 5G ?">📡 5G</div>
        <div class="suggestion" data-q="Comment sécuriser mon réseau ?">🔒 Sécurité</div>
        <div class="suggestion" data-q="Que signifie IPv6 ?">🌐 IPv6</div>
        <div class="suggestion" data-q="C'est quoi un VPN ?">🔐 VPN</div>
    </div>
    <div class="footer">📡 Expert en télécommunications et informatique · Diagnostic réseau · Solutions techniques</div>
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

addMessage('📡 **KENNYSON OURAGAN - AGENT TÉLÉCOM**\n\nBonjour ! Je suis votre expert en télécommunications et informatique.\n\n**🔍 Mes compétences :**\n• 📊 Analyse de réseau (latence, débit, signal)\n• 🔒 Cybersécurité (pare-feu, VPN, protection)\n• 📶 Technologies (5G, Wi-Fi, IoT)\n• 🌐 Protocoles (IPv4, IPv6, DNS, TCP/IP)\n• ☁️ Cloud Computing (IaaS, PaaS, SaaS)\n\n**💡 Exemples :**\n• "J\'ai 150 ms de latence, c\'est normal ?"\n• "Comment configurer un VPN ?"\n• "Quelle est la différence entre IPv4 et IPv6 ?"\n• "Comment sécuriser mon réseau Wi-Fi ?"\n\nJe vous donne des diagnostics précis et des solutions concrètes ! 🔥', 'bot');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
