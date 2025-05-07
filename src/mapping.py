from collections import defaultdict
from src.objects import Graph, Skip, SelfLoop, SkipSelfLoop


def find_self_loops(mapping, new_nodes_counter):
    new_mapping = {}
    reversed_mapping = defaultdict(set)

    for key, value in mapping.items():
        reversed_mapping[value].add(key)

    # skips = set()
    # self_loops = set()
    # skip_self_loops = set()
    tagged_node_element_map = defaultdict(list)

    for node in reversed_mapping.keys():
        if isinstance(node, Skip):
            pass
            # skips.add(node)
        elif isinstance(node, SelfLoop):
            pass
            # self_loops.add(node)
        elif isinstance(node, SkipSelfLoop):
            pass
            # skip_self_loops.add(node)
        else:
            continue
        tagged_node_element_map[node.element].append(node)

    # tagged_nodes = skips | self_loops | skip_self_loops

    processed_keys = set()
    print(f"reversed_mapping: {reversed_mapping}")

    for tagged_node_element in tagged_node_element_map.keys():

        element_list = tagged_node_element_map[tagged_node_element]

        if tagged_node_element in reversed_mapping.keys():
            new_node = SelfLoop(tagged_node_element)
            values = reversed_mapping[tagged_node_element]
            processed_keys.add(tagged_node_element)
            for tagged_node in element_list:
                values.update(reversed_mapping[tagged_node])
                processed_keys.add(tagged_node)
            for node in values:
                new_mapping[node] = new_node

        elif len(element_list) > 1:
            if any(isinstance(tagged_node, SelfLoop) for tagged_node in element_list):
                new_node = SelfLoop(tagged_node_element)
            else:
                new_node = SkipSelfLoop(tagged_node_element)

            values = set()
            for tagged_node in element_list:
                values.update(reversed_mapping[tagged_node])
                processed_keys.add(tagged_node)

            for node in values:
                new_mapping[node] = new_node

    for key, value in reversed_mapping.items():
        if key in processed_keys:
            continue
        if new_nodes_counter[key] > 1:
            if isinstance(key, Skip):
                new_node = SkipSelfLoop(key.element)
            else:
                new_node = SelfLoop(key)
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
