from collections import defaultdict
from src.objects import XOR, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY


class SkipMiner:

    @classmethod
    def find_skips(cls, partial_orders):

        partial_orders = list(partial_orders)
        node_to_orders = defaultdict(list)
        n = len(partial_orders)

        # important to use set first then convert to list; otherwise, nodes will be duplicated
        all_nodes = list({node for graph in partial_orders for node in graph.nodes})


        for node_id, current_node in enumerate(all_nodes):
            for graph_id, graph in enumerate(partial_orders):
                if current_node in graph.nodes:
                    node_to_orders[node_id].append(graph_id)

        graph_ids_lists_to_nodes = defaultdict(list)

        sorted_keys = sorted(node_to_orders.keys(), key=lambda x: len(node_to_orders[x]), reverse=True)
        # print(sorted_keys)

        for node_id in sorted_keys:
            graph_id_list = node_to_orders[node_id]
        # for node_id, graph_id_list in node_to_orders.items():

            new_frozenset = frozenset(graph_id_list)
            number_supersets = 0
            for key in graph_ids_lists_to_nodes.keys():
                if len(key) < n and new_frozenset.issubset(key):
                    # graph_ids_lists_to_nodes[key].append(node_id)
                    number_supersets = number_supersets + 1
                    last_superset = key
                    # break
            if number_supersets == 1 and False:
                graph_ids_lists_to_nodes[last_superset].append(node_id)
            else:
                # if number_supersets > 1:
                #     raise Exception("Too many supersets")
                graph_ids_lists_to_nodes[new_frozenset].append(node_id)


        res_dict = {}

        for graph_id_list, node_id_list in graph_ids_lists_to_nodes.items():
            if len(graph_id_list) == n:
                for node_id in node_id_list:
                    node = all_nodes[node_id]
                    res_dict[node] = node
            else:
                child_1 = ActivityInstance(None, 1)

                all_projections = []
                for graph_id in graph_id_list:
                    graph = partial_orders[graph_id]
                    proj_nodes = [node for i, node in enumerate(all_nodes) if i in node_id_list and node in graph.nodes]
                    proj_edges = [(s,t) for (s, t) in graph.edges if s in proj_nodes and t in proj_nodes]
                    projection = Graph(frozenset(proj_nodes),
                                       frozenset(proj_edges),
                                       {VARIANT_FREQUENCY_KEY: graph.additional_information[VARIANT_FREQUENCY_KEY]})
                    all_projections.append(projection)
                from src.miner import _mine
                print(f"LEN PROJ: {len(all_projections)}")
                new_graph = _mine(all_projections)
                xor = XOR(frozenset([new_graph, child_1]))
                for node_id in node_id_list:
                    node = all_nodes[node_id]
                    res_dict[node] = xor



            # can_be_skipped = not all(current_node in graph.nodes for graph in partial_orders)
            # loop = False
            # # loop = any(current_activity in graph.nodes)
            # for graph in partial_orders:
            #     if current_activity in graph.nodes:
            #     # po_activities = po.additional_information[VARIANT_ACTIVITIES_KEY]
            #     if po_activities.count(current_activity) == 0:
            #         can_be_skipped = True
            #     elif po_activities.count(current_activity) > 1:
            #         loop = True

            # if can_be_skipped and loop:
            #     res_dict[current_node] = LOOP(body=ActivityInstance(None, 1), redo=current_node)
            # elif can_be_skipped and not loop:
            #     res_dict[current_node] = XOR(children=frozenset({current_node, ActivityInstance(None, 1)}))
            # elif not can_be_skipped and loop:
            #     res_dict[current_node] = LOOP(body=current_node, redo=ActivityInstance(None, 1),)
            # else:
            #     res_dict[current_node] = current_node

        return res_dict

