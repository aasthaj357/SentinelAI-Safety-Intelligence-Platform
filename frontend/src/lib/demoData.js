import { getAuthUser } from './auth';
import { API_URL } from './constants';
import { getOrCreateProject } from './project';

// This will be called from a component with context access
// For now, we store the flag and reset it after navigation
export const loadDemoData = async () => {
  try {
    const { data: { user }, error: authError } = await getAuthUser();
    if (authError || !user) throw new Error('Authentication required to load demo data. Please log in.');

    const projectId = await getOrCreateProject();

    // Set as active project in localStorage before reload
    localStorage.setItem('activeProjectId', projectId);
    localStorage.setItem('userId', user.id);

    const response = await fetch(`${API_URL}/api/demo/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, user_id: user.id }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || data.message || `Server returned ${response.status}`);
    }

    alert('Demo data loaded successfully!');
    window.location.reload();
  } catch (error) {
    console.error('Error loading demo data:', error);
    alert(`Failed to load demo data: ${error.message}`);
  }
};

export const resetDemoData = async () => {
  try {
    const { data: { user } } = await getAuthUser();
    if (!user) return;

    const projectId = await getOrCreateProject();

    const response = await fetch(`${API_URL}/api/demo/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, user_id: user.id }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.message || `Server returned ${response.status}`);
    }

    // Keep the active project set
    localStorage.setItem('activeProjectId', projectId);
    localStorage.setItem('userId', user.id);

    alert('Project data reset.');
    window.location.reload();
  } catch (error) {
    console.error('Error resetting demo data:', error);
    alert(`Failed to reset demo data: ${error.message}`);
  }
};
