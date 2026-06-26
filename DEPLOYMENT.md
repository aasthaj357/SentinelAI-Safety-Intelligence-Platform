# Deployment Guide

This document outlines how to deploy the Multi-Agent Workplace Safety Intelligence Platform to production.

## 1. Database (Supabase)

1. Navigate to your Supabase project dashboard.
2. In the **SQL Editor**, run the two migration scripts found in `supabase/migrations/`:
   - `00000000000000_initial_schema.sql`
   - `00000000000001_phase3_rag.sql` (This enables `pgvector` and the `match_knowledge` RPC)
3. Ensure the Storage Buckets (`videos`, `annotated-videos`, `sop-documents`, `reports`) are created and public (if required by your frontend).

## 2. Backend (Render)

The backend is packaged as a Docker container, optimized for OpenCV and Python 3.10.

1. Connect your GitHub repository to Render.
2. Render will automatically detect the `render.yaml` file in the root directory.
3. Deploy the `safety-intelligence-backend` service.
4. **Environment Variables**: You must configure the following in the Render dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_SECRET_KEY`
   - `GROQ_API_KEY`
   - `ROBOFLOW_API_KEY`

Render will handle the Docker build, install the `sentence-transformers` for local RAG embeddings, and expose the FastAPI endpoints.

## 3. Frontend (Vercel)

The frontend is a Vite + React application.

1. Connect your GitHub repository to Vercel.
2. Set the **Framework Preset** to `Vite`.
3. Vercel will automatically use the `vercel.json` provided in `frontend/` to handle client-side routing.
4. **Environment Variables**: Configure the following in the Vercel dashboard:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL` (Set this to your deployed Render URL, e.g., `https://safety-intelligence-backend.onrender.com`)

## 4. Multi-Agent Orchestration (n8n)

The repository includes an `n8n_workflow.json` file.

1. Open your n8n instance.
2. Click **Add Workflow** -> **Import from File**.
3. Select `n8n_workflow.json`.
4. Ensure the HTTP Request nodes point to your production Render URL instead of `localhost`.
5. You can trigger this workflow manually or set up a webhook trigger to fire when a video finishes uploading.

## Health Checks

Once deployed, you can verify the backend is running by visiting:
- `https://<YOUR-RENDER-URL>/` (Should return the FastAPI root response)
- `https://<YOUR-RENDER-URL>/docs` (Swagger UI for all API endpoints)
