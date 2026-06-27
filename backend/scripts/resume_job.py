import os
import sys

print("Loading dotenv...")
from dotenv import load_dotenv
load_dotenv()

print("Importing supabase...")
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
print(f"Creating supabase client for url: {url}")
supabase = create_client(url, key)

print("Querying approval request...")
res = supabase.table("approval_requests").select("*").eq("target_id", "32001a35-44a8-4074-acae-e6e26160f25f").maybe_single().execute()
ticket = getattr(res, "data", None)
print(f"Ticket found: {ticket is not None}")

if ticket:
    details = ticket.get("details") or {}
    checkpoint = details.get("checkpoint") or {}
    job_id = ticket.get("target_id")
    user_id = ticket.get("user_id")
    project_id = ticket.get("project_id")
    
    print("Querying analysis job...")
    job_res = supabase.table("analysis_jobs").select("*").eq("id", job_id).maybe_single().execute()
    job_data = getattr(job_res, "data", None)
    print(f"Job found: {job_data is not None}")
    
    if job_data:
        video_id = job_data["target_id"]
        print("Querying video upload...")
        video_res = supabase.table("video_uploads").select("*").eq("id", video_id).maybe_single().execute()
        video_data = getattr(video_res, "data", None)
        print(f"Video data found: {video_data is not None}")
        
        if video_data:
            print("Importing process_video_job...")
            from app.services.video_pipeline import process_video_job
            print("Calling process_video_job...")
            process_video_job(
                job_id=job_id,
                video_id=video_id,
                project_id=project_id,
                file_url=video_data["file_url"],
                user_id=user_id,
                start_frame=checkpoint.get("checkpoint_frame", 1),
                worker_state=checkpoint.get("tracked_workers"),
                violations_state=checkpoint.get("cumulative_violations")
            )
            print("process_video_job completed!")
        else:
            print("No video data found.")
    else:
        print("No job data found.")
else:
    print("No approval ticket found.")
