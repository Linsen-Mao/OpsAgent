
import asyncio
import os


from dotenv import load_dotenv
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
        # Always keep a valid Conversation instance
        # self.conversation_history = Conversation(conversation=[])

    def chat_stream(
        self,
        question: str,
        # conversation: Conversation
    ) -> str:
        """
        Generate a response using OpenAI and maintain conversation history.
        """
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=openai_api_key,
            streaming=False
        )

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
                # "chat_history": lambda x: history,
            }
            | ANSWER_PROMPT
            | llm
            | StrOutputParser()
        )

        answer = ""
        for chunk in conversational_qa_chain.stream(
            {"question": question}
        ):
            answer += chunk

        return answer


async def main():
    """Example usage to test chatbot locally in terminal."""
    bot = Chatbot()

    print("Chatbot initialized. Type 'quit' to exit.")

    while True:
        usr_input = input("User: ").strip()
        if usr_input.lower() == "quit":
            print("Exiting chatbot. Goodbye!")
            break

        # Add user's message to the conversation
        bot.conversation_history.add_message(sender="user", content=usr_input)

        # Get bot response
        response = bot.chat_stream(usr_input, bot.conversation_history)
        print("Bot:", response)

        # Store the bot's answer as well
        bot.conversation_history.add_message(sender="bot", content=response)


if __name__ == "__main__":
    asyncio.run(main())
