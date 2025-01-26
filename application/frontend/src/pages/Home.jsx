// src/pages/Home.jsx
import React, { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import Sidebar from "../components/Sidebar";
import ChatContainer from "../components/ChatContainer";
import "../styles/ChatGPTStyle.css";

function Home() {
  // 多對話列表: { id, title, messages: [] }
  const [conversations, setConversations] = useState([]);
  // 目前選擇哪個對話 (active)
  const [activeConvId, setActiveConvId] = useState(null);

  // -- A) 一開始載入 localStorage --
  useEffect(() => {
    const storedData = localStorage.getItem("myConversations");
    if (storedData) {
      const parsed = JSON.parse(storedData);
      setConversations(parsed);
      // 可以看需不需要還原 activeConvId
      if (parsed.length > 0) {
        setActiveConvId(parsed[0].id);
      }
    }
  }, []);

  // -- B) 每次 conversations 改變，就存回 localStorage --
  useEffect(() => {
    localStorage.setItem("myConversations", JSON.stringify(conversations));
  }, [conversations]);

  // 新增一個新的對話
  const handleNewChat = () => {
    const newId = uuidv4();
    const newConv = {
      id: newId,
      title: "Untitled Chat",
      messages: []
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConvId(newId);
  };

  // 選擇某個對話 (切換)
  const handleSelectChat = (convId) => {
    setActiveConvId(convId);
  };

  // 更新某個對話的 messages
  const handleUpdateMessages = (convId, newMessages) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === convId
          ? { ...conv, messages: newMessages }
          : conv
      )
    );
  };

  // 更新對話的 title
  const handleUpdateTitle = (convId, newTitle) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === convId
          ? { ...conv, title: newTitle }
          : conv
      )
    );
  };

  // 取得當前對話
  const activeConv = conversations.find((c) => c.id === activeConvId);

  return (
    <div className="home-container">
      <Sidebar
        conversations={conversations}
        activeConvId={activeConvId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onUpdateTitle={handleUpdateTitle}
      />

      {activeConv ? (
        <ChatContainer
          conversation={activeConv}
          onUpdateMessages={(newMsgs) =>
            handleUpdateMessages(activeConv.id, newMsgs)
          }
        />
      ) : (
        <div style={{ flex: 1, color: "#ccc", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p>Please select or create a chat.</p>
        </div>
      )}
    </div>
  );
}

export default Home;
