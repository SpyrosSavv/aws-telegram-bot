from functools import lru_cache
from ipaddress import summarize_address_range
from langchain_core.tools import retriever
from langgraph import graph
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from aws_telegram_bot.application.conversation_service.workflow.edges import should_summarize_conversation
from aws_telegram_bot.application.conversation_service.workflow.nodes import (
    router_node,
    generate_text_response_node,
    summarize_conversation_node,
    generate_final_response_node
)
from aws_telegram_bot.application.conversation_service.workflow.state import TelegramAgentState
from aws_telegram_bot.application.conversation_service.workflow.tools import get_retrieval_tool

retriever_tool = get_retrieval_tool()

@lru_cache(maxsize=1)
def create_workflow_graph():
    graph_builder = StateGraph(TelegramAgentState)

    graph_builder.add_node("router_node", router_node)
    graph_builder.add_node("generate_text_response_node", generate_text_response_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    graph_builder.add_node("tools", ToolNode([retriever_tool]))
    graph_builder.add_node("generate_final_response_node", generate_final_response_node)

    graph_builder.add_edge(START, "router_node")
    graph_builder.add_edge("router_node", "generate_text_response_node")
    graph_builder.add_conditional_edges("generate_text_response_node", tools_condition, {"tools": "tools", END: "generate_final_response_node"})
    graph_builder.add_edge("tools", "generate_text_response_node")
    graph_builder.add_conditional_edges("generate_final_response_node", should_summarize_conversation)

    graph_builder.add_edge("summarize_conversation_node", END)

    return graph_builder