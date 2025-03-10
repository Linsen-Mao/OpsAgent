import os

import numpy as np
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")


class ChatbotVectorDatabase:
    PDF_PATH = "User_manual.pdf"

    def __init__(self):
        # Initialize the Cosmos DB client
        self.cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        self.database = self.cosmos_client.get_database_client(COSMOS_DATABASE_NAME)
        self.container = self.database.get_container_client(COSMOS_CONTAINER_NAME)
        # Initialize OpenAI client
        self.openai_client = OpenAI(
            api_key=openai_api_key)

    @staticmethod
    def cosine_similarity(vec1, vec2):
        """Compute cosine similarity between two vectors."""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def get_embedding(self, text, model="text-embedding-3-large"):
        """
        Generate an embedding for the given text.
        Args:
            text (str): Input text for which to generate the embedding.
            model (str): OpenAI model to use.
        Returns:
            list: The embedding vector.
        """
        text = text.replace("\n", " ")
        return self.openai_client.embeddings.create(input=[text], model=model).data[0].embedding

    def search(self, query, model="text-embedding-3-large", top_k=3):
        """
        Search Cosmos DB based on a user's query using semantic similarity.

        Args:
            query (str): User's search query.
            model (str): OpenAI model to generate query embedding.
            top_k (int): Number of top results to return.

        Returns:
            list: Top matching documents from Cosmos DB.
        """
        # Get embedding for the user's query
        query_embedding = self.get_embedding(query, model=model)

        # Fetch all documents from Cosmos DB
        documents = list(self.container.read_all_items())

        # Compute similarities
        results = []
        for doc in documents:
            doc_embedding = np.array(doc["text_embedding"])
            similarity = self.cosine_similarity(query_embedding, doc_embedding)
            results.append({"document": doc, "similarity": similarity})

        # Sort results by similarity and return top_k
        results = sorted(results, key=lambda x: x["similarity"], reverse=True)
        return [result["document"] for result in results[:top_k]]


def chatbot_test():
    """
    A simple chatbot to query Cosmos DB based on user input.
    """
    print("Welcome to the Knowledge Chatbot! Ask your question (type 'exit' to quit).")
    db = ChatbotVectorDatabase()

    while True:
        # Get user query
        query = input("\nYour Query: ")

        if query.lower() == "exit":
            print("Goodbye!")
            break

        # Search the database
        print("\nSearching for the best matches...\n")
        try:
            results = db.search(query, top_k=3)
            if not results:
                print("No relevant documents found.")
            else:
                print("Here are the top results:")
                for idx, doc in enumerate(results, 1):
                    print(f"\nResult {idx}:\n")
                    print(f"Page: {doc['page_number']}")
                    print(f"Text: {doc['text'][:500]}")  # Truncate text for readability
                    print("-" * 50)
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    chatbot_test()
