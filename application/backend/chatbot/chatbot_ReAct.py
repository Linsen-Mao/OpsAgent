import os
from dotenv import load_dotenv
from typing_extensions import Literal, Annotated, TypedDict

from langchain_core.messages import convert_to_messages, HumanMessage, AnyMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.graph import StateGraph, START, add_messages
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState

from langchain_openai import ChatOpenAI

from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.conversation import Conversation

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, max_tokens=8000)

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    conversation: Conversation

def get_latest_human_question(state: MessagesState) -> str:
    """Return the most recent HumanMessage."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""

@tool
def ecommerce_chat_tool(state: Annotated[dict, InjectedState]) -> str:
    """Handle e-commerce chat tool."""
    chatbot = Chatbot()
    question = get_latest_human_question(state)
    messages = state.get("messages", [])
    conversation_data = []

    for message in messages:
        if isinstance(message, HumanMessage):
            sender = "user"
        elif isinstance(message, AIMessage):
            sender = "assistant"
        else:
            sender = "unknown"

        conversation_data.append({
            "role": sender,
            "content": message.content
        })

    conversation = Conversation(conversation=conversation_data)

    return chatbot.chat_stream(question, conversation)

def make_handoff_tool(*, agent_name: str):
    """Create a handoff tool."""
    tool_name = f"transfer_to_{agent_name}"

    @tool(tool_name)
    def handoff_to_agent(
            state: Annotated[dict, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        """Handoff to another agent."""
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": tool_name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={"messages": state["messages"] + [tool_message]},
        )

    return handoff_to_agent

@tool
def get_commerce():
    """Handle e-commerce queries."""
    return

@tool
def get_general():
    """Handle general queries."""
    return

@tool
def get_product_selection():
    """Handle product selection queries."""
    return

commerce_tools = [
    ecommerce_chat_tool,
    make_handoff_tool(agent_name="product_selection_agent"),
    make_handoff_tool(agent_name="general_agent"),
]

general_tools = [
    get_general,
    make_handoff_tool(agent_name="product_selection_agent"),
    make_handoff_tool(agent_name="ecommerce_agent"),
]

product_tools = [
    get_product_selection,
    make_handoff_tool(agent_name="ecommerce_agent"),
    make_handoff_tool(agent_name="general_agent"),
]

product_selection_agent = create_react_agent(
    model,
    product_tools,
    state_modifier=(
        "You are a product selection expert that can recommend products based on dimensions and requirements. "
        "If you need help with e-commerce queries, ask 'ecommerce_agent' for help. "
        "If you need help with general queries, ask 'general_agent' for help. "
    ),
)

def call_product_selection_agent(
    state: MessagesState,
) -> Command[Literal["ecommerce_agent", "general_agent", "__end__"]]:
    """Call the product selection agent."""
    return product_selection_agent.invoke(state)

ecommerce_agent = create_react_agent(
    model,
    commerce_tools,
    state_modifier=(
        "You are an e-commerce expert that can handle queries about online shopping and store management. "
        "If you need product recommendations, ask 'product_selection_agent' for help. "
        "If you need help with general queries, ask 'general_agent' for help. "
    ),
)

def call_ecommerce_agent(
    state: MessagesState,
) -> Command[Literal["product_selection_agent", "general_agent", "__end__"]]:
    """Call the e-commerce agent."""
    return ecommerce_agent.invoke(state)

general_agent = create_react_agent(
    model,
    general_tools,
    state_modifier=(
        "You are a general assistant that can help with various queries. "
        "If you need product recommendations, ask 'product_selection_agent' for help. "
        "If you need any help with e-commerce, ask 'ecommerce_agent' for help. "
    ),
)

def call_general_agent(
    state: MessagesState,
) -> Command[Literal["product_selection_agent", "ecommerce_agent", "__end__"]]:
    """Call the general agent."""
    return general_agent.invoke(state)

builder = StateGraph(MessagesState)
builder.add_node("general_agent", call_general_agent)
builder.add_node("ecommerce_agent", call_ecommerce_agent)
builder.add_node("product_selection_agent", call_product_selection_agent)

builder.add_edge(START, "general_agent")

graph = builder.compile()

def pretty_print_messages(update):
    """Pretty print messages."""
    if isinstance(update, tuple):
        ns, update = update
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:")
        print("\n")

    for node_name, node_update in update.items():
        print(f"Update from node {node_name}:")
        print("\n")

        for m in convert_to_messages(node_update["messages"]):
            m.pretty_print()
        print("\n")

if __name__ == '__main__':
    user_messages = [("user", "how to change the e-commerce system to allow customers to earn loyalty points")]
    for chunk in graph.stream(
        {
            "messages": user_messages,
        }
    ):
        print(chunk)
        pretty_print_messages(chunk)
