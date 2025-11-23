import random

from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai.types.responses import response
from pydantic import BaseModel, Field

from aws_telegram_bot.config import settings
from aws_telegram_bot.infrastructure.clients.openai import get_openai_client
from aws_telegram_bot.infrastructure.clients.elevenlabs import get_elevenlabs_client
from aws_telegram_bot.domain.prompts import ROUTER_SYSTEM_PROMPT, SYSTEM_PROMPT
from aws_telegram_bot.application.conversation_service.workflow.state import TelegramAgentState
from aws_telegram_bot.application.conversation_service.workflow.tools import get_retriever_tool


openai_client = get_openai_client()
elevenlabs_client = get_elevenlabs_client()

class RouterResponse(BaseModel):
    response_type: str = Field(description="The response type to give to the user. It must be one of: 'text' or 'audio")

def router_node(state: TelegramAgentState):
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)

    sys_msg = SystemMessage(content=ROUTER_SYSTEM_PROMPT.prompt)
    llm_structured = llm.with_structured_output(RouterResponse)

    response = llm_structured.invoke([sys_msg, state["messages"][-1]])

    if response.response_type == "text":
        if random.random() > 0.5:
            # This way gives more realism to the bot.
            # From time to time the Agent will send voice notes even if the type == "text"
            return {"response_type": "audio"}

    return {"response_type": response.response_type}

def generate_text_response_node(state: TelegramAgentState):
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)
    llm_with_tools = llm.bind_tools([get_retriever_tool()])

    summary = state.get("summary", "")

    if summary:
        system_message = f"{SYSTEM_PROMPT.prompt} \n Summary of conversation earlier: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = [SystemMessage(content=SYSTEM_PROMPT.prompt) + state["messages"]]

    response = llm_with_tools.invoke(messages)

    return {"messages": response}

def summarize_conversation_node(state: TelegramAgentState):
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)

    summary = state.get("summary", "")

    if summary:
        summary_messages = f"This is summary of the conversation to date: {summary}\n\nExtend the summary by taking into account the new messages above:"
    else:
        summary_messages = "Create a summary of the conversation above:"

    messages = state["messages"] + [HumanMessage(content=summary_messages)]
    response = llm.invoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    
    return {"summary": response.content, "messages": delete_messages}


def generate_final_response_node(state: TelegramAgentState):
    if state["response_type"] == "audio":
        audio = elevenlabs_client.text_to_speech.convert(
            text=state["messages"][-1].content,
            voice_id=settings.ELEVENLABS_VOICE_ID,
            model_id=settings.ELEVENLABS_MODEL_ID
        )

        audio_bytes = b"".join(audio)

        return {"audio_buffer": audio_bytes}
    else:
        return state