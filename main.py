import operator
import os
from typing import TypedDict, Annotated

import psycopg
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from langchain_groq import ChatGroq

from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# Initialize Groq LLM
llm = ChatGroq(
    model="openai/gpt-oss-120b"
)


# PostgreSQL database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")


# --------------------------------------------------
# Travel State
# --------------------------------------------------

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int


# --------------------------------------------------
# Flight Agent
# --------------------------------------------------

def flight_agent(state: TravelState):

    query = state["user_query"]

    flight_data = search_flights(query)

    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(content="Flight results fetched")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# --------------------------------------------------
# Hotel Agent
# --------------------------------------------------

def hotel_agent(state: TravelState):

    query = f"Best hotels for {state['user_query']}"

    hotel_results = tavily_search(query)

    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(content="Hotel information fetched")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# --------------------------------------------------
# Itinerary Agent
# --------------------------------------------------

def itinerary_agent(state: TravelState):

    prompt = f"""
Create a travel itinerary.

User Query:
{state['user_query']}

Flight Results:
{state['flight_results']}

Hotel Results:
{state['hotel_results']}
"""

    response = llm.invoke([
        SystemMessage(
            content="You are an expert travel planner."
        ),
        HumanMessage(content=prompt)
    ])

    return {
        "itinerary": response.content,
        "messages": [
            response
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# --------------------------------------------------
# Final Agent
# --------------------------------------------------

def final_agent(state: TravelState):

    final_prompt = f"""
Generate the final travel response.

User Query:
{state['user_query']}

Flights:
{state['flight_results']}

Hotels:
{state['hotel_results']}

Itinerary:
{state['itinerary']}
"""

    response = llm.invoke([
        SystemMessage(
            content="You are a helpful travel assistant."
        ),
        HumanMessage(content=final_prompt)
    ])

    return {
        "messages": [
            response
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# --------------------------------------------------
# Create Graph
# --------------------------------------------------

graph = StateGraph(TravelState)


# Add nodes
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)


# --------------------------------------------------
# Define Workflow
# --------------------------------------------------

graph.add_edge(START, "flight_agent")

graph.add_edge(
    "flight_agent",
    "hotel_agent"
)

graph.add_edge(
    "hotel_agent",
    "itinerary_agent"
)

graph.add_edge(
    "itinerary_agent",
    "final_agent"
)

graph.add_edge(
    "final_agent",
    END
)


# --------------------------------------------------
# PostgreSQL Checkpointer
# --------------------------------------------------

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True
)

checkpointer = PostgresSaver(_conn)

checkpointer.setup()


# --------------------------------------------------
# Compile Graph
# --------------------------------------------------

app = graph.compile(
    checkpointer=checkpointer
)


# --------------------------------------------------
# Run Application
# --------------------------------------------------

if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": "user_abhijit"
        }
    }

    user_input = input(
        "Enter travel request: "
    )

    result = app.invoke(
        {
            "messages": [
                HumanMessage(
                    content=user_input
                )
            ],

            "user_query": user_input,

            "flight_results": "",

            "hotel_results": "",

            "itinerary": "",

            "llm_calls": 0
        },

        config=config
    )

    print("\nFinal Response:")
    print(
        result["messages"][-1].content
    )