# Email Triage Assistant

An agentic AI assistant built with Google Agent Development Kit (ADK) and A2UI for automated L1/L2 email processing triage, diagnostics, and escalation management.

![Email Triage Assistant Full Capability Demo](./demo.gif)

---

## Features & Capabilities

The Email Triage Assistant implements the following capabilities directly through its tools, callback pipeline, and backend services:

* **Firestore Email & Error Log Querying**:
  * `search_failed_emails(start_date, end_date)`: Queries the Google Cloud Firestore `emails` collection (or local seed fallback) for emails with status `Failed`, supporting ISO date filtering.
  * `get_email_error_detail(email_id)`: Fetches error logs from the Firestore `logs` collection containing detailed error messages, flow names, timestamps, and severity levels.

* **Vertex AI RAG Engine Error Reference Retrieval**:
  * `consult_error_reference(error_code)`: Retrieves common root causes and step-by-step remediation procedures for error codes (e.g. `ERR-401`, `ERR-403`, `ERR-408`, `ERR-410`, `ERR-502`) from the RAG knowledge reference.

* **Deterministic Escalation Logic**:
  * `suggest_escalation(email_id)`: Evaluates deterministic rules to recommend tier-3 platform team escalation if:
    1. Log severity is **Critical**, OR
    2. The error code occurs **3 or more times** across the dataset.

* **A2UI Card Surfaces (v0.8 Basic Catalog)**:
  * Uses `A2uiSchemaManager` (v0.8) and `a2ui_callback` (`after_model_callback`) to render structured visual card surfaces displaying email Subject, Status, Error Code, Error Message, Severity Level, and Remediation Guidance.

* **Cloud-Native Web Client**:
  * High-performance FastAPI proxy server and modern HTML/CSS/JS frontend supporting streaming A2UI surface rendering.

---

## Repository Structure

```
.
├── app/
│   ├── agent.py                 # Core ADK Agent, tools definition & A2UI prompt
│   ├── a2ui_utils.py            # A2UI callback and surface construction helpers
│   ├── error_codes_reference.txt# RAG error code knowledge base
│   └── data/
│       └── seed_data.json       # Seed dataset for Firestore fallback
├── frontend/
│   ├── main.py                  # FastAPI proxy connecting UI to Agent Engine via A2A SDK
│   ├── static/index.html        # Responsive Chat UI with A2UI web renderer
│   ├── Dockerfile               # Container build definition for Cloud Run
│   └── requirements.txt         # Frontend dependencies
├── agents-cli-manifest.yaml     # Agent deployment manifest (ADK / Agent Runtime)
├── full_capability_demo.webm    # Original recorded video demo
├── demo.gif                     # Optimized inline looping demo GIF
└── README.md                    # Project documentation
```

---

## Setup & Deployment Instructions

### Prerequisites
- Python 3.11+
- Google Cloud SDK (`gcloud`)
- Antigravity / ADK CLI (`agents-cli`)
- Active GCP Project with Firestore and Vertex AI APIs enabled

---

### 1. Local Playground Testing

To run the agent locally in the ADK Playground:

```bash
agents-cli playground --port 8080
```

Open `http://localhost:8080` in your browser to test tools and A2UI rendering.

---

### 2. Deploying Agent Engine to Agent Runtime

Deploy the agent to GCP Agent Runtime using `agents-cli`:

```bash
agents-cli deploy
```

Once deployment completes, record the output `AGENT_ENGINE_RESOURCE_NAME` (e.g., `projects/<PROJECT_ID>/locations/<REGION>/reasoningEngines/<RESOURCE_ID>`).

---

### 3. Running the Local Frontend Proxy

To run the FastAPI proxy locally against your deployed agent:

```bash
cd frontend
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/<REGION>/reasoningEngines/<RESOURCE_ID>"
export AGENT_DIRECTORY="app"
export PORT=8081

python main.py
```

Access the chat frontend at `http://localhost:8081`.

---

### 4. Deploying Frontend to Google Cloud Run

Deploy the web application to Google Cloud Run:

```bash
gcloud run deploy email-triage-frontend \
  --source ./frontend \
  --region <REGION> \
  --project <PROJECT_ID> \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME=<AGENT_ENGINE_RESOURCE_NAME>,AGENT_DIRECTORY=app \
  --allow-unauthenticated
```

---

### 5. IAM Role Configuration

Grant required service account permissions:

1. **Agent Service Account** (Firestore access):
   ```bash
   gcloud projects add-iam-policy-binding <PROJECT_ID> \
     --member="serviceAccount:<AGENT_SERVICE_ACCOUNT>" \
     --role="roles/datastore.user"
   ```

2. **Cloud Run Service Account** (Agent Engine invocation access):
   ```bash
   gcloud projects add-iam-policy-binding <PROJECT_ID> \
     --member="serviceAccount:<CLOUD_RUN_SERVICE_ACCOUNT>" \
     --role="roles/aiplatform.user"
   ```
