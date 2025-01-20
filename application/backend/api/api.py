import uvicorn
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage

from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.chatbot_supervisor import graph


load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = Chatbot()

@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "backend is running (ᗒᗨᗕ)/ (ᗒᗨᗕ)/ (ᗒᗨᗕ)/"}

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, ChatMessage

app = FastAPI()

@app.post("/chat_stream")
async def chat_stream_api(payload: dict):
    """Handle chat stream API."""
    question = payload["question"]
    conversation_data = payload["conversation"]

    messages = []
    for item in conversation_data:
        if item["sender"] == "user":
            messages.append(ChatMessage(content=item["content"], role=item["sender"]))
        elif item["sender"] == "assistant":
            messages.append(AIMessage(content=item["content"]))

    messages.append(ChatMessage(content=question, role="user"))

    answer = ""

    async def event_generator(messages=None):
        """Generate stream events."""
        nonlocal answer
        try:
            # Stream conversation through the graph
            for chunk in graph.stream({"messages": messages}):
                for key, value in chunk.items():
                    if isinstance(value, dict) and "messages" in value:
                        conversation_messages = value["messages"]
                        if conversation_messages and isinstance(conversation_messages[-1], AIMessage):
                            answer = conversation_messages[-1].content
                            break
        except Exception as e:
            yield f'data: {{ "error": "{str(e)}" }}\n\n'

    async def final_response_generator(messages=None):
        """Generate final response."""
        async for chunk in event_generator(messages):
            yield chunk
        yield f'data: {{"type": "final", "data": "{answer}"}}\n\n'

    return StreamingResponse(final_response_generator(messages), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(
        "application.backend.api.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
