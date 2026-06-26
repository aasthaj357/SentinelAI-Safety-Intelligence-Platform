-- Migration 8: Add missing columns for full pipeline persistence

-- violation_tracking: add metadata JSONB for worker_id, duration, bbox etc.
ALTER TABLE public.violation_tracking
  ADD COLUMN IF NOT EXISTS metadata JSONB;

-- analysis_jobs: ensure user_id exists (already in migration 5 but belt-and-suspenders)
ALTER TABLE public.analysis_jobs
  ADD COLUMN IF NOT EXISTS user_id UUID;

-- knowledge_base: ensure user_id and metadata columns exist
ALTER TABLE public.knowledge_base
  ADD COLUMN IF NOT EXISTS user_id UUID,
  ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Indexes for new columns
CREATE INDEX IF NOT EXISTS idx_violation_tracking_metadata ON public.violation_tracking USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_evidence_records_video_id ON public.evidence_records(video_id);
CREATE INDEX IF NOT EXISTS idx_evidence_records_violation_id ON public.evidence_records(violation_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_id ON public.analysis_jobs(user_id);
