from src.combine_order import combine_orders
from src.labeled_xor_miner import LabeledXORMiner
from src.objects import VARIANT_FREQUENCY_KEY, Graph, XOR, ActivityInstance, simplified_model_to_powl

from pm4py.objects.powl.obj import SilentTransition


def __add_edge(node, other_node, label_mapping, edges_set):
    if node.label in label_mapping.keys():
        source = label_mapping[node.label]
    else:
        source = node
    if other_node.label in label_mapping.keys():
        target = label_mapping[other_node.label]
    else:
        target = other_node
    if source != target:
        edges_set.add((source, target))


def __map_transitions_to_submodels(orders, label_mapping):
    res = []

    for graph in orders:
        new_nodes = set()
        for node in graph.nodes:
            if node.label not in label_mapping.keys():
                new_nodes.add(node)
            else:
                new_nodes.add(label_mapping[node.label])

        edges_set = set()
        for (s, t) in graph.edges:
            __add_edge(s, t, label_mapping, edges_set)

        for s in new_nodes:
            for t in new_nodes:
                if (s, t) in edges_set and (t, s) in edges_set:
                    edges_set.remove((s, t))
                    edges_set.remove((t, s))

        new_graph = Graph(frozenset(new_nodes), frozenset(edges_set),
                          {VARIANT_FREQUENCY_KEY: graph.additional_information[VARIANT_FREQUENCY_KEY]})

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


def __mine(orders):
    if len(orders) == 1:
        if len(orders[0].nodes) == 0:
            return SilentTransition()
        elif len(orders[0].nodes) == 1:
            return list(orders[0].nodes)[0]

    xor_clusters = LabeledXORMiner.find_disjoint_activities(orders)
    if xor_clusters is not None:
        label_mapping = {}
        for cluster in xor_clusters:

            sub_models = []
            if LabeledXORMiner.has_empty_traces(orders, cluster):
                sub_models.append(ActivityInstance(None, 1))
            for group in cluster:
                projected_log = LabeledXORMiner.project_partial_orders_on_groups(orders, list(group))
                sub_models.append(__mine(projected_log))
            model = XOR(children=frozenset(sub_models))
            for group in cluster:
                for activity_label in group:
                    label_mapping[activity_label] = model
        orders = __map_transitions_to_submodels(orders, label_mapping)
    # mapping_self_loop = SelfLoopMiner.find_self_loops(orders)
    # orders = map_tansitions_to_submodels(orders, mapping_self_loop)
    order = combine_orders(orders)
    # for order in orders:
    # print(order.additional_information[VARIANT_FREQUENCY_KEY])

    return order


def mine_powl_from_partial_orders(partial_orders):
    order = __mine(partial_orders)
    print("✅ Done Mining!")
    powl = simplified_model_to_powl(order)
    print("✅ Done Conversion!")
    return powl