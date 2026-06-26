# Workplace Safety Intelligence Platform - Demo Guide

This guide is designed to help you execute a flawless, end-to-end demonstration of the Multi-Agent Safety Platform for judging or executive review.

## 1. Demo Initialization
Before starting the presentation, you can load a rich set of sample data (violations, predictions, transcripts, risk scores) without waiting for a 10-minute video upload to process.

- **Action:** Open your browser console or use Postman to send a `POST` request to `http://localhost:8000/api/demo/load`.
- **Result:** The Dashboard, Evidence Gallery, and Copilot will instantly populate with "Demo Construction Site A" data.

## 2. Executive Dashboard (The "Hook")
Start the demo on the main **Dashboard** page.
- **Key Feature to Highlight:** The *Executive Safety Scorecard*. Point out that this isn't just counting violations; it's fusing PPE compliance, SOP compliance, and Incident Risk into actionable scores.
- **Key Feature to Highlight:** The *Training Recommendations* section. Explain how the "Training Recommendation Agent" automatically prescribes corrective actions (e.g., "Mandatory re-training for Sector 4 team").

## 3. Analysis Viewer (The "Evidence")
Navigate to an uploaded video's **Analysis Viewer**.
- **Key Feature to Highlight:** The *Annotated Video Viewer* syncing with the *Transcript Viewer*.
- **Key Feature to Highlight:** The *Visual Violation Timeline*. Click on a timeline event to demonstrate how an executive can jump directly to the exact frame of a safety violation, complete with confidence scores.

## 4. Multi-Agent Architecture (The "Under the Hood")
Navigate to the **Agent Activity Viewer** (if added to your sidebar) or explain the n8n orchestration.
- **Key Feature to Highlight:** Explain that 7 distinct AI agents (Observation, Communication, SOP, Auditor, Risk, Prediction, Training) process the data in a pipeline. This is what differentiates the platform from a simple object-detection wrapper.

## 5. Safety Copilot (The "Wow" Factor)
Navigate to the **Safety Copilot** page.
- **Key Feature to Highlight:** The copilot uses **Retrieval Augmented Generation (RAG)**. It doesn't use generic LLM knowledge; it searches your specific embedded SOPs and violation records.
- **Action:** Ask the copilot:
  - *"Why was this risk score generated?"*
  - *"Which SOP sections were violated in Sector 4?"*
  - *"What training is recommended and why?"*
- **Key Feature to Highlight:** Point out the **Evidence Viewer** and source attribution tags `[Source 1]` in the chat responses. This demonstrates Explainable AI (XAI) and builds trust with safety inspectors.

## 6. PDF Export (The "Takeaway")
- Conclude the demo by showing that all this intelligence can be exported into a structured PDF report for compliance filing or OSHA auditing.

---

### Architecture Overview for Judges
If asked about the tech stack, highlight:
- **Frontend:** React + Tailwind + Vite (Deployed on Vercel)
- **Backend:** FastAPI + Python (Deployed on Render via Docker)
- **Database:** Supabase with `pgvector` enabled for local RAG embeddings.
- **AI Models:** YOLOv8 (Objects), Roboflow (Custom PPE), Groq Whisper (Speech), Groq Llama3 (Reasoning & NLP), `sentence-transformers` (Local Embeddings).
- **Orchestration:** n8n natively chaining 7 FastAPI endpoints.
