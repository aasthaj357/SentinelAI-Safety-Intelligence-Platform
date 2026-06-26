-- Supabase Database Schema - Phase 3 Extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create Knowledge Base table for RAG
CREATE TABLE public.knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL, -- e.g., 'sop', 'transcript', 'violation', 'risk', 'prediction', 'report', 'training'
    source_id UUID, -- Reference to the original record ID
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(384), -- Using sentence-transformers all-MiniLM-L6-v2 which outputs 384d vectors
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Index for similarity search
CREATE INDEX knowledge_base_embedding_idx ON public.knowledge_base USING hnsw (embedding vector_cosine_ops);

-- Create Training Recommendations table
CREATE TABLE public.training_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    priority TEXT NOT NULL, -- 'Critical', 'High', 'Medium', 'Low'
    recommendation_json JSONB NOT NULL,
    human_readable_summary TEXT NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- RPC for RAG similarity search
CREATE OR REPLACE FUNCTION match_knowledge (
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  p_project_id uuid
)
RETURNS TABLE (
  id uuid,
  project_id uuid,
  source_type text,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    k.id,
    k.project_id,
    k.source_type,
    k.content,
    k.metadata,
    1 - (k.embedding <=> query_embedding) AS similarity
  FROM public.knowledge_base k
  WHERE k.project_id = p_project_id
    AND 1 - (k.embedding <=> query_embedding) > match_threshold
  ORDER BY k.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
