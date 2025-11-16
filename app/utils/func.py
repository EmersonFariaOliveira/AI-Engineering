import json
from langchain_core.messages import convert_to_messages

def _pretty_print_message(message, indent=False):
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)

def _pretty_print_messages(update, last_message=False):
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:")
        print("\n")
        is_subgraph = True

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

def _load_cloud_gpu_data(json_path) -> list[dict]:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)