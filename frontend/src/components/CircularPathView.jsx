import { useState, useEffect } from 'react';
import { getAllCircularPaths } from '../api';

export default function CircularPathView({ onCompanyClick }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [sortBy, setSortBy] = useState('length');

    useEffect(() => {
        setLoading(true);
        getAllCircularPaths()
            .then(res => setData(res.data))
            .catch(() => setData(null))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="page-section">
            <div className="loading-overlay"><div className="spinner" /><span>Detecting circular paths...</span></div>
        </div>
    );

    const paths = data?.circular_paths || data?.paths || [];
    const sorted = [...paths].sort((a, b) => {
        if (sortBy === 'length') return (b.path_nodes?.length || 0) - (a.path_nodes?.length || 0);
        if (sortBy === 'amount') return (b.total_amount || 0) - (a.total_amount || 0);
        return 0;
    });

    const totalAmount = paths.reduce((s, p) => s + (p.total_amount || 0), 0);

    return (
        <div className="page-section">
            <div className="page-header">
                <div>
                    <h1>Circular Transaction Intelligence</h1>
                    <p>Detecting fund flows that loop back to origin • 3–7 hop analysis</p>
                </div>
                <div className="header-stats">
                    <span className="header-stat">{paths.length} loops</span>
                    <span className="header-stat">₹{(totalAmount / 10000000).toFixed(1)}Cr total</span>
                </div>
            </div>

            {paths.length > 0 && (
                <div className="sort-controls">
                    <button className={`ctrl-btn ${sortBy === 'length' ? 'active' : ''}`} onClick={() => setSortBy('length')}>By Length</button>
                    <button className={`ctrl-btn ${sortBy === 'amount' ? 'active' : ''}`} onClick={() => setSortBy('amount')}>By Amount</button>
                </div>
            )}

            {sorted.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /></svg>
                    </div>
                    <h3>No circular paths detected</h3>
                    <p>Run the pipeline to analyze transaction flow patterns.</p>
                </div>
            ) : (
                <div className="paths-list">
                    {sorted.slice(0, 50).map((p, i) => {
                        const nodes = p.path_nodes || p.path || [];
                        const amount = p.total_amount || 0;
                        const hopCount = nodes.length;
                        const loopRisk = Math.min(
                            (hopCount <= 3 ? 40 : hopCount <= 5 ? 60 : 80) +
                            (amount > 50000000 ? 20 : 0), 100
                        );
                        const riskColor = loopRisk >= 70 ? 'var(--risk-critical)' : loopRisk >= 40 ? 'var(--risk-medium)' : 'var(--risk-low)';

                        return (
                            <div key={i} className="path-card">
                                <div className="path-header">
                                    <div className="path-info">
                                        <span className="path-label">Loop #{i + 1}</span>
                                        <span className="path-hops">{hopCount} hops</span>
                                    </div>
                                    <div className="path-metrics">
                                        <span className="path-amount">₹{(amount / 10000000).toFixed(2)}Cr</span>
                                        <span className={`risk-badge ${loopRisk >= 70 ? 'critical' : loopRisk >= 40 ? 'medium' : 'low'}`} style={{ marginLeft: 8 }}>
                                            {loopRisk >= 70 ? 'High Risk' : loopRisk >= 40 ? 'Medium Risk' : 'Low Risk'}
                                        </span>
                                    </div>
                                </div>
                                <div className="path-viz">
                                    {nodes.map((n, j) => (
                                        <span key={j} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <span
                                                className={`path-node ${j === 0 ? 'origin' : ''}`}
                                                onClick={() => onCompanyClick(n)}
                                                title={n}
                                            >
                                                {n.split('-')[1]?.slice(0, 6) || n.slice(0, 8)}
                                            </span>
                                            {j < nodes.length - 1 && (
                                                <svg className="path-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
                                                </svg>
                                            )}
                                        </span>
                                    ))}
                                    <svg className="path-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: '4px' }}>
                                        <path d="M19 12H5" /><path d="m12 19-7-7 7-7" />
                                    </svg>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
