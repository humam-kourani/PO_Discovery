from collections import defaultdict
from src.objects import Graph, LOOP, ActivityInstance, XOR


def find_self_loops(mapping):
    new_mapping = {}
    reversed_mapping = defaultdict(set)

    for key, value in mapping.items():
        normalized_node = value.normalize()
        # node_mapping[node] = normalized_node
        reversed_mapping[normalized_node].add(key)

    # print(f"len new nodes: {len(reversed_mapping.keys())}")
    #
    # print("reversed_mapping: ", reversed_mapping)
    for key, value in reversed_mapping.items():
        if len(value) > 1:
            new_node = None
            if isinstance(key, XOR):
                for child in key.children:
                    if isinstance(child, ActivityInstance) and not child.label:
                        rest_children = [c for c in key.children if c != child]
                        if len(rest_children) > 1:
                            redo = XOR(frozenset(rest_children))
                        else:
                            redo = rest_children[0]
                        new_node = LOOP(body=ActivityInstance(label=None, number=1), redo=redo)
                        break
            if not new_node:
                new_node = LOOP(body=key, redo=ActivityInstance(label=None, number=1))
        else:
            new_node = key
        for node in value:
            new_mapping[node] = new_node

    return new_mapping


def apply_node_mapping_on_single_graph(graph: Graph, node_mapping: dict):

    reverse_mapping = defaultdict(set)
    for n in graph.nodes:
        if n in node_mapping:
            value = node_mapping[n]
            reverse_mapping[value].add(n)
        else:
            raise ValueError

    new_nodes = frozenset(node_mapping.values())
    new_edges = set()

    for source in new_nodes:
        for target in new_nodes:
            if source != target and all(
                    (s, t) in graph.edges for s in reverse_mapping[source] for t in reverse_mapping[target]):
                new_edges.add((source, target))
    # filtered_edges = {(s, t) for (s, t) in new_edges if (t, s) not in new_edges}
    return Graph(
        nodes=new_nodes,
        edges=frozenset(new_edges),
        additional_information=graph.additional_information
    )


def apply_node_mapping(graphs, node_mapping: dict):
    node_mapping = find_self_loops(node_mapping)
    return [apply_node_mapping_on_single_graph(g, node_mapping) for g in graphs]
