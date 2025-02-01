import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import {CpuChipIcon, UserCircleIcon} from "@heroicons/react/24/solid";

const ChatMessage = ({sender, content, status, timestamp}) => {
    if (status === "thinking") {
        return (
            <div className={`chat-message ${sender} thinking`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style text-blue-400"/>
                        ) : (
                            <CpuChipIcon className="icon-style text-purple-400"/>
                        )}
                    </div>
                    <div className="message-container">
                        <div className="thinking-text">
                            {content}
                            <span className="dot-flashing"></span>
                        </div>
                        <div className="message-timestamp">
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit"
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // error 状态
    if (status === "error") {
        return (
            <div className={`chat-message ${sender} error`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style text-blue-400"/>
                        ) : (
                            <CpuChipIcon className="icon-style text-purple-400"/>
                        )}
                    </div>
                    <div className="message-container">
                        <div className="error-message">⚠️ {content}</div>
                        <div className="message-timestamp">
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit"
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (status === "typing") {
        return (
            <div className={`chat-message ${sender} typing`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style text-blue-400"/>
                        ) : (
                            <CpuChipIcon className="icon-style text-purple-400"/>
                        )}
                    </div>
                    <div className="message-container">
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight]}
                        >
                            {content}
                        </ReactMarkdown>
                        <span className="typing-cursor">▌</span>
                        <div className="message-timestamp">
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit"
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={`chat-message ${sender} ${status}`}>
            <div className="chat-bubble">
                <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                    {sender === "user" ? (
                        <UserCircleIcon className="icon-style text-blue-400"/>
                    ) : (
                        <CpuChipIcon className="icon-style text-purple-400"/>
                    )}
                </div>
                <div className="message-container">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeHighlight]}
                    >
                        {content}
                    </ReactMarkdown>
                    <div className="message-timestamp">
                        {new Date(timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit"
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatMessage;
