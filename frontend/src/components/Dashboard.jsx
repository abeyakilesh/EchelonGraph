import { useState, useEffect, useCallback } from 'react';
import GraphView from './GraphView';
import CompanyPanel from './CompanyPanel';
import RiskHeatmap from './RiskHeatmap';
import ShellClusterView from './ShellClusterView';
import CircularPathView from './CircularPathView';
import InvoiceVerification from './InvoiceVerification';
import {
    uploadData, getGraphData, computeFeatures, trainModel,
    computeAllRiskScores, getDashboardStats, getTopRiskCompanies,
    getRiskDistribution, searchCompanies
} from '../api';

export default function Dashboard({ user, onLogout, theme, setTheme }) {
    const [view, setView] = useState('dashboard');
    const [graphData, setGraphData] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');
    const [pipelineStep, setPipelineStep] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState(null);
    const [dashStats, setDashStats] = useState(null);
    const [topRisk, setTopRisk] = useState(null);
    const [riskDist, setRiskDist] = useState(null);
    const [showUserMenu, setShowUserMenu] = useState(false);

    useEffect(() => {
        if (view === 'dashboard') loadDashboard();
    }, [view]);

    const loadDashboard = async () => {
        try {
            const [statsRes, topRes, distRes] = await Promise.all([
                getDashboardStats(), getTopRiskCompanies(10), getRiskDistribution()
            ]);
            setDashStats(statsRes.data);
            setTopRisk(topRes.data.companies || []);
            setRiskDist(distRes.data.distribution || []);
        } catch { /* first load may fail if no data */ }
    };

    const runPipeline = async () => {
        setLoading(true);
        const startTime = Date.now();

        try {
            setPipelineStep(1); setStatus('Generating synthetic data & building graph...');
            await uploadData(true);
            setPipelineStep(2); setStatus('Computing network features...');
            await computeFeatures();
            setPipelineStep(3); setStatus('Training fraud detection model...');
            await trainModel(50);
            setPipelineStep(4); setStatus('Computing composite risk scores...');
            await computeAllRiskScores();
            setPipelineStep(5); setStatus('Loading graph visualization...');
            const graphRes = await getGraphData(300);
            setGraphData(graphRes.data);
            await loadDashboard();

            // Artificial delay to let the animation play out for a better UX
            const elapsedTime = Date.now() - startTime;
            if (elapsedTime < 4000) {
                await new Promise(resolve => setTimeout(resolve, 4000 - elapsedTime));
            }

            setStatus('Pipeline complete');
            setPipelineStep(6);
        } catch (error) {
            setStatus(`Error: ${error.response?.data?.detail || error.message}`);
        }
        setLoading(false);
    };

    const handleSearch = async (e) => {
        e?.preventDefault();
        if (!searchQuery.trim()) { setSearchResults(null); return; }
        try {
            const res = await searchCompanies(searchQuery);
            setSearchResults(res.data.results);
        } catch { setSearchResults([]); }
    };

    const handleNodeClick = useCallback((node) => {
        setSelectedNode(node ? node.id || node : null);
    }, []);

    const navItems = [
        { key: 'dashboard', label: 'Executive Dashboard', icon: 'D' },
        { key: 'invoices', label: 'Invoice Verification', icon: 'V' },
        { key: 'investigation', label: 'Investigation', icon: 'I' },
        { key: 'shells', label: 'Shell Clusters', icon: 'S' },
        { key: 'circular', label: 'Circular Paths', icon: 'C' },
        { key: 'heatmap', label: 'Risk Heatmap', icon: 'H' },
    ];

    const getRiskColor = (score) => {
        if (score >= 71) return 'var(--risk-critical)';
        if (score >= 51) return 'var(--risk-high)';
        if (score >= 31) return 'var(--risk-medium)';
        return 'var(--risk-low)';
    };

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <div className="logo-icon">E</div>
                    <div>
                        <h1>EchelonGraph</h1>
                        <div className="version">v2.0</div>
                    </div>
                </div>

                <div className="nav-section-label">MODULES</div>
                {navItems.map(item => (
                    <div
                        key={item.key}
                        className={`nav-item ${view === item.key ? 'active' : ''}`}
                        onClick={() => setView(item.key)}
                    >
                        <span className="nav-icon-letter">{item.icon}</span>
                        {item.label}
                    </div>
                ))}

                <div style={{ flex: 1 }} />

                {user?.role === 'admin' && (
                    <button
                        className="btn btn-primary"
                        onClick={runPipeline}
                        disabled={loading}
                        style={{ width: '100%', justifyContent: 'center', marginBottom: 16 }}
                    >
                        {loading ? `Step ${pipelineStep}/5...` : 'Run Pipeline'}
                    </button>
                )}

                <div className="sidebar-user" onClick={() => setShowUserMenu(!showUserMenu)} style={{ marginTop: 'auto' }}>
                    <div className="user-avatar">{user?.name?.[0] || 'U'}</div>
                    <div className="user-info">
                        <div className="user-name">{user?.name}</div>
                        <div className="user-role">{user?.role}</div>
                    </div>
                </div>
                {showUserMenu && (
                    <div className="user-menu" style={{ bottom: 70, top: 'auto' }}>
                        <button onClick={onLogout}>Sign Out</button>
                    </div>
                )}
            </aside>

            {/* Main */}
            <main className="main-content">
                {/* Top Bar */}
                <div className="top-bar">
                    <form onSubmit={handleSearch} className="search-bar">
                        <input
                            type="text"
                            placeholder="Search company or director..."
                            value={searchQuery}
                            onChange={(e) => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults(null); }}
                        />
                        <button type="submit" className="search-submit">Search</button>
                    </form>
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        {status && (
                            <div className={`status-pill ${status.includes('Error') ? 'error' : status.includes('complete') ? 'success' : 'info'}`}>
                                {status}
                            </div>
                        )}
                        <button
                            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                            className="btn"
                            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                            {theme === 'dark' ? (
                                <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" /></svg> Light</>
                            ) : (
                                <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></svg> Dark</>
                            )}
                        </button>
                    </div>
                </div>

                {/* Search Results Overlay */}
                {searchResults && (
                    <div className="search-results">
                        <div className="search-results-header">
                            <span>{searchResults.length} results for "{searchQuery}"</span>
                            <button onClick={() => setSearchResults(null)}>✕</button>
                        </div>
                        {searchResults.map(r => (
                            <div key={r.id} className="search-result-item" onClick={() => {
                                setSelectedNode(r.id);
                                setView('investigation');
                                setSearchResults(null);
                            }}>
                                <span className="sr-name">{r.name}</span>
                                <span className="sr-industry">{r.industry}</span>
                                <span className="risk-badge-sm" style={{ color: getRiskColor(r.risk_score) }}>
                                    {r.risk_score?.toFixed(0)}
                                </span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Executive Dashboard */}
                {view === 'dashboard' && (
                    <div className="page-section">
                        <div className="page-header">
                            <div>
                                <h1>Executive Dashboard</h1>
                                <p>Fraud intelligence overview</p>
                            </div>
                        </div>

                        {dashStats ? (
                            <>
                                <div className="stats-grid">
                                    <div className="stat-card cyan">
                                        <div className="stat-label">Total Companies</div>
                                        <div className="stat-value">{dashStats.total_companies}</div>
                                    </div>
                                    <div className="stat-card red">
                                        <div className="stat-label">Critical Risk</div>
                                        <div className="stat-value">{dashStats.critical_risk}</div>
                                    </div>
                                    <div className="stat-card orange">
                                        <div className="stat-label">High Risk</div>
                                        <div className="stat-value">{dashStats.high_risk}</div>
                                    </div>
                                    <div className="stat-card purple">
                                        <div className="stat-label">Shell Clusters</div>
                                        <div className="stat-value">{dashStats.shell_clusters}</div>
                                    </div>
                                    <div className="stat-card blue">
                                        <div className="stat-label">Circular Paths</div>
                                        <div className="stat-value">{dashStats.circular_paths}</div>
                                    </div>
                                    <div className="stat-card cyan">
                                        <div className="stat-label">Avg Risk Score</div>
                                        <div className="stat-value">{dashStats.avg_risk_score}</div>
                                    </div>
                                </div>

                                {/* Risk Distribution */}
                                {riskDist && riskDist.length > 0 && (
                                    <div className="card" style={{ marginBottom: 16 }}>
                                        <div className="card-header"><h2>Risk Distribution</h2></div>
                                        <div className="dist-bars">
                                            {riskDist.map(d => (
                                                <div key={d.band} className="dist-bar-row">
                                                    <div className="dist-label">{d.band}</div>
                                                    <div className="dist-track">
                                                        <div className="dist-fill" style={{
                                                            width: `${Math.min((d.count / (dashStats?.total_companies || 1)) * 100, 100)}%`,
                                                            background: (() => {
                                                                const c = d.band.includes('Critical') ? 'var(--risk-critical)' :
                                                                    d.band.includes('High') ? 'var(--risk-high)' :
                                                                        d.band.includes('Medium') ? 'var(--risk-medium)' : 'var(--risk-low)';
                                                                return `linear-gradient(90deg, color-mix(in srgb, ${c} 20%, transparent), ${c})`;
                                                            })()
                                                        }} />
                                                    </div>
                                                    <div className="dist-count">{d.count}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Top Risk Table */}
                                {topRisk && topRisk.length > 0 && (
                                    <div className="card">
                                        <div className="card-header"><h2>Top 10 Highest Risk Companies</h2></div>
                                        <table className="data-table">
                                            <thead>
                                                <tr>
                                                    <th style={{ textAlign: 'right', width: '40px' }}>#</th>
                                                    <th>Company</th>
                                                    <th>Industry</th>
                                                    <th style={{ textAlign: 'right' }}>Risk Score</th>
                                                    <th>Risk Band</th>
                                                    <th style={{ textAlign: 'right' }}>GNN Prob</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {topRisk.map((c, i) => (
                                                    <tr key={c.id} onClick={() => { setSelectedNode(c.id); setView('investigation'); }}>
                                                        <td className="mono" style={{ textAlign: 'right' }}>{i + 1}</td>
                                                        <td>{c.name}</td>
                                                        <td style={{ color: 'var(--text-muted)' }}>{c.industry}</td>
                                                        <td className="mono" style={{ color: getRiskColor(c.risk_score), textAlign: 'right' }}>
                                                            {c.risk_score?.toFixed(1)}
                                                        </td>
                                                        <td><span className={`risk-badge ${c.risk_band?.toLowerCase()}`}>{c.risk_band}</span></td>
                                                        <td className="mono" style={{ textAlign: 'right' }}>{(c.gnn_prob * 100).toFixed(0)}%</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </>
                        ) : (
                            loading ? (
                                <div className="calculating-container">
                                    <div className="calculating-animation">
                                        <div className="calc-ring"></div>
                                        <div className="calc-ring"></div>
                                        <div className="calc-ring"></div>
                                        <div className="calc-icon">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
                                        </div>
                                    </div>
                                    <div>
                                        <h3 style={{ fontSize: '18px', marginBottom: '8px' }}>Running Analytics Engine</h3>
                                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Generating supply chain graph, computing risk topologies, and detecting shell loops...</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="empty-dashboard-hero">
                                    <div className="empty-hero-icon">
                                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect x="2" y="14" width="20" height="8" rx="2" ry="2" /><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" /></svg>
                                    </div>
                                    <h2 className="empty-hero-title">Enterprise Fraud Intelligence</h2>
                                    <p className="empty-hero-text">
                                        Welcome to EchelonGraph. The secure environment is initialized. Run the advanced analytics pipeline to generate structural features, run PageRank, and compute multi-layered risk metrics.
                                    </p>
                                    {user?.role === 'admin' ? (
                                        <button className="pipeline-run-btn" onClick={runPipeline}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg> Initialize Engine & Compute Risks
                                        </button>
                                    ) : (
                                        <div className="status-pill info">Contact an Administrator to initialize the pipeline</div>
                                    )}
                                </div>
                            )
                        )}
                    </div>
                )}

                {/* Investigation Workspace */}
                {view === 'investigation' && (
                    <div className="page-section">
                        <div className="page-header">
                            <div>
                                <h1>Investigation Workspace</h1>
                                <p>Interactive graph exploration • Click nodes to investigate</p>
                            </div>
                            {graphData && (
                                <div className="header-stats">
                                    <span className="header-stat">{graphData.nodes?.length || 0} nodes</span>
                                    <span className="header-stat">{graphData.edges?.length || 0} edges</span>
                                </div>
                            )}
                        </div>
                        {graphData ? (
                            <GraphView
                                graphData={graphData}
                                onNodeClick={handleNodeClick}
                                selectedNode={selectedNode}
                            />
                        ) : (
                            <div className="empty-state">
                                <div className="empty-icon">
                                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
                                </div>
                                <h3>No graph loaded</h3>
                                <p>Run the pipeline from the sidebar to generate the supply chain graph.</p>
                            </div>
                        )}
                    </div>
                )}

                {view === 'shells' && <ShellClusterView onCompanyClick={(id) => { setSelectedNode(id); setView('investigation'); }} />}
                {view === 'circular' && <CircularPathView onCompanyClick={(id) => { setSelectedNode(id); setView('investigation'); }} />}
                {view === 'heatmap' && <RiskHeatmap />}
                {view === 'invoices' && <InvoiceVerification onCompanyClick={(id) => { setSelectedNode(id); setView('investigation'); }} />}
            </main>

            {/* Company Panel */}
            {selectedNode && (
                <CompanyPanel
                    companyId={selectedNode}
                    onClose={() => setSelectedNode(null)}
                    userRole={user?.role}
                />
            )}
        </div>
    );
}
