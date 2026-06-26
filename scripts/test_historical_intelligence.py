import os
import sys

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv('.env')

from app.api.chat import _build_reply
from app.api.reports import _generate_report_html

def validate():
    # Mock data that AnalyticsService would return
    mock_analytics = {
        "monthly_violations": [
            {
                "violation_type": "No Helmet",
                "monthly_trend": [
                    {"month": "Jan", "count": 18},
                    {"month": "Feb", "count": 12},
                    {"month": "Mar", "count": 7}
                ]
            }
        ],
        "risk_trend": [
            {"period": "Jan", "avg_risk_score": 91},
            {"period": "Feb", "avg_risk_score": 73},
            {"period": "Mar", "avg_risk_score": 54}
        ],
        "ppe_trend": [
            {"period": "Jan", "ppe_compliance_pct": 61},
            {"period": "Feb", "ppe_compliance_pct": 78},
            {"period": "Mar", "ppe_compliance_pct": 92}
        ],
        "sop_trend": {
            "Standard PPE": [
                {"period": "Jan", "violation_count": 15},
                {"period": "Feb", "violation_count": 10},
                {"period": "Mar", "violation_count": 5}
            ]
        },
        "training_effectiveness": {
            "Advanced Head Protection": {
                "reduction_percent": 61,
                "violations_before": 18,
                "violations_after": 7
            }
        }
    }
    
    mock_context = {
        "risks": [{"score": 54, "details": {"reasoning": "Improving PPE compliance."}}],
        "violations": [{"violation_type": "No Helmet"}],
        "analytics": mock_analytics
    }

    message = "Are we improving? Show PPE compliance and risk score trends."
    
    print("--- SAMPLE COPILOT RESPONSE ---")
    reply = _build_reply(message, mock_context, [], [])
    print(reply)
    
    print("\n--- SAMPLE PDF HTML ---")
    report_data = {
        "project": {"name": "Test Project"},
        "analytics": mock_analytics,
        "evidence": [{"detection_label": "No Helmet", "timestamp": 12.5, "screenshot_url": ""}],
        "risks": [{"score": 54, "details": {"reasoning": "Improving PPE compliance."}}]
    }
    html = _generate_report_html(report_data)
    print(html[:1000] + "\n... [TRUNCATED] ...\n" + html[-1000:])
    
if __name__ == "__main__":
    validate()
