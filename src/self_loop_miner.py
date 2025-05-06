from collections import defaultdict
from src.objects import XOR, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY, LOOP
from src.xor_miner import get_activity


class SelfLoopMiner:

    @classmethod
    def find_self_loops(cls, graph):

        node_mapping = {}
        reversed_mapping = defaultdict(set)

        print(f"len nodes: {len(graph.nodes)}")

        for node in graph.nodes:
            normalized_node = node.normalize()
            # node_mapping[node] = normalized_node
            reversed_mapping[normalized_node].add(node)

        print(f"len new nodes: {len(reversed_mapping.keys())}")

        print("reversed_mapping: ", reversed_mapping)
        for key, value in reversed_mapping.items():
            if len(value) > 1:
                new_node = LOOP(body=key, redo=ActivityInstance(label=None, number=1))
            else:
                new_node = key
            for node in value:
                node_mapping[node] = new_node

        return node_mapping

        # succ = defaultdict(set)
        # pred = defaultdict(set)
        # t_edges = {(s, t) for (s, m1) in graph.edges for (m2, t) in graph.edges if
        #            m1 == m2 and (s, t) in graph.edges}
        # reduction = graph.edges - t_edges
        # for s, t in reduction:
        #     succ[s].add(t)
        #     pred[t].add(s)
        #
        # for (s, t) in reduction:
        #
        #
        # self_loops.update({s.label  if s in all_nodes and t in all_nodes and s.label == t.label})
        #
        # res_dict = {}
        # for node in all_nodes_including_complex:
        #     if node in all_nodes and node.label in self_loops:
        #         res_dict[node] = LOOP(body=ActivityInstance(node.label, 1), redo=ActivityInstance(None, 1))
        #     else:
        #         res_dict[node] = node
        #
        # return res_dict

    # @classmethod
    # def apply_mapping(cls, orders, mapping_skips):
    #     res = []
    #
    #     print(mapping_skips)
    #
    #     for graph in orders:
    #         new_nodes = {mapping_skips[node] for node in graph.nodes}
    #         new_edges = {(mapping_skips[s], mapping_skips[t]) for s, t in graph.edges}
    #
    #         new_graph = Graph(frozenset(new_nodes), frozenset(new_edges),
    #                           {VARIANT_FREQUENCY_KEY: graph.additional_information[VARIANT_FREQUENCY_KEY]})
    #         res.append(new_graph)
    #
    #     return res

