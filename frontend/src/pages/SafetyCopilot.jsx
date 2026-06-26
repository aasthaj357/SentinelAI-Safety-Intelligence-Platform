import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useActiveProject } from '../context/ActiveProjectContext';
import { API_URL } from '../lib/constants';

const SUGGESTED = [
  'Show all helmet violations',
  'Why was this risk score generated?',
  'Which SOP sections were violated?',
  'What training is recommended?',
  'Show violations by worker',
  'What is the PPE compliance rate?',
  'Predict likely incidents based on evidence',
];

function SourceBadge({ source, onClick }) {
  const m = source.metadata || {};
  const isGap = m.undetermined || m.source === 'sop_gap';
  const conf = isGap ? 'GAP' : (m.confidence != null ? `${(m.confidence * 100).toFixed(0)}%` : null);
  const ts = m.timestamp != null && !isGap ? `${Number(m.timestamp).toFixed(1)}s` : null;
  const frame = m.frame_num && !isGap ? `f${m.frame_num}` : null;
  const worker = m.worker_id || null;
  const label = m.detection_label?.replace(/-/g, ' ') || 'Evidence';
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full transition font-mono ${isGap ? 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300 hover:bg-orange-200' : 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200'}`}
    >
      <span className="font-bold">[{source.id}]</span>
      <span>{label}</span>
      {ts && <span className="text-indigo-500">@{ts}</span>}
      {frame && <span className="text-indigo-400">{frame}</span>}
      {worker && <span className="bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1 rounded">{worker}</span>}
      {conf && <span className={`font-bold ${isGap ? 'text-orange-600' : (parseFloat(conf) >= 70 ? 'text-red-600' : 'text-yellow-600')}`}>{conf}</span>}
    </button>
  );
}

function EvidencePanel({ source, onSeek, onClose }) {
  if (!source) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-400 text-sm text-center px-4">Click a source citation in the chat to inspect evidence here.</p>
      </div>
    );
  }
  const m = source.metadata || {};
  const isGap = m.undetermined || m.source === 'sop_gap';
  const imgUrl = m.cropped_url || m.screenshot_url;
  const fields = isGap ? [
    ['Detection', (m.detection_label || '').replace(/-/g,' ')],
    ['Status', 'SOP Compliance Gap'],
    ['Coverage', 'Whole Video'],
    ['Confidence', 'Undetermined'],
    ['Worker', m.worker_id || '—'],
    ['Duration', m.duration_seconds ? `${m.duration_seconds.toFixed(1)}s` : '10.0s'],
    ['Risk Score', m.risk_score != null ? `${m.risk_score}/100` : '—'],
  ] : [
    ['Detection', (m.detection_label || '').replace(/-/g,' ')],
    ['Timestamp', m.timestamp != null ? `${Number(m.timestamp).toFixed(2)}s` : '—'],
    ['Frame', m.frame_num ? `#${m.frame_num}` : '—'],
    ['Confidence', m.confidence != null ? `${(m.confidence*100).toFixed(0)}%` : '—'],
    ['Worker', m.worker_id || '—'],
    ['Duration', m.duration_seconds ? `${m.duration_seconds.toFixed(1)}s` : '—'],
    ['Risk Score', m.risk_score != null ? `${m.risk_score}/100` : '—'],
  ];
  return (

    <div className="flex-1 overflow-y-auto space-y-3 p-1">
      <div className="flex justify-between items-center">
        <span className="text-xs font-bold uppercase text-indigo-600">Evidence [{source.id}]</span>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
      </div>
      {isGap && (
        <div className="bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-800 rounded p-2 text-xs text-orange-800 dark:text-orange-200">
          <p className="font-bold">⚠️ SOP Gap (Not Visually Confirmed)</p>
          <p className="mt-1">This item is flagged because the SOP requires it, but the worker or body part was not visible in the video frame (e.g., due to camera angle).</p>
        </div>
      )}
      {imgUrl && <img src={imgUrl} alt="Evidence" className="w-full rounded border border-gray-200 dark:border-gray-700" />}
      <div className="grid grid-cols-2 gap-1">
        {fields.map(([k, v]) => (
          <div key={k} className="bg-gray-50 dark:bg-gray-800 rounded p-1.5">
            <p className="text-xs text-gray-400">{k}</p>
            <p className="text-xs font-bold text-gray-900 dark:text-white truncate">{v}</p>
          </div>
        ))}
      </div>
      {m.sop_section && (
        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded p-2">
          <p className="text-xs font-bold text-indigo-600 mb-0.5">SOP Section</p>
          <p className="text-xs text-indigo-900 dark:text-indigo-200 font-semibold">{m.sop_section}</p>
          {m.sop_excerpt && <p className="text-xs text-indigo-700 dark:text-indigo-300 mt-0.5 italic line-clamp-3">{m.sop_excerpt}</p>}
        </div>
      )}
      {m.risk_reason && (
        <div className="bg-red-50 dark:bg-red-900/20 rounded p-2">
          <p className="text-xs font-bold text-red-600 mb-0.5">Risk Explanation</p>
          <p className="text-xs text-red-800 dark:text-red-200">{m.risk_reason}</p>
        </div>
      )}
      {m.why_detected && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded p-2">
          <p className="text-xs font-bold text-yellow-700 mb-0.5">Why Detected</p>
          <p className="text-xs text-yellow-900 dark:text-yellow-200">{m.why_detected}</p>
        </div>
      )}
      {m.mitigation && (
        <div className="bg-green-50 dark:bg-green-900/20 rounded p-2">
          <p className="text-xs font-bold text-green-700 mb-0.5">Mitigation</p>
          <p className="text-xs text-green-900 dark:text-green-200">{m.mitigation}</p>
        </div>
      )}
      {m.bbox && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded p-2">
          <p className="text-xs font-bold text-gray-500 mb-0.5">Bounding Box</p>
          <p className="text-xs font-mono text-gray-700 dark:text-gray-300">[{m.bbox.join(', ')}]</p>
        </div>
      )}
      {!isGap && m.timestamp != null && m.video_id != null && (
        <button
          onClick={() => onSeek(m, source)}
          className="w-full bg-indigo-600 text-white text-xs py-2 rounded-lg hover:bg-indigo-700 font-medium"
        >▶ Seek to Frame in Video</button>
      )}
    </div>
  );
}

export default function SafetyCopilot() {
  const { activeProjectId, userId } = useActiveProject();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([
    { role: 'system', content: 'Hello! I\'m your AI Safety Copilot. Every answer is grounded in your evidence records and SOP. Ask me anything about violations, risk scores, PPE compliance, or training.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async (text) => {
    const msg = text || input;
    if (!msg.trim() || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setLoading(true);
    try {
      if (!activeProjectId || !userId) throw new Error('No project loaded. Load demo data from the Dashboard first.');
      const res = await axios.post(`${API_URL}/api/chat/`, {
        project_id: activeProjectId,
        user_id: userId,
        message: msg,
        history: messages.filter(m => m.role !== 'system').slice(-6),
      });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.reply,
        sources: res.data.sources || [],
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.response?.data?.reply || err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSeek = (meta) => {
    const videoId = meta.video_id;
    if (videoId) {
      navigate(`/analysis/${videoId}?t=${meta.timestamp || 0}&frame=${meta.frame_num || ''}`);
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] bg-gray-50 dark:bg-gray-900">
      {/* Chat */}
      <div className="flex-1 flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <h2 className="text-lg font-bold text-gray-800 dark:text-white">Safety Officer Copilot</h2>
          <p className="text-xs text-gray-500">Every answer is grounded in retrieved evidence + SOP. Citations show frame, timestamp, confidence.</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-2xl rounded-xl px-4 py-3 ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'}`}>
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                {msg.sources?.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-gray-300/50 dark:border-gray-600">
                    <p className="text-xs text-gray-400 mb-1.5 font-semibold">Retrieved Evidence:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.sources.map((s, si) => (
                        <SourceBadge key={si} source={s} onClick={() => setSelectedSource(s)} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 px-4 py-3 rounded-xl text-sm text-gray-500 italic flex items-center gap-2">
                <div className="animate-spin w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full"></div>
                Retrieving evidence and generating grounded answer...
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="p-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
          <div className="flex flex-wrap gap-1">
            {SUGGESTED.map(q => (
              <button key={q} onClick={() => handleSend(q)} className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full hover:bg-indigo-100 dark:hover:bg-indigo-900/30 hover:text-indigo-700 transition">{q}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Ask about violations, risk scores, PPE compliance, SOP..."
              className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button onClick={() => handleSend()} disabled={loading} className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50">Send</button>
          </div>
        </div>
      </div>

      {/* Evidence panel */}
      <div className="w-80 bg-white dark:bg-gray-800 flex flex-col p-4">
        <h3 className="text-sm font-bold text-gray-800 dark:text-white mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">Evidence Inspector</h3>
        <EvidencePanel source={selectedSource} onSeek={handleSeek} onClose={() => setSelectedSource(null)} />
      </div>
    </div>
  );
}
