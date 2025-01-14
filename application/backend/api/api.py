# application/backend/api/api.py
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.chatbot_ReAct_test import graph
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from application.backend.chatbot.conversation import Conversation
from langgraph.graph import StateGraph

# Define the FastAPI application
app = FastAPI()

@app.post("/chat_stream")
async def chat_stream_api(payload: dict):
    """
    Receive question and conversation (list) from the frontend,
    call the graph to process the input, and return a streamed response using SSE.
    """
    question = payload["question"]
    conversation_data = payload["conversation"]  # [{sender, content}, ...]

    # Convert input into a format compatible with the graph
    messages = [{"sender": item["sender"], "content": item["content"]} for item in conversation_data]
    messages.append({"sender": "user", "content": question})  # Add the user's current question to the messages

    # Async generator: yield a chunk of response each time
    async def event_generator():
        try:
            # Stream updates from the graph
            for chunk in graph.stream({"messages": messages}):
                yield f'{{"type": "stream", "data": {chunk}}}\n\n'
        except Exception as e:
            yield f"Error: {str(e)}\n\n"  # Handle exceptions gracefully

    # Return as text/event-stream, so the frontend can use SSE or fetch reader to read
    return StreamingResponse(event_generator(), media_type="text/event-stream")
