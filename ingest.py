import os
import re
import json
import hashlib
import chromadb
from typing import Dict, List, Optional
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.errors import NotFoundError
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


HANDBOOK_DB_PATH = "./handbook_db"

# Grading document of the current term. To update for a new term, replace this file
# (and GRADING_TERM); the app rebuilds the grading index on its next start.
GRADING_PATH = os.path.join("Data", "grading", "sep2026_grading_document.txt")
GRADING_TERM = "Sep 2026"

# A course section starts with a heading like "3. Computational Thinking (CS1001)"
_COURSE_HEADING = re.compile(r"^\s*\d+\s*\.\s*(?P<title>.+?)\s*\(\s*(?P<code>[A-Z]{2}\d{4})\s*\)\s*$")
# Short summary of the term's exam dates, always sent with general questions
KEY_DATES_TITLE = "Key exam dates (Sep 2026 term)"
# General (non-course) parts of the grading document start with one of these lines
_GENERAL_HEADINGS = {
    KEY_DATES_TITLE, "OPPE SCHEDULE (Sep 2026 TERM)", "ASSIGNMENT DEADLINES:", "Bonus Marks",
    "Information about course grades:", "Diploma Level courses", "Project Courses:",
    "Degree Level courses", "Annexure I",
}


def load_embedding_function() -> DefaultEmbeddingFunction:
    """
    all-MiniLM-L6-v2 run through ONNX (bundled with chromadb). Gives the same vectors as the
    sentence-transformers version, without needing PyTorch, so installs stay small.
    """
    return DefaultEmbeddingFunction()


#  ----- INGESTION FUNCTION ------
def ingest_handbook(handbook_path: str, client, embedding_function, collection_name: str = "handbook"):
    """
    Loads, chunks, embed and stores the handbook in a chromadb vector store.
    Also called by chatbot.py on first start, and whenever the handbook file has changed.
    """
    
    #Load document
    try:
        loader = TextLoader(handbook_path, encoding="utf-8")
        handbook_doc = loader.load()
        handbook_text = handbook_doc[0].page_content
        print(f"Successfully loaded: {os.path.basename(handbook_path)}")
    except Exception as e:
        print(f"Error loading handbook: {e}")
        return
    
    #Chunk the documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300
    )
    chunks = text_splitter.split_text(handbook_text)
    print(f"Split Handbook into {len(chunks)} chunks.")

    #Embed the chunks and store them in Chromadb.
    # The collection is rebuilt from scratch so chunks from an older handbook never linger,
    # and it stores the file's hash so chatbot.py can tell when the handbook was replaced.
    try:
        client.delete_collection(collection_name)
    except (NotFoundError, ValueError):
        pass
    collection = client.create_collection(name=collection_name, metadata={"source_hash": file_hash(handbook_path)})
    ids = [f"handbook_{i}" for i in range(len(chunks))]
    embedded_chunks = embedding_function(chunks)

    collection.add(
        embeddings=embedded_chunks,
        documents=chunks,
        ids=ids
    )

    print(f"Handbook ingestion complete. Total chunks in collection: {collection.count()}")



def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def split_grading_sections(text: str) -> List[Dict[str, Optional[str]]]:
    """
    Splits the grading document into sections: one per course (with its course code)
    plus the general parts (exam schedule, deadlines, grades, projects, degree rules...).
    Returns [{"title": ..., "code": "CS1001" or None, "text": ...}].
    """
    sections = []
    current = {"title": "Exam schedule, OPPE eligibility and term rules", "code": None, "heading": "", "body": []}

    for line in text.splitlines():
        course = _COURSE_HEADING.match(line)
        if course or line.strip() in _GENERAL_HEADINGS:
            sections.append(current)
            current = {
                "title": course.group("title") if course else line.strip().rstrip(":"),
                "code": course.group("code") if course else None,
                "heading": line,
                "body": [],
            }
        else:
            current["body"].append(line)
    sections.append(current)

    return [
        {
            "title": s["title"],
            "code": s["code"],
            "text": re.sub(r"\n{3,}", "\n\n", "\n".join([s["heading"]] + s["body"])).strip(),
        }
        for s in sections
        if "".join(s["body"]).strip()  # skip headings that only appear in the table of contents
    ]


def ingest_grading(grading_path: str, client, embedding_function, collection_name: str = "grading"):
    """
    Chunks the current term's grading document section by section and stores it in its own
    collection. Each chunk starts with its section title so the course name survives chunking.
    The collection is rebuilt from scratch, so chunks from an older document never linger.
    """
    with open(grading_path, encoding="utf-8") as f:
        sections = split_grading_sections(f.read())

    try:
        client.delete_collection(collection_name)
    except (NotFoundError, ValueError):
        pass
    collection = client.create_collection(name=collection_name, metadata={"source_hash": file_hash(grading_path)})

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    documents, ids, metadatas = [], [], []
    for s_idx, section in enumerate(sections):
        label = f"[{GRADING_TERM} grading document — {section['title']}" + (f" ({section['code']})]" if section["code"] else "]")
        for c_idx, chunk in enumerate(text_splitter.split_text(section["text"])):
            documents.append(f"{label}\n{chunk}")
            ids.append(f"grading_{s_idx}_{c_idx}")
            metadatas.append({"section": section["title"], "code": section["code"] or ""})

    collection.add(embeddings=embedding_function(documents), documents=documents, ids=ids, metadatas=metadatas)
    print(f"Grading document ingestion complete: {len(sections)} sections, {collection.count()} chunks.")



def ingest_subjects(subject_folder: str, output_json_path: str = "subjects_db.json"):
    """
    Loads all subjects .txt file whole and saves them into a dictionary in a JSON file
    """
    print("\n--- Starting Subject Ingestion ---")
    subjects_dict = {}

    #Loop through all files in the folder
    for file in os.listdir(subject_folder):
        if file.endswith(".txt") and file.lower() != "handbook.txt":
            file_path = os.path.join(subject_folder, file)
            try:
                with open(file_path, 'r', encoding="utf-8") as f:
                    content = f.read()
                
                subject_key = os.path.splitext(file)[0]
                subjects_dict[subject_key] = content
                print(f"  - Successfully loaded {file} with key '{subject_key}' ")
            except Exception as e:
                print(f"   - Error loading {file}: {e}")

    #Save the complete dictionary to a JSON file
    with open(output_json_path, 'w', encoding="utf-8") as f:
        json.dump(subjects_dict, f, indent=4)

    print(f"\nSubject ingestion complete. Saved {len(subjects_dict)} subjects to {output_json_path}")



# ----- MAIN EXECUTION BLOCK -----
def main():
    """
    Main function to run the entire ingestion process for both knowledge bases.
    """
    data_folder = "Data"

    client = chromadb.PersistentClient(path=HANDBOOK_DB_PATH)
    embedding_function = load_embedding_function()

    ingest_handbook(os.path.join(data_folder, "handbook.txt"), client, embedding_function)
    ingest_grading(GRADING_PATH, client, embedding_function)
    ingest_subjects(data_folder)



if __name__ == "__main__":
    main()