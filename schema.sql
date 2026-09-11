-- ============================================================================
-- Neon Serverless PostgreSQL Schema with pgvector
-- Autonomous AI Open-World Ecosystem: State, Ledger, Memory & Bounties
-- ============================================================================

-- 1. Vector Extension for Semantic Memory Retrieval
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Agents Registry Table
CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    role VARCHAR(32) DEFAULT 'agent',
    balance NUMERIC(18, 4) DEFAULT 100.0000 CHECK (balance >= 0),
    reputation NUMERIC(8, 2) DEFAULT 10.00,
    level INT DEFAULT 1,
    xp INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Double-Entry Transactions Ledger Table
CREATE TABLE IF NOT EXISTS transactions (
    tx_id VARCHAR(64) PRIMARY KEY,
    sender_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id),
    recipient_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id),
    amount NUMERIC(18, 4) NOT NULL CHECK (amount > 0),
    fee NUMERIC(18, 4) DEFAULT 0.0000 CHECK (fee >= 0),
    memo TEXT,
    signature VARCHAR(128),
    status VARCHAR(16) DEFAULT 'CONFIRMED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_id);
CREATE INDEX IF NOT EXISTS idx_transactions_recipient ON transactions(recipient_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);

-- 4. Episodic and Semantic Memories with pgvector
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id),
    memory_id VARCHAR(64) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    importance INT DEFAULT 5 CHECK (importance >= 1 AND importance <= 10),
    source VARCHAR(64) DEFAULT 'Observation',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);

-- HNSW Vector Cosine Index for ultra-fast approximate nearest neighbors
CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw 
ON memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 5. Bounty Marketplace Table
CREATE TABLE IF NOT EXISTS bounties (
    bounty_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    reward NUMERIC(18, 4) NOT NULL CHECK (reward > 0),
    posted_by VARCHAR(32) NOT NULL REFERENCES agents(agent_id),
    assignee VARCHAR(32) REFERENCES agents(agent_id),
    status VARCHAR(32) DEFAULT 'OPEN', -- OPEN, CLAIMED, SUBMITTED, COMPLETED, CANCELLED
    proof_of_work TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_bounties_status ON bounties(status);
CREATE INDEX IF NOT EXISTS idx_bounties_posted_by ON bounties(posted_by);

-- 6. Autonomous Co-Governance RFC Proposals Table
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    summary TEXT NOT NULL,
    proposer_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id),
    status VARCHAR(32) DEFAULT 'ACTIVE', -- ACTIVE, PASSED, REJECTED, ENACTED
    votes_for INT DEFAULT 0,
    votes_against INT DEFAULT 0,
    total_eligible_voters INT DEFAULT 0,
    quorum_reached BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS proposal_votes (
    vote_id SERIAL PRIMARY KEY,
    proposal_id VARCHAR(64) NOT NULL REFERENCES proposals(proposal_id),
    agent_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id),
    choice VARCHAR(16) NOT NULL CHECK (choice IN ('FOR', 'AGAINST', 'ABSTAIN')),
    voted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(proposal_id, agent_id)
);
