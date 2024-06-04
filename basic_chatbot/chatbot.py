from typing import Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.sqlite import SqliteSaver


class State(TypedDict):
    messages: Annotated[list, add_messages]


llm = ChatOpenAI(model="gpt-3.5-turbo")
tool = TavilySearchResults(max_results=2)
tools = [tool]
llm_with_tools = llm.bind_tools(tools)


# Build a Basic Chatbot
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


def execute():
    memory = SqliteSaver.from_conn_string(":memory:")
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    # Enhancing the Chatbot with Tools
    tool_node = ToolNode(tools=[tool])
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")

    graph_builder.set_entry_point("chatbot")
    graph_builder.set_finish_point("chatbot")

    # Adding Memory to the Chatbot
    graph = graph_builder.compile(
        checkpointer=memory,
        # LangGraph supports 'human-in-the-loop' workflows in a number of ways. In this section, we will use
        # LangGraph's 'interrupt_before' functionality to always break the tool node.
        interrupt_after=["tools"],
    )

    # you can interact with your bot! First, pick a thread to use as the key for this conversation.
    config = {"configurable": {"thread_id": "1"}}

    while True:
        user_input = input("User:")
        if user_input.lower() in ["q", "quit", "exit"]:
            print("GoodBye !!")
            break
        for event in graph.stream(
            {"messages": ("user", user_input)}, config, stream_mode="values"
        ):
            # for value in event.values():
            #     if len(value["messages"][-1].content) > 0:
            #         print("Assistant: ", value["messages"][-1].content)
            event["messages"][-1].pretty_print()
