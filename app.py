from flask import Flask, jsonify, request
import requests
import os
import json
import hashlib
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
TELECOM_KNOWLEDGE = {
    "réseaux": {
        "latence": {
            "definition": "Temps de transmission entre deux points",
            "seuil_normal": "Moins de 50ms",
            "causes": ["Congestion réseau", "Distance géographique", "Interférences", "Matériel obsolète"],
            "solutions": ["Configurer la QoS", "Passer à la fibre optique", "Optimiser le routage", "Mettre à jour le matériel"]
        },
        "bande_passante": {
            "definition": "Capacité de transmission de données",
            "seuil_normal": "Dépend de l'usage",
            "causes": ["Trop d'utilisateurs", "Applications gourmandes", "Matériel limité"],
            "solutions": ["Augmenter la bande passante", "Prioriser le trafic", "Mettre en place un cache"]
        }
    },
    "securité": {
        "menaces": ["DDoS", "Phishing", "Malware", "Interception", "Ransomware"],
        "protections": ["Pare-feu", "IDS/IPS", "Chiffrement des données", "Authentification forte", "VPN"],
        "bonnes_pratiques": ["Mettre à jour régulièrement", "Utiliser des mots de passe complexes", "Former les utilisateurs"]
    },
    "5g": {
        "definition": "Cinquième génération de réseau mobile",
        "debit": "Jusqu'à 10 Gbps",
        "latence": "Moins de 1ms",
        "applications": ["IoT", "Véhicules autonomes", "Smart Cities", "Réalité augmentée"],
        "infrastructure": ["Antennes massives MIMO", "Small cells", "Edge computing"]
    },
    "cloud": {
        "fournisseurs": ["AWS", "Azure", "Google Cloud", "Oracle Cloud"],
        "services": ["IaaS", "PaaS", "SaaS", "Serverless"],
        "avantages": ["Scalabilité", "Flexibilité", "Réduction des coûts", "Accès global"],
        "securité": ["Chiffrement", "IAM", "Monitoring", "Backup"]
    },
    "voip": {
        "protocoles": ["SIP", "H.323", "MGCP"],
        "problèmes": ["Latence", "Jitter", "Perte de paquets"],
        "solutions": ["Prioriser le trafic VoIP", "Optimiser la bande passante", "Utiliser un codec adapté"]
    },
    "iot": {
        "protocoles": ["MQTT", "CoAP", "LwM2M", "Zigbee"],
        "applications": ["Smart Home", "Industrie 4.0", "Villes intelligentes"],
        "securité": ["Chiffrement", "Authentification", "Mises à jour régulières"]
    }
}

# ==================================================
# AGENT SPÉCIALISÉ TÉLÉCOM
# ==================================================
class TelecomAgent:
    def __init__(self):
        self.memory = []
        self.knowledge = TELECOM_KNOWLEDGE
    
    def get_context(self, question):
        q = question.lower()
        context = ""
        
        # 1. Recherche dans la base de connaissances
        for domaine, subdomain in self.knowledge.items():
            for key, data in subdomain.items():
                if key in q or domaine in q:
                    if isinstance(data, dict):
                        context += f"📡 DOMAINE: {domaine.upper()} - {key.upper()}\n"
                        for k, v in data.items():
                            if isinstance(v, list):
                                context += f"  {k}: {', '.join(v)}\n"
                            else:
                                context += f"  {k}: {v}\n"
                        context += "\n"
        
        # 2. Suggestions si aucun domaine trouvé
        if not context:
            context = "📡 DOMAINES DISPONIBLES:\n"
            for domaine in self.knowledge.keys():
                context += f"  • {domaine.capitalize()}\n"
            context += "\nPosez une question précise sur un domaine."
        
        return context
    
    def generate_response(self, question, context):
        if not GROQ_API_KEY:
            return "⚠️ GROQ_API_KEY manquante. Ajoute-la dans Environment sur Render."
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": """Tu es KENNYSON OURAGAN, un expert en télécommunications et informatique.

RÈGLES:
- Utilise les informations techniques du CONTEXTE
- Propose des solutions concrètes et actionnables
- Structure ta réponse en: Diagnostic → Causes → Solutions → Prévention
- Sois précis et professionnel

Ton expertise couvre:
- Réseaux (TCP/IP, DNS, DHCP, VPN, Routage)
- Sécurité (Pare-feu, IDS/IPS, Chiffrement)
- Cloud (AWS, Azure, Google Cloud)
- 5G, IoT, VoIP, Téléphonie
- Serveurs Linux/Windows
- Bases de données et optimisations
"""},
                {"role": "user", "content": f"Contexte technique:\n{context}\n\nQuestion de l'utilisateur: {question}\n\nRéponds en tant qu'expert Télécom."}
            ],
            "temperature": 0.5,
            "max_tokens": 800
        }
        
        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                reponse = r.json()['choices'][0]['message']['content']
                return reponse
            return f"Erreur API: {r.status_code}"
        except Exception as e:
            return f"Erreur technique: {str(e)[:100]}"

# ==================================================
# INITIALISATION
# ==================================================
agent = TelecomAgent()

# ==================================================
# ROUTES API
# ==================================================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    context = agent.get_context(question)
    reponse = agent.generate_response(question, context)
    return jsonify({"reponse": reponse, "context": context})

@app.route('/api/knowledge')
def knowledge():
    return jsonify(agent.knowledge)

# ==================================================
# FRONTEND
# ==================================================
HTML = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Expert Télécom</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto; background: #343541; color: #ececec; height: 100vh; display: flex; flex-direction: column; }
        .header { background: #202123; padding: 16px 20px; border-bottom: 1px solid #4a4b5a; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; background: linear-gradient(135deg, #e94560, #ff5a7c); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .badge { background: #0085CA; border-radius: 20px; padding: 2px 12px; font-size: 10px; margin-left: 8px; }
        .sub { font-size: 11px; color: #8e8ea0; margin-top: 4px; }
        .stats-bar { background: #2a2b32; padding: 6px 16px; font-size: 11px; text-align: center; border-bottom: 1px solid #4a4b5a; }
        .chat-container { flex: 1; overflow-y: auto; padding: 20px; max-width: 800px; margin: 0 auto; width: 100%; }
        .message { display: flex; gap: 16px; margin-bottom: 24px; }
        .avatar { width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .avatar.user { background: #10a37f; }
        .avatar.bot { background: #e94560; }
        .content { flex: 1; line-height: 1.6; white-space: pre-wrap; font-size: 14px; }
        .content strong { color: #e94560; }
        .content .highlight { background: rgba(0,133,202,0.2); padding: 2px 6px; border-radius: 4px; }
        .input-area { background: #202123; padding: 16px; border-top: 1px solid #4a4b5a; }
        .input-wrapper { max-width: 800px; margin: 0 auto; display: flex; gap: 12px; }
        textarea { flex: 1; background: #40414f; border: none; border-radius: 12px; padding: 12px 16px; color: white; font-family: inherit; resize: none; font-size: 14px; }
        button { background: #0085CA; border: none; border-radius: 12px; padding: 12px 24px; color: white; cursor: pointer; font-weight: 500; }
        .suggestions { max-width: 800px; margin: 12px auto 0; display: flex; gap: 8px; flex-wrap: wrap; }
        .suggestion { background: #2a2b32; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; }
        .suggestion:hover { background: #0085CA; }
        .footer { text-align: center; padding: 8px; font-size: 10px; color: #565869; }
        .typing span { display: inline-block; width: 8px; height: 8px; background: #8e8ea0; border-radius: 50%; animation: pulse 1.4s infinite; margin: 0 2px; }
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
        @media (max-width: 768px) { .suggestions { justify-content: center; } }
    </style>
</head>
<body>
<div class="header">
    <div class="logo">📡 KENNYSON OURAGAN <span class="badge">EXPERT TÉLÉCOM</span></div>
    <div class="sub">Agent IA spécialisé en Réseaux · Sécurité · Cloud · 5G · IoT</div>
</div>
<div class="stats-bar">📡 6 domaines d'expertise · Solutions techniques · Diagnostic réseau</div>
<div class="chat-container" id="chat"></div>
<div class="input-area">
    <div class="input-wrapper">
        <textarea id="input" rows="1" placeholder="Posez votre question technique..."></textarea>
        <button id="send">Envoyer</button>
    </div>
    <div class="suggestions">
        <div class="suggestion" data-q="Comment réduire la latence réseau ?">📶 Réduire la latence</div>
        <div class="suggestion" data-q="Sécuriser un réseau d'entreprise">🔒 Sécurité réseau</div>
        <div class="suggestion" data-q="Qu'est-ce que le 5G ?">📡 5G</div>
        <div class="suggestion" data-q="Avantages du Cloud">☁️ Cloud</div>
        <div class="suggestion" data-q="Problèmes VoIP">📞 VoIP</div>
        <div class="suggestion" data-q="Sécurité IoT">🔐 IoT</div>
    </div>
    <div class="footer">KENNYSON OURAGAN · Expert Télécom & Informatique · 100% Render</div>
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
        addMessage("❌ Erreur. Vérifie que GROQ_API_KEY est configurée.", 'bot');
    }
}

document.getElementById('send').onclick = send;
input.onkeypress = (e) => { if(e.key === 'Enter') { e.preventDefault(); send(); } };
document.querySelectorAll('.suggestion').forEach(s => { s.onclick = () => { input.value = s.dataset.q; send(); }; });

addMessage('📡 **KENNYSON OURAGAN - EXPERT TÉLÉCOM**\n\nBonjour ! Je suis votre assistant spécialisé en télécommunications et informatique.\n\n**🔧 Mes domaines d\'expertise :**\n• Réseaux (Latence, Bande passante, QoS)\n• Sécurité (Pare-feu, IDS/IPS, Chiffrement)\n• Cloud (AWS, Azure, Google Cloud)\n• 5G (Débit, Latence, Applications)\n• IoT (Protocoles, Sécurité, Applications)\n• VoIP (SIP, Jitter, Latence)\n\n**💡 Exemples de questions :**\n• "Comment réduire la latence réseau ?"\n• "Comment sécuriser un réseau d\'entreprise ?"\n• "Quels sont les avantages du Cloud ?"\n\nPosez votre question technique ! 🔥', 'bot');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
