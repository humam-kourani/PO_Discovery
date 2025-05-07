from collections import defaultdict
from src.objects import Graph, LOOP, ActivityInstance, XOR, Skip


def find_self_loops(mapping, new_nodes_counter):
    new_mapping = {}
    reversed_mapping = defaultdict(set)

    for key, value in mapping.items():
        reversed_mapping[value].add(key)

    skips = {skip for skip in reversed_mapping.keys() if isinstance(skip, Skip)}

    processed_keys = set()

    for skip in skips:
        skip_element = skip.element

        if skip_element in reversed_mapping.keys():
            new_node = LOOP(body=skip_element, redo=ActivityInstance(label=None, number=1))
            value_1 = reversed_mapping[skip_element]
            value_2 = reversed_mapping[skip]
            for node in value_1 | value_2:
                new_mapping[node] = new_node
            processed_keys.update({skip, skip_element})

    for key, value in reversed_mapping.items():
        if key in processed_keys:
            continue
        print(value)
        if new_nodes_counter[key] > 1:
            if isinstance(key, Skip):
                new_node = LOOP(body=ActivityInstance(label=None, number=1), redo=key.element)
            else:
                new_node = LOOP(body=key, redo=ActivityInstance(label=None, number=1))
            # if isinstance(key, XOR):
            #     for child in key.children:
            #         if isinstance(child, ActivityInstance) and not child.label:
            #             rest_children = [c for c in key.children if c != child]
            #             if len(rest_children) > 1:
            #                 redo = XOR(frozenset(rest_children))
            #             else:
            #                 redo = rest_children[0]
            #             new_node = LOOP(body=ActivityInstance(label=None, number=1), redo=redo)
            #             loop_keys[redo] = new_node
            #             break
            # else:

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


def apply_node_mapping(graphs, node_mapping: dict, new_nodes_counter: dict):
    node_mapping = find_self_loops(node_mapping, new_nodes_counter)
    return [apply_node_mapping_on_single_graph(g, node_mapping) for g in graphs]
