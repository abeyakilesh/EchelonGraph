import { useState, useEffect } from 'react';
import { getSuspiciousClusters } from '../api';

export default function ShellClusterView({ onCompanyClick }) {
    const [clusters, setClusters] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);

    useEffect(() => {
        setLoading(true);
        getSuspiciousClusters()
            .then(res => setClusters(res.data))
            .catch(() => setClusters(null))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="page-section">
            <div className="loading-overlay"><div className="spinner" /><span>Analyzing shell clusters...</span></div>
        </div>
    );

    const data = clusters?.clusters || [];

    return (
        <div className="page-section">
            <div className="page-header">
                <div>
                    <h1>Shell Cluster Intelligence</h1>
                    <p>Directors controlling 3+ companies • Ownership concentration analysis</p>
                </div>
                <div className="header-stats">
                    <span className="header-stat">{data.length} clusters</span>
                </div>
            </div>

            {data.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
                    </div>
                    <h3>No shell clusters detected</h3>
                    <p>Run the pipeline to analyze ownership patterns.</p>
                </div>
            ) : (
                <div className="cluster-grid">
                    {data.map((cluster, i) => {
                        const companies = cluster.companies || [];
                        const avgRisk = companies.length > 0
                            ? companies.reduce((s, c) => s + (c.risk_score || 0), 0) / companies.length : 0;
                        const totalExposure = companies.reduce((s, c) => s + (c.annual_revenue || 0), 0);
                        const riskColor = avgRisk >= 60 ? 'var(--risk-critical)' : avgRisk >= 40 ? 'var(--risk-medium)' : 'var(--risk-low)';

                        return (
                            <div key={i} className="cluster-card">
                                <div className="cluster-header" onClick={() => setExpanded(cluster)}>
                                    <div className="cluster-director">
                                        <div className={`director-avatar ${avgRisk >= 60 ? 'high-risk-pulse' : ''}`} style={{ borderColor: riskColor, color: riskColor }}>
                                            {cluster.director?.charAt(0) || 'D'}
                                        </div>
                                        <div>
                                            <div className="director-name">{cluster.director || `Cluster ${i + 1}`}</div>
                                            <div className="director-meta">{companies.length} companies controlled</div>
                                        </div>
                                    </div>
                                    <span className={`risk-badge ${avgRisk >= 60 ? 'critical' : avgRisk >= 40 ? 'medium' : 'low'}`} style={{ position: 'absolute', top: 16, right: 16 }}>
                                        {avgRisk >= 60 ? 'High' : avgRisk >= 40 ? 'Med' : 'Low'}
                                    </span>
                                </div>

                                <div className="cluster-sparkline" onClick={() => setExpanded(cluster)}>
                                    {companies.slice(0, 30).map((c, idx) => (
                                        <div key={idx} className="spark-bar" style={{
                                            height: `${Math.max(15, (c.risk_score || 0))}%`,
                                            background: (c.risk_score || 0) >= 60 ? 'var(--risk-critical)' : (c.risk_score || 0) >= 40 ? 'var(--risk-medium)' : 'var(--risk-low)'
                                        }} />
                                    ))}
                                </div>

                                <div className="cluster-metrics">
                                    <div className="cm-item">
                                        <span className="cm-label">Companies</span>
                                        <span className="cm-value">{companies.length}</span>
                                    </div>
                                    <div className="cm-item">
                                        <span className="cm-label">Avg Risk</span>
                                        <span className="cm-value" style={{ color: riskColor }}>{avgRisk.toFixed(1)}</span>
                                    </div>
                                    <div className="cm-item">
                                        <span className="cm-label">Exposure</span>
                                        <span className="cm-value">₹{(totalExposure / 10000000).toFixed(1)}Cr</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {expanded && (
                <div className="modal-overlay" onClick={() => setExpanded(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <h2>{expanded.director || 'Cluster'}</h2>
                                <p>{expanded.companies?.length || 0} Controlled Entities</p>
                            </div>
                            <button className="modal-close" onClick={() => setExpanded(null)}>✕</button>
                        </div>
                        <div className="modal-body">
                            {expanded.companies?.map(c => (
                                <div key={c.id} className="cluster-company-row" onClick={() => { setExpanded(null); onCompanyClick(c.id); }}>
                                    <span className="cc-name">{c.name}</span>
                                    <span className="cc-industry">{c.industry}</span>
                                    <span className="risk-badge-sm" style={{
                                        color: (c.risk_score || 0) >= 71 ? 'var(--risk-critical)' : (c.risk_score || 0) >= 51 ? 'var(--risk-high)' : 'var(--risk-low)'
                                    }}>{(c.risk_score || 0).toFixed(0)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
