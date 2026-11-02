"""
Core RAG logic shared by the command-line app (rag.py) and the web apps (app.py, streamlit_app.py).
"""
import os
import json
import yaml
from dotenv import load_dotenv
import chromadb
from llm_providers import (
    load_models, invoke_with_fallback, with_schema,
    DEFAULT_ROUTER_ORDER, DEFAULT_ANSWER_ORDER,
)
from typing import List, Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from chromadb.errors import NotFoundError
from ingest import (
    ingest_handbook, ingest_grading, split_grading_sections, file_hash, load_embedding_function,
    HANDBOOK_DB_PATH, GRADING_PATH, GRADING_TERM, KEY_DATES_TITLE,
)



load_dotenv()

# DEFINE PATHS TO OUR DATABASE AND CONFIG
HANDBOOK_PATH = "Data/handbook.txt"
SUBJECTS_DB_PATH = "subjects_db.json"
PROMPT_CONFIG_PATH = "config/rag_prompts.yaml"

# More subjects than this means a broad question, which the handbook answers better.
# It also keeps the prompt under Groq's free-tier limit of 8k tokens per minute.
MAX_SUBJECTS = 3

# Total size of the subject documents + their grading sections sent with one question
MAX_SUBJECT_CONTEXT_CHARS = 18000

# Chunks taken from each source for general (non-subject) questions
GRADING_RESULTS = 5
HANDBOOK_RESULTS = 5

# How much of the conversation is sent with each question
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS = 600

# Subject documents in Data/ -> course code of their section in the grading document
SUBJECT_COURSE_CODES = {
    "Maths1": "MA1001", "English1": "HS1001", "Computational_Thinking(CT)": "CS1001",
    "Stats1": "MA1002", "Maths2": "MA1003", "English2": "HS1002",
    "Python_Programming": "CS1002", "Stats2": "MA1004",
    "Machine_learning_foundation(MLF)": "CS2004", "Machine_learning_technique(MLT)": "CS2007",
    "Machine_learning_practise(MLP)": "CS2008", "Bussiness_data_management(BDM)": "MS2001",
    "Bussiness_analytics(BA)": "MS2002", "Tools_in_data_science(TDS)": "SE2002",
    "Data_structures_algorithm_in_python(PDSA)": "CS2002", "Database_management_system(DBMS)": "CS2001",
    "Modern_app_dev_1(MAD1)": "CS2003", "Programming_in_java": "CS2005",
    "System_commands(SC)": "SE2001", "Modern_app_dev_2(MAD2)": "CS2006",
    "Intro_to_dl_and_genAI": "DA2001",
}
# Project subjects get the "Project Courses" section of the grading document instead
PROJECT_SUBJECTS = {
    "Bussiness_data_management_project(BDMProject)", "Machine_learning_practise_project(MLPProject)",
    "Modern_app_dev_project_1(MAD1Project)", "Modern_app_dev_project_2(MAD2Project)",
    "Intro_to_dl_and_genAI_Project",
}

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

embedding_function = load_embedding_function()

handbook_client = chromadb.PersistentClient(path=HANDBOOK_DB_PATH)
try:
    handbook_collection = handbook_client.get_collection(name="handbook")
except NotFoundError:
    # handbook_db/ is not in git, so a fresh clone or deployment builds it on first start
    print("Handbook database not found, building it now (first start only)...")
    ingest_handbook(HANDBOOK_PATH, handbook_client, embedding_function)
    handbook_collection = handbook_client.get_collection(name="handbook")

# Current term's grading document: per-course sections for subject questions,
# and its own vector index for general questions.
with open(GRADING_PATH, encoding="utf-8") as f:
    grading_sections = split_grading_sections(f.read())
grading_by_code = {s["code"]: s for s in grading_sections if s["code"]}
project_grading_section = next(s for s in grading_sections if s["title"] == "Project Courses")
# Only the summary lines, not the raw schedule tables that follow them in the same section
key_dates_text = next(s for s in grading_sections if s["title"] == KEY_DATES_TITLE)["text"].split("\n\n")[0]

try:
    grading_collection = handbook_client.get_collection(name="grading")
    if (grading_collection.metadata or {}).get("source_hash") != file_hash(GRADING_PATH):
        raise NotFoundError("grading document changed")
except NotFoundError:
    # first start, or the grading document was replaced with a newer one
    print("Building the grading document index...")
    ingest_grading(GRADING_PATH, handbook_client, embedding_function)
    grading_collection = handbook_client.get_collection(name="grading")

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
        budget = MAX_SUBJECT_CONTEXT_CHARS // len(subjects)
        context = "\n\n========\n\n".join(subject_context(subject_key, budget) for subject_key in subjects)

    else:
        # The standalone version finds better matches for follow-ups like "what about its fees?"
        search_query = decision.search_query.strip() or user_question
        print(f"Performing vector search on the grading document and handbook for: {search_query}")

        query_vector = embedding_function([search_query])[0]

        grading_results = grading_collection.query(
            query_embeddings=[query_vector], n_results=GRADING_RESULTS, include=["documents"]
        )
        handbook_results = handbook_collection.query(
            query_embeddings=[query_vector], n_results=HANDBOOK_RESULTS, include=["documents"]
        )
        context = (
            f"SOURCE: {GRADING_TERM} grading document (current term)\n\n"
            + key_dates_text + "\n\n----\n\n"
            + "\n\n----\n\n".join(grading_results["documents"][0])
            + "\n\n========\n\nSOURCE: Student handbook (general program rules, may be from an older term)\n\n"
            + "\n\n----\n\n".join(handbook_results["documents"][0])
        )

    return context


def subject_context(subject_key: str, budget: int) -> str:
    """
    A subject's course document plus its section of the current grading document,
    trimmed to fit the budget. The grading section comes first since it's the newest.
    """
    if subject_key in PROJECT_SUBJECTS:
        grading = project_grading_section
    else:
        grading = grading_by_code.get(SUBJECT_COURSE_CODES.get(subject_key))

    parts = []
    if grading:
        parts.append(f"SOURCE: {GRADING_TERM} grading document (current term) — {grading['title']}\n\n{grading['text']}")
    parts.append(f"SOURCE: Course document — {subject_key}\n\n{subjects_db[subject_key]}")

    return "\n\n----\n\n".join(parts)[:budget]



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
