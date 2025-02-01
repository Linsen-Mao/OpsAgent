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
        // 以下字段仅用于 assistant 的复合回复消息
        thinking,
        stream,
        final: finalContent,
        finalStatus,
    } = props;
    
    // 如果是 assistant 的复合回复消息（包含 thinking、stream 或 final 字段），则按复合渲染
    if (
        sender === "assistant" &&
        (thinking !== undefined || stream !== undefined || finalContent !== undefined)
    ) {
        return (
            <div className={`chat-message ${sender} composite`}>
                <div className="chat-bubble">
                    <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                        {sender === "user" ? (
                            <UserCircleIcon className="icon-style text-blue-400"/>
                        ) : (
                            <CpuChipIcon className="icon-style text-purple-400"/>
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

    // 非复合回复消息的渲染逻辑
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
                                minute: "2-digit",
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

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
                                minute: "2-digit",
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

    // 默认最终回复消息的渲染（如用户消息或普通 assistant 消息）
    return (
        <div className={`chat-message ${sender} final`}>
            <div className="chat-bubble">
                <div className={`avatar ${sender === "user" ? "user-avatar" : ""}`}>
                    {sender === "user" ? (
                        <UserCircleIcon className="icon-style text-blue-400"/>
                    ) : (
                        <CpuChipIcon className="icon-style text-purple-400"/>
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
                </div>
            </div>
        </div>
    );
};

// 用于复合回复中 stream / final 部分的可折叠面板组件
const CompositePanel = ({panelType, content, timestamp, isTyping}) => {
    const [isOpen, setIsOpen] = useState(true);
    let header = "";
    let body = "";
    if (panelType === "stream") {
        // stream 面板标题固定为 DeepThink
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
