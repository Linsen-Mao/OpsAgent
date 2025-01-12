import os
from PyPDF2 import PdfReader
from azure.cosmos import CosmosClient
from openai import OpenAI

# Configuration
PDF_PATH = "User_manual.pdf"
COSMOS_ENDPOINT = "https://chatbotgenai.documents.azure.com:443/"
COSMOS_KEY = ""
COSMOS_DATABASE_NAME = "Embeddings"
COSMOS_CONTAINER_NAME = "embeddings1"
OPENAI_API_KEY = ""

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Cosmos DB client
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DATABASE_NAME)
container = database.get_container_client(COSMOS_CONTAINER_NAME)

def get_embedding(text, model="text-embedding-3-large"):
    """Get embeddings for a given text using OpenAI's GPT models."""
    text = text.replace("\n", " ")
    response = client.embeddings.create(
        input=[text],
        model=model
    )
    return response.data[0].embedding

def chunk_text(text, max_tokens=8192):
    """Split text into chunks that fit within the model's token limit."""
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)
        if len(" ".join(current_chunk)) > max_tokens * 4:  # Approximate token count based on characters
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def get_embedding_for_text_chunks(text, model="text-embedding-3-large"):
    """Get embeddings for text by processing it in chunks."""
    chunks = chunk_text(text)
    embeddings = []

    for chunk in chunks:
        embedding = get_embedding(chunk, model=model)
        embeddings.append(embedding)
import os
from PyPDF2 import PdfReader
from azure.cosmos import CosmosClient
from openai import OpenAI

# Configuration
PDF_PATH = "User_manual.pdf"
COSMOS_ENDPOINT = "https://chatbotgenai.documents.azure.com:443/"
COSMOS_KEY = "Igqj9FsXb4nU2QVHXFXqAwfGFLwRYBODvaJR4rmBn1L8MwoPOOw7lJbyJWLPGl60JIoTFQEvnqLvACDbDgheXg=="
COSMOS_DATABASE_NAME = "Embeddings"
COSMOS_CONTAINER_NAME = "embeddings1"
OPENAI_API_KEY = "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"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Cosmos DB client
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DATABASE_NAME)
container = database.get_container_client(COSMOS_CONTAINER_NAME)


def get_embedding(text, model="text-embedding-3-large"):
    """Get embeddings for a given text using OpenAI's GPT models."""
    text = text.replace("\n", " ")
    response = client.embeddings.create(
        input=[text],
        model=model
    )
    return response.data[0].embedding


def chunk_text(text, max_tokens=8192):
    """Split text into chunks that fit within the model's token limit."""
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)
        if len(" ".join(current_chunk)) > max_tokens * 4:  # Approximate token count based on characters
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def get_embedding_for_text_chunks(text, model="text-embedding-3-large"):
    """Get embeddings for text by processing it in chunks."""
    chunks = chunk_text(text)
    embeddings = []

    for chunk in chunks:
        embedding = get_embedding(chunk, model=model)
        embeddings.append(embedding)

    combined_embedding = [sum(x) / len(x) for x in zip(*embeddings)]
    return combined_embedding


def calculate_embedding_cost(num_tokens, model="text-embedding-3-large"):
    """Calculate the cost of embeddings based on token count."""
    cost_per_1000_tokens = 0.0001  # Cost for text-embedding-3-large
    return (num_tokens / 1000) * cost_per_1000_tokens


def process_pdf(pdf_path):
    """Process a PDF, extracting text, and return embedded data."""
    reader = PdfReader(pdf_path)
    pages = reader.pages

    total_tokens = 0
    data = []

    for i, page in enumerate(pages):
        page_text = page.extract_text() or ""
        text_chunks = chunk_text(page_text)
        text_tokens = sum(len(chunk) for chunk in text_chunks)
        total_tokens += text_tokens

        chunk_embeddings = []
        for chunk in text_chunks:
            chunk_embedding = get_embedding(chunk)
            chunk_embeddings.append(chunk_embedding)

        data.append({
            "page_number": i + 1,
            "text": page_text,
            "text_embedding": chunk_embeddings
        })

    # Calculate cost
    total_cost = calculate_embedding_cost(total_tokens)
    print(f"The estimated cost for embedding is: ${total_cost:.4f}")

    return data


def store_in_cosmos(data):
    """Store processed data into Azure Cosmos DB."""
    for page in data:
        page_number = page["page_number"]
        text_chunks = page.get("text_embedding", [])

        for chunk_index, chunk_embedding in enumerate(text_chunks):
            # Create a unique 'id' for each chunk
            chunk_id = f"page-{page_number}-chunk-{chunk_index}"

            # Prepare the item with a unique id
            item = {
                "id": chunk_id,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "text_embedding": chunk_embedding,
                "text": page["text"]  # Optionally, include the text if needed
            }

            container.upsert_item(body=item)


def main():
    # Process the PDF
    print("Processing PDF...")
    embedded_data = process_pdf(PDF_PATH)

    if embedded_data:
        # Store data in Cosmos DB
        print("Storing data in Cosmos DB...")
        store_in_cosmos(embedded_data)
        print("Process completed successfully!")


if __name__ == "__main__":
    main()

def calculate_embedding_cost(num_tokens, model="text-embedding-3-large"):
    """Calculate the cost of embeddings based on token count."""
    cost_per_1000_tokens = 0.0001  # Cost for text-embedding-3-large
    return (num_tokens / 1000) * cost_per_1000_tokens

def process_pdf(pdf_path):
    """Process a PDF, extracting text, and return embedded data."""
    reader = PdfReader(pdf_path)
    pages = reader.pages

    total_tokens = 0
    data = []

    for i, page in enumerate(pages):
        page_text = page.extract_text() or ""
        text_chunks = chunk_text(page_text)
        text_tokens = sum(len(chunk) for chunk in text_chunks)
        total_tokens += text_tokens

        chunk_embeddings = []
        for chunk in text_chunks:
            chunk_embedding = get_embedding(chunk)
            chunk_embeddings.append(chunk_embedding)

        data.append({
            "page_number": i + 1,
            "text": page_text,
            "text_embedding": chunk_embeddings
        })

    # Calculate cost
    total_cost = calculate_embedding_cost(total_tokens)
    print(f"The estimated cost for embedding is: ${total_cost:.4f}")

    return data


def store_in_cosmos(data):
    """Store processed data into Azure Cosmos DB."""
    for page in data:
        page_number = page["page_number"]
        text_chunks = page.get("text_embedding", [])

        for chunk_index, chunk_embedding in enumerate(text_chunks):
            # Create a unique 'id' for each chunk
            chunk_id = f"page-{page_number}-chunk-{chunk_index}"

            # Prepare the item with a unique id
            item = {
                "id": chunk_id,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "text_embedding": chunk_embedding,
                "text": page["text"]  # Optionally, include the text if needed
            }

            container.upsert_item(body=item)


def main():
    # Process the PDF
    print("Processing PDF...")
    embedded_data = process_pdf(PDF_PATH)

    if embedded_data:
        # Store data in Cosmos DB
        print("Storing data in Cosmos DB...")
        store_in_cosmos(embedded_data)
        print("Process completed successfully!")

if __name__ == "__main__":
    main()