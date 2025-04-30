from src.objects import XOR, LOOP, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY


class SkipMiner:

    @classmethod
    def find_skips(cls, partial_orders):

        all_nodes = {node for graph in partial_orders for node in graph.nodes}

        res_dict = {}
        for current_node in all_nodes:
            can_be_skipped = not all(current_node in graph.nodes for graph in partial_orders)
            loop = False
            # # loop = any(current_activity in graph.nodes)
            # for graph in partial_orders:
            #     if current_activity in graph.nodes:
            #     # po_activities = po.additional_information[VARIANT_ACTIVITIES_KEY]
            #     if po_activities.count(current_activity) == 0:
            #         can_be_skipped = True
            #     elif po_activities.count(current_activity) > 1:
            #         loop = True

            if can_be_skipped and loop:
                res_dict[current_node] = LOOP(body=ActivityInstance(None, 1), redo=current_node)
            elif can_be_skipped and not loop:
                res_dict[current_node] = XOR(children=frozenset({current_node, ActivityInstance(None, 1)}))
            elif not can_be_skipped and loop:
                res_dict[current_node] = LOOP(body=current_node, redo=ActivityInstance(None, 1),)
            else:
                res_dict[current_node] = current_node

        return res_dict

    @classmethod
    def apply_mapping(cls, orders, mapping_skips):
        res = []

        for graph in orders:
            new_nodes = {mapping_skips[node] for node in graph.nodes}
            new_edges = {(mapping_skips[s], mapping_skips[t]) for s, t in graph.edges}

            new_graph = Graph(frozenset(new_nodes), frozenset(new_edges),
                              {VARIANT_FREQUENCY_KEY: graph.additional_information[VARIANT_FREQUENCY_KEY]})
            res.append(new_graph)

        return res

