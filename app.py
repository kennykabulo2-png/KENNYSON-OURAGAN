from flask import Flask, jsonify, request, session
import hashlib
import secrets
import requests
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kennyson_render_ready_2026'

# ==================================================
# BASE DE DONNÉES
# ==================================================
def init_db():
    conn = sqlite3.connect('kennyson_memory.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        question TEXT,
        reponse TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# ==================================================
# API GRATUITES (sans clé ou avec clé si dispo)
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_worldbank_gdp():
    try:
        r = requests.get("http://api.worldbank.org/v2/country/CD/indicator/NY.GDP.MKTP.CD?format=json", timeout=8)
        if r.status_code == 200:
            data = r.json()
            if len(data) > 1 and data[1] and data[1][0].get('value'):
                return f"📊 PIB RDC: {int(float(data[1][0]['value'])):,} USD"
    except:
        pass
    return None

def get_crypto_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=8)
        if r.status_code == 200:
            return f"💰 Bitcoin: ${r.json()['bitcoin']['usd']:,} USD"
    except:
        pass
    return None

def get_weather():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast?latitude=-4.325&longitude=15.322&current_weather=true", timeout=8)
        if r.status_code == 200:
            return f"🌤️ Kinshasa: {r.json()['current_weather']['temperature']}°C"
    except:
        pass
    return None

def search_news():
    if not GNEWS_API_KEY:
        return None
    try:
        r = requests.get(f"https://gnews.io/api/v4/search?q=économie&token={GNEWS_API_KEY}&lang=fr&max=2", timeout=8)
        if r.status_code == 200:
            articles = r.json().get('articles', [])
            if articles:
                result = "📰 ACTUALITÉS:\n"
                for a in articles[:2]:
                    result += f"- {a.get('title', '')}\n"
                return result
    except:
        pass
    return None

# ==================================================
# IA CENTRALE
# ==================================================
SYSTEM_PROMPT = """Tu es KENNYSON OURAGAN, un assistant intelligent.
Sois utile, précis, naturel. Réponds en français en 2-3 paragraphes.
Tu peux aider sur: économie, météo, crypto, définitions, actualités."""

def kennyson_answer(question):
    external = ""
    q = question.lower()
    
    if "pib" in q or "économie" in q:
        ext = get_worldbank_gdp()
        if ext: external += ext + "\n\n"
    if "bitcoin" in q or "crypto" in q:
        ext = get_crypto_price()
        if ext: external += ext + "\n\n"
    if "météo" in q or "temps" in q:
        ext = get_weather()
        if ext: external += ext + "\n\n"
    if "actualité" in q or "news" in q:
        ext = search_news()
        if ext: external += ext + "\n\n"
    
    if not GROQ_API_KEY:
        return external or "KENNYSON OURAGAN est prêt. Ajoute ta clé Groq dans les variables Render."
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}],
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=35)
        if r.status_code == 200:
            rep = r.json()['choices'][0]['message']['content']
            return f"{external}\n{rep}" if external else rep
        return external or "Je rencontre une difficulté. Veuillez réessayer."
    except:
        return external or "KENNYSON OURAGAN prêt. Reformulez votre question."

# ==================================================
# ROUTES API
# ==================================================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    reponse = kennyson_answer(question)
    return jsonify({"reponse": reponse})

@app.route('/api/health')
def health():
    return jsonify({"status": "online", "groq": bool(GROQ_API_KEY), "gnews": bool(GNEWS_API_KEY)})

# ==================================================
# FRONTEND STYLE CHATGPT
# ==================================================
HTML = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Agent IA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto; background: #343541; color: #ececec; height: 100vh; overflow: hidden; }
        .app { display: flex; flex-direction: column; height: 100vh; }
        .header { background: #202123; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #4a4b5a; }
        .logo { font-size: 18px; font-weight: bold; background: linear-gradient(135deg, #e94560, #ff5a7c); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .chat-container { flex: 1; overflow-y: auto; padding: 20px; }
        .message { display: flex; gap: 16px; margin-bottom: 24px; }
        .avatar { width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .avatar.user { background: #10a37f; }
        .avatar.bot { background: #e94560; }
        .content { flex: 1; line-height: 1.6; }
        .input-area { background: #202123; padding: 16px; border-top: 1px solid #4a4b5a; }
        .input-wrapper { max-width: 800px; margin: 0 auto; display: flex; gap: 12px; }
        textarea { flex: 1; background: #40414f; border: none; border-radius: 12px; padding: 12px 16px; color: white; font-family: inherit; resize: none; }
        button { background: #e94560; border: none; border-radius: 12px; padding: 12px 24px; color: white; cursor: pointer; font-weight: 500; }
        .suggestions { max-width: 800px; margin: 12px auto 0; display: flex; gap: 8px; flex-wrap: wrap; }
        .suggestion { background: #2a2b32; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; }
        .suggestion:hover { background: #e94560; }
        .footer { text-align: center; padding: 8px; font-size: 11px; color: #565869; background: #202123; border-top: 1px solid #4a4b5a; }
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
        .typing span { display: inline-block; width: 8px; height: 8px; background: #8e8ea0; border-radius: 50%; animation: pulse 1.4s infinite; margin: 0 2px; }
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <div class="logo">🔥 KENNYSON OURAGAN</div>
        <div style="font-size:12px; color:#8e8ea0;">Agent IA · Version Render Ready</div>
    </div>
    <div class="chat-container" id="chat"></div>
    <div class="input-area">
        <div class="input-wrapper">
            <textarea id="input" rows="1" placeholder="Posez votre question..."></textarea>
            <button id="send">Envoyer</button>
        </div>
        <div class="suggestions">
            <div class="suggestion" data-q="PIB de la RDC">📊 PIB RDC</div>
            <div class="suggestion" data-q="Prix du Bitcoin">💰 Bitcoin</div>
            <div class="suggestion" data-q="Météo à Kinshasa">🌤️ Météo</div>
            <div class="suggestion" data-q="Actualités économiques">📰 Actualités</div>
        </div>
        <div class="footer">KENNYSON OURAGAN · Agent IA · Gratuit · Render Ready</div>
    </div>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');

function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = 'message';
    div.innerHTML = `<div class="avatar ${role}">${role === 'user' ? '👤' : 'K'}</div><div class="content">${text.replace(/\\n/g, '<br>')}</div>`;
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
        addMessage("Erreur technique. Veuillez réessayer.", 'bot');
    }
}

sendBtn.onclick = send;
input.onkeypress = (e) => { if(e.key === 'Enter') { e.preventDefault(); send(); } };
document.querySelectorAll('.suggestion').forEach(s => { s.onclick = () => { input.value = s.dataset.q; send(); }; });
addMessage('Bonjour ! Je suis KENNYSON OURAGAN, agent IA compatible Render. Posez-moi vos questions sur économie, crypto, météo, actualités...', 'bot');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
