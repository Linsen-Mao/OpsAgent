// src/components/ChatMessage.jsx
import React, {useState} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import {CpuChipIcon, UserCircleIcon} from "@heroicons/react/24/solid";

const ChatMessage = (props) => {
    const {
        id,
        sender,
        content,
        status,
        timestamp,
        open,
        thinking,
        stream,
        final: finalContent,
        finalStatus,
    } = props;

    // 如果是 assistant 的复合回复消息，则按复合渲染
    if (
        sender === "assistant" &&
        (thinking !== undefined || stream !== undefined || finalContent !== undefined)
    ) {
        return (
            <div className={`chat-message ${sender} composite`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style"/>
                        ) : (
                            <CpuChipIcon className="icon-style"/>
                        )}
                    </div>
                    <div className="message-container">
                        {thinking && (
                            <div className="composite-thinking-part">
                                Thinking <span className="dot-flashing"></span>
                            </div>
                        )}
                        {stream && (
                            <CompositePanel panelType="stream" content={stream} timestamp={timestamp}/>
                        )}
                        {(finalStatus === "typing" || finalStatus === "final" || finalContent) && (
                            <CompositePanel
                                panelType="final"
                                content={finalContent}
                                timestamp={timestamp}
                                isTyping={finalStatus === "typing"}
                            />
                        )}
                        <div className="message-timestamp">
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // 如果是 thinking 状态
    if (status === "thinking") {
        return (
            <div className={`chat-message ${sender} thinking`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style"/>
                        ) : (
                            <CpuChipIcon className="icon-style"/>
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
                                minute: "2-digit",
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // 如果是 error 状态
    if (status === "error") {
        return (
            <div className={`chat-message ${sender} error`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style"/>
                        ) : (
                            <CpuChipIcon className="icon-style"/>
                        )}
                    </div>
                    <div className="message-container">
                        <div className="error-message">⚠️ {content}</div>
                        <div className="message-timestamp">
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // 如果是 typing 状态
    if (status === "typing") {
        return (
            <div className={`chat-message ${sender} typing`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style"/>
                        ) : (
                            <CpuChipIcon className="icon-style"/>
                        )}
                    </div>
                    <div className="message-container">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                            {content}
                        </ReactMarkdown>
                        <span className="typing-cursor">▌</span>
                        <div className="message-timestamp">
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // 默认：最终回复或用户消息
    return (
        <div className={`chat-message ${sender} final`}>
            <div className="chat-bubble">
                <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                    {sender === "user" ? (
                        <UserCircleIcon className="icon-style"/>
                    ) : (
                        <CpuChipIcon className="icon-style"/>
                    )}
                </div>
                <div className="message-container">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                        {content}
                    </ReactMarkdown>
                    <div className="message-timestamp">
                        {new Date(timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                        })}
                    </div>
                    {/* 如果是 assistant 的最终回复，提供复制功能 */}
                    {sender === "assistant" && finalStatus === "final" && (
                        <button
                            className="copy-button"
                            onClick={() => navigator.clipboard.writeText(content)}
                            title="Copy message"
                        >
                            📋
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

// Composite Panel 用于显示复合回复中的 stream / final 部分
const CompositePanel = ({panelType, content, timestamp, isTyping}) => {
    const [isOpen, setIsOpen] = useState(true);
    let header = "";
    let body = "";
    if (panelType === "stream") {
        header = "DeepThink";
        body = content;
    } else if (panelType === "final") {
        header = "Answer";
        body = content;
    }
    return (
        <div className={`composite-panel ${panelType}`}>
            <div
                className="composite-panel-header"
                onClick={() => setIsOpen(!isOpen)}
                style={{cursor: "pointer", userSelect: "none"}}
            >
                <span style={{marginRight: "5px"}}>{isOpen ? "▼" : "▶"}</span>
                <strong>{header}</strong>
            </div>
            {isOpen && (
                <div className="composite-panel-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                        {body}
                    </ReactMarkdown>
                    {panelType === "final" && isTyping && <span className="typing-cursor">▌</span>}
                </div>
            )}
        </div>
    );
};

export default ChatMessage;
