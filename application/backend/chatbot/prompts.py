from langchain_core.prompts import ChatPromptTemplate

#TODO answer template
# answer_template = f"""
#
# """
#
# ANSWER_PROMPT = ChatPromptTemplate.from_template(answer_template)

answer_template = f"""
    <instructions>
    You are a young, nice and friendly chatbot specialized in answering questions about the TUM School of Management. At the bottom you have questions asked by a user to you.

    {{question}}

    <history>
    {{chat_history}}
    </history>

    </instructions>

    Answer:

"""

ANSWER_PROMPT = ChatPromptTemplate.from_template(answer_template)