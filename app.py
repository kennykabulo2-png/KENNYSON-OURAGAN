from flask import Flask, jsonify, request, session, redirect, url_for
from functools import wraps
import json
import logging
import hashlib
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'oyebi_secret_key_2026'

# ==================== LOGS ET GESTION DES ERREURS ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.before_request
def log_request_info():
    logger.info(f"{datetime.now()} - {request.method} {request.path}")

@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404 - Page non trouvée</h1><p>La page que vous cherchez n'existe pas.</p><a href='/'>Retour à l'accueil</a>", 404

@app.errorhandler(500)
def internal_error(e):
    return "<h1>500 - Erreur interne</h1><p>Une erreur s'est produite. Veuillez réessayer plus tard.</p><a href='/'>Retour à l'accueil</a>", 500

# ==================== AUTHENTIFICATION ====================
users = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if email in users:
        return jsonify({"error": "Email déjà utilisé"}), 400
    
    users[email] = {
        "name": name,
        "password": hash_password(password),
        "email": email,
        "created_at": datetime.now().isoformat()
    }
    return jsonify({"message": "Compte créé avec succès !"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = users.get(email)
    if not user or user['password'] != hash_password(password):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    
    token = secrets.token_hex(32)
    session['user'] = email
    return jsonify({"token": token, "user": {"name": user['name'], "email": user['email']}}), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"message": "Déconnecté"}), 200

@app.route('/api/me')
def me():
    email = session.get('user')
    if not email:
        return jsonify({"error": "Non authentifié"}), 401
    user = users.get(email)
    return jsonify({"name": user['name'], "email": user['email']}), 200

# ==================== DONNEES ====================
AGENTS = [
    {"id": "AG-001", "nom": "KABULO Kenny", "grade": "Directeur", "salaire": 3000000},
    {"id": "AG-002", "nom": "MBEMBA Jeanne", "grade": "Chef Bureau", "salaire": 2100000},
    {"id": "AG-003", "nom": "TSHIBANDA Paul", "grade": "Agent", "salaire": 1300000},
]

SOCIETES = [
    {"nom": "Minière du Congo", "secteur": "Mines", "impot_du": 13500, "impot_paye": 3200, "statut": "Alerte"},
    {"nom": "Telecom Congo", "secteur": "Telco", "impot_du": 8400, "impot_paye": 7600, "statut": "Conforme"},
    {"nom": "BTP Congo", "secteur": "BTP", "impot_du": 3600, "impot_paye": 3100, "statut": "Modéré"},
    {"nom": "Commerce Intl", "secteur": "Commerce", "impot_du": 2400, "impot_paye": 500, "statut": "Alerte"},
]

LIVRES = [
    {
        "titre": "Le prix de la corruption",
        "auteur": "M. Nkolo",
        "categorie": "Anti-corruption",
        "resume": "Une analyse approfondie des mécanismes de la corruption en Afrique centrale, avec des études de cas en RDC.",
        "contenu": "La corruption est un fléau qui touche tous les secteurs de la société congolaise."
    },
    {
        "titre": "Gestion des finances publiques",
        "auteur": "J. Tshibangu",
        "categorie": "Finances",
        "resume": "Guide pratique pour comprendre et maîtriser les rouages des finances publiques en RDC.",
        "contenu": "Ce guide s'adresse aux agents publics et aux citoyens."
    },
    {
        "titre": "Manuel du citoyen congolais",
        "auteur": "Société civile",
        "categorie": "Droits citoyens",
        "resume": "Un guide complet des droits et devoirs des citoyens congolais.",
        "contenu": "Ce manuel est un outil pédagogique."
    }
]

# ==================== TEMPLATE BASE CORRIGE ====================
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OYEBI · {title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0A0F1E; color: #F1F5F9; overflow-x: hidden; }
        #particles-js { position: fixed; width: 100%; height: 100%; top: 0; left: 0; z-index: 0; }
        .navbar { position: fixed; top: 0; width: 100%; background: rgba(10,15,30,0.9); backdrop-filter: blur(15px); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; z-index: 100; border-bottom: 1px solid rgba(255,255,255,0.1); flex-wrap: wrap; gap: 1rem; }
        .logo { font-size: 1.5rem; font-weight: 800; background: linear-gradient(135deg, #FFFFFF, #0085CA, #FACC15); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .nav-links { display: flex; gap: 1.5rem; flex-wrap: wrap; }
        .nav-links a { color: #F1F5F9; text-decoration: none; font-weight: 500; font-size: 0.9rem; transition: 0.3s; position: relative; }
        .nav-links a::after { content: ''; position: absolute; bottom: -5px; left: 0; width: 0; height: 2px; background: #FACC15; transition: width 0.3s ease; }
        .nav-links a:hover::after { width: 100%; }
        .nav-links a:hover { color: #FACC15; }
        .container { position: relative; z-index: 2; max-width: 1280px; margin: 0 auto; padding: 6rem 1.5rem 2rem; }
        .hero { background: rgba(255,255,255,0.03); backdrop-filter: blur(10px); border-radius: 2rem; padding: 3rem 2rem; text-align: center; margin-bottom: 2rem; border: 1px solid rgba(255,255,255,0.1); }
        .hero h1 { font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #FFFFFF, #0085CA, #FACC15); -webkit-background-clip: text; background-clip: text; color: transparent; margin-bottom: 1rem; }
        .typed-text { font-size: 1.2rem; color: #FACC15; margin-bottom: 1rem; min-height: 4rem; }
        .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card-glass { background: rgba(255,255,255,0.03); backdrop-filter: blur(10px); border-radius: 1rem; padding: 1.5rem; border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s ease; height: 100%; }
        .card-glass:hover { transform: translateY(-5px); border-color: #FACC15; background: rgba(255,255,255,0.07); }
        .card-glass i { font-size: 2rem; color: #FACC15; margin-bottom: 1rem; display: inline-block; }
        .kpi-value { font-size: 2rem; font-weight: 700; color: #FACC15; }
        .agents-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        .agents-table th, .agents-table td { padding: 0.75rem 0.5rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .agents-table th { color: #FACC15; }
        .grade-badge { background: rgba(0,133,202,0.2); color: #0085CA; padding: 0.2rem 0.6rem; border-radius: 2rem; font-size: 0.7rem; display: inline-block; }
        .badge-alert { background: rgba(239,68,68,0.2); color: #F87171; padding: 0.2rem 0.6rem; border-radius: 2rem; font-size: 0.7rem; }
        .badge-conforme { background: rgba(34,197,94,0.2); color: #4ADE80; }
        .badge-modere { background: rgba(250,204,21,0.2); color: #FACC15; }
        .progress-bar { background: rgba(255,255,255,0.1); border-radius: 1rem; height: 8px; margin: 0.5rem 0; overflow: hidden; }
        .progress-fill { background: #FACC15; width: 0%; height: 8px; border-radius: 1rem; }
        .toast-notification { position: fixed; bottom: 20px; right: 20px; background: #FACC15; color: #0A0F1E; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.2); animation: fadeInOut 3s ease forwards; }
        @keyframes fadeInOut { 0% { opacity: 0; transform: translateY(20px); } 15% { opacity: 1; transform: translateY(0); } 85% { opacity: 1; transform: translateY(0); } 100% { opacity: 0; transform: translateY(20px); } }
        .last-update { font-size: 0.7rem; color: #94A3B8; text-align: right; margin-bottom: 1rem; }
        .footer { text-align: center; padding: 2rem; border-top: 1px solid rgba(255,255,255,0.1); font-size: 0.8rem; color: #64748B; }
        canvas { max-width: 100%; height: auto; }
        @media (max-width: 768px) { .navbar { flex-direction: column; text-align: center; padding: 1rem; } .nav-links { justify-content: center; gap: 1rem; } .container { padding: 6rem 1rem 2rem; } .hero { padding: 2rem 1rem; } .hero h1 { font-size: 1.8rem; } }
        @media (max-width: 480px) { .grid-4, .grid-3 { grid-template-columns: 1fr; } .nav-links { flex-direction: column; gap: 0.5rem; } }
    </style>
</head>
<body>
<div id="particles-js"></div>
<nav class="navbar">
    <div class="logo">OYEBI</div>
    <div class="nav-links">
        <a href="/">Accueil</a>
        <a href="/dashboard">Dashboard</a>
        <a href="/insights">Insights</a>
        <a href="/objectifs">Objectifs</a>
        <a href="/bibliotheque">Bibliothèque</a>
        <a href="/apropos">À propos</a>
        <a href="/login" id="authLink">Connexion</a>
    </div>
</nav>
<div class="container">{content}</div>
<footer class="footer">OYEBI · Gouvernance transparente · Kinshasa, RDC</footer>
<script>
    particlesJS("particles-js", { particles: { number: { value: 80, density: { enable: true, value_area: 800 } }, color: { value: "#0085CA" }, shape: { type: "circle" }, opacity: { value: 0.5, random: true }, size: { value: 3, random: true }, line_linked: { enable: true, distance: 150, color: "#0085CA", opacity: 0.2, width: 1 }, move: { enable: true, speed: 2, direction: "none", random: true, straight: false, out_mode: "out" } }, interactivity: { detect_on: "canvas", events: { onhover: { enable: true, mode: "repulse" }, onclick: { enable: true, mode: "push" } } }, retina_detect: true });
    const phrases = {phrases};
    let i = 0, j = 0, isDeleting = false;
    function type() {
        const current = phrases[i];
        const typed = document.getElementById("typed");
        if (typed) {
            if (isDeleting) typed.innerText = current.substring(0, j--);
            else typed.innerText = current.substring(0, j++);
            if (!isDeleting && j === current.length) isDeleting = true;
            if (isDeleting && j === 0) { isDeleting = false; i = (i + 1) % phrases.length; }
        }
        setTimeout(type, 100);
    }
    type();
    const token = localStorage.getItem('token');
    const authLink = document.getElementById('authLink');
    if (token && authLink) {
        fetch('/api/me', { headers: { 'Authorization': 'Bearer ' + token } }).then(res => {
            if (res.ok) {
                authLink.innerHTML = '<i class="fas fa-user-circle"></i> Mon compte';
                authLink.href = '/mon-compte';
            } else {
                localStorage.removeItem('token');
                authLink.innerHTML = 'Connexion';
                authLink.href = '/login';
            }
        }).catch(() => {
            authLink.innerHTML = 'Connexion';
            authLink.href = '/login';
        });
    } else if (authLink) {
        authLink.innerHTML = 'Connexion';
        authLink.href = '/login';
    }
</script>
</body>
</html>
'''

def render_page(title, content, phrases):
    return BASE_TEMPLATE.format(title=title, content=content, phrases=phrases)

# ==================== PAGE ACCUEIL ====================
ACCUEIL = '''
<div class="hero"><h1>OYEBI</h1><div class="typed-text" id="typed"></div></div>
<div class="grid-3">
    <div class="card-glass"><i class="fas fa-chart-line"></i><h3>Données fiables</h3><p>Issues des bases officielles</p></div>
    <div class="card-glass"><i class="fas fa-eye"></i><h3>Transparence totale</h3><p>Visualisez les fonds publics</p></div>
    <div class="card-glass"><i class="fas fa-shield-alt"></i><h3>Sécurité avancée</h3><p>Accès agent certifié</p></div>
</div>
'''

@app.route('/')
def index():
    return render_page("Accueil", ACCUEIL, '["La transparence au service de la nation.", "Données publiques pour un Congo qui avance.", "Ensemble, bâtissons une administration exemplaire."]')

# ==================== DASHBOARD ====================
DASHBOARD = '''
<div class="hero"><h1>Tableau de bord stratégique</h1><p>Indicateurs clés de la gouvernance</p></div>
<div class="last-update"><i class="fas fa-sync-alt"></i> Dernière mise à jour : <span id="lastUpdate"></span><button id="refreshBtn" style="background:none; border:none; color:#FACC15; cursor:pointer; margin-left:10px;"><i class="fas fa-arrow-rotate-right"></i> Rafraîchir</button></div>
<div class="grid-4" id="kpis"></div>
<div class="card-glass"><h3><i class="fas fa-chart-line"></i> Comparaison impôts (M$)</h3><canvas id="chart"></canvas></div>
<div class="card-glass"><h3><i class="fas fa-users"></i> Agents de l'État</h3><div style="overflow-x:auto;"><table class="agents-table"><thead><tr><th>Matricule</th><th>Nom complet</th><th>Grade</th><th>Salaire mensuel</th></tr></thead><tbody id="agentsTable"></tbody></table></div></div>
<div class="card-glass"><h3><i class="fas fa-building"></i> Sociétés</h3><div id="societesTable"></div></div>
<script>
    function showToast(message) { var toast = document.createElement('div'); toast.className = 'toast-notification'; toast.innerHTML = '<i class="fas fa-check-circle"></i> ' + message; document.body.appendChild(toast); setTimeout(function() { toast.remove(); }, 3000); }
    function exportToCSV(data, filename) { var headers = Object.keys(data[0]); var csvRows = [headers.join(',')]; for (var i = 0; i < data.length; i++) { var values = headers.map(function(header) { return '"' + data[i][header] + '"'; }); csvRows.push(values.join(',')); } var blob = new Blob([csvRows.join('\\n')], { type: 'text/csv' }); var url = URL.createObjectURL(blob); var a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url); showToast('Export CSV réussi !'); }
    function updateLastUpdate() { var span = document.getElementById('lastUpdate'); if (span) span.innerText = new Date().toLocaleString(); }
    async function fetchData(url) { var r = await fetch(url); return r.json(); }
    async function load() {
        var agents = await fetchData('/api/agents');
        var societes = await fetchData('/api/societes');
        var stats = await fetchData('/api/stats');
        document.getElementById('kpis').innerHTML = '<div class="card-glass"><div class="kpi-value">' + stats.nb_agents + '</div><div>Agents</div></div><div class="card-glass"><div class="kpi-value">' + stats.nb_societes + '</div><div>Sociétés</div></div><div class="card-glass"><div class="kpi-value">' + (stats.masse_salariale/1e6).toFixed(1) + 'M</div><div>Masse salariale</div></div><div class="card-glass"><div class="kpi-value">' + (stats.manque_fiscal/1e6).toFixed(0) + 'M</div><div>Manque 2025</div></div>';
        var agentsHtml = '';
        for (var i = 0; i < agents.length; i++) { agentsHtml += '<tr><td><strong>' + agents[i].id + '</strong></td><td>' + agents[i].nom + '</td><td><span class="grade-badge">' + agents[i].grade + '</span></td><td class="salaire">' + (agents[i].salaire/1e6).toFixed(2) + ' M FC</td></tr>'; }
        document.getElementById('agentsTable').innerHTML = agentsHtml;
        var societesHtml = '<thead><tr><th>Société</th><th>Impôt dû</th><th>Payé</th><th>Statut</th></tr></thead><tbody>';
        for (var i = 0; i < societes.length; i++) { var badge = societes[i].statut === 'Alerte' ? 'badge-alert' : (societes[i].statut === 'Conforme' ? 'badge-conforme' : 'badge-modere'); societesHtml += '<tr><td><strong>' + societes[i].nom + '</strong></td><td>' + societes[i].impot_du + ' M$</td><td>' + societes[i].impot_paye + ' M$</td><td><span class="' + badge + '">' + societes[i].statut + '</span></td></tr>'; }
        societesHtml += '</tbody>';
        document.getElementById('societesTable').innerHTML = societesHtml;
        if (!document.getElementById('exportAgentsBtn')) { var exportBtn = document.createElement('button'); exportBtn.id = 'exportAgentsBtn'; exportBtn.innerHTML = '<i class="fas fa-download"></i> Exporter agents (CSV)'; exportBtn.style.cssText = 'background:#0085CA; color:white; border:none; border-radius:0.5rem; padding:0.5rem 1rem; margin-top:0.5rem; cursor:pointer;'; exportBtn.onclick = function() { exportToCSV(agents, 'agents_oyebi.csv'); }; var container = document.querySelector('.card-glass h3'); if (container && container.parentNode) container.parentNode.appendChild(exportBtn); }
        var refreshBtn = document.getElementById('refreshBtn'); if (refreshBtn) { refreshBtn.onclick = function() { load(); showToast('Données actualisées'); }; }
        updateLastUpdate();
        new Chart(document.getElementById('chart'), { type: 'bar', data: { labels: societes.map(function(s) { return s.nom; }), datasets: [{ label: 'Dû', data: societes.map(function(s) { return s.impot_du; }), backgroundColor: '#0085CA' }, { label: 'Payé', data: societes.map(function(s) { return s.impot_paye; }), backgroundColor: '#FACC15' }] } });
    }
    load();
</script>
'''

@app.route('/dashboard')
def dashboard():
    return render_page("Dashboard", DASHBOARD, '["Visualisez les indicateurs clés en temps réel.", "Suivez l\'évolution des impôts et des agents.", "Prenez des décisions basées sur des données fiables."]')

# ==================== INSIGHTS ====================
INSIGHTS = '''
<div class="hero"><h1><i class="fas fa-search"></i> Insights nationaux</h1><p>Analyse des écarts fiscaux par secteur</p></div>
<div class="grid-3" id="insightsGrid"></div>
<div class="card-glass"><h3>Répartition du manque fiscal</h3><canvas id="donut"></canvas></div>
<script>
    async function loadInsights() {
        var societes = await (await fetch('/api/societes')).json();
        var total = societes.reduce(function(s,c) { return s + (c.impot_du - c.impot_paye); }, 0);
        var mines = societes.find(function(s) { return s.nom === 'Minière du Congo'; });
        var telecom = societes.find(function(s) { return s.nom === 'Telecom Congo'; });
        var btp = societes.find(function(s) { return s.nom === 'BTP Congo'; });
        var m = mines.impot_du - mines.impot_paye;
        var t = telecom.impot_du - telecom.impot_paye;
        var b = btp.impot_du - btp.impot_paye;
        document.getElementById('insightsGrid').innerHTML = '<div class="card-glass"><h3>Mines</h3><div class="kpi-value">' + m + 'M$</div><div>' + Math.round(m/total*100) + '% du total</div></div><div class="card-glass"><h3>Télécoms</h3><div class="kpi-value">' + t + 'M$</div><div>' + Math.round(t/total*100) + '%</div></div><div class="card-glass"><h3>BTP</h3><div class="kpi-value">' + b + 'M$</div><div>' + Math.round(b/total*100) + '%</div></div>';
        new Chart(document.getElementById('donut'), { type: 'doughnut', data: { labels: ['Mines','Télécoms','BTP','Commerce'], datasets: [{ data: societes.map(function(s) { return s.impot_du - s.impot_paye; }), backgroundColor: ['#0085CA','#FACC15','#EF4444','#10B981'] }] } });
    }
    loadInsights();
</script>
'''

@app.route('/insights')
def insights():
    return render_page("Insights", INSIGHTS, '["Analyse des écarts fiscaux par secteur.", "Découvrez les tendances et anomalies.", "Des données pour mieux comprendre l\'économie."]')

# ==================== OBJECTIFS ====================
OBJECTIFS = '''
<div class="hero"><h1><i class="fas fa-flag-checkered"></i> Objectifs 2025</h1><p>Suivi des cibles de l'administration</p></div>
<div class="card-glass"><h3>Impôts collectés</h3><div id="o1"></div><div class="progress-bar"><div id="b1" class="progress-fill"></div></div></div>
<div class="card-glass"><h3>Agents formés</h3><div id="o2"></div><div class="progress-bar"><div id="b2" class="progress-fill"></div></div></div>
<script>
    async function load() {
        var stats = await (await fetch('/api/stats')).json();
        var obj1 = { objectif: 15000, realise: stats.manque_fiscal/1e6 };
        var obj2 = { objectif: 500, realise: 120 };
        document.getElementById('o1').innerHTML = '<i class="fas fa-chart-simple"></i> Objectif ' + obj1.objectif + 'M$ | <i class="fas fa-check-circle"></i> Réalisé ' + obj1.realise + 'M$';
        document.getElementById('o2').innerHTML = '<i class="fas fa-chart-simple"></i> Objectif ' + obj2.objectif + ' agents | <i class="fas fa-check-circle"></i> Réalisé ' + obj2.realise + ' agents';
        document.getElementById('b1').style.width = Math.min((obj1.realise/obj1.objectif)*100,100) + '%';
        document.getElementById('b2').style.width = Math.min((obj2.realise/obj2.objectif)*100,100) + '%';
    }
    load();
</script>
'''

@app.route('/objectifs')
def objectifs():
    return render_page("Objectifs", OBJECTIFS, '["Mesurez l\'avancement des objectifs 2025.", "Suivez les cibles de l\'administration.", "Atteignons ensemble nos ambitions nationales."]')

# ==================== BIBLIOTHEQUE ====================
BIBLIOTHEQUE = '''
<div class="hero"><h1><i class="fas fa-book-open"></i> Bibliothèque citoyenne</h1><p>Lectures pour renforcer la gouvernance</p></div>
<div class="grid-3" id="booksGrid"></div>
<div id="bookModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); z-index:2000; justify-content:center; align-items:center;"><div style="background:#0A0F1E; border-radius:1rem; max-width:600px; width:90%; max-height:80vh; overflow-y:auto; padding:2rem; border:1px solid #FACC15;"><div style="text-align:right;"><button onclick="closeModal()" style="background:none; border:none; color:#FACC15; font-size:2rem; cursor:pointer;">&times;</button></div><h2 id="modalTitle" style="color:#FACC15; margin-bottom:0.5rem;"></h2><p id="modalAuthor" style="color:#94A3B8; margin-bottom:1rem;"></p><h3 style="color:#0085CA; margin-top:1rem;">Résumé</h3><p id="modalResume" style="line-height:1.6;"></p><h3 style="color:#0085CA; margin-top:1rem;">Extrait</h3><p id="modalContent" style="line-height:1.6;"></p></div></div>
<script>
    var livresData = [];
    async function loadBooks() {
        var res = await fetch('/api/livres');
        livresData = await res.json();
        var html = '';
        for (var i = 0; i < livresData.length; i++) { var l = livresData[i]; html += '<div class="card-glass" style="cursor:pointer;" onclick="openBookModal(' + i + ')"><i class="fas fa-book" style="font-size:2rem; color:#FACC15; margin-bottom:1rem;"></i><h3>' + l.titre + '</h3><p>' + l.auteur + '</p><small style="color:#94A3B8;">' + l.categorie + '</small><p style="margin-top:0.8rem; font-size:0.85rem;">' + l.resume.substring(0, 120) + '...</p><div style="margin-top:1rem;"><button style="background:#0085CA; color:white; border:none; border-radius:0.5rem; padding:0.3rem 0.8rem; cursor:pointer;">Lire l\'extrait</button></div></div>'; }
        document.getElementById('booksGrid').innerHTML = html;
    }
    function openBookModal(index) { var livre = livresData[index]; document.getElementById('modalTitle').innerText = livre.titre; document.getElementById('modalAuthor').innerHTML = '<i class="fas fa-user"></i> ' + livre.auteur + ' | <i class="fas fa-tag"></i> ' + livre.categorie; document.getElementById('modalResume').innerText = livre.resume; document.getElementById('modalContent').innerText = livre.contenu; document.getElementById('bookModal').style.display = 'flex'; }
    function closeModal() { document.getElementById('bookModal').style.display = 'none'; }
    loadBooks();
</script>
'''

@app.route('/bibliotheque')
def bibliotheque():
    return render_page("Bibliothèque", BIBLIOTHEQUE, '["Des livres pour comprendre la gouvernance.", "La connaissance au service de la transparence.", "Formez-vous pour mieux agir."]')

# ==================== À PROPOS ====================
APROPOS = '''
<div class="hero"><h1><i class="fas fa-info-circle"></i> À propos d'OYEBI</h1></div>
<div class="card-glass"><h2><i class="fas fa-bullseye"></i> Notre Vision</h2><p>OYEBI est né d'une conviction profonde : la transparence est le fondement d'une gouvernance juste et efficace.</p></div>
<div class="card-glass"><h2><i class="fas fa-flag-checkered"></i> Notre Mission</h2><p>Offrir une plateforme accessible, fiable et moderne qui centralise les données essentielles de l'administration congolaise.</p></div>
<div class="card-glass"><h2><i class="fas fa-gem"></i> Nos Valeurs</h2><div class="grid-3"><div class="card-glass"><i class="fas fa-eye"></i><h3>Transparence</h3></div><div class="card-glass"><i class="fas fa-shield-alt"></i><h3>Intégrité</h3></div><div class="card-glass"><i class="fas fa-chart-line"></i><h3>Innovation</h3></div></div></div>
<div class="card-glass"><h2><i class="fas fa-globe-africa"></i> Pourquoi OYEBI ?</h2><p>Le nom OYEBI signifie "savoir" en lingala. Un citoyen informé est un citoyen qui peut agir.</p></div>
<div class="card-glass" style="text-align:center;"><h2><i class="fas fa-laptop-code"></i> Concepteur</h2><p><strong>Kenny Kabulo Matanda</strong><br>Kinshasa, RDC</p></div>
'''

@app.route('/apropos')
def apropos():
    return render_page("À propos", APROPOS, '["Une vision pour un Congo transparent.", "La donnée au service du citoyen.", "Innovation et intégrité."]')

# ==================== PAGE CONNEXION ====================
LOGIN_PAGE = '''
<div style="max-width: 500px; margin: 0 auto;">
    <div class="card-glass">
        <h2 style="text-align:center; margin-bottom:1rem;" id="formTitle">Créer un compte</h2>
        <div id="loginForm" style="display: none;">
            <div class="input-group"><input type="email" id="loginEmail" placeholder="Email" style="width:100%; padding:0.8rem; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:0.5rem; color:white; margin-bottom:1rem;"></div>
            <div class="input-group"><input type="password" id="loginPassword" placeholder="Mot de passe" style="width:100%; padding:0.8rem; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:0.5rem; color:white; margin-bottom:1rem;"></div>
            <div style="display:flex; align-items:center; gap:0.5rem; margin:0.5rem 0 1rem 0;"><input type="checkbox" id="showLoginPassword"><label style="color:#94A3B8;">Afficher le mot de passe</label></div>
            <button onclick="login()" style="width:100%; padding:0.8rem; background:#FACC15; color:#0A0F1E; border:none; border-radius:0.5rem; font-weight:bold; cursor:pointer;">Se connecter</button>
            <div style="text-align:center; margin-top:1rem; color:#94A3B8;">Pas encore de compte ? <span onclick="showRegister()" style="color:#FACC15; cursor:pointer;">S'inscrire</span></div>
        </div>
        <div id="registerForm">
            <div class="input-group"><input type="text" id="regName" placeholder="Nom complet" style="width:100%; padding:0.8rem; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:0.5rem; color:white; margin-bottom:1rem;"></div>
            <div class="input-group"><input type="email" id="regEmail" placeholder="Email" style="width:100%; padding:0.8rem; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:0.5rem; color:white; margin-bottom:1rem;"></div>
            <div class="input-group"><input type="password" id="regPassword" placeholder="Mot de passe" style="width:100%; padding:0.8rem; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:0.5rem; color:white; margin-bottom:1rem;"></div>
            <div style="display:flex; align-items:center; gap:0.5rem; margin:0.5rem 0 1rem 0;"><input type="checkbox" id="showRegPassword"><label style="color:#94A3B8;">Afficher le mot de passe</label></div>
            <button onclick="register()" style="width:100%; padding:0.8rem; background:#FACC15; color:#0A0F1E; border:none; border-radius:0.5rem; font-weight:bold; cursor:pointer;">Créer mon compte</button>
            <div style="text-align:center; margin-top:1rem; color:#94A3B8;">Déjà un compte ? <span onclick="showLogin()" style="color:#FACC15; cursor:pointer;">Se connecter</span></div>
        </div>
        <div id="message" style="color:#EF4444; font-size:0.8rem; margin-top:1rem; text-align:center;"></div>
    </div>
</div>
<script>
    if(document.getElementById('showLoginPassword')) document.getElementById('showLoginPassword').addEventListener('change', function() { document.getElementById('loginPassword').type = this.checked ? 'text' : 'password'; });
    if(document.getElementById('showRegPassword')) document.getElementById('showRegPassword').addEventListener('change', function() { document.getElementById('regPassword').type = this.checked ? 'text' : 'password'; });
    function showLogin() { document.getElementById('registerForm').style.display = 'none'; document.getElementById('loginForm').style.display = 'block'; document.getElementById('formTitle').innerText = 'Connexion'; document.getElementById('message').innerHTML = ''; }
    function showRegister() { document.getElementById('registerForm').style.display = 'block'; document.getElementById('loginForm').style.display = 'none'; document.getElementById('formTitle').innerText = 'Créer un compte'; document.getElementById('message').innerHTML = ''; }
    async function register() { var res = await fetch('/api/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: document.getElementById('regName').value, email: document.getElementById('regEmail').value, password: document.getElementById('regPassword').value }) }); var data = await res.json(); if (res.ok) { document.getElementById('message').innerHTML = '<div style="color:#4ADE80;"> ' + data.message + '</div>'; setTimeout(function() { showLogin(); }, 2000); } else { document.getElementById('message').innerHTML = '<div style="color:#EF4444;"> ' + data.error + '</div>'; } }
    async function login() { var res = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.getElementById('loginEmail').value, password: document.getElementById('loginPassword').value }) }); var data = await res.json(); if (res.ok) { localStorage.setItem('token', data.token); window.location.href = '/mon-compte'; } else { document.getElementById('message').innerHTML = '<div style="color:#EF4444;"> ' + data.error + '</div>'; } }
    if (localStorage.getItem('token')) { window.location.href = '/mon-compte'; }
</script>
'''

@app.route('/login')
def login_page():
    return render_page("Connexion", LOGIN_PAGE, '["Connectez-vous à votre espace", "Accédez aux données sécurisées", "Identifiez-vous pour continuer"]')

# ==================== PAGE MON COMPTE ====================
MON_COMPTE = '''
<div class="hero"><h1><i class="fas fa-user-circle"></i> Mon compte</h1><p>Bienvenue sur votre espace personnel</p></div>
<div class="card-glass" style="text-align:center;"><div id="userInfo"></div><button onclick="logout()" style="margin-top:1rem; background:#EF4444; color:white; border:none; border-radius:0.5rem; padding:0.5rem 1rem; cursor:pointer;"><i class="fas fa-sign-out-alt"></i> Se déconnecter</button></div>
<script>
    async function loadUser() { var res = await fetch('/api/me'); if (res.ok) { var user = await res.json(); document.getElementById('userInfo').innerHTML = '<i class="fas fa-user" style="font-size:3rem; color:#FACC15;"></i><h2>' + user.name + '</h2><p><i class="fas fa-envelope"></i> ' + user.email + '</p><p><i class="fas fa-calendar"></i> Membre depuis 2025</p>'; } else { window.location.href = '/login'; } }
    async function logout() { await fetch('/api/logout', { method: 'POST' }); localStorage.removeItem('token'); window.location.href = '/'; }
    loadUser();
</script>
'''

@app.route('/mon-compte')
def mon_compte():
    return render_page("Mon compte", MON_COMPTE, '["Bienvenue dans votre espace", "Gérez vos informations", "Accédez aux fonctionnalités réservées"]')

# ==================== API ====================
@app.route('/api/agents')
def api_agents(): return jsonify(AGENTS)
@app.route('/api/societes')
def api_societes(): return jsonify(SOCIETES)
@app.route('/api/livres')
def api_livres(): return jsonify(LIVRES)
@app.route('/api/stats')
def api_stats():
    return jsonify({
        "nb_agents": len(AGENTS),
        "nb_societes": len(SOCIETES),
        "masse_salariale": sum(a['salaire'] for a in AGENTS),
        "manque_fiscal": sum(s['impot_du'] - s['impot_paye'] for s in SOCIETES) * 1_000_000
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
