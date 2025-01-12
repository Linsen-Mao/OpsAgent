from langchain_core.prompts import ChatPromptTemplate

#TODO answer template
# answer_template = f"""
#
# """
#
# ANSWER_PROMPT = ChatPromptTemplate.from_template(answer_template)

answer_template = f"""
    <instructions>

    {{question}}

    <history>
    {{chat_history}}
    </history>

    </instructions>

    Answer:

"""

ANSWER_PROMPT = ChatPromptTemplate.from_template(answer_template)