//single message component
// src/components/ChatMessage.jsx
import React from "react";
import "../styles/ChatGPTStyle.css"; 

const ChatMessage = ({ sender, content }) => {
  return (
    <div className={`chat-message ${sender === "bot" ? "bot" : "user"}`}>
      <div className="chat-bubble">
        {sender === "bot" ? (
          <div className="avatar bot-avatar">gi🦉</div>
        ) : (
          <div className="avatar user-avatar">🦥</div>
        )}
        <div className="message-content">{content}</div>
      </div>
    </div>
  );
};

export default ChatMessage;
