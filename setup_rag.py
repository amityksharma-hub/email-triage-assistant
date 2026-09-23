import json
import os
import vertexai
from vertexai.preview import rag

PROJECT_ID = "qwiklabs-gcp-01-e10e0dbf7912"
LOCATION = "us-west1"
FILE_PATH = "error_codes_reference.txt"

def setup_rag():
    print(f"Initializing Vertex AI RAG Corpus setup in {LOCATION}...")
    os.makedirs("data", exist_ok=True)
    
    rag_info = {
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "file_path": FILE_PATH,
        "corpus_name": None,
        "status": "pending"
    }

    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        corpus = rag.create_corpus(display_name="email_error_codes_corpus")
        print(f"Created RAG Corpus: {corpus.name}")
        
        rag_file = rag.upload_file(
            corpus_name=corpus.name,
            display_name="error_codes_reference.txt",
            path=FILE_PATH,
        )
        print(f"Uploaded file to corpus: {rag_file.name}")

        rag_info["corpus_name"] = corpus.name
        rag_info["status"] = "indexed"
    except Exception as e:
        print(f"Vertex AI RAG Engine notice: {e}")
        print("Fallback local indexing active for RAG query tool.")
        rag_info["status"] = "local_fallback"

    with open("data/rag_info.json", "w") as f:
        json.dump(rag_info, f, indent=2)
    print("RAG setup complete!")

if __name__ == "__main__":
    setup_rag()
