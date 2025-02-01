import os

from dotenv import load_dotenv
from langchain.schema import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from application.backend.chatbot.prompts import ANSWER_PROMPT
from application.backend.datastore.db import ChatbotVectorDatabase

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

chatvec = ChatbotVectorDatabase()


def ecommerce_query(
        question: str,
) -> str:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        openai_api_key=openai_api_key,
        streaming=False
    )

    docs_from_vdb = chatvec.search(
        query=question,
        top_k=4,
    )

    context = ""
    for i, res in enumerate(docs_from_vdb):
        replaced_text = res['text'].replace('\n', ' ')
        context += f"Document Index: {i + 1}, {replaced_text}\n"

    conversational_qa_chain = (
            {
                "context": lambda x: context,
                "question": RunnablePassthrough(),
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
