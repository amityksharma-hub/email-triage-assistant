Tech Stack — Explained

*Every technology/tool used to build this POC, in plain language, so you can
answer follow-up questions confidently.*



1. Build Tooling — how the code got written

Component
What it is
Why it's here
Antigravity (AGY)
Google's agentic IDE — an AI pair-programming assistant that runs in a remote development desktop
This is the tool that actually wrote the code, ran commands, and deployed everything, based on instructions given to it in plain English
agents-cli
A Google CLI tool that scaffolds, tests, and deploys ADK-based agents
Used to generate the initial project skeleton (app/agent.py, config files), run the local Playground, and deploy to Agent Runtime
Developer Knowledge MCP
A Model Context Protocol server that gives AGY grounded, up-to-date access to Google's official docs (Cloud, Firebase, ADK, Agent Platform)
Prevents AGY from guessing at APIs — it looks up the real, current documentation before writing code that calls Google Cloud services
Firebase MCP
An MCP server that lets AGY work directly with Firebase/Firestore
Used when setting up the Firestore collections and seed data
uv
A fast Python package manager (the tool behind agents-cli install, uv run)
Manages the Python virtual environment and dependency lockfile (uv.lock) for the project

What is MCP, in one sentence? Model Context Protocol is a standard way to
plug external tools and data sources (docs, databases, APIs) into an AI
agent, so it doesn't have to guess — it can look things up.



2. Agent Framework — what the agent itself is built with

Component
What it is
Why it's here
Google ADK (Agent Development Kit)
An open-source Python framework for building agents — provides the Agent and App classes, tool-calling machinery, session management
This is the core framework the entire agent is written in
Gemini 2.5 Flash
Google's LLM, the "brain" of the agent
Chosen for speed/cost balance appropriate for a support-tool use case; it decides which tools to call and composes the final answer
Function Tools
Plain Python functions with type hints and docstrings, registered on the agent
ADK reads the docstring to know when to call each tool — this is how the model "knows" what search_failed_emails does without being told explicitly in the prompt
after_model_callback
An ADK hook that intercepts the model's raw output before it's returned
Used to catch the model's A2UI JSON and rewrap it into the format the renderer expects



3. Data & Knowledge Layer

Component
What it is
Why it's here
Cloud Firestore
A serverless, NoSQL document database from Google Cloud
Stores the two structured collections (emails, logs) — chosen because it's simple, has no schema migrations, and is trivial to query from Python
Vertex AI RAG Engine
A managed retrieval-augmented-generation service — takes a document, chunks it, embeds it, and lets you run similarity search queries against it
Powers the "what does this error code mean" lookups — this is the actual RAG (Retrieval-Augmented Generation) component
Embeddings / vector similarity search
The underlying technique RAG uses — turns text into numeric vectors so "similar meaning" text can be found even without exact keyword matches
This is why asking about "ERR-401" reliably finds the right passage even if worded slightly differently

What does RAG actually stand for, and why not just paste the whole
document into the prompt? Retrieval-Augmented Generation. For one small
file it wouldn't matter much, but the pattern scales — if the knowledge base
grows to hundreds of documents, RAG retrieves only the relevant few
paragraphs instead of overwhelming the model's context window with
everything.



4. Communication Protocols

Component
What it is
Why it's here
A2A (Agent-to-Agent) protocol
An open protocol for one service to talk to a deployed agent
Used by the Cloud Run frontend to send messages to the deployed agent and stream back responses
A2UI
An open-source protocol/schema (a2ui.org) for agents to describe rich UI (cards, tables) as structured JSON instead of plain text
Lets the agent's answer render as a visual card (subject, status, error, remediation) instead of a wall of text
Application Default Credentials (ADC)
Google Cloud's standard mechanism for a service to authenticate as itself, without hardcoded keys
The Cloud Run frontend uses this to securely call the deployed agent, and the agent uses it to call Firestore/RAG Engine



5. Deployment & Infrastructure

Component
What it is
Why it's here
Vertex AI Agent Runtime (Reasoning Engine)
A managed hosting service specifically for deployed agents
Where the agent itself lives in production — handles scaling, session state, and exposes the A2A endpoint
Cloud Run
Google's serverless container platform
Hosts the frontend (FastAPI proxy + static chat UI) — scales to zero when idle, no server management
Docker
Container packaging
The frontend is packaged as a container image (via a Dockerfile) so Cloud Run can run it
IAM (Identity and Access Management)
Google Cloud's permission system
Used to grant the agent's service account roles/datastore.user (Firestore access) and the Cloud Run service account roles/aiplatform.user (so it can call the deployed agent)
gcloud CLI
Google Cloud's command-line tool
Underlying tool AGY uses for deployments, IAM grants, and resource lookups

Why two separate deployed services instead of one? Separation of
concerns and separately manageable identities/scaling — the frontend can be
redeployed or replaced without touching the agent, and each has only the
IAM permissions it actually needs (least privilege).



6. Testing & Quality

Component
What it is
Why it's here
pytest
Python's standard testing framework
Used for unit tests on the tool functions (e.g. verifying suggest_escalation logic)
ADK Playground (adk web)
A local browser-based dev UI bundled with ADK
Used for interactive testing before every deploy — lets you inspect sessions, traces (which tools fired), and raw tool responses
Manual QA scenario pass
A curated list of 9 test prompts covering every tool, edge cases (unknown IDs/codes), and multi-step orchestration
Used to verify the deployed agent (not just local) behaves correctly end-to-end



7. Version Control & Sharing

Component
What it is
Why it's here
Git / GitHub
Version control + hosting
The finished project is pushed to a public GitHub repo so it survives after the temporary lab environment is torn down
GitHub CLI (gh) device auth flow
A secure login flow using a one-time code instead of a password
Used to authenticate AGY to push to the user's personal GitHub account, separate from the lab's Google Cloud credentials
Personal Access Token (PAT)
A scoped credential used instead of a GitHub password for git push over HTTPS
GitHub requires this since password auth for git was deprecated



One-paragraph summary if your architect asks "what's the whole stack in one breath"

"It's a Python agent built on Google's ADK framework, running Gemini 2.5
Flash, deployed to Vertex AI Agent Runtime. It reads/writes Firestore for
structured data, does retrieval-augmented generation against a Vertex AI RAG
Engine corpus for grounded knowledge, applies a deterministic Python rule for
escalation decisions, and renders responses as A2UI cards. The whole thing
is fronted by a FastAPI proxy on Cloud Run that talks to the agent over the
A2A protocol using Application Default Credentials — no hardcoded secrets
anywhere in the code path."
