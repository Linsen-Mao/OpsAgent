from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.conversation import Conversation

load_dotenv(find_dotenv())
app = FastAPI()
bot = Chatbot()

@app.post("/chat/")
async def chat_stream_endpoint(question: str, conversation: Conversation) -> EventSourceResponse:
    """
    Ask a question to the chatbot and return the answer as a stream
    :param question: the question of the user
    :param conversation: the context of the conversation
    :return: the answer of the chatbot as a stream
    """
    return EventSourceResponse(
        bot.chat_stream(
            question=question,
            conversation=conversation,
        ),
        media_type="text/event-stream",
    )
