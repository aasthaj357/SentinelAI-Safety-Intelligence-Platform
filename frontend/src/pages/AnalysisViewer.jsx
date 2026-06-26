import { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';

export default function AnalysisViewer() {
  const { videoId } = useParams();
  const [searchParams] = useSearchParams();
  const { activeProjectId, userId, isLoading } = useActiveProject();
  const [video, setVideo] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [violations, setViolations] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [jobStatus, setJobStatus] = useState(null);
  const [activeViolation, setActiveViolation] = useState(null);
  const videoRef = useRef(null);

  // Seek target from URL params (?t=12.5&frame=375)
  const seekTarget = parseFloat(searchParams.get('t')) || null;

  const fetchData = async () => {
    if (!videoId || !activeProjectId || !userId) return;

    try {
      const response = await axios.get(`${API_URL}/api/analysis/video/${videoId}?project_id=${activeProjectId}&user_id=${userId}`);
      const data = response.data;
      if (data) {
        if (data.video) setVideo(data.video);
        if (data.video_url) setVideoUrl(data.video_url);
        if (data.transcript) setTranscript(data.transcript);
        if (data.violations) setViolations(data.violations);
        if (data.evidence) setEvidence(data.evidence);
        if (data.job_status) setJobStatus(data.job_status);
      }
    } catch (err) {
      console.error("Failed to fetch video analysis details:", err);
    }
  };

  useEffect(() => {
    if (!isLoading && activeProjectId && userId) fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId, activeProjectId, userId, isLoading]);

  useEffect(() => {
    // Once video is loaded and we have a seek target, jump to it
    if (videoRef.current && seekTarget != null) {
      const handler = () => {
        videoRef.current.currentTime = seekTarget;
        videoRef.current.pause();
      };
      videoRef.current.addEventListener('loadedmetadata', handler, { once: true });
      // If already loaded
      if (videoRef.current.readyState >= 1) {
        videoRef.current.currentTime = seekTarget;
        videoRef.current.pause();
      }
    }
  }, [videoUrl, seekTarget]);

  const seekTo = (timestamp, violation = null) => {
    if (videoRef.current && timestamp != null) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.pause();
    }
    if (violation) setActiveViolation(violation);
  };

  const fmtTs = (s) => {
    if (s == null) return '--:--';
    const m = Math.floor(s / 60);
    const sec = (s % 60).toFixed(1).padStart(4, '0');
    return `${m}:${sec}`;
  };

  if (!video) return (
    <div className="p-8 text-gray-500">
      {isLoading ? 'Loading your workspace...' : 'Video not found or still loading. It may still be processing.'}
    </div>
  );

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{video.title}</h1>
        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${jobStatus === 'completed' ? 'bg-green-100 text-green-800' : jobStatus === 'processing' ? 'bg-blue-100 text-blue-800' : jobStatus === 'failed' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>
          {jobStatus?.toUpperCase() || 'UNKNOWN'}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video player — spans 2 cols */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-3">Video Player</h2>
          <div className="aspect-video bg-black rounded overflow-hidden">
            {videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                className="w-full h-full"
                onLoadedMetadata={() => {
                  if (seekTarget != null && videoRef.current) {
                    videoRef.current.currentTime = seekTarget;
                    videoRef.current.pause();
                  }
                }}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                {video.status === 'analyzed' ? 'Video not available for playback' : 'Analysis in progress...'}
              </div>
            )}
          </div>
          {seekTarget != null && (
            <p className="text-xs text-indigo-600 mt-2">↗ Seeked to {fmtTs(seekTarget)} from evidence record</p>
          )}
          {activeViolation && (() => {
            const activeMeta = typeof activeViolation.metadata === 'string' ? JSON.parse(activeViolation.metadata) : (activeViolation.metadata || {});
            return (
              <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 text-sm">
                <span className="font-bold text-red-700">{activeViolation.violation_type?.replace(/-/g,' ')}</span>
                {activeMeta.worker_id && <span className="ml-2 text-gray-500">Worker {activeMeta.worker_id}</span>}
                {activeViolation.confidence != null && <span className="ml-2 text-gray-500">({(activeViolation.confidence*100).toFixed(0)}% conf)</span>}
              </div>
            );
          })()}
        </div>

        {/* Transcript */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-3">Audio Transcript</h2>
          <div className="h-72 overflow-y-auto bg-gray-50 dark:bg-gray-900 p-3 rounded border border-gray-200 dark:border-gray-700 text-xs font-mono text-gray-800 dark:text-gray-200 leading-relaxed">
            {transcript?.transcript_text || 'No transcript available.'}
          </div>
        </div>
      </div>

      {/* Violation timeline + evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-3">
            Violation Timeline <span className="text-sm text-gray-400 font-normal">({violations.length} events — click to seek)</span>
          </h2>
          {violations.length === 0 ? (
            <p className="text-sm text-gray-500">No violations detected.</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {violations.map(v => {
                const meta = typeof v.metadata === 'string' ? JSON.parse(v.metadata) : (v.metadata || {});
                const isGap = meta.undetermined || meta.source === 'sop_gap';
                const dur = meta.duration_seconds;
                const wid = meta.worker_id;
                const frameStart = meta.frame_start;
                const isCritical = !isGap && v.confidence >= 0.9;
                return (
                  <div
                    key={v.id}
                    className={`flex gap-3 p-3 rounded-lg border-l-4 transition ${isGap ? 'border-orange-500 bg-orange-50/30 dark:bg-orange-900/10 cursor-default' : (isCritical ? 'border-red-500 bg-red-50/30 dark:bg-red-900/10 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700' : 'border-yellow-400 bg-yellow-50/30 dark:bg-yellow-900/10 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700')}`}
                    onClick={() => !isGap && seekTo(v.timestamp, v)}
                  >
                    <span className={`font-mono text-xs w-12 shrink-0 pt-0.5 ${isGap ? 'text-orange-600 dark:text-orange-400 font-bold' : 'text-indigo-500'}`}>
                      {isGap ? 'GAP' : fmtTs(v.timestamp)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">{v.violation_type?.replace(/-/g,' ')}</p>
                      <div className="flex flex-wrap gap-2 mt-0.5">
                        {wid && <span className="text-xs text-gray-400">{wid}</span>}
                        {isGap ? (
                          <>
                            <span className="text-xs text-red-600 dark:text-red-400 font-semibold">SOP Compliance Gap</span>
                            <span className="text-xs text-gray-400">Whole Video</span>
                            <span className="text-xs text-orange-600 font-semibold">Duration: {(dur || 10.0).toFixed(1)}s</span>
                            <span className="text-xs text-gray-400">Undetermined conf</span>
                          </>
                        ) : (
                          <>
                            {frameStart != null && <span className="text-xs text-gray-400 font-mono">Frame #{frameStart}</span>}
                            {dur && <span className="text-xs text-orange-600 font-semibold">Duration: {dur.toFixed(1)}s</span>}
                            <span className="text-xs text-gray-400">{(v.confidence*100).toFixed(0)}% conf</span>
                          </>
                        )}
                      </div>
                    </div>
                    {!isGap && (
                      <svg className="w-4 h-4 text-gray-300 shrink-0 self-center" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/></svg>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-3">
            Evidence Records <span className="text-sm text-gray-400 font-normal">({evidence.length} — click to seek)</span>
          </h2>
          {evidence.length === 0 ? (
            <p className="text-sm text-gray-500">No evidence records for this video.</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {evidence.map(ev => {
                const meta = typeof ev.metadata === 'string' ? JSON.parse(ev.metadata) : (ev.metadata || {});
                const isGap = meta.undetermined || meta.source === 'sop_gap';
                const croppedUrl = meta.cropped_url;
                const duration = meta.duration_seconds;
                return (
                  <div
                    key={ev.id}
                    className={`flex gap-3 p-3 rounded-lg border transition ${isGap ? 'border-orange-300 dark:border-orange-800 bg-orange-50/10 hover:bg-orange-50/20 cursor-default' : 'border-gray-200 dark:border-gray-700 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 cursor-pointer'}`}
                    onClick={() => !isGap && seekTo(ev.timestamp)}
                  >
                    {ev.annotated_screenshot_url || croppedUrl || ev.screenshot_url ? (
                      <img src={ev.annotated_screenshot_url || croppedUrl || ev.screenshot_url} alt="" className="w-14 h-10 object-cover rounded shrink-0" />
                    ) : (
                      <div className="w-14 h-10 bg-gray-200 dark:bg-gray-700 rounded shrink-0 flex items-center justify-center text-xs text-gray-400 font-mono">
                        {isGap ? 'GAP' : (ev.frame_num ? `f${ev.frame_num}` : '—')}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-xs text-gray-900 dark:text-gray-100 truncate">{ev.detection_label?.replace(/-/g,' ')}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {isGap ? (
                          <span className="text-red-600 dark:text-red-400 font-semibold">SOP Compliance Gap (Whole Video)</span>
                        ) : (
                          `${fmtTs(ev.timestamp)}${ev.frame_num ? ` (Frame #${ev.frame_num})` : ''}`
                        )} · {ev.sop_section || 'No SOP match'}
                      </p>
                      <div className="flex flex-wrap gap-2 items-center text-xs text-gray-400 mt-0.5">
                        <span>
                          {isGap ? 'Undetermined conf' : (ev.confidence != null ? `${(ev.confidence*100).toFixed(0)}% conf` : '—')}
                        </span>
                        {(duration || isGap) && (
                          <>
                            <span>·</span>
                            <span className="text-orange-600 font-semibold">Duration: {(duration || 10.0).toFixed(1)}s</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
