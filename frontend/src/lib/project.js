import { supabase } from './supabase';
import { getAuthUser } from './auth';
import { API_URL } from './constants';

export async function getOrCreateProject() {
  const { data: { user }, error } = await getAuthUser();
  if (error || !user) throw new Error('User not authenticated. Please sign in first.');

  const projectName = `Project-${user.id}`;
  const isDemo = localStorage.getItem('demoSession') !== null;

  if (isDemo) {
    try {
      const response = await fetch(`${API_URL}/api/demo/ensure-project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id, project_name: projectName }),
      });
      if (response.ok) {
        const data = await response.json();
        if (data.project_id) return data.project_id;
      }
    } catch (e) {
      console.warn('Backend ensure-project failed:', e);
    }
    throw new Error('Failed to create project via backend for demo user');
  }

  // Check for existing project
  const { data: existing } = await supabase
    .from('projects')
    .select('id')
    .eq('name', projectName)
    .eq('user_id', user.id)
    .maybeSingle();

  if (existing) return existing.id;

  // Try backend ensure-project endpoint (uses service role, bypasses RLS)
  try {
    const response = await fetch(`${API_URL}/api/demo/ensure-project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: user.id, project_name: projectName }),
    });
    if (response.ok) {
      const data = await response.json();
      if (data.project_id) return data.project_id;
    }
  } catch (e) {
    console.warn('Backend ensure-project failed, trying direct insert:', e);
  }

  // Direct Supabase insert (requires user to be authenticated + RLS allows it)
  const { data: newProject, error: insertError } = await supabase
    .from('projects')
    .insert([{ name: projectName, user_id: user.id }])
    .select('id')
    .single();

  if (insertError) throw new Error(`Failed to create project: ${insertError.message}`);
  return newProject.id;
}

export async function getProjectId() {
  const { data: { user }, error } = await getAuthUser();
  if (error || !user) return null;

  const isDemo = localStorage.getItem('demoSession') !== null;
  if (isDemo) {
    try {
      return await getOrCreateProject();
    } catch {
      return null;
    }
  }

  const { data: project } = await supabase
    .from('projects')
    .select('id')
    .eq('name', `Project-${user.id}`)
    .eq('user_id', user.id)
    .maybeSingle();

  return project?.id ?? null;
}

export async function ensureActiveProject() {
  return await getOrCreateProject();
}

