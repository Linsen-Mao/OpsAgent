import asyncio
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing_extensions import Literal

from langchain_core.tools import tool
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.types import Command

from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.conversation import Conversation

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize LLM
model = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, max_tokens=8000)


# Define a helper for each of the agent nodes to call


@tool
def transfer_to_product_selection():
    """Transfer to product selection agent for product recommendations."""
    return


@tool
def transfer_to_ecommerce():
    """Transfer to ecommerce agent for handling e-commerce queries."""
    return


@tool
def transfer_to_general():
    """Transfer to general agent for handling general queries."""
    return

def product_selection_agent(
    state: MessagesState,
) -> Command[Literal["ecommerce_agent", "general_agent", "__end__"]]:
    system_prompt = """You are a product selection expert that can recommend products based on dimensions and requirements. 
    If you need help with e-commerce queries, ask 'ecommerce_agent' for help.
    If you need help with general queries, ask 'general_agent' for help."""

    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    ai_msg = model.bind_tools([transfer_to_ecommerce, transfer_to_general]).invoke(messages)
    # If there are tool calls, the LLM needs to hand off to another agent
    if len(ai_msg.tool_calls) > 0:
        tool_call = ai_msg.tool_calls[-1]
        tool_call_id = ai_msg.tool_calls[-1]["id"]
        # NOTE: it's important to insert a tool message here because LLM providers are expecting
        # all AI messages to be followed by a corresponding tool result message
        tool_msg = {
            "role": "tool",
            "content": "Successfully transferred",
            "tool_call_id": tool_call_id,
        }

        if "ecommerce" in tool_call["name"]:
            return Command(goto="ecommerce_agent", update={"messages": [ai_msg, tool_msg]})
        else:
            return Command(goto="general_agent", update={"messages": [ai_msg, tool_msg]})

    # If the expert has an answer, return it directly to the user
    return {"messages": [ai_msg]}

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


def ecommerce_agent(
    state: MessagesState,
) -> Command[Literal["product_selection_agent", "general_agent", "__end__"]]:
    """
    Example of refactoring the ecommerce_agent to use the new Chatbot class
    and maintain the logic for routing between product_selection_agent and general_agent.
    """
    # A system prompt to remind the LLM of its role (optional):
    system_prompt = """You are an e-commerce expert that can handle queries about online shopping and store management. 
    If you need product recommendations, ask 'product_selection_agent' for help.
    If you need help with general queries, ask 'general_agent' for help."""

    # Extract the user's latest question from state
    # (Adjust if your state structure differs)
    user_question = get_latest_human_question(state) if state["messages"] else ""

    # Retrieve or initialize a Conversation object in the state
    if "conversation" not in state:
        state["conversation"] = Conversation(conversation=[])
    conversation = state["conversation"]

    # Prepend your system prompt to the conversation if desired
    # (Alternatively, you could incorporate it directly in chat_stream context)
    conversation.add_message("system", system_prompt)

    # Initialize the new chatbot
    chatbot = Chatbot()

    # Because chat_stream is async, we need to run it in an event loop and collect the stream chunks
    loop = asyncio.get_event_loop()
    collected_chunks = []

    async def collect_stream():
        async for chunk in chatbot.chat_stream(user_question, conversation):
            collected_chunks.append(chunk)

    loop.run_until_complete(collect_stream())

    user_question_lower = user_question.lower()
    if "recommend" in user_question_lower or "product" in user_question_lower:
        return Command(goto="product_selection_agent", update={"messages": collected_chunks})
    else:
        return Command(goto="general_agent", update={"messages": collected_chunks})


def general_agent(
        state: MessagesState,
) -> Command[Literal["product_selection_agent", "ecommerce_agent", "__end__"]]:
    system_prompt = """You are a general assistant that can help with various queries. 
    If you need product recommendations, ask 'product_selection_agent' for help.
    If you need help with e-commerce queries, ask 'ecommerce_agent' for help."""

    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    ai_msg = model.bind_tools([transfer_to_product_selection, transfer_to_ecommerce]).invoke(messages)

    if len(ai_msg.tool_calls) > 0:
        tool_call = ai_msg.tool_calls[-1]
        tool_call_id = ai_msg.tool_calls[-1]["id"]
        # NOTE: it's important to insert a tool message here because LLM providers are expecting
        # all AI messages to be followed by a corresponding tool result message
        tool_msg = {
            "role": "tool",
            "content": "Successfully transferred",
            "tool_call_id": tool_call_id,
        }

        if "product" in tool_call["name"]:
            return Command(goto="product_selection_agent", update={"messages": [ai_msg, tool_msg]})
        else:
            return Command(goto="ecommerce_agent", update={"messages": [ai_msg, tool_msg]})

    # If the expert has an answer, return it directly to the user
    return {"messages": [ai_msg]}



builder = StateGraph(MessagesState)
builder.add_node("general_agent", general_agent)
builder.add_node("ecommerce_agent", ecommerce_agent)
builder.add_node("product_selection_agent", product_selection_agent)

# we'll always start with a general agent
builder.add_edge(START, "general_agent")

graph = builder.compile()

from IPython.display import display, Image

display(Image(graph.get_graph().draw_mermaid_png()))

from langchain_core.messages import convert_to_messages, HumanMessage


def pretty_print_messages(update):
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

if __name__ == '__main__':
    for chunk in graph.stream(
            {"messages": [("user", "how to allows customers to earn loyalty points, use referrals, and be part of our loyalty program")]}
    ):
        pretty_print_messages(chunk)