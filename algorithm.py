from itertools import product
import pm4py
from utils.labeled_xor_miner import LabeledXORMiner
from utils.log_to_partial_orders import \
    transform_log_to_partially_ordered_variants
from utils.objects import VARIANT_FREQUENCY_KEY, Graph, XOR, ActivityInstance, simplified_model_to_powl
from pm4py.objects.powl.obj import SilentTransition


def add_edge(node, other_node, label_mapping, edges_set):
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


def map_transitions_to_submodels(orders, label_mapping):
    res = []

    for graph in orders:
        new_nodes = set()
        for node in graph.nodes:
            # node is an activity instance
            if node.label not in label_mapping.keys():
                new_nodes.add(node)
            else:
                new_nodes.add(label_mapping[node.label])

        edges_set = set()
        for (s, t) in graph.edges:
            add_edge(s, t, label_mapping, edges_set)

        for s in new_nodes:
            for t in new_nodes:
                if (s, t) in edges_set and (t, s) in edges_set:


                    # nodes = sorted(list(new_nodes))
                    # def remove_edge_without_violating_transitivity2(source, target) -> None:
                    #
                    #     edges_set.discard((source, target))
                    #     n = len(nodes)
                    #     changed = True
                    #     while changed:
                    #         changed = False
                    #         for i, j, k in product(range(n), range(n), range(n)):
                    #             if i != j and j != k:
                    #                 n1 = nodes[i];
                    #                 n2 = nodes[j];
                    #                 n3 = nodes[k]
                    #                 if (n1, n2) in edges_set and (n2, n3) in edges_set and (n1, n3) not in edges_set:
                    #                     edges_set.discard((n2, n3))
                    #                     changed = True
                    #
                    # remove_edge_without_violating_transitivity2(s, t)
                    # remove_edge_without_violating_transitivity2(t, s)

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


def combine_orders(orders):
    conflicts = set()

    edges = set()
    nodes = set()
    i = 0
    for graph in orders:
        i = i + 1

        for s in graph.nodes:
            nodes.add(s)
            for t in graph.nodes:
                if (s, t) in graph.edges:
                    edges.add((s, t))
                else:
                    conflicts.add((s, t))

    nodes = sorted(list(nodes))


    edges = edges - conflicts



    def add_transitive_edges() -> None:
        n = len(nodes)
        changed = True
        while changed:
            changed = False
            for i, j, k in product(range(n), range(n), range(n)):
                if i != j and j != k:
                    n1 = nodes[i]; n2 = nodes[j]; n3 = nodes[k]
                    if (n1, n2) in edges and (n2, n3) in edges and not (n1, n3) in edges:
                        edges.add((n1, n3))
                        changed = True

    add_transitive_edges()

    new_conflicts = {(s, t) for (s, t) in edges if (t, s) in edges}

    conflicts = conflicts | new_conflicts

    def remove_edge_without_violating_transitivity(source, target) -> None:

        edges.remove((source, target))
        n = len(nodes)
        changed = True
        while changed:
            changed = False
            for i, j, k in product(range(n), range(n), range(n)):
                if i != j and j != k:
                    n1 = nodes[i]; n2 = nodes[j]; n3 = nodes[k]
                    if (n1, n2) in edges and (n2, n3) in edges and (n1, n3) not in edges:
                        edges.remove((n2, n3))
                        changed = True


    for (s, t) in conflicts & edges:
        remove_edge_without_violating_transitivity(s, t)

    # for node in nodes:
    #     for other_node in nodes:
    #         if (node, other_node) in edges and (other_node, node) in edges:
    #             remove_edge_without_violating_transitivity(node, other_node)
    #             remove_edge_without_violating_transitivity(other_node, node)
            # elif (node, other_node) in edges:
            #     for graph in orders:
            #         if node in graph.nodes and other_node in graph.nodes:
            #             if not (node, other_node) in graph.edges:
            #                 remove_edge_without_violating_transitivity(node, other_node)

    new_graph = Graph(frozenset(nodes), frozenset(edges),)
    return new_graph


def mine(orders):
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
                sub_models.append(mine(projected_log))
            model = XOR(children=frozenset(sub_models))
            for group in cluster:
                for activity_label in group:
                    label_mapping[activity_label] = model
        orders = map_transitions_to_submodels(orders, label_mapping)
    # mapping_self_loop = SelfLoopMiner.find_self_loops(orders)
    # orders = map_tansitions_to_submodels(orders, mapping_self_loop)
    order = combine_orders(orders)
    # for order in orders:
    # print(order.additional_information[VARIANT_FREQUENCY_KEY])

    return order





if __name__ == "__main__":
    log = pm4py.read_xes(r"C:\Users\kourani\OneDrive - Fraunhofer\FIT\powl_ev\Unfiltered XES Logs\BPI_Challenge_2012.xes.gz", variant="rustxes")
    # log = pm4py.read_xes(r"C:\Users\kourani\Downloads\example-logs\example-logs\repairExample.xes", variant="rustxes")

    # print(log)
    # log = pm4py.read_xes("test_logs/interval_event_log_with_LC.xes", variant="rustxes")
    # print(log['lifecycle:transition'])
    # print(len(log))
    # complete_log = log[log['lifecycle:transition'].isin(["complete", "COMPLETE"])]
    # print(len(complete_log))
    # start_log = log[log['lifecycle:transition'].isin(["start", "START"])]
    # print(len(start_log))

    partial_orders = transform_log_to_partially_ordered_variants(log)
    print(len(partial_orders))
    print(partial_orders)
    # for graph_order in partial_orders:
    # # #     print(graph_order.additional_information[VARIANT_FREQUENCY_KEY])
    #     print(graph_order)
    #     powl_order = simplified_model_to_powl(graph_order)
    #     pm4py.view_powl(powl_order, format='svg')
    # pm4py.view_powl(partial_orders[12], format='svg')


    import time
    import threading



    # Simulate a long-running function
    def long_task():
        print("🔧 Task started...")
        order = mine(partial_orders)
        print("✅ Done Mining!")
        powl = simplified_model_to_powl(order)
        print("✅ Done Conversion!")
        pm4py.view_powl(powl, format='svg')
        # Simulates a task that takes 35 seconds
        print("✅ Done Visualizing!")


    # Reminder function
    def reminder():
        while not task_done.is_set():
            print(f"⏰ Reminder: Task is still running... ({time.strftime('%H:%M:%S')})")
            time.sleep(10)


    # Event to signal when task is done
    task_done = threading.Event()


    # Wrapper to run the task and signal when done
    def run_task_with_flag():
        long_task()
        task_done.set()


    # Start the task and reminder in separate threads
    task_thread = threading.Thread(target=run_task_with_flag)
    reminder_thread = threading.Thread(target=reminder)

    task_thread.start()
    reminder_thread.start()

    # Wait for task to complete
    task_thread.join()
    reminder_thread.join()







    # powl_model = mine(partial_orders)
    # # print(powl_model)
    # # # order = order.apply_all_reductions()
    #
    #
    # pn, im, fm = pm4py.convert_to_petri_net(powl_model)
    # pm4py.view_petri_net(pn, im, fm)
    # print(pm4py.fitness_token_based_replay(complete_log, pn, im, fm))
    #
    # powl_2 = pm4py.discover_powl(complete_log)
    # pm4py.view_powl(powl_2, format='svg')
    # print(pm4py.fitness_alignments(start_log, pn, im, fm))

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
