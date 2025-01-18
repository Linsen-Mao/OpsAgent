import asyncio
import os
from dotenv import load_dotenv
from typing_extensions import Literal, Annotated, TypedDict

from langchain_core.messages import convert_to_messages, HumanMessage, AnyMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.graph import StateGraph, START, add_messages
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState

from langchain_openai import ChatOpenAI

from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.conversation import Conversation

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize LLM
model = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, max_tokens=8000)


##############################################################################
# Tools for handing off to other agents
##############################################################################

from typing_extensions import Annotated
from langchain_core.tools import tool
from langgraph.types import Command
from langgraph.prebuilt import InjectedState

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    conversation: Conversation

def get_latest_human_question(state: MessagesState) -> str:
    """
    Return the content of the most recent HumanMessage in state['messages'].
    If none is found, return an empty string.
    """
    messages = state.get("messages", [])
    # Iterate from the end to find the last HumanMessage
    for msg in reversed(messages):
        # If you're using LangChain or similar, you might check types:
        #   isinstance(msg, HumanMessage)
        # or you can check an attribute like msg['role'] == 'user' or similar:
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""

@tool
def ecommerce_chat_tool(state: Annotated[dict, InjectedState]) -> str:
    """
    Get e-commerce information to help user manage their online store, using your
    vector database Chatbot. This tool is async, so it can be called within an
    async environment without manually creating an event loop.
    """

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
            sender = "unknown"  # Fallback if type isn't recognized

        conversation_data.append({
            "role": sender,
            "content": message.content
        })

    conversation = Conversation(conversation=conversation_data)

    return chatbot.chat_stream(question, conversation)


def make_handoff_tool(*, agent_name: str):
    """Create a tool that can return handoff via a Command"""
    tool_name = f"transfer_to_{agent_name}"

    @tool(tool_name)
    def handoff_to_agent(
            state: Annotated[dict, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        """Ask another agent for help."""
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": tool_name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            # navigate to another agent node in the PARENT graph
            goto=agent_name,
            graph=Command.PARENT,
            # This is the state update that the agent `agent_name` will see when it is invoked.
            # We're passing agent's FULL internal message history AND adding a tool message to make sure
            # the resulting chat history is valid.
            update={"messages": state["messages"] + [tool_message]},
        )

    return handoff_to_agent


@tool
def get_commerce():
    """Get information about e-commerce system management."""
    return

@tool
def get_general():
    """Generate general answer."""
    return

@tool
def get_product_selection():
    """Get information about product selection."""
    return

commerce_tools = [
    ecommerce_chat_tool,
    make_handoff_tool(agent_name="product_selection_agent"),  # match the node name
    make_handoff_tool(agent_name="general_agent"),          # match the node name
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



##############################################################################
# 1) PRODUCT SELECTION AGENT
##############################################################################

# Create a ReAct agent for Product Selection
# This replicates the same "system prompt" logic you had previously:
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
    """
    Mimics the original product_selection_agent functionality using ReAct logic.
    """
    return product_selection_agent.invoke(state)


##############################################################################
# 2) ECOMMERCE AGENT
##############################################################################

ecommerce_agent = create_react_agent(
    model,
    commerce_tools,  # presumably: [ get_commerce, make_handoff_tool(...), ... ]
    state_modifier=(
        "You are an e-commerce expert that can handle queries about online shopping and store management. "
        "If you need product recommendations, ask 'product_selection_agent' for help. "
        "If you need help with general queries, ask 'general_agent' for help. "
    ),
)

# 2) Implement call_ecommerce_agent so it matches the structure of the other two agents.
def call_ecommerce_agent(
    state: MessagesState,
) -> Command[Literal["product_selection_agent", "general_agent", "__end__"]]:
    """
    This now works the same as the other ReAct agents:
      - simply call ecommerce_agent.invoke(state).
      - ReAct logic + your defined tools handle the conversation and routing.
    """
    return ecommerce_agent.invoke(state)


##############################################################################
# 3) GENERAL AGENT
##############################################################################

# Create a ReAct agent for General queries
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
    """
    Mimics the original general_agent functionality using ReAct logic.
    """
    return general_agent.invoke(state)


##############################################################################
# BUILD THE STATE GRAPH
##############################################################################

builder = StateGraph(MessagesState)
builder.add_node("general_agent", call_general_agent)
builder.add_node("ecommerce_agent", call_ecommerce_agent)
builder.add_node("product_selection_agent", call_product_selection_agent)

# We'll always start with the general agent, as in the original code
builder.add_edge(START, "general_agent")

graph = builder.compile()


##############################################################################
# PRETTY PRINT MESSAGES
##############################################################################
def pretty_print_messages(update):
    """
    Replicates the logic in the second snippet for printing updated messages.
    """
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
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


##############################################################################
# MAIN
##############################################################################
if __name__ == '__main__':
    # Example user query that you want to test in this flow
    user_messages = [("user", "how to change the e-commerce system to allow customers to earn loyalty points")]
    # 3) Now call your stream method with the properly formatted conversation:
    for chunk in graph.stream(
        {
            "messages": user_messages,
        }
    ):
        print(chunk)
        pretty_print_messages(chunk)

