import { useState, useEffect, useRef } from 'react';
import { getAuthUser } from '../lib/auth';
import { getOrCreateProject } from '../lib/project';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';
import { loadDemoData, resetDemoData } from '../lib/demoData';

const EMPTY_STATS = {
  violations: 0,
  compliance: null,
  sopCompliance: null,
  riskScore: null,
  overallSafety: null,
  trainingReadiness: null,
};

export default function Dashboard() {
  const { activeProjectId, userId, setProject, setUser, isLoading, refreshKey } = useActiveProject();
  const [stats, setStats] = useState(EMPTY_STATS);
  const [hasData, setHasData] = useState(false);
  const [trainings, setTrainings] = useState([]);
  const [risks, setRisks] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [recentLogs, setRecentLogs] = useState([]);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [violations, setViolations] = useState([]);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState(null);
  const dashboardRef = useRef(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    // Run once on mount to initialize user/project if not already set
    if (!activeProjectId || !userId) {
      initializeAndFetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Reset fetchedRef when activeProjectId or refreshKey changes so it re-fetches
    fetchedRef.current = false;
  }, [activeProjectId, refreshKey]);

  useEffect(() => {
    // Run when context provides activeProjectId + userId (e.g. after login or context hydration)
    // but skip if initializeAndFetch already triggered a fetch (fetchedRef guards against double-fetch)
    if (!isLoading && activeProjectId && userId && !fetchedRef.current) {
      fetchedRef.current = true;
      fetchDashboardData(activeProjectId, userId);
    }
  }, [activeProjectId, userId, isLoading, refreshKey]);

  const initializeAndFetch = async () => {
    try {
      const { data: { user } } = await getAuthUser();
      if (!user) return;

      // Only call setUser if it changed — prevents triggering the context useEffect above
      let projectId = activeProjectId;
      if (!projectId) {
        try {
          projectId = await getOrCreateProject();
        } catch {
          return;
        }
      }

      // Mark as fetched BEFORE calling setUser/setProject so the second useEffect doesn't double-fire
      fetchedRef.current = true;
      setUser(user.id);
      if (!activeProjectId) setProject(projectId);

      await fetchDashboardData(projectId, user.id);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDashboardData = async (projectId, uid) => {
    if (!projectId || !uid) return;

    try {
      const risksRes = await axios.get(`${API_URL}/api/risk?project_id=${projectId}&user_id=${uid}`);
      const risksData = risksRes.data || [];

      const violationsRes = await axios.get(`${API_URL}/api/violations?project_id=${projectId}&user_id=${uid}`);
      const viols = violationsRes.data || [];

      const trnsRes = await axios.get(`${API_URL}/api/trainings?project_id=${projectId}&user_id=${uid}`);
      const trns = trnsRes.data || [];

      const predsRes = await axios.get(`${API_URL}/api/predictions?project_id=${projectId}&user_id=${uid}`);
      const preds = predsRes.data || [];

      const logsRes = await axios.get(`${API_URL}/api/logs?project_id=${projectId}&user_id=${uid}`);
      const logs = logsRes.data || [];



      let analyticsResult = null;
      let uploadedVideos = [];
      try {
        const analyticsRes = await axios.get(`${API_URL}/api/dashboard/analytics?project_id=${projectId}&user_id=${uid}`);
        if (analyticsRes.data) {
          analyticsResult = analyticsRes.data;
          // Also fetch stats for timeline + worker_summary
          try {
            const statsRes = await axios.get(`${API_URL}/api/dashboard/stats?project_id=${projectId}&user_id=${uid}`);
            if (statsRes.data) {
              analyticsResult.timeline = statsRes.data.timeline || [];
              analyticsResult.worker_summary = statsRes.data.worker_summary || {};
              uploadedVideos = statsRes.data.uploaded_videos || [];
            }
          } catch {
            /* ignore */
          }
          setAnalyticsData(analyticsResult);
        }
      } catch (err) {
        console.error("Failed to fetch analytics", err);
      }

      const isDemoVideo = (v) => {
        if (!v) return false;
        const title = (v.title || '').toLowerCase();
        const fileUrl = (v.file_url || '').toLowerCase();
        return (
          title.includes('sector a') ||
          title.includes('sector b') ||
          title.includes('sector c') ||
          fileUrl.includes('example.com') ||
          fileUrl.startsWith('http')
        );
      };

      const userVideos = uploadedVideos.filter(v => !isDemoVideo(v));
      const hasUserVideos = userVideos.length > 0;
      
      let targetVideoIds = [];
      let isDemoOnly = !hasUserVideos;

      if (hasUserVideos) {
        targetVideoIds = userVideos.map(v => v.id);
      } else {
        targetVideoIds = uploadedVideos.map(v => v.id);
      }

      // Filter violations, risks, and evidence to target videos only
      let filteredViols = viols;
      if (targetVideoIds.length > 0) {
        filteredViols = viols.filter(v => targetVideoIds.includes(v.video_id));
      }
      
      let filteredRisks = risksData;
      if (targetVideoIds.length > 0) {
        filteredRisks = risksData.filter(r => targetVideoIds.includes(r.video_id) || r.video_id == null);
      }



      // If we only have demo videos, apply the 7-day filter to avoid subtraction-overflow to 0
      if (isDemoOnly) {
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        
        filteredViols = filteredViols.filter(v => new Date(v.created_at) >= sevenDaysAgo);
        filteredRisks = filteredRisks.filter(r => new Date(r.created_at) >= sevenDaysAgo);

      }

      const dataExists =
        (filteredRisks?.length || 0) > 0 ||
        filteredViols.length > 0 ||
        (trns?.length || 0) > 0 ||
        (preds?.length || 0) > 0;

      setHasData(dataExists);
      if (risksData) setRisks(risksData);
      if (trns) setTrainings(trns);
      if (viols) setViolations(viols);
      if (preds) setPredictions(preds);
      if (logs) setRecentLogs(logs);

      if (!dataExists) {
        setStats(EMPTY_STATS);
        return;
      }

      const maxRisk = filteredRisks?.length ? Math.max(...filteredRisks.map((r) => Number(r.score))) : 0;


      const totalViolations = filteredViols.length;
      
      // Calculate unique categories violated
      const violatedCategories = new Set();
      const violatedPPE = new Set();
      filteredViols.forEach(v => {
        const t = (v.violation_type || '').toLowerCase();
        if (t.includes('helmet') || t.includes('hardhat') || t.includes('hard-hat')) {
          violatedCategories.add('helmet');
          violatedPPE.add('helmet');
        } else if (t.includes('glove')) {
          violatedCategories.add('gloves');
          violatedPPE.add('gloves');
        } else if (t.includes('goggle') || t.includes('eye')) {
          violatedCategories.add('goggles');
          violatedPPE.add('goggles');
        } else if (t.includes('vest') || t.includes('vis')) {
          violatedCategories.add('vest');
          violatedPPE.add('vest');
        } else if (t.includes('shoes') || t.includes('boots') || t.includes('foot')) {
          violatedCategories.add('shoes');
          violatedPPE.add('shoes');
        } else if (t.includes('mask') || t.includes('respirator')) {
          violatedCategories.add('mask');
          violatedPPE.add('mask');
        } else {
          violatedCategories.add('other');
        }
      });

      let ppeCompliance;
      if (totalViolations === 0) {
        ppeCompliance = null; // No data yet
      } else {
        ppeCompliance = Math.max(0, 100 - violatedPPE.size * 15);
      }

      const ppeFromAnalytics = analyticsResult?.ppe_trend?.slice(-1)?.[0]?.ppe_compliance_pct;
      const calcPPE = ppeFromAnalytics != null ? ppeFromAnalytics : ppeCompliance;

      const calcSOP = totalViolations === 0 ? null : Math.max(0, 100 - violatedCategories.size * 10);
      const calcOverall = (filteredRisks?.length || totalViolations > 0)
        ? Math.max(0, 100 - violatedCategories.size * 8 - maxRisk * 0.4)
        : null;
      const calcTraining = (trns?.length || 0) > 0
        ? Math.max(0, 100 - (trns?.length || 0) * 10)
        : null;

      setStats({
        violations: filteredViols.length,
        riskScore: maxRisk || null,
        overallSafety: calcOverall != null ? Number(calcOverall).toFixed(1) : null,
        compliance: calcPPE != null ? Number(calcPPE).toFixed(1) : null,
        sopCompliance: calcSOP != null ? calcSOP.toFixed(1) : null,
        trainingReadiness: calcTraining != null ? calcTraining.toFixed(1) : null,
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleExportPDF = async () => {
    if (!activeProjectId || !userId || exportLoading) return;
    
    setExportLoading(true);
    setExportError(null);
    
    try {
      const response = await axios.post(`${API_URL}/api/reports/generate`, {
        project_id: activeProjectId,
        user_id: userId
      });
      
      if (response.data.status === 'success') {
        const reportHtml = response.data.report_html;
        const pdfB64 = response.data.report_pdf_b64;
        const filename = `Safety-Report-${activeProjectId.substring(0,8)}.pdf`;

        // If backend provided PDF bytes, download directly
        if (pdfB64) {
          try {
            const byteCharacters = atob(pdfB64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            setExportLoading(false);
            return;
          } catch (blobErr) {
            console.warn('Direct PDF download failed, falling back to html2pdf:', blobErr);
          }
        }

        // Fallback: use html2pdf.js to convert HTML to PDF in-browser
        try {
          const html2pdf = (await import('html2pdf.js')).default;
          const element = document.createElement('div');
          element.innerHTML = reportHtml;
          
          await html2pdf()
            .set({
              margin: 0.5,
              filename,
              image: { type: 'jpeg', quality: 0.98 },
              html2canvas: { scale: 2, useCORS: true },
              jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' },
            })
            .from(element)
            .save();
        } catch {
          // Final fallback: open in new tab and let user print
          const blob = new Blob([reportHtml], { type: 'text/html' });
          const url = URL.createObjectURL(blob);
          window.open(url, '_blank');
          URL.revokeObjectURL(url);
        }
      } else {
        setExportError(response.data.message || 'Report generation failed');
      }
    } catch (err) {
      console.error('Report generation failed:', err);
      setExportError('Failed to generate report. Please try again.');
    } finally {
      setExportLoading(false);
    }
  };

  const handleResetAllUserData = async () => {
    if (!userId) return;
    if (!confirm('Are you sure you want to delete ALL your data and projects? This cannot be undone.')) return;
    
    try {
      const response = await fetch(`${API_URL}/api/demo/reset-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      if (response.ok) {
        localStorage.removeItem('activeProjectId');
        setProject(null);
        alert('All user data has been reset.');
        window.location.reload();
      }
    } catch (err) {
      console.error(err);
      alert('Failed to reset user data.');
    }
  };

  const statDisplay = (val, suffix = '') =>
    val === null || val === undefined ? '—' : `${val}${suffix}`;

  // Helper to safely render risk detail evidence (may be list or string)
  const renderEvidence = (val) => {
    if (!val) return 'N/A';
    if (Array.isArray(val)) return val.join(' | ');
    return String(val);
  };

  const getTrainingEvidenceWithTimestamp = (t) => {
    const backendEvidence = t.recommendation_json?.evidence;
    if (backendEvidence && String(backendEvidence).includes('@')) {
      return backendEvidence;
    }
    const trigger = (t.recommendation_json?.violation_trigger || '').toLowerCase();
    if (!trigger) return backendEvidence || 'N/A';
    
    const matchedViol = violations.find(v => (v.violation_type || '').toLowerCase().includes(trigger));
    if (matchedViol) {
      const ts = matchedViol.timestamp != null ? `${parseFloat(matchedViol.timestamp).toFixed(2)}s` : '0.00s';
      return `${trigger} @ ${ts}`;
    }
    
    return backendEvidence || t.recommendation_json?.violation_trigger || 'N/A';
  };

  // Helper to render related SOPs (may be related_sop_rules or related_sops)

  return (
    <div className="p-8 space-y-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="flex flex-wrap justify-between items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Executive Safety Dashboard</h1>
        <div className="flex flex-wrap gap-2">
          <button onClick={loadDemoData} className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm font-medium">
            Load Demo Data
          </button>
          <button onClick={resetDemoData} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm font-medium">
            Reset Project
          </button>
          <button onClick={handleResetAllUserData} className="px-4 py-2 bg-red-900 text-white rounded hover:bg-red-950 text-sm font-medium">
            Reset All Data
          </button>
          <button
            onClick={handleExportPDF}
            disabled={!hasData || exportLoading}
            className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-900 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exportLoading ? 'Generating PDF...' : 'Export to PDF'}
          </button>
        </div>
      </div>

      {exportError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-800 dark:text-red-200">
          {exportError}{' '}
          <button onClick={() => setExportError(null)} className="ml-2 text-red-600 underline">Dismiss</button>
        </div>
      )}

      {!hasData && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-sm text-yellow-800 dark:text-yellow-200">
          No safety data yet. Click <strong>Load Demo Data</strong> to populate the dashboard, or upload a video from the Upload page.
        </div>
      )}

      <div ref={dashboardRef} className="space-y-8 bg-gray-50 dark:bg-gray-900 pb-10">
        <div>
          <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-gray-200">Safety Scorecard</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
              <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium">Overall Safety Score</h3>
              <p className="text-3xl font-bold mt-2 text-indigo-600">{statDisplay(stats.overallSafety, '/100')}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
              <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium">PPE Compliance</h3>
              <p className="text-3xl font-bold mt-2 text-green-600">{statDisplay(stats.compliance, '%')}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
              <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium">SOP Compliance</h3>
              <p className="text-3xl font-bold mt-2 text-blue-600">{statDisplay(stats.sopCompliance, '/100')}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
              <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium">Incident Risk Score</h3>
              <p className="text-3xl font-bold mt-2 text-yellow-600">{statDisplay(stats.riskScore)}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
              <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium">Training Readiness</h3>
              <p className="text-3xl font-bold mt-2 text-purple-600">{statDisplay(stats.trainingReadiness, '%')}</p>
            </div>
          </div>
          {hasData && (
            <p className="text-xs text-gray-500 mt-2">{stats.violations} violation(s) detected across uploaded videos.</p>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">AI Risk Analysis</h2>

            {risks.map((r) => (
              <div key={r.id} className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center border-b pb-3 mb-3">
                  <h3 className="font-bold text-gray-900 dark:text-white">Risk Assessment</h3>
                  <span className={`px-2 py-1 text-xs font-bold rounded ${r.score > 75 ? 'bg-red-100 text-red-800' : r.score > 50 ? 'bg-orange-100 text-orange-800' : r.score > 25 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                    Score: {r.score}/100 ({r.score > 75 ? 'Critical' : r.score > 50 ? 'High' : r.score > 25 ? 'Medium' : 'Low'})
                  </span>
                </div>
                {/* Risk Explainability Breakdown */}
                {r.details?.violation_breakdown?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold text-gray-500 uppercase mb-2">Score Breakdown (base × duration × confidence)</p>
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {r.details.violation_breakdown.slice(0, 10).map((v, i) => (
                        <div key={i} className="flex items-center justify-between text-xs font-mono bg-gray-50 dark:bg-gray-700 rounded px-2 py-1">
                          <span className="text-gray-700 dark:text-gray-300 truncate flex-1">{v.rule}</span>
                          <span className="ml-2 text-red-600 font-bold whitespace-nowrap">
                            {v.base_weight} × {v.duration_multiplier?.toFixed(2)} × {v.confidence_multiplier?.toFixed(2)} = +{v.adjusted_weight?.toFixed(1)}
                          </span>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs font-bold text-right mt-1 text-gray-700 dark:text-gray-300">
                      Final Score: {r.score}/100
                    </p>
                  </div>
                )}
                <p className="text-xs text-gray-500">{r.details?.score_formula}</p>
              </div>
            ))}

            {predictions.map((p) => (
              <div key={p.id} className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/10">
                <div className="flex justify-between items-center border-b border-orange-200 dark:border-orange-800 pb-3 mb-3">
                  <h3 className="font-bold text-orange-900 dark:text-orange-100">Incident Prediction: {p.prediction_details?.type}</h3>
                  <span className="px-2 py-1 text-xs font-bold rounded bg-orange-200 text-orange-900">{(p.probability * 100).toFixed(0)}% Prob</span>
                </div>
                <div className="space-y-2 text-sm text-orange-800 dark:text-orange-200">
                  <p><span className="font-semibold">Reasoning:</span> {p.prediction_details?.reasoning}</p>
                  <p><span className="font-semibold">Evidence:</span> {renderEvidence(p.prediction_details?.evidence)}</p>
                </div>
              </div>
            ))}

            {risks.length === 0 && <p className="text-sm text-gray-500">No risk data available.</p>}
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">Training &amp; Insights</h2>

            {trainings.map((t) => (
              <div key={t.id} className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center border-b pb-3 mb-3">
                  <h3 className="font-bold text-gray-900 dark:text-white">Training: {t.human_readable_summary}</h3>
                  <span className={`px-2 py-1 text-xs font-bold rounded ${t.priority === 'Critical' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>{t.priority}</span>
                </div>
                <div className="space-y-2 text-sm">
                  <p><span className="font-semibold text-gray-700 dark:text-gray-300">Module:</span> {t.recommendation_json?.module_name || t.recommendation_json?.training_title || t.human_readable_summary || 'N/A'}</p>
                  <p><span className="font-semibold text-gray-700 dark:text-gray-300">Reasoning:</span> {t.recommendation_json?.reasoning || t.recommendation_json?.recommended_action || t.explanation || 'N/A'}</p>
                  <p><span className="font-semibold text-gray-700 dark:text-gray-300">Evidence:</span> {getTrainingEvidenceWithTimestamp(t)}</p>
                  <p><span className="font-semibold text-gray-700 dark:text-gray-300">Related SOPs:</span> {t.recommendation_json?.related_sop_rules ? (t.recommendation_json.related_sop_rules.join(', ')) : (t.recommendation_json?.violation_trigger || 'N/A')}</p>
                </div>
              </div>
            ))}

            <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="font-bold text-gray-900 dark:text-white mb-3">Recent Agent Activity</h3>
              <div className="space-y-3">
                {recentLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md text-sm border-l-4 border-indigo-500">
                    <span className="font-bold text-gray-700 dark:text-gray-200 block mb-1 uppercase text-xs">{log.source_type} Agent</span>
                    {log.content}
                  </div>
                ))}
                {recentLogs.length === 0 && <p className="text-sm text-gray-500">No agent logs available.</p>}
              </div>
            </div>
          </div>
        </div>

        {/* Violation Timeline */}
        {hasData && (() => {
          const timeline = analyticsData?.timeline || [];
          if (timeline.length === 0) return null;
          return (
            <div className="mt-8">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200 border-t pt-8 mb-4">Violation Timeline</h2>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 p-5">
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {timeline.map((ev, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm border-b border-gray-100 dark:border-gray-700 pb-2">
                      <span className="font-mono text-indigo-600 dark:text-indigo-400 w-12 shrink-0">{ev.timestamp_fmt}</span>
                      <span className={`shrink-0 px-1 rounded text-xs font-bold ${ev.ppe_type === 'helmet' ? 'bg-red-100 text-red-800' : ev.ppe_type === 'gloves' ? 'bg-orange-100 text-orange-800' : ev.ppe_type === 'goggles' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>
                        {ev.worker_id}
                      </span>
                      <span className="flex-1 text-gray-700 dark:text-gray-300">{ev.description}</span>
                      {ev.confidence > 0 && <span className="text-xs text-gray-400 shrink-0">{(ev.confidence*100).toFixed(0)}%</span>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Worker Summary */}
        {hasData && (() => {
          const workerSummary = analyticsData?.worker_summary || {};
          const workers = Object.entries(workerSummary);
          if (workers.length === 0) return null;
          return (
            <div className="mt-8">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200 mb-4">Worker PPE Compliance</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {workers.map(([wid, data]) => (
                  <div key={wid} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold text-gray-900 dark:text-white">Worker {wid}</span>
                      <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">{(data.violations || []).length} violation(s)</span>
                    </div>
                    <p className="text-xs text-gray-500 mb-1">Missing PPE: <span className="font-semibold text-orange-600">{(data.ppe_types_missing || []).join(', ') || 'none'}</span></p>
                    <p className="text-xs text-gray-500">Total exposure: <span className="font-semibold text-red-600">{data.total_duration?.toFixed(1) || 0}s</span></p>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* PPE by Type Breakdown */}
        {hasData && analyticsData?.ppe_by_type?.by_ppe_type && (
          <div className="mt-8">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200 mb-4">PPE Violations by Type</h2>
            <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {Object.entries(analyticsData.ppe_by_type.by_ppe_type).map(([ppe, count]) => (
                  <div key={ppe} className="text-center">
                    <div className={`text-2xl font-bold ${count > 0 ? 'text-red-600' : 'text-green-600'}`}>{count}</div>
                    <div className="text-xs text-gray-500 capitalize mt-1">{ppe}</div>
                    <div className={`h-1 rounded mt-1 ${count > 0 ? 'bg-red-400' : 'bg-green-400'}`}></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Training Recommendations from Violations */}
        {hasData && analyticsData?.training_recommendations?.length > 0 && (
          <div className="mt-8">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200 mb-4">Training Recommendations</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analyticsData.training_recommendations.map((rec, i) => {
                const priority = rec.priority || 'medium';
                const title = rec.training_title || rec.module_name || 'Safety Training';
                const action = rec.recommended_action || rec.reasoning || rec.explanation || 'N/A';
                const trigger = rec.violation_trigger || (rec.related_sop_rules ? rec.related_sop_rules.join(', ') : 'N/A');
                return (
                  <div key={i} className={`p-4 rounded-lg border-l-4 ${priority.toLowerCase() === 'high' || priority.toLowerCase() === 'critical' ? 'border-red-500 bg-red-50 dark:bg-red-900/10' : 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/10'}`}>
                    <p className="font-bold text-sm text-gray-900 dark:text-gray-100">{title}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{action}</p>
                    <p className="text-xs text-gray-400 mt-1">Triggered by: {trigger}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Historical Analytics Trends */}
        {analyticsData && hasData && (
          <div className="mt-8 space-y-6">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200 border-t pt-8">Historical Analytics Trends</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Most Common Violations */}
              <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <h3 className="text-gray-500 dark:text-gray-400 font-bold mb-4 border-b pb-2">Most Common Violations</h3>
                <div className="space-y-4">
                  {(analyticsData.monthly_violations || []).slice(0, 3).map((vTrend, idx) => (
                    <div key={idx} className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                      <p className="font-bold text-indigo-600 dark:text-indigo-400 text-sm mb-2">{vTrend.violation_type}</p>
                      <div className="flex gap-4 text-sm text-gray-700 dark:text-gray-300 flex-wrap">
                        {vTrend.monthly_trend.map(m => (
                          <div key={m.month} className="flex flex-col items-center">
                            <span className="text-xs text-gray-500">{m.month}</span>
                            <span className="font-semibold">{m.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {(!analyticsData.monthly_violations || analyticsData.monthly_violations.length === 0) && (
                    <p className="text-sm text-gray-500">No historical violation data.</p>
                  )}
                </div>
              </div>

              {/* Risk Trend */}
              <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <h3 className="text-gray-500 dark:text-gray-400 font-bold mb-4 border-b pb-2">Average Risk Score Trend</h3>
                <div className="flex justify-between items-end h-32 gap-2 mt-4">
                  {(analyticsData.risk_trend || []).map((point, idx) => (
                    <div key={idx} className="flex flex-col items-center flex-1">
                      <div className="w-full bg-blue-100 dark:bg-blue-900/30 rounded-t flex items-end justify-center relative" style={{ height: '80px' }}>
                        <div className="w-full bg-blue-500 rounded-t" style={{ height: `${Math.min(point.avg_risk_score, 100)}%` }}></div>
                        <span className="absolute -top-6 text-xs font-bold text-gray-700 dark:text-gray-300">{point.avg_risk_score}</span>
                      </div>
                      <span className="text-xs text-gray-500 mt-2">{point.period}</span>
                    </div>
                  ))}
                </div>
                {(!analyticsData.risk_trend || analyticsData.risk_trend.length === 0) && (
                  <p className="text-sm text-gray-500 mt-4">Not enough risk data for trend.</p>
                )}
              </div>

              {/* PPE Trend */}
              <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <h3 className="text-gray-500 dark:text-gray-400 font-bold mb-4 border-b pb-2">PPE Compliance Trend</h3>
                <div className="space-y-3 mt-4">
                  {(analyticsData.ppe_trend || []).map((point, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium w-12 text-gray-600 dark:text-gray-400">{point.period}</span>
                      <div className="flex-1 mx-3 h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full bg-green-500" style={{ width: `${point.ppe_compliance_pct}%` }}></div>
                      </div>
                      <span className="text-sm font-bold w-12 text-right text-gray-700 dark:text-gray-200">{point.ppe_compliance_pct}%</span>
                    </div>
                  ))}
                  {(!analyticsData.ppe_trend || analyticsData.ppe_trend.length === 0) && (
                    <p className="text-sm text-gray-500">Not enough PPE data for trend.</p>
                  )}
                </div>
              </div>

              {/* SOP Compliance Trend */}
              <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <h3 className="text-gray-500 dark:text-gray-400 font-bold mb-4 border-b pb-2">SOP Violation Trend</h3>
                <div className="space-y-4 mt-4 max-h-48 overflow-y-auto">
                  {analyticsData.sop_trend && Object.keys(analyticsData.sop_trend).length > 0 ? (
                    Object.entries(analyticsData.sop_trend).map(([sop, trend], idx) => (
                      <div key={idx} className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                        <p className="font-bold text-blue-600 dark:text-blue-400 text-sm mb-2">{sop}</p>
                        <div className="flex gap-4 text-sm text-gray-700 dark:text-gray-300 flex-wrap">
                          {trend.map(m => (
                            <div key={m.period} className="flex flex-col items-center">
                              <span className="text-xs text-gray-500">{m.period}</span>
                              <span className="font-semibold">{m.violation_count}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Not enough SOP data for trend.</p>
                  )}
                </div>
              </div>

              {/* Training Effectiveness */}
              <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 md:col-span-2">
                <h3 className="text-gray-500 dark:text-gray-400 font-bold mb-4 border-b pb-2">Training Effectiveness</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  {analyticsData.training_effectiveness && Object.keys(analyticsData.training_effectiveness).length > 0 && !analyticsData.training_effectiveness.status ? (
                    Object.entries(analyticsData.training_effectiveness).map(([module, eff], idx) => (
                      <div key={idx} className="flex justify-between items-center bg-gray-50 dark:bg-gray-700 p-4 rounded border-l-4 border-purple-500">
                        <div>
                          <p className="font-bold text-sm text-gray-900 dark:text-gray-100">{module}</p>
                          <p className="text-xs text-gray-500">Before: {eff.violations_before} | After: {eff.violations_after}</p>
                        </div>
                        <div className={`px-2 py-1 rounded text-xs font-bold ${eff.effective ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {eff.reduction_percent}% reduction
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Not enough training data available.</p>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}
