# src/loop_miner.py

from collections import defaultdict, deque
from src.objects import LOOP, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY

class LoopMiner:
    @classmethod
    def find_loops(cls, graph: Graph):
        # 1) collect all ActivityInstance nodes by label
        label_to_instances = defaultdict(list)
        for node in graph.nodes:
            if isinstance(node, ActivityInstance) and node.label:
                label_to_instances[node.label].append(node)

        # 2) build adjacency so we can find reachability
        succ = defaultdict(set)
        pred = defaultdict(set)
        for s, t in graph.edges:
            succ[s].add(t)
            pred[t].add(s)

        mapping = {}

        # 3) for each label with ≥2 instances, build one LOOP
        for label, insts in label_to_instances.items():
            if len(insts) < 2:
                continue

            # sort by the instance.number
            insts = sorted(insts, key=lambda x: x.number)
            first, second = insts[0], insts[1]

            # reachable from first
            reachable = set()
            dq = deque([first])
            while dq:
                u = dq.popleft()
                for v in succ[u]:
                    if v not in reachable:
                        reachable.add(v)
                        dq.append(v)

            # ancestors of second
            ancestors = set()
            dq = deque([second])
            while dq:
                u = dq.popleft()
                for v in pred[u]:
                    if v not in ancestors:
                        ancestors.add(v)
                        dq.append(v)

            # redo = intersection minus the two As
            redo_nodes = reachable & ancestors
            redo_nodes.discard(first)
            redo_nodes.discard(second)

            if len(redo_nodes) == 1:
                redo = next(iter(redo_nodes))
            elif len(redo_nodes) > 1:
                # wrap multiple in a sub-Graph
                redo = Graph(
                    nodes=frozenset(redo_nodes),
                    edges=frozenset((s, t)
                                    for s, t in graph.edges
                                    if s in redo_nodes and t in redo_nodes),
                    additional_information={VARIANT_FREQUENCY_KEY:
                                            graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
                )
            else:
                # fallback to silent
                redo = ActivityInstance(None, 1)

            body = ActivityInstance(label, 1)
            loop_node = LOOP(body=body, redo=redo)

            # map *all* occurrences of this label to the one loop_node
            for inst in insts:
                mapping[inst] = loop_node

        # 4) identity‐map everything else
        for n in graph.nodes:
            if n not in mapping:
                mapping[n] = n

        return mapping

    @classmethod
    def apply_mapping(cls, graph: Graph, mapping: dict):
        new_nodes = frozenset(mapping.values())
        new_edges = set()
        for s, t in graph.edges:
            source = mapping[s]
            target = mapping[t]
            if source != target:
                new_edges.add((source, target))
        filtered_edges = {(s, t) for s, t in new_edges if (t, s) not in new_edges}
        return Graph(
            nodes=new_nodes,
            edges=frozenset(filtered_edges),
            additional_information={VARIANT_FREQUENCY_KEY:
                                    graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)}
        )
