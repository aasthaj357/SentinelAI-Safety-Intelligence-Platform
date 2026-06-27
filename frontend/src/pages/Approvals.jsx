import { useState, useEffect } from 'react';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';
import { ShieldCheck, CheckCircle2, XCircle, Clock } from 'lucide-react';

export default function Approvals() {
  const { activeProjectId, userId, isLoading, refreshKey } = useActiveProject();
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actioningId, setActioningId] = useState(null);

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/approvals/?project_id=${activeProjectId}&status=pending`);
      setApprovals(response.data || []);
    } catch (err) {
      console.error("Failed to fetch approvals:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading && activeProjectId) {
      fetchApprovals();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, isLoading, refreshKey]);

  const handleAction = async (requestId, action) => {
    if (!userId) return;
    try {
      setActioningId(requestId);
      await axios.post(`${API_URL}/api/approvals/${requestId}/action`, {
        action: action,
        user_id: userId
      });
      // Remove from list after approval/rejection
      setApprovals(prev => prev.filter(item => item.id !== requestId));
    } catch (err) {
      console.error(`Failed to execute approval action '${action}':`, err);
    } finally {
      setActioningId(null);
    }
  };

  return (
    <div className="p-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-8 h-8 text-indigo-500" />
            Human-In-The-Loop Approval Center
          </h1>
          <p className="text-gray-500 mt-2">
            Validate pending safety assessments and override high-risk incident predictions before final audit log locks.
          </p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          </div>
        ) : approvals.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {approvals.map((req) => (
              <div key={req.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-xs font-mono bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-1 rounded-full uppercase tracking-wider font-bold">
                      {req.request_type.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">ID: {req.id.slice(0, 8)}</span>
                  </div>
                  
                  <h3 className="font-bold text-gray-950 dark:text-white text-lg mb-2">
                    Awaiting Validation Check
                  </h3>
                  
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    {req.details.reason || 'Reasoning parameters unspecified.'}
                  </p>

                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 mb-4 border border-gray-100">
                    <div className="flex justify-between items-center text-sm mb-2">
                      <span className="text-gray-500">Risk Score Estimate</span>
                      <span className="font-bold text-red-600 text-base">{req.details.risk_score || 'N/A'}/100</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-500">Target Pipeline Job</span>
                      <span className="font-mono text-gray-700 dark:text-gray-300">{(req.target_id || '').slice(0, 8)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 border-t border-gray-100 dark:border-gray-700 pt-4">
                  <button
                    disabled={actioningId !== null}
                    onClick={() => handleAction(req.id, 'approved')}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg flex items-center justify-center gap-1.5 transition-colors text-sm"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Approve & Resume
                  </button>
                  <button
                    disabled={actioningId !== null}
                    onClick={() => handleAction(req.id, 'rejected')}
                    className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg flex items-center justify-center gap-1.5 transition-colors text-sm"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject & Halt
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-dashed">
            <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h3 className="font-semibold text-gray-700 dark:text-gray-300 text-lg">All caught up!</h3>
            <p className="text-gray-500 text-sm mt-1">No pending supervisor approvals in queue.</p>
          </div>
        )}
      </div>
    </div>
  );
}
