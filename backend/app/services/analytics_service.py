"""
Analytics Service: Provides historical analytics and trend calculations
for user safety data across multiple projects and time periods.
"""

from app.core.supabase_client import supabase
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json


class AnalyticsService:
    """
    Service for querying and analyzing historical safety data.
    All queries are scoped to user_id for multi-user isolation.
    """

    @staticmethod
    def get_violations_this_week(user_id: str, project_id: Optional[str] = None) -> Dict:
        """Get violation count and breakdown for this week."""
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        query = supabase.table("violation_tracking").select("*").eq("user_id", user_id).gte("created_at", week_ago)
        if project_id:
            video_ids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if video_ids:
                query = query.in_("video_id", video_ids)
            else:
                return {"total": 0, "breakdown": {}, "period": "This Week"}
        
        res = query.execute()
        violations = res.data or []
        
        # Group by type
        by_type = {}
        for v in violations:
            vtype = v.get("violation_type", "Unknown")
            by_type[vtype] = by_type.get(vtype, 0) + 1
        
        return {
            "total": len(violations),
            "breakdown": by_type,
            "period": "This Week",
        }

    @staticmethod
    def get_violations_this_month(user_id: str, project_id: Optional[str] = None) -> Dict:
        """Get violation count and breakdown for this month."""
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        
        query = supabase.table("violation_tracking").select("*").eq("user_id", user_id).gte("created_at", month_ago)
        if project_id:
            video_ids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if video_ids:
                query = query.in_("video_id", video_ids)
            else:
                return {"total": 0, "breakdown": {}, "period": "This Month"}
        
        res = query.execute()
        violations = res.data or []
        
        # Group by type
        by_type = {}
        for v in violations:
            vtype = v.get("violation_type", "Unknown")
            by_type[vtype] = by_type.get(vtype, 0) + 1
        
        return {
            "total": len(violations),
            "breakdown": by_type,
            "period": "This Month",
        }

    @staticmethod
    def get_violation_trend_by_type(user_id: str, project_id: str, days: int = 90) -> List[Dict]:
        """Get monthly trend of specific violation types (e.g., Helmet)."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = supabase.table("violation_tracking").select("*").eq("user_id", user_id).gte("created_at", cutoff_date)
        if project_id:
            video_ids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if video_ids:
                query = query.in_("video_id", video_ids)
            else:
                return []
        
        res = query.execute()
        violations = res.data or []
        
        # Group by type and month
        by_type_month = {}
        for v in violations:
            vtype = v.get("violation_type", "Unknown")
            dt = datetime.fromisoformat(v["created_at"][:19])
            month_str = dt.strftime("%b")
            
            if vtype not in by_type_month:
                by_type_month[vtype] = {}
            if month_str not in by_type_month[vtype]:
                by_type_month[vtype][month_str] = 0
            
            by_type_month[vtype][month_str] += 1
            
        months_order = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        
        trend = []
        for vtype, months in by_type_month.items():
            month_data = [{"month": m, "count": c} for m, c in months.items()]
            month_data.sort(key=lambda x: months_order.get(x["month"], 0))
            trend.append({
                "violation_type": vtype,
                "monthly_trend": month_data
            })
            
        # Sort by total volume
        trend.sort(key=lambda x: sum(m["count"] for m in x["monthly_trend"]), reverse=True)
        return trend

    @staticmethod
    def get_most_violated_sops(user_id: str, project_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Get SOPs that are violated most often."""
        query = supabase.table("evidence_records").select("*").eq("user_id", user_id)
        if project_id:
            query = query.eq("project_id", project_id)
        
        res = query.execute()
        evidence = res.data or []
        
        # Count violations by SOP section
        by_sop = {}
        for ev in evidence:
            sop = ev.get("sop_section", "Unknown")
            if sop:
                by_sop[sop] = by_sop.get(sop, 0) + 1
        
        # Sort by count
        sorted_sops = sorted(by_sop.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"sop_section": sop, "violation_count": count}
            for sop, count in sorted_sops[:limit]
        ]

    @staticmethod
    def get_risk_score_trend(user_id: str, project_id: str, days: int = 90, group_by: str = "month") -> List[Dict]:
        """Get risk score trend over time for a project."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        res = supabase.table("risk_assessments").select("*").eq("user_id", user_id).eq("project_id", project_id).gte("created_at", cutoff_date).order("created_at", desc=False).execute()
        
        assessments = res.data or []
        
        by_date = {}
        for assessment in assessments:
            if group_by == "month":
                dt = datetime.fromisoformat(assessment["created_at"][:19])
                date_str = dt.strftime("%b")
            else:
                date_str = assessment["created_at"][:10]  # YYYY-MM-DD
                
            score = float(assessment.get("score", 0))
            if date_str not in by_date:
                by_date[date_str] = []
            by_date[date_str].append(score)
        
        trend = []
        months_order = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        
        if group_by == "month":
            sorted_keys = sorted(by_date.keys(), key=lambda x: months_order.get(x, 0))
        else:
            sorted_keys = sorted(by_date.keys())

        for date_str in sorted_keys:
            avg_score = sum(by_date[date_str]) / len(by_date[date_str])
            trend.append({
                "period": date_str,
                "avg_risk_score": round(avg_score, 1),
                "assessments": len(by_date[date_str]),
            })
        
        return trend

    @staticmethod
    def get_ppe_compliance_trend(user_id: str, project_id: str, days: int = 90, group_by: str = "month") -> List[Dict]:
        """Get PPE compliance trend over time."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        res = supabase.table("evidence_records").select("*").eq("user_id", user_id).eq("project_id", project_id).gte("created_at", cutoff_date).order("created_at", desc=False).execute()
        
        evidence = res.data or []
        
        by_date = {}
        for ev in evidence:
            if group_by == "month":
                dt = datetime.fromisoformat(ev["created_at"][:19])
                date_str = dt.strftime("%b")
            else:
                date_str = ev["created_at"][:10]  # YYYY-MM-DD
            
            if date_str not in by_date:
                by_date[date_str] = set()
            
            label = ev.get("detection_label", "").lower().strip()
            normalized_label = label.replace(" ", "-").replace("_", "-")
            
            if "helmet" in normalized_label or "hardhat" in normalized_label:
                by_date[date_str].add("helmet")
            elif "glove" in normalized_label:
                by_date[date_str].add("gloves")
            elif "goggle" in normalized_label or "eye" in normalized_label:
                by_date[date_str].add("goggles")
            elif "vest" in normalized_label or "vis" in normalized_label:
                by_date[date_str].add("vest")
            elif "shoes" in normalized_label or "boots" in normalized_label:
                by_date[date_str].add("shoes")
            elif "mask" in normalized_label or "respirator" in normalized_label:
                by_date[date_str].add("mask")
        
        trend = []
        months_order = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        
        if group_by == "month":
            sorted_keys = sorted(by_date.keys(), key=lambda x: months_order.get(x, 0))
        else:
            sorted_keys = sorted(by_date.keys())

        for date_str in sorted_keys:
            violated_set = by_date[date_str]
            compliance = max(0.0, 100.0 - len(violated_set) * 15.0)
            
            trend.append({
                "period": date_str,
                "ppe_compliance_pct": compliance,
                "total_violations": len(violated_set),
                "ppe_violations": len(violated_set),
            })
        
        return trend

    @staticmethod
    def get_sop_compliance_trend(user_id: str, project_id: str, days: int = 90, group_by: str = "month") -> Dict[str, List[Dict]]:
        """Get SOP compliance trend for each SOP section over time."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        res = supabase.table("evidence_records").select("*").eq("user_id", user_id).eq("project_id", project_id).gte("created_at", cutoff_date).order("created_at", desc=False).execute()
        evidence = res.data or []

        # Also pull from violation_tracking for SOP violations
        viol_video_ids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
        if viol_video_ids:
            viol_res = supabase.table("violation_tracking").select("*").eq("user_id", user_id).in_("video_id", viol_video_ids).gte("created_at", cutoff_date).order("created_at", desc=False).execute()
        else:
            viol_res = type("R", (), {"data": []})()  # empty result
        violations = viol_res.data or []

        # Group by SOP and date
        by_sop_date = {}
        for ev in evidence:
            sop = ev.get("sop_section") or "Unknown SOP"
            if group_by == "month":
                dt = datetime.fromisoformat(ev["created_at"][:19])
                date_str = dt.strftime("%b")
            else:
                date_str = ev["created_at"][:10]
            
            if sop not in by_sop_date:
                by_sop_date[sop] = {}
            if date_str not in by_sop_date[sop]:
                by_sop_date[sop][date_str] = 0
            
            by_sop_date[sop][date_str] += 1

        for v in violations:
            vtype = v.get("violation_type") or "Unknown Violation"
            if group_by == "month":
                dt = datetime.fromisoformat(v["created_at"][:19])
                date_str = dt.strftime("%b")
            else:
                date_str = v["created_at"][:10]
            
            if vtype not in by_sop_date:
                by_sop_date[vtype] = {}
            if date_str not in by_sop_date[vtype]:
                by_sop_date[vtype][date_str] = 0
            
            by_sop_date[vtype][date_str] += 1
            
        months_order = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        
        # Format for response
        trend = {}
        for sop in sorted(by_sop_date.keys()):
            if group_by == "month":
                dates = sorted(by_sop_date[sop].keys(), key=lambda x: months_order.get(x, 0))
            else:
                dates = sorted(by_sop_date[sop].keys())
                
            trend[sop] = [
                {"period": date_str, "violation_count": by_sop_date[sop][date_str]}
                for date_str in dates
            ]
        
        return trend

    @staticmethod
    def is_improving(user_id: str, project_id: str) -> Dict:
        """Determine if user is improving safety over time."""
        now = datetime.now()
        current_month_start = now.replace(day=1).isoformat()
        prev_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()

        _vids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
        if _vids:
            current_res = supabase.table("violation_tracking").select("*").eq("user_id", user_id).in_("video_id", _vids).gte("created_at", current_month_start).execute()
            current_violations = len(current_res.data or [])
        else:
            current_violations = 0

        if _vids:
            prev_res = supabase.table("violation_tracking").select("*").eq("user_id", user_id).in_("video_id", _vids).gte("created_at", prev_month_start).lt("created_at", current_month_start).execute()
            prev_violations = len(prev_res.data or [])
        else:
            prev_violations = 0

        if prev_violations == 0:
            if current_violations == 0:
                improvement = "stable"
                change_pct = 0
                comparison_label = "No violations in either period"
            else:
                improvement = "worsening"
                change_pct = None
                comparison_label = "Insufficient historical baseline"
        else:
            change_pct = round(100 * (current_violations - prev_violations) / prev_violations, 1)
            if change_pct < -10:
                improvement = "improving"
            elif change_pct > 10:
                improvement = "worsening"
            else:
                improvement = "stable"
            comparison_label = f"{abs(change_pct)}% {'decrease' if change_pct < 0 else 'increase'} vs last month"

        return {
            "status": improvement,
            "change_percent": change_pct,
            "comparison_label": comparison_label,
            "current_month_violations": current_violations,
            "previous_month_violations": prev_violations,
        }

    @staticmethod
    def compare_projects(user_id: str) -> Dict:
        """Compare safety metrics across all user's projects."""
        # Get all projects for user
        projects_res = supabase.table("projects").select("id, name").eq("user_id", user_id).execute()
        projects = projects_res.data or []
        
        comparison = {}
        for project in projects:
            project_id = project["id"]
            project_name = project.get("name", "Unknown")
            
            # Count violations via video_ids
            vids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if vids:
                viol_res = supabase.table("violation_tracking").select("*").eq("user_id", user_id).in_("video_id", vids).execute()
                violations = len(viol_res.data or [])
            else:
                violations = 0
            
            # Get latest risk assessment
            risk_res = supabase.table("risk_assessments").select("*").eq("user_id", user_id).eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
            latest_risk = risk_res.data[0]["score"] if risk_res.data else 0
            
            # Count evidence
            evid_res = supabase.table("evidence_records").select("*").eq("user_id", user_id).eq("project_id", project_id).execute()
            evidence_count = len(evid_res.data or [])
            
            comparison[project_name] = {
                "project_id": project_id,
                "total_violations": violations,
                "latest_risk_score": float(latest_risk),
                "evidence_records": evidence_count,
            }
        
        return comparison

    @staticmethod
    def get_training_effectiveness(user_id: str, project_id: str) -> Dict:
        """Analyze training effectiveness by looking at violation reduction."""
        # Get all training recommendations
        trainings_res = supabase.table("training_recommendations").select("*").eq("user_id", user_id).eq("project_id", project_id).order("created_at", desc=False).execute()
        trainings = trainings_res.data or []
        
        if not trainings:
            return {"status": "no_data", "message": "No training recommendations found"}
        
        effectiveness = {}
        
        for training in trainings:
            created_date = training["created_at"][:10]
            module_name = training.get("human_readable_summary", "Unknown Module")
            
            # Get violations before and after training
            _vids2 = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if _vids2:
                before_res = supabase.table("violation_tracking").select("*").eq("user_id", user_id).in_("video_id", _vids2).lt("created_at", created_date).order("created_at", desc=True).limit(30).execute()
                before_violations = len(before_res.data or [])

                after_res = supabase.table("violation_tracking").select("*").eq("user_id", user_id).in_("video_id", _vids2).gte("created_at", created_date).limit(30).execute()
                after_violations = len(after_res.data or [])
            else:
                before_violations = 0
                after_violations = 0
            
            if before_violations > 0:
                reduction = round(100 * (before_violations - after_violations) / before_violations, 1)
            else:
                reduction = 0
            
            effectiveness[module_name] = {
                "violations_before": before_violations,
                "violations_after": after_violations,
                "reduction_percent": reduction,
                "effective": reduction > 20,
            }
        
        return effectiveness

    @staticmethod
    def get_ppe_violations_by_type(user_id: str, project_id=None) -> dict:
        """Get violation counts broken down by specific PPE type."""
        PPE_TYPE_PATTERNS = {
            "helmet": ["helmet", "hardhat", "hard-hat"],
            "gloves": ["glove", "gloves"],
            "goggles": ["goggle", "goggles", "glasses", "eye protection"],
            "vest": ["vest", "hi-vis", "visibility"],
            "shoes": ["shoes", "boots", "foot"],
            "mask": ["mask", "respirator"],
        }
        query = supabase.table("violation_tracking").select("violation_type").eq("user_id", user_id)
        if project_id:
            video_ids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if video_ids:
                query = query.in_("video_id", video_ids)
            else:
                return {"total": 0, "by_ppe_type": {ppe: 0 for ppe in PPE_TYPE_PATTERNS} | {"other": 0}}
        res = query.execute()
        violations = res.data or []
        counts = {ppe: 0 for ppe in PPE_TYPE_PATTERNS}
        counts["other"] = 0
        for v in violations:
            vt = (v.get("violation_type") or "").lower()
            matched = False
            for ppe_type, patterns in PPE_TYPE_PATTERNS.items():
                if any(p in vt for p in patterns):
                    counts[ppe_type] += 1
                    matched = True
                    break
            if not matched:
                counts["other"] += 1
        return {"total": len(violations), "by_ppe_type": counts}

    @staticmethod
    def get_training_recommendations_from_violations(user_id: str, project_id=None) -> list:
        """Generate specific training recommendations from observed violation types."""
        RECOMMENDATIONS = {
            "helmet": {"title": "Head Protection Training", "action": "Mandatory helmet wearing; toolbox talk on TBI risk"},
            "glove": {"title": "Hand Protection Training", "action": "Glove selection and usage; chemical/cut hazard awareness"},
            "goggle": {"title": "Eye Protection Training", "action": "Mandatory eyewear in hazard zones; emergency eyewash locations"},
            "vest": {"title": "High-Visibility Awareness", "action": "Hi-vis vest requirements; vehicle exclusion zone marking"},
            "shoes": {"title": "Foot Protection Training", "action": "Safety footwear policy; dropped object awareness"},
            "mask": {"title": "Respiratory Protection Training", "action": "Respirator selection; fit testing; chemical exposure controls"},
            "jack stand": {"title": "Vehicle Lift Safety", "action": "Jack stand placement; vehicle lift point identification"},
            "fire": {"title": "Fire Safety & Hot Work", "action": "Hot work permit; fire extinguisher locations; evacuation"},
            "lockout": {"title": "Lockout/Tagout Procedure", "action": "LOTO procedure; energy isolation verification"},
            "battery": {"title": "Electrical Safety", "action": "Battery isolation; arc flash PPE; short circuit prevention"},
        }
        query = supabase.table("violation_tracking").select("violation_type, timestamp").eq("user_id", user_id)
        if project_id:
            video_ids = [r["id"] for r in (supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute().data or [])]
            if video_ids:
                query = query.in_("video_id", video_ids)
            else:
                return []
        res = query.execute()
        violations = res.data or []
        seen = set()
        recs = []
        for v in violations:
            vt = (v.get("violation_type") or "").lower()
            for key, rec in RECOMMENDATIONS.items():
                if key in vt and key not in seen:
                    ts_val = float(v.get("timestamp") or 0.0)
                    recs.append({
                        "violation_trigger": vt,
                        "training_title": rec["title"],
                        "recommended_action": rec["action"],
                        "priority": "high" if any(k in vt for k in ("helmet", "fire", "jack", "lockout")) else "medium",
                        "evidence": f"{vt} @ {ts_val:.2f}s",
                    })
                    seen.add(key)
                    break
        return recs


def get_analytics_service() -> AnalyticsService:
    """Factory function to get analytics service instance."""
    return AnalyticsService()
