from application.backend.chatbot.conversation import Conversation, format_chat_history
from langchain_openai import AzureChatOpenAI
import os
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import StrOutputParser
import json

from application.backend.chatbot.prompts import ANSWER_PROMPT
from application.backend.datastore.db import ChatbotVectorDatabase

openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")


class Chatbot:
    def __init__(self):
        """
        Initialize the chatbot
        :param session_id: mostly generated automatically, but can be set manually
        """
        self.chatvec = ChatbotVectorDatabase()
        pass

    async def chat_stream(
            self, question: str, conversation: Conversation):
        llm = AzureChatOpenAI(
            openai_api_version="2023-05-15",
            deployment_name="ChatbotMGT",
            azure_endpoint=azure_endpoint,
            openai_api_key=openai_api_key,
        )

        #TODO format the conversation history
        history = format_chat_history(conversation)

        #TODO get the document from the model
        docs_from_vdb = self.chatvec.search(
            query=question,
            k=3,
        )

        context = ""

        for i, res in enumerate(docs_from_vdb):
            replaced_text = res.text.replace('\n', ' ')
            context += f"Document Index: {i + 1}, {replaced_text}, {res.subtopic} \n"


        conversational_qa_chain = (
                {
                    "context": lambda x: context,
                    "question": RunnablePassthrough(),
                    "chat_history": RunnablePassthrough(),
                }
                | ANSWER_PROMPT
                | llm
                | StrOutputParser()
        )

        answer = ""

        async for chunk in conversational_qa_chain.astream(
                {"question": question, "chat_history": history}
        ):
            data_to_send = {"type": "stream", "data": chunk}
            yield f"{json.dumps(data_to_send)}\n\n"
            answer += chunk

        final_data = {
            "data": {
                "full_answer": answer,
            },
        }

        yield f"{json.dumps(final_data)}\n\n"
