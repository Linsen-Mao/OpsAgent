import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing_extensions import Literal

from langchain_core.tools import tool
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.types import Command


# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize LLM
model = ChatOpenAI(model="gpt-4", api_key=openai_api_key)


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


def ecommerce_agent(
    state: MessagesState,
) -> Command[Literal["product_selection_agent", "general_agent", "__end__"]]:
    system_prompt = """You are an e-commerce expert that can handle queries about online shopping and store management. 
    If you need product recommendations, ask 'product_selection_agent' for help.
    If you need help with general queries, ask 'general_agent' for help."""

    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    ai_msg = model.bind_tools([transfer_to_product_selection, transfer_to_general]).invoke(messages)

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
            return Command(goto="general_agent", update={"messages": [ai_msg, tool_msg]})

    # If the expert has an answer, return it directly to the user
    return {"messages": [ai_msg]}


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

from langchain_core.messages import convert_to_messages


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
            {"messages": [("user", "I want to buy product")]}
    ):
        pretty_print_messages(chunk)