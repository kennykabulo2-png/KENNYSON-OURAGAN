from flask import Flask, jsonify, request, session
import hashlib
import secrets
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'kennyson_ouragan_secret_2026'

# ==================================================
# CONFIGURATIONS API
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY', '')

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GNEWS_URL = "https://gnews.io/api/v4/search"

# ==================================================
# BASE DE DONNÉES ÉCONOMIQUE MONDIALE
# ==================================================
ECONOMIES_MONDIALES = {
    "États-Unis": {"code": "US", "pib": 25400000, "inflation": 3.2, "croissance": 2.1, "monnaie": "$", "chomage": 3.8},
    "Chine": {"code": "CN", "pib": 17800000, "inflation": 1.8, "croissance": 5.2, "monnaie": "¥", "chomage": 5.0},
    "France": {"code": "FR", "pib": 2780000, "inflation": 2.5, "croissance": 1.8, "monnaie": "€", "chomage": 7.2},
    "RDC": {"code": "CD", "pib": 65000, "inflation": 18.5, "croissance": 4.5, "monnaie": "FC", "chomage": 22.0},
    "Nigeria": {"code": "NG", "pib": 440000, "inflation": 24.5, "croissance": 2.9, "monnaie": "₦", "chomage": 33.0},
    "Afrique du Sud": {"code": "ZA", "pib": 419000, "inflation": 5.5, "croissance": 1.2, "monnaie": "R", "chomage": 32.0},
    "Brésil": {"code": "BR", "pib": 1920000, "inflation": 4.6, "croissance": 2.5, "monnaie": "R$", "chomage": 8.5},
    "Inde": {"code": "IN", "pib": 3730000, "inflation": 5.2, "croissance": 6.5, "monnaie": "₹", "chomage": 6.8},
    "Allemagne": {"code": "DE", "pib": 4080000, "inflation": 2.1, "croissance": 1.5, "monnaie": "€", "chomage": 3.1},
    "Japon": {"code": "JP", "pib": 4230000, "inflation": 1.5, "croissance": 1.8, "monnaie": "¥", "chomage": 2.6},
    "Royaume-Uni": {"code": "GB", "pib": 3070000, "inflation": 2.8, "croissance": 1.9, "monnaie": "£", "chomage": 4.0},
    "Canada": {"code": "CA", "pib": 2140000, "inflation": 2.4, "croissance": 2.2, "monnaie": "C$", "chomage": 5.1},
    "Australie": {"code": "AU", "pib": 1690000, "inflation": 2.6, "croissance": 2.3, "monnaie": "A$", "chomage": 3.7},
    "Russie": {"code": "RU", "pib": 2240000, "inflation": 6.5, "croissance": 1.1, "monnaie": "₽", "chomage": 3.9},
    "Turquie": {"code": "TR", "pib": 1080000, "inflation": 45.0, "croissance": 3.5, "monnaie": "₺", "chomage": 10.2},
}

# ==================================================
# FONCTIONS GNEWS
# ==================================================
def get_international_news(query, pays=None):
    if not GNEWS_API_KEY:
        return []
    
    recherche = f"{query} {pays}" if pays else query
    params = {
        "q": recherche,
        "token": GNEWS_API_KEY,
        "lang": "fr",
        "max": 5,
        "country": "us,fr,cd,gb,ca,ng,za,de"
    }
    
    try:
        response = requests.get(GNEWS_URL, params=params, timeout=15)
        if response.status_code == 200:
            return response.json().get("articles", [])
        return []
    except:
        return []

def format_news(articles):
    if not articles:
        return "📭 Aucune actualité récente majeure détectée."
    
    text = "\n📰 **ACTUALITÉS ÉCONOMIQUES RÉCENTES :**\n\n"
    for i, a in enumerate(articles[:4], 1):
        text += f"{i}. **{a.get('title', 'Sans titre')}**\n   📍 {a.get('source', {}).get('name', 'Source')}\n   📝 {a.get('description', '')[:120]}...\n\n"
    return text

# ==================================================
# FONCTION IA
# ==================================================
SYSTEM_PROMPT = """Tu es KENNYSON OURAGAN, un expert économique international. Tu réponds de manière professionnelle, structurée et précise.

Structure ta réponse ainsi :
📊 **CHIFFRES CLÉS** : donne les données essentielles
🔍 **ANALYSE** : explique la situation
⚡ **FACTEURS CLÉS** : liste les 3-4 facteurs déterminants
🎯 **RECOMMANDATIONS** : donne des conseils actionnables
🔮 **PRÉVISION** : projette les 12-18 prochains mois

Sois concis, factuel et utile. Termine par une question ouverte pour engager l'utilisateur."""

def kennyson_answer(question):
    # Détection des mots-clés pays
    pays_mentionne = None
    for pays in ECONOMIES_MONDIALES.keys():
        if pays.lower() in question.lower():
            pays_mentionne = pays
            break
    
    # Récupération des actualités si pertinent
    news_context = ""
    if any(word in question.lower() for word in ["économie", "actualité", "crise", "marché", "tendance"]):
        news = get_international_news("économie", pays_mentionne)
        news_context = format_news(news)
    
    # Données économiques du pays
    eco_context = ""
    if pays_mentionne and pays_mentionne in ECONOMIES_MONDIALES:
        data = ECONOMIES_MONDIALES[pays_mentionne]
        eco_context = f"""
📊 **DONNÉES {pays_mentionne.upper()} :**
- PIB : {data['pib']:,} M$ | Croissance : {data['croissance']}%
- Inflation : {data['inflation']}% | Chômage : {data['chomage']}%
- Monnaie : {data['monnaie']}
"""
    
    if not GROQ_API_KEY:
        return f"""📊 **KENNYSON OURAGAN**\n\n{eco_context}\n\n{news_context}\n\n🎯 **Recommandation :** Analyse les données ci-dessus avant d'investir.\n\n🔮 **Question :** Quel secteur t'intéresse particulièrement ?"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question : {question}\n\n{eco_context}\n\n{news_context}\n\nRéponds de manière professionnelle et structurée."}
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=45)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        return f"📊 **KENNYSON OURAGAN**\n\n{eco_context}\n\n{news_context}\n\n🎯 Analyse basée sur les données disponibles.\n\n🔮 Une question précise ?"
    except:
        return f"📊 **KENNYSON OURAGAN**\n\n{eco_context}\n\n{news_context}\n\n🎯 Données chargées. L'IA répondra dans quelques secondes.\n\n🔮 Reformule ta question si besoin."

# ==================================================
# AUTHENTIFICATION
# ==================================================
users = {}
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email, pwd, name = data.get('email'), data.get('password'), data.get('name')
    if email in users: return jsonify({"error": "Email existe"}), 400
    if '@' not in email or len(pwd) < 6: return jsonify({"error": "Email ou mot de passe invalide"}), 400
    users[email] = {"name": name, "password": hash_password(pwd), "email": email}
    return jsonify({"message": "Compte KENNYSON créé !"}), 201

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
    if not question:
        return jsonify({"reponse": "Pose ta question, KENNYSON OURAGAN répond."})
    reponse = kennyson_answer(question)
    return jsonify({"reponse": reponse})

# ==================================================
# INTERFACE STYLE CHATGPT
# ==================================================
@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>KENNYSON · Intelligence Économique</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: #343541;
            color: #ececec;
            height: 100vh;
            overflow: hidden;
        }

        /* Layout principal style ChatGPT */
        .app {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        /* Header */
        .header {
            background: #202123;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            background: #e94560;
            width: 32px;
            height: 32px;
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
            letter-spacing: 1px;
        }

        .header-actions {
            display: flex;
            gap: 12px;
        }

        .header-btn {
            background: none;
            border: none;
            color: #8e8ea0;
            cursor: pointer;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            transition: 0.2s;
        }

        .header-btn:hover {
            background: #2a2b32;
            color: white;
        }

        /* Zone de chat principale */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 0;
            scroll-behavior: smooth;
        }

        /* Messages style ChatGPT */
        .message {
            padding: 20px 15px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }

        .message.user {
            background: #343541;
        }

        .message.bot {
            background: #444654;
        }

        .message-content {
            max-width: 800px;
            margin: 0 auto;
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }

        .avatar {
            width: 30px;
            height: 30px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: bold;
            flex-shrink: 0;
        }

        .avatar.user {
            background: #10a37f;
        }

        .avatar.bot {
            background: #e94560;
        }

        .text {
            flex: 1;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 14px;
        }

        .text p {
            margin-bottom: 12px;
        }

        .text strong {
            color: #e94560;
        }

        /* Zone d'input style ChatGPT */
        .input-area {
            background: #202123;
            padding: 12px 15px;
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
            padding: 12px 50px 12px 16px;
            color: white;
            font-family: inherit;
            font-size: 14px;
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
            font-size: 12px;
            font-weight: bold;
        }

        .send-btn:hover {
            background: #ff5a7c;
        }

        /* Suggestions rapides */
        .suggestions {
            max-width: 800px;
            margin: 10px auto 0;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .suggestion-chip {
            background: #2a2b32;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
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

        ::-webkit-scrollbar-thumb:hover {
            background: #6e6f80;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .message-content {
                padding: 0 10px;
            }
            .text {
                font-size: 13px;
            }
            .suggestions {
                padding: 0 10px;
            }
        }

        /* Animation chargement */
        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }

        .typing-indicator {
            display: flex;
            gap: 4px;
            align-items: center;
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
    </style>
</head>
<body>
    <div class="app">
        <div class="header">
            <div class="logo-area">
                <div class="logo-icon">K</div>
                <div class="logo-text">
                    <h1>KENNYSON OURAGAN</h1>
                    <p>Intelligence Économique Internationale</p>
                </div>
            </div>
            <div class="header-actions">
                <button class="header-btn" id="newChatBtn">✨ Nouvelle conversation</button>
                <button class="header-btn" id="loginBtn">🔐 Connexion</button>
            </div>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="message bot">
                <div class="message-content">
                    <div class="avatar bot">K</div>
                    <div class="text">
                        <strong>KENNYSON OURAGAN</strong><br><br>
                        Bonjour ! Je suis votre assistant économique international.<br><br>
                        <strong>Je peux vous aider avec :</strong><br>
                        • 📊 Analyse économique par pays (USA, Chine, RDC, etc.)<br>
                        • 🌍 Comparaisons internationales<br>
                        • 📰 Actualités économiques en temps réel<br>
                        • 💰 Cryptomonnaies et investissements<br>
                        • 🔮 Prévisions et recommandations<br><br>
                        <strong>Exemples de questions :</strong><br>
                        "Quelle est la situation économique des États-Unis ?"<br>
                        "Compare l'économie de la France et de l'Allemagne"<br>
                        "Dernières actualités économiques en RDC"<br>
                        "Où investir en 2026 ?"<br><br>
                        <em>✨ Posez votre question, je vous réponds avec précision et structure.</em>
                    </div>
                </div>
            </div>
        </div>

        <div class="input-area">
            <div class="input-wrapper">
                <textarea id="questionInput" rows="1" placeholder="Posez votre question économique..."></textarea>
                <button class="send-btn" id="sendBtn">➤</button>
            </div>
            <div class="suggestions">
                <div class="suggestion-chip" data-question="Analyse l'économie des États-Unis">🇺🇸 États-Unis</div>
                <div class="suggestion-chip" data-question="Compare la France et l'Allemagne économiquement">🇫🇷 vs 🇩🇪 Comparaison</div>
                <div class="suggestion-chip" data-question="Quelles sont les dernières actualités économiques en RDC ?">🇨🇩 Actualités RDC</div>
                <div class="suggestion-chip" data-question="Où investir en 2026 ?">💸 Investir en 2026</div>
            </div>
        </div>
        <div class="footer">
            <span>KENNYSON OURAGAN · Données actualisées · Économie mondiale</span>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const textarea = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');

        // Auto-resize textarea
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Envoyer message
        async function sendMessage() {
            const question = textarea.value.trim();
            if (!question) return;

            // Ajouter message utilisateur
            addMessage(question, 'user');
            textarea.value = '';
            textarea.style.height = 'auto';

            // Ajouter indicateur de chargement
            const loadingId = addTypingIndicator();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                const data = await response.json();
                removeTypingIndicator(loadingId);
                addMessage(data.reponse, 'bot');
            } catch (error) {
                removeTypingIndicator(loadingId);
                addMessage('⚠️ Désolé, une erreur technique est survenue. Veuillez réessayer.', 'bot');
            }
        }

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
            return text.replace(/\\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        }

        function addTypingIndicator() {
            const id = 'typing-' + Date.now();
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot';
            typingDiv.id = id;
            typingDiv.innerHTML = `
                <div class="message-content">
                    <div class="avatar bot">K</div>
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

        // Événements
        sendBtn.addEventListener('click', sendMessage);
        textarea.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Suggestions
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const question = chip.dataset.question;
                if (question) {
                    textarea.value = question;
                    sendMessage();
                }
            });
        });

        // Nouvelle conversation
        document.getElementById('newChatBtn').addEventListener('click', () => {
            chatContainer.innerHTML = '';
            addMessage("✨ Nouvelle conversation démarrée. Posez votre question économique !", 'bot');
        });

        // Connexion (simple redirection)
        document.getElementById('loginBtn').addEventListener('click', () => {
            window.location.href = '/login';
        });
    </script>
</body>
</html>
    '''

# ==================================================
# PAGE LOGIN STYLE CHATGPT
# ==================================================
LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Connexion</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #343541;
            color: #ececec;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: #202123;
            padding: 40px;
            border-radius: 16px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        h2 { margin-bottom: 8px; color: #e94560; }
        .subtitle { font-size: 13px; color: #8e8ea0; margin-bottom: 24px; }
        input {
            width: 100%;
            padding: 12px;
            margin-bottom: 12px;
            background: #40414f;
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 14px;
        }
        input:focus { outline: none; background: #4a4b5a; }
        button {
            width: 100%;
            padding: 12px;
            background: #e94560;
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            margin-top: 8px;
        }
        button:hover { background: #ff5a7c; }
        .toggle { text-align: center; margin-top: 16px; font-size: 13px; color: #8e8ea0; cursor: pointer; }
        .toggle:hover { color: #e94560; }
        .message { margin-top: 12px; text-align: center; font-size: 13px; color: #10a37f; }
        .error { color: #e94560; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>KENNYSON OURAGAN</h2>
        <div class="subtitle">Intelligence Économique Internationale</div>
        
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
    </div>
    <script>
        function showLogin() {
            document.getElementById('registerForm').style.display = 'none';
            document.getElementById('loginForm').style.display = 'block';
        }
        function showRegister() {
            document.getElementById('registerForm').style.display = 'block';
            document.getElementById('loginForm').style.display = 'none';
        }
        async function register() {
            let name = document.getElementById('regName').value;
            let email = document.getElementById('regEmail').value;
            let password = document.getElementById('regPassword').value;
            if (!email.includes('@')) { showMsg('Email invalide', true); return; }
            if (password.length < 6) { showMsg('Mot de passe trop court', true); return; }
            let res = await fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, email, password})
            });
            let data = await res.json();
            if (res.ok) { showMsg('Compte créé ! Connectez-vous.'); setTimeout(showLogin, 1500); }
            else { showMsg(data.error, true); }
        }
        async function login() {
            let email = document.getElementById('loginEmail').value;
            let password = document.getElementById('loginPassword').value;
            let res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, password})
            });
            let data = await res.json();
            if (res.ok) {
                localStorage.setItem('token', data.token);
                window.location.href = '/';
            } else {
                showMsg(data.error, true);
            }
        }
        function showMsg(msg, isError=false) {
            let div = document.getElementById('msg');
            div.textContent = msg;
            div.className = isError ? 'message error' : 'message';
            setTimeout(() => { div.textContent = ''; }, 3000);
        }
    </script>
</body>
</html>
'''

# ==================================================
# PAGE MON COMPTE
# ==================================================
ACCOUNT_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Mon compte</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #343541;
            color: #ececec;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .account-container {
            background: #202123;
            padding: 40px;
            border-radius: 16px;
            width: 100%;
            max-width: 420px;
            text-align: center;
        }
        .avatar {
            background: #e94560;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            margin: 0 auto 20px;
        }
        h2 { margin-bottom: 8px; }
        .email { color: #8e8ea0; margin-bottom: 24px; }
        button {
            padding: 12px 24px;
            background: #e94560;
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { background: #ff5a7c; }
        .back-link {
            display: block;
            margin-top: 16px;
            color: #8e8ea0;
            text-decoration: none;
            font-size: 13px;
        }
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
        async function loadUser() {
            let res = await fetch('/api/me');
            if (res.ok) {
                let user = await res.json();
                document.getElementById('userData').innerHTML = `
                    <h2>${user.name}</h2>
                    <div class="email">${user.email}</div>
                `;
            } else {
                window.location.href = '/login';
            }
        }
        async function logout() {
            await fetch('/api/logout', {method: 'POST'});
            localStorage.removeItem('token');
            window.location.href = '/';
        }
        loadUser();
    </script>
</body>
</html>
'''

@app.route('/login')
def login_page():
    return LOGIN_PAGE

@app.route('/mon-compte')
def mon_compte():
    return ACCOUNT_PAGE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
