# Deployment & Verification Checklist

## Pre-Deployment Verification

### Database Migration
- [ ] Run migration: `supabase/migrations/00000000000005_add_user_id_tracking.sql`
  - Adds user_id columns to all core tables
  - Creates indexes on user_id
  - Does NOT affect existing data (backward compatible)

### Backend Files Changed
- [ ] `backend/app/api/chat.py` - Complete rewrite, Safety Officer responses
- [ ] `backend/app/api/demo.py` - Added user_id tracking to all demo inserts
- [ ] `backend/app/api/reports.py` - Complete rewrite, full HTML report generation

### Frontend Files Changed
- [ ] `frontend/src/context/ActiveProjectContext.jsx` - NEW file (global state)
- [ ] `frontend/src/App.jsx` - Added ActiveProjectProvider wrapper
- [ ] `frontend/src/pages/Dashboard.jsx` - Uses useActiveProject hook
- [ ] `frontend/src/pages/SafetyCopilot.jsx` - Uses activeProjectId from context
- [ ] `frontend/src/pages/EvidenceGallery.jsx` - Filters by activeProjectId
- [ ] `frontend/src/lib/project.js` - Added user_id to project creation

### Documentation Added
- [ ] `ARCHITECTURE_IMPROVEMENTS.md` - Full implementation guide
- [ ] `BEFORE_AFTER_IMPROVEMENTS.md` - Side-by-side comparisons

---

## Deployment Steps

### Step 1: Database
```bash
# Apply migration to Supabase
# Option A: Via Supabase dashboard
#   - Go to SQL editor
#   - Copy contents of migrations/00000000000005_add_user_id_tracking.sql
#   - Execute

# Option B: Via CLI
supabase db push
```

### Step 2: Backend
```bash
# No additional dependencies needed
# Changes are in Python files only

# If deploying to production:
cd backend
pip install -r requirements.txt  # Same as before
python -m uvicorn app.main:app --reload
```

### Step 3: Frontend
```bash
# No additional dependencies needed
# Changes are in React files only

cd frontend
npm install  # Same as before
npm run dev
```

---

## Testing Checklist

### State Consistency
- [ ] **Load Demo Data**
  - Click "Load Demo Data" on Dashboard
  - Check browser console: localStorage should have `activeProjectId`
  - Verify all stats appear (violations, risk score, etc.)

- [ ] **Navigate Pages**
  - Go to Dashboard → Copilot → Evidence Gallery → back to Dashboard
  - Active project should remain the same
  - All data should be consistent across pages

- [ ] **Page Refresh**
  - Load demo data
  - Refresh browser (Ctrl+R)
  - Dashboard should immediately show data (not blank/loading)
  - Active project should be restored

- [ ] **Reset Data**
  - Click "Reset Data" button
  - Verify all data clears
  - Active project remains set
  - Can load demo data again

### Copilot Response Quality
- [ ] **Risk Question**: "Why was this risk score generated?"
  - Response should start with risk level (⚠️ CRITICAL/HIGH or ✓ MANAGEABLE)
  - Should explain key drivers in business terms
  - Should list violations with timestamps
  - Should end with separated citations

- [ ] **Violation Question**: "What violations were detected?"
  - Should group violations by type
  - Should show count and specific incidents
  - Should mention SOP relevance

- [ ] **SOP Question**: "What does the SOP say?"
  - Should reference the SOP document
  - Should show violations of that SOP
  - Should provide context

- [ ] **Training Question**: "What training is recommended?"
  - Should suggest modules based on violations
  - Should prioritize (Critical, High, Medium)
  - Should mention effort required (hours)

### Evidence Viewer
- [ ] **Filter by Project**
  - Should only show evidence from current project
  - Not all evidence in database
  - Counts should match dashboard

### PDF Export
- [ ] **Generate Report** (when implemented in Dashboard)
  - Should include all sections
  - Should match active project data
  - Should be downloadable as PDF

---

## Verification Commands

### Check Frontend Context Integration
```javascript
// Open browser console (F12)
// In any page, run:
// This should show the current active project
localStorage.getItem('activeProjectId')
```

### Check Backend Response Format
```bash
# Test the chat endpoint
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "YOUR_PROJECT_ID",
    "message": "Why was this risk score generated?",
    "history": []
  }'

# Response should have human-readable 'reply' field, not database dump
```

### Check Demo Data User Association
```sql
-- In Supabase SQL editor
-- Verify demo data has user_id
SELECT id, project_id, user_id, title FROM video_uploads LIMIT 5;
SELECT id, project_id, user_id, violation_type FROM violation_tracking LIMIT 5;
SELECT id, project_id, user_id, score FROM risk_assessments LIMIT 5;
```

---

## Rollback Instructions (If Needed)

### If Migration Causes Issues
```sql
-- Remove user_id columns (if needed)
ALTER TABLE projects DROP COLUMN IF EXISTS user_id;
ALTER TABLE video_uploads DROP COLUMN IF EXISTS user_id;
-- ... repeat for all tables
-- (Backward compatible - data still works without user_id)
```

### If Frontend Issues Occur
- Active project context is in localStorage
- Can clear with: `localStorage.clear()` in browser console
- React will fall back to loading project on demand

---

## Performance Considerations

### Database
- [ ] New indexes on user_id improve query performance
- [ ] No performance regression on existing queries
- [ ] Backward compatible - all columns are optional

### Frontend
- [ ] ActiveProjectContext adds minimal overhead
- [ ] localStorage is <1ms read time
- [ ] No additional API calls for state management

### Backend
- [ ] chat.py response building similar complexity
- [ ] reports.py is new, may take ~2-3 seconds for large projects

---

## Post-Deployment Checklist

- [ ] Monitor application logs for errors
- [ ] Test with demo user account
- [ ] Verify database migrations applied successfully
- [ ] Test with real video upload (if applicable)
- [ ] Check localStorage in production (should work in all browsers)
- [ ] Verify CORS settings still working
- [ ] Test on mobile browser (localStorage works same)

---

## Known Limitations & Future Work

### Current Limitations
1. **Single Active Project per Browser**: User can only have one active project at a time
   - Future: Add project switcher to sidebar

2. **localStorage Scope**: Per browser/domain
   - Future: Sync with backend user preferences

3. **PDF Export**: HTML only, requires browser for PDF conversion
   - Future: Server-side PDF generation with reportlab

### Future Enhancements (No Schema Changes Needed)
- [ ] Trend dashboards (violations per day, risk score trends)
- [ ] Organization-level reporting (aggregate across users)
- [ ] Custom date range queries for historical analysis
- [ ] Training effectiveness tracking
- [ ] Incident pattern analysis

---

## Support & Troubleshooting

### Issue: Active project not persisting after refresh
**Solution**: Clear localStorage and reload
```javascript
localStorage.clear();
location.reload();
```

### Issue: Copilot responses still showing database format
**Solution**: Verify chat.py changes were deployed
```bash
grep "_answer_risk_question" backend/app/api/chat.py
# Should find multiple _answer_* functions
```

### Issue: Evidence gallery showing all violations
**Solution**: Verify EvidenceGallery.jsx uses activeProjectId
```bash
grep "activeProjectId" frontend/src/pages/EvidenceGallery.jsx
# Should appear in multiple places
```

### Issue: Demo data not loading
**Solution**: Check user_id is being passed
```bash
# Check browser network tab - POST /api/demo/load
# Request body should include: {"project_id": "...", "user_id": "..."}
```

---

## Sign-Off

Once all items in this checklist are verified:

- [ ] Development environment tested
- [ ] Staging environment tested
- [ ] Production migration applied
- [ ] Production deployment successful
- [ ] End-user acceptance testing passed
- [ ] Documentation shared with team

**Ready for Production** ✓

---

## Documents for Reference

1. **ARCHITECTURE_IMPROVEMENTS.md** - Detailed implementation guide
2. **BEFORE_AFTER_IMPROVEMENTS.md** - Side-by-side comparisons showing improvements
3. **This file** - Deployment and verification checklist

All changes maintain backward compatibility while establishing the foundation for multi-user support and historical analytics.
