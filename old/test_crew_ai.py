from crewai import Crew, Agent, Task
from dotenv import load_dotenv
load_dotenv(override=True)

agent = Agent(
    role="Coder",
    goal="Create, edit and validate kubernetes YAML configuration files. You can use only one tool simultaneously.",
    backstory="A specialized agent with expertise in kubernetes YAML configuration files. With years of experience, you are proficient in creating, editing, and validating kubernetes YAML configuration files with the best practices and security standards for production level kubernetes configuration files.",
    reasoning=True,
    llm="gpt-4.1-mini"
)

task = Task(
    name="Create, edit and validate kubernetes YAML configuration files",
    description="Create, edit and validate kubernetes YAML configuration files. You can use only one tool simultaneously.",
    expected_output="A valid kubernetes YAML configuration file.",
    agent=agent
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True,
)

crew.kickoff()