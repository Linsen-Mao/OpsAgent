// src/components/ChatContainer.jsx
import React, { useState, useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import { fetchChatStream } from "../api/chatbotApi";

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);

  // conversation：要傳給後端的上下文
  const [conversation, setConversation] = useState([]);

  const messageEndRef = useRef(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!userInput.trim()) return;

    setLoading(true);

    // 1) 先把使用者輸入顯示到畫面
    const userMsg = { sender: "user", content: userInput };
    setMessages((prev) => [...prev, userMsg]);
    setConversation((prevConv) => [...prevConv, userMsg]);
    setUserInput("");

    try {
      // 2) 呼叫後端 SSE，準備讀取串流
      const reader = await fetchChatStream(
        userInput,
        [...conversation, userMsg]
      );

      // 3) 在畫面上先放一個空白 bot 訊息等待
      let botMsg = { sender: "assistant", content: "" };
      setMessages((prev) => [...prev, botMsg]);

      let finalAnswer = ""; // 只會有一次 final

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        // 讀 chunk
        const chunkValue = new TextDecoder("utf-8").decode(value);
        // ★ 目前後端把 SSE 事件格式化為 "data: { ... }\n\n"
        //   所以我們以 "\n" 為分隔，再檢查每一行是否以 "data: " 開頭
        const lines = chunkValue.split("\n").filter(Boolean);

        for (const line of lines) {
          if (line.startsWith("data:")) {
            // ★ 去掉 "data: " 前綴
            const jsonStr = line.replace(/^data:\s*/, "");
            // console.log("DEBUG SSE line =>", jsonStr);

            try {
              const parsed = JSON.parse(jsonStr);
              // console.log("DEBUG SSE parsed =>", parsed);

              // ★ 新版後端只會在最後 yield {"type": "final", "data": "..."}
              if (parsed.type === "final") {
                finalAnswer = parsed.data;
                updateLastBotMessage(finalAnswer);
              }
              else if (parsed.error) {
                // 如果發生例外
                updateLastBotMessage(`Error: ${parsed.error}`);
              }

            } catch (err) {
              console.error("Failed to parse SSE line:", line, err);
            }
          }
        }
      }

      // 在 SSE 流結束後，更新 conversation
      const finalBotMsg = {
        sender: "assistant",
        content: finalAnswer,
      };
      setConversation((prevConv) => [...prevConv, finalBotMsg]);

    } catch (error) {
      console.error("Error while fetching SSE:", error);
    } finally {
      setLoading(false);
    }
  };

  // 更新最後一則 bot 訊息的 content
  const updateLastBotMessage = (text) => {
    setMessages((prev) => {
      if (prev.length === 0) {
        return [{ sender: "assistant", content: text }];
      }
      const lastMsg = prev[prev.length - 1];
      if (lastMsg.sender === "assistant") {
        // 修改最後一筆
        return [...prev.slice(0, -1), { sender: "assistant", content: text }];
      } else {
        // 若最後一筆不是 assistant，就補上一筆
        return [...prev, { sender: "assistant", content: text }];
      }
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((m, idx) => (
          <ChatMessage key={idx} sender={m.sender} content={m.content} />
        ))}
        <div ref={messageEndRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          rows="1"
          placeholder="Send a message..."
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading}>
          {loading ? "Thinking..." : "Send"}
        </button>
      </div>
    </div>
  );
};

export default ChatContainer;
