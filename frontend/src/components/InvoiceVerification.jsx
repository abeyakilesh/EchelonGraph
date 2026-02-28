import { useState, useEffect } from 'react';
import { getAllInvoices, verifyInvoice, generateSampleInvoices } from '../api';

export default function InvoiceVerification({ onCompanyClick }) {
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedInvoice, setSelectedInvoice] = useState(null);
    const [isFundingBlocked, setIsFundingBlocked] = useState(false);

    useEffect(() => {
        loadInvoices();
    }, []);

    const loadInvoices = async () => {
        setLoading(true);
        try {
            const res = await getAllInvoices();
            setInvoices(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleVerify = async (id) => {
        try {
            const res = await verifyInvoice(id);
            setSelectedInvoice(res.data);
            setIsFundingBlocked(false); // Reset block state when opening new invoice
        } catch (e) {
            console.error(e);
        }
    };

    const handleGenerateSamples = async () => {
        setLoading(true);
        try {
            await generateSampleInvoices();
            await loadInvoices();
        } catch (e) {
            console.error("Failed to generate samples", e);
            alert("Failed to generate samples. Ensure the main pipeline has been run first.");
            setLoading(false);
        }
    };

    // Calculate sum of phantom invoices
    const phantomCount = invoices.filter(i => i.is_phantom).length;
    const totalExposure = invoices.filter(i => i.is_phantom).reduce((acc, curr) => acc + curr.amount, 0);

    return (
        <div className="page-section">
            <div className="page-header">
                <div>
                    <h1>Invoice Verification</h1>
                    <p>Multi-Tier Supply Chain Fraud Detection • Real-time PO/GRN matching & Fingerprinting</p>
                </div>
                <div className="header-stats" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <span className="header-stat">{invoices.length} invoices tracked</span>
                    <button className="btn" style={{ padding: '6px 12px', fontSize: '12px', background: 'var(--bg-card)', border: '1px solid var(--border)' }} onClick={handleGenerateSamples}>
                        Generate Samples
                    </button>
                </div>
            </div>

            <div className="stats-grid" style={{ marginBottom: 24 }}>
                <div className="stat-card cyan">
                    <div className="stat-label">Total Invoices</div>
                    <div className="stat-value">{invoices.length}</div>
                </div>
                <div className="stat-card red">
                    <div className="stat-label">Phantom / High-Risk</div>
                    <div className="stat-value">{phantomCount}</div>
                </div>
                <div className="stat-card orange">
                    <div className="stat-label">Total SCF Exposure</div>
                    <div className="stat-value">₹{(totalExposure / 10000000).toFixed(2)}Cr</div>
                </div>
            </div>

            {loading ? (
                <div className="loading-overlay"><div className="spinner" /><span>Fetching supply chain documents...</span></div>
            ) : invoices.length === 0 ? (
                <div className="empty-dashboard-hero">
                    <div className="empty-hero-icon">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" /></svg>
                    </div>
                    <h3 className="empty-hero-title">No Invoices Tracked</h3>
                    <p className="empty-hero-text" style={{ marginBottom: '24px' }}>Ingest invoices to begin checking for duplicate fingerprints and PO/GRN matches.</p>
                    <button className="pipeline-run-btn" onClick={handleGenerateSamples}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /><path d="M18 5h6" /><path d="M21 2v6" /></svg>
                        Generate Sample Invoices
                    </button>
                </div>
            ) : (
                <div className="card">
                    <div className="card-header">
                        <h2>Recent Invoices</h2>
                    </div>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Invoice ID</th>
                                <th>Date</th>
                                <th>Supplier</th>
                                <th>Buyer</th>
                                <th style={{ textAlign: 'right' }}>Amount</th>
                                <th style={{ textAlign: 'center' }}>PO Match</th>
                                <th style={{ textAlign: 'center' }}>GRN Match</th>
                                <th style={{ textAlign: 'center' }}>Fingerprint</th>
                                <th>Status</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {invoices.map(inv => (
                                <tr key={inv.id} className={inv.is_phantom ? 'row-critical' : ''}>
                                    <td className="mono" style={{ fontWeight: 600 }}>{inv.id}</td>
                                    <td style={{ color: 'var(--text-muted)' }}>{inv.date}</td>
                                    <td>{inv.supplier}</td>
                                    <td>{inv.buyer}</td>
                                    <td className="mono" style={{ textAlign: 'right' }}>₹{inv.amount.toLocaleString()}</td>

                                    <td style={{ textAlign: 'center' }}>
                                        {inv.has_po ?
                                            <span style={{ color: 'var(--risk-low)' }}>✓</span> :
                                            <span style={{ color: 'var(--risk-critical)' }}>✗</span>
                                        }
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {inv.has_grn ?
                                            <span style={{ color: 'var(--risk-low)' }}>✓</span> :
                                            <span style={{ color: 'var(--risk-critical)' }}>✗</span>
                                        }
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {inv.duplicate_count === 0 ?
                                            <span className="risk-badge low" style={{ padding: '2px 6px', fontSize: '10px' }}>Unique</span> :
                                            <span className="risk-badge critical" style={{ padding: '2px 6px', fontSize: '10px' }}>{inv.duplicate_count} Dupes</span>
                                        }
                                    </td>
                                    <td>
                                        {inv.is_phantom ?
                                            <span className="risk-badge critical">Phantom Risk</span> :
                                            <span className="risk-badge low">Cleared</span>
                                        }
                                    </td>
                                    <td>
                                        <button className="btn btn-primary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => handleVerify(inv.id)}>Verify</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Verification Modal */}
            {selectedInvoice && (
                <div className="modal-overlay" onClick={() => setSelectedInvoice(null)}>
                    <div className="modal-content" style={{ maxWidth: '600px' }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <h2>Invoice Analysis: {selectedInvoice.invoice_id}</h2>
                                <p>Hash: {selectedInvoice.fingerprint}</p>
                            </div>
                            <button className="modal-close" onClick={() => setSelectedInvoice(null)}>✕</button>
                        </div>
                        <div className="modal-body">

                            <div className="inv-flow-viz" style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px',
                                padding: '24px', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', marginBottom: '24px'
                            }}>
                                <div className="path-node">{selectedInvoice.supplier}</div>
                                <div className="path-arrow">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
                                </div>
                                <div className="path-node origin">{selectedInvoice.invoice_id}</div>
                                <div className="path-arrow">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
                                </div>
                                <div className="path-node">{selectedInvoice.buyer}</div>
                            </div>

                            <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                                <div className="card" style={{ padding: '16px' }}>
                                    <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Document Match</h3>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span>Purchase Order (PO):</span>
                                            <span style={{ color: selectedInvoice.has_po ? 'var(--risk-low)' : 'var(--risk-critical)' }}>{selectedInvoice.has_po ? "Matched" : "Missing"}</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span>Goods Receipt (GRN):</span>
                                            <span style={{ color: selectedInvoice.has_grn ? 'var(--risk-low)' : 'var(--risk-critical)' }}>{selectedInvoice.has_grn ? "Matched" : "Missing"}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="card" style={{ padding: '16px' }}>
                                    <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Network Multi-Pledging</h3>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span>Duplicate Fingerprints:</span>
                                            <span className="mono" style={{ color: selectedInvoice.duplicate_count > 0 ? 'var(--risk-critical)' : 'var(--risk-low)' }}>{selectedInvoice.duplicate_count}</span>
                                        </div>
                                        {selectedInvoice.duplicate_count > 0 && (
                                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'var(--bg-app)', padding: '8px', borderRadius: '4px' }}>
                                                Duplicate Refs: {selectedInvoice.duplicate_refs.join(", ")}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div style={{ marginTop: '24px', padding: '16px', borderRadius: 'var(--radius-md)', background: selectedInvoice.is_phantom ? 'color-mix(in srgb, var(--risk-critical) 10%, transparent)' : 'color-mix(in srgb, var(--risk-low) 10%, transparent)', border: `1px solid ${selectedInvoice.is_phantom ? 'var(--risk-critical)' : 'var(--risk-low)'}` }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div>
                                        <div style={{ fontWeight: 600, color: selectedInvoice.is_phantom ? 'var(--risk-critical)' : 'var(--risk-low)' }}>
                                            {selectedInvoice.is_phantom ? "PHANTOM INVOICE DETECTED" : "INVOICE VERIFIED"}
                                        </div>
                                        <div style={{ fontSize: '12px', marginTop: '4px', color: 'var(--text-secondary)' }}>
                                            Risk Score: {selectedInvoice.phantom_risk_score}/100
                                        </div>
                                    </div>
                                    {selectedInvoice.is_phantom && (
                                        <button
                                            className="btn btn-primary"
                                            style={{
                                                background: isFundingBlocked ? 'var(--bg-card)' : 'var(--risk-critical)',
                                                color: isFundingBlocked ? 'var(--text-muted)' : '#fff',
                                                border: isFundingBlocked ? '1px solid var(--border)' : 'none',
                                                cursor: isFundingBlocked ? 'not-allowed' : 'pointer'
                                            }}
                                            onClick={() => setIsFundingBlocked(true)}
                                            disabled={isFundingBlocked}
                                        >
                                            {isFundingBlocked ? "Funding Blocked ✓" : "Block Funding"}
                                        </button>
                                    )}
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
