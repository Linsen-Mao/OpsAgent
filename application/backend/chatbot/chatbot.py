import asyncio
import os
import json

from dotenv import load_dotenv

from application.backend.chatbot.conversation import Conversation, format_chat_history
from application.backend.chatbot.prompts import ANSWER_PROMPT
from application.backend.datastore.db import ChatbotVectorDatabase
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import StrOutputParser

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

class Chatbot:
    def __init__(self):
        """
        Initialize the chatbot
        """
        self.chatvec = ChatbotVectorDatabase()
        self.conversation_history = Conversation(conversation=[])
        pass

    async def chat_stream(
            self, question: str, conversation: Conversation):
        """
        Generate responses using OpenAI and maintain conversation history.
        """
        llm = ChatOpenAI(
            model="gpt-4o-mini",  # Use the appropriate OpenAI model
            temperature=0.7,  # Adjust as needed
            openai_api_key=openai_api_key,
            streaming=True
        )

        # Format the conversation history into a LangChain-compatible format
        history = conversation.get_history()

        # Search for related documents in the vector database
        docs_from_vdb = self.chatvec.search(
            query=question,
            k=3,
        )

        # Create context from retrieved documents
        context = ""
        for i, res in enumerate(docs_from_vdb):
            replaced_text = res.text.replace('\n', ' ')
            context += f"Document Index: {i + 1}, {replaced_text}, {res.subtopic} \n"

        # Create the conversational QA chain
        conversational_qa_chain = (
                {
                    "context": lambda x: context,
                    "question": RunnablePassthrough(),
                    "chat_history": lambda x: history,  # Pass the formatted history
                }
                | ANSWER_PROMPT
                | llm
                | StrOutputParser()
        )

        answer = ""

        # Stream the response from the QA chain
        async for chunk in conversational_qa_chain.astream(
                {"question": question, "chat_history": history}
        ):
            data_to_send = {"type": "stream", "data": chunk}
            yield f"{json.dumps(data_to_send)}\n\n"
            answer += chunk

        # Add the question and answer to the conversation history
        conversation.add_message("user", question)
        conversation.add_message("bot", answer)

        # Structure the final data
        final_data = {
            "type": "final",
            "data": {
                "full_answer": answer,
            },
        }

        yield f"{json.dumps(final_data)}\n\n"


async def main():
    """
    Main function to test chatbot locally in terminal.
    """
    bot = Chatbot()

    print("Chatbot initialized. Type 'quit' to exit.")

    while True:
        usr_input = input("User: ").strip()
        if usr_input.lower() == "quit":
            print("Exiting chatbot. Goodbye!")
            break

        # Stream responses from the bot
        print("Bot:", end=" ", flush=True)  # Print "Bot:" as a prefix for responses
        async for r in bot.chat_stream(usr_input, bot.conversation_history):
            try:
                response_dict = json.loads(r)
                if "data" in response_dict and "full_answer" in response_dict["data"]:
                    # Print the full answer once available
                    print(response_dict["data"]["full_answer"])
                    break  # No need to keep the stream open
                elif "data" in response_dict and "stream" in response_dict["data"]:
                    # Print the streaming response
                    print(response_dict["data"]["stream"], end="", flush=True)
            except json.JSONDecodeError:
                print("Error: Unable to parse response.")


if __name__ == "__main__":
    asyncio.run(main())
