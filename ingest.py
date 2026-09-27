import os
import json
import chromadb
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


HANDBOOK_DB_PATH = "./handbook_db"


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
    Also called by chatbot.py on first start when the database doesn't exist yet.
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

    #Embed the chunks and store them in Chromadb
    collection = client.get_or_create_collection(name=collection_name)
    ids = [f"handbook_{i}" for i in range(len(chunks))]
    embedded_chunks = embedding_function(chunks)

    # upsert so running ingestion again replaces chunks instead of duplicating them
    collection.upsert(
        embeddings=embedded_chunks,
        documents=chunks,
        ids=ids
    )

    print(f"Handbook ingestion complete. Total chunks in collection: {collection.count()}")



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
    ingest_subjects(data_folder)



if __name__ == "__main__":
    main()