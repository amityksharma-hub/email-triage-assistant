# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import re
from typing import Any, Dict, List, Optional
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.8-flash"
PROJECT_ID = "qwiklabs-gcp-01-e10e0dbf7912"


def _get_firestore_client() -> Optional[firestore.Client]:
    """Helper to initialize Firestore client with project ID."""
    try:
        return firestore.Client(project=PROJECT_ID)
    except Exception:
        return None


def _load_local_data() -> Dict[str, Any]:
    """Helper fallback to load local seeded data."""
    paths = [
        os.path.join(os.path.dirname(__file__), "data", "seed_data.json"),
        os.path.join(os.path.dirname(__file__), "seed_data.json"),
        os.path.join(os.path.dirname(__file__), "..", "data", "seed_data.json"),
    ]
    for seed_path in paths:
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
    return {"emails": [], "logs": []}


def search_failed_emails(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Queries the Firestore 'emails' collection for emails with status='Failed'.

    Args:
        start_date: Optional ISO date string (YYYY-MM-DD) to filter received_date from.
        end_date: Optional ISO date string (YYYY-MM-DD) to filter received_date to.

    Returns:
        Dict containing total count and list of failed email records.
    """
    db = _get_firestore_client()
    failed_emails = []

    if db:
        try:
            query = db.collection("emails").where("status", "==", "Failed")
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict()
                rec_date = data.get("received_date", "")
                if start_date and rec_date < start_date:
                    continue
                if end_date and rec_date > end_date:
                    continue
                failed_emails.append(data)
            if failed_emails:
                return {
                    "count": len(failed_emails),
                    "failed_emails": failed_emails,
                }
        except Exception:
            pass

    # Fallback to local dataset
    local_data = _load_local_data()
    for email in local_data.get("emails", []):
        if email.get("status") == "Failed":
            rec_date = email.get("received_date", "")
            if start_date and rec_date < start_date:
                continue
            if end_date and rec_date > end_date:
                continue
            failed_emails.append(email)

    return {
        "count": len(failed_emails),
        "failed_emails": failed_emails,
    }


def get_email_error_detail(email_id: str) -> Dict[str, Any]:
    """Queries the Firestore 'logs' collection for error details corresponding to an email_id.

    Args:
        email_id: The ID of the email to look up log error details for (e.g. EMAIL-1001).

    Returns:
        Dict containing error message, flow name, timestamp, and severity.
    """
    db = _get_firestore_client()
    if db:
        try:
            doc = db.collection("logs").document(email_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            pass

    # Fallback to local dataset
    local_data = _load_local_data()
    for log in local_data.get("logs", []):
        if log.get("email_id") == email_id:
            return log

    return {"error": f"No error logs found for email_id {email_id}"}


def consult_error_reference(error_code: str) -> Dict[str, Any]:
    """Queries the Known Error Codes RAG Corpus reference document for common cause and remediation guidance.

    Args:
        error_code: The error code string (e.g. 'ERR-401', 'ERR-502', 'ERR-504').

    Returns:
        Dict containing error code, explanation, common cause, and recommended remediation steps.
    """
    code_str = str(error_code).strip().upper()
    if not code_str.startswith("ERR-") and code_str.isdigit():
        code_str = f"ERR-{code_str}"

    ref_paths = [
        os.path.join(os.path.dirname(__file__), "error_codes_reference.txt"),
        os.path.join(os.path.dirname(__file__), "..", "error_codes_reference.txt"),
    ]
    content = ""
    for path in ref_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    content = f.read()
                if content:
                    break
            except Exception:
                pass

    if content:
        blocks = content.strip().split("\n\n")
        for block in blocks:
            if block.startswith(code_str):
                # Extract cause and remediation
                cause_match = re.search(r"Common cause:(.*?)(?=\. Remediation:|\.|$)", block)
                rem_match = re.search(r"Remediation:(.*?)(?=\.|$)", block)
                desc_match = re.search(r"^" + re.escape(code_str) + r":\s*(.*?)(?=\. Common cause:|\.|$)", block)

                return {
                    "error_code": code_str,
                    "description": desc_match.group(1).strip() if desc_match else "",
                    "common_cause": cause_match.group(1).strip() if cause_match else "",
                    "remediation": rem_match.group(1).strip() if rem_match else "",
                    "full_reference": block.strip(),
                }

    return {
        "error_code": code_str,
        "error": f"No error code reference found for {code_str}",
    }


def suggest_escalation(email_id: str) -> Dict[str, Any]:
    """Determines whether an email error should be escalated to the platform team.

    Evaluates rule-based criteria:
    1. Severity is 'Critical' in the log entry.
    2. The email's error_code appears 3 or more times across logs/failed emails.

    Args:
        email_id: The ID of the email to evaluate (e.g. EMAIL-1001).

    Returns:
        Dict containing email_id, recommend_escalation (bool), reason, and recommended_action.
    """
    log_detail = get_email_error_detail(email_id)
    if "error" in log_detail:
        return {
            "email_id": email_id,
            "recommend_escalation": False,
            "reason": f"No logs found for email {email_id}",
            "recommended_action": "Standard L1/L2 investigation",
        }

    severity = log_detail.get("severity", "")
    is_critical = severity == "Critical"

    # Fetch email doc to get error_code
    error_code = None
    all_failed = search_failed_emails().get("failed_emails", [])
    for email in all_failed:
        if email.get("email_id") == email_id:
            error_code = email.get("error_code")
            break

    # Count occurrences of error_code across all failed emails
    code_count = 0
    if error_code:
        code_count = sum(1 for e in all_failed if e.get("error_code") == error_code)

    repeats_exceeded = code_count >= 3

    if is_critical or repeats_exceeded:
        reasons = []
        if is_critical:
            reasons.append("Log severity is Critical")
        if repeats_exceeded:
            reasons.append(f"Error code {error_code} repeated {code_count} times (threshold: >=3)")

        return {
            "email_id": email_id,
            "recommend_escalation": True,
            "severity": severity,
            "error_code": error_code,
            "error_code_occurrences": code_count,
            "reason": "; ".join(reasons),
            "recommended_action": "Escalate to Platform Engineering Team immediately.",
        }

    return {
        "email_id": email_id,
        "recommend_escalation": False,
        "severity": severity,
        "error_code": error_code,
        "error_code_occurrences": code_count,
        "reason": f"Severity is {severity} and error code occurrences ({code_count}) < 3 threshold",
        "recommended_action": "Standard L1/L2 remediation using consult_error_reference",
    }


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are an agentic Email Triage Assistant for L1/L2 support analysts."
        " Your goal is to troubleshoot failed email processing using search_failed_emails,"
        " get_email_error_detail, consult_error_reference, and suggest_escalation."
    ),
    workflow_description=(
        "Query tool data for failed emails, error logs, and RAG remediation guidance,"
        " then render the results as structured A2UI card surfaces."
    ),
    ui_description=(
        "Render failed email triage results as flat A2UI Card surfaces. "
        "Each card surface must display: Subject, Status badge, Error code, Error message, "
        "Severity level, and Remediation guidance from the consult_error_reference tool. "
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, Divider, List. Do not use Table or Heading. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in <a2a_datapart_json> tags."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="email_triage_assistant",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        search_failed_emails,
        get_email_error_detail,
        consult_error_reference,
        suggest_escalation,
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
