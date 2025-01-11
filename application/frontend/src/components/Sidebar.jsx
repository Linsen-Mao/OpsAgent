// 就 sidebar XD
// 抄襲 ChatGPT 的 UI
// src/components/Sidebar.jsx
import React from "react";
import "../styles/ChatGPTStyle.css";

const Sidebar = () => {
  return (
    <div className="sidebar">
      <button className="new-chat-button">+ New Chat</button>
      <div className="sidebar-footer">
        <p>Some Setting</p>
        <p>Logout</p>
      </div>
    </div>
  );
};

export default Sidebar;
