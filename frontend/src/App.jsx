import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import LoginPage from './components/LoginPage';
import './index.css';

const Dashboard = lazy(() => import('./components/Dashboard'));

function App() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [theme, setTheme] = useState(() => localStorage.getItem('echelon_theme') || 'dark');

    useEffect(() => {
        const stored = localStorage.getItem('echelon_user');
        const token = localStorage.getItem('echelon_token');
        if (stored && token) {
            try { setUser(JSON.parse(stored)); } catch { /* ignore */ }
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('echelon_theme', theme);
    }, [theme]);

    const handleLogin = useCallback((userData) => setUser(userData), []);

    const handleLogout = useCallback(() => {
        localStorage.removeItem('echelon_token');
        localStorage.removeItem('echelon_user');
        setUser(null);
    }, []);

    if (loading) return (
        <div className="loading-overlay" style={{ minHeight: '100vh' }}>
            <div className="spinner" /><span>Loading EchelonGraph...</span>
        </div>
    );

    if (!user) return <LoginPage onLogin={handleLogin} />;

    return (
        <Suspense fallback={
            <div className="loading-overlay" style={{ minHeight: '100vh' }}>
                <div className="spinner" /><span>Loading Dashboard...</span>
            </div>
        }>
            <Dashboard user={user} onLogout={handleLogout} theme={theme} setTheme={setTheme} />
        </Suspense>
    );
}

export default App;
