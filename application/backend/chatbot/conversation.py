from typing import Optional

from pydantic import BaseModel

class Message(BaseModel):
    """
    A message in the conversation, it has a role and content, then the AI and Human Message classes are derived from this class
    """
    role: str
    content: str


class Conversation(BaseModel):
    """
    A conversation object is all the data that is needed to keep track of a conversation for the bot and save all the
    necessary data
    """
    conversation: list[Message]
    chat_uuid: Optional[str] = None


#TODO format_chat_history function
def format_chat_history(conversation: Conversation) -> str:
    pass