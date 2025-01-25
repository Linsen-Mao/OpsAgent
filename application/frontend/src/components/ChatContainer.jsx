// ChatContainer.jsx
import { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from 'uuid';
import ChatMessage from "./ChatMessage";
import { fetchChatStream } from "../api/chatbotApi";

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const messageEndRef = useRef(null);

  // 流式处理相关ref
  const streamQueue = useRef([]);
  const isTyping = useRef(false);
  const currentTyping = useRef(null);
  const streamBuffer = useRef("");
  const activeStreamId = useRef(null);
  const TYPING_SPEED = 20; // 20ms/字符

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      // 清理定时器
      if (currentTyping.current) {
        clearTimeout(currentTyping.current);
      }
    };
  }, []);

  const processStreamQueue = async () => {
    if (isTyping.current || streamQueue.current.length === 0) return;

    isTyping.current = true;
    const { content } = streamQueue.current[0];
    let index = 0;

    const typeNextChar = () => {
      if (index < content.length) {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === activeStreamId.current
              ? { ...msg, content: content.slice(0, index + 1) + '▌' }
              : msg
          )
        );
        index++;
        currentTyping.current = setTimeout(typeNextChar, TYPING_SPEED);
      } else {
        // 完成当前内容输入
        setMessages(prev =>
          prev.map(msg =>
            msg.id === activeStreamId.current
              ? { ...msg, content: content }
              : msg
          )
        );
        streamQueue.current.shift();
        isTyping.current = false;
        processStreamQueue();
      }
    };

    typeNextChar();
  };

  const handleSend = async () => {
    if (!userInput.trim() || loading) return;

    setLoading(true);
    const userMsg = {
      sender: "user",
      content: userInput,
      id: uuidv4(),
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setUserInput("");

    try {
      const tempMessageId = uuidv4();
      streamBuffer.current = "";
      activeStreamId.current = tempMessageId;
      streamQueue.current = [];

      // 初始化流式消息
      setMessages(prev => [
        ...prev,
        {
          sender: "bot",
          content: "",
          id: tempMessageId,
          status: "streaming",
          timestamp: Date.now()
        }
      ]);

      const currentConversation = [...conversation, { sender: "user", content: userInput }];
      const reader = await fetchChatStream(userInput, currentConversation);

      let buffer = '';
      const processChunk = async () => {
        const { done, value } = await reader.read();
        if (done) return;

        buffer += new TextDecoder("utf-8").decode(value);
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          const data = event.split('\n').find(line => line.startsWith('data: '));
          if (!data) continue;

          try {
            const parsed = JSON.parse(data.slice(6));
            if (parsed.type === "stream") {
              streamBuffer.current += parsed.data;
              streamQueue.current.push({
                content: streamBuffer.current
              });
              processStreamQueue();
            }

            if (parsed.type === "final") {
              // 等待所有输入完成
              while (isTyping.current) {
                await new Promise(resolve => setTimeout(resolve, 50));
              }

              // 确保使用最终内容
              const finalContent = streamBuffer.current;
              replaceWithFinalMessage(tempMessageId, finalContent);
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
      setMessages(prev =>
        prev.map(msg =>
          msg.id === activeStreamId.current
            ? { ...msg, content: "Error: Failed to get response", status: "error" }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const replaceWithFinalMessage = (tempId, finalContent) => {
    setMessages(prev => [
      ...prev.filter(msg => msg.id !== tempId),
      {
        sender: "bot",
        content: finalContent,
        id: uuidv4(),
        status: "final",
        timestamp: Date.now()
      }
    ]);
    setConversation(prev => [...prev, { sender: "bot", content: finalContent }]);
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