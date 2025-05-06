from collections import defaultdict, deque

from pm4py.objects.powl.obj import SilentTransition

from src.combine_order import combine_orders
from src.objects import LOOP, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY
from src.skip_miner import SkipMiner

LOOP_THRESHOLD = 0.9


def get_inbetween(pred, succ, first, last):
    reach = set()
    dq = deque([first])
    while dq:
        u = dq.popleft()
        for v in succ[u]:
            if v not in reach:
                reach.add(v)
                dq.append(v)

    anc = set()
    dq = deque([last])
    while dq:
        u = dq.popleft()
        for p in pred[u]:
            if p not in anc:
                anc.add(p)
                dq.append(p)

    return reach & anc


def project_on_nodes(graph, proj_nodes):
    new_nodes_map = {}
    label_counter = defaultdict(int)

    for n in sorted(proj_nodes):
        label_counter[n.label] += 1
        new_nodes_map[n] = ActivityInstance(n.label, label_counter[n.label])

    new_edges = {(new_nodes_map[s], new_nodes_map[t]) for (s, t) in graph.edges if
                 s in proj_nodes and t in proj_nodes}
    do_part = Graph(
        nodes=frozenset(new_nodes_map.values()),
        edges=frozenset(new_edges),
        additional_information={VARIANT_FREQUENCY_KEY:
                                    graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
    )
    return do_part


class LoopMinerStartEnd:
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
        t_edges = {(s, t) for (s, m1) in graph.edges for (m2, t) in graph.edges if m1 == m2 and (s, t) in graph.edges}
        reduction = graph.edges - t_edges
        for s, t in reduction:
            succ[s].add(t)
            pred[t].add(s)

        transitive_succ = defaultdict(set)
        transitive_pred = defaultdict(set)
        for s, t in graph.edges:
            transitive_succ[s].add(t)
            transitive_pred[t].add(s)

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
        # ordered_labels = sorted(label_to_instances.keys(), key=lambda l: len(transitive_pred[sorted(label_to_instances[label], key=lambda x: x.number)[0]]), reverse=True)
        sorted_nodes = sorted(graph.nodes, key=lambda l: transitive_pred[l], reverse=False)

        mapping = {}
        processed_nodes = set()
        processed_labels = set()
        loops = set()
        loops_frequencies = defaultdict(int)
        loop_groups = []
        label_group_to_loop_map = defaultdict(set)

        sorted_nodes = {n for n in sorted_nodes if isinstance(n, ActivityInstance)}
        # 5) Process labels in order
        for node in sorted_nodes:
            label = node.label

            insts = label_to_instances[label]

            if len(insts) < 2 or label in processed_labels:
                continue


            current_labels_to_include = set()
            current_nodes_to_include = set()
            current_loop_start_labels = set()
            current_loop_end_labels = set()
            new_label_group = set()

            current_labels_to_include.add(label)
            current_nodes_to_include |= set(insts)
            current_loop_start_labels.add(label)

            insts_sorted = sorted(insts, key=lambda x: x.number)

            for i in range(len(insts) - 1):

                first, last = insts_sorted[i], insts_sorted[i+1]
                inbetween = get_inbetween(pred, succ, first, last)

                direct_anc = pred[last]

                do_set = inbetween | {first}

                new_label_group = {n.label for n in do_set}
                current_labels_to_include.update(new_label_group)
                current_nodes_to_include.update(do_set)
                current_loop_end_labels.update({x.label for x in inbetween & direct_anc})
                if len(inbetween) == 0:
                    current_loop_end_labels.add(first.label)
                processed_labels.update(new_label_group)

            print("current_loop_labels: ", current_labels_to_include)
            print("current_loop_start_nodes: ", current_loop_start_labels)
            print("current_loop_end_nodes: ", current_loop_end_labels)

            n = 0
            while n !=  len(current_loop_end_labels) + len(current_loop_start_labels):
                n = len(current_loop_end_labels) + len(current_loop_start_labels)
                for node_label in current_loop_end_labels:
                    node_insts = label_to_instances[node_label]

                    node_insts_sorted = sorted(node_insts, key=lambda x: x.number)
                    for j in range(len(node_insts_sorted) - 1):

                        first, last = node_insts_sorted[j], node_insts_sorted[j + 1]
                        inbetween = get_inbetween(pred, succ, first, last)

                        direct_succ = succ[first]
                        current_loop_start_labels.update({x.label for x in inbetween & direct_succ})
                        if len(inbetween) == 0:
                            current_loop_start_labels.add(last.label)

                        current_nodes = inbetween | {first, last}
                        new_label_group.update({n.label for n in current_nodes})
                        current_labels_to_include.update(new_label_group)
                        current_nodes_to_include.update(current_nodes)
                        processed_labels.update(new_label_group)
                for node_label in current_loop_start_labels:
                    node_insts = label_to_instances[node_label]

                    node_insts_sorted = sorted(node_insts, key=lambda x: x.number)
                    for j in range(len(node_insts_sorted) - 1):
                        # sort instances
                        first, last = node_insts_sorted[j], node_insts_sorted[j + 1]
                        inbetween = get_inbetween(pred, succ, first, last)
                        direct_prec = pred[last]
                        current_loop_end_labels.update({x.label for x in inbetween & direct_prec})
                        if len(inbetween) == 0:
                            current_loop_end_labels.add(first.label)

                        current_nodes = inbetween | {first, last}

                        new_label_group.update({n.label for n in current_nodes})
                        current_labels_to_include.update(new_label_group)
                        current_nodes_to_include.update(current_nodes)

                print("new current_loop_labels: ", current_labels_to_include)
                print("new current_loop_start_nodes: ", current_loop_start_labels)
                print("new current_loop_end_nodes: ", current_loop_end_labels)

                processed_labels.update(current_labels_to_include)

                loop_groups.append(new_label_group)

            all_current_projections = set()
            sorted_nodes = sorted(current_nodes_to_include, key=lambda l: transitive_pred[l], reverse=False)
            print("sorted_nodes: ", sorted_nodes)
            next_start = {sorted_nodes[0]}
            while len(next_start) > 0:
                print(f"next_start: {next_start}")
                projection_start = next_start
                projection_end = set()
                print(f"prj_start: {projection_start}")
                print(f"prj_end: {projection_end}")
                n = 0
                while n != len(projection_start) + len(projection_end):
                    n = len(projection_start) + len(projection_end)

                    reach = set()
                    dq = deque(list(projection_start))
                    while dq:
                        u = dq.popleft()
                        for v in succ[u]:
                            if v not in reach and v in current_nodes_to_include and v.label not in current_loop_start_labels:
                                reach.add(v)
                                if v.label in current_loop_end_labels:
                                    projection_end.add(v)
                                dq.append(v)

                    anc = set()

                    dq = deque(list(projection_end))
                    while dq:
                        u = dq.popleft()
                        for p in pred[u]:
                            if p not in anc and p in current_nodes_to_include and p.label not in current_loop_end_labels:
                                anc.add(p)
                                if p.label in current_loop_start_labels:
                                    projection_start.add(p)
                                dq.append(p)

                proj_nodes = (projection_end | anc) & (projection_start | reach)

                if len(proj_nodes) == 0:
                    projection_end = projection_start
                    proj_nodes = projection_start

                print(f"prj_start: {projection_start}")
                print(f"prj_end: {projection_end}")
                print(f"reach: {reach}")
                print(f"anc: {anc}")
                print(f"proj_nodes: {proj_nodes}")
                projection = project_on_nodes(graph, proj_nodes)
                print(f"projection: {projection}")
                all_current_projections.add(projection)
                next_start = set()
                for u in projection_end:
                    next_start.update(succ[u])
                next_start &= current_nodes_to_include

            from src.miner import _mine
            orders = list(all_current_projections)
            mapping_skips = SkipMiner.find_skips(orders)
            orders = SkipMiner.apply_mapping(orders, mapping_skips)

            combined_order = combine_orders(orders)
            print(f"all_orders: {all_current_projections}")
            print(f"combined_order: {combined_order}")
            loop_node = LOOP(body=combined_order, redo=ActivityInstance(label=None, number=1))

            for n in current_labels_to_include:
                mapping[n] = loop_node

        return mapping, {}


            # print("created loop node:", loop_node)

            # found = False
            # for other_loop in loops:
            #     other_do = other_loop.body
            #     if isinstance(do_part, ActivityInstance):
            #         if isinstance(other_do, ActivityInstance) and other_do.label == do_part.label:
            #             found = True
            #             loop_node = other_loop
            #     elif isinstance(do_part, Graph):
            #         if isinstance(other_do, Graph):
            #             other_labels = {n.label for n in other_do.nodes}
            #             other_edges = {(s.label, t.label) for (s, t) in other_do.edges}
            #             new_edges_labels = {(s.label, t.label) for (s, t) in new_edges}
            #             if other_labels == new_label_group and other_edges == new_edges_labels:
            #                 found = True
            #                 loop_node = other_loop

            # if not found:
            #     loops.add(loop_node)

            # loops_frequencies[loop_node] += 1
            # label_group_to_loop_map[frozenset(new_label_group)].add(do_part)

            # for n in do_set:
            #     processed_nodes.add(n)
            #     mapping[n] = loop_node
            #     # print(f"mapped loop node {n} to {loop_node}")
            # if len(do_set) == 1:
            #     mapping[last] = loop_node
        #
        # print(f"Loop labels: {loop_groups}")
        # merged = []
        # for label_group in loop_groups:
        #     placed = False
        #     for m in merged:
        #         if m & label_group:
        #             m |= label_group
        #             placed = True
        #             break
        #     if not placed:
        #         merged.append(set(label_group))
        # print(f"Loop labels merged: {merged}")
        # changed = True
        # new_group_to_orders_mapping = {}
        # while changed:
        #     changed = False
        #     new_merged = []
        #
        #     while merged:
        #         grp = merged.pop()
        #         grp_orders = label_group_to_loop_map[frozenset(grp)]
        #         for other in merged:
        #             if grp & other:
        #                 merged.remove(other)
        #                 grp |= other
        #                 grp_orders |= label_group_to_loop_map[frozenset(other)]
        #                 changed = True
        #                 break
        #         for order in grp_orders:
        #             old_nodes = set(order.nodes)
        #             for label in grp:
        #                 node = ActivityInstance(label, 1)
        #                 old_nodes.add(node)
        #             order.nodes = frozenset(old_nodes)
        #         new_merged.append(grp)
        #         new_group_to_orders_mapping[frozenset(grp)] = grp_orders
        #     merged = new_merged
        # print(f"Loop labels merged new: {merged}")
        #
        # # 5) build one LOOP per merged group
        # mapping = {}
        # for group in merged:
        #     print(new_group_to_orders_mapping[frozenset(group)])
        #     merged_order = combine_orders(new_group_to_orders_mapping[frozenset(group)])
        #     print("COMBINED INTO: ", new_group_to_orders_mapping[frozenset(group)])
        #     for n in group:
        #         mapping[n] = merged_order
        #
        #
        # return mapping, loops_frequencies

    @classmethod
    def apply_mapping(cls, graph: Graph, input_mapping: dict, loops_frequencies: {}):


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
