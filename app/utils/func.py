from langchain_core.messages import convert_to_messages


def _pretty_print_message(message, indent=False):
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)


def pretty_print_messages(update, last_message=False):
    is_subgraph = False

    # CASO 1: veio uma lista de mensagens (ex: result["messages"] do ainvoke)
    if isinstance(update, list):
        messages = convert_to_messages(update)

        if last_message:
            messages = messages[-1:]

        print("Update from state (messages list):\n")
        for m in messages:
            _pretty_print_message(m, indent=False)
        print("\n")
        return

    # CASO 2: tuple (ns, update) vindo do graph.stream / astream
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:")
        print("\n")
        is_subgraph = True

    # CASO 3: dict no formato {node_name: node_update}
    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label)
        print("\n")
        
        # Try default key
        if "messages" in node_update:
            raw_messages = node_update["messages"]
        else:
            # Find any key that contains "messages"
            message_key = next(
                (k for k in node_update.keys() if "messages" in k.lower()),
                None
            )

            if not message_key:
                raise KeyError("No messages-like key found in node_update")

            raw_messages = node_update[message_key]

        messages = convert_to_messages(raw_messages)

        if last_message:
            messages = messages[-1:]

        for m in messages:
            _pretty_print_message(m, indent=is_subgraph)
        print("\n")


def generate_mermaid(graph, path_to_save = './flow.mmd'): 
    # Generate the .mmd to render the graph in .png 
    # Once .mmd is generated use the command below to generate the flow: 
    # mmdc -i graph_diagrams/flow.mmd -o graph_diagrams/flow.png 
    dot = graph.get_graph(xray=True).draw_mermaid() 
    with open(path_to_save, "w", encoding="utf-8") as f: 
        f.write(dot)