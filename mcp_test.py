from crewai_tools import MCPServerAdapter
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
load_dotenv(override=True)

server_params = {"url": "http://127.0.0.1:9000/fs/sse"}

with MCPServerAdapter(server_params) as tools:
    print(f"Available tools from SSE MCP server: {[tool.name for tool in tools]}")

    # Example: Using the tools from the SSE MCP server in a CrewAI Agent
    agent = Agent(
        role="Writer",
        goal="Write a file.",
        backstory="An AI that can write files.",
        tools=tools,
        verbose=True,
    )
    task = Task(
        description="Write a file about kubernetes.",
        expected_output="File written.",
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )
    result = crew.kickoff()
    print(result)