import os
import certifi
from dotenv import load_dotenv

# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


# ============================================================
# IMPORTS
# ============================================================

from typing import TypedDict, Annotated

import operator
import uuid
import asyncio

import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from langchain_groq import ChatGroq

from mcp_client import (
    tavily_mcp_search,
    aviation_mcp_call,
    extract_destination,
    forecast_mcp_search,
    weather_mcp_search,
)


# ============================================================
# DATABASE
# ============================================================

def get_database_url():

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. "
            "Please add DATABASE_URL to your .env file."
        )

    if "sslmode=" not in database_url:

        separator = "&" if "?" in database_url else "?"

        database_url = (
            f"{database_url}{separator}sslmode=require"
        )

    return database_url


# ============================================================
# GROQ
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:

    raise ValueError(
        "GROQ_API_KEY is missing. "
        "Please add it to your .env file."
    )


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY
)


# ============================================================
# HELPER
# ============================================================

def limit_text(value, max_chars):

    if value is None:
        return ""

    text = str(value)

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n...[truncated]"


# ============================================================
# TRAVEL STATE
# ============================================================

class TravelState(TypedDict):

    messages: Annotated[
        list[AnyMessage],
        operator.add
    ]

    user_query: str

    flight_results: str

    hotel_results: str

    itinerary: str

    llm_calls: int

    weather_results: str


# ============================================================
# FLIGHT AGENT
# ============================================================

FLIGHT_AGENT_PROMPT = """
You are an expert travel flight assistant.

User request:

{query}

Airport information:

{airport_data}

Airline information:

{airline_data}

Provide useful flight information.

Include:

- Departure airport
- Arrival airport
- Airlines
- Flight duration
- Flight number if available
- Departure time if available
- Arrival time if available
- Price only if actually available from the data

IMPORTANT:

Do not invent flight numbers.

Do not invent departure times.

Do not invent arrival times.

Do not invent live prices.

If information is unavailable, clearly say:
"Not available."

Keep the response concise.
"""


def flight_agent(state: TravelState):

    print("\nINSIDE FLIGHT AGENT\n")

    query = state["user_query"]

    try:

        # ====================================================
        # AIRPORTS
        # ====================================================

        airports = asyncio.run(
            aviation_mcp_call(
                "list_airports"
            )
        )

        # ====================================================
        # AIRLINES
        # ====================================================

        airlines = asyncio.run(
            aviation_mcp_call(
                "list_airlines"
            )
        )

        print("\nAIRPORTS:", airports)

        print("\nAIRLINES:", airlines)

        # ====================================================
        # PROMPT
        # ====================================================

        prompt = FLIGHT_AGENT_PROMPT.format(

            query=limit_text(
                query,
                1000
            ),

            airport_data=limit_text(
                airports,
                1500
            ),

            airline_data=limit_text(
                airlines,
                1500
            )
        )

        # ====================================================
        # LLM
        # ====================================================

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are an expert travel flight "
                        "planning assistant."
                    )
                ),

                HumanMessage(
                    content=prompt
                )
            ]
        )

        flight_data = response.content

    except Exception as e:

        print(
            "Flight agent error:",
            e
        )

        flight_data = (
            "Flight information unavailable.\n"
            f"Reason: {str(e)}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "flight_results": flight_data,

        "messages": [
            AIMessage(
                content="Flight information generated."
            )
        ],

        "llm_calls":
            state.get(
                "llm_calls",
                0
            ) + 1
    }


# ============================================================
# HOTEL AGENT
# ============================================================

def hotel_agent(state: TravelState):

    print("\nINSIDE HOTEL AGENT\n")

    query = f"""
Find useful hotel information for this trip:

{state["user_query"]}

Provide:

- Hotel name
- Location
- Approximate price range if available
- Rating if available
- Important amenities
- Booking information

Do not invent information.
"""

    try:

        hotel_results = asyncio.run(
            tavily_mcp_search(
                query
            )
        )

        hotel_results = limit_text(
            hotel_results,
            3500
        )

    except Exception as e:

        print(
            "Hotel agent error:",
            e
        )

        hotel_results = (
            "Hotel information unavailable.\n"
            f"Reason: {str(e)}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "hotel_results": hotel_results,

        "messages": [
            AIMessage(
                content="Hotel information generated."
            )
        ],

        "llm_calls":
            state.get(
                "llm_calls",
                0
            ) + 1
    }


# ============================================================
# WEATHER AGENT
# ============================================================

def weather_agent(state: TravelState):

    print("\nINSIDE WEATHER AGENT\n")

    try:

        # ====================================================
        # DESTINATION
        # ====================================================

        city = extract_destination(
            state["user_query"]
        )

        print(
            "DESTINATION:",
            city
        )

        # ====================================================
        # CURRENT WEATHER
        # ====================================================

        weather_data = asyncio.run(
            weather_mcp_search(
                city
            )
        )

        # ====================================================
        # FORECAST
        # ====================================================

        forecast_data = asyncio.run(
            forecast_mcp_search(
                city
            )
        )

        # ====================================================
        # COMBINE
        # ====================================================

        weather_results = f"""
Current Weather:

{limit_text(
    weather_data,
    1200
)}

Forecast:

{limit_text(
    forecast_data,
    1800
)}
"""

    except Exception as e:

        print(
            "Weather agent error:",
            e
        )

        weather_results = (
            "Weather information unavailable.\n"
            f"Reason: {str(e)}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "weather_results": weather_results,

        "messages": [
            AIMessage(
                content="Weather information generated."
            )
        ],

        "llm_calls":
            state.get(
                "llm_calls",
                0
            ) + 1
    }


# ============================================================
# ITINERARY AGENT
# ============================================================

def itinerary_agent(state: TravelState):

    print("\nINSIDE ITINERARY AGENT\n")

    prompt = f"""
Create a practical travel itinerary.

User Request:

{limit_text(
    state["user_query"],
    1000
)}

Flight Information:

{limit_text(
    state["flight_results"],
    1800
)}

Hotel Information:

{limit_text(
    state["hotel_results"],
    2200
)}

Weather Information:

{limit_text(
    state["weather_results"],
    1500
)}

Create a day-by-day itinerary.

Include:

- Morning activities
- Afternoon activities
- Evening activities
- Local transportation
- Sightseeing
- Practical travel suggestions

Do not invent exact information that is unavailable.

Keep the itinerary concise.
"""

    try:

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are an expert travel itinerary "
                        "planner."
                    )
                ),

                HumanMessage(
                    content=prompt
                )
            ]
        )

        itinerary = response.content

    except Exception as e:

        print(
            "Itinerary agent error:",
            e
        )

        itinerary = (
            "Itinerary information unavailable.\n"
            f"Reason: {str(e)}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "itinerary": itinerary,

        "messages": [
            AIMessage(
                content="Travel itinerary generated."
            )
        ],

        "llm_calls":
            state.get(
                "llm_calls",
                0
            ) + 1
    }


# ============================================================
# FINAL AGENT
# ============================================================

def final_agent(state: TravelState):

    print("\nINSIDE FINAL AGENT\n")

    # ========================================================
    # LIMIT CONTEXT
    # ========================================================

    user_query = limit_text(
        state["user_query"],
        1000
    )

    flight_results = limit_text(
        state["flight_results"],
        1800
    )

    hotel_results = limit_text(
        state["hotel_results"],
        2200
    )

    weather_results = limit_text(
        state["weather_results"],
        1500
    )

    itinerary = limit_text(
        state["itinerary"],
        2500
    )

    # ========================================================
    # FINAL PROMPT
    # ========================================================

    final_prompt = f"""
You are TripMate AI, a professional AI travel planner.

Create a complete and clean travel plan for the user.

The final answer MUST contain these sections:

1. Trip Summary
2. Flight Information
3. Hotel Information
4. Weather Information
5. Day-by-Day Itinerary
6. Estimated Budget
7. Travel Recommendations

============================================================
USER REQUEST
============================================================

{user_query}


============================================================
FLIGHT INFORMATION
============================================================

{flight_results}


============================================================
HOTEL INFORMATION
============================================================

{hotel_results}


============================================================
WEATHER INFORMATION
============================================================

{weather_results}


============================================================
ITINERARY
============================================================

{itinerary}


============================================================
REQUIRED OUTPUT FORMAT
============================================================

# [Trip Name] – [Origin] → [Destination]

## 1. Trip Summary

- **Duration:** [duration]
- **Key cities:** [cities]
- **Transport:** [transport]
- **Accommodation:** [accommodation]
- **Travel period:** [period]


## 2. Flight Information

| Item | Details |
|---|---|
| Departure airport | [airport] |
| Arrival airport | [airport] |
| Airline | [airline] |
| Flight number | [number or Not available] |
| Departure time | [time or Not available] |
| Arrival time | [time or Not available] |
| Duration | [duration or Not available] |


## 3. Hotel Information

Provide useful hotel options.

For each hotel include:

- Hotel name
- Location
- Price range if available
- Rating if available
- Key amenities


## 4. Weather Information

Include:

- Current temperature
- Weather condition
- Humidity if available
- Wind if available
- Short forecast


## 5. Day-by-Day Itinerary

Provide a practical itinerary.

Example:

### Day 1
- Morning:
- Afternoon:
- Evening:

### Day 2
- Morning:
- Afternoon:
- Evening:


## 6. Estimated Budget

Include an approximate breakdown where information is available:

- Flights
- Hotels
- Food
- Local transportation
- Sightseeing
- Other expenses
- Total estimated budget


## 7. Travel Recommendations

Include concise practical recommendations about:

- Best time to visit
- Transportation
- Booking
- Important travel considerations
- General tips


============================================================
IMPORTANT RULES
============================================================

1. Use only information available from the agents and user request.

2. Do not invent live flight prices.

3. Do not invent flight numbers.

4. Do not invent departure times.

5. Do not invent arrival times.

6. If flight information is unavailable, write:
   "Not available."

7. Clearly distinguish approximate information from confirmed
   information.

8. Keep the answer professional and readable.

9. Do not add unnecessary sections outside the seven required
   sections.

10. Use Markdown formatting.
"""

    # ========================================================
    # CALL GROQ
    # ========================================================

    try:

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a professional AI travel "
                        "planning assistant. Create accurate, "
                        "well-structured and concise travel plans."
                    )
                ),

                HumanMessage(
                    content=final_prompt
                )
            ]
        )

        final_response = response

    except Exception as e:

        print(
            "Final agent error:",
            e
        )

        final_response = AIMessage(
            content=(
                "I could not generate the final travel plan "
                f"because of an LLM error: {str(e)}"
            )
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "messages": [
            final_response
        ],

        "llm_calls":
            state.get(
                "llm_calls",
                0
            ) + 1
    }


# ============================================================
# LANGGRAPH
# ============================================================

graph = StateGraph(
    TravelState
)


# ============================================================
# ADD NODES
# ============================================================

graph.add_node(
    "flight_agent",
    flight_agent
)

graph.add_node(
    "hotel_agent",
    hotel_agent
)

graph.add_node(
    "weather_agent",
    weather_agent
)

graph.add_node(
    "itinerary_agent",
    itinerary_agent
)

graph.add_node(
    "final_agent",
    final_agent
)


# ============================================================
# GRAPH FLOW
# ============================================================

graph.add_edge(
    START,
    "flight_agent"
)

graph.add_edge(
    "flight_agent",
    "hotel_agent"
)

graph.add_edge(
    "hotel_agent",
    "weather_agent"
)

graph.add_edge(
    "weather_agent",
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


# ============================================================
# POSTGRESQL CHECKPOINTER
# ============================================================

DATABASE_URL = get_database_url()


_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row
)


checkpointer = PostgresSaver(
    _conn
)


# ============================================================
# DATABASE SETUP
# ============================================================

checkpointer.setup()


# ============================================================
# COMPILE GRAPH
# ============================================================

travel_graph = graph.compile(
    checkpointer=checkpointer
)


# ============================================================
# RUN TRAVEL AGENT
# ============================================================

def run_travel_agent(
    user_input: str,
    thread_id: str | None = None
):

    # ========================================================
    # THREAD ID
    # ========================================================

    if not thread_id:

        thread_id = (
            f"user_{uuid.uuid4().hex}"
        )


    # ========================================================
    # CONFIG
    # ========================================================

    config = {

        "configurable": {

            "thread_id": thread_id

        }

    }


    # ========================================================
    # INITIAL STATE
    # ========================================================

    initial_state = {

        "messages": [

            HumanMessage(
                content=user_input
            )

        ],

        "user_query": user_input,

        "flight_results": "",

        "hotel_results": "",

        "weather_results": "",

        "itinerary": "",

        "llm_calls": 0
    }


    # ========================================================
    # RUN GRAPH
    # ========================================================

    result = travel_graph.invoke(
        initial_state,
        config=config
    )


    # ========================================================
    # FINAL ANSWER
    # ========================================================

    final_answer = (
        result["messages"][-1].content
    )


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "thread_id": thread_id,

        "answer": final_answer,

        "flight_results":
            result.get(
                "flight_results",
                ""
            ),

        "hotel_results":
            result.get(
                "hotel_results",
                ""
            ),

        "weather_results":
            result.get(
                "weather_results",
                ""
            ),

        "itinerary":
            result.get(
                "itinerary",
                ""
            ),

        "llm_calls":
            result.get(
                "llm_calls",
                0
            )

    }