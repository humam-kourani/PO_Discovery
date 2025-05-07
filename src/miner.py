from src.combine_order import combine_orders
from src.constants import LOOP_MINING, XOR_MINING
from src.mapping import find_self_loops, apply_node_mapping_on_single_graph
from src.xor_miner import XORMiner, get_activity
from src.objects import XOR, simplified_model_to_powl, ActivityInstance, SelfLoop, Skip, Graph, LOOP

from src.skip_miner import SkipMiner

def apply_mining_algorithm_recursively(node):
    if isinstance(node, ActivityInstance):
        if LOOP_MINING:
            return ActivityInstance(node.label, 1)
        else:
            return node
    elif isinstance(node, Skip):
        node_element = apply_mining_algorithm_recursively(node.element)
        return Skip.create(node_element)
    elif isinstance(node, Graph):
        return _mine([node])
    elif isinstance(node, LOOP):
        body = apply_mining_algorithm_recursively(node.body)
        redo = apply_mining_algorithm_recursively(node.redo)
        return LOOP(body, redo)
    elif isinstance(node, XOR):
        new_children = {apply_mining_algorithm_recursively(child) for child in node.children}
        return XOR(frozenset(new_children))
    else:
        raise TypeError('Unsupported node type')


def _mine(orders):

    if len(orders) < 1:
        raise ValueError("Input list of partial orders is empty!")

    all_activity_labels = set()

    for graph in orders:
        for node in graph.nodes:
            all_activity_labels.update(get_activity(node))

    if LOOP_MINING:
        if len(all_activity_labels) == 1:
            activity_label = all_activity_labels.pop()
            activity = ActivityInstance(activity_label, 1)
            if any(len(order.nodes) > 1 for order in orders):
                return SelfLoop(activity)
            else:
                return activity

    if XOR_MINING:
        xor_clusters = XORMiner.find_disjoint_activities(orders, all_activity_labels)

        label_mapping = {}
        if xor_clusters is not None:

            for cluster in xor_clusters:

                sub_models = []
                for group in cluster:
                    projected_log = XORMiner.project_partial_orders_on_groups(orders, list(group))
                    sub_models.append(_mine(projected_log))
                model = XOR(children=frozenset(sub_models))
                for group in cluster:
                    for activity_label in group:
                        if activity_label in label_mapping.keys():
                            raise ValueError("Duplicate activity label")
                        label_mapping[activity_label] = model

        orders = XORMiner.apply_mapping(orders, label_mapping)


    mapping_skips, new_nodes_counter = SkipMiner.find_skips(orders)
    if LOOP_MINING:
        node_mapping = find_self_loops(mapping_skips, new_nodes_counter)
    else:
        node_mapping = mapping_skips
    orders = [apply_node_mapping_on_single_graph(g, node_mapping) for g in orders]

    if len(orders) == 1:
        order = orders[0]
    else:
        order = combine_orders(orders)


    if len(order.nodes) == 0:
        return ActivityInstance(None, 1)

    if len(order.nodes) == 1:
        return list(order.nodes)[0]

    return order


def mine_powl_from_partial_orders(partial_orders):
    order = _mine(partial_orders)
    # mapping_self_loops = SelfLoopMiner.find_self_loops(order)
    # order = apply_node_mapping_on_single_graph(order, mapping_self_loops)
    print("✅ Done Mining!")
    powl = simplified_model_to_powl(order)
    powl = powl.simplify()
    print("✅ Done Conversion!")
    return powl