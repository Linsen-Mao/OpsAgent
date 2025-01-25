import { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatMessage from "./ChatMessage";
import { fetchChatStream } from "../api/chatbotApi";

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const messageEndRef = useRef(null);

  const typingTimeoutRef = useRef(null);

  const TYPING_SPEED = 5;

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    // 组件卸载时清理定时器
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  /**
   * 发送消息
   */
  const handleSend = async () => {
    if (!userInput.trim() || loading) return;
    setLoading(true);

    const userMsg = {
      sender: "user",
      content: userInput,
      id: uuidv4(),
      timestamp: Date.now()
    };
    setMessages((prev) => [...prev, userMsg]);

    const thinkingId = uuidv4();
    setMessages((prev) => [
      ...prev,
      {
        sender: "bot",
        content: "Thinking ",
        id: thinkingId,
        status: "thinking",
        timestamp: Date.now()
      }
    ]);

    try {
      const currentConversation = [...conversation, { sender: "user", content: userInput }];
      setUserInput("");

      const reader = await fetchChatStream(userInput, currentConversation);
      let buffer = "";
      const processChunk = async () => {
        const { done, value } = await reader.read();
        if (done) return;

        buffer += new TextDecoder("utf-8").decode(value);
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const dataLine = event.split("\n").find((line) => line.startsWith("data: "));
          if (!dataLine) continue;

          try {
            const parsed = JSON.parse(dataLine.slice(6));

            if (parsed.type === "stream") {
              // 忽略中间 stream，不做任何处理
            }

            if (parsed.type === "final") {
              // 收到最终结果 -> 逐字打印
              const finalContent = parsed.data;

              // 移除「Thinking...」占位
              setMessages((prev) => prev.filter((m) => m.id !== thinkingId));

              // 新建一个空消息来逐字打印
              const finalMsgId = uuidv4();
              setMessages((prev) => [
                ...prev,
                {
                  sender: "bot",
                  content: "",
                  id: finalMsgId,
                  status: "typing", // 用于打字机动画
                  timestamp: Date.now()
                }
              ]);

              // 启动打字机
              typeOutFinalAnswer(finalContent, finalMsgId);

              // 更新会话
              setConversation((prev) => [...prev, { sender: "bot", content: finalContent }]);
            }
          } catch (err) {
            console.error("Parse error:", err);
          }
        }
        processChunk();
      };
      processChunk();
    } catch (error) {
      console.error("SSE Error:", error);
      setMessages((prev) => prev.filter((m) => m.id !== thinkingId));

      const errId = uuidv4();
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          content: "Error: Failed to get response",
          id: errId,
          status: "error",
          timestamp: Date.now()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const typeOutFinalAnswer = (fullText, messageId) => {
    let index = 0;

    const typeChar = () => {
      if (index < fullText.length) {
        const currentText = fullText.slice(0, index + 1);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId ? { ...m, content: currentText } : m
          )
        );
        index++;
        typingTimeoutRef.current = setTimeout(typeChar, TYPING_SPEED);
      } else {
        // 打字完毕，状态改为 final
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId ? { ...m, status: "final" } : m
          )
        );
      }
    };

    typeChar();
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
        {messages.map((m) => (
          <ChatMessage
            key={m.id}
            sender={m.sender}
            content={m.content}
            status={m.status}
            timestamp={m.timestamp}
          />
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
