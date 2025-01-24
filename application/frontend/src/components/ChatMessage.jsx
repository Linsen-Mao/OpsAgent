//single message component
// src/components/ChatMessage.jsx
import React from "react";
import "../styles/ChatGPTStyle.css"; 

const ChatMessage = ({ sender, content }) => {
  // 如果 sender 是 "assistant"，就當作機器人
  const isBot = sender === "assistant";

  return (
    <div className={`chat-message ${isBot ? "bot" : "user"}`}>
      <div className="chat-bubble">
        {isBot ? (
          <div className="avatar bot-avatar">🦉</div>
        ) : (
          <div className="avatar user-avatar">🦥</div>
        )}
        <div className="message-content">{content}</div>
      </div>
    </div>
  );
};

export default ChatMessage;
