"""Minimal FastAPI proxy for Email Triage Assistant (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import json
import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from google.protobuf.json_format import MessageToDict

from a2a.client import ClientConfig, create_client
from a2a.types import Message, Part, Role, SendMessageRequest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)

_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI(title="Email Triage Assistant Proxy")


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}


def _extract_parts(parts: list) -> list[dict]:
    """Filter out intermediate debug/tool events and return clean user-facing parts."""
    out: list[dict] = []
    for p in parts:
        try:
            d = MessageToDict(p) if hasattr(p, "DESCRIPTOR") else (p if isinstance(p, dict) else {})
        except Exception:
            continue

        # 1. Text part
        text_val = d.get("text")
        if text_val:
            s_text = str(text_val).strip()
            if s_text and not s_text.startswith("struct_value") and "fields {" not in s_text:
                out.append({"kind": "text", "text": s_text})
            continue

        # 2. Data part
        data_field = d.get("data")
        if isinstance(data_field, dict):
            # Ignore intermediate tool call / response debug parts
            if "name" in data_field or "args" in data_field or "response" in data_field:
                continue

            metadata = d.get("metadata") or {}
            if metadata.get("adk_type") in ("function_call", "function_response"):
                continue

            inner_meta = data_field.get("metadata") or {}
            inner_mime = inner_meta.get("mimeType") if isinstance(inner_meta, dict) else None
            inner_data = data_field.get("data")

            if inner_mime == _A2UI_MIME or metadata.get("mimeType") == _A2UI_MIME:
                target = inner_data if inner_data is not None else data_field
                out.append({"kind": "a2ui", "data": target})
                continue

            if isinstance(inner_data, dict) and ("beginRendering" in inner_data or "surfaceUpdate" in inner_data):
                out.append({"kind": "a2ui", "data": inner_data})
                continue
            elif isinstance(data_field, dict) and ("beginRendering" in data_field or "surfaceUpdate" in data_field):
                out.append({"kind": "a2ui", "data": data_field})
                continue

    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120.0) as client:
        a2a_client = await create_client(
            A2A_BASE,
            client_config=ClientConfig(httpx_client=client)
        )

        user_role = getattr(Role, "ROLE_USER", getattr(Role, "user", "ROLE_USER"))

        context_id = _contexts.get(user_id)
        msg_kwargs = {
            "message_id": str(uuid.uuid4()),
            "role": user_role,
            "parts": [Part(text=message)],
        }
        if context_id:
            msg_kwargs["context_id"] = context_id

        msg = Message(**msg_kwargs)
        send_req = SendMessageRequest(message=msg)

        async for event in a2a_client.send_message(send_req):
            candidate_parts = []
            if hasattr(event, "artifact_update") and event.artifact_update:
                au = event.artifact_update
                cid = getattr(au, "context_id", None)
                if cid:
                    _contexts[user_id] = cid
                art = getattr(au, "artifact", None)
                if art and hasattr(art, "parts"):
                    candidate_parts.extend(art.parts)

            if hasattr(event, "message") and event.message:
                m = event.message
                cid = getattr(m, "context_id", None)
                if cid:
                    _contexts[user_id] = cid
                if hasattr(m, "parts"):
                    candidate_parts.extend(m.parts)

            if hasattr(event, "status_update") and event.status_update:
                su = event.status_update
                cid = getattr(su, "context_id", None)
                if cid:
                    _contexts[user_id] = cid

            if candidate_parts:
                parts.extend(_extract_parts(candidate_parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
