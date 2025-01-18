# application/backend/api/api.py
import uvicorn
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage

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

    messages = []
    for item in conversation_data:
        role = "user" if item["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": item["content"]})
    messages.append({"role": "user", "content": question})  # Add the user's current question to the messages

    answer = ""

    # Async generator: yield a chunk of response each time
    async def event_generator(messages=None):
        nonlocal answer  # To allow updating the final answer variable
        try:
            # Stream updates from the graph
            for chunk in graph.stream({"messages": messages}):  # Remove {"messages": messages}
                # Dynamically find the key that contains 'messages'
                for key, value in chunk.items():
                    if isinstance(value, dict) and "messages" in value:
                        messages = value["messages"]
                        if messages and isinstance(messages[-1], AIMessage):  # Check if it's an AIMessage
                            # Get the last AIMessage and extract its content
                            answer = messages[-1].content
                            break  # Stop searching once the correct key is found

                # Stream each chunk as it comes
                # yield f'{{"type": "stream", "data": {chunk}}}\n\n'
        except Exception as e:
            yield f"Error: {str(e)}\n\n"  # Handle exceptions gracefully

    # After all chunks have been streamed, return the final response
    async def final_response_generator(messages=None):
        async for chunk in event_generator(messages):
            yield chunk
        # Once streaming is complete, yield the final formatted response
        yield f'{{"type": "final", "data": "{answer}"}}\n\n'

    # Return as text/event-stream, so the frontend can use SSE or fetch reader to read
    return StreamingResponse(final_response_generator(messages), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(
        "application.backend.api.api:app",  # Module and application instance
        host="0.0.0.0",  # Bind to all network interfaces
        port=8000,  # Default port for the backend
        reload=True  # Enable auto-reload for development
    )
