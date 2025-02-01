import React, {useState} from "react";
import {v4 as uuidv4} from "uuid";
import ChatContainer from "../components/ChatContainer";
import "../styles/ChatGPTStyle.css";

function Home() {
    // 使用单一对话对象，初始为空对话
    const [conversation, setConversation] = useState({
        id: uuidv4(),
        title: "Chat",
        messages: [],
    });

    // 刷新按钮处理函数，清空当前对话并清除本地存储记录
    const handleRefresh = () => {
        setConversation({
            id: uuidv4(),
            title: "Chat",
            messages: [],
        });
        localStorage.removeItem("myConversations");
    };

    return (
        <div className="home-container">
            <div
                className="chat-wrapper"
                style={{
                    position: "relative",
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                {/* 刷新按钮：位于左上角 */}
                <button className="refresh-button" title="Refresh" onClick={handleRefresh}>
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        fill="none"
                        stroke="#333"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="feather feather-refresh-cw"
                    >
                        <polyline points="23 4 23 10 17 10"></polyline>
                        <polyline points="1 20 1 14 7 14"></polyline>
                        <path d="M3.51 9a9 9 0 0114.36-3.36L23 10"></path>
                        <path d="M20.49 15a9 9 0 01-14.36 3.36L1 14"></path>
                    </svg>
                </button>
                <ChatContainer
                    conversation={conversation}
                    onUpdateMessages={(newMsgs) =>
                        setConversation({...conversation, messages: newMsgs})
                    }
                />
            </div>
        </div>
    );
}

export default Home;
