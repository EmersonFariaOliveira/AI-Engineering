from dotenv import load_dotenv
load_dotenv()

from utils.agents.orchestrator_agent.graph import OrchestratorAgent
# from utils.agents.research_agent.graph import ResearchAgent
from utils.func import pretty_print_messages
from utils.func import generate_mermaid

from langchain_core.messages import  HumanMessage

def main():

    print("Starting application...")
    graph = OrchestratorAgent.build_graph()
    # graph = ResearchAgent.build_graph()
    generate_mermaid(graph, "./graph_diagrams/orchestratorflow.mmd")
    # generate_mermaid(graph, "./graph_diagrams/ResearchAgent.mmd")

    # question = {"messages": [HumanMessage(content="Crie um relatorio levantando as principais diferenças entre Azure e AWS em termos de estrategias de scalling?")]}
    question = {"messages": [HumanMessage(content="Monte um relatório que mostre o preço médio de GPUs na AWS, Azure e GCP, e sugira a opção mais barata por hora de uso")]}
    for chunk in graph.stream(question):
        pretty_print_messages(chunk)

if __name__ == "__main__":
    main()