import os
from typing import List

from dotenv import load_dotenv
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AnyMessage, ChatMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from typing_extensions import TypedDict, Literal

from application.backend.chatbot.ecommmerce_query import ecommerce_query
from application.backend.chatbot.product_query import process_user_query
from application.backend.chatbot.prompts import product_query_prompt, ecommerce_prompt, supervisor_prompt, final_prompt

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=openai_api_key,
    streaming=False
)


class MessagesState(TypedDict):
    """
    Stores the entire conversation plus any data you want.
    'conversation' must always be a valid instance of Conversation,
    not just a list.
    """
    messages: List[AnyMessage]


class SupervisorState(MessagesState):
    """
    Supervisor's expanded state.
    You can store extra keys like 'next' or 'instructions'.
    """
    next: str
    instructions: str


def get_latest_human_question(state: MessagesState) -> str:
    """Return the most recent human message's text."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


@tool
def ecommerce_chat_tool(state: MessagesState) -> str:
    """
    E-commerce chat tool that uses your Chatbot class.
    This is invoked by the e-commerce agent to handle e-commerce tasks.
    """
    question = get_latest_human_question(state)
    ans = ecommerce_query(question)
    print(f"Chatbot response: {ans}")
    return ans


@tool
def product_query_tool(state: MessagesState) -> str:
    """
    Product selection logic.
    This is invoked by the product-selection agent to handle product queries.
    """
    question = get_latest_human_question(state)
    return process_user_query(question)


product_selection_agent = create_react_agent(
    model,
    tools=[product_query_tool],
    state_modifier=(product_query_prompt),
)

ecommerce_agent = create_react_agent(
    model,
    tools=[ecommerce_chat_tool],
    state_modifier=(ecommerce_prompt),
)


class RouterOutput(TypedDict):
    next: Literal["product_selection_agent", "ecommerce_agent", "FINISH"]
    instructions: str
    reason: str


def produce_final_answer(all_messages: list[AnyMessage], llm: ChatOpenAI) -> str:
    conversation_text = ""

    for msg in all_messages:
        if isinstance(msg, ChatMessage):
            conversation_text += f"[USER]: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            conversation_text += f"[ASSISTANT]: {msg.content}\n"

    final_prompt_text = (
        "SYSTEM PROMPT:\n"
        f"{final_prompt}\n\n"
        "CONVERSATION:\n"
        f"{conversation_text}\n"
        "END.\n"
    )

    result = llm.invoke(final_prompt_text)
    return result.content


def supervisor_node(state: SupervisorState) -> Command[
    Literal["product_selection_agent", "ecommerce_agent", "__end__"]
]:
    conversation_text = ""

    for msg in state["messages"]:
        if isinstance(msg, ChatMessage):
            conversation_text += f"[USER]: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            conversation_text += f"[ASSISTANT]: {msg.content}\n"

    final_prompt_text = (
        "SYSTEM PROMPT:\n"
        f"{supervisor_prompt}\n\n"
        "CONVERSATION:\n"
        f"{conversation_text}\n\n"
        "END OF CONVERSATION.\n"
    )

    llm_output = model.with_structured_output(RouterOutput).invoke(final_prompt_text)

    next_agent = llm_output["next"]
    instructions = llm_output["instructions"]
    title = llm_output["title"]
    reason = llm_output["reason"]

    if next_agent == "FINISH":
        final_answer = produce_final_answer(state["messages"], model)
        finish_msg = AIMessage(content=final_answer, name="supervisor")
        return Command(
            goto=END,
            update={"messages": state["messages"] + [finish_msg]}
        )

    new_user_msg = HumanMessage(content=instructions, title=title, reason=reason, name="supervisor_instructions",
                                role="user")
    updated_msgs = state["messages"] + [new_user_msg]

    return Command(
        goto=next_agent,
        update={"messages": updated_msgs, "next": next_agent, "instructions": instructions}
    )


def product_selection_node(state: SupervisorState) -> Command[Literal["supervisor"]]:
    last_instruction = state["messages"][-1]

    sub_state = {
        "messages": [last_instruction],
    }

    result = product_selection_agent.invoke(sub_state)

    updated_main = {
        "messages": state["messages"] + result["messages"],  # unify results back
    }
    return Command(
        update=updated_main,
        goto="supervisor",
    )


def ecommerce_node(state: SupervisorState) -> Command[Literal["supervisor"]]:
    last_instruction = state["messages"][-1]

    sub_state = {
        "messages": [last_instruction],
    }

    result = ecommerce_agent.invoke(sub_state)

    updated_main = {
        "messages": state["messages"] + result["messages"],
    }
    return Command(
        update=updated_main,
        goto="supervisor",
    )


builder = StateGraph(SupervisorState)
builder.add_edge(START, "supervisor")  # always start at supervisor
builder.add_node("supervisor", supervisor_node)
builder.add_node("product_selection_agent", product_selection_node)
builder.add_node("ecommerce_agent", ecommerce_node)
graph = builder.compile()


def pretty_print_messages(update):
    if isinstance(update, tuple):
        ns, update = update
        if not ns:
            return
        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph: {graph_id}\n")

    for node_name, node_update in update.items():
        print(f"Update from node: {node_name}\n")
        for m in node_update["messages"]:
            role = "assistant"
            if isinstance(m, ChatMessage):
                role = "user"
            name_str = f" ({m.name})" if getattr(m, 'name', '') else ""
            print(f"[{role}{name_str}] {m.content}")
        print()


if __name__ == "__main__":
    user_messages = [
        ("user", "I'm looking for 5 products for automotive applications with a Cortex-M23 chip, "
                 "and also I'd like to know how to add them to my e-commerce site.")
    ]

    initial_state = {
        "messages": [],
        "next": "",
        "instructions": ""
    }

    for _, content in user_messages:
        initial_state["messages"].append(ChatMessage(content=content, role="user"))

    for chunk in graph.stream(initial_state):
        pretty_print_messages(chunk)
