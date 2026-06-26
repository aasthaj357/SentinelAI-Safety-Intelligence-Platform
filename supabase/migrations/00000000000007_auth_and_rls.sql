-- Migration 7: Add user_id to projects and enable RLS for real user auth

-- 1. Add user_id to projects (if not already there)
ALTER TABLE public.projects
  ADD COLUMN IF NOT EXISTS user_id UUID;

-- 2. Create index for performance
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);

-- 3. Enable RLS on all tables
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.video_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sop_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.violation_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.incident_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.video_transcripts ENABLE ROW LEVEL SECURITY;

-- 4. Drop old policies if they exist (idempotent)
DO $$ BEGIN
  DROP POLICY IF EXISTS projects_user_policy ON public.projects;
  DROP POLICY IF EXISTS video_uploads_user_policy ON public.video_uploads;
  DROP POLICY IF EXISTS sop_documents_user_policy ON public.sop_documents;
  DROP POLICY IF EXISTS violation_tracking_user_policy ON public.violation_tracking;
  DROP POLICY IF EXISTS risk_assessments_user_policy ON public.risk_assessments;
  DROP POLICY IF EXISTS incident_predictions_user_policy ON public.incident_predictions;
  DROP POLICY IF EXISTS evidence_records_user_policy ON public.evidence_records;
  DROP POLICY IF EXISTS generated_reports_user_policy ON public.generated_reports;
  DROP POLICY IF EXISTS analysis_jobs_user_policy ON public.analysis_jobs;
  DROP POLICY IF EXISTS knowledge_base_user_policy ON public.knowledge_base;
  DROP POLICY IF EXISTS video_transcripts_user_policy ON public.video_transcripts;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- 5. RLS policies: users see only their own rows
-- Also allow the DEMO_USER_ID to be accessed from the service role (backend uses service role key)

CREATE POLICY projects_user_policy ON public.projects
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY video_uploads_user_policy ON public.video_uploads
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY sop_documents_user_policy ON public.sop_documents
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY violation_tracking_user_policy ON public.violation_tracking
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY risk_assessments_user_policy ON public.risk_assessments
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY incident_predictions_user_policy ON public.incident_predictions
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY evidence_records_user_policy ON public.evidence_records
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY generated_reports_user_policy ON public.generated_reports
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY analysis_jobs_user_policy ON public.analysis_jobs
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

CREATE POLICY knowledge_base_user_policy ON public.knowledge_base
  FOR ALL USING (
    auth.uid() = user_id
    OR user_id = '00000000-0000-4000-a000-000000000001'::uuid
  );

-- video_transcripts join via video_uploads — allow if matching video upload's user
CREATE POLICY video_transcripts_user_policy ON public.video_transcripts
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.video_uploads
      WHERE video_uploads.id = video_transcripts.video_id
        AND (video_uploads.user_id = auth.uid()
             OR video_uploads.user_id = '00000000-0000-4000-a000-000000000001'::uuid)
    )
  );

-- 6. Service role bypass: backend uses SUPABASE_SERVICE_ROLE_KEY which bypasses RLS by default.
--    No additional grants needed for service role.

-- 7. Grant anon/authenticated users access to tables
GRANT SELECT, INSERT, UPDATE, DELETE ON public.projects TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.video_uploads TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.sop_documents TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.violation_tracking TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.risk_assessments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.incident_predictions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evidence_records TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.generated_reports TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.analysis_jobs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.knowledge_base TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.video_transcripts TO authenticated;
