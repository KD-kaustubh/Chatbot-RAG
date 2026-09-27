# RAG Chatbot for the IITM BS in Data Science Program

A retrieval-augmented generation (RAG) chatbot that answers student questions about the IIT Madras BS in Data Science program — course content, degree structure, exam rules and policies — using the official course documents and student handbook as its only source of truth.

## How it works

1. **Routing** – An LLM reads the question and decides whether it is about a specific subject (e.g. "What will I learn in Computational Thinking?") or a general handbook question (e.g. "What are the rules for the end term exam?").
2. **Retrieval**
   - Subject questions get the full text of the matching subject document(s) from `subjects_db.json`.
   - Handbook questions run a semantic search over the handbook, stored in a local ChromaDB vector store.
3. **Answering** – The retrieved context is passed to the LLM with a strict prompt: answer only from the documents, and refuse anything outside them (including prompt-injection attempts).

### LLM providers and fallback

The app uses two LLM providers:

| Order | Provider | Default model | Why |
|-------|----------|---------------|-----|
| 1 | Google Gemini | `gemini-flash-latest` | More accurate, stays closer to the source documents |
| 2 | Groq | `openai/gpt-oss-20b` | Very fast and reliable, used as fallback |

If the primary provider errors, times out, hits a rate limit or returns an empty response, the same request is retried on the next provider automatically. The terminal logs which provider answered each request.

Embeddings are generated locally with `sentence-transformers/all-MiniLM-L6-v2`, so no API is needed for retrieval.

## Project structure

```
.
├── config/
│   └── rag_prompts.yaml    # Router and answer prompt templates
├── Data/                   # Source .txt documents (handbook + one file per subject)
├── handbook_db/            # ChromaDB vector store (created by ingest.py, git-ignored)
├── subjects_db.json        # Full text of every subject document
├── ingest.py               # Builds the knowledge bases from Data/
├── llm_providers.py        # Gemini/Groq setup with automatic fallback
├── rag.py                  # Command-line chatbot
├── app.py                  # Gradio web interface
└── requirements.txt
```

## Setup

**1. Clone and create a virtual environment**
```bash
git clone https://github.com/KD-kaustubh/Chatbot-RAG.git
cd Chatbot-RAG

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API keys**

Create a `.env` file in the project root:
```
GEMINI_API_KEY="your_gemini_key"
GROQ_API_KEY="your_groq_key"
```
- Gemini key: https://aistudio.google.com/apikey
- Groq key: https://console.groq.com/keys

You can run with just one of the two keys — the missing provider is skipped.

Optional settings in `.env`:
```
LLM_ORDER="gemini,groq"              # provider order, first one is primary
GEMINI_MODEL="gemini-flash-latest"
GROQ_MODEL="openai/gpt-oss-20b"
```

**4. Build the knowledge base (run once)**
```bash
python ingest.py
```
This creates `handbook_db/` and regenerates `subjects_db.json` from the files in `Data/`.

## Usage

**Web interface**
```bash
python app.py
```
Open http://127.0.0.1:7860 in your browser.

**Command line**
```bash
python rag.py
```
Type `exit` to quit.

## Example questions

- What will I learn in the Computational Thinking course?
- Tell me about the foundational level subjects.
- What are the eligibility rules to write the end term exam?
- What is the difference between Machine Learning Foundations and Machine Learning Techniques?

Out-of-scope questions ("What is the capital of France?") and prompt-injection attempts get a polite refusal:
> I'm sorry, I cannot answer that question as the information is not in the provided documents.

## Tech stack

- **Framework:** LangChain
- **LLMs:** Google Gemini (primary), Groq (fallback)
- **Vector store:** ChromaDB
- **Embeddings:** Hugging Face `sentence-transformers/all-MiniLM-L6-v2`
- **UI:** Gradio
- **Config & validation:** PyYAML, python-dotenv, Pydantic
