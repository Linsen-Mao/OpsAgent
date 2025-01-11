// src/components/ChatContainer.jsx
import React, { useState, useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import { fetchChatStream } from "../api/chatbotApi";

const ChatContainer = () => {
  const [messages, setMessages] = useState([]); 
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);

  // conversation：要傳給後端的上下文
  const [conversation, setConversation] = useState([]); // 改成列表

  const messageEndRef = useRef(null);

  useEffect(() => {
    // 自動捲到底
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 按下「送出」按鈕或按 Enter
  const handleSend = async () => {
    if (!userInput.trim()) return;

    setLoading(true);

    // 1) 先把使用者輸入顯示到畫面
    const userMsg = { sender: "user", content: userInput };
    setMessages((prev) => [...prev, userMsg]);
    setConversation((prevConv) => [...prevConv, userMsg]); // 直接操作列表
    setUserInput("");

    try {
      // 2) 呼叫後端 SSE，準備讀取串流
      const reader = await fetchChatStream(
        userInput, 
        [...conversation, userMsg] // 傳遞列表
      );

      // 3) 畫面上加一個空訊息，逐字更新
      let botMsg = { sender: "bot", content: "" };
      setMessages((prev) => [...prev, botMsg]);

      let partialAnswer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        // 讀 chunk
        const chunkValue = new TextDecoder("utf-8").decode(value);
        const lines = chunkValue.split("\n\n").filter(Boolean);

        for (const line of lines) {
          try {
            const parsed = JSON.parse(line);






            console.log("Parsed SSE message:", parsed); // 增加日誌
            // 確保 'type' 是 'stream' + 'data' 是 string
            if (parsed.type === "stream" && typeof parsed.data === "string") {
              partialAnswer += parsed.data;
              updateLastBotMessage(partialAnswer);
            }
          } catch (err) {
            // chunk 還不完整或 JSON parse 失敗就先忽略
            console.error("Failed to parse SSE line:", line, err);
          }
        }
      }

      // 在 stream 結束後，更新 conversation
      const finalBotMsg = {
        sender: "bot",
        content: partialAnswer,
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
        return [{ sender: "bot", content: text }];
      }
      const lastMsg = prev[prev.length - 1];
      if (lastMsg.sender === "bot") {
        // 修改最後一筆
        return [...prev.slice(0, -1), { sender: "bot", content: text }];
      } else {
        // 若最後一筆不是 bot，就補上一筆
        return [...prev, { sender: "bot", content: text }];
      }
    });
  };

  // 按下 Enter 鍵時送出
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { // 防止在多行輸入時按 Enter 捲動
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
