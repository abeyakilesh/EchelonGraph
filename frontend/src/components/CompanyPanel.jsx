import { useState, useEffect } from 'react';
import { getCompany, getInvestigationSummary, getRiskScore, propagateFraud } from '../api';

export default function CompanyPanel({ companyId, onClose, userRole }) {
    const [company, setCompany] = useState(null);
    const [summary, setSummary] = useState(null);
    const [riskDetails, setRiskDetails] = useState(null);
    const [tab, setTab] = useState('overview');
    const [loading, setLoading] = useState(true);
    const [escalated, setEscalated] = useState(false);

    useEffect(() => {
        if (!companyId) return;
        setLoading(true);
        setTab('overview');
        setEscalated(false);
        setSummary(null);

        Promise.all([
            getCompany(companyId).then(r => setCompany(r.data)).catch(() => setCompany(null)),
            getRiskScore(companyId).then(r => setRiskDetails(r.data)).catch(() => null),
        ]).finally(() => setLoading(false));
    }, [companyId]);

    useEffect(() => {
        if (tab === 'intelligence' && !summary && companyId) {
            getInvestigationSummary(companyId).then(r => setSummary(r.data)).catch(() => null);
        }
    }, [tab, companyId]);

    if (loading) return (
        <div className="detail-panel">
            <button className="panel-close" onClick={onClose}>✕</button>
            <div className="loading-overlay"><div className="spinner" /><span>Loading...</span></div>
        </div>
    );

    if (!company || company.error) return (
        <div className="detail-panel">
            <button className="panel-close" onClick={onClose}>✕</button>
            <div className="panel-error">
                <div className="error-icon">⚠️</div>
                <h3>Company Not Found</h3>
                <p>ID: {companyId}</p>
                <p>This entity may not have been loaded in the current graph subset.</p>
            </div>
        </div>
    );

    const riskColor = company.risk_score >= 71 ? 'var(--risk-critical)' :
        company.risk_score >= 51 ? 'var(--risk-high)' :
            company.risk_score >= 31 ? 'var(--risk-medium)' : 'var(--risk-low)';

    const signals = company.fraud_signals?.signals || [];
    const triggeredSignals = signals.filter(s => s.triggered);

    const tabs = [
        { key: 'overview', label: 'Overview' },
        { key: 'risk', label: 'Risk Breakdown' },
        { key: 'signals', label: `Signals (${triggeredSignals.length})` },
        { key: 'intelligence', label: 'AI Summary' },
    ];

    return (
        <div className="detail-panel">
            <button className="panel-close" onClick={onClose}>✕</button>

            <h2>{company.name}</h2>
            <div className="company-id">{company.id}</div>
            <div className="company-meta">
                <span>{company.industry}</span>
                {company.annual_revenue > 0 && <span>₹{(company.annual_revenue / 10000000).toFixed(1)}Cr</span>}
            </div>

            {/* Risk Gauge */}
            <div className="risk-gauge">
                <div className="gauge-value" style={{ color: riskColor }}>
                    {company.risk_score?.toFixed(0) || 0}
                </div>
                <span className={`risk-badge ${company.risk_band?.toLowerCase()}`}>{company.risk_band}</span>
                <div className="gauge-bar">
                    <div className="gauge-fill" style={{ width: `${company.risk_score || 0}%`, background: riskColor }} />
                </div>
            </div>

            {/* Tabs */}
            <div className="panel-tabs">
                {tabs.map(t => (
                    <button key={t.key} className={`panel-tab ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Overview */}
            {tab === 'overview' && (
                <div className="panel-section">
                    <div className="section-title">Network Metrics</div>
                    <div className="metrics-grid">
                        <div className="metric-item">
                            <div className="metric-label">PageRank</div>
                            <div className="metric-value">{company.pagerank?.toFixed(6)}</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-label">Betweenness</div>
                            <div className="metric-value">{company.betweenness_centrality?.toFixed(6)}</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-label">Clustering</div>
                            <div className="metric-value">{company.clustering_coefficient?.toFixed(4)}</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-label">Community</div>
                            <div className="metric-value">{company.community_id}</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-label">Neighbors</div>
                            <div className="metric-value">{company.neighbor_count}</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-label">GNN Prob</div>
                            <div className="metric-value" style={{ color: company.gnn_probability > 0.5 ? 'var(--risk-critical)' : 'var(--risk-low)' }}>
                                {(company.gnn_probability * 100).toFixed(0)}%
                            </div>
                        </div>
                    </div>

                    {company.neighbors?.length > 0 && (
                        <>
                            <div className="section-title">Top Neighbors</div>
                            <div className="neighbor-list">
                                {company.neighbors.map(n => (
                                    <div key={n.id} className="neighbor-item">
                                        <span className="n-name">{n.name}</span>
                                        <span className="risk-badge-sm" style={{ color: n.risk_score >= 51 ? 'var(--risk-critical)' : 'var(--risk-low)' }}>
                                            {n.risk_score?.toFixed(0)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Risk Breakdown */}
            {tab === 'risk' && riskDetails && (
                <div className="panel-section">
                    <div className="section-title">5-Factor Risk Decomposition</div>
                    {[
                        { label: 'Structural Centrality', value: riskDetails.structural_centrality, weight: '25%' },
                        { label: 'Transaction Anomaly', value: riskDetails.transaction_anomaly, weight: '25%' },
                        { label: 'Ownership Overlap', value: riskDetails.ownership_overlap, weight: '20%' },
                        { label: 'Circular Involvement', value: riskDetails.circular_involvement, weight: '15%' },
                        { label: 'ML Probability', value: riskDetails.ml_probability, weight: '15%' },
                    ].map(f => (
                        <div key={f.label} className="shap-bar">
                            <div className="bar-label">{f.label} <span className="bar-weight">({f.weight})</span></div>
                            <div className="bar-track">
                                <div className="bar-fill" style={{
                                    width: `${f.value || 0}%`,
                                    background: f.value >= 70 ? 'var(--risk-critical)' : f.value >= 40 ? 'var(--risk-medium)' : 'var(--risk-low)'
                                }} />
                            </div>
                            <div className="bar-value">{f.value?.toFixed(1)}</div>
                        </div>
                    ))}

                    <div className="composite-result">
                        <span>Composite Score</span>
                        <span style={{ color: riskColor, fontWeight: 700 }}>{riskDetails.composite_score?.toFixed(1)}</span>
                    </div>
                </div>
            )}

            {/* Fraud Signals */}
            {tab === 'signals' && (
                <div className="panel-section">
                    <div className="section-title">Advanced Fraud Signals</div>
                    {signals.map((s, i) => (
                        <div key={i} className={`signal-card ${s.triggered ? 'triggered' : ''}`}>
                            <div className="signal-header">
                                <span className={`signal-dot ${s.triggered ? 'red' : 'green'}`} />
                                <span className="signal-name">{s.signal}</span>
                                <span className="signal-score">{s.score?.toFixed(0)}</span>
                            </div>
                            <div className="signal-detail">{s.detail}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* AI Intelligence Summary */}
            {tab === 'intelligence' && (
                <div className="panel-section">
                    <div className="section-title">AI Investigation Summary</div>
                    {summary ? (
                        <>
                            <div className="ai-summary">{summary.summary}</div>

                            {summary.top_counterparties?.length > 0 && (
                                <>
                                    <div className="section-title">Top Counterparties</div>
                                    <table className="data-table compact">
                                        <thead>
                                            <tr><th>Entity</th><th>Volume</th><th>Risk</th></tr>
                                        </thead>
                                        <tbody>
                                            {summary.top_counterparties.map((cp, i) => (
                                                <tr key={i}>
                                                    <td>{cp.name}</td>
                                                    <td className="mono">₹{(cp.volume / 10000000).toFixed(1)}Cr</td>
                                                    <td className="mono" style={{ color: cp.risk >= 51 ? 'var(--risk-critical)' : 'var(--risk-low)' }}>
                                                        {cp.risk?.toFixed(0)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </>
                            )}

                            <div className="section-title">Evidence Summary</div>
                            <div className="evidence-grid">
                                <div className="evidence-item">
                                    <span>Shared Directors</span><span>{summary.evidence?.shared_directors || 0}</span>
                                </div>
                                <div className="evidence-item">
                                    <span>Circular Loops</span><span>{summary.evidence?.circular_loops || 0}</span>
                                </div>
                                <div className="evidence-item">
                                    <span>High-Risk Counterparties</span><span>{summary.evidence?.high_risk_counterparties || 0}</span>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="loading-overlay"><div className="spinner" /><span>Generating summary...</span></div>
                    )}
                </div>
            )}

            {/* Actions */}
            <div className="panel-actions">
                {['admin', 'investigator'].includes(userRole) && (
                    <button
                        className={`btn ${escalated ? 'btn-secondary' : 'btn-danger'}`}
                        onClick={() => setEscalated(true)}
                        disabled={escalated}
                    >
                        {escalated ? '✓ Escalated' : 'Escalate for Review'}
                    </button>
                )}
                <button className="btn btn-secondary" onClick={() => window.print()}>
                    Export Report
                </button>
            </div>
        </div>
    );
}
