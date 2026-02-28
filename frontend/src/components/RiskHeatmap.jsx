import { useState, useEffect } from 'react';
import { getCommunityRisk } from '../api';

export default function RiskHeatmap({ onCompanyClick }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);

    useEffect(() => {
        setLoading(true);
        getCommunityRisk()
            .then(res => setData(res.data))
            .catch(() => setData(null))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="page-section">
            <div className="loading-overlay"><div className="spinner" /><span>Analyzing communities...</span></div>
        </div>
    );

    const communities = data?.communities || [];

    const getRiskColor = (score) => {
        if (score >= 60) return { bg: 'color-mix(in srgb, var(--risk-critical) 15%, transparent)', border: 'color-mix(in srgb, var(--risk-critical) 30%, transparent)', text: 'var(--risk-critical)' };
        if (score >= 40) return { bg: 'color-mix(in srgb, var(--risk-high) 15%, transparent)', border: 'color-mix(in srgb, var(--risk-high) 30%, transparent)', text: 'var(--risk-high)' };
        if (score >= 20) return { bg: 'color-mix(in srgb, var(--risk-medium) 15%, transparent)', border: 'color-mix(in srgb, var(--risk-medium) 30%, transparent)', text: 'var(--risk-medium)' };
        return { bg: 'color-mix(in srgb, var(--risk-low) 10%, transparent)', border: 'color-mix(in srgb, var(--risk-low) 20%, transparent)', text: 'var(--risk-low)' };
    };

    return (
        <div className="page-section">
            <div className="page-header">
                <div>
                    <h1>Risk Heatmap</h1>
                    <p>Louvain community detection • Color-coded by average risk</p>
                </div>
                <div className="header-stats">
                    <span className="header-stat">{communities.length} communities</span>
                </div>
            </div>

            {communities.length === 0 ? (
                <div className="empty-dashboard-hero">
                    <div className="empty-hero-icon">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" /><path d="M9 3v18" /><path d="M15 3v18" /><path d="M3 9h18" /><path d="M3 15h18" /></svg>
                    </div>
                    <h3 className="empty-hero-title">No Community Data</h3>
                    <p className="empty-hero-text">Run the analysis pipeline to detect communities via Louvain clustering and evaluate their density.</p>
                </div>
            ) : (
                <div className="cluster-grid">
                    {communities.map((c, i) => {
                        const colors = getRiskColor(c.avg_risk || 0);

                        return (
                            <div key={i} className="heatmap-card" style={{ borderColor: colors.border }} onClick={() => setExpanded(c)}>
                                <div className="hm-header">
                                    <div className="hm-id">Community {c.community_id}</div>
                                    <div className="hm-risk" style={{ color: colors.text }}>
                                        {(c.avg_risk || 0).toFixed(1)}
                                    </div>
                                </div>

                                <div className="hm-metrics">
                                    <div className="hm-metric">
                                        <span>Nodes</span><span>{c.company_count}</span>
                                    </div>
                                    <div className="hm-metric">
                                        <span>Max Risk</span><span style={{ color: colors.text }}>{(c.max_risk || 0).toFixed(0)}</span>
                                    </div>
                                    <div className="hm-metric">
                                        <span>Internal Txns</span><span>{c.internal_txns || 0}</span>
                                    </div>
                                    <div className="hm-metric">
                                        <span>Volume</span><span>₹{((c.internal_volume || 0) / 10000000).toFixed(1)}Cr</span>
                                    </div>
                                </div>

                                <div className="hm-bar">
                                    <div className="hm-bar-fill" style={{
                                        width: `${Math.min(c.avg_risk || 0, 100)}%`,
                                        background: `linear-gradient(90deg, ${colors.bg} 0%, ${colors.text} 100%)`,
                                    }} />
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
                                <h2>Community {expanded.community_id}</h2>
                                <p>{expanded.company_count} Members • sorted by risk</p>
                            </div>
                            <button className="modal-close" onClick={() => setExpanded(null)}>✕</button>
                        </div>
                        <div className="modal-body">
                            {expanded.top_entities?.sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).map(emp => (
                                <div key={emp.id} className="cluster-company-row" onClick={() => { setExpanded(null); onCompanyClick(emp.id); }}>
                                    <span className="cc-name">{emp.name}</span>
                                    <span className="cc-industry">{emp.industry}</span>
                                    <span className="risk-badge-sm" style={{
                                        color: (emp.risk_score || 0) >= 71 ? 'var(--risk-critical)' : (emp.risk_score || 0) >= 51 ? 'var(--risk-high)' : 'var(--risk-low)'
                                    }}>{(emp.risk_score || 0).toFixed(0)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
