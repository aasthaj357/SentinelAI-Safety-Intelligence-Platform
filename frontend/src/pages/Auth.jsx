import { useState } from 'react';
import { supabase } from '../lib/supabase';
import { 
  Shield, FileText, Cpu, AlertTriangle, MessageSquare, ArrowRight, Video, Lock, HelpCircle,
  Upload, Play, CheckCircle, TrendingUp, UserCheck, Activity, Sparkles, Plus, ChevronRight, Download
} from 'lucide-react';

export default function Auth() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [view, setView] = useState('login'); // 'login', 'signup', 'how-to-use'
  const [showPassword, setShowPassword] = useState(false);
  const [activeStep, setActiveStep] = useState(1);

  const validate = () => {
    if (!email.includes('@')) {
      setMessage({ text: 'Please enter a valid email address.', type: 'error' });
      return false;
    }
    if (password.length < 6) {
      setMessage({ text: 'Password must be at least 6 characters.', type: 'error' });
      return false;
    }
    if (view === 'signup' && password !== confirmPassword) {
      setMessage({ text: 'Passwords do not match.', type: 'error' });
      return false;
    }
    return true;
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setMessage({ text: '', type: '' });
    if (!validate()) return;

    setLoading(true);
    try {
      if (view === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        // onAuthStateChange in App.jsx will handle session + redirect
        window.location.href = '/';
      } else {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;

        if (data.session) {
          window.location.href = '/';
        } else {
          // Try immediate sign-in (works when email confirm is disabled)
          const { error: loginError } = await supabase.auth.signInWithPassword({ email, password });
          if (!loginError) {
            window.location.href = '/';
          } else {
            setMessage({
              text: '✅ Account created! Check your email to confirm, then sign in.',
              type: 'success',
            });
            setView('login');
          }
        }
      }
    } catch (err) {
      setMessage({ text: err.message || 'Authentication failed. Please try again.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    localStorage.setItem('demoSession', 'true');
    // Trigger a storage event so ActiveProjectContext picks it up
    window.dispatchEvent(new Event('storage'));
    window.location.href = '/';
  };

  const switchMode = () => {
    setView(view === 'login' ? 'signup' : 'login');
    setMessage({ text: '', type: '' });
    setPassword('');
    setConfirmPassword('');
  };

  if (view === 'how-to-use') {
    return (
      <div className="flex flex-col min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-indigo-950 px-6 py-20 lg:py-24 text-white items-center justify-center relative overflow-hidden">
        {/* Glow decorative effects */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none" />

        {/* Navigation header */}
        <div className="absolute top-6 left-6 right-6 flex justify-between items-center z-10">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-600 shadow-md">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-white font-bold text-lg tracking-tight">SafeGuard AI</span>
          </div>
          <button 
            onClick={() => setView('login')}
            className="text-sm font-semibold transition-all px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-750 text-white shadow-md flex items-center gap-1.5"
          >
            Sign In to Platform <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Content Container */}
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch mt-6 relative z-10">
          {/* Left panel: Step navigation */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
                Interactive Product Walkthrough
              </div>
              <h2 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
                How It <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">Works</span>
              </h2>
              <p className="text-gray-300 text-sm leading-relaxed">
                Click on each stage of the safety audit pipeline below to preview the interface and see how SafeGuard AI processes SOP compliance in real-time.
              </p>
            </div>

            {/* Stepper buttons */}
            <div className="space-y-4">
              {/* Step 1 */}
              <button 
                onClick={() => setActiveStep(1)}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-300 flex items-start gap-4 ${
                  activeStep === 1 
                    ? 'bg-indigo-600/10 border-indigo-500/50 shadow-indigo-500/5 shadow-lg' 
                    : 'bg-white/5 border-white/5 hover:bg-white/10'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shadow-md ${
                  activeStep === 1 ? 'bg-indigo-600 text-white' : 'bg-white/10 text-gray-400'
                }`}>
                  1
                </div>
                <div className="flex-1 space-y-1">
                  <h3 className="text-white font-semibold text-sm flex items-center gap-1.5">
                    <Video className="w-4 h-4 text-indigo-400" />
                    SOP & Video Ingestion
                  </h3>
                  <p className="text-gray-400 text-xs leading-relaxed">
                    Upload workplace safety SOP (PDF) and camera footage. Our pipeline automatically parses regulatory constraints.
                  </p>
                </div>
              </button>

              {/* Step 2 */}
              <button 
                onClick={() => setActiveStep(2)}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-300 flex items-start gap-4 ${
                  activeStep === 2 
                    ? 'bg-purple-600/10 border-purple-500/50 shadow-purple-500/5 shadow-lg' 
                    : 'bg-white/5 border-white/5 hover:bg-white/10'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shadow-md ${
                  activeStep === 2 ? 'bg-purple-600 text-white' : 'bg-white/10 text-gray-400'
                }`}>
                  2
                </div>
                <div className="flex-1 space-y-1">
                  <h3 className="text-white font-semibold text-sm flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-purple-400" />
                    AI Detection & Tracking
                  </h3>
                  <p className="text-gray-400 text-xs leading-relaxed">
                    YOLOv8 + Roboflow processes frames. Worker IDs are locked temporally to avoid over-counting and false alerts.
                  </p>
                </div>
              </button>

              {/* Step 3 */}
              <button 
                onClick={() => setActiveStep(3)}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-300 flex items-start gap-4 ${
                  activeStep === 3 
                    ? 'bg-pink-600/10 border-pink-500/50 shadow-pink-500/5 shadow-lg' 
                    : 'bg-white/5 border-white/5 hover:bg-white/10'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shadow-md ${
                  activeStep === 3 ? 'bg-pink-600 text-white' : 'bg-white/10 text-gray-400'
                }`}>
                  3
                </div>
                <div className="flex-1 space-y-1">
                  <h3 className="text-white font-semibold text-sm flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-pink-400" />
                    SOP Compliance Engine
                  </h3>
                  <p className="text-gray-400 text-xs leading-relaxed">
                    Violations are mapped frame-by-frame. A dynamic risk index is calculated for each work zone.
                  </p>
                </div>
              </button>

              {/* Step 4 */}
              <button 
                onClick={() => setActiveStep(4)}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-300 flex items-start gap-4 ${
                  activeStep === 4 
                    ? 'bg-emerald-600/10 border-emerald-500/50 shadow-emerald-500/5 shadow-lg' 
                    : 'bg-white/5 border-white/5 hover:bg-white/10'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shadow-md ${
                  activeStep === 4 ? 'bg-emerald-600 text-white' : 'bg-white/10 text-gray-400'
                }`}>
                  4
                </div>
                <div className="flex-1 space-y-1">
                  <h3 className="text-white font-semibold text-sm flex items-center gap-1.5">
                    <MessageSquare className="w-4 h-4 text-emerald-400" />
                    Safety Copilot & Reports
                  </h3>
                  <p className="text-gray-400 text-xs leading-relaxed">
                    Interact with Safety Copilot using natural language, view agent explainability traces, and export PDF audits.
                  </p>
                </div>
              </button>
            </div>

            <div className="text-gray-500 text-xs text-center lg:text-left">
              Click any step above to update the screenshot mockup. Perfect for Kaggle thumbnail capture.
            </div>
          </div>

          {/* Right side: Mockup Canvas */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[520px] transition-all duration-300">
              {/* Window header */}
              <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-rose-500" />
                  <span className="w-3 h-3 rounded-full bg-amber-500" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500" />
                </div>
                <div className="bg-slate-900 px-3 py-1 rounded-md text-[10px] text-gray-400 font-mono tracking-tight select-none">
                  {activeStep === 1 && "safeguard-ai://ingestion-portal"}
                  {activeStep === 2 && "safeguard-ai://cv-inference-viewer"}
                  {activeStep === 3 && "safeguard-ai://risk-compliance-scorecard"}
                  {activeStep === 4 && "safeguard-ai://copilot-dialogue"}
                </div>
                <div className="w-12" /> {/* spacer */}
              </div>

              {/* Window Body */}
              <div className="flex-1 p-6 overflow-y-auto bg-slate-950/50">
                {activeStep === 1 && (
                  <div className="space-y-6 h-full flex flex-col justify-center">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Upload className="w-5 h-5 text-indigo-400" />
                      Ingestion & Document Parser
                    </h3>
                    <div className="border border-dashed border-indigo-500/30 rounded-xl p-8 bg-indigo-500/5 text-center space-y-3">
                      <div className="w-12 h-12 rounded-full bg-indigo-600/20 flex items-center justify-center mx-auto">
                        <Upload className="w-6 h-6 text-indigo-400" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">Workspace Ingestion Successful</p>
                        <p className="text-xs text-gray-400">PDF SOP & video processed by AI Agents</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 flex items-center gap-3">
                        <FileText className="w-8 h-8 text-rose-400" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold truncate">construction_site_sop.pdf</p>
                          <p className="text-[10px] text-emerald-400 font-medium">✓ 12 Rules Extracted</p>
                        </div>
                      </div>
                      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 flex items-center gap-3">
                        <Video className="w-8 h-8 text-indigo-400" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold truncate">east_gate_camera.mp4</p>
                          <p className="text-[10px] text-emerald-400 font-medium">✓ Transcoded (1080p)</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeStep === 2 && (
                  <div className="space-y-4 h-full flex flex-col justify-between">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Cpu className="w-5 h-5 text-purple-400" />
                      AI Computer Vision Tracking
                    </h3>
                    
                    {/* Simulated video frame */}
                    <div className="bg-slate-950 rounded-xl border border-slate-800 flex-1 relative overflow-hidden flex items-center justify-center p-4">
                      {/* Grid lines overlay */}
                      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:3rem_3rem] opacity-20" />
                      
                      {/* Bounding Box 1 */}
                      <div className="absolute left-[5%] top-[15%] w-[38%] h-[70%] border-2 border-emerald-500 rounded-lg flex flex-col justify-between p-2 bg-emerald-500/5 animate-pulse">
                        <span className="bg-emerald-500 text-slate-950 font-bold font-mono text-[9px] px-1 py-0.5 rounded self-start">
                          WORKER #03 [COMPLIANT]
                        </span>
                        <div className="flex flex-col gap-1 text-[8px] font-mono text-emerald-300 bg-slate-950/80 p-1 rounded border border-emerald-500/20">
                          <div>HELMET: OK (94%)</div>
                          <div>VEST: OK (91%)</div>
                          <div>GLOVES: OK (89%)</div>
                        </div>
                      </div>

                      {/* Bounding Box 2 */}
                      <div className="absolute right-[5%] top-[20%] w-[38%] h-[65%] border-2 border-rose-500 rounded-lg flex flex-col justify-between p-2 bg-rose-500/5 animate-pulse">
                        <span className="bg-rose-500 text-white font-bold font-mono text-[9px] px-1 py-0.5 rounded self-start">
                          WORKER #04 [VIOLATION]
                        </span>
                        <div className="flex flex-col gap-1 text-[8px] font-mono text-rose-300 bg-slate-950/80 p-1 rounded border border-rose-500/20">
                          <div className="text-emerald-300">HELMET: OK (95%)</div>
                          <div className="text-rose-400 font-bold">GOGGLES: MISSING</div>
                          <div className="text-emerald-300">VEST: OK (92%)</div>
                        </div>
                      </div>
                      
                      <div className="absolute bottom-2 left-2 right-2 flex justify-between text-[10px] text-gray-500 font-mono">
                        <span>● RECORDING [EAST_GATE_CAM]</span>
                        <span>FPS: 30.0</span>
                      </div>
                    </div>
                  </div>
                )}

                {activeStep === 3 && (
                  <div className="space-y-6 h-full flex flex-col justify-between">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Shield className="w-5 h-5 text-pink-400" />
                      Compliance Audit & Scoring
                    </h3>

                    {/* Stats cards */}
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-center">
                        <p className="text-[10px] text-gray-400 font-medium">Compliance Rate</p>
                        <p className="text-2xl font-bold text-emerald-400 mt-1">86.4%</p>
                      </div>
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-center">
                        <p className="text-[10px] text-gray-400 font-medium">Active Risk Score</p>
                        <p className="text-2xl font-bold text-amber-400 mt-1">45%</p>
                      </div>
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-center">
                        <p className="text-[10px] text-gray-400 font-medium">Total Violations</p>
                        <p className="text-2xl font-bold text-rose-400 mt-1">2</p>
                      </div>
                    </div>

                    {/* Safety Timeline */}
                    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex-1 space-y-3 overflow-y-auto">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Live Incident log</p>
                      <div className="flex items-start gap-3 text-xs">
                        <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5" />
                        <div>
                          <p className="text-white font-medium">Eye Protection Violation (Worker #04)</p>
                          <p className="text-[10px] text-gray-500">10:14:22 | Zone C - Near Grinding Mill</p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 text-xs border-t border-slate-850 pt-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5" />
                        <div>
                          <p className="text-white font-medium">Helmet & Vest Verified (Worker #03)</p>
                          <p className="text-[10px] text-gray-500">10:12:05 | Zone A - Loading Dock</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeStep === 4 && (
                  <div className="space-y-4 h-full flex flex-col justify-between">
                    <div className="flex justify-between items-center">
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <MessageSquare className="w-5 h-5 text-emerald-400" />
                        Safety Copilot AI
                      </h3>
                      <button className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors">
                        <Download className="w-3.5 h-3.5" />
                        Export PDF Report
                      </button>
                    </div>

                    {/* Chat Area */}
                    <div className="flex-1 bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 justify-end overflow-y-auto">
                      <div className="bg-slate-850 rounded-lg p-2.5 max-w-[85%] self-end border border-slate-700/50 text-xs text-left">
                        <p className="text-gray-300 font-mono text-[9px] mb-1">USER (Auditor)</p>
                        Explain the violation details for Worker #04.
                      </div>
                      
                      <div className="bg-indigo-950/40 rounded-lg p-3 max-w-[85%] self-start border border-indigo-900/40 text-xs text-left">
                        <p className="text-indigo-400 font-semibold font-mono text-[9px] mb-1 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> COPILOT AGENT
                        </p>
                        Worker #04 failed to wear eye protection (goggles) at 10:14:22 in Zone C. This is a high-risk violation of **SOP Section 4.2: Machinery Protective Eyewear**.
                        <div className="mt-2 text-[10px] text-indigo-300 bg-indigo-950/60 p-1.5 rounded border border-indigo-900/20 font-mono text-left">
                          Source: construction_site_sop.pdf (p. 4)
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Window Footer */}
              <div className="bg-slate-950 px-6 py-3 border-t border-slate-800 flex justify-between items-center text-[10px] text-gray-500">
                <span>Multi-Agent Compliance Auditor</span>
                <span>Active Model: Roboflow-PPE-v9</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-indigo-950 px-6 py-12 relative overflow-hidden">
      {/* Decorative Glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-500/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-500/5 blur-[120px] rounded-full pointer-events-none" />

      {/* Top Navigation Bar */}
      <div className="absolute top-6 left-6 right-6 flex justify-between items-center z-10">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-600 shadow-md">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-bold text-lg tracking-tight">SafeGuard AI</span>
        </div>
        <button 
          onClick={() => setView('how-to-use')}
          className="text-xs lg:text-sm font-semibold transition-all px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-300 hover:text-white hover:bg-white/10 flex items-center gap-1.5"
        >
          <HelpCircle className="w-4 h-4 text-indigo-400" />
          How It Works
        </button>
      </div>

      <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-12 items-center mt-6">
        
        {/* Left Side: Aesthetic "How to Use" Platform Guide */}
        <div className="lg:col-span-7 text-left space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold uppercase tracking-wider mb-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            AI Safety Orchestration Agent
          </div>
          
          <h1 className="text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Workplace Safety <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
              Intelligence Platform
            </span>
          </h1>
          
          <p className="text-gray-300 text-sm lg:text-base max-w-xl leading-relaxed">
            A state-of-the-art computer vision and multi-agent reasoning system designed to automatically audit workplace PPE compliance, calculate risk scores, and prevent site incidents.
          </p>

          {/* Interactive Timeline of Steps */}
          <div className="relative pl-6 border-l-2 border-indigo-500/20 space-y-6 mt-8">
            
            {/* Step 1 */}
            <div className="relative group hover:translate-x-1 transition-transform duration-300">
              <span className="absolute -left-[37px] top-1.5 flex items-center justify-center w-7 h-7 rounded-full bg-indigo-600 border border-indigo-400 text-white shadow-lg text-xs font-bold">
                1
              </span>
              <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 shadow-xl hover:bg-white/10 transition-colors">
                <h3 className="text-white font-semibold text-sm flex items-center gap-2 mb-1.5">
                  <Video className="w-4 h-4 text-indigo-400" />
                  Upload SOP & Site Video
                </h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Provide your operational safety procedures in PDF format alongside active CCTV or work zone footage to begin analysis.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="relative group hover:translate-x-1 transition-transform duration-300">
              <span className="absolute -left-[37px] top-1.5 flex items-center justify-center w-7 h-7 rounded-full bg-purple-600 border border-purple-400 text-white shadow-lg text-xs font-bold">
                2
              </span>
              <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 shadow-xl hover:bg-white/10 transition-colors">
                <h3 className="text-white font-semibold text-sm flex items-center gap-2 mb-1.5">
                  <Cpu className="w-4 h-4 text-purple-400" />
                  AI Computer Vision Inference
                </h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  YOLOv8 assigns temporal IDs to workers to prevent track duplication, while Roboflow performs multi-label detection for helmets, gloves, goggles, masks, and vests.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="relative group hover:translate-x-1 transition-transform duration-300">
              <span className="absolute -left-[37px] top-1.5 flex items-center justify-center w-7 h-7 rounded-full bg-pink-600 border border-pink-400 text-white shadow-lg text-xs font-bold">
                3
              </span>
              <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 shadow-xl hover:bg-white/10 transition-colors">
                <h3 className="text-white font-semibold text-sm flex items-center gap-2 mb-1.5">
                  <Shield className="w-4 h-4 text-pink-400" />
                  Compliance SOP Audit & Scoring
                </h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Compliance agents check frames against PDF safety bounds, log violations, and update the dynamic risk index based on occurrence duration.
                </p>
              </div>
            </div>

            {/* Step 4 */}
            <div className="relative group hover:translate-x-1 transition-transform duration-300">
              <span className="absolute -left-[37px] top-1.5 flex items-center justify-center w-7 h-7 rounded-full bg-emerald-600 border border-emerald-400 text-white shadow-lg text-xs font-bold">
                4
              </span>
              <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 shadow-xl hover:bg-white/10 transition-colors">
                <h3 className="text-white font-semibold text-sm flex items-center gap-2 mb-1.5">
                  <MessageSquare className="w-4 h-4 text-emerald-400" />
                  Explainability & Copilot Reasoning
                </h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Review granular, agent-compiled decision traces and SOP citations for every exception. Interact directly with Safety Copilot to query insights.
                </p>
              </div>
            </div>

          </div>
        </div>

        {/* Right Side: Auth Card */}
        <div className="lg:col-span-5 w-full">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 border border-gray-100 dark:border-gray-700">
            {/* Logo / Brand */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-600 shadow-md mb-3">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                {view === 'login' ? 'Welcome back' : 'Create account'}
              </h2>
              <p className="text-gray-500 dark:text-gray-400 text-xs mt-1">
                Access your safety intelligence workspace
              </p>
            </div>

            <form onSubmit={handleAuth} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@company.com"
                  className="w-full px-3.5 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white placeholder-gray-400"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    autoComplete={view === 'login' ? 'current-password' : 'new-password'}
                    placeholder={view === 'login' ? '••••••••' : 'Minimum 6 characters'}
                    className="w-full px-3.5 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white placeholder-gray-400 pr-10"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              {view === 'signup' && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Confirm Password
                  </label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    autoComplete="new-password"
                    placeholder="Re-enter your password"
                    className={`w-full px-3.5 py-2 border rounded-lg shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white placeholder-gray-400 ${
                      confirmPassword && confirmPassword !== password
                        ? 'border-red-400 bg-red-50 dark:bg-red-900/20'
                        : 'border-gray-300 dark:border-gray-600'
                    }`}
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                  />
                  {confirmPassword && confirmPassword !== password && (
                    <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
                  )}
                </div>
              )}

              {message.text && (
                <div className={`p-3 text-sm rounded-lg flex items-start gap-2 ${
                  message.type === 'error'
                    ? 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800'
                    : 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800'
                }`}>
                  <span>{message.text}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || (view === 'signup' && confirmPassword && confirmPassword !== password)}
                className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-750 text-white font-semibold rounded-lg shadow-sm text-sm transition disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                    {view === 'login' ? 'Signing in...' : 'Creating account...'}
                  </span>
                ) : (
                  view === 'login' ? 'Sign in' : 'Create account'
                )}
              </button>

              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200 dark:border-gray-700" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 bg-white dark:bg-gray-800 text-gray-400">or</span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDemoLogin}
                className="w-full py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-750 hover:bg-gray-50 dark:hover:bg-gray-600 transition focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                🚀 Try Demo (no sign-up required)
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={switchMode}
                className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 font-medium"
              >
                {view === 'login' ? "Don't have an account? Sign up →" : '← Already have an account? Sign in'}
              </button>
            </div>
          </div>

          <p className="text-center text-xs text-gray-500 mt-6">
            Your data is private and encrypted. <br />Powered by Supabase Auth.
          </p>
        </div>

      </div>
    </div>
  );
}
