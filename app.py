from flask import Flask, jsonify, request
import requests
import os
import json
import hashlib
import numpy as np
import faiss
from datetime import datetime

app = Flask(__name__)

# ==================================================
# CONFIGURATION
# ==================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==================================================
# REFLEXION AGENT - MÉMOIRE PERSISTANTE (Shinn et al. 2023)
# ==================================================

class ReflexionMemory:
    """
    Mémoire épisodique pour l'agent Reflexion
    Stocke les feedbacks d'erreur pour ne plus les répéter
    """
    
    def __init__(self, filepath='reflexion_memory.json'):
        self.filepath = filepath
        self.episodic_memory = []      # Succès/échecs passés
        self.reflection_memory = []    # Conseils textuels générés
        self.load()
    
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    self.episodic_memory = data.get('episodic_memory', [])
                    self.reflection_memory = data.get('reflection_memory', [])
            except:
                pass
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump({
                'episodic_memory': self.episodic_memory[-100:],
                'reflection_memory': self.reflection_memory[-50:]
            }, f)
    
    def add_episode(self, task, action, outcome, success, feedback=""):
        """Ajoute un épisode à la mémoire"""
        self.episodic_memory.append({
            'task': task,
            'action': action,
            'outcome': outcome[:500] if outcome else "",
            'success': success,
            'feedback': feedback,
            'timestamp': datetime.now().isoformat()
        })
        if not success and feedback:
            self.add_reflection(feedback)
        self.save()
    
    def add_reflection(self, advice):
        """Ajoute un conseil réflexif"""
        # Éviter les doublons
        if advice not in [r['advice'] for r in self.reflection_memory]:
            self.reflection_memory.append({
                'advice': advice,
                'timestamp': datetime.now().isoformat()
            })
        self.save()
    
    def get_reflections(self, task, limit=3):
        """Récupère les réflexions pertinentes pour la tâche"""
        task_words = set(task.lower().split())
        scored = []
        
        for ref in self.reflection_memory:
            ref_words = set(ref['advice'].lower().split())
            score = len(task_words & ref_words) / max(len(task_words), 1)
            scored.append((score, ref))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [r['advice'] for score, r in scored[:limit] if score > 0.1]
    
    def get_similar_episodes(self, task, limit=3):
        """Récupère des épisodes similaires"""
        task_words = set(task.lower().split())
        scored = []
        
        for ep in self.episodic_memory:
            ep_words = set(ep['task'].lower().split())
            score = len(task_words & ep_words) / max(len(task_words), 1)
            scored.append((score, ep))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[:limit]

# ==================================================
# FAISS VECTOR MEMORY (pour recherche de similarité)
# ==================================================
class FAISSMemory:
    def __init__(self, dimension=128):
        self.dimension = dimension
        self.index = None
        self.metadata = []
        self._init_index()
    
    def _init_index(self):
        # Index IVF pour bonne précision/vitesse
        quantizer = faiss.IndexFlatL2(self.dimension)
        nlist = 50
        self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_L2)
        self.is_trained = False
    
    def _simple_embed(self, text):
        """Embedding simple pour démo"""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vector = []
        for i in range(self.dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            vector.append((byte_val / 255.0) * 2 - 1)
        return np.array(vector, dtype=np.float32)
    
    def train(self, vectors):
        if not self.is_trained and len(vectors) > 0:
            self.index.train(vectors)
            self.is_trained = True
    
    def add(self, text):
        vector = self._simple_embed(text)
        if not self.is_trained:
            self.train(np.array([vector]))
        self.index.add(np.array([vector]))
        self.metadata.append({
            'id': len(self.metadata),
            'text': text[:500],
            'timestamp': datetime.now().isoformat()
        })
        return len(self.metadata) - 1
    
    def search(self, query, k=3, nprobe=10):
        if self.index.ntotal == 0:
            return []
        self.index.nprobe = nprobe
        query_vec = self._simple_embed(query)
        distances, indices = self.index.search(np.array([query_vec]), min(k, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.metadata):
                results.append({
                    'score': float(1.0 / (1.0 + distances[0][i])),
                    'text': self.metadata[idx]['text']
                })
        return results
    
    def stats(self):
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'is_trained': self.is_trained
        }

# ==================================================
# REFLEXION AGENT COMPLET
# ==================================================
class ReflexionAgent:
    """
    Agent Reflexion avec mémoire épisodique et réflexions persistantes
    Basé sur l'article "Reflexion: Language Agents with Verbal Reinforcement Learning" (Shinn et al. 2023)
    """
    
    def __init__(self):
        self.memory = ReflexionMemory()      # Mémoire épisodique
        self.vector_memory = FAISSMemory()   # FAISS pour similarité
        self.max_iterations = 3
        self.current_trajectory = []
    
    def reflect_on_failure(self, task, action, error, iteration):
        """
        Phase de réflexion - génère un feedback textuel à partir de l'erreur
        C'est le cœur de l'agent Reflexion
        """
        if not GROQ_API_KEY:
            return f"Erreur: {error[:200]}"
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        reflexion_prompt = f"""
Tu es un agent réflexif. Tu as échoué à la tâche suivante.

TÂCHE: {task}
ACTION ENTREPRISE: {action}
ERREUR RENCONTRÉE: {error}
ITÉRATION: {iteration}

Génère un CONSEIL TEXTUEL (1-2 phrases) pour ne pas reproduire cette erreur.
Le conseil doit être concret et actionnable.
Exemple: "Pour les questions de PIB, toujours appeler l'API World Bank avec le code pays en majuscules."
"""
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": reflexion_prompt}],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                advice = r.json()['choices'][0]['message']['content']
                self.memory.add_reflection(advice)
                return advice
        except:
            pass
        
        return f"À retenir: {error[:100]}"
    
    def get_reflexion_context(self, task):
        """Récupère les réflexions pertinentes de la mémoire"""
        reflections = self.memory.get_reflections(task, 3)
        if not reflections:
            return ""
        
        context = "📚 **RÉFLEXIONS PASSÉES (Mémoire épisodique)** :\n\n"
        for i, ref in enumerate(reflections, 1):
            context += f"{i}. ⚠️ {ref}\n\n"
        return context
    
    def get_similar_experiences(self, task):
        """Récupère des expériences similaires via FAISS"""
        similar = self.vector_memory.search(task, k=2)
        if not similar:
            return ""
        
        context = "🔄 **EXPÉRIENCES SIMILAIRES** :\n\n"
        for i, sim in enumerate(similar, 1):
            context += f"{i}. {sim['text'][:200]}... (similarité: {sim['score']:.2f})\n\n"
        return context
    
    def execute_with_reflexion(self, task, execute_func, max_attempts=3):
        """
        Exécute une tâche avec boucle de réflexion
        """
        self.current_trajectory = []
        
        for attempt in range(max_attempts):
            # Récupérer les réflexions passées
            reflexion_context = self.get_reflexion_context(task)
            similar_context = self.get_similar_experiences(task)
            
            # Exécuter avec contexte
            result, success, error = execute_func(task, reflexion_context, similar_context, attempt)
            
            # Sauvegarder la trajectoire
            self.current_trajectory.append({
                'attempt': attempt + 1,
                'result': result[:500] if result else "",
                'success': success,
                'error': error
            })
            
            if success:
                # Sauvegarder le succès dans la mémoire
                self.memory.add_episode(task, str(self.current_trajectory[-1]), result, True)
                # Sauvegarder dans FAISS pour recherche future
                self.vector_memory.add(f"Tâche: {task}\nRésultat: {result[:300]}")
                return result, success, self.current_trajectory
            
            else:
                # Phase de réflexion sur l'échec
                advice = self.reflect_on_failure(task, str(self.current_trajectory[-1]), error, attempt)
                self.memory.add_episode(task, str(self.current_trajectory[-1]), error, False, advice)
        
        return f"Échec après {max_attempts} tentatives.", False, self.current_trajectory

# ==================================================
# TOOLS POUR L'AGENT
# ==================================================
class AgentTools:
    
    @staticmethod
    def get_worldbank_gdp(country_code="CD", country_name="RDC"):
        try:
            url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/NY.GDP.MKTP.CD?format=json"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 1 and data[1] and data[1][0].get('value'):
                    return f"{country_name} - PIB: {int(float(data[1][0]['value'])):,} USD"
        except:
            pass
        return None
    
    @staticmethod
    def get_crypto():
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=8)
            if r.status_code == 200:
                return f"💰 Bitcoin: ${r.json()['bitcoin']['usd']:,.2f} USD"
        except:
            pass
        return None
    
    @staticmethod
    def get_weather(city="Kinshasa"):
        try:
            geo = requests.get(f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1",
                              headers={'User-Agent': 'REFLEXION-AGENT/1.0'}, timeout=8)
            if geo.status_code == 200 and geo.json():
                lat = geo.json()[0]['lat']
                lon = geo.json()[0]['lon']
                r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=8)
                if r.status_code == 200:
                    return f"🌤️ {city}: {r.json()['current_weather']['temperature']}°C"
        except:
            pass
        return None

# ==================================================
# FONCTION D'EXÉCUTION AVEC RÉFLEXION
# ==================================================
def execute_task(task, reflexion_context, similar_context, attempt):
    """Fonction exécutée par l'agent Reflexion"""
    q = task.lower()
    external_data = ""
    tools = AgentTools()
    
    # Appels API
    if "pib" in q or "économie" in q:
        ext = tools.get_worldbank_gdp("CD", "RDC")
        if ext: external_data += ext + "\n\n"
    elif "bitcoin" in q:
        ext = tools.get_crypto()
        if ext: external_data += ext + "\n\n"
    elif "météo" in q:
        city = "Kinshasa"
        for word in q.split():
            if word[0].isupper() and len(word) > 3:
                city = word
                break
        ext = tools.get_weather(city)
        if ext: external_data += ext + "\n\n"
    
    if not GROQ_API_KEY:
        return external_data or "Ajoute ta clé Groq", bool(external_data), "Pas de clé API" if not external_data else ""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    full_prompt = f"""
{reflexion_context}
{similar_context}

DONNÉES EXTERNES:
{external_data}

TÂCHE: {task}

RÉPONDS de manière structurée et précise.
"""
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.7,
        "max_tokens": 600
    }
    
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            rep = r.json()['choices'][0]['message']['content']
            return rep, True, ""
        return f"Erreur API: {r.status_code}", False, f"HTTP {r.status_code}"
    except Exception as e:
        return f"Erreur: {str(e)}", False, str(e)

# ==================================================
# ROUTES API
# ==================================================
agent = ReflexionAgent()

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    
    # Exécuter avec boucle de réflexion
    response, success, trajectory = agent.execute_with_reflexion(question, execute_task, max_attempts=3)
    
    return jsonify({
        "reponse": response,
        "success": success,
        "attempts": len(trajectory),
        "trajectory": trajectory
    })

@app.route('/api/memory/reflections', methods=['GET'])
def get_reflections():
    return jsonify(agent.memory.reflection_memory)

@app.route('/api/memory/episodes', methods=['GET'])
def get_episodes():
    return jsonify(agent.memory.episodic_memory[-20:])

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'reflections': len(agent.memory.reflection_memory),
        'episodes': len(agent.memory.episodic_memory),
        'vectors': agent.vector_memory.stats()
    })

# ==================================================
# HTML INTERFACE
# ==================================================
HTML = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KENNYSON · Reflexion Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto; background: #343541; color: #ececec; height: 100vh; display: flex; flex-direction: column; }
        .header { background: #202123; padding: 16px 20px; border-bottom: 1px solid #4a4b5a; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; background: linear-gradient(135deg, #e94560, #ff5a7c); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .badge { background: #e94560; border-radius: 20px; padding: 2px 12px; font-size: 10px; margin-left: 8px; }
        .sub { font-size: 11px; color: #8e8ea0; margin-top: 4px; }
        .stats-bar { background: #2a2b32; padding: 6px 16px; font-size: 11px; display: flex; justify-content: space-between; border-bottom: 1px solid #4a4b5a; }
        .main { display: flex; flex: 1; overflow: hidden; }
        .chat-container { flex: 2; overflow-y: auto; padding: 20px; }
        .trajectory-panel { flex: 1; background: #202123; border-left: 1px solid #4a4b5a; overflow-y: auto; padding: 16px; font-family: monospace; font-size: 11px; }
        .trajectory-title { color: #e94560; margin-bottom: 12px; font-size: 12px; font-weight: bold; }
        .trajectory-log { color: #8e8ea0; line-height: 1.5; }
        .message { display: flex; gap: 16px; margin-bottom: 24px; }
        .avatar { width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .avatar.user { background: #10a37f; }
        .avatar.bot { background: #e94560; }
        .content { flex: 1; line-height: 1.6; white-space: pre-wrap; font-size: 14px; }
        .content strong { color: #e94560; }
        .attempt-badge { background: #e94560; border-radius: 4px; padding: 2px 6px; font-size: 9px; margin-left: 8px; }
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
    </style>
</head>
<body>
<div class="header">
    <div class="logo">🔥 KENNYSON OURAGAN <span class="badge">REFLEXION AGENT</span></div>
    <div class="sub">Mémoire épisodique · Apprentissage par essai-erreur · Reflexion (Shinn et al. 2023)</div>
</div>
<div class="stats-bar" id="statsBar">Chargement...</div>
<div class="main">
    <div class="chat-container" id="chat"></div>
    <div class="trajectory-panel">
        <div class="trajectory-title">🧠 TRAJECTOIRE DE RÉFLEXION</div>
        <div class="trajectory-log" id="trajectoryLog">En attente d'une question...</div>
    </div>
</div>
<div class="input-area">
    <div class="input-wrapper">
        <textarea id="input" rows="1" placeholder="Posez votre question..."></textarea>
        <button id="send">Envoyer</button>
    </div>
    <div class="suggestions">
        <div class="suggestion" data-q="PIB de la RDC">📊 PIB RDC</div>
        <div class="suggestion" data-q="Prix du Bitcoin">💰 Bitcoin</div>
        <div class="suggestion" data-q="Météo à Kinshasa">🌤️ Météo</div>
    </div>
    <div class="footer">🧠 Reflexion Agent · Boucle réflexive · Jusqu'à 3 tentatives · Mémoire persistante</div>
</div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const trajectoryLog = document.getElementById('trajectoryLog');

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('statsBar').innerHTML = `📊 Réflexions: ${stats.reflections} | Épisodes: ${stats.episodes} | Vecteurs FAISS: ${stats.vectors.total_vectors}`;
    } catch(e) {}
}

function updateTrajectory(trajectory) {
    if (!trajectory || trajectory.length === 0) {
        trajectoryLog.innerHTML = 'En attente d\'une question...';
        return;
    }
    let html = '';
    trajectory.forEach(t => {
        const status = t.success ? '✅ SUCCÈS' : '❌ ÉCHEC';
        html += `<div style="margin-bottom: 12px; border-left: 2px solid ${t.success ? '#10a37f' : '#e94560'}; padding-left: 8px;">`;
        html += `<strong>Tentative ${t.attempt}</strong> <span style="color: ${t.success ? '#10a37f' : '#e94560'}">${status}</span><br>`;
        if (t.error) html += `<span style="color: #e94560; font-size: 10px;">Erreur: ${t.error.substring(0, 100)}...</span><br>`;
        html += `</div>`;
    });
    trajectoryLog.innerHTML = html;
}

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
    updateTrajectory([]);
    addMessage('<div class="typing"><span>●</span><span>●</span><span>●</span></div>', 'bot');
    
    try {
        const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) });
        const data = await res.json();
        chat.lastChild.remove();
        addMessage(data.reponse, 'bot');
        updateTrajectory(data.trajectory);
        loadStats();
    } catch(e) {
        chat.lastChild.remove();
        addMessage("❌ Erreur technique. Veuillez réessayer.", 'bot');
    }
}

document.getElementById('send').onclick = send;
input.onkeypress = (e) => { if(e.key === 'Enter') { e.preventDefault(); send(); } };
document.querySelectorAll('.suggestion').forEach(s => { s.onclick = () => { input.value = s.dataset.q; send(); }; });

addMessage('🧠 **KENNYSON OURAGAN - REFLEXION AGENT**\n\nJe suis un agent **Reflexion** (Shinn et al. 2023) avec mémoire épisodique.\n\n**Ce que je fais :**\n\n**1. ACTEUR (Actor)** : J\'exécute la tâche\n**2. ÉVALUATEUR (Evaluator)** : Je vérifie si j\'ai réussi\n**3. RÉFLECTEUR (Reflector)** : En cas d\'échec, j\'analyse et génère un conseil\n**4. MÉMOIRE** : Je garde les conseils pour ne plus refaire les mêmes erreurs\n\n**Nouveautés :**\n• 🔄 Boucle réflexive (jusqu\'à 3 tentatives)\n• 📚 Mémoire épisodique persistante\n• 🧠 Apprentissage par essai-erreur\n• 🎯 Amélioration continue\n\n**Exemples :**\n• "PIB de la RDC"\n• "Prix du Bitcoin"\n• "Météo à Kinshasa"\n\nPosez votre question ! 🔥', 'bot');
loadStats();
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
