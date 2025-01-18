import asyncio
import os
import json

from dotenv import load_dotenv

from application.backend.chatbot.conversation import Conversation
from application.backend.chatbot.prompts import ANSWER_PROMPT
from application.backend.datastore.db import ChatbotVectorDatabase
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import StrOutputParser

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

class Chatbot:
    """Initialize the chatbot."""
    def __init__(self):
        self.chatvec = ChatbotVectorDatabase()
        self.conversation_history = Conversation(conversation=[])
        pass

    """Generate responses using OpenAI and maintain conversation history."""
    def chat_stream(
            self, question: str, conversation: Conversation):
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=openai_api_key,
            streaming= False
        )

        history = conversation.get_history()

        docs_from_vdb = self.chatvec.search(
            query=question,
            top_k=3,
        )

        context = ""
        for i, res in enumerate(docs_from_vdb):
            replaced_text = res['text'].replace('\n', ' ')
            context += f"Document Index: {i + 1}, {replaced_text}\n"

        conversational_qa_chain = (
                {
                    "context": lambda x: context,
                    "question": RunnablePassthrough(),
                    "chat_history": lambda x: history,
                }
                | ANSWER_PROMPT
                | llm
                | StrOutputParser()
        )

        answer = ""

        for chunk in conversational_qa_chain.stream(
                {"question": question, "chat_history": history}
        ):
            answer += chunk

        return answer

async def main():
    """Main function to test chatbot locally in terminal."""
    bot = Chatbot()

    print("Chatbot initialized. Type 'quit' to exit.")

    while True:
        usr_input = input("User: ").strip()
        if usr_input.lower() == "quit":
            print("Exiting chatbot. Goodbye!")
            break

        print("Bot:", end=" ", flush=True)
        async for r in bot.chat_stream(usr_input, bot.conversation_history):
            try:
                response_dict = json.loads(r)
                if "data" in response_dict and "full_answer" in response_dict["data"]:
                    print(response_dict["data"]["full_answer"])
                    break
                elif "data" in response_dict and "stream" in response_dict["data"]:
                    print(response_dict["data"]["stream"], end="", flush=True)
            except json.JSONDecodeError:
                print("Error: Unable to parse response.")

if __name__ == "__main__":
    asyncio.run(main())
