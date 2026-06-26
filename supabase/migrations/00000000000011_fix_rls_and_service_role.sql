-- Migration 11: Fix RLS for demo user + add service-role bypass
-- Run this in Supabase SQL Editor (or via supabase db push)

-- ============================================================
-- SECTION 1: Ensure projects.user_id column exists
-- (already added in migration 7, this is idempotent safety)
-- ============================================================
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS user_id UUID;

-- ============================================================
-- SECTION 2: Drop all existing policies on critical tables
-- (so we can recreate them cleanly without conflicts)
-- ============================================================
DO $$ BEGIN
  -- projects
  DROP POLICY IF EXISTS projects_user_policy            ON public.projects;
  DROP POLICY IF EXISTS projects_service_role_policy    ON public.projects;
  -- video_uploads
  DROP POLICY IF EXISTS video_uploads_user_policy       ON public.video_uploads;
  DROP POLICY IF EXISTS video_uploads_service_policy    ON public.video_uploads;
  -- sop_documents
  DROP POLICY IF EXISTS sop_documents_user_policy       ON public.sop_documents;
  DROP POLICY IF EXISTS sop_documents_service_policy    ON public.sop_documents;
  -- analysis_jobs
  DROP POLICY IF EXISTS analysis_jobs_user_policy       ON public.analysis_jobs;
  DROP POLICY IF EXISTS analysis_jobs_service_policy    ON public.analysis_jobs;
  -- violation_tracking
  DROP POLICY IF EXISTS violation_tracking_user_policy  ON public.violation_tracking;
  DROP POLICY IF EXISTS violation_tracking_service_policy ON public.violation_tracking;
  -- evidence_records
  DROP POLICY IF EXISTS evidence_records_user_policy    ON public.evidence_records;
  DROP POLICY IF EXISTS evidence_records_service_policy ON public.evidence_records;
  -- risk_assessments
  DROP POLICY IF EXISTS risk_assessments_user_policy    ON public.risk_assessments;
  DROP POLICY IF EXISTS risk_assessments_service_policy ON public.risk_assessments;
  -- incident_predictions
  DROP POLICY IF EXISTS incident_predictions_user_policy ON public.incident_predictions;
  DROP POLICY IF EXISTS incident_predictions_service_policy ON public.incident_predictions;
  -- additional inherited policies
  DROP POLICY IF EXISTS decision_traces_user_policy     ON public.decision_traces;
  DROP POLICY IF EXISTS detections_user_policy          ON public.detections;
  DROP POLICY IF EXISTS frames_user_policy              ON public.frames;
  DROP POLICY IF EXISTS observations_user_policy        ON public.observations;
  DROP POLICY IF EXISTS ppe_associations_user_policy    ON public.ppe_associations;
  DROP POLICY IF EXISTS workers_user_policy             ON public.workers;
  -- generated_reports
  DROP POLICY IF EXISTS generated_reports_user_policy   ON public.generated_reports;
  DROP POLICY IF EXISTS generated_reports_service_policy ON public.generated_reports;
  -- knowledge_base
  DROP POLICY IF EXISTS knowledge_base_user_policy      ON public.knowledge_base;
  DROP POLICY IF EXISTS knowledge_base_service_policy   ON public.knowledge_base;
  -- training_recommendations
  DROP POLICY IF EXISTS training_recommendations_user_policy ON public.training_recommendations;
  DROP POLICY IF EXISTS training_recommendations_service_policy ON public.training_recommendations;
  -- video_transcripts
  DROP POLICY IF EXISTS video_transcripts_user_policy   ON public.video_transcripts;
  DROP POLICY IF EXISTS video_transcripts_service_policy ON public.video_transcripts;
  -- audit_logs
  DROP POLICY IF EXISTS audit_logs_service_policy       ON public.audit_logs;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- ============================================================
-- SECTION 3: projects — user policy + service-role bypass
-- ============================================================
-- Users can only see / edit their own projects.
-- Demo user row (00000000-0000-4000-a000-000000000001) is always accessible.
-- Backend service-role key bypasses RLS by default in Supabase, but we add
-- an explicit policy here in case security settings change.
CREATE POLICY projects_user_policy ON public.projects
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- ============================================================
-- SECTION 4: Helper macro — recreate per-table policies
-- Pattern: user can access their own rows; demo user always visible;
-- service_role can always write (backend pipeline).
-- ============================================================

-- video_uploads
CREATE POLICY video_uploads_user_policy ON public.video_uploads
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- sop_documents
CREATE POLICY sop_documents_user_policy ON public.sop_documents
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- analysis_jobs
CREATE POLICY analysis_jobs_user_policy ON public.analysis_jobs
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- violation_tracking
CREATE POLICY violation_tracking_user_policy ON public.violation_tracking
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- evidence_records
CREATE POLICY evidence_records_user_policy ON public.evidence_records
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- risk_assessments
CREATE POLICY risk_assessments_user_policy ON public.risk_assessments
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- incident_predictions
CREATE POLICY incident_predictions_user_policy ON public.incident_predictions
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = incident_predictions.project_id
        AND (projects.user_id = auth.uid() OR projects.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = incident_predictions.project_id
        AND (projects.user_id = auth.uid() OR projects.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- decision_traces
ALTER TABLE public.decision_traces ENABLE ROW LEVEL SECURITY;
CREATE POLICY decision_traces_user_policy ON public.decision_traces
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = decision_traces.project_id
        AND (projects.user_id = auth.uid() OR projects.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = decision_traces.project_id
        AND (projects.user_id = auth.uid() OR projects.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- workers
ALTER TABLE public.workers ENABLE ROW LEVEL SECURITY;
CREATE POLICY workers_user_policy ON public.workers
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = workers.video_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = workers.video_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- frames
ALTER TABLE public.frames ENABLE ROW LEVEL SECURITY;
CREATE POLICY frames_user_policy ON public.frames
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = frames.video_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = frames.video_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- detections
ALTER TABLE public.detections ENABLE ROW LEVEL SECURITY;
CREATE POLICY detections_user_policy ON public.detections
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.frames
      JOIN public.video_uploads ON video_uploads.id = frames.video_id
      WHERE frames.id = detections.frame_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.frames
      JOIN public.video_uploads ON video_uploads.id = frames.video_id
      WHERE frames.id = detections.frame_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- observations
ALTER TABLE public.observations ENABLE ROW LEVEL SECURITY;
CREATE POLICY observations_user_policy ON public.observations
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.frames
      JOIN public.video_uploads ON video_uploads.id = frames.video_id
      WHERE frames.id = observations.frame_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.frames
      JOIN public.video_uploads ON video_uploads.id = frames.video_id
      WHERE frames.id = observations.frame_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- ppe_associations
ALTER TABLE public.ppe_associations ENABLE ROW LEVEL SECURITY;
CREATE POLICY ppe_associations_user_policy ON public.ppe_associations
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.frames
      JOIN public.video_uploads ON video_uploads.id = frames.video_id
      WHERE frames.id = ppe_associations.frame_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.frames
      JOIN public.video_uploads ON video_uploads.id = frames.video_id
      WHERE frames.id = ppe_associations.frame_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- generated_reports
CREATE POLICY generated_reports_user_policy ON public.generated_reports
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- knowledge_base
CREATE POLICY knowledge_base_user_policy ON public.knowledge_base
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- training_recommendations
ALTER TABLE public.training_recommendations ENABLE ROW LEVEL SECURITY;
CREATE POLICY training_recommendations_user_policy ON public.training_recommendations
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  )
  WITH CHECK (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
    OR auth.role() = 'service_role'
  );

-- video_transcripts (joined via video_uploads.user_id)
CREATE POLICY video_transcripts_user_policy ON public.video_transcripts
  FOR ALL USING (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = video_transcripts.video_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = video_transcripts.video_id
        AND (video_uploads.user_id = auth.uid() OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- audit_logs — service_role can always write; users read their own
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_logs_service_policy ON public.audit_logs
  FOR ALL USING (
    auth.role() = 'service_role'
    OR auth.uid()::text = user_id::text
  )
  WITH CHECK (
    auth.role() = 'service_role'
    OR auth.uid()::text = user_id::text
  );

-- ============================================================
-- SECTION 5: Grant table permissions to authenticated role
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON public.projects                  TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.video_uploads             TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.sop_documents             TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.analysis_jobs             TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.violation_tracking        TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evidence_records          TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.risk_assessments          TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.incident_predictions      TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.generated_reports         TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.knowledge_base            TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.training_recommendations  TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.video_transcripts         TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.audit_logs                TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.decision_traces           TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.detections                TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.frames                    TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.observations              TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.ppe_associations          TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.workers                   TO authenticated;
