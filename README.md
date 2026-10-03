# ✈️ PlanMyTrip AI

A full-stack, multi-agent generative AI travel planner. Describe a trip in plain English, and four specialised agents search flights, find hotels, build a day-by-day itinerary and write a complete travel plan, streamed live to the UI.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-F55036)

![Home page with agent pipeline](docs/screenshots/01-home-pipeline.png)

## Features

- **Multi-agent workflow**: Flight, Hotel, Itinerary and Final agents orchestrated with LangGraph
- **Live progress**: each agent's status updates in the sidebar as it finishes (streamed from the backend)
- **Tool use**: Tavily web search for hotels and a flight search tool
- **REST API backend**: FastAPI with normal and streaming endpoints
- **Persistent state**: PostgreSQL checkpointing, so every trip is saved by `thread_id`
- **Downloadable plan**: export the final plan as Markdown

## Architecture

```mermaid
flowchart LR
    A[Streamlit UI] -->|HTTP / NDJSON stream| B[FastAPI backend]
    B --> C[LangGraph workflow]
    C --> D[Flight Agent]
    D --> E[Hotel Agent]
    E --> F[Itinerary Agent]
    F --> G[Final Agent]
    D -.-> H[(Flight search tool)]
    E -.-> I[(Tavily search)]
    F -.-> J[Groq LLM]
    G -.-> J
    C <--> K[(PostgreSQL checkpoints)]
```

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI, Uvicorn |
| Agent orchestration | LangGraph |
| LLM | Groq (`openai/gpt-oss-120b`) |
| Tools | Tavily Search, flight search tool |
| Database | PostgreSQL (LangGraph `PostgresSaver`) |

## Screenshots

**Complete plan with budget breakdown**

![Final plan](docs/screenshots/02-final-plan.png)

**Flight and hotel recommendations**

![Flights and hotels](docs/screenshots/03-flights-hotels.png)

**Practical tips and downloadable plan**

![Tips and download](docs/screenshots/04-tips-download.png)

## Project structure

```
PlanMyTrip-AI/
├── app.py              # Streamlit frontend
├── api.py              # FastAPI backend (REST + streaming endpoints)
├── main.py             # LangGraph workflow, agents and PostgreSQL checkpointer
├── tools/
│   ├── flight_tool.py  # Flight search tool
│   └── tavily_tool.py  # Tavily hotel/web search tool
├── docs/screenshots/   # README images
├── requirements.txt
├── .env.example
└── README.md
```

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/plan-trip` | Plan a trip and return the full result |
| POST | `/plan-trip/stream` | Plan a trip and stream each agent's result as it finishes |
| GET | `/trips/{thread_id}` | Load a saved trip from PostgreSQL |

Interactive docs are available at `http://localhost:8000/docs` when the backend is running.

## Getting started

### Prerequisites

- Python 3.10 or newer
- A running PostgreSQL database
- API keys for [Groq](https://console.groq.com) and [Tavily](https://tavily.com)

### 1. Clone and install

```bash
git clone https://github.com/AbhijitRoy893/PlanMyTrip-AI.git
cd PlanMyTrip-AI
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

### 3. Run the backend

```bash
python -m uvicorn api:api
```

### 4. Run the frontend (in a second terminal)

```bash
source venv/bin/activate
python -m streamlit run app.py
```

Open `http://localhost:8501` and describe your trip, for example:

> Plan a 5 days Goa trip from Kolkata for 2 people, travelling on 15 November 2026, budget ₹40,000 including flights, hotels and sightseeing.

## How it works

1. The user's request goes from Streamlit to the FastAPI `/plan-trip/stream` endpoint.
2. LangGraph runs four nodes in order, sharing one `TravelState` (flight results, hotel results, itinerary, messages).
3. Each node's output is streamed back as soon as it finishes, which drives the live progress in the UI.
4. LangGraph saves the state to PostgreSQL after every step, so a trip can be reloaded by its `thread_id`.

## Known limitations

- The agents run as a fixed pipeline (flights → hotels → itinerary → final), not as fully autonomous tool-choosing agents.
- Flight search quality depends on the flight tool; results can be irrelevant to the requested route.
- Budget totals are written by the LLM, so they can be off by a small amount.
- No user login yet: the User ID is typed manually and used as the `thread_id`.

## Roadmap

- [ ] Improve flight search accuracy (parse origin, destination and date from the request)
- [ ] Calculate budget totals in code instead of the LLM
- [ ] User accounts and a "My Trips" page
- [ ] Follow-up requests such as "make it cheaper"
- [ ] Docker setup and cloud deployment

## Author

**Abhijit Roy**: [GitHub](https://github.com/AbhijitRoy893)
