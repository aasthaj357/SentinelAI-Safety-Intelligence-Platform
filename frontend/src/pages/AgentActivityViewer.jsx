import { useState, useEffect } from 'react';
import { useActiveProject } from '../context/ActiveProjectContext';
import axios from 'axios';
import { API_URL } from '../lib/constants';
import { CheckCircle2, AlertCircle, Loader2, Clock, ChevronDown, ChevronUp, Brain } from 'lucide-react';

export default function AgentActivityViewer() {
  const { activeProjectId, userId, isLoading } = useActiveProject();
  const [job, setJob] = useState(null);
  const [expandedAgent, setExpandedAgent] = useState(null);
  const [pollingActive, setPollingActive] = useState(true);

  const agentConfig = {
    'frame_extraction': { title: 'Frame Extraction Agent', desc: 'Extracts video frames every 0.5 seconds and stores them.', order: 1 },
    'object_detection': { title: 'Object Detection Agent', desc: 'Runs YOLO once across all frames to detect persons and tools.', order: 2 },
    'person_tracking': { title: 'Person Tracking Agent', desc: 'Groups person detections into persistent Worker IDs.', order: 3 },
    'ppe_association': { title: 'PPE Association Agent', desc: 'Determines worker compliance with PPE using overlap IoU.', order: 4 },
    'observation': { title: 'Observation Agent', desc: 'Generates factual frame-level safety observations.', order: 5 },
    'sop_parsing': { title: 'SOP Parsing Agent', desc: 'Extracts structured safety rules from the project SOP.', order: 6 },
    'compliance_auditor': { title: 'Compliance Auditor Agent', desc: 'Audits observations against SOP rules; skips empty records.', order: 7 },
    'evidence_builder': { title: 'Evidence Builder Agent', desc: 'Constructs verified evidence packages with strict assertions.', order: 8 },
    'annotation': { title: 'Annotation Agent', desc: 'Outlines violations and generates annotated screenshots.', order: 9 },
    'risk_assessment': { title: 'Risk Assessment Agent', desc: 'Calculates risk severity scores without inspecting video.', order: 10 },
    'incident_prediction': { title: 'Incident Prediction Agent', desc: 'Predicts high-risk incidents citing specific evidence.', order: 11 },
    'training_recommendation': { title: 'Training Recommendation Agent', desc: 'Recommends safety modules mapped to violations.', order: 12 }
  };

  const fetchLatestJob = async () => {
    if (!activeProjectId || !userId) return;
    try {
      const response = await axios.get(`${API_URL}/api/analysis/project/${activeProjectId}/latest?user_id=${userId}`);
      if (response.data) {
        setJob(response.data);
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setPollingActive(false);
        }
      } else {
        setJob(null);
      }
    } catch (err) {
      console.error("Failed to fetch latest job status:", err);
    }
  };

  useEffect(() => {
    let interval = null;
    if (!isLoading && activeProjectId && userId && pollingActive) {
      fetchLatestJob();
      interval = setInterval(fetchLatestJob, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, userId, isLoading, pollingActive]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'completed':
        return 'border-green-200 bg-green-50/50 dark:bg-green-950/20';
      case 'failed':
        return 'border-red-200 bg-red-50/50 dark:bg-red-950/20';
      case 'running':
        return 'border-blue-300 bg-blue-50/50 dark:bg-blue-950/20 animate-pulse';
      default:
        return 'border-gray-200 bg-white dark:bg-gray-800';
    }
  };

  const toggleExpand = (key) => {
    setExpandedAgent(expandedAgent === key ? null : key);
  };

  const restartTracking = () => {
    setPollingActive(true);
    fetchLatestJob();
  };

  // Build sequential list of agents with their current states
  const dbAgents = job?.result?.agents || {};
  const agentList = Object.keys(agentConfig).map(key => {
    const dbAgent = dbAgents[key] || {};
    return {
      key,
      title: agentConfig[key].title,
      desc: agentConfig[key].desc,
      order: agentConfig[key].order,
      status: dbAgent.status || 'waiting',
      output: dbAgent.output || null,
      error: dbAgent.error || null
    };
  });

  return (
    <div className="p-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Brain className="w-8 h-8 text-indigo-500" />
              Agent Activity Orchestrator
            </h1>
            <p className="text-gray-500 mt-2">
              Trace execution steps sequentially. Each downstream agent strictly consumes JSON output from prior stages.
            </p>
          </div>
          {job && (
            <button
              onClick={restartTracking}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded transition-colors text-sm"
            >
              Refresh Status
            </button>
          )}
        </div>

        {job ? (
          <div className="space-y-4">
            {/* Pipeline status card */}
            <div className="p-4 rounded-xl border bg-white dark:bg-gray-800 shadow-sm flex items-center justify-between mb-6">
              <div>
                <span className="text-xs text-gray-400 font-mono">JOB ID: {job.id}</span>
                <h3 className="font-bold text-lg text-gray-900 dark:text-white mt-1">
                  Workflow Status: <span className="capitalize text-indigo-600">{job.status}</span>
                </h3>
              </div>
              <div className="flex items-center gap-2">
                {job.status === 'processing' && (
                  <span className="flex h-3.5 w-3.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-blue-500"></span>
                  </span>
                )}
                <span className="text-sm font-semibold capitalize text-gray-500">{job.status}</span>
              </div>
            </div>

            {/* Steps line */}
            <div className="relative border-l border-gray-200 dark:border-gray-700 ml-4 pl-8 space-y-6">
              {agentList.map((agent) => {
                const isExpanded = expandedAgent === agent.key;
                const showOutputButton = agent.status === 'completed' || agent.error;

                return (
                  <div key={agent.key} className="relative">
                    {/* Circle icon */}
                    <div className="absolute -left-12 top-1.5 bg-white dark:bg-gray-900 rounded-full p-1 border">
                      {getStatusIcon(agent.status)}
                    </div>

                    <div className={`p-5 rounded-xl border shadow-sm transition-all duration-300 ${getStatusClass(agent.status)}`}>
                      <div className="flex justify-between items-start cursor-pointer" onClick={() => showOutputButton && toggleExpand(agent.key)}>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-bold px-2 py-0.5 rounded">
                              Step {agent.order}
                            </span>
                            <h3 className="font-bold text-gray-900 dark:text-white text-base">{agent.title}</h3>
                          </div>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{agent.desc}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className={`text-xs font-semibold capitalize px-2 py-0.5 rounded-full border
                              ${agent.status === 'completed' ? 'bg-green-100 text-green-800 border-green-200' :
                                agent.status === 'failed' ? 'bg-red-100 text-red-800 border-red-200' :
                                agent.status === 'running' ? 'bg-blue-100 text-blue-800 border-blue-200' :
                                'bg-gray-100 text-gray-800 border-gray-200'}`}
                            >
                              {agent.status}
                            </span>
                          </div>
                        </div>
                        {showOutputButton && (
                          <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                          </button>
                        )}
                      </div>

                      {/* Expandable output section */}
                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                          {agent.error ? (
                            <div className="bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-400 p-3 rounded text-xs font-mono whitespace-pre-wrap">
                              {agent.error}
                            </div>
                          ) : (
                            <div>
                              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2">JSON Output:</span>
                              <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-60 shadow-inner">
                                {JSON.stringify(agent.output, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-dashed">
            <Brain className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h3 className="font-semibold text-gray-700 dark:text-gray-300 text-lg">No active analysis pipeline</h3>
            <p className="text-gray-500 text-sm mt-1">Upload a workplace video on the Uploads tab to trigger the pipeline.</p>
          </div>
        )}
      </div>
    </div>
  );
}
