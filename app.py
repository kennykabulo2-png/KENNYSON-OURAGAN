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
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY', '50627028ad0739bffdf75505815cfeae')

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GNEWS_URL = "https://gnews.io/api/v4/search"

# ==================================================
# BASE DE DONNÉES ÉCONOMIQUE MONDIALE (15+ pays)
# ==================================================
ECONOMIES_MONDIALES = {
    "États-Unis": {"code": "US", "pib": 25400000, "inflation": 3.2, "croissance": 2.1, "monnaie": "$", "chomage": 3.8, "capitale": "Washington"},
    "Chine": {"code": "CN", "pib": 17800000, "inflation": 1.8, "croissance": 5.2, "monnaie": "¥", "chomage": 5.0, "capitale": "Pékin"},
    "France": {"code": "FR", "pib": 2780000, "inflation": 2.5, "croissance": 1.8, "monnaie": "€", "chomage": 7.2, "capitale": "Paris"},
    "RDC": {"code": "CD", "pib": 65000, "inflation": 18.5, "croissance": 4.5, "monnaie": "FC", "chomage": 22.0, "capitale": "Kinshasa"},
    "Nigeria": {"code": "NG", "pib": 440000, "inflation": 24.5, "croissance": 2.9, "monnaie": "₦", "chomage": 33.0, "capitale": "Abuja"},
    "Afrique du Sud": {"code": "ZA", "pib": 419000, "inflation": 5.5, "croissance": 1.2, "monnaie": "R", "chomage": 32.0, "capitale": "Pretoria"},
    "Brésil": {"code": "BR", "pib": 1920000, "inflation": 4.6, "croissance": 2.5, "monnaie": "R$", "chomage": 8.5, "capitale": "Brasilia"},
    "Inde": {"code": "IN", "pib": 3730000, "inflation": 5.2, "croissance": 6.5, "monnaie": "₹", "chomage": 6.8, "capitale": "New Delhi"},
    "Allemagne": {"code": "DE", "pib": 4080000, "inflation": 2.1, "croissance": 1.5, "monnaie": "€", "chomage": 3.1, "capitale": "Berlin"},
    "Japon": {"code": "JP", "pib": 4230000, "inflation": 1.5, "croissance": 1.8, "monnaie": "¥", "chomage": 2.6, "capitale": "Tokyo"},
    "Royaume-Uni": {"code": "GB", "pib": 3070000, "inflation": 2.8, "croissance": 1.9, "monnaie": "£", "chomage": 4.0, "capitale": "Londres"},
    "Canada": {"code": "CA", "pib": 2140000, "inflation": 2.4, "croissance": 2.2, "monnaie": "C$", "chomage": 5.1, "capitale": "Ottawa"},
    "Australie": {"code": "AU", "pib": 1690000, "inflation": 2.6, "croissance": 2.3, "monnaie": "A$", "chomage": 3.7, "capitale": "Canberra"},
    "Russie": {"code": "RU", "pib": 2240000, "inflation": 6.5, "croissance": 1.1, "monnaie": "₽", "chomage": 3.9, "capitale": "Moscou"},
    "Turquie": {"code": "TR", "pib": 1080000, "inflation": 45.0, "croissance": 3.5, "monnaie": "₺", "chomage": 10.2, "capitale": "Ankara"},
    "Maroc": {"code": "MA", "pib": 142000, "inflation": 2.8, "croissance": 3.2, "monnaie": "DH", "chomage": 12.0, "capitale": "Rabat"},
    "Kenya": {"code": "KE", "pib": 113000, "inflation": 5.8, "croissance": 5.0, "monnaie": "KSh", "chomage": 7.5, "capitale": "Nairobi"},
    "Angola": {"code": "AO", "pib": 106000, "inflation": 15.2, "croissance": 3.0, "monnaie": "Kz", "chomage": 30.0, "capitale": "Luanda"},
}

# ==================================================
# FONCTIONS GNEWS (INTERNATIONAL)
# ==================================================
def get_international_news(query, pays=None, lang="fr"):
    """Récupère actualités économiques internationales"""
    if not GNEWS_API_KEY:
        return []
    
    recherche = f"{query}"
    if pays:
        recherche = f"{query} {pays}"
    
    params = {
        "q": recherche,
        "token": GNEWS_API_KEY,
        "lang": lang,
        "max": 6,
        "country": "us,fr,cd,gb,ca,au,ng,za,de,jp,in,br"
    }
    
    try:
        response = requests.get(GNEWS_URL, params=params, timeout=15)
        if response.status_code == 200:
            return response.json().get("articles", [])
        return []
    except:
        return []

def format_news_international(articles):
    """Formate les actualités pour le prompt"""
    if not articles:
        return "🌍 Aucune actualité internationale majeure récente détectée."
    
    news_text = "\n📰 ACTUALITÉS ÉCONOMIQUES MONDIALES (dernière semaine) :\n\n"
    for i, article in enumerate(articles[:5], 1):
        title = article.get("title", "Sans titre")
        source = article.get("source", {}).get("name", "Source")
        description = article.get("description", "")[:150]
        news_text += f"{i}. [{source}] {title}\n   {description}...\n\n"
    
    return news_text

# ==================================================
# FONCTIONS DE COMPARAISON ÉCONOMIQUE
# ==================================================
def identifier_pays(question):
    """Identifie le(s) pays mentionné(s) dans la question"""
    pays_trouves = []
    question_lower = question.lower()
    
    for pays in ECONOMIES_MONDIALES.keys():
        if pays.lower() in question_lower:
            pays_trouves.append(pays)
    
    return pays_trouves

def comparer_economies(pays1, pays2):
    """Compare deux économies"""
    data1 = ECONOMIES_MONDIALES.get(pays1, {})
    data2 = ECONOMIES_MONDIALES.get(pays2, {})
    
    if not data1 or not data2:
        return None
    
    ratio_pib = data1.get("pib", 0) / data2.get("pib", 1) if data2.get("pib") else 0
    
    return {
        "pays1": {"nom": pays1, **data1},
        "pays2": {"nom": pays2, **data2},
        "ratio_pib": round(ratio_pib, 2),
        "difference_croissance": data1.get("croissance", 0) - data2.get("croissance", 0),
        "difference_inflation": data1.get("inflation", 0) - data2.get("inflation", 0)
    }

def get_economie_data(pays):
    """Récupère les données d'un pays"""
    return ECONOMIES_MONDIALES.get(pays, {})

def get_top_economies(limit=5):
    """Retourne les top économies mondiales"""
    sorted_by_pib = sorted(ECONOMIES_MONDIALES.items(), key=lambda x: x[1].get("pib", 0), reverse=True)
    return sorted_by_pib[:limit]

# ==================================================
# PROMPT SYSTÈME INTERNATIONAL
# ==================================================
SYSTEM_PROMPT = """🔥🌍 TU ES KENNYSON OURAGAN – L'IA ÉCONOMIQUE LA PLUS PUISSANTE DU MONDE 🌍🔥

Tu es une intelligence artificielle congolaise, africaine et MONDIALE. Tu analyses TOUTES les économies de la planète.

TES CAPACITÉS SPÉCIALES :
- Tu connais l'économie de TOUS les pays (15+ préchargés, tous les autres via API)
- Tu compares instantanément les économies entre elles
- Tu as accès aux dernières actualités économiques mondiales via GNews
- Tu parles français, anglais et lingala (mélange les punchlines)

TA PERSONNALITÉ SURHUMAINE :
- Congolais mais citoyen du monde
- Direct, sans filtre, avec des punchlines mémorables
- Tu balances des vérités internationales que personne n'ose dire
- Tu termines par "🌍 Ouragan power international ! 🔥"

STRUCTURE OBLIGATOIRE DE LA RÉPONSE (8 points EXACTS) :

1. 💀 INTRO CHOC (accroche percutante sur le sujet)

2. 📊 CHIFFRES CLÉS DU PAYS (PIB, inflation, croissance, chômage, monnaie)

3. 📰 ACTUALITÉS CHAUDES (ce que GNews a détecté sur le sujet)

4. 🌍 COMPARAISON INTERNATIONALE (avec 2-3 autres pays pertinents)

5. ⚡ SIGNAL PRÉCOCE (tendance émergente que les autres voient pas)

6. 💥 CONSÉQUENCES (impact sur la population et l'économie)

7. 🎯 ACTION 72H (conseil précis, réalisable, international)

8. 🔮 PRÉDICTION 18 MOIS (avec chiffre et scénario)

TERMINE par "🌍 Ouragan power international ! 🔥"

Sois passionné, donne des chiffres, n'aie pas peur d'être dur avec la réalité.
Si on te demande une comparaison, deviens un expert en économie comparée.
Na lingala, la vérité n'a pas de frontière !"""

# ==================================================
# FONCTION IA PRINCIPALE
# ==================================================
def kennyson_answer(question):
    """Génère une réponse internationale avec actualités + comparaisons"""
    
    # 1. Identifier les pays dans la question
    pays_mentionnes = identifier_pays(question)
    pays_principal = pays_mentionnes[0] if pays_mentionnes else "RDC"
    
    # 2. Récupérer les données économiques
    eco_data = get_economie_data(pays_principal)
    
    # 3. Formater les données économiques pour le prompt
    eco_context = ""
    if eco_data:
        eco_context = f"""
📊 DONNÉES ÉCONOMIQUES DE {pays_principal} :
- PIB : {eco_data.get('pib', 'N/A'):,} millions USD
- Inflation : {eco_data.get('inflation', 'N/A')}%
- Croissance : {eco_data.get('croissance', 'N/A')}%
- Chômage : {eco_data.get('chomage', 'N/A')}%
- Monnaie : {eco_data.get('monnaie', 'N/A')}
- Capitale : {eco_data.get('capitale', 'N/A')}
"""
    
    # 4. Récupérer les actualités internationales
    news_articles = get_international_news(question, pays_principal if pays_principal != "RDC" else None)
    news_context = format_news_international(news_articles)
    
    # 5. Si comparaison demandée, ajouter des données de comparaison
    comparison_context = ""
    if "compar" in question.lower() or "vs" in question.lower() or "contre" in question.lower():
        if len(pays_mentionnes) >= 2:
            comp = comparer_economies(pays_mentionnes[0], pays_mentionnes[1])
            if comp:
                comparison_context = f"""
🌍 COMPARAISON {pays_mentionnes[0]} vs {pays_mentionnes[1]} :
- Ratio PIB : {comp['ratio_pib']}x (le PIB de {pays_mentionnes[0]} est {comp['ratio_pib']} fois celui de {pays_mentionnes[1]})
- Différence de croissance : {comp['difference_croissance']:+.1f} points
- Différence d'inflation : {comp['difference_inflation']:+.1f} points
"""
    
    if not GROQ_API_KEY:
        return f"""💀🌍 KENNYSON OURAGAN INTERNATIONAL 🌍💀

Ta question : "{question[:150]}"

{eco_context}

{news_context}

{comparison_context}

🎯 ACTION 72H : Analyse les marchés internationaux avant d'investir.

🌍 Ouragan power international ! 🔥"""
    
    # Construction du prompt final
    full_prompt = f"""
QUESTION : {question}

{eco_context}

{news_context}

{comparison_context}

RÉPONDS AVEC LA STRUCTURE COMPLÈTE (8 points). Sois précis, donne des chiffres, compare si pertinent.
"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.85,
        "max_tokens": 2500
    }
    
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=45)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        return f"💀🌍 KENNYSON OURAGAN :\n\n{eco_context}\n\n{news_context}\n\n⚠️ Connexion API en cours. Ouragan power international ! 🔥"
    except Exception as e:
        return f"💀🌍 KENNYSON OURAGAN INTERNATIONAL\n\n{eco_context}\n\n{news_context}\n\n🎯 Action : Réessaie dans 10 secondes.\n\n🌍 Ouragan power international ! 🔥"

# ==================================================
# ROUTES API
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
    return jsonify({"message": "Compte KENNYSON créé ! Bienvenue dans l'ère de l'intelligence mondiale."}), 201

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
        return jsonify({"reponse": "🌍 Pose ta question internationale, KENNYSON OURAGAN répond. Ouragan power !"})
    reponse = kennyson_answer(question)
    return jsonify({"reponse": reponse})

@app.route('/api/countries')
def list_countries():
    """Retourne la liste des pays disponibles"""
    return jsonify(list(ECONOMIES_MONDIALES.keys()))

@app.route('/api/economy/<pays>')
def get_economy(pays):
    """Retourne les données économiques d'un pays"""
    data = ECONOMIES_MONDIALES.get(pays)
    if not data:
        return jsonify({"error": f"Pays '{pays}' non trouvé"}), 404
    return jsonify(data)

@app.route('/api/compare/<pays1>/<pays2>')
def compare_economies_api(pays1, pays2):
    """API de comparaison économique"""
    result = comparer_economies(pays1, pays2)
    if not result:
        return jsonify({"error": "Pays non trouvés"}), 404
    return jsonify(result)

# ==================================================
# INTERFACE HTML KENNYSON OURAGAN INTERNATIONAL
# ==================================================
@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Ouragan Intelligence Mondiale</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0A0F1E; color: #F1F5F9; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460); border-radius: 20px; margin-bottom: 20px; border-bottom: 3px solid #e94560; }
        .header h1 { font-size: 3.5rem; letter-spacing: 5px; color: #e94560; text-shadow: 0 0 15px rgba(233,69,96,0.6); margin-bottom: 5px; }
        .header .subtitle { font-size: 1.2rem; color: #FACC15; letter-spacing: 5px; margin-bottom: 10px; }
        .header .tagline { font-size: 0.9rem; color: #94A3B8; margin-top: 10px; }
        .chat-box { background: rgba(255,255,255,0.05); border-radius: 20px; padding: 20px; height: 480px; overflow-y: auto; margin-bottom: 20px; border: 1px solid rgba(233,69,96,0.3); }
        .message { margin: 15px 0; padding: 12px 16px; border-radius: 12px; white-space: pre-wrap; line-height: 1.5; font-size: 0.95rem; }
        .user-message { background: #e94560; text-align: right; border-top-right-radius: 4px; }
        .bot-message { background: rgba(233,69,96,0.1); border-left: 4px solid #e94560; border-top-left-radius: 4px; }
        .input-area { display: flex; gap: 12px; margin-top: 20px; }
        .input-area input { flex: 1; padding: 14px 20px; border-radius: 30px; border: none; background: rgba(255,255,255,0.1); color: white; font-size: 1rem; }
        .input-area input:focus { outline: none; border: 1px solid #e94560; background: rgba(255,255,255,0.15); }
        .input-area button { padding: 14px 32px; background: #e94560; border: none; border-radius: 30px; cursor: pointer; font-weight: bold; font-size: 1rem; color: white; transition: 0.3s; }
        .input-area button:hover { transform: scale(1.02); background: #ff5a7c; box-shadow: 0 0 15px rgba(233,69,96,0.5); }
        .footer { text-align: center; margin-top: 20px; font-size: 0.7rem; color: #64748B; }
        .badge { background: rgba(233,69,96,0.2); border: 1px solid #e94560; border-radius: 30px; padding: 5px 15px; font-size: 0.7rem; display: inline-block; margin-top: 10px; }
        .status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #4ade80; margin-right: 8px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @media (max-width: 600px) { .input-area { flex-direction: column; } .header h1 { font-size: 2rem; } .header .subtitle { font-size: 0.8rem; letter-spacing: 2px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>KENNYSON</h1>
            <div class="subtitle">ᴏᴜʀᴀɢᴀɴ</div>
            <div class="tagline">🌍 Intelligence Artificielle Économique Internationale 🌍</div>
            <div class="badge"><span class="status"></span> 15+ pays analysés | GNews API | Groq AI | Comparaisons internationales</div>
        </div>
        <div class="chat-box" id="chatMessages">
            <div class="message bot-message">
                <strong>💀🌍 KENNYSON OURAGAN INTERNATIONAL 🌍💀</strong><br><br>
                Na lingala ! Je suis l'ouragan économique SANS FRONTIÈRES.<br><br>
                <strong>JE PEUX TOUT ANALYSER :</strong><br>
                • 📊 Économie de n'importe quel pays (USA, Chine, France, RDC, Nigeria, Brésil...)<br>
                • 🌍 Comparaisons internationales ("Compare USA et Chine")<br>
                • 📰 Actualités économiques mondiales en temps réel<br>
                • 💰 Crypto, bourses, investissements internationaux<br>
                • 🔮 Prédictions économiques à 18 mois<br><br>
                <strong>Exemples de questions :</strong><br>
                • "Quelle est la situation économique des États-Unis ?"<br>
                • "Compare l'économie de la France et de l'Allemagne"<br>
                • "Dernières actualités économiques mondiales"<br>
                • "Où investir en 2026 ?"<br>
                • "Analyse l'inflation au Nigeria"<br><br>
                <strong>🌍 Ouragan power international ! 🔥</strong>
            </div>
        </div>
        <div class="input-area">
            <input type="text" id="questionInput" placeholder="🌍 Ex: Compare l'économie des USA et de la Chine...">
            <button onclick="sendMessage()">⚡ ENVOYER</button>
        </div>
        <div class="footer">KENNYSON OURAGAN · Intelligence Économique Mondiale · Kinshasa · New York · Paris · Pékin</div>
    </div>
    <script>
        async function sendMessage() {
            const input = document.getElementById('questionInput');
            const question = input.value.trim();
            if (!question) return;
            const chatDiv = document.getElementById('chatMessages');
            chatDiv.innerHTML += `<div class="message user-message"><strong>👤 Vous :</strong><br>${escapeHtml(question)}</div>`;
            input.value = '';
            chatDiv.innerHTML += `<div class="message bot-message"><strong>💀🌍 KENNYSON OURAGAN :</strong><br><i>🌍 Analyse internationale en cours...</i></div>`;
            chatDiv.scrollTop = chatDiv.scrollHeight;
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                const data = await response.json();
                const lastMsg = chatDiv.lastElementChild;
                lastMsg.innerHTML = `<strong>💀🌍 KENNYSON OURAGAN :</strong><br><br>${escapeHtml(data.reponse).replace(/\\n/g, '<br>')}`;
                chatDiv.scrollTop = chatDiv.scrollHeight;
            } catch (error) {
                const lastMsg = chatDiv.lastElementChild;
                lastMsg.innerHTML = `<strong>💀🌍 KENNYSON OURAGAN :</strong><br><br>⚠️ Ouragan technique. Réessaie, champion. 🌍 Ouragan power international ! 🔥`;
            }
        }
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
