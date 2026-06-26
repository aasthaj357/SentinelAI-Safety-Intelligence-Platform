import { useState, useEffect } from 'react';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';
import { HelpCircle, Brain, BookOpen, Quote, AlertTriangle, CheckCircle, Activity, Shield } from 'lucide-react';

export default function Explainability() {
  const { activeProjectId, userId, isLoading } = useActiveProject();
  const [violations, setViolations] = useState([]);
  const [selectedViolation, setSelectedViolation] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [loading, setLoading] = useState(true);
  const [projectSummary, setProjectSummary] = useState(null);

  const fetchViolations = async () => {
    try {
      setLoading(true);
      const [evRes, statsRes] = await Promise.allSettled([
        axios.get(`${API_URL}/api/evidence/project/${activeProjectId}?user_id=${userId || 'guest'}`),
        axios.get(`${API_URL}/api/dashboard/stats?project_id=${activeProjectId}&user_id=${userId || 'guest'}`)
      ]);

      if (evRes.status === 'fulfilled') {
        setViolations(evRes.value.data || []);
      }
      if (statsRes.status === 'fulfilled' && statsRes.value.data) {
        setProjectSummary(statsRes.value.data);
      }
    } catch (err) {
      console.error("Failed to fetch violations for explainability:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading && activeProjectId) {
      fetchViolations();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, isLoading]);

  const explainViolation = async (violation) => {
    try {
      setSelectedViolation(violation);
      setLoadingExplanation(true);
      setExplanation(null);

      // Call the new dynamic explain endpoint
      const res = await axios.get(`${API_URL}/api/audit/explain/${violation.id}`);
      const data = res.data;

      setExplanation(data);
    } catch (err) {
      console.error("Failed to compile agent explanation:", err);
      // Fallback: build explanation from the violation record itself
      setExplanation({
        violation_type: violation.detection_label || 'Unknown',
        ppe_type: (violation.detection_label || '').replace('no-', '').replace('No ', ''),
        worker_label: violation.metadata?.worker_id || 'Unknown Worker',
        timestamp: violation.timestamp,
        frame_num: violation.frame_num,
        confidence: violation.confidence,
        sop_section: violation.sop_section || 'Standard PPE Requirements',
        sop_excerpt: violation.sop_excerpt || 'All workers must wear required PPE.',
        decision_context: violation.risk_reason || `${violation.detection_label} detected as a violation at frame #${violation.frame_num}.`,
        ai_summary: `**Violation**: ${violation.detection_label} detected on worker at ${violation.timestamp}s.\n**Evidence**: Frame #${violation.frame_num} with ${(violation.confidence * 100).toFixed(0)}% confidence.`,
        citations: [
          `SOP Reference: ${violation.sop_section || 'Standard PPE'}`,
          `Evidence Captured: Frame #${violation.frame_num} at ${violation.timestamp}s`,
          `Detection Confidence: ${(violation.confidence * 100).toFixed(0)}%`,
        ],
        screenshot_url: violation.annotated_screenshot_url || violation.screenshot_url,
        training_recommendations: [],
        risk_score: null,
        risk_level: null,
      });
    } finally {
      setLoadingExplanation(false);
    }
  };

  const getSeverityColor = (violationType) => {
    const t = (violationType || '').toLowerCase();
    if (t.includes('helmet') || t.includes('hardhat')) return 'text-red-600 bg-red-50 border-red-200';
    if (t.includes('glove')) return 'text-orange-600 bg-orange-50 border-orange-200';
    if (t.includes('goggle') || t.includes('eye')) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    if (t.includes('mask') || t.includes('respirator')) return 'text-purple-600 bg-purple-50 border-purple-200';
    if (t.includes('vest')) return 'text-blue-600 bg-blue-50 border-blue-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const getRiskBadgeColor = (level) => {
    switch ((level || '').toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 border border-red-300';
      case 'high': return 'bg-orange-100 text-orange-800 border border-orange-300';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border border-yellow-300';
      default: return 'bg-green-100 text-green-800 border border-green-300';
    }
  };

  return (
    <div className="p-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Brain className="w-8 h-8 text-indigo-500" />
            Agent Explainability Dashboard
          </h1>
          <p className="text-gray-500 mt-2">
            Click any registered safety violation to trigger the Explainability Agent and review full decision traces, citations, and AI reasoning.
          </p>
        </div>

        {/* Project-level summary bar */}
        {projectSummary && (
          <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center">
              <p className="text-2xl font-bold text-red-600">{projectSummary.total_violations ?? '—'}</p>
              <p className="text-xs text-gray-500 mt-1">Total Violations</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center">
              <p className="text-2xl font-bold text-orange-600">{projectSummary.incident_risk_score != null ? `${projectSummary.incident_risk_score}/100` : '—'}</p>
              <p className="text-xs text-gray-500 mt-1">Risk Score</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center">
              <p className="text-2xl font-bold text-blue-600">{projectSummary.evidence_records ?? '—'}</p>
              <p className="text-xs text-gray-500 mt-1">Evidence Records</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center">
              <p className="text-2xl font-bold text-green-600">{violations.length}</p>
              <p className="text-xs text-gray-500 mt-1">Loaded Exceptions</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Violations List */}
          <div className="md:col-span-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-bold text-gray-950 dark:text-white text-base mb-4 border-b pb-2">
              Registered Exceptions
              {violations.length > 0 && (
                <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-semibold">
                  {violations.length}
                </span>
              )}
            </h3>
            {loading ? (
              <div className="text-center py-6">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto"></div>
              </div>
            ) : violations.length > 0 ? (
              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {violations.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => explainViolation(v)}
                    className={`w-full text-left p-3 rounded-lg border text-sm transition-all flex items-center justify-between gap-2
                      ${selectedViolation?.id === v.id
                        ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 text-indigo-700 dark:text-indigo-400 font-semibold'
                        : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50 dark:hover:bg-gray-750'}`}
                  >
                    <div className="flex-1 min-w-0">
                      <span className="block capitalize font-medium truncate">
                        {(v.detection_label || 'Unknown').replace(/-/g, ' ').replace(/no /i, 'Missing ')}
                      </span>
                      <span className="text-xs text-gray-400 font-mono block mt-0.5">
                        Frame #{v.frame_num} | {parseFloat(v.timestamp || 0).toFixed(2)}s | {(v.confidence * 100).toFixed(0)}%
                      </span>
                      {v.metadata?.worker_id && (
                        <span className="text-xs text-indigo-500">{v.metadata.worker_id}</span>
                      )}
                    </div>
                    <HelpCircle className="w-4 h-4 text-gray-400 shrink-0" />
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Shield className="w-10 h-10 text-green-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">No violations recorded.</p>
                <p className="text-xs text-gray-400 mt-1">Load demo data or analyze a video.</p>
              </div>
            )}
          </div>

          {/* Explanation Panel */}
          <div className="md:col-span-2">
            {selectedViolation ? (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                {loadingExplanation ? (
                  <div className="text-center py-16">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mx-auto mb-4"></div>
                    <p className="text-sm text-gray-500">Compiling agent reasoning from analysis data...</p>
                  </div>
                ) : explanation ? (
                  <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-start justify-between border-b pb-4">
                      <div>
                        <h3 className="font-bold text-gray-950 dark:text-white text-lg flex items-center gap-2">
                          <BookOpen className="w-5 h-5 text-indigo-500" />
                          {(explanation.violation_type || 'Violation').replace(/no-|no_/gi, 'Missing ').replace(/-/g, ' ')}
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                          {explanation.worker_label} · Frame #{explanation.frame_num} · {parseFloat(explanation.timestamp || 0).toFixed(2)}s
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        {explanation.risk_level && (
                          <span className={`px-2 py-1 text-xs font-bold rounded ${getRiskBadgeColor(explanation.risk_level)}`}>
                            {explanation.risk_level} Risk
                          </span>
                        )}
                        {explanation.confidence != null && (
                          <span className="text-xs text-gray-400">{(explanation.confidence * 100).toFixed(0)}% confidence</span>
                        )}
                      </div>
                    </div>

                    {/* AI Summary — dynamic from analysis */}
                    <div>
                      <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2 flex items-center gap-1">
                        <Activity className="w-3.5 h-3.5" /> AI Analysis Summary
                      </span>
                      <div className="bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-800 rounded-lg p-4 text-sm text-gray-700 dark:text-gray-300 space-y-2">
                        {(explanation.ai_summary || '').split('\n\n').map((para, i) => (
                          <p key={i}>{para.replace(/\*\*/g, '')}</p>
                        ))}
                      </div>
                    </div>

                    {/* Decision Context — from compliance auditor trace */}
                    <div>
                      <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2 flex items-center gap-1">
                        <Brain className="w-3.5 h-3.5" /> Decision Context (Compliance Auditor Trace)
                      </span>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-600 dark:text-gray-300 border border-gray-100 font-medium leading-relaxed">
                        {explanation.decision_context}
                      </div>
                    </div>

                    {/* Grounded Citations */}
                    <div>
                      <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2 flex items-center gap-1">
                        <Quote className="w-3.5 h-3.5" /> Grounded Citations
                      </span>
                      <ul className="space-y-1.5">
                        {(explanation.citations || []).map((cit, idx) => (
                          <li key={idx} className="text-xs font-mono text-gray-500 dark:text-gray-400 flex items-start gap-2">
                            <CheckCircle className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5" />
                            {cit}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Training Recommendations */}
                    {explanation.training_recommendations && explanation.training_recommendations.length > 0 && (
                      <div>
                        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" /> Triggered Training Recommendations
                        </span>
                        <div className="space-y-2">
                          {explanation.training_recommendations.map((tr, i) => (
                            <div key={i} className={`p-3 rounded-lg border-l-4 text-sm ${tr.priority === 'Critical' ? 'border-red-500 bg-red-50 dark:bg-red-900/10' : tr.priority === 'High' ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/10' : 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/10'}`}>
                              <p className="font-semibold text-gray-900 dark:text-gray-100">{tr.title}</p>
                              <p className="text-gray-600 dark:text-gray-400 text-xs mt-1">{tr.action}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Evidence Screenshot */}
                    {explanation.screenshot_url && (
                      <div>
                        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2">Evidence Capture</span>
                        <img
                          src={explanation.screenshot_url}
                          alt="Annotated evidence capture"
                          className="max-h-56 border rounded-lg shadow-inner object-contain"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">Failed to compile safety agent explanation. Please try again.</p>
                )}
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm text-center py-16">
                <Brain className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="font-semibold text-gray-700 dark:text-gray-300 text-lg">Select a violation to explain</h3>
                <p className="text-gray-500 text-sm mt-2 max-w-sm mx-auto">
                  Choose a safety exception from the left panel to view full AI reasoning, decision traces, SOP citations, risk impact, and training recommendations — all derived from actual analysis results.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
