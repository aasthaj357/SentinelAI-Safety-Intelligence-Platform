-- Migration: Add project_id and user_id to remaining tables for strict isolation

-- 1. violation_tracking: add project_id (it already has video_id, but project_id simplifies filtering)
ALTER TABLE public.violation_tracking
ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;

-- 2. analysis_jobs: add project_id and user_id
ALTER TABLE public.analysis_jobs
ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;

-- 3. incident_predictions: add user_id (it already has project_id)
ALTER TABLE public.incident_predictions
ADD COLUMN IF NOT EXISTS user_id UUID;

-- 4. generated_reports: ensure it has both (it should from migration 5, but double checking)
-- Migration 5 already added user_id to generated_reports.

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_violation_tracking_project_id ON public.violation_tracking(project_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_project_id ON public.analysis_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_incident_predictions_user_id ON public.incident_predictions(user_id);
