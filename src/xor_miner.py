from typing import Set

import networkx as nx

from src.objects import Graph, ActivityInstance, XOR, LOOP
from src.log_to_partial_orders import VARIANT_FREQUENCY_KEY
from pm4py.algo.discovery.inductive.cuts import utils as cut_util


def get_activity(node) -> Set[str]:
    if isinstance(node, ActivityInstance):
        return {node.label} if node.label else set()
    if isinstance(node, Graph):
        children = node.nodes
    elif isinstance(node, XOR):
        children = node.children
    elif isinstance(node, LOOP):
        children = [node.body, node.redo]
    else:
        raise TypeError
    res = set()
    for child in children:
        res.update(get_activity(child))
    return res


class XORMiner:

    @classmethod
    def find_disjoint_activities(cls, partial_orders, all_activity_labels):

        """
        Finds activities that never occur together in the same partial order.

        :param all_activity_labels:
        :param partial_orders: List of partial orders.
        :return: Groups of disjoint activities.
        """

        all_activity_labels = sorted(all_activity_labels)
        adjacency = {activity: {other_activity: 0 for other_activity in all_activity_labels} for activity in all_activity_labels}

        for graph in partial_orders:
            activity_labels_in_trace = get_activity(graph)
            for i, activity in enumerate(activity_labels_in_trace):
                for j, other_activity in enumerate(activity_labels_in_trace):
                    if i != j:
                        adjacency[activity][other_activity] += 1

        found_xor = False
        clusters = [[a] for a in all_activity_labels]
        for i in range(len(all_activity_labels)):
            activity = all_activity_labels[i]
            for j in range(i + 1, len(all_activity_labels)):
                other_activity = all_activity_labels[j]
                if adjacency[activity][other_activity] == 0 and adjacency[other_activity][activity] == 0:
                    found_xor = True
                    clusters = cut_util.merge_lists_based_on_activities(activity, other_activity, clusters)

        if found_xor:
            res = []
            for cluster in clusters:
                if len(cluster) == 1:
                    # res_dict[cluster[0]] = cluster[0]
                    pass
                else:
                    from itertools import combinations
                    nx_graph = nx.DiGraph()
                    nx_graph.add_nodes_from(cluster)
                    # print(adjacency)
                    for a, b in combinations(cluster, 2):
                        if adjacency[a][b] > 0 and adjacency[b][a] > 0:
                            nx_graph.add_edge(a, b)
                    nx_und = nx_graph.to_undirected()
                    conn_comps = [nx_und.subgraph(c).copy() for c in nx.connected_components(nx_und)]
                    if len(conn_comps) > 1:
                        cuts = list()
                        for comp in conn_comps:
                            cuts.append(set(comp.nodes))
                        # children = [cls.project_partial_orders_on_groups(partial_orders, list(cut)) for cut in cuts]
                        # model = OperatorPOWL(Operator.XOR, children=children)
                        # res_dict[tuple(sorted(cluster))] = model
                        res.append(cuts)
                    else:
                        return None
            return res
        else:
            return None

    @classmethod
    def project_partial_orders_on_groups(cls, partial_orders, group):
        res = []
        for graph in partial_orders:
            new_nodes = frozenset([n for n in graph.nodes if get_activity(n).issubset(group)])
            if len(new_nodes) == 0:
                continue
            new_edges = frozenset([(s, t) for (s, t) in graph.edges if s in new_nodes and t in new_nodes])
            new_graph = Graph(new_nodes, new_edges)
            found = False
            # for other_graph in res:
            #     if other_graph == new_graph:
            #         found = True
            #         other_graph.additional_information[VARIANT_FREQUENCY_KEY] = other_graph.additional_information[VARIANT_FREQUENCY_KEY] + graph.additional_information[VARIANT_FREQUENCY_KEY]
            #         break
            if not found:
                new_graph.additional_information = {VARIANT_FREQUENCY_KEY: graph.additional_information[VARIANT_FREQUENCY_KEY]}
                res.append(new_graph)
        return res

    # @classmethod
    # def has_empty_traces(cls, partial_orders, cluster):
    #     # res = StrictPartialOrder([Transition(a) for a in list(group)])
    #     all_nodes = []
    #     for group in cluster:
    #         all_nodes = all_nodes + list(group)
    #
    #     for graph in partial_orders:
    #         new_nodes = [n for n in graph.nodes if n.label in all_nodes]
    #         if len(new_nodes) == 0:
    #             return True
    #
    #     return False
    @classmethod
    def apply_mapping(cls, orders, label_mapping):
        res = []

        for graph in orders:
            new_nodes = set()
            for node in graph.nodes:
                label = get_activity(node).pop()
                if label in label_mapping.keys():
                    new_nodes.add(label_mapping[node.label])
                else:
                    new_nodes.add(node)

            edges_set = set()
            for (s, t) in graph.edges:
                XORMiner.__add_edge(s, t, label_mapping, edges_set)

            for s in new_nodes:
                for t in new_nodes:
                    if (s, t) in edges_set and (t, s) in edges_set:
                        edges_set.remove((s, t))
                        edges_set.remove((t, s))

            new_graph = Graph(frozenset(new_nodes), frozenset(edges_set), graph.additional_information)

            found_po = False
            # for other_graph in res:
            #     if other_graph == new_graph:
            #         other_graph.additional_information[VARIANT_FREQUENCY_KEY] = other_graph.additional_information[
            #                                                                      VARIANT_FREQUENCY_KEY] + \
            #                                                                  graph.additional_information[
            #                                                                      VARIANT_FREQUENCY_KEY]
            #         found_po = True
            #         break

            if not found_po:
                res.append(new_graph)
        return res

    @classmethod
    def __add_edge(cls, node, other_node, label_mapping, edges_set):
        label = get_activity(node).pop()
        if label in label_mapping.keys():
            source = label_mapping[label]
        else:
            source = node
        other_labels = get_activity(other_node)
        if other_labels.issubset(label_mapping.keys()):
            target = label_mapping[other_labels.pop()]
        else:
            target = other_node
        if source != target:
            edges_set.add((source, target))

