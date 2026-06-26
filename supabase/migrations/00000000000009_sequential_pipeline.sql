-- Migration 9: Strict Sequential Agentic Pipeline Schema

-- Create frames table
CREATE TABLE IF NOT EXISTS public.frames (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES public.video_uploads(id) ON DELETE CASCADE,
    frame_number INTEGER NOT NULL,
    timestamp NUMERIC NOT NULL,
    image_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Create workers table
CREATE TABLE IF NOT EXISTS public.workers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES public.video_uploads(id) ON DELETE CASCADE,
    worker_label TEXT NOT NULL, -- e.g., 'Worker_1', 'Worker_2'
    track_id INTEGER,           -- YOLO track ID
    start_frame INTEGER,
    end_frame INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Create detections table
CREATE TABLE IF NOT EXISTS public.detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    frame_id UUID REFERENCES public.frames(id) ON DELETE CASCADE,
    class_name TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    bbox JSONB NOT NULL,        -- [x1, y1, x2, y2]
    track_id INTEGER,
    worker_id UUID REFERENCES public.workers(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Create ppe_associations table
CREATE TABLE IF NOT EXISTS public.ppe_associations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID REFERENCES public.workers(id) ON DELETE CASCADE,
    frame_id UUID REFERENCES public.frames(id) ON DELETE CASCADE,
    timestamp NUMERIC NOT NULL,
    helmet BOOLEAN NOT NULL DEFAULT false,
    gloves BOOLEAN NOT NULL DEFAULT false,
    goggles BOOLEAN NOT NULL DEFAULT false,
    mask BOOLEAN NOT NULL DEFAULT false,
    vest BOOLEAN NOT NULL DEFAULT false,
    shoes BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Create observations table
CREATE TABLE IF NOT EXISTS public.observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    frame_id UUID REFERENCES public.frames(id) ON DELETE CASCADE,
    worker_id UUID REFERENCES public.workers(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    timestamp NUMERIC NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Add foreign keys and new columns to existing tables for trace-level tracking
ALTER TABLE public.violation_tracking
ADD COLUMN IF NOT EXISTS frame_id UUID REFERENCES public.frames(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS worker_id UUID REFERENCES public.workers(id) ON DELETE CASCADE;

ALTER TABLE public.evidence_records
ADD COLUMN IF NOT EXISTS frame_id UUID REFERENCES public.frames(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS worker_id UUID REFERENCES public.workers(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS annotated_screenshot_url TEXT;

ALTER TABLE public.training_recommendations
ADD COLUMN IF NOT EXISTS worker_id UUID REFERENCES public.workers(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS evidence_id UUID REFERENCES public.evidence_records(id) ON DELETE CASCADE;

ALTER TABLE public.risk_assessments
ADD COLUMN IF NOT EXISTS video_id UUID REFERENCES public.video_uploads(id) ON DELETE CASCADE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_frames_video_id ON public.frames(video_id);
CREATE INDEX IF NOT EXISTS idx_workers_video_id ON public.workers(video_id);
CREATE INDEX IF NOT EXISTS idx_detections_frame_id ON public.detections(frame_id);
CREATE INDEX IF NOT EXISTS idx_detections_worker_id ON public.detections(worker_id);
CREATE INDEX IF NOT EXISTS idx_ppe_associations_worker_id ON public.ppe_associations(worker_id);
CREATE INDEX IF NOT EXISTS idx_ppe_associations_frame_id ON public.ppe_associations(frame_id);
CREATE INDEX IF NOT EXISTS idx_observations_frame_id ON public.observations(frame_id);
CREATE INDEX IF NOT EXISTS idx_observations_worker_id ON public.observations(worker_id);
CREATE INDEX IF NOT EXISTS idx_violation_tracking_frame_id ON public.violation_tracking(frame_id);
CREATE INDEX IF NOT EXISTS idx_violation_tracking_worker_id ON public.violation_tracking(worker_id);
CREATE INDEX IF NOT EXISTS idx_evidence_records_frame_id ON public.evidence_records(frame_id);
CREATE INDEX IF NOT EXISTS idx_evidence_records_worker_id ON public.evidence_records(worker_id);
CREATE INDEX IF NOT EXISTS idx_training_recommendations_worker_id ON public.training_recommendations(worker_id);
CREATE INDEX IF NOT EXISTS idx_training_recommendations_evidence_id ON public.training_recommendations(evidence_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_video_id ON public.risk_assessments(video_id);
