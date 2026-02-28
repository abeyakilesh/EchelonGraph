import { useState } from 'react';
import { login } from '../api';
import ParticleNetwork from './ParticleNetwork';

export default function LoginPage({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await login(username, password);
            localStorage.setItem('echelon_token', res.data.token);
            localStorage.setItem('echelon_user', JSON.stringify(res.data.user));
            onLogin(res.data.user);
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        }
        setLoading(false);
    };

    const quickLogin = (u, p) => {
        setUsername(u);
        setPassword(p);
    };

    return (
        <div className="login-page">
            <ParticleNetwork />
            <div className="login-card">
                <div className="login-header">
                    <div className="login-logo">E</div>
                    <h1>EchelonGraph</h1>
                    <p>Supply Chain Fraud Intelligence</p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label>Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Enter username"
                            autoFocus
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter password"
                            required
                        />
                    </div>

                    {error && <div className="login-error">{error}</div>}

                    <button type="submit" className="btn btn-primary login-btn" disabled={loading}>
                        {loading ? 'Authenticating...' : 'Sign In'}
                    </button>
                </form>

                <div className="login-demo">
                    <span className="demo-label">Quick Access</span>
                    <div className="demo-accounts">
                        {[
                            { u: 'admin', p: 'echelon123', role: 'Admin' },
                            { u: 'investigator', p: 'investigate123', role: 'Investigator' },
                            { u: 'auditor', p: 'audit123', role: 'Auditor' },
                            { u: 'viewer', p: 'view123', role: 'Viewer' },
                        ].map((a) => (
                            <button key={a.u} className="demo-btn" onClick={() => quickLogin(a.u, a.p)}>
                                {a.role}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="login-footer">
                    <span>v2.0.0</span>
                    <span>Enterprise License</span>
                </div>
            </div>
        </div>
    );
}
