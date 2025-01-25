// ChatMessage.jsx
import React from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { UserCircleIcon, CpuChipIcon } from '@heroicons/react/24/solid';

const ChatMessage = ({ sender, content, status, timestamp }) => {
  const renderContent = () => {
    switch (status) {
      case 'thinking':
        return (
          <div className="thinking-message">
            <div className="thinking-text">
              Thinking
              <span className="dot-flashing"></span>
            </div>
            <div className="stream-content">
              {content}
              <span className="typing-cursor"></span>
            </div>
          </div>
        );

      case 'final':
        return (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              code({ inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <div className="code-block">
                    <span className="language-tag">{match[1]}</span>
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </div>
                ) : (
                  <code className={`inline-code ${className}`} {...props}>
                    {children}
                  </code>
                );
              }
            }}
          >
            {content}
          </ReactMarkdown>
        );

      case 'error':
        return <div className="error-message">⚠️ {content}</div>;

      default:
        return content;
    }
  };

  return (
    <div className={`chat-message ${sender} ${status}`}>
      <div className="chat-bubble">
        <div className={`avatar ${sender === 'user' ? 'user-avatar' : ''}`}>
          {sender === 'user' ? (
            <UserCircleIcon className="icon-style text-blue-400" />
          ) : (
            <CpuChipIcon className="icon-style text-purple-400" />
          )}
        </div>

        <div className="message-container">
          {renderContent()}
          <div className="message-timestamp">
            {new Date(timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;