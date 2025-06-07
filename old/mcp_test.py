from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

# Define the server parameters
server_params = StdioServerParameters(
    command="docker",
    args=[
        "run", "--rm", "-i",
        "-v", "D:\\Python\\MasterIA\\TFM\\TFM\\TFM\\temp:/projects",
        "ghcr.io/mark3labs/mcp-filesystem-server:latest",
        "/projects"
    ],
)

# Use the MCPServerAdapter to connect to the MCP server
with MCPServerAdapter(server_params) as tools:
    print(f"Available tools: {[tool.name for tool in tools]}")

    # # Define an agent with access to the MCP tools
    # agent = Agent(
    #     role="File Manager",
    #     goal="Manage and interact with the local filesystem.",
    #     backstory="An AI agent capable of reading, writing, and organizing files.",
    #     tools=tools,
    #     verbose=True,
    # )

    # # Define a task for the agent
    # task = Task(
    #     description="List all files in the specified directory.",
    #     expected_output="A list of filenames in the directory.",
    #     agent=agent,
    # )

    # # Create a crew to execute the task
    # crew = Crew(
    #     agents=[agent],
    #     tasks=[task],
    #     verbose=True,
    # )

    # # Execute the task
    # result = crew.kickoff()
    # print(result)
