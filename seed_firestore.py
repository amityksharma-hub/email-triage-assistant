import json
import os
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-e10e0dbf7912"

EMAILS = [
  {"email_id": "EMAIL-1001", "subject": "Invoice #48213 - Please process for payment", "sender": "billing@acme-vendor.com", "status": "Failed", "received_date": "2026-09-18T09:14:00Z", "error_code": "ERR-401"},
  {"email_id": "EMAIL-1002", "subject": "Claim documentation attached - policy 88213", "sender": "claims@northwind-insurance.com", "status": "Processed", "received_date": "2026-09-18T10:02:00Z", "error_code": None},
  {"email_id": "EMAIL-1003", "subject": "Scanned contract - urgent review needed", "sender": "legal.docs@partnerfirm.com", "status": "Failed", "received_date": "2026-09-19T08:47:00Z", "error_code": "ERR-502"},
  {"email_id": "EMAIL-1004", "subject": "Re: Renewal notice for account 7745", "sender": "renewals@acme-vendor.com", "status": "Failed", "received_date": "2026-09-19T11:30:00Z", "error_code": "ERR-408"},
  {"email_id": "EMAIL-1005", "subject": "Weekly reconciliation report", "sender": "reports@internal-finance.com", "status": "Processed", "received_date": "2026-09-19T13:05:00Z", "error_code": None},
  {"email_id": "EMAIL-1006", "subject": "Updated W-9 form attached", "sender": "vendor.onboarding@supplyco.com", "status": "Failed", "received_date": "2026-09-20T07:58:00Z", "error_code": "ERR-422"},
  {"email_id": "EMAIL-1007", "subject": "Batch export - customer records Q3", "sender": "no-reply@crm-export.com", "status": "Received", "received_date": "2026-09-20T09:20:00Z", "error_code": None},
  {"email_id": "EMAIL-1008", "subject": "URGENT: Wire transfer confirmation needed", "sender": "unknown-sender@mailer-promo.ru", "status": "Failed", "received_date": "2026-09-20T12:41:00Z", "error_code": "ERR-450"},
  {"email_id": "EMAIL-1009", "subject": "Password protected statement - Sept cycle", "sender": "statements@acme-vendor.com", "status": "Failed", "received_date": "2026-09-21T06:33:00Z", "error_code": "ERR-500"},
  {"email_id": "EMAIL-1010", "subject": "Case escalation - ticket #55210", "sender": "support@partnerfirm.com", "status": "Failed", "received_date": "2026-09-21T15:12:00Z", "error_code": "ERR-504"}
]

LOGS = [
  {"email_id": "EMAIL-1001", "error_message": "Authentication to Dataverse failed: token expired for service account svc-email-processor@acme.onmicrosoft.com", "flow_name": "Invoice-Intake-Flow", "timestamp": "2026-09-18T09:14:22Z", "severity": "Critical"},
  {"email_id": "EMAIL-1003", "error_message": "PDF merge step aborted: attachment size 41.2MB exceeds 25MB threshold", "flow_name": "Contract-Ingestion-Flow", "timestamp": "2026-09-19T08:47:41Z", "severity": "Error"},
  {"email_id": "EMAIL-1004", "error_message": "Timeout after 30000ms calling mail-relay-api /v2/send-confirmation", "flow_name": "Renewal-Notice-Flow", "timestamp": "2026-09-19T11:30:58Z", "severity": "Warning"},
  {"email_id": "EMAIL-1006", "error_message": "Schema validation failed: missing required header 'Message-ID' in inbound MIME payload", "flow_name": "Vendor-Onboarding-Flow", "timestamp": "2026-09-20T07:58:15Z", "severity": "Error"},
  {"email_id": "EMAIL-1008", "error_message": "Message quarantined by security gateway: sender domain flagged by heuristic spam filter", "flow_name": "Inbound-Security-Flow", "timestamp": "2026-09-20T12:41:09Z", "severity": "Critical"},
  {"email_id": "EMAIL-1009", "error_message": "Unhandled exception in PDF parser: attachment is password-protected, cannot extract text", "flow_name": "Statement-Processing-Flow", "timestamp": "2026-09-21T06:33:47Z", "severity": "Error"},
  {"email_id": "EMAIL-1010", "error_message": "Gateway timeout calling case-management API /v1/cases/create, HTTP 504", "flow_name": "Case-Escalation-Flow", "timestamp": "2026-09-21T15:12:33Z", "severity": "Critical"}
]

def seed():
    # Save local seed copy
    seed_data = {"emails": EMAILS, "logs": LOGS}
    os.makedirs("data", exist_ok=True)
    with open("data/seed_data.json", "w") as f:
        json.dump(seed_data, f, indent=2)
    print("Saved local seed_data.json")

    # Seed GCP Firestore if available
    try:
        db = firestore.Client(project=PROJECT_ID)
        print(f"Connecting to Firestore in project: {PROJECT_ID}")
        
        emails_ref = db.collection("emails")
        for email_data in EMAILS:
            doc_id = email_data["email_id"]
            emails_ref.document(doc_id).set(email_data)

        logs_ref = db.collection("logs")
        for log_data in LOGS:
            doc_id = log_data["email_id"]
            logs_ref.document(doc_id).set(log_data)

        print("GCP Firestore seeded successfully!")
    except Exception as e:
        print(f"Note on GCP Firestore: {e}")
        print("Fallback local database initialized for agent query operations.")

if __name__ == "__main__":
    seed()
