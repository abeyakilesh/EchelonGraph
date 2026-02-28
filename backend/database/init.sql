-- EchelonGraph PostgreSQL Schema

CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    incorporation_date DATE,
    industry VARCHAR(128),
    annual_revenue NUMERIC(15,2),
    employee_count INTEGER DEFAULT 0,
    is_shell_suspect BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_features (
    company_id VARCHAR(64) PRIMARY KEY REFERENCES companies(id),
    degree_centrality FLOAT DEFAULT 0,
    betweenness_centrality FLOAT DEFAULT 0,
    pagerank FLOAT DEFAULT 0,
    clustering_coefficient FLOAT DEFAULT 0,
    community_id INTEGER DEFAULT -1,
    avg_transaction_deviation FLOAT DEFAULT 0,
    transaction_velocity_spike FLOAT DEFAULT 0,
    director_overlap_ratio FLOAT DEFAULT 0,
    circularity_index FLOAT DEFAULT 0,
    shell_risk_score FLOAT DEFAULT 0,
    cycle_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_scores (
    company_id VARCHAR(64) PRIMARY KEY REFERENCES companies(id),
    network_risk FLOAT DEFAULT 0,
    transaction_anomaly FLOAT DEFAULT 0,
    identity_overlap FLOAT DEFAULT 0,
    gnn_probability FLOAT DEFAULT 0,
    compliance_flags FLOAT DEFAULT 0,
    composite_score FLOAT DEFAULT 0,
    risk_band VARCHAR(20) DEFAULT 'Monitor',
    is_confirmed_fraud BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_explanations (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(64) REFERENCES companies(id),
    feature_name VARCHAR(128),
    feature_value FLOAT,
    shap_value FLOAT,
    rank INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS circular_paths (
    id SERIAL PRIMARY KEY,
    origin_company_id VARCHAR(64) REFERENCES companies(id),
    path_nodes TEXT[], -- array of company IDs in cycle
    cycle_length INTEGER,
    total_amount NUMERIC(15,2),
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_risk_scores_band ON risk_scores(risk_band);
CREATE INDEX idx_risk_scores_composite ON risk_scores(composite_score DESC);
CREATE INDEX idx_company_features_community ON company_features(community_id);
CREATE INDEX idx_circular_paths_origin ON circular_paths(origin_company_id);
