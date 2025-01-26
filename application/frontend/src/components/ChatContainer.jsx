import React, { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatMessage from "./ChatMessage";
import { fetchChatStream } from "../api/chatbotApi";

const ChatContainer = ({ conversation, onUpdateMessages }) => {
  // 用 local state 來儲存對話中的所有訊息
  // 一開始先把 props.conversation.messages 複製進來
  const [localMessages, setLocalMessages] = useState(conversation.messages);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);

  const messageEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  const TYPING_SPEED = 5;
  

  // 如果父層切換了另一個 conversation，id 不同，就要重置 localMessages
  useEffect(() => {
    setLocalMessages(conversation.messages);
  }, [conversation.id]);

  // 監聽 localMessages 改變，自動捲動
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages]);

  // 離開時清理
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    };
  }, []);

  // 更新 localMessages
  const updateLocal = (newMsgs) => {
    setLocalMessages(newMsgs);
  };

  // 在 SSE 最終結束時，把 localMessages 同步到父層
  const syncToParent = (msgs) => {
    onUpdateMessages(msgs);
  };

  const handleSend = async () => {
    if (!userInput.trim() || loading) return;
    setLoading(true);

    // 1) 新增 userMsg 到 local
    const userMsg = {
      sender: "user",
      content: userInput,
      id: uuidv4(),
      timestamp: Date.now()
    };
    const updatedUser = [...localMessages, userMsg];
    updateLocal(updatedUser);

    // 2) thinking
    const thinkingId = uuidv4();
    const updatedThinking = [
      ...updatedUser,
      {
        sender: "bot",
        content: "Thinking...",
        id: thinkingId,
        status: "thinking",
        timestamp: Date.now()
      }
    ];
    updateLocal(updatedThinking);

    setUserInput("");

    try {
      // SSE 送出 current localMessages 來拼對話
      const reader = await fetchChatStream(userInput, updatedUser);

      let buffer = "";
      const processChunk = async () => {
        const { done, value } = await reader.read();
        if (done) {
          // SSE 完整結束 → 同步最終 messages 給父層
          //syncToParent(localMessages);
          onUpdateMessages(localMessages);
          return;
        }

        buffer += new TextDecoder("utf-8").decode(value);
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const dataLine = event.split("\n").find((line) => line.startsWith("data: "));
          if (!dataLine) continue;

          try {
            const parsed = JSON.parse(dataLine.slice(6));

            if (parsed.type === "final") {
              // 移除 thinking
              let removeThinking = updatedThinking.filter(
                (m) => m.id !== thinkingId
              );

              // 新增一個空 botMsg(typing)
              const finalMsgId = uuidv4();
              let newMsg = {
                sender: "bot",
                content: "",
                id: finalMsgId,
                status: "typing",
                timestamp: Date.now()
              };
              let updatedTyping = [...removeThinking, newMsg];
              updateLocal(updatedTyping);

              // 逐字顯示
              typeOutFinalAnswer(parsed.data, finalMsgId);

              // 立即同步給父層
              //syncToParent(localMessages);
              onUpdateMessages(localMessages);
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

      let removeThinking = localMessages.filter((m) => m.id !== thinkingId);
      updateLocal([
        ...removeThinking,
        {
          sender: "bot",
          content: "Error: Failed to get response",
          id: uuidv4(),
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
        // 更新 localMessages
        setLocalMessages((prev) =>
          prev.map((m) =>
            m.id === messageId ? { ...m, content: currentText } : m
          )
        );
        index++;
        typingTimeoutRef.current = setTimeout(typeChar, TYPING_SPEED);
      } else {
        // 打字完 → status: "final"
        setLocalMessages((prev) =>
          prev.map((m) =>
            m.id === messageId ? { ...m, status: "final" } : m
          )
        );
        // TBC: 要不要在這裡 syncToParent(localMessages)？不過 setState 是 async
        // 在 SSE 結束 (done === true) 再做一次 sync？
        // 目前存localsorage都失敗QQ
      }
    };
    typeChar();
  };

  const handleKeyDown = (e) => {
    if (e.nativeEvent.isComposing) {
      // 還在中文輸入法組字階段，就不處理
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {localMessages.map((m) => (
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
