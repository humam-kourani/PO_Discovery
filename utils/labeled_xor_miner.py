import networkx as nx

from utils.log_to_partial_orders import VARIANT_ACTIVITIES_KEY, VARIANT_FREQUENCY_KEY
from pm4py.objects.powl.obj import Transition, StrictPartialOrder
from pm4py.algo.discovery.inductive.cuts import utils as cut_util


class LabeledXORMiner:

    @classmethod
    def find_disjoint_activities(cls, partial_orders):

        """
        Finds activities that never occur together in the same partial order.

        :param partial_orders: List of partial orders.
        :return: Groups of disjoint activities.
        """

        all_activities = sorted(
            set(activity for po in partial_orders for activity in po.additional_information[VARIANT_ACTIVITIES_KEY]))

        adjacency = {activity: {other_activity: 0 for other_activity in all_activities} for activity in all_activities}

        for po in partial_orders:
            activities_in_trace = po.additional_information[VARIANT_ACTIVITIES_KEY]
            for i, activity in enumerate(activities_in_trace):
                for j, other_activity in enumerate(activities_in_trace):
                    if i != j:
                        adjacency[activity][other_activity] += 1

        found_xor = False
        clusters = [[a] for a in all_activities]
        for i in range(len(all_activities)):
            activity = all_activities[i]
            for j in range(i + 1, len(all_activities)):
                other_activity = all_activities[j]
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

        for po in partial_orders:
            new_nodes = [n for n in po.order.nodes if n.label in group]
            if len(new_nodes) == 0:
                continue
            new_po = StrictPartialOrder(nodes=new_nodes)
            for n1 in new_nodes:
                for n2 in new_nodes:
                    if po.order.is_edge(n1, n2):
                        new_po.order.add_edge(n1, n2)
            found = False
            for other_po in res:
                if other_po.equal_content(new_po):
                    found = True
                    other_po.additional_information[VARIANT_FREQUENCY_KEY] = other_po.additional_information[VARIANT_FREQUENCY_KEY] + po.additional_information[VARIANT_FREQUENCY_KEY]
                    break
            if not found:
                new_po.additional_information = {VARIANT_FREQUENCY_KEY: po.additional_information[VARIANT_FREQUENCY_KEY],
                                             VARIANT_ACTIVITIES_KEY: [n.label for n in new_nodes if isinstance(n, Transition)]}
                res.append(new_po)
        return res

    @classmethod
    def has_empty_traces(cls, partial_orders, groups):
        # res = StrictPartialOrder([Transition(a) for a in list(group)])
        all_nodes = []
        for group in groups:
            all_nodes = all_nodes + list(group)

        for po in partial_orders:
            new_nodes = [n for n in po.order.nodes if n.label in all_nodes]
            if len(new_nodes) == 0:
                return True

        return False
