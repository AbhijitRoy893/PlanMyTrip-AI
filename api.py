import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from main import app as travel_graph   # your compiled LangGraph

api = FastAPI(title="PlanMyTrip AI")


class TripRequest(BaseModel):
    query: str
    thread_id: str | None = None   # omit to start a new trip


def build_payload(query: str) -> dict:
    return {
        "messages": [HumanMessage(content=query)],
        "user_query": query,
        "flight_results": "",
        "hotel_results": "",
        "itinerary": "",
        "llm_calls": 0,
    }


@api.get("/health")
def health():
    return {"status": "ok"}


@api.post("/plan-trip")
def plan_trip(req: TripRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = travel_graph.invoke(build_payload(req.query), config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "thread_id": thread_id,
        "reply": result["messages"][-1].content,
        "flights": result["flight_results"],
        "hotels": result["hotel_results"],
        "itinerary": result["itinerary"],
    }


@api.post("/plan-trip/stream")
def plan_trip_stream(req: TripRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    payload = build_payload(req.query)

    def event_stream():
        try:
            for update in travel_graph.stream(payload, config=config, stream_mode="updates"):
                for node, data in update.items():
                    data = data or {}
                    event = {"node": node}
                    for key in ("flight_results", "hotel_results", "itinerary", "llm_calls"):
                        if key in data:
                            event[key] = data[key]
                    if node == "final_agent" and data.get("messages"):
                        event["final"] = data["messages"][-1].content
                    yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@api.get("/trips/{thread_id}")
def get_trip(thread_id: str):
    """Reload a saved trip from the Postgres checkpoint."""
    config = {"configurable": {"thread_id": thread_id}}
    state = travel_graph.get_state(config).values
    if not state:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {
        "thread_id": thread_id,
        "query": state.get("user_query"),
        "flights": state.get("flight_results"),
        "hotels": state.get("hotel_results"),
        "itinerary": state.get("itinerary"),
        "reply": state["messages"][-1].content,
    }