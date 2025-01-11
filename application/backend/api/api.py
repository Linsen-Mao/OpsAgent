# application/backend/api/api.py
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.conversation import Conversation
import json


load_dotenv(find_dotenv())

app = FastAPI()

# add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = Chatbot()

@app.get("/")
def read_root():
    return {"message": "backend is running (ᗒᗨᗕ)/ (ᗒᗨᗕ)/ (ᗒᗨᗕ)/"}

@app.post("/chat_stream")
async def chat_stream_api(payload: dict):
    """
    receive question and conversation (list) from frontend
    call Chatbot/chat_stream, SSE return response
    """
    question = payload["question"]
    conversation_data = payload["conversation"]  # [{sender, content}, ...]

    # convert to Conversation object
    conversation_obj = Conversation(conversation=conversation_data)

    # async generator：yield a chunk of response each time
    async def event_generator():
        async for chunk in bot.chat_stream(question, conversation_obj):
            # chunk "\n\n" 
            yield chunk

    # Return as text/event-stream, so frontend can use SSE or fetch reader to read
    return StreamingResponse(event_generator(), media_type="text/event-stream")
