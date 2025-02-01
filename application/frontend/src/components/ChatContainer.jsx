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

    const TYPING_SPEED = 5;


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

    const updateLocal = (newMsgs) => {
        setLocalMessages(newMsgs);
    };

    const syncToParent = (msgs) => {
        onUpdateMessages(msgs);
    };

    const handleSend = async () => {
        if (!userInput.trim() || loading) return;
        setLoading(true);

        const userMsg = {
            sender: "user",
            content: userInput,
            id: uuidv4(),
            timestamp: Date.now()
        };
        const updatedUser = [...localMessages, userMsg];
        updateLocal(updatedUser);

        const thinkingId = uuidv4();
        const updatedThinking = [
            ...updatedUser,
            {
                sender: "assistant",
                content: "Thinking ",
                id: thinkingId,
                status: "thinking",
                timestamp: Date.now()
            }
        ];
        updateLocal(updatedThinking);

        setUserInput("");

        try {
            const reader = await fetchChatStream(userInput, updatedUser);

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

                        if (parsed.type === "final") {
                            let removeThinking = updatedThinking.filter(
                                (m) => m.id !== thinkingId
                            );
                            const finalMsgId = uuidv4();
                            let newMsg = {
                                sender: "assistant",
                                content: "",
                                id: finalMsgId,
                                status: "typing",
                                timestamp: Date.now()
                            };
                            let updatedTyping = [...removeThinking, newMsg];
                            updateLocal(updatedTyping);

                            typeOutFinalAnswer(parsed.data, finalMsgId);

                            onUpdateMessages(localMessages);
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

            let removeThinking = localMessages.filter((m) => m.id !== thinkingId);
            updateLocal([
                ...removeThinking,
                {
                    sender: "assistant",
                    content: "Error: Failed to get response",
                    id: uuidv4(),
                    status: "error",
                    timestamp: Date.now()
                }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const typeOutFinalAnswer = (fullText, messageId) => {
        let index = 0;

        const typeChar = () => {
            if (index < fullText.length) {
                const currentText = fullText.slice(0, index + 1);
                setLocalMessages((prev) =>
                    prev.map((m) =>
                        m.id === messageId ? {...m, content: currentText} : m
                    )
                );
                index++;
                typingTimeoutRef.current = setTimeout(typeChar, TYPING_SPEED);
            } else {
                setLocalMessages((prev) =>
                    prev.map((m) =>
                        m.id === messageId ? {...m, status: "final"} : m
                    )
                );
            }
        };
        typeChar();
    };

    const handleKeyDown = (e) => {
        if (e.nativeEvent.isComposing) {
            return;
        }
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {localMessages.map((m) => (
                    <ChatMessage
                        key={m.id}
                        sender={m.sender}
                        content={m.content}
                        status={m.status}
                        timestamp={m.timestamp}
                    />
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
