"""
Core RAG logic shared by the command-line app (rag.py) and the web app (app.py).
"""
import os
import json
import yaml
from dotenv import load_dotenv
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from llm_providers import (
    load_models, invoke_with_fallback, with_schema,
    DEFAULT_ROUTER_ORDER, DEFAULT_ANSWER_ORDER,
)
from typing import List, Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from chromadb.errors import NotFoundError
from ingest import ingest_handbook, HANDBOOK_DB_PATH, EMBEDDING_MODEL_NAME



load_dotenv()

# DEFINE PATHS TO OUR DATABASE AND CONFIG
HANDBOOK_PATH = "Data/handbook.txt"
SUBJECTS_DB_PATH = "subjects_db.json"
PROMPT_CONFIG_PATH = "config/rag_prompts.yaml"

# More subjects than this means a broad question, which the handbook answers better.
# It also keeps the prompt under Groq's free-tier limit of 8k tokens per minute.
MAX_SUBJECTS = 3

# How much of the conversation is sent with each question
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS = 600

SERVICE_BUSY_MESSAGE = (
    "Sorry, the AI service is busy right now and I couldn't get an answer. "
    "Please try again in a minute."
)


def load_json_db(file_path: str) -> Dict[str, Any]:
    """
    Loads the subjects json database from specified path.
    """
    with open(file_path, 'r', encoding="utf-8") as f:
        return json.load(f)


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """
    Loads a YAML configuration files.
    """
    with open(file_path, 'r', encoding="utf-8") as f:
        return yaml.safe_load(f)


print("Initializing components... Please wait.")

subjects_db = load_json_db(SUBJECTS_DB_PATH)

prompt_configs = load_yaml_config(PROMPT_CONFIG_PATH)

embedding_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_NAME
)

handbook_client = chromadb.PersistentClient(path=HANDBOOK_DB_PATH)
try:
    handbook_collection = handbook_client.get_collection(name="handbook")
except NotFoundError:
    # handbook_db/ is not in git, so a fresh clone or deployment builds it on first start
    print("Handbook database not found, building it now (first start only)...")
    ingest_handbook(HANDBOOK_PATH, handbook_client, embedding_model)
    handbook_collection = handbook_client.get_collection(name="handbook")

router_models = load_models("ROUTER_ORDER", DEFAULT_ROUTER_ORDER)
answer_models = load_models("LLM_ORDER", DEFAULT_ANSWER_ORDER)

print("Initialisation Complete. All components are ready.")
print("-" * 50)


#  ----  LLM ROUTER LOGIC ----

class RouterOutput(BaseModel):
    """
    Defines the structured output for the router's decision.
    """
    query_type: Literal["subject_content", "general_handbook_query"] = Field(description="The type of query. Either 'subject_content' or 'general_handbook_query'.")
    subjects: List[str] = Field(description="A list of specific subject keyword found in user's question. Should be an empty list if query_type is 'general_handbook_query'.")
    search_query: str = Field(description="The user's question rewritten as a standalone question, resolving references like 'it' from the conversation.")



#  ----  CHAT HISTORY ----

def _message_text(content: Any) -> str:
    """
    Gradio can give message content as a plain string or as a list of parts.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content or "")


def format_history(history: Optional[List[Dict[str, Any]]]) -> str:
    """
    Turns the last few chat messages into plain text for the prompts.
    Long answers are cut short to keep the prompt small.
    """
    if not history:
        return "(no previous conversation)"

    lines = []
    for message in history[-MAX_HISTORY_MESSAGES:]:
        role = "User" if message.get("role") == "user" else "Assistant"
        text = _message_text(message.get("content")).strip()
        if len(text) > MAX_HISTORY_CHARS:
            text = text[:MAX_HISTORY_CHARS] + "..."
        lines.append(f"{role}: {text}")
    return "\n".join(lines)



#  ----  LLM ROUTER LOGIC ----

def get_router_decision(user_question: str, chat_history: str) -> RouterOutput:
    """
    Uses an LLM to classify the user's question and extract subject keywords.
    """
    subject_keywords = list(subjects_db.keys())

    prompt = PromptTemplate(
        template=prompt_configs['router_prompt'],
        input_variables=["user_question", "subject_keywords", "chat_history"]
    )

    try:
        return invoke_with_fallback(
            router_models,
            lambda model: prompt | with_schema(model, RouterOutput),
            {
                "user_question" : user_question,
                "subject_keywords" : subject_keywords,
                "chat_history" : chat_history
            }
        )
    except RuntimeError:
        # Routing is only a hint, so fall back to a handbook search instead of failing.
        print("Router unavailable, defaulting to handbook search.")
        return RouterOutput(query_type="general_handbook_query", subjects=[], search_query=user_question)



#   ------ CONTEXT RETRIEVAL LOGIC -----
def retrieve_context(user_question: str, decision: RouterOutput) -> str:
    """
    Retrieves the appropriate context based on the router's decision.
    """
    query_type = decision.query_type
    # Keep only subjects that really exist, without duplicates
    subjects = [s for s in dict.fromkeys(decision.subjects) if s in subjects_db]

    if query_type == "subject_content" and not 1 <= len(subjects) <= MAX_SUBJECTS:
        print(f"Router picked {len(subjects)} valid subject(s), using handbook search instead.")
        query_type = "general_handbook_query"

    print(f"Router decided query type is {query_type}")

    if query_type == "subject_content":
        print(f"Retrieving content for subject(s): {subjects}")
        context = "\n\n".join(subjects_db[subject_key] for subject_key in subjects)

    else:
        # The standalone version finds better matches for follow-ups like "what about its fees?"
        search_query = decision.search_query.strip() or user_question
        print(f"Performing vector search on the handbook for: {search_query}")

        query_vector = embedding_model.embed_query(search_query)

        results = handbook_collection.query(
            query_embeddings=[query_vector],
            n_results=10,
            include=["documents"]
        )
        context = "\n\n----\n\n".join(results["documents"][0])

    return context



#   ------ ANSWER GENERATION -----
def answer_question(user_question: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Runs the full pipeline for one question: route -> retrieve -> generate.
    history is the previous messages as [{"role": "user" | "assistant", "content": ...}].
    """
    chat_history = format_history(history)

    decision = get_router_decision(user_question, chat_history)

    context = retrieve_context(user_question, decision)

    prompt = PromptTemplate(
        template=prompt_configs['rag_final_prompt'],
        input_variables=["context", "question", "chat_history"]
    )

    try:
        ai_response = invoke_with_fallback(
            answer_models,
            lambda model: prompt | model,
            {
                "context": context,
                "question": user_question,
                "chat_history": chat_history
            }
        )
    except RuntimeError:
        return SERVICE_BUSY_MESSAGE

    return ai_response.text
