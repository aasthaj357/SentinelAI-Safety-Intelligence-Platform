import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import { ActiveProjectProvider } from './context/ActiveProjectContext';
import Dashboard from './pages/Dashboard';
import Uploads from './pages/Uploads';
import AnalysisViewer from './pages/AnalysisViewer';
import SafetyCopilot from './pages/SafetyCopilot';
import EvidenceGallery from './pages/EvidenceGallery';
import AgentActivityViewer from './pages/AgentActivityViewer';
import Approvals from './pages/Approvals';
import AuditLogs from './pages/AuditLogs';
import Explainability from './pages/Explainability';
import Auth from './pages/Auth';
import ProtectedRoute from './components/ProtectedRoute';
import { getDemoSession } from './lib/auth';

function resolveSession(authSession) {
  if (authSession) return authSession;
  if (localStorage.getItem('demoSession')) return getDemoSession();
  return null;
}

function Sidebar({ session, onLogout }) {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: '📊' },
    { to: '/uploads', label: 'Upload Video', icon: '📤' },
    { to: '/evidence', label: 'Evidence Gallery', icon: '🔍' },
    { to: '/copilot', label: 'Safety Copilot', icon: '🤖' },
    { to: '/agents', label: 'Agent Activity', icon: '⚡' },
    { to: '/approvals', label: 'Approvals', icon: '🛡️' },
    { to: '/explain', label: 'Explainability', icon: '🧠' },
    { to: '/audit', label: 'Audit Logs', icon: '📜' },
  ];

  const isDemo = !!localStorage.getItem('demoSession');
  const userEmail = session?.user?.email || (isDemo ? 'demo@hackathon.com' : '');

  return (
    <div className="w-full md:w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col min-h-screen">
      {/* Brand */}
      <div className="p-5 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-800 dark:text-white leading-tight">Safety Platform</h2>
            <p className="text-xs text-gray-400">AI Safety Analysis</p>
          </div>
        </div>
      </div>

      {/* User info */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-xs font-bold text-indigo-700 dark:text-indigo-300 uppercase">
            {userEmail ? userEmail[0] : '?'}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{userEmail}</p>
            {isDemo && <span className="text-xs text-orange-500 font-medium">Demo Mode</span>}
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 py-2 px-3 rounded-lg text-sm font-medium transition ${
                isActive
                  ? 'bg-indigo-50 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`
            }
          >
            <span>{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 py-2 px-3 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition"
        >
          <span>🚪</span>
          <span>Sign out</span>
        </button>
      </div>
    </div>
  );
}

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(resolveSession(s));
      setLoading(false);
    });

    // Real-time auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(resolveSession(s));
    });

    // Demo session storage events
    const onStorage = () => {
      if (localStorage.getItem('demoSession')) {
        setSession(getDemoSession());
      } else {
        supabase.auth.getSession().then(({ data: { session: s } }) => {
          setSession(s || null);
        });
      }
    };
    window.addEventListener('storage', onStorage);

    return () => {
      subscription.unsubscribe();
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    localStorage.removeItem('demoSession');
    localStorage.removeItem('activeProjectId');
    localStorage.removeItem('userId');
    await supabase.auth.signOut();
    setSession(null);
    window.location.href = '/auth';
  };

  return (
    <ActiveProjectProvider>
      <Router>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col md:flex-row">
          {session && <Sidebar session={session} onLogout={handleLogout} />}

          <div className="flex-1 overflow-auto">
            <Routes>
              <Route path="/auth" element={!session ? <Auth /> : <Navigate to="/" replace />} />
              <Route path="/" element={<ProtectedRoute session={session}><Dashboard /></ProtectedRoute>} />
              <Route path="/uploads" element={<ProtectedRoute session={session}><Uploads /></ProtectedRoute>} />
              <Route path="/evidence" element={<ProtectedRoute session={session}><EvidenceGallery /></ProtectedRoute>} />
              <Route path="/analysis/:videoId" element={<ProtectedRoute session={session}><AnalysisViewer /></ProtectedRoute>} />
              <Route path="/copilot" element={<ProtectedRoute session={session}><SafetyCopilot /></ProtectedRoute>} />
              <Route path="/agents" element={<ProtectedRoute session={session}><AgentActivityViewer /></ProtectedRoute>} />
              <Route path="/approvals" element={<ProtectedRoute session={session}><Approvals /></ProtectedRoute>} />
              <Route path="/explain" element={<ProtectedRoute session={session}><Explainability /></ProtectedRoute>} />
              <Route path="/audit" element={<ProtectedRoute session={session}><AuditLogs /></ProtectedRoute>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </div>
      </Router>
    </ActiveProjectProvider>
  );
}

export default App;
