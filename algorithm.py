import pm4py
from utils.labeled_xor_miner import LabeledXORMiner
from utils.log_to_partial_orders import \
    transform_log_to_partially_ordered_variants, VARIANT_FREQUENCY_KEY, VARIANT_ACTIVITIES_KEY
from utils.self_loop_miner import SelfLoopMiner
from pm4py.objects.powl.obj import StrictPartialOrder, OperatorPOWL, SilentTransition
from pm4py.objects.process_tree.obj import Operator
from pm4py.visualization.powl.visualizer import apply as visualize_powl


def add_edge(node, other_node, groups, po):
    if node.label in groups.keys():
        source = groups[node.label]
    else:
        source = node
    if other_node.label in groups.keys():
        target = groups[other_node.label]
    else:
        target = other_node
    po.order.add_edge(source, target)


def map_tansitions_to_submodels(orders, mapping):
    res = []
    for po in orders:
        nodes = set()
        for node in po.order.nodes:
            if node.label not in mapping.keys():
                nodes.add(node)
            else:
                nodes.add(mapping[node.label])

        new_order = StrictPartialOrder(nodes=list(nodes))
        for node in po.order.nodes:
            for other_node in po.order.nodes:
                if po.order.is_edge(node, other_node):
                    add_edge(node, other_node, mapping, new_order)

        for node in new_order.order.nodes:
            for other_node in new_order.order.nodes:
                if new_order.order.is_edge(node, other_node) and new_order.order.is_edge(other_node, node):
                    new_order.order.remove_edge(node, other_node)
                    new_order.order.remove_edge(other_node, node)

        found_po = False
        for other_po in res:
            if new_order.equal_content(other_po):
                other_po.additional_information[VARIANT_FREQUENCY_KEY] = other_po.additional_information[
                                                                             VARIANT_FREQUENCY_KEY] + \
                                                                         po.additional_information[
                                                                             VARIANT_FREQUENCY_KEY]
                found_po = True
                break

        if not found_po:
            old_leaves = po.additional_information[VARIANT_ACTIVITIES_KEY]
            new_order.additional_information = {VARIANT_FREQUENCY_KEY: po.additional_information[VARIANT_FREQUENCY_KEY],
                                                VARIANT_ACTIVITIES_KEY: [a for a in old_leaves if a not in mapping.keys()]}
            res.append(new_order)

    res.sort(key=lambda po: po.additional_information[VARIANT_FREQUENCY_KEY], reverse=True)
    return res


def combine_orders(orders):
    new_order = StrictPartialOrder(nodes=[])

    for partial_order in orders:
        for node in partial_order.order.nodes:
            new_order.order.add_node(node)
        for node1 in partial_order.order.nodes:
            for node2 in partial_order.order.nodes:
                if partial_order.order.is_edge(node1, node2):
                    new_order.order.add_edge(node1, node2)

    # new_order.order.add_transitive_edges()

    for node in new_order.order.nodes:
        for other_node in new_order.order.nodes:
            if new_order.order.is_edge(node, other_node) and new_order.order.is_edge(other_node, node):
                new_order.order.remove_edge_without_violating_transitivity(node, other_node)
                new_order.order.remove_edge_without_violating_transitivity(other_node, node)
            elif new_order.order.is_edge(node, other_node):
                for partial_order in orders:
                    if node in partial_order.order.nodes and other_node in partial_order.order.nodes:
                        if not partial_order.order.is_edge(node, other_node):
                            new_order.order.remove_edge_without_violating_transitivity(node, other_node)

    if not new_order.order.is_strict_partial_order():
        raise ValueError('Not strict_partial_order!')

    return new_order


def mine(orders):
    if len(orders) == 1:
        if len(orders[0].order.nodes) == 0:
            return SilentTransition()
        elif len(orders[0].order.nodes) == 1:
            return orders[0].order.nodes[0]

    xor_clusters = LabeledXORMiner.find_disjoint_activities(orders)
    if xor_clusters is not None:
        mapping = {}
        for cluster in xor_clusters:
            sub_models = []
            if LabeledXORMiner.has_empty_traces(orders, cluster):
                sub_models.append(SilentTransition())
            for group in cluster:
                projected_log = LabeledXORMiner.project_partial_orders_on_groups(orders, list(group))
                # print(projected_log)
                sub_models.append(mine(projected_log))
            model = OperatorPOWL(Operator.XOR, children=sub_models)
            for group in cluster:
                for activity in group:
                    mapping[activity] = model
        orders = map_tansitions_to_submodels(orders, mapping)
    mapping_self_loop = SelfLoopMiner.find_self_loops(orders)
    orders = map_tansitions_to_submodels(orders, mapping_self_loop)
    po = combine_orders(orders)

    return po


if __name__ == "__main__":
    log = pm4py.read_xes(r"C:\Users\kourani\OneDrive - Fraunhofer\FIT\powl_ev\Unfiltered XES Logs\BPI_Challenge_2012.xes.gz")
    # log = pm4py.read_xes("test_logs/interval_event_log_with_LC.xes")
    partial_orders = transform_log_to_partially_ordered_variants(log)
    powl_model = mine(partial_orders)
    # order = order.apply_all_reductions()
    pm4py.view_powl(powl_model, format='svg')

    # for i, po in enumerate(partial_orders):
    #   print(str(i + 1) + "th PO with a freq of " + str(po.additional_information[VARIANT_FREQUENCY_KEY]))
    #   if not po.order.is_transitive():
    #       raise ValueError("NOT transitive")
    #   if not po.order.is_irreflexive():
    #       raise ValueError("NOT irreflexive")
    #   vis_3 = visualize_powl(po, variant=pm4py.visualization.powl.visualizer.POWLVisualizationVariants.BASIC,
    #                          parameters={"format": "svg"})
    #   vis_3.view()
    # print(po.order.get_transitive_reduction())
    # print()
