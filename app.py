from flask import Flask, jsonify, request
import requests
import os
import feedparser
import praw
import wikipedia
import json
from datetime import datetime

app = Flask(__name__)

# ==================================================
# CONFIGURATION
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY', '')
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID', '')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET', '')

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==================================================
# 1. SOURCES FONDATIONNELLES (Wikipedia + Wikidata)
# ==================================================
def get_wikipedia_summary(topic):
    """Récupère un résumé Wikipedia (source #1 de ChatGPT)"""
    try:
        wikipedia.set_lang("fr")
        summary = wikipedia.summary(topic, sentences=5)
        return f"📖 **Wikipedia - {topic.capitalize()}** :\n{summary}\n"
    except:
        try:
            wikipedia.set_lang("en")
            summary = wikipedia.summary(topic, sentences=5)
            return f"📖 **Wikipedia - {topic.capitalize()}** :\n{summary}\n"
        except:
            return None

def get_wikidata_info(entity_id):
    """Récupère des données structurées depuis Wikidata"""
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            entities = data.get('entities', {})
            if entity_id in entities:
                labels = entities[entity_id].get('labels', {})
                fr_label = labels.get('fr', {}).get('value', '')
                return fr_label
    except:
        pass
    return None

# ==================================================
# 2. SOURCES DYNAMIQUES (RSS Feeds + Reddit)
# ==================================================
RSS_FEEDS = [
    "https://www.lemonde.fr/rss/une.xml",
    "https://www.lefigaro.fr/rss/figaro_actualites.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.lepoint.fr/feed.xml"
]

def get_rss_news():
    """Récupère les dernières nouvelles des grands médias"""
    results = []
    for feed_url in RSS_FEEDS[:3]:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                results.append({
                    "title": entry.title,
                    "summary": entry.summary[:200] if 'summary' in entry else '',
                    "source": feed.feed.title if 'title' in feed.feed else feed_url,
                    "link": entry.link
                })
        except:
            pass
    return results

def get_reddit_posts(query, limit=5):
    """Récupère des posts Reddit (source #2 de ChatGPT)"""
    if not REDDIT_CLIENT_ID:
        return None
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="KENNYSON-IA/1.0"
        )
        posts = []
        for post in reddit.subreddit("all").search(query, limit=limit):
            posts.append({
                "title": post.title,
                "score": post.score,
                "subreddit": post.subreddit.display_name,
                "url": post.url
            })
        return posts
    except:
        return None

# ==================================================
# 3. SOURCES TEMPS RÉEL (Actualités, Météo, Crypto, Économie)
# ==================================================
def get_worldbank_gdp(country_code="CD"):
    try:
        url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/NY.GDP.MKTP.CD?format=json"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if len(data) > 1 and data[1] and data[1][0].get('value'):
                return int(float(data[1][0]['value']))
    except:
        pass
    return None

def get_worldbank_inflation(country_code="CD"):
    try:
        url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/FP.CPI.TOTL.ZG?format=json"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if len(data) > 1 and data[1] and data[1][0].get('value'):
                return float(data[1][0]['value'])
    except:
        pass
    return None

def get_crypto_price(coin="bitcoin"):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur", timeout=8)
        if r.status_code == 200:
            data = r.json()
            if coin in data:
                return {"usd": data[coin]['usd'], "eur": data[coin]['eur']}
    except:
        pass
    return None

def get_weather(city):
    try:
        geo = requests.get(f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1", 
                          headers={'User-Agent': 'KENNYSON-IA/1.0'}, timeout=8)
        if geo.status_code == 200 and geo.json():
            lat = geo.json()[0]['lat']
            lon = geo.json()[0]['lon']
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=8)
            if r.status_code == 200:
                return r.json()['current_weather']['temperature']
    except:
        pass
    return None

def get_news_gnews(query):
    if not GNEWS_API_KEY:
        return None
    try:
        r = requests.get(f"https://gnews.io/api/v4/search?q={query}&token={GNEWS_API_KEY}&lang=fr&max=5", timeout=8)
        if r.status_code == 200:
            articles = r.json().get('articles', [])
            return articles[:5]
    except:
        pass
    return None

# ==================================================
# 4. MÉMOIRE VECTORIELLE (Qdrant simplifié)
# ==================================================
class SimpleVectorMemory:
    def __init__(self):
        self.documents = []
    
    def add(self, content, source):
        self.documents.append({"content": content[:500], "source": source, "timestamp": datetime.now().isoformat()})
    
    def search(self, query, limit=3):
        query_words = set(query.lower().split())
        scored = []
        for doc in self.documents:
            words = set(doc["content"].lower().split())
            score = len(query_words & words)
            scored.append((score, doc))
        scored.sort(reverse=True)
        return scored[:limit]

memory = SimpleVectorMemory()

# ==================================================
# 5. IA CENTRALE AVEC TOUTES LES SOURCES
# ==================================================
COUNTRIES = {
    "rdc": "CD", "usa": "US", "france": "FR", "chine": "CN", "allemagne": "DE",
    "japon": "JP", "royaume-uni": "GB", "canada": "CA", "bresil": "BR", "inde": "IN"
}

SYSTEM_PROMPT = """Tu es KENNYSON OURAGAN, un assistant intelligent de niveau ChatGPT.

TES SOURCES D'INFORMATION :
1. Wikipedia (savoir général structuré)
2. RSS des grands médias (Le Monde, Figaro, NYT, BBC)
3. Reddit (discussions et opinions)
4. Banque mondiale (données économiques)
5. GNews (actualités en temps réel)
6. Open-Meteo (météo mondiale)
7. CoinGecko (cryptomonnaies)

RÈGLES :
- Réponds en français de manière professionnelle
- Cite TES SOURCES à la fin de ta réponse
- Structure ta réponse en paragraphes
- Sois précis, donne des chiffres
- N'invente jamais d'informations

Tu es une IA internationale. Tu connais TOUS les pays.
"""

def get_all_sources(question):
    """Rassemble les informations de toutes les sources"""
    q = question.lower()
    context = ""
    
    # 1. Wikipedia
    if len(q.split()) > 2:
        topic = q.split()[-1]
        wiki = get_wikipedia_summary(topic)
        if wiki:
            context += f"\n📖 **SOURCE WIKIPEDIA** :\n{wiki}\n"
            memory.add(wiki, "wikipedia")
    
    # 2. RSS Feeds (actualités médias)
    rss_news = get_rss_news()
    if rss_news:
        context += "\n📰 **ACTUALITÉS DES MÉDIAS** :\n"
        for article in rss_news[:3]:
            context += f"• {article['title']}\n  📍 {article['source']}\n\n"
            memory.add(article['title'], article['source'])
    
    # 3. Reddit
    if REDDIT_CLIENT_ID:
        reddit_posts = get_reddit_posts(q, 3)
        if reddit_posts:
            context += "\n💬 **DISCUSSIONS REDDIT** :\n"
            for post in reddit_posts:
                context += f"• r/{post['subreddit']}: {post['title']} (👍 {post['score']})\n"
                memory.add(post['title'], f"reddit.com/r/{post['subreddit']}")
    
    # 4. Données économiques (Banque mondiale)
    for country_name, code in COUNTRIES.items():
        if country_name in q:
            gdp = get_worldbank_gdp(code)
            inflation = get_worldbank_inflation(code)
            if gdp:
                context += f"\n📊 **BANQUE MONDIALE - {country_name.upper()}** :\n"
                context += f"   PIB: {gdp:,} USD\n"
                if inflation:
                    context += f"   Inflation: {inflation:.1f}%\n"
            break
    
    # 5. Crypto
    if "bitcoin" in q or "btc" in q:
        btc = get_crypto_price("bitcoin")
        if btc:
            context += f"\n💰 **COINGECKO** : Bitcoin: ${btc['usd']:,} USD\n"
    
    # 6. Météo
    for word in q.split():
        if word[0].isupper() and len(word) > 3:
            temp = get_weather(word)
            if temp:
                context += f"\n🌤️ **OPEN-METEO** - {word}: {temp}°C\n"
                break
    
    # 7. Actualités GNews
    news = get_news_gnews(q)
    if news:
        context += "\n🌍 **GNews - ACTUALITÉS** :\n"
        for article in news[:3]:
            context += f"• {article['title']}\n"
            memory.add(article['title'], "gnews.io")
    
    return context

def get_ia_response(question):
    # Récupérer toutes les sources
    sources_context = get_all_sources(question)
    
    # Recherche en mémoire
    memory_results = memory.search(question, 2)
    memory_context = ""
    if memory_results:
        memory_context = "\n📚 **MÉMOIRE (connaissances antérieures)** :\n"
        for score, doc in memory_results:
            memory_context += f"• {doc['content'][:200]}... (source: {doc['source']})\n"
    
    if not GROQ_API_KEY:
        return sources_context or "KENNYSON OURAGAN prêt. Ajoute ta clé Groq."
    
    full_prompt = f"""
SOURCES COLLECTÉES :
{sources_context}

{memory_context}

QUESTION : {question}

RÉPONDS en utilisant UNIQUEMENT ces sources. Cite TOUJOURS tes sources.
"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1200
    }
    
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=45)
        if r.status_code == 200:
            rep = r.json()['choices'][0]['message']['content']
            return f"{sources_context}\n---\n{rep}" if sources_context else rep
        return sources_context or "Erreur technique. Veuillez réessayer."
    except:
        return sources_context or "KENNYSON OURAGAN prêt. Reformulez votre question."

# ==================================================
# ROUTES API
# ==================================================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    reponse = get_ia_response(question)
    return jsonify({"reponse": reponse})

@app.route('/api/sources')
def list_sources():
    """Affiche les sources disponibles"""
    return jsonify({
        "wikipedia": "API Wikipedia - résumés d'articles",
        "rss_feeds": RSS_FEEDS,
        "reddit": "API Reddit - discussions",
        "worldbank": "API Banque mondiale - PIB, inflation",
        "gnews": "API GNews - actualités",
        "coingecko": "API CoinGecko - cryptomonnaies",
        "openmeteo": "API Open-Meteo - météo"
    })

# ==================================================
# FRONTEND
# ==================================================
HTML = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON OURAGAN · IA Multi-Sources</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto; background: #343541; color: #ececec; height: 100vh; display: flex; flex-direction: column; }
        .header { background: #202123; padding: 16px 20px; border-bottom: 1px solid #4a4b5a; text-align: center; }
        .logo { font-size: 28px; font-weight: bold; background: linear-gradient(135deg, #e94560, #ff5a7c); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .sub { font-size: 11px; color: #8e8ea0; margin-top: 4px; }
        .sources-bar { background: #2a2b32; padding: 8px 20px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; border-bottom: 1px solid #4a4b5a; font-size: 10px; }
        .source-badge { color: #10a37f; }
        .chat-container { flex: 1; overflow-y: auto; padding: 20px; max-width: 900px; margin: 0 auto; width: 100%; }
        .message { display: flex; gap: 16px; margin-bottom: 24px; }
        .avatar { width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .avatar.user { background: #10a37f; }
        .avatar.bot { background: #e94560; }
        .content { flex: 1; line-height: 1.6; white-space: pre-wrap; font-size: 14px; }
        .content strong { color: #e94560; }
        .input-area { background: #202123; padding: 16px; border-top: 1px solid #4a4b5a; }
        .input-wrapper { max-width: 800px; margin: 0 auto; display: flex; gap: 12px; }
        textarea { flex: 1; background: #40414f; border: none; border-radius: 12px; padding: 12px 16px; color: white; font-family: inherit; resize: none; font-size: 14px; }
        button { background: #e94560; border: none; border-radius: 12px; padding: 12px 24px; color: white; cursor: pointer; font-weight: 500; }
        .suggestions { max-width: 800px; margin: 12px auto 0; display: flex; gap: 8px; flex-wrap: wrap; }
        .suggestion { background: #2a2b32; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; }
        .suggestion:hover { background: #e94560; }
        .footer { text-align: center; padding: 8px; font-size: 10px; color: #565869; }
        .typing span { display: inline-block; width: 8px; height: 8px; background: #8e8ea0; border-radius: 50%; animation: pulse 1.4s infinite; margin: 0 2px; }
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
        @media (max-width: 768px) { .suggestions { justify-content: center; } .content { font-size: 13px; } }
    </style>
</head>
<body>
<div class="header">
    <div class="logo">🔥 KENNYSON OURAGAN</div>
    <div class="sub">IA Multi-Sources · Wikipedia · Médias · Reddit · Banque mondiale · Actualités</div>
</div>
<div class="sources-bar">
    <span>📖 Wikipedia</span> <span class="source-badge">✓</span>
    <span>📰 Le Monde/Figaro/NYT/BBC</span> <span class="source-badge">✓</span>
    <span>💬 Reddit</span> <span class="source-badge">✓</span>
    <span>📊 Banque mondiale</span> <span class="source-badge">✓</span>
    <span>🌍 GNews</span> <span class="source-badge">✓</span>
    <span>💰 CoinGecko</span> <span class="source-badge">✓</span>
    <span>🌤️ Open-Meteo</span> <span class="source-badge">✓</span>
</div>
<div class="chat-container" id="chat"></div>
<div class="input-area">
    <div class="input-wrapper">
        <textarea id="input" rows="1" placeholder="Posez votre question..."></textarea>
        <button id="send">Envoyer</button>
    </div>
    <div class="suggestions">
        <div class="suggestion" data-q="Qui est Elon Musk ?">📖 Biographie Elon Musk</div>
        <div class="suggestion" data-q="PIB des États-Unis">📊 PIB USA</div>
        <div class="suggestion" data-q="Prix du Bitcoin">💰 Bitcoin</div>
        <div class="suggestion" data-q="Actualités économiques">🌍 Actualités</div>
        <div class="suggestion" data-q="Météo à Paris">🌤️ Météo Paris</div>
        <div class="suggestion" data-q="Reddit intelligence artificielle">💬 Reddit IA</div>
    </div>
    <div class="footer">Sources: Wikipedia · RSS Médias · Reddit · Banque mondiale · GNews · CoinGecko · Open-Meteo</div>
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
        addMessage("❌ Erreur technique. Veuillez réessayer.", 'bot');
    }
}

document.getElementById('send').onclick = send;
input.onkeypress = (e) => { if(e.key === 'Enter') { e.preventDefault(); send(); } };
document.querySelectorAll('.suggestion').forEach(s => { s.onclick = () => { input.value = s.dataset.q; send(); }; });

addMessage('🌍 **KENNYSON OURAGAN - IA Multi-Sources**\n\nBonjour ! Je suis votre assistant avec accès aux MÊMES SOURCES que ChatGPT.\n\n**📚 Mes sources d\'information :**\n• 📖 Wikipedia (savoir général)\n• 📰 RSS des grands médias (Le Monde, Figaro, NYT, BBC)\n• 💬 Reddit (discussions et opinions)\n• 📊 Banque mondiale (PIB, inflation)\n• 🌍 GNews (actualités temps réel)\n• 💰 CoinGecko (cryptomonnaies)\n• 🌤️ Open-Meteo (météo mondiale)\n\n**Exemples de questions :**\n• "Qui est Albert Einstein ?" (Wikipedia)\n• "PIB de la France" (Banque mondiale)\n• "Dernières actualités économiques" (GNews)\n• "Reddit intelligence artificielle" (Reddit)\n• "Météo à Londres" (Open-Meteo)\n\n**Chaque réponse CITERA SES SOURCES.**\n\nPosez votre question ! 🔥', 'bot');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
