from src.services_registry.services import init_services, get

init_services()

web_browser_tool = get("web_browser_tool")
rag_tool = get("rag")

if __name__ == "__main__":
    result_1 = web_browser_tool._run(
        query="what are the recommended steps ton configure a nginx server in kubernetes?",
    )
    result_2 = rag_tool._run(
        query="what are the recommended steps ton configure a nginx server in kubernetes?",
        collection="kubernetes_fundamentals",
    )

    print("\n\n\n")
    print(10*"#" + "web browser tool" + 10*"#")
    print("\n\n\n")
    print(result_1)
    print("\n\n\n")
    print(10*"#" + "rag tool" + 10*"#")
    print("\n\n\n")
    print(result_2)
