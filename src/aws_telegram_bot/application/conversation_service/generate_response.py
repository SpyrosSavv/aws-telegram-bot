from langgraph.checkpoint.mongodb import MongoDBSaver
from opik.integrations.adk import opik_tracer
from opik.integrations.langchain import OpikTracer

from aws_telegram_bot.application.conversation_service.workflow.graph import create_workflow_graph
from aws_telegram_bot.infrastructure.clients.mongodb import get_mongodb_client

def get_agent_response(payload: dict, user_id: int):
    checkpointer = MongoDBSaver(get_mongodb_client())

    graph = create_workflow_graph().compile(checkpointer=checkpointer)
    opik_tracer = OpikTracer(graph=graph.get_graph(xray=True))

    config = {"configurable": {"thread_id": str(user_id), "callbacks": [opik_tracer]}}

    return graph.invoke(payload, config)