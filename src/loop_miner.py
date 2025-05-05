from collections import defaultdict, deque
from src.objects import LOOP, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY


MULTIPLE_LOOPS = True


class LoopMiner:
    @classmethod
    def find_loops(cls, graph: Graph):
        # 1) Collect all ActivityInstance nodes by label
        label_to_instances = defaultdict(list)
        for node in graph.nodes:
            if isinstance(node, ActivityInstance) and node.label:
                label_to_instances[node.label].append(node)

        # 2) Build adjacency for reachability
        succ = defaultdict(set)
        pred = defaultdict(set)
        for s, t in graph.edges:
            succ[s].add(t)
            pred[t].add(s)

        # 3) Calculate number of predecessors ("distance to start") for each label
        label_predecessors_count = {}
        for label, insts in label_to_instances.items():
            all_preds = set()
            for inst in insts:
                dq = deque([inst])
                visited = set()
                while dq:
                    u = dq.popleft()
                    for p in pred[u]:
                        if p not in visited:
                            visited.add(p)
                            dq.append(p)
                all_preds.update(visited)
            label_predecessors_count[label] = len(all_preds)
        #
        # # 4) Sort labels by predecessor count (closer to start first)
        ordered_labels = sorted(label_to_instances.keys(), key=lambda l: label_predecessors_count[l], reverse=True)


        mapping = {}
        processed_nodes = set()
        loops = set()
        loops_frequencies = defaultdict(int)
        loop_groups = []

        # 5) Process labels in order
        for label in ordered_labels:

            insts = label_to_instances[label]

            if len(insts) < 2:
                continue

            insts_sorted = sorted(insts, key=lambda x: x.number)

            for i in range(len(insts) - 1):

                # sort instances

                first, last = insts_sorted[i], insts_sorted[i+1]

                if MULTIPLE_LOOPS:
                    if first in processed_nodes:
                        continue

                # reachable from first
                reach = set()
                dq = deque([first])
                while dq:
                    u = dq.popleft()
                    for v in succ[u]:
                        if v not in reach:
                            reach.add(v)
                            dq.append(v)

                # ancestors of last
                anc = set()
                dq = deque([last])
                while dq:
                    u = dq.popleft()
                    for p in pred[u]:
                        if p not in anc:
                            anc.add(p)
                            dq.append(p)

                # do-set = intersection + include the boundary instances
                do_set = (reach & anc) | {first}

                new_label_group = {n.label for n in do_set}
                loop_groups.append(new_label_group)

                if MULTIPLE_LOOPS:

                    # new_nodes_map = {n: ActivityInstance(n.label, 1) for n in do_set}

                    if len(do_set) == 1:
                        do_part = list(do_set)[0]
                    else:
                        new_edges = {(s, t) for (s, t) in graph.edges if
                                     s in do_set and t in do_set}
                        do_part = Graph(
                            nodes=frozenset(do_set),
                            edges=frozenset(new_edges),
                            # additional_information={VARIANT_FREQUENCY_KEY:
                            #                             graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
                        )
                    loop_node = LOOP(body=do_part, redo=ActivityInstance(None, 1))

                    print("created loop node:", loop_node)

                    found = False
                    for other_loop in loops:
                        other_do = other_loop.body
                        if isinstance(do_part, ActivityInstance):
                            if isinstance(other_do, ActivityInstance) and other_do.label == do_part.label:
                                found = True
                                loop_node = other_loop
                        elif isinstance(do_part, Graph):
                            if isinstance(other_do, Graph):
                                other_labels = {n.label for n in other_do.nodes}
                                other_edges = {(s.label, t.label) for (s, t) in other_do.edges}
                                new_edges_labels = {(s.label, t.label) for (s, t) in new_edges}
                                if other_labels == new_label_group and other_edges == new_edges_labels:
                                    found = True
                                    loop_node = other_loop

                    if not found:
                        loops.add(loop_node)

                    loops_frequencies[loop_node] += 1

                    for n in do_set:
                        processed_nodes.add(n)
                        mapping[n] = loop_node
                        print(f"mapped loop node {n} to {loop_node}")
                    if len(do_set) == 1:
                        mapping[last] = loop_node
        if not MULTIPLE_LOOPS:
            print(f"Loop labels: {loop_groups}")
            merged = []
            for label_group in loop_groups:
                placed = False
                for m in merged:
                    if m & label_group:
                        m |= label_group
                        placed = True
                        break
                if not placed:
                    merged.append(set(label_group))
            print(f"Loop labels merged: {merged}")
            changed = True
            while changed:
                changed = False
                new_merged = []
                while merged:
                    grp = merged.pop()
                    for other in merged:
                        if grp & other:
                            merged.remove(other)
                            grp |= other
                            changed = True
                            break
                    new_merged.append(grp)
                merged = new_merged
            print(f"Loop labels merged new: {merged}")

            # 5) build one LOOP per merged group
            mapping = {}
            for group in merged:
                new_nodes = {ActivityInstance(n, 1) for n in group}

                # for source in new_nodes:
                #     for target in new_nodes:
                #         if source != target and all(
                #                 (s, t) in graph.edges for s in reverse_mapping[source] for t in reverse_mapping[target]):
                #             new_edges.add((source, target))

                # sub-graph for the do-part
                # sub_edges = {
                #     (s, t)
                #     for (s, t) in graph.edges
                #     if s in group and t in group
                # }


                if len(new_nodes) == 1:
                    do_part = new_nodes.pop()
                else:
                    do_part = Graph(
                        nodes=frozenset(new_nodes),
                        edges=frozenset([]),
                        # additional_information={VARIANT_FREQUENCY_KEY:
                        #                             graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
                    )
                loop_node = LOOP(body=do_part, redo=ActivityInstance(None, 1))
                # map every node in the group to this loop
                for n in group:
                    mapping[n] = loop_node

            # # Build redo submodel
            # if len(redo_nodes) == 1:
            #     redo = next(iter(redo_nodes))
            # elif len(redo_nodes) > 1:
            #     redo = Graph(
            #         nodes=frozenset(redo_nodes),
            #         edges=frozenset((s, t) for s, t in graph.edges if s in redo_nodes and t in redo_nodes),
            #         additional_information={VARIANT_FREQUENCY_KEY: graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
            #     )
            # else:
            #     redo = ActivityInstance(None, 1)
            #
            # body = first
            # loop_node = LOOP(body=body, redo=redo)
            #
            # # map loop activities
            # for inst in insts:
            #     mapping[label] = loop_node
            #     already_in_loop.add(inst)
            #
            # # map redo nodes also
            # if isinstance(redo, Graph):
            #     for redo_node in redo.nodes:
            #         mapping[redo_node.label] = loop_node
            #         already_in_loop.add(redo_node)
            # elif isinstance(redo, ActivityInstance):
            #     mapping[redo.label] = loop_node
            #     already_in_loop.add(redo)

        # 6) Identity mapping for the rest
        # for n in graph.nodes:
        #     if n not in mapping:
        #         mapping[n] = n

        return mapping, loops_frequencies

    @classmethod
    def apply_mapping(cls, graph: Graph, input_mapping: dict, loops_frequencies: {}):

        if MULTIPLE_LOOPS:
            node_mapping = input_mapping
            reverse_mapping = defaultdict(set)
            for n in graph.nodes:
                if n in node_mapping.keys():
                    new_node = node_mapping[n]
                    if isinstance(new_node, LOOP):
                        body = new_node.body
                        freq = loops_frequencies[new_node]
                        if isinstance(body, Graph):
                            body_loop_mapping, body_loops_frequencies = LoopMiner.find_loops(body)
                            body = LoopMiner.apply_mapping(body, body_loop_mapping, body_loops_frequencies)
                        if freq < 2:
                             new_node = body
                        else:
                             new_node.body = body
                        node_mapping[n] = new_node
                    reverse_mapping[node_mapping[n]].add(n)
                else:
                    node_mapping[n] = n
                    reverse_mapping[n].add(n)
            new_nodes = frozenset(node_mapping.values())

        else:
            label_mapping = input_mapping

            mapping = defaultdict(set)
            reverse_mapping = defaultdict(set)
            for n in graph.nodes:
                if isinstance(n, ActivityInstance) and n.label in label_mapping:
                    new_node = label_mapping[n.label]
                    mapping[n] = new_node
                    reverse_mapping[new_node].add(n)
                else:
                    mapping[n] = n
                    reverse_mapping[n].add(n)

            new_nodes = frozenset(mapping.values())

        new_edges = set()

        for source in new_nodes:
            for target in new_nodes:
                if source != target and all((s, t) in graph.edges for s in reverse_mapping[source] for t in reverse_mapping[target]):
                    new_edges.add((source, target))
        # for s, t in graph.edges:
        #     source = mapping[s]
        #     target = mapping[t]
        #     if source != target:
        #         new_edges.add((source, target))
        filtered_edges = {(s, t) for (s, t) in new_edges if (t, s) not in new_edges}
        return Graph(
            nodes=new_nodes,
            edges=frozenset(filtered_edges),
            additional_information={VARIANT_FREQUENCY_KEY: graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
        )
