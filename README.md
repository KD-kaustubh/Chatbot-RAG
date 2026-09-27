# RAG Chatbot for the IITM BS in Data Science Program

A retrieval-augmented generation (RAG) chatbot that answers student questions about the IIT Madras BS in Data Science program — course content, degree structure, exam rules and policies — using the official course documents and student handbook as its only source of truth.

## How it works

1. **Routing** – An LLM reads the question and decides whether it is about a specific subject (e.g. "What will I learn in Computational Thinking?") or a general handbook question (e.g. "What are the rules for the end term exam?").
2. **Retrieval**
   - Subject questions get the full text of the matching subject document(s) from `subjects_db.json`.
   - Handbook questions run a semantic search over the handbook, stored in a local ChromaDB vector store.
3. **Answering** – The retrieved context is passed to the LLM with a strict prompt: answer only from the documents, and refuse anything outside them (including prompt-injection attempts).

The last few messages of the chat are sent along with each question, so follow-ups like "How is it graded?" work. The router rewrites them into a standalone question ("How is the Maths 1 course graded?") before searching.

### LLM providers and fallback

The app uses three LLM providers:

| Provider | Default model | Used for |
|----------|---------------|----------|
| [AI Pipe](https://aipipe.org) (OpenAI) | `gpt-4.1-mini` | Writing answers (first choice) |
| Google Gemini | `gemini-flash-latest` | Answers when AI Pipe is unavailable |
| Groq | `openai/gpt-oss-20b` | Routing questions (very fast), and last fallback for answers |

Answer order is AI Pipe → Gemini → Groq. Routing is a simple classification, so it runs on free Groq first to save the AI Pipe budget and Gemini quota for the answers. Each step falls back to the next provider: if one provider errors, times out, hits a rate limit or returns an empty response, the same request is retried on the next provider automatically. The terminal logs which provider answered each request.

Embeddings are generated locally with `all-MiniLM-L6-v2`, run through ONNX by ChromaDB, so retrieval needs no API and no PyTorch.

## Project structure

```
.
├── .streamlit/
│   └── config.toml         # Maroon theme for the Streamlit app
├── assets/
│   └── bot.svg             # Chat avatar for the Gradio app
├── config/
│   └── rag_prompts.yaml    # Router and answer prompt templates
├── Data/                   # Source .txt documents (handbook + one file per subject)
├── handbook_db/            # ChromaDB vector store (created by ingest.py, git-ignored)
├── subjects_db.json        # Full text of every subject document
├── ingest.py               # Builds the knowledge bases from Data/
├── chatbot.py              # Core RAG logic shared by all the apps
├── llm_providers.py        # AI Pipe/Gemini/Groq setup with automatic fallback
├── ui_content.py           # Text and styling shared by both web UIs
├── streamlit_app.py        # Streamlit web interface (used for deployment)
├── app.py                  # Gradio web interface
├── rag.py                  # Command-line chatbot
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
AI_PIPE="your_aipipe_token"
GEMINI_API_KEY="your_gemini_key"
GROQ_API_KEY="your_groq_key"
```
- AI Pipe token: https://aipipe.org (log in with your IITM account)
- Gemini key: https://aistudio.google.com/apikey
- Groq key: https://console.groq.com/keys

Any provider without a key is skipped, so the app runs with just one of them.

Optional settings in `.env`:
```
LLM_ORDER="aipipe,gemini,groq"       # provider order for answers, first one is primary
ROUTER_ORDER="groq,gemini,aipipe"    # provider order for routing
AIPIPE_MODEL="gpt-4.1-mini"
GEMINI_MODEL="gemini-flash-latest"
GROQ_MODEL="openai/gpt-oss-20b"
```

AI Pipe has a small weekly budget ($0.10 by default). One question costs about $0.002 with `gpt-4.1-mini` (~45 questions/week) and about $0.013 with `gpt-4o` (~7 questions/week). When the budget runs out, answers fall back to Gemini and Groq automatically.

**4. Knowledge base**

The app builds the handbook vector store (`handbook_db/`) automatically the first time it starts. If you change the files in `Data/`, rebuild everything with:
```bash
python ingest.py
```
This updates `handbook_db/` and regenerates `subjects_db.json`.

## Usage

Both web interfaces have the same IITM-style maroon design, a "Program at a glance" sidebar and suggested questions, and work on phones.

**Streamlit web interface**
```bash
streamlit run streamlit_app.py
```
Opens http://localhost:8501 in your browser.

**Gradio web interface**
```bash
python app.py
```
Open http://127.0.0.1:7860 in your browser.

**Command line**
```bash
python rag.py
```
Type `exit` to quit.

## Deploying to Streamlit Community Cloud

The app deploys straight from this GitHub repo, for free.

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub** and fill in:
   - **Repository:** `KD-kaustubh/Chatbot-RAG`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** pick a name, e.g. `iitm-bs-assistant`
3. Open **Advanced settings**, choose **Python 3.12**, and paste your keys into **Secrets** (TOML format):
   ```toml
   AI_PIPE = "your_aipipe_token"
   GEMINI_API_KEY = "your_gemini_key"
   GROQ_API_KEY = "your_groq_key"
   ```
4. Click **Deploy**. The first start takes a few minutes: it installs the packages, downloads the embedding model and builds `handbook_db/`.

Every push to `main` redeploys the app automatically. Keys can be changed later from the app's **Settings → Secrets**.

Notes:
- Anyone with the link uses your API keys. The AI Pipe budget is small, so once it runs out answers come from Gemini and Groq.
- Free apps go to sleep after a while without visitors. The next visitor sees a "wake up" button, and the app is back in about a minute.

## Example questions

- What will I learn in the Computational Thinking course?
- Tell me about the foundational level subjects.
- What are the eligibility rules to write the end term exam?
- What is the difference between Machine Learning Foundations and Machine Learning Techniques?

Out-of-scope questions ("What is the capital of France?") and prompt-injection attempts get a polite refusal:
> I'm sorry, I cannot answer that question as the information is not in the provided documents.

## Tech stack

- **Framework:** LangChain
- **LLMs:** OpenAI via AI Pipe (answers), Google Gemini (fallback), Groq (routing + fallback)
- **Vector store:** ChromaDB
- **Embeddings:** `all-MiniLM-L6-v2` (ONNX, via ChromaDB)
- **UI:** Gradio
- **Config & validation:** PyYAML, python-dotenv, Pydantic
