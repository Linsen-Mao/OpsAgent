// src/components/Sidebar.jsx
import React, { useState } from "react";
import "../styles/ChatGPTStyle.css";

const Sidebar = ({
  conversations,
  activeConvId,
  onNewChat,
  onSelectChat,
  onUpdateTitle
}) => {
  return (
    <div className="sidebar">
      <button className="new-chat-button" onClick={onNewChat}>
        + New Chat
      </button>

      <div style={{ marginTop: "1rem" }}>
        {conversations.map((conv) => (
          <SidebarItem
            key={conv.id}
            conversation={conv}
            active={conv.id === activeConvId}
            onSelectChat={onSelectChat}
            onUpdateTitle={onUpdateTitle}
          />
        ))}
      </div>

        
      <div className="sidebar-footer">
        <p>CITHN2014</p>
        <p>Group 8</p>
      </div>
      
    </div>
  );
};

// 單獨分出一個子元件，顯示並允許編輯標題
const SidebarItem = ({ conversation, active, onSelectChat, onUpdateTitle }) => {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(conversation.title);

  const handleTitleClick = () => {
    onSelectChat(conversation.id);
  };

  const handleDoubleClick = () => {
    setEditing(true);
  };

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
  };

  const handleBlur = () => {
    setEditing(false);
    // 通知 parent 更新
    onUpdateTitle(conversation.id, title);
  };

  return (
    <div
      className={`chat-list-item ${active ? "active" : ""}`}
      style={{ padding: "8px", cursor: "pointer" }}
      onClick={handleTitleClick}
      onDoubleClick={handleDoubleClick}
    >
      {editing ? (
        <input
          style={{ width: "100%" }}
          value={title}
          onChange={handleTitleChange}
          onBlur={handleBlur}
          autoFocus
        />
      ) : (
        <span>{conversation.title}</span>
      )}
    </div>
  );
};

export default Sidebar;
