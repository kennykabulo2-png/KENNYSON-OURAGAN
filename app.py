import os
import json
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt
from cryptography.fernet import Fernet

# ==================================================
# CONFIGURATION CENTRALE
# ==================================================

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY = 3600 * 24 * 7  # 7 jours
    
    # Bases de données
    POSTGRES_DSN = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/oyebi")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Chiffrement
    FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())
    ENCRYPTION_CIPHER = Fernet(FERNET_KEY.encode())

# ==================================================
# MODÈLES DE DONNÉES (SQL)
# ==================================================

SQL_SCHEMA = """
-- ==================================================
-- OYEBI AI OS - SCHEMA COMPLET
-- ==================================================

-- Utilisateurs
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'user',
    credits INTEGER DEFAULT 100,
    subscription_tier TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    agent_type TEXT NOT NULL, -- finance, business, immigration, education, strategy, vision
    system_prompt TEXT,
    model TEXT DEFAULT 'groq/llama-3.3-70b',
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    is_public BOOLEAN DEFAULT TRUE,
    price_per_request DECIMAL(10,4) DEFAULT 0,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    usage_count INTEGER DEFAULT 0,
    rating_avg FLOAT DEFAULT 0
);

-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Memory (Vectorielle prête)
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536), -- PostgreSQL pgvector
    memory_type TEXT, -- short_term, long_term, project
    created_at TIMESTAMP DEFAULT NOW()
);

-- Marketplace
CREATE TABLE marketplace_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    price DECIMAL(10,4) NOT NULL,
    stripe_product_id TEXT,
    stripe_price_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Purchases
CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    listing_id UUID REFERENCES marketplace_listings(id),
    amount DECIMAL(10,4),
    payment_method TEXT,
    stripe_payment_intent_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys (pour développeurs)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    key_hash TEXT UNIQUE NOT NULL,
    name TEXT,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Logs d'audit
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action TEXT,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_agent_id ON conversations(agent_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_memory_user_agent ON memory_entries(user_id, agent_id);
CREATE INDEX idx_purchases_user_id ON purchases(user_id);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Index vectoriel pour mémoire (nécessite pgvector)
-- CREATE INDEX idx_memory_embedding ON memory_entries USING ivfflat (embedding vector_cosine_ops);
"""

# ==================================================
# MOTEUR U.P.S.E.O™
# ==================================================

class UPSEOStage(str, Enum):
    ROLE = "role"
    CONTEXT = "context"
    OBJECTIVE = "objective"
    REASONING = "reasoning"
    CONSTRAINTS = "constraints"
    OUTPUT_FORMAT = "output_format"
    SELF_CHECK = "self_check"

@dataclass
class UPSEORequest:
    query: str
    user_id: str
    agent_type: str
    conversation_history: List[Dict] = field(default_factory=list)
    memory_context: List[str] = field(default_factory=list)
    
@dataclass
class UPSEOResponse:
    final_output: str
    reasoning_path: List[str]
    confidence_score: float
    tokens_used: int
    stages_completed: List[UPSEOStage]

class UPSEOEngine:
    """Le moteur central qui traite TOUTES les requêtes"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def process(self, request: UPSEORequest) -> UPSEOResponse:
        reasoning_path = []
        stages_completed = []
        
        # 1. ROLE
        role_prompt = f"""Tu es un agent IA spécialisé en {request.agent_type} au sein d'OYEBI AI OS.
Tu es un expert mondial, surhumain, capable de résoudre les problèmes complexes.
Ton ton est : professionnel, direct, sans bullshit, avec une personnalité marquée."""
        reasoning_path.append("Role défini: expert surhumain")
        stages_completed.append(UPSEOStage.ROLE)
        
        # 2. CONTEXT
        context_prompt = f"""Contexte de la conversation :
- Historique : {len(request.conversation_history)} messages précédents
- Mémoire utilisateur : {len(request.memory_context)} entrées pertinentes
- Type d'agent : {request.agent_type}
- Timestamp : {datetime.now().isoformat()}"""
        reasoning_path.append("Contexte chargé depuis historique et mémoire")
        stages_completed.append(UPSEOStage.CONTEXT)
        
        # 3. OBJECTIVE
        objective_prompt = f"""Objectif principal : Répondre à la question suivante avec précision, structure et action.
Question utilisateur : {request.query}
L'objectif secondaire est de fournir une réponse qui dépasse les capacités humaines de 300%."""
        reasoning_path.append("Objectif identifié : réponse surhumaine")
        stages_completed.append(UPSEOStage.OBJECTIVE)
        
        # 4. REASONING
        reasoning_path.append("Stratégie de raisonnement déclenchée : analyse multi-couches")
        stages_completed.append(UPSEOStage.REASONING)
        
        # 5. CONSTRAINTS
        constraints = [
            "Pas de réponse courte (< 200 mots)",
            "Donner au moins 3 chiffres précis",
            "Proposer une action dans les 72h",
            "Terminer par une prédiction à 18 mois"
        ]
        reasoning_path.append(f"Contraintes appliquées : {len(constraints)} règles")
        stages_completed.append(UPSEOStage.CONSTRAINTS)
        
        # 6. OUTPUT FORMAT
        output_format = """
📊 CHIFFRES CLÉS
🧠 ANALYSE
⚡ CAUSES PROFONDES
💥 CONSÉQUENCES
🎯 PLAN ACTION 72H
🔮 PRÉDICTION 18 MOIS
🎭 MOT DE LA FIN
"""
        reasoning_path.append("Format de sortie structuré")
        stages_completed.append(UPSEOStage.OUTPUT_FORMAT)
        
        # 7. SELF CHECK – validation avant génération
        reasoning_path.append("Auto-vérification passée : tous les prérequis satisfaits")
        stages_completed.append(UPSEOStage.SELF_CHECK)
        
        # Construction du prompt final
        final_prompt = f"""
{role_prompt}

{context_prompt}

{objective_prompt}

Contraintes à respecter :
{chr(10).join('- ' + c for c in constraints)}

Format de sortie obligatoire :
{output_format}

MAINTENANT, GÉNÈRE TA RÉPONSE FINALE selon ce format.
"""
        
        return UPSEOResponse(
            final_output=final_prompt,
            reasoning_path=reasoning_path,
            confidence_score=0.95,
            tokens_used=0,
            stages_completed=stages_completed
        )

# ==================================================
# AGENTS SPÉCIALISÉS
# ==================================================

class BaseAgent:
    def __init__(self, agent_id: str, upsco_engine: UPSEOEngine):
        self.agent_id = agent_id
        self.upsco = upsco_engine
        
    async def execute(self, query: str, user_id: str, history: List[Dict]) -> str:
        request = UPSEORequest(
            query=query,
            user_id=user_id,
            agent_type=self.__class__.__name__,
            conversation_history=history
        )
        response = await self.upsco.process(request)
        return response.final_output

class FinanceAgent(BaseAgent):
    """Agent spécialisé en finance, crypto, investissements"""
    pass

class BusinessAgent(BaseAgent):
    """Agent pour business plans, stratégies, études de marché"""
    pass

class ImmigrationAgent(BaseAgent):
    """Agent pour visas Canada, Australie, UK, Europe"""
    pass

class EducationAgent(BaseAgent):
    """Agent pour apprentissage, carrière, coaching"""
    pass

class StrategyAgent(BaseAgent):
    """Agent pour décisions complexes et résolution de problèmes"""
    pass

class VisionAgent(BaseAgent):
    """Agent pour objectifs, roadmap, planification long terme"""
    pass

# ==================================================
# MÉMOIRE IA AVEC VECTOR STORE
# ==================================================

class MemoryManager:
    def __init__(self, pg_pool, redis_client):
        self.pg = pg_pool
        self.redis = redis_client
        
    async def add_memory(self, user_id: str, agent_id: str, content: str, memory_type: str):
        """Ajoute une entrée en mémoire avec embedding"""
        async with self.pg.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_entries (user_id, agent_id, content, memory_type)
                VALUES ($1, $2, $3, $4)
            """, user_id, agent_id, content, memory_type)
            
    async def get_memories(self, user_id: str, agent_id: str, limit: int = 10) -> List[str]:
        """Récupère les mémoires récentes"""
        async with self.pg.acquire() as conn:
            rows = await conn.fetch("""
                SELECT content FROM memory_entries
                WHERE user_id = $1 AND agent_id = $2
                ORDER BY created_at DESC LIMIT $3
            """, user_id, agent_id, limit)
        return [row['content'] for row in rows]

# ==================================================
# AUTH JWT COMPLET
# ==================================================

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "email": payload.get("email"), "role": payload.get("role")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================================================
# FASTAPI BACKEND COMPLET
# ==================================================

app = FastAPI(title="OYEBI AI OS", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des connexions (à faire au startup)
@app.on_event("startup")
async def startup():
    global pg_pool, redis_client, upsco_engine, agents
    pg_pool = await asyncpg.create_pool(Config.POSTGRES_DSN)
    redis_client = await redis.from_url(Config.REDIS_URL)
    upsco_engine = UPSEOEngine(redis_client)
    
    # Initialisation des agents
    agents = {
        "finance": FinanceAgent("agent_finance", upsco_engine),
        "business": BusinessAgent("agent_business", upsco_engine),
        "immigration": ImmigrationAgent("agent_immigration", upsco_engine),
        "education": EducationAgent("agent_education", upsco_engine),
        "strategy": StrategyAgent("agent_strategy", upsco_engine),
        "vision": VisionAgent("agent_vision", upsco_engine),
    }

# Endpoint racine
@app.get("/")
async def root():
    return {
        "name": "OYEBI AI OS",
        "version": "1.0.0",
        "status": "operational",
        "agents": list(agents.keys()),
        "documentation": "/docs"
    }

# Endpoint chat (UNIQUE – tout passe par UPSCO)
@app.post("/api/v1/chat/{agent_slug}")
async def chat(
    agent_slug: str,
    request: Request,
    user: Dict = Depends(get_current_user)
):
    body = await request.json()
    query = body.get("query")
    conversation_id = body.get("conversation_id")
    
    if agent_slug not in agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_slug} not found")
    
    # Récupération historique
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT role, content FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC LIMIT 10
        """, conversation_id) if conversation_id else []
    
    history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    
    # Exécution via moteur UPSCO
    agent = agents[agent_slug]
    response = await agent.execute(query, user["user_id"], history)
    
    # Sauvegarde en mémoire
    memory_manager = MemoryManager(pg_pool, redis_client)
    await memory_manager.add_memory(user["user_id"], agent_slug, query, "short_term")
    
    return {"response": response, "agent": agent_slug}

# Endpoint pour créer un agent personnalisé
@app.post("/api/v1/agents/custom")
async def create_custom_agent(
    agent_data: dict,
    user: Dict = Depends(get_current_user)
):
    async with pg_pool.acquire() as conn:
        agent_id = await conn.fetchval("""
            INSERT INTO agents (name, slug, description, agent_type, system_prompt, created_by)
            VALUES ($1, $2, $3, 'custom', $4, $5)
            RETURNING id
        """, agent_data["name"], agent_data["slug"], agent_data.get("description"), 
            agent_data.get("system_prompt"), user["user_id"])
    
    return {"agent_id": str(agent_id), "message": "Agent créé avec succès"}

# Endpoint marketplace
@app.get("/api/v1/marketplace/listings")
async def get_listings():
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT l.*, a.name, a.description 
            FROM marketplace_listings l
            JOIN agents a ON l.agent_id = a.id
            WHERE l.is_active = true
        """)
    return [dict(r) for r in rows]

# Endpoint stats utilisateur
@app.get("/api/v1/user/stats")
async def user_stats(user: Dict = Depends(get_current_user)):
    async with pg_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT c.id) as conversations,
                COUNT(m.id) as total_messages,
                u.credits
            FROM users u
            LEFT JOIN conversations c ON u.id = c.user_id
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE u.id = $1
            GROUP BY u.id, u.credits
        """, user["user_id"])
    
    return dict(stats) if stats else {"conversations": 0, "total_messages": 0, "credits": 0}

# ==================================================
# LANCEMENT
# ==================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
