import { useState, useRef } from 'react';
import { getOrCreateProject } from '../lib/project';
import { useActiveProject } from '../context/ActiveProjectContext';
import { API_URL } from '../lib/constants';
import { supabase } from '../lib/supabase';
import { UploadCloud, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const FileUploader = ({
  title,
  accept,
  allowedExtensions,
  onUpload,
  status,
  progress,
  error,
  successMessage,
  fileTypeLabel,
  colorClass,
}) => {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState('');
  const inputRef = useRef(null);

  const validateFile = (selectedFile) => {
    setValidationError('');
    if (!selectedFile) return false;

    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      setValidationError(`Invalid file type. Allowed: ${allowedExtensions.join(', ')}`);
      return false;
    }
    return true;
  };

  const formatFileSize = (bytes) => {
    if (!bytes && bytes !== 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
      }
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
      }
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) {
      setValidationError('Please select a file first.');
      return;
    }
    if (validateFile(file)) {
      onUpload(file);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col h-full">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">{title}</h2>

      <form onSubmit={handleSubmit} className="flex flex-col flex-grow">
        <div
          className={`relative flex-grow flex flex-col items-center justify-center p-8 mb-4 border-2 border-dashed rounded-lg transition-colors cursor-pointer
            ${dragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}
            ${status === 'uploading' ? 'opacity-50 pointer-events-none' : ''}
          `}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input ref={inputRef} type="file" accept={accept} onChange={handleChange} className="hidden" />

          {file ? (
            <div className="text-center">
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[250px]">{file.name}</p>
              <p className="text-xs text-gray-500 mt-1">{formatFileSize(file.size)}</p>
            </div>
          ) : (
            <div className="text-center flex flex-col items-center">
              <UploadCloud className="w-10 h-10 text-gray-400 mb-3" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Drag and drop or click to browse</p>
              <p className="text-xs text-gray-500 mt-1">Supported formats: {allowedExtensions.join(', ')}</p>
            </div>
          )}
        </div>

        {validationError && (
          <div className="mb-4 text-sm text-red-600 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4" />
            <span>{validationError}</span>
          </div>
        )}

        {error && (
          <div className="mb-4 text-sm text-red-600 flex items-start gap-1.5 p-3 bg-red-50 dark:bg-red-900/20 rounded">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span className="break-words">{error}</span>
          </div>
        )}

        {status === 'success' && (
          <div className="mb-4 text-sm text-green-600 flex items-start gap-1.5 p-3 bg-green-50 dark:bg-green-900/20 rounded">
            <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>{successMessage}</div>
          </div>
        )}

        {status === 'uploading' && (
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
              <span>Uploading...</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 overflow-hidden">
              <div className={`h-2.5 rounded-full ${colorClass}`} style={{ width: `${progress}%` }}></div>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={!file || status === 'uploading'}
          className={`mt-auto w-full font-medium py-2 px-4 rounded transition-colors flex items-center justify-center gap-2 ${colorClass} hover:opacity-90 text-white disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {status === 'uploading' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </>
          ) : (
            `Upload ${fileTypeLabel}`
          )}
        </button>
      </form>
    </div>
  );
};

export default function Uploads() {
  const { activeProjectId, userId, setProject, refreshActiveJob } = useActiveProject();
  const [videoStatus, setVideoStatus] = useState('idle');
  const [videoProgress, setVideoProgress] = useState(0);
  const [videoError, setVideoError] = useState('');
  const [analysisStatus, setAnalysisStatus] = useState('');

  const [sopStatus, setSopStatus] = useState('idle');
  const [sopProgress, setSopProgress] = useState(0);
  const [sopError, setSopError] = useState('');
  const [sopFileSize, setSopFileSize] = useState(null);

  const uploadViaBackend = async (endpoint, file, projectId, uid, onProgress) => {
    // Get the current session token so the backend can optionally validate it
    let authToken = null;
    try {
      if (!localStorage.getItem('demoSession')) {
        const { data: { session } } = await supabase.auth.getSession();
        authToken = session?.access_token || null;
      }
    } catch { /* non-fatal */ }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    formData.append('user_id', uid);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress((e.loaded / e.total) * 100);
        }
      });
      xhr.addEventListener('load', () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
          } else {
            reject(new Error(data.detail || data.message || `Upload failed (${xhr.status})`));
          }
        } catch {
          reject(new Error(`Upload failed (${xhr.status}): ${xhr.responseText?.slice(0, 200)}`));
        }
      });
      xhr.addEventListener('error', () => {
        // Connection-level failure — backend is likely not running or unreachable.
        const url = `${API_URL}${endpoint}`;
        reject(new Error(
          `Cannot reach backend at ${url}. ` +
          `Make sure the backend is running: cd backend && uvicorn app.main:app --reload\n` +
          `Then open http://localhost:8000/health to confirm it is up.`
        ));
      });
      xhr.open('POST', `${API_URL}${endpoint}`);
      if (authToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${authToken}`);
      }
      xhr.send(formData);
    });
  };

  const handleVideoUpload = async (file) => {
    setVideoStatus('uploading');
    setVideoError('');
    setAnalysisStatus('');
    setVideoProgress(0);

    try {
      let projectId = activeProjectId;
      if (!projectId) {
        projectId = await getOrCreateProject();
        setProject(projectId);
      }
      const result = await uploadViaBackend('/api/upload/video', file, projectId, userId, setVideoProgress);

      setVideoProgress(100);
      setVideoStatus('success');
      setAnalysisStatus(
        `Analysis job ${result.job_id} queued. YOLOv8 + PPE pipeline is processing the video.`
      );
      
      // Trigger context update to kick off active polling
      await refreshActiveJob();
    } catch (err) {
      console.error(err);
      setVideoProgress(0);
      setVideoError(err.message || 'An unexpected error occurred.');
      setVideoStatus('error');
    }
  };

  const handleSopUpload = async (file) => {
    setSopStatus('uploading');
    setSopError('');
    setSopProgress(0);
    setSopFileSize(null);

    try {
      let projectId = activeProjectId;
      if (!projectId) {
        projectId = await getOrCreateProject();
        setProject(projectId);
      }
      const result = await uploadViaBackend('/api/upload/sop', file, projectId, userId, setSopProgress);
      const sizeInBytes = result?.file_size ?? file.size;

      setSopFileSize(sizeInBytes);
      setSopProgress(100);
      setSopStatus('success');
      
      // Trigger context update
      await refreshActiveJob();
    } catch (err) {
      console.error(err);
      setSopProgress(0);
      setSopError(err.message || 'An unexpected error occurred.');
      setSopStatus('error');
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">Upload Documents & Media</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <FileUploader
            title="Upload Workplace Video"
            accept="video/mp4,video/quicktime,video/x-msvideo,video/webm"
            allowedExtensions={['mp4', 'mov', 'avi', 'webm']}
            onUpload={handleVideoUpload}
            status={videoStatus}
            progress={videoProgress}
            error={videoError}
            successMessage={
              <div className="flex flex-col">
                <span className="font-semibold text-gray-900 dark:text-gray-100">Video uploaded successfully.</span>
                {analysisStatus && <span className="text-xs text-gray-600 dark:text-gray-300 mt-1">{analysisStatus}</span>}
              </div>
            }
            fileTypeLabel="Video"
            colorClass="bg-blue-600"
          />

          <FileUploader
            title="Upload SOP Document"
            accept="application/pdf"
            allowedExtensions={['pdf']}
            onUpload={handleSopUpload}
            status={sopStatus}
            progress={sopProgress}
            error={sopError}
            successMessage={
              <div className="flex flex-col">
                <span className="font-semibold text-gray-900 dark:text-gray-100">SOP document uploaded successfully.</span>
                {sopFileSize !== null && (
                  <span className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                    Stored file size: {sopFileSize < 1024 ? `${sopFileSize} B` : sopFileSize < 1024 * 1024 ? `${(sopFileSize / 1024).toFixed(1)} KB` : `${(sopFileSize / (1024 * 1024)).toFixed(2)} MB`}
                  </span>
                )}
              </div>
            }
            fileTypeLabel="SOP"
            colorClass="bg-green-600"
          />
        </div>
      </div>
    </div>
  );
}
