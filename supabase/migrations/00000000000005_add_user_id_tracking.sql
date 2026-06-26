-- Supabase Database Schema - User ID Tracking for Multi-User Support

-- Add user_id to projects table (optional for backward compatibility with single-user projects)
ALTER TABLE public.projects
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to violation_tracking (link violations to users)
ALTER TABLE public.violation_tracking
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to evidence_records (link evidence to users)
ALTER TABLE public.evidence_records
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to risk_assessments (link risk assessments to users)
ALTER TABLE public.risk_assessments
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to knowledge_base (link KB entries to users)
ALTER TABLE public.knowledge_base
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to training_recommendations (link training to users)
ALTER TABLE public.training_recommendations
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to generated_reports (link reports to users)
ALTER TABLE public.generated_reports
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to video_uploads (link videos to users)
ALTER TABLE public.video_uploads
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to sop_documents (link SOPs to users)
ALTER TABLE public.sop_documents
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to analysis_jobs (link analysis jobs to users)
ALTER TABLE public.analysis_jobs
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to chatbot_conversations (link conversations to users)
ALTER TABLE public.chatbot_conversations
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Create indexes on user_id columns for faster queries
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_video_uploads_user_id ON public.video_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_violation_tracking_user_id ON public.violation_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_records_user_id ON public.evidence_records(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_user_id ON public.risk_assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_user_id ON public.knowledge_base(user_id);
CREATE INDEX IF NOT EXISTS idx_training_recommendations_user_id ON public.training_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_user_id ON public.generated_reports(user_id);

-- Future: Add RLS policies for user-level data isolation
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.projects TO authenticated;
-- ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY user_projects ON public.projects FOR ALL USING (auth.uid() = user_id);
