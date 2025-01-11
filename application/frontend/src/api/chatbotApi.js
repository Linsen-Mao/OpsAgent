// src/api/chatbotApi.js
export async function fetchChatStream(question, conversation) {
    /**
     * 發送 POST，取得 SSE (text/event-stream) 
     *
     * question: (string) 輸入的問題
     * conversation: (List) [{sender, content}, ...]
     */
    const url = "http://localhost:8000/chat_stream"; 
    // 送出請求
    const bodyData = {
      question,
      conversation, // 傳遞列表
    };
  
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(bodyData),
    });
  
    if (!response.ok) {
      throw new Error(`Server responded with ${response.status}`);
    }
  
    // 回傳一個 ReadableStream 讓呼叫方用 reader.read()
    const reader = response.body.getReader();
    return reader;
}
