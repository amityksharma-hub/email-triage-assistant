Presentation Script — Email Triage Assistant

*A spoken walkthrough for presenting Architecture_Overview.md to your
architect. Read section by section, pausing to show the matching diagram.*



Opening (30 sec)

"This is a POC I built during the Gemini World Tour lab — an agentic
assistant for L1/L2 support analysts. Instead of manually checking a
database, opening flow logs, and searching a wiki for what an error code
means, the analyst just asks the agent in plain language, and it does all
three lookups and gives back a structured answer."



1. Executive Summary

"The core idea is that this isn't just a chatbot with a database attached.
It's four distinct concerns working together: structured data for facts,
a knowledge base for grounded explanations, deterministic rules for
decisions that need to be consistent, and the **LLM only for orchestration
and language** — deciding which tool to call and phrasing the final answer.
I'll show you why that separation matters in a minute."



2. System Architecture (show the flowchart)

"There are two separately deployed services here, and that's intentional.
The agent itself runs on Vertex AI Agent Runtime — that's a managed
service, so I don't manage servers for it. Then there's a Cloud Run
service that's just a thin FastAPI proxy plus the chat UI. The browser only
ever talks to Cloud Run. Cloud Run then talks to the agent using something
called the A2A protocol — Agent-to-Agent — authenticated with
Application Default Credentials, so there's no API key floating around in
the frontend code.

The reason I split it this way: each service has its own identity and its
own IAM permissions. If I need to scale the frontend independently, or swap
it for a different UI entirely, the agent doesn't need to change at all."



3. Functional / Data Structure (show the tables)

"Underneath, there's really just three things: two Firestore collections —
emails and logs — and one knowledge corpus. emails is the source of
truth for what came in and its status. logs is the operational detail —
what actually broke, and how severe it was. Those are joined by email_id.

The fourth piece, error_codes_reference.txt, is indexed into a **Vertex AI
RAG Engine** corpus. That's deliberately a separate artifact from the live
data — it's a runbook. Ops can update remediation guidance without touching
the data pipeline at all, and vice versa."



4. Function Tools (show the tools table)

"There are four tools the agent can call. Two are plain Firestore reads.
One does the RAG lookup. And the fourth — suggest_escalation — is
deliberately not an LLM decision. It's a plain Python rule: escalate if
severity is Critical, or if the same error code has happened three or more
times. I made that a hard rule on purpose, because an escalation decision
needs to be the same every time given the same input — you don't want that
varying between model runs."



5. RAG Flow (show the sequence diagram — this is usually the part architects ask most about)

"This is the part worth walking through carefully. Say the analyst asks 'why
did this email fail.' First hop: the agent calls Firestore, gets the raw log
— error code, severity. Second hop: it takes that error code and calls
consult_error_reference, which embeds the code and does a vector
similarity search against the indexed corpus. That's the actual RAG step —
it's retrieving the matching passage, not generating an explanation from
scratch.

If the corpus call fails for any reason — indexing lag, a transient
permission issue — there's a fallback: the same reference file is bundled
locally with the agent's code, and it does a keyword match instead. That's
a resilience choice, not the primary path.

Then the model combines both pieces — the Firestore fact and the RAG
passage — into one answer. The important thing to emphasize: the model
never invents the meaning of an error code. If the corpus has no match, it
says so rather than guessing."



6. Response Rendering / A2UI (show the last diagram)

"Last piece — the output isn't plain text, it's a structured card. There's
an open protocol called A2UI that lets the model emit a small JSON
schema describing a card layout, and a renderer on the frontend turns that
into the visual card you'll see in the demo. That's done through a callback
that intercepts the model's raw output before it reaches the frontend."



Closing (30 sec)

"So end to end: analyst asks a question in plain English, the agent
orchestrates Firestore for facts, RAG for grounded knowledge, a rule engine
for consistent decisions, and renders it all as a card — deployed as two
independently scalable services on Google Cloud. Happy to go deeper on any
one piece — data model, the RAG setup, or the deployment side."



*(If asked "what would you change for production": mention removing the
hardcoded project ID / bucket names — currently required due to how Agent
Runtime resolves the deployed service account's project — and adding
Memory Bank if per-analyst personalization becomes valuable.)*
