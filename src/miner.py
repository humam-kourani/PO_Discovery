from src.combine_order import combine_orders
from src.xor_miner import XORMiner
from src.objects import XOR, simplified_model_to_powl
from src.loop_miner import LoopMiner

from pm4py.objects.powl.obj import SilentTransition

from src.skip_miner import SkipMiner


def __mine(orders):
    if len(orders) == 1:
        if len(orders[0].nodes) == 0:
            return SilentTransition()
        elif len(orders[0].nodes) == 1:
            return list(orders[0].nodes)[0]

    xor_clusters = XORMiner.find_disjoint_activities(orders)

    label_mapping = {}
    if xor_clusters is not None:

        for cluster in xor_clusters:

            sub_models = []
            # if LabeledXORMiner.has_empty_traces(orders, cluster):
            #     sub_models.append(ActivityInstance(None, 1))
            for group in cluster:
                projected_log = XORMiner.project_partial_orders_on_groups(orders, list(group))
                sub_models.append(__mine(projected_log))
            model = XOR(children=frozenset(sub_models))
            for group in cluster:
                for activity_label in group:
                    if activity_label in label_mapping.keys():
                        raise ValueError("Duplicate activity label")
                    label_mapping[activity_label] = model

    orders = XORMiner.apply_mapping(orders, label_mapping)


    # mapping_self_loop = SelfLoopMiner.find_self_loops(orders)
    # orders = map_tansitions_to_submodels(orders, mapping_self_loop)
    # mapping_skips = SkipMiner.find_skips(orders)
    # orders = SkipMiner.apply_mapping(orders, mapping_skips)

    order = combine_orders(orders)

    # for order in orders:
    # print(order.additional_information[VARIANT_FREQUENCY_KEY])

    loop_mapping = LoopMiner.find_loops(order)
    order = LoopMiner.apply_mapping(order, loop_mapping)

    return order


def mine_powl_from_partial_orders(partial_orders):
    order = __mine(partial_orders)
    print("✅ Done Mining!")
    powl = simplified_model_to_powl(order)
    print("✅ Done Conversion!")
    return powl