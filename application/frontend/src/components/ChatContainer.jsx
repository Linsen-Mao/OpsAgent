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
    // 保存每个 assistant 消息当前已完成的 stream 文本
    const streamBaseRef = useRef({});
    // 保存每个 assistant 消息的 stream 逐字打印“链”
    const streamChainRef = useRef({});

    // 打字速度（毫秒）
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

    // 更新指定 assistant 消息（复合消息）的内容
    const updateAssistantMessage = (messageId, updater) => {
        setLocalMessages((prev) =>
            prev.map((m) => (m.id === messageId ? updater(m) : m))
        );
    };

    // 对 stream 新 chunk 进行逐字打字效果，并返回一个 Promise，当打字完成后 resolve
    const typeOutStreamChunk = (newChunk, messageId) => {
        return new Promise((resolve) => {
            const currentBase = streamBaseRef.current[messageId] || "";
            // 如果已有内容，先添加换行
            const separator = currentBase ? "\n\n" : "";
            const baseForNewChunk = currentBase + separator;
            let index = 0;
            const typeChar = () => {
                if (index < newChunk.length) {
                    updateAssistantMessage(messageId, (msg) => ({
                        ...msg,
                        stream: baseForNewChunk + newChunk.slice(0, index + 1),
                        content: baseForNewChunk + newChunk.slice(0, index + 1), // 同步 content 字段（供后端读取）
                    }));
                    index++;
                    typingTimeoutRef.current = setTimeout(typeChar, TYPING_SPEED);
                } else {
                    // 保存完整的新 chunk 到 streamBase 中
                    streamBaseRef.current[messageId] = baseForNewChunk + newChunk;
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

    // 对最终答案进行逐字打字效果，并返回 Promise
    const typeOutFinalAnswer = (fullText, messageId) => {
        return new Promise((resolve) => {
            let index = 0;
            const typeChar = () => {
                if (index < fullText.length) {
                    const currentText = fullText.slice(0, index + 1);
                    updateAssistantMessage(messageId, (msg) => ({
                        ...msg,
                        final: currentText,
                        content: currentText, // 同步 content 字段
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

        // 用户消息
        const userMsg = {
            sender: "user",
            content: userInput,
            id: uuidv4(),
            timestamp: Date.now(),
        };

        // 创建 assistant 的复合回复消息，包含三个部分：thinking、stream、final
        // 同时保证顶级 content 字段存在（后端读取时用到）
        const assistantMsgId = uuidv4();
        // 初始化该消息的 streamBase 和 streamChain
        streamBaseRef.current[assistantMsgId] = "";
        streamChainRef.current[assistantMsgId] = Promise.resolve();
        const assistantMsg = {
            sender: "assistant",
            id: assistantMsgId,
            timestamp: Date.now(),
            thinking: true,
            stream: "",
            final: "",
            finalStatus: "pending", // 后续更新为 "typing" 再变为 "final"
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
                            // 这里后端返回的 stream 数据包含 title 与 reason，
                            // 格式化为 "**title**\nreason"
                            const {title, reason} = parsed.data;
                            const newLine = `**${title}**\n\n${reason}`;
                            // 将本次 stream 打字任务追加到该 assistant 消息的链上
                            streamChainRef.current[assistantMsgId] = streamChainRef.current[assistantMsgId]
                                .then(() => typeOutStreamChunk(newLine, assistantMsgId));
                        } else if (parsed.type === "final") {
                            // 收到 final 消息后，不立即启动最终答案的打字，
                            // 而是将其追加到 streamChain 链上，等待所有 stream 打字完成后再执行
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
                {localMessages.map((m) => (
                    <ChatMessage key={m.id} {...m} />
                ))}
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
