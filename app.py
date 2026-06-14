from flask import Flask, jsonify, request, session
import hashlib
import secrets
import requests
import os
import json
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kennyson_chatgpt_style_secret_2026'

# ==================================================
# BASE DE DONNÉES (MÉMOIRE)
# ==================================================
def init_db():
    conn = sqlite3.connect('kennyson_memory.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        question TEXT,
        reponse TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
        user_id TEXT PRIMARY KEY,
        theme TEXT DEFAULT 'dark',
        niveau TEXT DEFAULT 'intermediaire',
        style TEXT DEFAULT 'détaillé'
    )''')
    conn.commit()
    conn.close()

init_db()

# ==================================================
# CONFIGURATIONS API
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY', '')

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GNEWS_URL = "https://gnews.io/api/v4/search"

# ==================================================
# API GRATUITES
# ==================================================
def get_worldbank_gdp(country_code="CD"):
    try:
        url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/NY.GDP.MKTP.CD?format=json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1 and data[1]:
                latest = data[1][0]
                if latest['value']:
                    return f"PIB : {int(float(latest['value'])):,} USD ({latest['date']})"
    except:
        pass
    return None

def get_crypto_price(coin="bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if coin in data:
                return f"💰 {coin.upper()} : ${data[coin]['usd']:,.2f} USD"
    except:
        pass
    return None

def get_weather_meteo(city="Kinshasa"):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude=-4.325&longitude=15.322&current_weather=true"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            weather = data.get('current_weather', {})
            return f"🌡️ {city} : {weather.get('temperature')}°C"
    except:
        pass
    return None

def get_wikipedia_summary(topic="économie"):
    try:
        url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{topic}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('extract', '')[:300]
    except:
        pass
    return None

# ==================================================
# PROMPT STYLE CHATGPT
# ==================================================
SYSTEM_PROMPT = """Tu es KENNYSON OURAGAN, un assistant intelligent, utile et bienveillant.

**STYLE DE RÉPONSE (IMPORTANT)** :
- Sois naturel, conversationnel, comme ChatGPT
- Utilise des émojis avec parcimonie 😊
- Structure ta réponse en paragraphes aérés
- Pose parfois une question de suivi

**TON** : Amical, professionnel, précis. Pas de "Na lingala" systématique.

**FORMAT** :
- Réponse principale claire
- Données chiffrées quand pertinent
- Si tu utilises une API, mentionne la source

Exemple de bonne réponse :
"Le PIB de la RDC est d'environ 65 milliards USD (données 2025, source Banque mondiale). 
Cela représente une croissance de 4.5% par rapport à l'année précédente.

Cette croissance est principalement tirée par le secteur minier (cobalt, cuivre).

Souhaitez-vous que je détaille les performances par secteur ?"

Sois utile, précis, et agréable à lire."""

# ==================================================
# IA CENTRALE
# ==================================================
def save_conversation(user_id, question, reponse):
    conn = sqlite3.connect('kennyson_memory.db')
    c = conn.cursor()
    c.execute('INSERT INTO conversations (user_id, question, reponse) VALUES (?, ?, ?)', 
              (user_id, question, reponse[:500]))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, limit=5):
    conn = sqlite3.connect('kennyson_memory.db')
    c = conn.cursor()
    c.execute('SELECT question, reponse FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', 
              (user_id, limit))
    results = c.fetchall()
    conn.close()
    return results

def kennyson_answer(question, user_id=None):
    # Récupérer les données externes si pertinent
    external_data = ""
    q_lower = question.lower()
    
    if "pib" in q_lower or "gdp" in q_lower:
        gdp = get_worldbank_gdp()
        if gdp:
            external_data += f"📊 {gdp}\n"
    elif "bitcoin" in q_lower or "crypto" in q_lower:
        crypto = get_crypto_price()
        if crypto:
            external_data += f"{crypto}\n"
    elif "météo" in q_lower or "temps" in q_lower:
        weather = get_weather_meteo()
        if weather:
            external_data += f"{weather}\n"
    
    # Récupérer historique
    history_context = ""
    if user_id:
        history = get_conversation_history(user_id, 3)
        if history:
            history_context = "Contexte (conversations récentes) :\n"
            for q, r in history:
                history_context += f"User: {q[:100]}\n"
                history_context += f"Assistant: {r[:100]}...\n\n"
    
    if not GROQ_API_KEY:
        return f"{external_data}\n\nBonjour ! Je suis KENNYSON OURAGAN. Pour fonctionner pleinement, j'ai besoin d'une clé API Groq. Ajoute-la dans les variables d'environnement Render.\n\nQue puis-je faire pour vous aujourd'hui ?"
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{history_context}\nDonnées externes:\n{external_data}\n\nQuestion: {question}"}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=45)
        if r.status_code == 200:
            reponse = r.json()['choices'][0]['message']['content']
            if user_id:
                save_conversation(user_id, question, reponse)
            return reponse
        return "Désolé, je rencontre une difficulté technique. Veuillez réessayer dans quelques instants."
    except Exception as e:
        return f"{external_data}\n\nJe suis KENNYSON OURAGAN, votre assistant intelligent.\n\n{question[:100]}...\n\nJe peux vous aider avec :\n• Questions économiques (PIB, inflation)\n• Cryptomonnaies\n• Météo\n• Actualités\n• Définitions\n\nPosez votre question plus précisément !"

# ==================================================
# AUTHENTIFICATION
# ==================================================
users = {}
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email, pwd, name = data.get('email'), data.get('password'), data.get('name')
    if email in users: return jsonify({"error": "Email existe déjà"}), 400
    if '@' not in email or len(pwd) < 6: return jsonify({"error": "Email ou mot de passe invalide"}), 400
    users[email] = {"name": name, "password": hash_password(pwd), "email": email}
    return jsonify({"message": "Compte créé !"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email, pwd = data.get('email'), data.get('password')
    user = users.get(email)
    if not user or user['password'] != hash_password(pwd):
        return jsonify({"error": "Identifiants incorrects"}), 401
    session['user'] = email
    return jsonify({"token": secrets.token_hex(32), "user": {"name": user['name'], "email": user['email']}}), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"message": "Déconnecté"}), 200

@app.route('/api/me')
def me():
    email = session.get('user')
    if not email: return jsonify({"error": "Non authentifié"}), 401
    return jsonify(users[email]), 200

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    question = data.get('question', '')
    user_id = session.get('user')
    if not question:
        return jsonify({"reponse": "Bonjour ! Je suis KENNYSON OURAGAN. Que puis-je faire pour vous aujourd'hui ?"})
    reponse = kennyson_answer(question, user_id)
    return jsonify({"reponse": reponse})

# ==================================================
# PAGE ACCUEIL ET CHAT (STYLE CHATGPT COMPLET)
# ==================================================
@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>KENNYSON OURAGAN · Assistant intelligent</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #343541;
            color: #ececec;
            height: 100vh;
            overflow: hidden;
        }

        /* Layout principal */
        .app {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        /* Sidebar gauche (nouvelle conversation) */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 260px;
            height: 100vh;
            background: #202123;
            transform: translateX(-100%);
            transition: transform 0.3s ease;
            z-index: 200;
            display: flex;
            flex-direction: column;
            padding: 20px;
        }

        .sidebar.open {
            transform: translateX(0);
        }

        .sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .new-chat-btn {
            background: #e94560;
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
            font-size: 14px;
        }

        .close-sidebar {
            background: none;
            border: none;
            color: #8e8ea0;
            font-size: 20px;
            cursor: pointer;
        }

        .sidebar-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 199;
            display: none;
        }

        .sidebar-overlay.open {
            display: block;
        }

        /* Header */
        .header {
            background: #202123;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            flex-shrink: 0;
        }

        .menu-btn {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
        }

        .menu-btn:hover {
            background: #2a2b32;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .logo-icon {
            background: linear-gradient(135deg, #e94560, #ff5a7c);
            width: 34px;
            height: 34px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
        }

        .logo-text h1 {
            font-size: 16px;
            font-weight: 600;
            color: white;
        }

        .logo-text p {
            font-size: 11px;
            color: #8e8ea0;
        }

        .header-actions {
            display: flex;
            gap: 8px;
        }

        .header-btn {
            background: none;
            border: none;
            color: #8e8ea0;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            transition: 0.2s;
        }

        .header-btn:hover {
            background: #2a2b32;
            color: white;
        }

        /* Zone de chat */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            scroll-behavior: smooth;
        }

        /* Messages style ChatGPT */
        .message {
            padding: 24px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }

        .message.user {
            background: #343541;
        }

        .message.assistant {
            background: #444654;
        }

        .message-content {
            max-width: 800px;
            margin: 0 auto;
            display: flex;
            gap: 24px;
        }

        .avatar {
            width: 30px;
            height: 30px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 500;
            flex-shrink: 0;
        }

        .avatar.user {
            background: #10a37f;
        }

        .avatar.assistant {
            background: #e94560;
        }

        .text {
            flex: 1;
            line-height: 1.65;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 15px;
        }

        .text p {
            margin-bottom: 12px;
        }

        .text strong {
            color: #e94560;
        }

        .text code {
            background: rgba(0,0,0,0.3);
            padding: 2px 6px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 13px;
        }

        /* Zone d'input */
        .input-area {
            background: #202123;
            padding: 16px 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            flex-shrink: 0;
        }

        .input-wrapper {
            max-width: 800px;
            margin: 0 auto;
            position: relative;
        }

        textarea {
            width: 100%;
            background: #40414f;
            border: none;
            border-radius: 12px;
            padding: 12px 48px 12px 16px;
            color: white;
            font-family: inherit;
            font-size: 15px;
            resize: none;
            line-height: 1.5;
        }

        textarea:focus {
            outline: none;
            background: #4a4b5a;
        }

        textarea::placeholder {
            color: #8e8ea0;
        }

        .send-btn {
            position: absolute;
            right: 12px;
            bottom: 10px;
            background: #e94560;
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
            color: white;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }

        .send-btn:hover {
            background: #ff5a7c;
        }

        /* Suggestions */
        .suggestions {
            max-width: 800px;
            margin: 12px auto 0;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .suggestion-chip {
            background: #2a2b32;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
            color: #ececec;
        }

        .suggestion-chip:hover {
            background: #e94560;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 8px;
            font-size: 11px;
            color: #565869;
            background: #202123;
            border-top: 1px solid rgba(255,255,255,0.05);
        }

        /* Typing indicator */
        .typing-indicator {
            display: flex;
            gap: 6px;
            align-items: center;
            padding: 8px 0;
        }

        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: #8e8ea0;
            border-radius: 50%;
            animation: pulse 1.4s infinite;
        }

        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes pulse {
            0%, 60%, 100% { opacity: 0.4; transform: scale(0.8); }
            30% { opacity: 1; transform: scale(1.2); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #202123;
        }
        ::-webkit-scrollbar-thumb {
            background: #565869;
            border-radius: 4px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .message-content {
                padding: 0 12px;
            }
            .text {
                font-size: 14px;
            }
            .suggestions {
                padding: 0 12px;
            }
        }
    </style>
</head>
<body>
    <div class="sidebar-overlay" id="sidebarOverlay"></div>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <button class="new-chat-btn" id="newChatSidebarBtn">✨ Nouvelle conversation</button>
            <button class="close-sidebar" id="closeSidebarBtn">✕</button>
        </div>
        <div style="font-size: 12px; color: #565869; text-align: center; margin-top: auto; padding-top: 20px;">
            KENNYSON OURAGAN<br>Assistant intelligent
        </div>
    </div>

    <div class="app">
        <div class="header">
            <button class="menu-btn" id="menuBtn">☰</button>
            <div class="logo-area">
                <div class="logo-icon">K</div>
                <div class="logo-text">
                    <h1>KENNYSON OURAGAN</h1>
                    <p>Assistant intelligent · Économie · Crypto · Météo</p>
                </div>
            </div>
            <div class="header-actions">
                <button class="header-btn" id="newChatTopBtn">✨ Nouveau chat</button>
                <button class="header-btn" id="loginBtn">🔐 Connexion</button>
            </div>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="message assistant">
                <div class="message-content">
                    <div class="avatar assistant">K</div>
                    <div class="text">
                        <strong>Bonjour ! Je suis KENNYSON OURAGAN.</strong><br><br>
                        Je suis votre assistant intelligent, conçu pour vous aider avec :<br><br>
                        📊 <strong>Économie</strong> – PIB, inflation, données Banque mondiale<br>
                        💰 <strong>Cryptomonnaies</strong> – Prix Bitcoin, Ethereum, tendances<br>
                        🌤️ <strong>Météo</strong> – Conditions actuelles<br>
                        📰 <strong>Actualités</strong> – Infos économiques récentes<br>
                        📖 <strong>Définitions</strong> – Explications claires<br><br>
                        <strong>Comment m'utiliser ?</strong><br>
                        Posez-moi une question directement, ou choisissez un exemple ci-dessous.<br><br>
                        <em>✨ Je me souviens de nos conversations et m'adapte à vous !</em>
                    </div>
                </div>
            </div>
        </div>

        <div class="input-area">
            <div class="input-wrapper">
                <textarea id="questionInput" rows="1" placeholder="Posez votre question..."></textarea>
                <button class="send-btn" id="sendBtn">➤</button>
            </div>
            <div class="suggestions">
                <div class="suggestion-chip" data-question="Quel est le PIB de la RDC ?">📊 PIB de la RDC</div>
                <div class="suggestion-chip" data-question="Quel est le prix du Bitcoin ?">💰 Prix du Bitcoin</div>
                <div class="suggestion-chip" data-question="Quelle est la météo à Kinshasa ?">🌤️ Météo à Kinshasa</div>
                <div class="suggestion-chip" data-question="Explique-moi l'inflation simplement">📖 Définition inflation</div>
            </div>
        </div>
        <div class="footer">
            KENNYSON OURAGAN · Assistant intelligent · Gratuit
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const textarea = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');

        // Auto-resize textarea
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Menu sidebar
        document.getElementById('menuBtn').addEventListener('click', () => {
            sidebar.classList.add('open');
            sidebarOverlay.classList.add('open');
        });
        document.getElementById('closeSidebarBtn').addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('open');
        });
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('open');
        });

        // Fonctions
        function addMessage(text, role) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="avatar ${role}">${role === 'user' ? '👤' : 'K'}</div>
                    <div class="text">${formatText(text)}</div>
                </div>
            `;
            chatContainer.appendChild(messageDiv);
            scrollToBottom();
        }

        function formatText(text) {
            let formatted = text.replace(/\\n/g, '<br>');
            formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            formatted = formatted.replace(/`(.*?)`/g, '<code>$1</code>');
            return formatted;
        }

        function addTypingIndicator() {
            const id = 'typing-' + Date.now();
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant';
            typingDiv.id = id;
            typingDiv.innerHTML = `
                <div class="message-content">
                    <div class="avatar assistant">K</div>
                    <div class="text"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
                </div>
            `;
            chatContainer.appendChild(typingDiv);
            scrollToBottom();
            return id;
        }

        function removeTypingIndicator(id) {
            const element = document.getElementById(id);
            if (element) element.remove();
        }

        function scrollToBottom() {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const question = textarea.value.trim();
            if (!question) return;

            addMessage(question, 'user');
            textarea.value = '';
            textarea.style.height = 'auto';

            const typingId = addTypingIndicator();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                const data = await response.json();
                removeTypingIndicator(typingId);
                addMessage(data.reponse, 'assistant');
            } catch (error) {
                removeTypingIndicator(typingId);
                addMessage("Désolé, une erreur technique s'est produite. Veuillez réessayer.", 'assistant');
            }
        }

        // Événements
        sendBtn.addEventListener('click', sendMessage);
        textarea.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                textarea.value = chip.dataset.question;
                sendMessage();
            });
        });

        document.getElementById('newChatTopBtn').addEventListener('click', () => {
            chatContainer.innerHTML = '';
            addMessage("✨ Nouvelle conversation démarrée ! Comment puis-je vous aider aujourd'hui ?", 'assistant');
        });

        document.getElementById('newChatSidebarBtn').addEventListener('click', () => {
            chatContainer.innerHTML = '';
            addMessage("✨ Nouvelle conversation démarrée ! Comment puis-je vous aider aujourd'hui ?", 'assistant');
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('open');
        });

        document.getElementById('loginBtn').addEventListener('click', () => {
            window.location.href = '/login';
        });

        // Vérifier token
        const token = localStorage.getItem('token');
        if (token) {
            fetch('/api/me').then(res => {
                if (res.ok) document.getElementById('loginBtn').innerHTML = '👤 Mon compte';
                else localStorage.removeItem('token');
            });
        }
    </script>
</body>
</html>
    '''

# ==================================================
# PAGE LOGIN
# ==================================================
LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Connexion</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #343541; color: #ececec; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .login-container { background: #202123; padding: 40px; border-radius: 16px; width: 100%; max-width: 420px; }
        h2 { margin-bottom: 8px; color: #e94560; font-size: 24px; }
        .subtitle { font-size: 13px; color: #8e8ea0; margin-bottom: 28px; }
        input { width: 100%; padding: 12px 14px; margin-bottom: 14px; background: #40414f; border: none; border-radius: 8px; color: white; font-size: 14px; }
        input:focus { outline: none; background: #4a4b5a; }
        button { width: 100%; padding: 12px; background: #e94560; border: none; border-radius: 8px; color: white; font-weight: 500; cursor: pointer; font-size: 14px; transition: 0.2s; }
        button:hover { background: #ff5a7c; }
        .toggle { text-align: center; margin-top: 16px; font-size: 13px; color: #8e8ea0; cursor: pointer; }
        .toggle:hover { color: #e94560; }
        .message { margin-top: 16px; text-align: center; font-size: 13px; }
        .error { color: #e94560; }
        .success { color: #10a37f; }
        .back-link { display: block; text-align: center; margin-top: 20px; color: #565869; text-decoration: none; font-size: 12px; }
        .back-link:hover { color: #e94560; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>KENNYSON OURAGAN</h2>
        <div class="subtitle">Assistant intelligent · Gratuit</div>
        
        <div id="registerForm">
            <input type="text" id="regName" placeholder="Nom">
            <input type="email" id="regEmail" placeholder="Email">
            <input type="password" id="regPassword" placeholder="Mot de passe (min 6)">
            <button onclick="register()">Créer un compte</button>
            <div class="toggle" onclick="showLogin()">Déjà un compte ? Se connecter</div>
        </div>
        
        <div id="loginForm" style="display:none;">
            <input type="email" id="loginEmail" placeholder="Email">
            <input type="password" id="loginPassword" placeholder="Mot de passe">
            <button onclick="login()">Se connecter</button>
            <div class="toggle" onclick="showRegister()">Pas de compte ? S'inscrire</div>
        </div>
        
        <div id="msg" class="message"></div>
        <a href="/" class="back-link">← Retour à l'accueil</a>
    </div>
    <script>
        function showLogin() { document.getElementById('registerForm').style.display = 'none'; document.getElementById('loginForm').style.display = 'block'; }
        function showRegister() { document.getElementById('registerForm').style.display = 'block'; document.getElementById('loginForm').style.display = 'none'; }
        async function register() {
            let name = document.getElementById('regName').value;
            let email = document.getElementById('regEmail').value;
            let password = document.getElementById('regPassword').value;
            if (!email.includes('@')) { showMsg('Email invalide', true); return; }
            if (password.length < 6) { showMsg('Mot de passe trop court', true); return; }
            let res = await fetch('/api/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, email, password }) });
            let data = await res.json();
            if (res.ok) { showMsg('Compte créé ! Connectez-vous.', false); setTimeout(showLogin, 1500); }
            else { showMsg(data.error, true); }
        }
        async function login() {
            let email = document.getElementById('loginEmail').value;
            let password = document.getElementById('loginPassword').value;
            let res = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
            let data = await res.json();
            if (res.ok) { localStorage.setItem('token', data.token); window.location.href = '/'; }
            else { showMsg(data.error, true); }
        }
        function showMsg(msg, isError) { let div = document.getElementById('msg'); div.textContent = msg; div.className = isError ? 'message error' : 'message success'; setTimeout(() => div.textContent = '', 3000); }
    </script>
</body>
</html>
'''

@app.route('/login')
def login_page():
    return LOGIN_PAGE

@app.route('/mon-compte')
def mon_compte():
    return '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Mon compte</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #343541; color: #ececec; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .account-container { background: #202123; padding: 40px; border-radius: 16px; width: 100%; max-width: 420px; text-align: center; }
        .avatar { background: linear-gradient(135deg, #e94560, #ff5a7c); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 40px; margin: 0 auto 20px; }
        h2 { margin-bottom: 8px; font-size: 22px; }
        .email { color: #8e8ea0; margin-bottom: 24px; }
        button { padding: 12px 24px; background: #e94560; border: none; border-radius: 8px; color: white; font-weight: 500; cursor: pointer; font-size: 14px; transition: 0.2s; }
        button:hover { background: #ff5a7c; }
        .back-link { display: block; margin-top: 20px; color: #565869; text-decoration: none; font-size: 12px; }
        .back-link:hover { color: #e94560; }
    </style>
</head>
<body>
    <div class="account-container" id="accountInfo">
        <div class="avatar">👤</div>
        <div id="userData">Chargement...</div>
        <button onclick="logout()">Se déconnecter</button>
        <a href="/" class="back-link">← Retour à KENNYSON</a>
    </div>
    <script>
        async function loadUser() { let res = await fetch('/api/me'); if (res.ok) { let user = await res.json(); document.getElementById('userData').innerHTML = `<h2>${user.name}</h2><div class="email">${user.email}</div>`; } else { window.location.href = '/login'; } }
        async function logout() { await fetch('/api/logout', {method: 'POST'}); localStorage.removeItem('token'); window.location.href = '/'; }
        loadUser();
    </script>
</body>
</html>
    '''

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
