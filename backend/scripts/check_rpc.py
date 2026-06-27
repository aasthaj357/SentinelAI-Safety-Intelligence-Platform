import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

try:
    res = supabase.rpc('match_knowledge', {
        'query_embedding': [0.1]*384,
        'match_threshold': 0.3,
        'match_count': 5,
        'p_project_id': 'test'
    }).execute()
    print("RPC exists:", res.data)
except Exception as e:
    print("RPC Error:", e)

    print("Attempting to create RPC...")
    sql = """
    create or replace function match_knowledge (
      query_embedding vector(384),
      match_threshold float,
      match_count int,
      p_project_id uuid
    )
    returns table (
      id uuid,
      project_id uuid,
      source_type text,
      source_id text,
      content text,
      metadata jsonb,
      similarity float
    )
    language sql stable
    as $$
      select
        knowledge_base.id,
        knowledge_base.project_id,
        knowledge_base.source_type,
        knowledge_base.source_id,
        knowledge_base.content,
        knowledge_base.metadata,
        1 - (knowledge_base.embedding <=> query_embedding) as similarity
      from knowledge_base
      where knowledge_base.project_id = p_project_id
        and 1 - (knowledge_base.embedding <=> query_embedding) > match_threshold
      order by knowledge_base.embedding <=> query_embedding
      limit match_count;
    $$;
    """
    # Unfortunately standard supabase-py doesn't have a direct raw SQL executor, 
    # but we can try to do it or tell the user to run it if it doesn't exist.
