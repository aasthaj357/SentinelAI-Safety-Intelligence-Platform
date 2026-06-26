import os
from supabase import create_client

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SECRET_KEY"]
supabase = create_client(url, key)

tables = [
    'projects', 'video_uploads', 'sop_documents', 'video_transcripts', 
    'risk_assessments', 'violation_tracking', 'incident_predictions', 
    'generated_reports', 'chatbot_conversations', 'analysis_jobs', 'knowledge_base'
]

for table in tables:
    try:
        res = supabase.table(table).select('*').limit(1).execute()
        print(f"Table '{table}' exists.")
    except Exception as e:
        print(f"Table '{table}' error: {e}")
