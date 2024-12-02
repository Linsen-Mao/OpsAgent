from application.backend.chatbot.conversation import Conversation


class Chatbot:
    def __init__(self):
        """
        Initialize the chatbot
        :param session_id: mostly generated automatically, but can be set manually
        """
        pass

    async def chat_stream(
            self, question: str, conversation: Conversation):
        pass