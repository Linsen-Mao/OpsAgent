// src/components/ChatContainer.jsx
import  { useState, useEffect, useRef } from "react";
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

  // 修改 handleSend 中的流处理逻辑
const handleSend = async () => {
  if (!userInput.trim()) return;

  setLoading(true);

  // 1) 添加用户消息
  const userMsg = { sender: "user", content: userInput };
  setMessages((prev) => [...prev, userMsg]);
  setConversation((prevConv) => [...prevConv, userMsg]);
  setUserInput("");

  try {
    // 2) 初始化 bot 消息
    let botMsg = { sender: "assistant", content: "" };
    setMessages((prev) => [...prev, botMsg]);

    const reader = await fetchChatStream(userInput, [...conversation, userMsg]);
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith("data:")) {
          try {
            const jsonStr = trimmedLine.slice(5).trim();
            const parsed = JSON.parse(jsonStr);

            // 处理最终数据
            if (parsed.type === "final") {
              botMsg.content = parsed.data;
              updateLastBotMessage(parsed.data);
              setConversation((prev) => [...prev, botMsg]);
            }
            // 处理中间 chunk 数据（如果存在）
            else if (parsed.type === "chunk") {
              botMsg.content += parsed.data;
              updateLastBotMessage(botMsg.content);
            }
            // 处理错误
            else if (parsed.error) {
              updateLastBotMessage(`Error: ${parsed.error}`);
            }
          } catch (err) {
            console.error("解析失败:", err);
          }
        }
      }
    }
  } catch (error) {
    console.error("请求失败:", error);
    updateLastBotMessage(`Error: ${error.message}`);
  } finally {
    setLoading(false);
  }
};

  // 更新最後一則 bot 訊息的 content
  const updateLastBotMessage = (text) => {
  setMessages((prev) => {
    const newMessages = [...prev];
    const lastIndex = newMessages.length - 1;

    // 如果最后一条消息是 assistant，直接更新
    if (lastIndex >= 0 && newMessages[lastIndex].sender === "assistant") {
      newMessages[lastIndex] = { ...newMessages[lastIndex], content: text };
    } else {
      // 否则添加新消息
      newMessages.push({ sender: "assistant", content: text });
    }

    return newMessages;
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
