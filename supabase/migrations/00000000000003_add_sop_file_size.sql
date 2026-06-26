-- Add file size metadata to SOP documents for upload reporting and audit
ALTER TABLE public.sop_documents
ADD COLUMN IF NOT EXISTS file_size BIGINT;
