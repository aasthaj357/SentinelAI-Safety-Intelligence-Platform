-- Supabase Database Schema - SOP text and evidence record support

ALTER TABLE public.sop_documents
ADD COLUMN IF NOT EXISTS file_size BIGINT,
ADD COLUMN IF NOT EXISTS sop_text TEXT,
ADD COLUMN IF NOT EXISTS sop_structure JSONB;

CREATE TABLE IF NOT EXISTS public.evidence_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    video_id UUID REFERENCES public.video_uploads(id) ON DELETE CASCADE,
    violation_id UUID REFERENCES public.violation_tracking(id) ON DELETE CASCADE,
    risk_assessment_id UUID REFERENCES public.risk_assessments(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL DEFAULT 'video_violation',
    frame_num INTEGER,
    timestamp NUMERIC,
    detection_label TEXT,
    confidence NUMERIC,
    screenshot_url TEXT,
    sop_section TEXT,
    sop_excerpt TEXT,
    risk_reason TEXT,
    risk_score NUMERIC,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
