import uvicorn
import json
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, ChatMessage

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
    return {"message": "backend is running (ᗒᗨᗕ)/ (ᗒᗨᗕ)/ (ᗒᗨᗕ)/"}

@app.post("/chat_stream")
async def chat_stream_api(payload: dict):
    """Handle chat stream API."""
    # question = payload["question"]
    conversation_data = payload["conversation"]

    messages = []
    for item in conversation_data:
        if item["sender"] == "user":
            messages.append(ChatMessage(content=item["content"], role=item["sender"]))
        elif item["sender"] == "assistant":
            messages.append(AIMessage(content=item["content"]))

    # messages.append(ChatMessage(content=question, role="user"))

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
                            # 每次获取到新内容时立即发送事件
                            current_content = conversation_messages[-1].content
                            answer = current_content  # 更新最终答案

                            # 修正：使用json.dumps确保格式正确
                            data = json.dumps({
                                "type": "stream",
                                "data": current_content
                            })
                            yield f"data: {data}\n\n"  # 标准SSE格式

        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"

    async def final_response_generator(messages=None):
        """Generate final response."""
        async for chunk in event_generator(messages):
            yield chunk

        # 最终响应也使用json.dumps
        final_data = json.dumps({
            "type": "final",
            "data": answer
        })
        yield f"data: {final_data}\n\n"

    return StreamingResponse(
        final_response_generator(messages),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run(
        "application.backend.api.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
