-- Migration to add a unique constraint on public.projects for (name, user_id) to prevent duplicate projects.
-- Note: Run migrate_duplicates.py to resolve existing duplicate rows before applying this constraint.

ALTER TABLE public.projects ADD CONSTRAINT unique_project_name_user_id UNIQUE (name, user_id);
