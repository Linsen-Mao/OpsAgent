import React, {useEffect, useRef, useState} from "react";
import {v4 as uuidv4} from "uuid";
import ChatMessage from "./ChatMessage";
import {fetchChatStream} from "../api/chatbotApi";

const ChatContainer = ({conversation, onUpdateMessages}) => {
    const [localMessages, setLocalMessages] = useState(conversation.messages);
    const [userInput, setUserInput] = useState("");
    const [loading, setLoading] = useState(false);

    const messageEndRef = useRef(null);
    const typingTimeoutRef = useRef(null);
    const streamBaseRef = useRef({});
    const streamChainRef = useRef({});

    const TYPING_SPEED = 10;
    const TYPING_SPEED_FINAL = 5;

    useEffect(() => {
        setLocalMessages(conversation.messages);
    }, [conversation.id]);

    useEffect(() => {
        messageEndRef.current?.scrollIntoView({behavior: "smooth"});
    }, [localMessages]);

    useEffect(() => {
        return () => {
            if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
        };
    }, []);

    // 清除后端返回内容前后的 ```markdown 和 ```
    const cleanMarkdown = (content) => {
        return content.replace(/^```markdown\s*|```$/g, "");
    };

    const updateAssistantMessage = (messageId, updater) => {
        setLocalMessages((prev) =>
            prev.map((m) => (m.id === messageId ? updater(m) : m))
        );
    };

    const typeOutStreamChunk = (newChunk, messageId) => {
        return new Promise((resolve) => {
            const cleanedChunk = cleanMarkdown(newChunk);
            const currentBase = streamBaseRef.current[messageId] || "";
            const separator = currentBase ? "\n\n" : "";
            const baseForNewChunk = currentBase + separator;
            let index = 0;
            const typeChar = () => {
                if (index < cleanedChunk.length) {
                    updateAssistantMessage(messageId, (msg) => ({
                        ...msg,
                        stream: baseForNewChunk + cleanedChunk.slice(0, index + 1),
                        content: baseForNewChunk + cleanedChunk.slice(0, index + 1),
                    }));
                    index++;
                    typingTimeoutRef.current = setTimeout(typeChar, TYPING_SPEED);
                } else {
                    streamBaseRef.current[messageId] = baseForNewChunk + cleanedChunk;
                    updateAssistantMessage(messageId, (msg) => ({
                        ...msg,
                        stream: streamBaseRef.current[messageId],
                        content: streamBaseRef.current[messageId],
                    }));
                    resolve();
                }
            };
            typeChar();
        });
    };

    const typeOutFinalAnswer = (fullText, messageId) => {
        return new Promise((resolve) => {
            const cleanedText = cleanMarkdown(fullText);
            let index = 0;
            const typeChar = () => {
                if (index < cleanedText.length) {
                    const currentText = cleanedText.slice(0, index + 1);
                    updateAssistantMessage(messageId, (msg) => ({
                        ...msg,
                        final: currentText,
                        content: currentText,
                    }));
                    index++;
                    typingTimeoutRef.current = setTimeout(typeChar, TYPING_SPEED_FINAL);
                } else {
                    updateAssistantMessage(messageId, (msg) => ({
                        ...msg,
                        finalStatus: "final",
                    }));
                    resolve();
                }
            };
            typeChar();
        });
    };

    const handleSend = async () => {
        if (!userInput.trim() || loading) return;
        setLoading(true);

        // 添加用户消息
        const userMsg = {
            sender: "user",
            content: userInput,
            id: uuidv4(),
            timestamp: Date.now(),
        };

        // 创建 assistant 的复合回复消息
        const assistantMsgId = uuidv4();
        streamBaseRef.current[assistantMsgId] = "";
        streamChainRef.current[assistantMsgId] = Promise.resolve();
        const assistantMsg = {
            sender: "assistant",
            id: assistantMsgId,
            timestamp: Date.now(),
            thinking: true,
            stream: "",
            final: "",
            finalStatus: "pending",
            content: "Thinking",
        };

        const updatedMessages = [...localMessages, userMsg, assistantMsg];
        setLocalMessages(updatedMessages);
        onUpdateMessages(updatedMessages);
        setUserInput("");

        try {
            const reader = await fetchChatStream(userInput, updatedMessages);
            let buffer = "";
            const processChunk = async () => {
                const {done, value} = await reader.read();
                if (done) {
                    onUpdateMessages(localMessages);
                    return;
                }
                buffer += new TextDecoder("utf-8").decode(value);
                const events = buffer.split("\n\n");
                buffer = events.pop() || "";
                for (const event of events) {
                    const dataLine = event.split("\n").find((line) => line.startsWith("data: "));
                    if (!dataLine) continue;
                    try {
                        const parsed = JSON.parse(dataLine.slice(6));
                        if (parsed.type === "stream") {
                            const {title, reason} = parsed.data;
                            const newLine = `**${title}**\n\n${reason}`;
                            streamChainRef.current[assistantMsgId] = streamChainRef.current[assistantMsgId]
                                .then(() => typeOutStreamChunk(newLine, assistantMsgId));
                        } else if (parsed.type === "final") {
                            streamChainRef.current[assistantMsgId] = streamChainRef.current[assistantMsgId]
                                .then(() => {
                                    updateAssistantMessage(assistantMsgId, (msg) => ({
                                        ...msg,
                                        thinking: false,
                                        finalStatus: "typing",
                                    }));
                                    return typeOutFinalAnswer(parsed.data, assistantMsgId);
                                });
                        }
                    } catch (err) {
                        console.error("Parse error:", err);
                    }
                }
                processChunk();
            };
            processChunk();
        } catch (error) {
            console.error("SSE Error:", error);
            updateAssistantMessage(assistantMsgId, (msg) => ({
                ...msg,
                thinking: false,
                final: "Error: Failed to get response",
                finalStatus: "final",
                content: "Error: Failed to get response",
            }));
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.nativeEvent.isComposing) return;
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {localMessages.length === 0 ? (
                    <div className="empty-chat">
                        <h1>OpsAgent</h1>
                        <p>Welcome to Prestashop Support Chat.<br/>Ask me anything!</p>
                    </div>
                ) : (
                    localMessages.map((m) => (
                        <ChatMessage key={m.id} {...m} />
                    ))
                )}
                <div ref={messageEndRef}/>
            </div>
            <div className="chat-input-area">
        <textarea
            rows="1"
            placeholder="Send a message..."
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
        />
                <button onClick={handleSend} disabled={loading}>
                    {loading ? "Thinking..." : "Send"}
                </button>
            </div>
        </div>
    );
};

export default ChatContainer;
