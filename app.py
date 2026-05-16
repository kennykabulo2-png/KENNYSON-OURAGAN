from flask import Flask, jsonify
import json

app = Flask(__name__)

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
    {"titre": "Le prix de la corruption", "auteur": "M. Nkolo", "categorie": "Anti-corruption"},
    {"titre": "Gestion des finances publiques", "auteur": "J. Tshibangu", "categorie": "Finances"},
    {"titre": "Manuel du citoyen congolais", "auteur": "Société civile", "categorie": "Droits citoyens"},
]

# ==================== TEMPLATE BASE (sans conflit avec .format) ====================
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OYEBI · [TITLE]</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;400;500;600;700;800&display=swap" rel="stylesheet">
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
        .nav-links a { color: #F1F5F9; text-decoration: none; font-weight: 500; font-size: 0.9rem; transition: 0.3s; }
        .nav-links a:hover { color: #FACC15; }
        .container { position: relative; z-index: 2; max-width: 1280px; margin: 0 auto; padding: 6rem 1.5rem 2rem; }
        .hero { background: rgba(255,255,255,0.03); backdrop-filter: blur(10px); border-radius: 2rem; padding: 3rem 2rem; text-align: center; margin-bottom: 2rem; border: 1px solid rgba(255,255,255,0.1); }
        .hero h1 { font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #FFFFFF, #0085CA, #FACC15); -webkit-background-clip: text; background-clip: text; color: transparent; margin-bottom: 1rem; }
        .typed-text { font-size: 1.2rem; color: #FACC15; margin-bottom: 1rem; min-height: 4rem; }
        .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card-glass { background: rgba(255,255,255,0.03); backdrop-filter: blur(10px); border-radius: 1rem; padding: 1.5rem; border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s ease; height: 100%; }
        .card-glass:hover { transform: translateY(-5px); border-color: #FACC15; background: rgba(255,255,255,0.07); }
        .card-glass i { font-size: 2rem; color: #FACC15; margin-bottom: 1rem; }
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
    </div>
</nav>
<div class="container">
    [CONTENT]
</div>
<footer class="footer">OYEBI · Gouvernance transparente · Kinshasa, RDC</footer>
<script>
    particlesJS("particles-js", {
        particles: {
            number: { value: 80, density: { enable: true, value_area: 800 } },
            color: { value: "#0085CA" },
            shape: { type: "circle" },
            opacity: { value: 0.5, random: true },
            size: { value: 3, random: true },
            line_linked: { enable: true, distance: 150, color: "#0085CA", opacity: 0.2, width: 1 },
            move: { enable: true, speed: 2, direction: "none", random: true, straight: false, out_mode: "out" }
        },
        interactivity: {
            detect_on: "canvas",
            events: { onhover: { enable: true, mode: "repulse" }, onclick: { enable: true, mode: "push" } }
        },
        retina_detect: true
    });
    const phrases = [PHRASES];
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
</script>
</body>
</html>
'''

def render_page(title, content, phrases):
    html = BASE_TEMPLATE.replace("[TITLE]", title).replace("[CONTENT]", content).replace("[PHRASES]", phrases)
    return html

# ==================== PAGE ACCUEIL ====================
ACCUEIL = '''
<div class="hero">
    <h1>OYEBI</h1>
    <div class="typed-text" id="typed"></div>
</div>
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
<div class="grid-4" id="kpis"></div>
<div class="card-glass"><h3><i class="fas fa-chart-line"></i> Comparaison impôts (M$)</h3><canvas id="chart"></canvas></div>
<div class="card-glass"><h3><i class="fas fa-users"></i> Agents de l'État</h3>
    <div style="overflow-x: auto;">
        <table class="agents-table">
            <thead><tr><th>Matricule</th><th>Nom</th><th>Grade</th><th>Salaire</th></tr></thead>
            <tbody id="agentsTable"></tbody>
        </table>
    </div>
</div>
<div class="card-glass"><h3><i class="fas fa-building"></i> Sociétés</h3><div id="societesTable"></div></div>
<script>
    async function fetchData(url) { let r = await fetch(url); return r.json(); }
    async function load() {
        let agents = await fetchData('/api/agents');
        let societes = await fetchData('/api/societes');
        let stats = await fetchData('/api/stats');
        document.getElementById('kpis').innerHTML = `
            <div class="card-glass"><div class="kpi-value">${stats.nb_agents}</div><div>Agents</div></div>
            <div class="card-glass"><div class="kpi-value">${stats.nb_societes}</div><div>Sociétés</div></div>
            <div class="card-glass"><div class="kpi-value">${(stats.masse_salariale/1e6).toFixed(1)}M</div><div>Masse salariale</div></div>
            <div class="card-glass"><div class="kpi-value">${(stats.manque_fiscal/1e6).toFixed(0)}M</div><div>Manque 2025</div></div>
        `;
        let agentsHtml = '';
        agents.forEach(a => {
            agentsHtml += `<tr><td><strong>${a.id}</strong></td><td>${a.nom}</td><td><span class="grade-badge">${a.grade}</span></td><td class="salaire">${(a.salaire/1e6).toFixed(2)} M FC</td></tr>`;
        });
        document.getElementById('agentsTable').innerHTML = agentsHtml;
        let societesHtml = '<thead><tr><th>Société</th><th>Impôt dû</th><th>Payé</th><th>Statut</th></tr></thead><tbody>';
        societes.forEach(s => {
            let badge = s.statut === 'Alerte' ? 'badge-alert' : (s.statut === 'Conforme' ? 'badge-conforme' : 'badge-modere');
            societesHtml += `<tr><td><strong>${s.nom}</strong></td><td>${s.impot_du} M$</td><td>${s.impot_paye} M$</td><td><span class="${badge}">${s.statut}</span></td></tr>`;
        });
        societesHtml += '</tbody>';
        document.getElementById('societesTable').innerHTML = societesHtml;
        new Chart(document.getElementById('chart'), {
            type: 'bar', data: { labels: societes.map(s => s.nom), datasets: [{ label: 'Dû', data: societes.map(s => s.impot_du), backgroundColor: '#0085CA' }, { label: 'Payé', data: societes.map(s => s.impot_paye), backgroundColor: '#FACC15' }] }
        });
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
        let societes = await (await fetch('/api/societes')).json();
        let total = societes.reduce((s,c)=>s+(c.impot_du-c.impot_paye),0);
        let mines = societes.find(s=>s.nom==='Minière du Congo');
        let telecom = societes.find(s=>s.nom==='Telecom Congo');
        let btp = societes.find(s=>s.nom==='BTP Congo');
        let m = mines.impot_du - mines.impot_paye;
        let t = telecom.impot_du - telecom.impot_paye;
        let b = btp.impot_du - btp.impot_paye;
        document.getElementById('insightsGrid').innerHTML = `
            <div class="card-glass"><h3>Mines</h3><div class="kpi-value">${m}M$</div><div>${Math.round(m/total*100)}% du total</div></div>
            <div class="card-glass"><h3>Télécoms</h3><div class="kpi-value">${t}M$</div><div>${Math.round(t/total*100)}%</div></div>
            <div class="card-glass"><h3>BTP</h3><div class="kpi-value">${b}M$</div><div>${Math.round(b/total*100)}%</div></div>
        `;
        new Chart(document.getElementById('donut'), {
            type: 'doughnut', data: { labels: ['Mines','Télécoms','BTP','Commerce'], datasets: [{ data: societes.map(s=>s.impot_du-s.impot_paye), backgroundColor: ['#0085CA','#FACC15','#EF4444','#10B981'] }] }
        });
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
        let stats = await (await fetch('/api/stats')).json();
        let obj1 = { objectif: 15000, realise: stats.manque_fiscal/1e6 };
        let obj2 = { objectif: 500, realise: 120 };
        document.getElementById('o1').innerHTML = `<i class="fas fa-chart-simple"></i> Objectif ${obj1.objectif}M$ | <i class="fas fa-check-circle"></i> Réalisé ${obj1.realise}M$`;
        document.getElementById('o2').innerHTML = `<i class="fas fa-chart-simple"></i> Objectif ${obj2.objectif} agents | <i class="fas fa-check-circle"></i> Réalisé ${obj2.realise} agents`;
        document.getElementById('b1').style.width = `${Math.min((obj1.realise/obj1.objectif)*100,100)}%`;
        document.getElementById('b2').style.width = `${Math.min((obj2.realise/obj2.objectif)*100,100)}%`;
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
<script>
    async function loadBooks() {
        let livres = await (await fetch('/api/livres')).json();
        let html = '';
        for (let l of livres) {
            html += `<div class="card-glass"><i class="fas fa-book" style="font-size:1.5rem; color:#FACC15;"></i><h3>${l.titre}</h3><p>${l.auteur}</p><small>${l.categorie}</small></div>`;
        }
        document.getElementById('booksGrid').innerHTML = html;
    }
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
<div class="card-glass" style="text-align: center;"><h2><i class="fas fa-laptop-code"></i> Concepteur</h2><p><strong>Kenny Kabulo Matanda</strong><br>Kinshasa, RDC</p></div>
'''

@app.route('/apropos')
def apropos():
    return render_page("À propos", APROPOS, '["Une vision pour un Congo transparent.", "La donnée au service du citoyen.", "Innovation et intégrité."]')

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
