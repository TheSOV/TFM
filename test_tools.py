from src.crewai.tools.web_browser_tool import WebBrowserTool

from src.services_registry.services import init_services, get

init_services()

brave_search_tool = get("brave_search")

if __name__ == "__main__":
    tool = WebBrowserTool(brave_search_tool)
    result = tool._run(
        query="what are the recommended steps ton configure a nginx server in kubernetes?",
    )
    print(result)
