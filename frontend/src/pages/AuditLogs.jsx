import { useState, useEffect } from 'react';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';
import { Shield, List, Scroll, ShieldAlert, Cpu } from 'lucide-react';

export default function AuditLogs() {
  const { activeProjectId, userId, isLoading, refreshKey } = useActiveProject();
  const [logs, setLogs] = useState([]);
  const [traces, setTraces] = useState([]);
  const [activeTab, setActiveTab] = useState('audit'); // 'audit' or 'traces'
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      if (activeTab === 'audit') {
        const url = userId 
          ? `${API_URL}/api/audit/logs?user_id=${userId}`
          : `${API_URL}/api/audit/logs`;
        const response = await axios.get(url);
        setLogs(response.data || []);
      } else {
        const response = await axios.get(`${API_URL}/api/audit/traces?project_id=${activeProjectId}`);
        setTraces(response.data || []);
      }
    } catch (err) {
      console.error("Failed to fetch audit data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading && activeProjectId) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, isLoading, activeTab, refreshKey]);

  return (
    <div className="p-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Shield className="w-8 h-8 text-indigo-500" />
            Security & Governance Audit Trail
          </h1>
          <p className="text-gray-500 mt-2">
            Immutable log record tracing system actions, user overrides, and granular AI agent reasoning steps.
          </p>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
          <button
            onClick={() => setActiveTab('audit')}
            className={`py-2 px-4 font-medium text-sm border-b-2 transition-colors flex items-center gap-1.5
              ${activeTab === 'audit'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            <ShieldAlert className="w-4 h-4" />
            Security Logs
          </button>
          <button
            onClick={() => setActiveTab('traces')}
            className={`py-2 px-4 font-medium text-sm border-b-2 transition-colors flex items-center gap-1.5
              ${activeTab === 'traces'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            <Cpu className="w-4 h-4" />
            Agent Decision Traces
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          </div>
        ) : activeTab === 'audit' ? (
          logs.length > 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">Timestamp</th>
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">User ID</th>
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">Action</th>
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-150">
                  {logs.map((log) => (
                    <tr key={log.id} className="text-sm">
                      <td className="p-4 text-gray-500 font-mono text-xs">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="p-4 text-gray-700 dark:text-gray-300 font-mono text-xs">
                        {(log.user_id || 'system').slice(0, 8)}
                      </td>
                      <td className="p-4">
                        <span className="font-semibold text-indigo-600">{log.action}</span>
                      </td>
                      <td className="p-4 text-gray-500 dark:text-gray-400 font-mono text-xs">
                        {JSON.stringify(log.details)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-dashed">
              <List className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="font-semibold text-gray-700 dark:text-gray-300 text-lg">No audit records found</h3>
            </div>
          )
        ) : (
          traces.length > 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">Agent</th>
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">Milestone</th>
                    <th className="p-4 font-semibold text-xs text-gray-400 uppercase tracking-wider">Reasoning Trace</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-150">
                  {traces.map((trace) => (
                    <tr key={trace.id} className="text-sm">
                      <td className="p-4">
                        <span className="bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-400 text-xs font-bold px-2.5 py-1 rounded">
                          {trace.agent_id}
                        </span>
                      </td>
                      <td className="p-4 text-gray-700 dark:text-gray-300 font-semibold">{trace.step}</td>
                      <td className="p-4 text-gray-500 dark:text-gray-400">
                        {trace.reasoning}
                        <span className="block text-xs font-mono text-gray-400 mt-1">
                          Context: {JSON.stringify(trace.context)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-dashed">
              <Scroll className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="font-semibold text-gray-700 dark:text-gray-300 text-lg">No agent traces recorded</h3>
            </div>
          )
        )}
      </div>
    </div>
  );
}
