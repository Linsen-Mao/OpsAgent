// 主畫面
// 把 Sidebar + Container 合在一起
// 範例：在 Home.jsx 中引用 ChatContainer
// import ChatContainer from "../components/ChatContainer";
// src/pages/Home.jsx
import React from "react";
import Sidebar from "../components/Sidebar";
import ChatContainer from "../components/ChatContainer";
import "../styles/ChatGPTStyle.css";

const Home = () => {
  return (
    <div className="home-container">
      <Sidebar />
      <ChatContainer />
    </div>
  );
};

export default Home;
