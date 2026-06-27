import os
import sys
from dotenv import load_dotenv

# Load env variables from absolute path
load_dotenv("e:/project_fixed2/backend/.env")

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath('backend'))

from app.core.supabase_client import supabase

def get_project_stats(project_id):
    """Retrieve counts of related assets for a project."""
    videos = supabase.table("video_uploads").select("id", count="exact").eq("project_id", project_id).execute()
    evidence = supabase.table("evidence_records").select("id", count="exact").eq("project_id", project_id).execute()
    risks = supabase.table("risk_assessments").select("id", count="exact").eq("project_id", project_id).execute()
    trainings = supabase.table("training_recommendations").select("id", count="exact").eq("project_id", project_id).execute()
    
    video_count = getattr(videos, "count", 0) or len(videos.data or [])
    evidence_count = getattr(evidence, "count", 0) or len(evidence.data or [])
    risk_count = getattr(risks, "count", 0) or len(risks.data or [])
    training_count = getattr(trainings, "count", 0) or len(trainings.data or [])
    
    total_assets = video_count + evidence_count + risk_count + training_count
    return {
        "id": project_id,
        "video_count": video_count,
        "evidence_count": evidence_count,
        "risk_count": risk_count,
        "training_count": training_count,
        "total_assets": total_assets
    }

def migrate_duplicates():
    print("Fetching all projects from database...")
    projects_res = supabase.table("projects").select("*").execute()
    projects = projects_res.data or []
    
    # Group by (name, user_id)
    groups = {}
    for p in projects:
        key = (p.get("name"), p.get("user_id"))
        if key not in groups:
            groups[key] = []
        groups[key].append(p)
        
    print(f"Found {len(projects)} projects, grouped into {len(groups)} unique slots.")
    
    duplicates_resolved = 0
    projects_deleted = 0
    
    for (name, user_id), p_list in groups.items():
        if len(p_list) <= 1:
            continue
            
        print(f"\nResolving duplicates for user_id={user_id}, name='{name}':")
        # Gather stats for each project in the duplicate list
        project_stats = []
        for p in p_list:
            stats = get_project_stats(p["id"])
            stats["created_at"] = p.get("created_at")
            project_stats.append(stats)
            print(f"  Project ID: {p['id']}, Created: {stats['created_at']}, Total Assets: {stats['total_assets']} (Videos: {stats['video_count']}, Evidence: {stats['evidence_count']})")
            
        # Select master project: highest total assets first, then oldest created_at
        project_stats.sort(key=lambda x: (-x["total_assets"], x["created_at"] or ""))
        master = project_stats[0]
        master_id = master["id"]
        print(f"  Selected MASTER Project ID: {master_id}")
        
        # Migrate assets from other duplicate projects to master project
        for stats in project_stats[1:]:
            dup_id = stats["id"]
            if stats["total_assets"] > 0:
                print(f"  Migrating assets from project {dup_id} to master {master_id}...")
                
                # 1. Migrate video uploads
                if stats["video_count"] > 0:
                    v_res = supabase.table("video_uploads").update({"project_id": master_id}).eq("project_id", dup_id).execute()
                    print(f"    Reassigned {len(v_res.data or [])} video uploads.")
                    
                # 2. Migrate evidence records
                if stats["evidence_count"] > 0:
                    e_res = supabase.table("evidence_records").update({"project_id": master_id}).eq("project_id", dup_id).execute()
                    print(f"    Reassigned {len(e_res.data or [])} evidence records.")
                    
                # 3. Migrate risk assessments
                if stats["risk_count"] > 0:
                    r_res = supabase.table("risk_assessments").update({"project_id": master_id}).eq("project_id", dup_id).execute()
                    print(f"    Reassigned {len(r_res.data or [])} risk assessments.")
                    
                # 4. Migrate training recommendations
                if stats["training_count"] > 0:
                    t_res = supabase.table("training_recommendations").update({"project_id": master_id}).eq("project_id", dup_id).execute()
                    print(f"    Reassigned {len(t_res.data or [])} training recommendations.")
                    
            # Delete empty duplicate project record
            print(f"  Deleting duplicate project {dup_id}...")
            supabase.table("projects").delete().eq("id", dup_id).execute()
            projects_deleted += 1
            
        duplicates_resolved += 1
        
    print(f"\nMigration complete. Resolved {duplicates_resolved} duplicate groups, deleted {projects_deleted} empty project records.")

if __name__ == "__main__":
    migrate_duplicates()
