# main.py (Supervisor + Sub-Agents)
import os
from dotenv import load_dotenv
from typing_extensions import TypedDict, Literal
from typing import List

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AnyMessage, ChatMessage,
)
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent

from langchain_openai import ChatOpenAI

# --- Your own logic ---
from application.backend.chatbot.chatbot import Chatbot
from application.backend.chatbot.product_selection import process_user_query

##############################################################################
# 1. Load environment variables and define LLM
##############################################################################
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Supervisor LLM
supervisor_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=openai_api_key,
    streaming=False
)

# Sub-agents can share the same LLM or use different ones
subagent_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=openai_api_key,
    streaming=False
)


##############################################################################
# 2. State Definitions
##############################################################################
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


##############################################################################
# 3. Helpers and Tools
##############################################################################
def get_latest_human_question(state: MessagesState) -> str:
    """Return the most recent human message's text."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


from langchain_core.tools import tool


@tool
def ecommerce_chat_tool(state: MessagesState) -> str:
    """
    E-commerce chat tool that uses your Chatbot class.
    This is invoked by the e-commerce agent to handle e-commerce tasks.
    """
    chatbot = Chatbot()
    question = get_latest_human_question(state)
    ans = chatbot.chat_stream(question)
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


##############################################################################
# 4. Sub-Agent Definitions
##############################################################################
product_selection_agent = create_react_agent(
    subagent_model,
    tools=[product_query_tool],
    state_modifier=(
        "You are a product query expert. Your only functions are: "
        "1. Answer specific parameters about a product. "
        "2. Recommend products based on user-provided parameters. If more than 5 products match, return the top 5 "
        "and suggest additional parameters for narrowing the search. These additional parameters must be derived "
        "from the database and relevant to the current product set. "
        "You must always call product_query_tool to fetch product related information."
        "Respond with your findings or clarifications."
    ),
)

ecommerce_agent = create_react_agent(
    subagent_model,
    tools=[ecommerce_chat_tool],
    state_modifier=(
        "You, the e-commerce agent, do not have direct e-commerce knowledge. You must call ecommerce_chat_tool to fetch e-commerce related instructions."
        "You can assist in configuring new features on the website, uploading products, and similar tasks."
        "Respond with your findings or clarifications."
    ),
)


# ---------- Only the Changed Code Below ----------

#
# 1) Modify the RouterOutput to include a "reason" field
#
class RouterOutput(TypedDict):
    next: Literal["product_selection_agent", "ecommerce_agent", "FINISH"]
    instructions: str
    reason: str  # A short explanation from the LLM about why it wants this next step

#
# 2) Update supervisor_prompt to instruct the LLM to include "reason"
#
supervisor_prompt = (
    "You are a supervisor overseeing a conversation with two workers: "
    "'product_selection_agent' and 'ecommerce_agent'. You can decide which worker "
    "to call next or to finish the conversation.\n\n"
    "Rules:\n"
    "1) If you believe there's enough information to fulfill the user's request, "
    "   respond with 'FINISH' and empty instructions.\n"
    "2) If you believe there's NOT enough user information, you can respond with 'FINISH' "
    "   but put a clarifying question in 'instructions'.\n"
    "3) If you need information about e-commerce content, you can route to 'ecommerce_agent'.\n"
    "   If you need information about product query, you can route to 'product_selection_agent'.\n"
    "4) Your output MUST be valid JSON with the schema:\n"
    "Output Requirements:\n"
    "{\n"
    '  "next": "agent_name/FINISH",\n'
    '  "instructions": "concrete task description",\n'
    '  "reason": "technical justification"\n'
    "}\n\n"
)


final_prompt = (
    "You are the supervisor, responsible for generating the final answer to the user. "
    "You are part of a Knowledge-Integrated Chatbot designed to provide expert guidance and support for managing an e-commerce platform built on Prestashop.\n"
    "\n"
    "Your responsibilities include:\n"
    "- Combining all relevant data from the conversation, including sub-agent outputs.\n"
    "- Providing clear, concise, and actionable responses for managing the Prestashop platform, such as:\n"
    "  - Configuration, module installation, and settings adjustments.\n"
    "  - Product management, order processing, and customer service optimization.\n"
    "  - Troubleshooting technical issues, including debugging Prestashop errors and server-related problems.\n"
    "  - Recommending strategies for improving store performance, SEO, and user experience.\n"
    "  - Explaining Prestashop integrations with third-party tools (e.g., payment gateways, shipping services, analytics tools).\n"
    "- Answering user inquiries about specific product parameters.\n"
    "- Assisting users in selecting the best products based on their needs, preferences, or use cases by comparing features and offering recommendations.\n"
    "\n"
    "Your task is to produce a final answer to the user's request by combining all relevant information. "
    "Ensure your response is comprehensive and leverages all sub-agent contributions. "
    "Do NOT omit or ignore any sub-agent's data, and thoroughly summarize and respond to the user's query. "
    "When responding to product inquiries or recommendations, provide detailed and accurate comparisons or parameters, where applicable."
    "The answer MUST be in Markdown format, remove unnecessary blank lines\n"
)


#
# 4) Helper function to produce final answer from all messages
#
def produce_final_answer(all_messages: list[AnyMessage], llm: ChatOpenAI) -> str:
    # final_prompt is your system-level instruction
    # We’ll merge it into a single string with the conversation
    conversation_text = ""

    for msg in all_messages:
        if isinstance(msg, ChatMessage):
            conversation_text += f"[USER]: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            conversation_text += f"[ASSISTANT]: {msg.content}\n"

    # Combine final_prompt and the conversation into one large string
    final_prompt_text = (
        "SYSTEM PROMPT:\n"
        f"{final_prompt}\n\n"
        "CONVERSATION:\n"
        f"{conversation_text}\n"
        "END.\n"
    )

    # Invoke the LLM with a single string prompt
    result = llm.invoke(final_prompt_text)
    # Return the final text content
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

    # Combine everything into one big string
    # The system text can remain "system-level" instructions.
    # Then you show conversation_text below it.
    final_prompt_text = (
        "SYSTEM PROMPT:\n"
        f"{supervisor_prompt}\n\n"
        "CONVERSATION:\n"
        f"{conversation_text}\n\n"
        "END OF CONVERSATION.\n"
    )

    # Now call LLM with a single string
    # .with_structured_output(RouterOutput) ensures you parse JSON as { next, instructions, reason }
    llm_output = supervisor_model.with_structured_output(RouterOutput).invoke(final_prompt_text)

    next_agent = llm_output["next"]
    instructions = llm_output["instructions"]

    if next_agent == "FINISH":
            final_answer = produce_final_answer(state["messages"], supervisor_model)
            finish_msg = AIMessage(content=final_answer, name="supervisor")
            return Command(
                goto=END,
                update={"messages": state["messages"] + [finish_msg]}
            )

    # Otherwise, we route to the chosen agent
    new_user_msg = HumanMessage(content=instructions, name="supervisor_instructions",role="user")
    updated_msgs = state["messages"] + [new_user_msg]

    # Save next_agent + instructions so we can check them on next loop
    return Command(
        goto=next_agent,
        update={"messages": updated_msgs, "next": next_agent, "instructions": instructions}
    )


##############################################################################
# 6. Sub-Agent Nodes
##############################################################################

def product_selection_node(state: SupervisorState) -> Command[Literal["supervisor"]]:
    """
    1) Extract the last instruction from the Supervisor.
    2) Build a minimal sub-state that includes ONLY that instruction.
    3) Call product_selection_agent with that minimal sub-state.
    4) Return the updated conversation to the Supervisor.
    """
    # The last message is the Supervisor’s instruction: state["messages"][-1]
    # We'll make a new minimal state for the sub-agent.

    last_instruction = state["messages"][-1]  # e.g. HumanMessage(...) from 'supervisor_instructions'

    sub_state = {
        "messages": [last_instruction],  # The sub-agent sees ONLY this single instruction
    }

    # Invoke the product_selection_agent with our new minimal sub-state
    result = product_selection_agent.invoke(sub_state)

    # Now we take the sub-agent's final message(s) and append them to the main state's messages
    updated_main = {
        "messages": state["messages"] + result["messages"],  # unify results back
    }
    return Command(
        update=updated_main,
        goto="supervisor",
    )


def ecommerce_node(state: SupervisorState) -> Command[Literal["supervisor"]]:
    """
    Same logic as product_selection_node, but for the e-commerce agent.
    """
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


##############################################################################
# 7. Build the Graph
##############################################################################
builder = StateGraph(SupervisorState)
builder.add_edge(START, "supervisor")  # always start at supervisor
builder.add_node("supervisor", supervisor_node)
builder.add_node("product_selection_agent", product_selection_node)
builder.add_node("ecommerce_agent", ecommerce_node)
graph = builder.compile()


##############################################################################
# 8. Pretty-print for streaming (optional)
##############################################################################
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


##############################################################################
# 9. Demo usage
##############################################################################
if __name__ == "__main__":
    # Example user messages that combine product queries and e-commerce
    user_messages = [
        ("user", "I'm looking for 5 products for automotive applications with a Cortex-M23 chip, "
                 "and also I'd like to know how to add them to my e-commerce site.")
    ]

    # IMPORTANT: conversation must be a valid Conversation object, not a raw list
    initial_state = {
        "messages": [],
        "next": "",
        "instructions": ""
    }

    # Convert user_messages into ChatMessage objects
    for _, content in user_messages:
        initial_state["messages"].append(ChatMessage(content=content, role="user"))

    # Stream the conversation through the graph
    for chunk in graph.stream(initial_state):
        pretty_print_messages(chunk)

