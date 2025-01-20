# conversation.py (same as you provided, but can be left unchanged)
from typing import Optional, List

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import messages_to_dict, BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, PrivateAttr

from langchain.chains.summarize import load_summarize_chain
from langchain_community.llms import OpenAI
from langchain.prompts import PromptTemplate


class Message(BaseModel):
    """
    Represents a single message in the conversation.
    """
    sender: str  # e.g., "user" or "bot"
    content: str  # The message text


class Conversation(BaseModel):
    """
    A conversation object is all the data that is needed to keep track
    of a conversation for the bot and save all necessary data.
    """
    conversation: List[Message]
    chat_uuid: Optional[str] = None

    _message_history: ChatMessageHistory = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize message history
        self._message_history = ChatMessageHistory()

        # Populate message history from the conversation
        for message in self.conversation:
            if message.sender == "user":
                self._message_history.add_user_message(message.content)
            elif message.sender == "bot":
                self._message_history.add_ai_message(message.content)

    def add_message(self, sender: str, content: str):
        """
        Add a message to the conversation and update the LangChain message history.
        """
        self.conversation.append(Message(sender=sender, content=content))
        if sender == "user":
            self._message_history.add_user_message(content)
        elif sender == "bot":
            self._message_history.add_ai_message(content)

    def get_history(self):
        """
        Return the full conversation history as a LangChain-compatible list of messages.
        """
        return self._message_history.messages

    def serialize(self):
        """
        Serialize the conversation for storage or debugging.
        """
        return {
            "conversation": [msg.dict() for msg in self.conversation],
            "chat_uuid": self.chat_uuid
        }

    def deserialize(self, data):
        """
        Load a conversation from serialized data.
        """
        self.conversation = [Message(**msg) for msg in data["conversation"]]
        self.chat_uuid = data.get("chat_uuid")
        self._message_history = ChatMessageHistory()
        for message in self.conversation:
            if message.sender == "user":
                self._message_history.add_user_message(message.content)
            elif message.sender == "bot":
                self._message_history.add_ai_message(message.content)

    def to_langchain_format(self):
        """
        Convert conversation history to a LangChain-compatible format.
        """
        return messages_to_dict(self._message_history.messages)

    def from_langchain_format(self, messages: List[BaseMessage]):
        """
        Load conversation history from a LangChain-compatible format.
        """
        self._message_history = ChatMessageHistory(messages=messages)
        self.conversation = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                self.conversation.append(Message(sender="user", content=msg.content))
            elif isinstance(msg, AIMessage):
                self.conversation.append(Message(sender="bot", content=msg.content))


def format_chat_history(conversation: Conversation) -> str:
    """
    Format chat history to a string. If the length of the conversation messages
    is more than 4, compress the history using LangChain summarization.
    """
    if len(conversation.conversation) <= 4:
        return "\n".join([f"{msg.sender}: {msg.content}" for msg in conversation.conversation])

    full_history = "\n".join([f"{msg.sender}: {msg.content}" for msg in conversation.conversation])
    llm = OpenAI(model="text-davinci-003")  # Summarization model
    summarize_chain = load_summarize_chain(llm, chain_type="stuff")

    prompt_template = PromptTemplate(
        input_variables=["text"],
        template="Summarize the following conversation history in a concise way:\n\n{text}"
    )

    compressed_history = summarize_chain.run(
        input_document=full_history,
        prompt_template=prompt_template
    )
    return f"Summary of the conversation:\n\n{compressed_history}"
