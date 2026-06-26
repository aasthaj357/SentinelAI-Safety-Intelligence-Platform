import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';
import { ShieldAlert, Eye, Download, ZoomIn, ZoomOut, Loader2, AlertCircle, X, ChevronRight } from 'lucide-react';

export default function EvidenceGallery() {
  const { activeProjectId, userId, isLoading } = useActiveProject();
  const navigate = useNavigate();
  const [violations, setViolations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [annotating, setAnnotating] = useState(false);
  const [zoomScale, setZoomScale] = useState(1);
  
  // Filters
  const [filterType, setFilterType] = useState('All');
  const [filterSeverity, setFilterSeverity] = useState('All');
  const [filterWorker, setFilterWorker] = useState('All');
  const [filterDate, setFilterDate] = useState('All');

  const fetchViolations = async () => {
    if (!activeProjectId || !userId) return;
    try {
      const response = await axios.get(`${API_URL}/api/evidence/project/${activeProjectId}?user_id=${userId}`);
      if (response.data) {
        setViolations(response.data);
      }
    } catch (err) {
      console.error("Failed to fetch violations:", err);
    }
  };

  useEffect(() => {
    if (!isLoading && activeProjectId && userId) fetchViolations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, userId, isLoading]);

  const getSeverity = (confidence, isGap = false) => {
    if (isGap) return { level: 'High', color: 'bg-orange-100 text-orange-800 border-orange-200 shadow-sm font-bold' };
    if (confidence >= 0.9) return { level: 'Critical', color: 'bg-red-100 text-red-800 border-red-200' };
    if (confidence >= 0.7) return { level: 'High', color: 'bg-orange-100 text-orange-800 border-orange-200' };
    if (confidence >= 0.5) return { level: 'Medium', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' };
    return { level: 'Low', color: 'bg-blue-100 text-blue-800 border-blue-200' };
  };

  const workerIds = useMemo(() => {
    const ids = new Set(violations.map(v => {
      const meta = typeof v.metadata === 'string' ? JSON.parse(v.metadata) : (v.metadata || {});
      return meta.worker_id;
    }).filter(Boolean));
    return ['All', ...Array.from(ids)];
  }, [violations]);

  const violationTypes = useMemo(() => {
    const types = new Set(violations.map(v => v.detection_label));
    return ['All', ...Array.from(types)];
  }, [violations]);

  const filteredViolations = useMemo(() => {
    return violations.filter(v => {
      const meta = typeof v.metadata === 'string' ? JSON.parse(v.metadata) : (v.metadata || {});
      const isGap = meta.undetermined || meta.source === 'sop_gap';
      if (filterType !== 'All' && v.detection_label !== filterType) return false;
      const sev = getSeverity(v.confidence, isGap).level;
      if (filterSeverity !== 'All' && sev !== filterSeverity) return false;
      if (filterWorker !== 'All' && meta.worker_id !== filterWorker) return false;
      if (filterDate !== 'All') {
        const vDate = new Date(v.created_at);
        const today = new Date();
        if (filterDate === 'Today' && vDate.toDateString() !== today.toDateString()) return false;
        if (filterDate === 'Last 7 Days') {
          const diffDays = Math.ceil(Math.abs(today - vDate) / (1000 * 60 * 60 * 24));
          if (diffDays > 7) return false;
        }
      }
      return true;
    });
  }, [violations, filterType, filterSeverity, filterWorker, filterDate]);

  const handleCardClick = async (v) => {
    setSelected(v);
    setZoomScale(1);
    
    // If annotated screenshot url is missing, generate it on demand!
    if (!v.annotated_screenshot_url && !v.screenshot_url) return; // skip if both missing
    if (!v.annotated_screenshot_url) {
      setAnnotating(true);
      try {
        const response = await axios.post(`${API_URL}/api/analysis/evidence/${v.id}/annotate?user_id=${userId}`);
        if (response.data && response.data.url) {
          const updatedUrl = response.data.url;
          setViolations(prev => prev.map(item => item.id === v.id ? { ...item, annotated_screenshot_url: updatedUrl } : item));
          setSelected(prev => ({ ...prev, annotated_screenshot_url: updatedUrl }));
        }
      } catch (err) {
        console.error("Failed to generate annotation on-demand:", err);
      } finally {
        setAnnotating(false);
      }
    }
  };

  const handleSeekVideo = (v) => {
    if (v.video_id && v.timestamp != null) {
      navigate(`/analysis/${v.video_id}?t=${v.timestamp}&frame=${v.frame_num || ''}`);
    }
  };

  const handleDownload = (url, filename) => {
    if (!url) return;
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'evidence_screenshot.jpg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-8 space-y-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ShieldAlert className="w-8 h-8 text-indigo-500" />
            Evidence Gallery
          </h1>
          <p className="text-sm text-gray-500 mt-1">{filteredViolations.length} of {violations.length} records — Click a card to view annotated frame</p>
        </div>
        <div className="flex flex-wrap gap-3 mt-4 md:mt-0 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          {[
            { label: 'Type', value: filterType, set: setFilterType, opts: violationTypes },
            { label: 'Severity', value: filterSeverity, set: setFilterSeverity, opts: ['All','Critical','High','Medium','Low'] },
            { label: 'Worker', value: filterWorker, set: setFilterWorker, opts: workerIds },
            { label: 'Date', value: filterDate, set: setFilterDate, opts: ['All','Today','Last 7 Days'] },
          ].map(({ label, value, set, opts }) => (
            <div key={label}>
              <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
              <select className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-md p-2" value={value} onChange={e => set(e.target.value)}>
                {opts.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredViolations.map(v => {
          const meta = typeof v.metadata === 'string' ? JSON.parse(v.metadata) : (v.metadata || {});
          const isGap = meta.undetermined || meta.source === 'sop_gap';
          const severity = getSeverity(v.confidence, isGap);
          const workerID = meta.worker_id;
          const duration = meta.duration_seconds;
          const imgUrl = v.annotated_screenshot_url || v.screenshot_url;

          return (
            <div
              key={v.id}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col transition-all hover:scale-[1.02] hover:shadow-md cursor-pointer"
              onClick={() => handleCardClick(v)}
            >
              {/* Image thumbnail */}
              <div className="h-44 bg-gray-200 dark:bg-gray-700 flex items-center justify-center relative group overflow-hidden">
                {imgUrl ? (
                  <img src={imgUrl} alt="Evidence Thumbnail" className="object-cover w-full h-full" />
                ) : (
                  <div className="flex flex-col items-center text-gray-400">
                    <Eye className="w-8 h-8 mb-1" />
                    <span className="font-mono text-xs">
                      {isGap ? 'SOP Compliance Gap' : `Frame ${v.frame_num} @ ${v.timestamp?.toFixed(1)}s`}
                    </span>
                  </div>
                )}
                <div className={`absolute top-2 right-2 px-2 py-0.5 text-xs font-bold rounded-full border shadow-sm ${severity.color}`}>
                  {severity.level}
                </div>
                {workerID && (
                  <div className="absolute top-2 left-2 px-2 py-0.5 text-xs font-bold rounded-full bg-gray-900/70 text-white font-mono">
                    {workerID}
                  </div>
                )}
              </div>

              {/* Card body */}
              <div className="p-4 flex-1 flex flex-col space-y-1.5 text-xs">
                <h3 className="font-bold text-sm text-gray-900 dark:text-white uppercase tracking-wide truncate">
                  {v.detection_label?.replace(/-/g, ' ')}
                </h3>
                <div className="grid grid-cols-2 gap-x-2 gap-y-1 font-mono">
                  <span className="text-gray-400">Timestamp</span>
                  <span className="text-gray-800 dark:text-gray-200 text-right">
                    {v.timestamp != null ? `${v.timestamp.toFixed(2)}s` : '—'}
                  </span>
                  
                  <span className="text-gray-400">Frame</span>
                  <span className="text-gray-800 dark:text-gray-200 text-right">
                    {v.frame_num ? `#${v.frame_num}` : '—'}
                  </span>
                  
                  <span className="text-gray-400">Confidence</span>
                  <span className={`text-right font-bold ${v.confidence >= 0.7 ? 'text-red-600' : 'text-yellow-600'}`}>
                    {v.confidence != null ? `${(v.confidence * 100).toFixed(0)}%` : '—'}
                  </span>

                  {duration && (
                    <>
                      <span className="text-gray-400">Duration</span>
                      <span className="text-orange-600 text-right font-bold">{duration.toFixed(1)}s</span>
                    </>
                  )}
                </div>
                {v.sop_section && (
                  <p className="text-indigo-600 dark:text-indigo-400 truncate mt-1">
                    <span className="text-gray-400">SOP: </span>{v.sop_section}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {violations.length === 0 && (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500">No evidence records found.</p>
          <p className="text-sm text-gray-400 mt-2">Upload and analyze a video to generate evidence.</p>
        </div>
      )}

      {/* Advanced Zoom/Metadata Side Panel Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setSelected(null)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-5xl w-full flex flex-col md:flex-row max-h-[90vh] overflow-hidden" onClick={e => e.stopPropagation()}>
            
            {/* Left side: Large Annotated Image with Zoom & Download Controls */}
            <div className="flex-1 bg-gray-950 flex flex-col relative items-center justify-center min-h-[300px]">
              {annotating ? (
                <div className="flex flex-col items-center gap-2 text-white">
                  <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
                  <span className="text-sm font-mono">Generating annotation on-demand...</span>
                </div>
              ) : (selected.annotated_screenshot_url || selected.screenshot_url) ? (
                <div className="relative overflow-hidden w-full h-full flex items-center justify-center">
                  <img
                    src={selected.annotated_screenshot_url || selected.screenshot_url}
                    alt="Annotated Evidence"
                    style={{ transform: `scale(${zoomScale})` }}
                    className="max-h-[60vh] max-w-full object-contain transition-transform duration-250 ease-out"
                  />
                  <div className="absolute bottom-4 left-4 flex gap-2">
                    <button
                      onClick={() => setZoomScale(prev => Math.min(prev + 0.25, 3))}
                      className="bg-black/60 hover:bg-black/80 text-white p-2 rounded-full transition-colors"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => setZoomScale(prev => Math.max(prev - 0.25, 0.75))}
                      className="bg-black/60 hover:bg-black/80 text-white p-2 rounded-full transition-colors"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDownload(selected.annotated_screenshot_url || selected.screenshot_url, `evidence_${selected.id}.jpg`)}
                      className="bg-black/60 hover:bg-black/80 text-white p-2 rounded-full transition-colors"
                      title="Download Annotated Image"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 flex flex-col items-center">
                  <AlertCircle className="w-12 h-12 text-gray-400 mb-2" />
                  <span className="text-sm font-mono">Image Not Available</span>
                </div>
              )}
            </div>

            {/* Right side: Metadata Side Panel */}
            <div className="w-full md:w-[360px] border-t md:border-t-0 md:border-l border-gray-200 dark:border-gray-700 flex flex-col bg-white dark:bg-gray-900 max-h-[90vh]">
              <div className="flex justify-between items-center p-5 border-b border-gray-200 dark:border-gray-700">
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white uppercase text-base truncate">
                    {selected.detection_label?.replace(/-/g, ' ')}
                  </h3>
                  <span className="text-xs text-gray-400 font-mono">EVIDENCE ID: {selected.id}</span>
                </div>
                <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-5 space-y-4 text-sm">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['Worker ID', selected.metadata?.worker_id || 'unknown'],
                    ['Frame Number', selected.frame_num ? `#${selected.frame_num}` : '—'],
                    ['Timestamp', selected.timestamp != null ? `${selected.timestamp.toFixed(2)}s` : '—'],
                    ['Confidence', selected.confidence != null ? `${(selected.confidence * 100).toFixed(0)}%` : '—'],
                  ].map(([lbl, val]) => (
                    <div key={lbl} className="bg-gray-50 dark:bg-gray-800 p-2.5 rounded-lg border border-gray-100 dark:border-gray-800">
                      <p className="text-xs text-gray-400 font-medium">{lbl}</p>
                      <p className="font-bold text-gray-900 dark:text-white mt-0.5">{val}</p>
                    </div>
                  ))}
                </div>

                {selected.sop_section && (
                  <div className="bg-indigo-50/50 dark:bg-indigo-950/20 p-3 rounded-lg border border-indigo-100 dark:border-indigo-900/40">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider block mb-1">SOP Section</span>
                    <p className="font-semibold text-indigo-900 dark:text-indigo-200">{selected.sop_section}</p>
                    {selected.sop_excerpt && <p className="text-xs text-indigo-700 dark:text-indigo-300 italic mt-1.5">"{selected.sop_excerpt}"</p>}
                  </div>
                )}

                {selected.risk_reason && (
                  <div className="bg-red-50/50 dark:bg-red-950/20 p-3 rounded-lg border border-red-100 dark:border-red-900/40">
                    <span className="text-xs font-bold text-red-600 dark:text-red-400 uppercase tracking-wider block mb-1">Risk Explanation</span>
                    <p className="text-red-800 dark:text-red-200">{selected.risk_reason}</p>
                  </div>
                )}

                {selected.metadata?.mitigation && (
                  <div className="bg-green-50/50 dark:bg-green-950/20 p-3 rounded-lg border border-green-100 dark:border-green-900/40">
                    <span className="text-xs font-bold text-green-700 dark:text-green-400 uppercase tracking-wider block mb-1">Recommended Action</span>
                    <p className="text-green-900 dark:text-green-200">{selected.metadata.mitigation}</p>
                  </div>
                )}
              </div>

              <div className="p-5 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40 flex gap-3">
                <button
                  onClick={() => handleSeekVideo(selected)}
                  className="flex-grow bg-indigo-600 hover:bg-indigo-700 text-white py-2 px-4 rounded-lg font-medium transition-colors text-sm flex items-center justify-center gap-1.5"
                >
                  Seek in Player
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
