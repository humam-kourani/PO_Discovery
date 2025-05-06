import pm4py

from src import local_powl_visualizer
from src.log_to_partial_orders import transform_log_to_partially_ordered_variants
from src.miner import mine_powl_from_partial_orders

if __name__ == "__main__":
    log = pm4py.read_xes(r"C:\Users\kourani\OneDrive - Fraunhofer\FIT\powl_ev\Unfiltered XES Logs\BPI_Challenge_2012.xes.gz", variant="rustxes")
    # log = pm4py.read_xes(r"C:\Users\kourani\Downloads\example-logs\example-logs\repairExample.xes", variant="rustxes")

    # print(log)
    # log = pm4py.read_xes("test_logs/interval_event_log_with_LC - skip make delivery and multiple payment.xes", variant="rustxes")
    # print(log['lifecycle:transition'])
    # print(len(log))
    # complete_log = log[log['lifecycle:transition'].isin(["complete", "COMPLETE"])]
    # print(len(complete_log))
    # start_log = log[log['lifecycle:transition'].isin(["start", "START"])]
    # print(len(start_log))
    import datetime
    start_time = datetime.datetime.now()
    partial_orders = transform_log_to_partially_ordered_variants(log)
    print(partial_orders)
    print(len(partial_orders))
    # print(partial_orders)
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
        powl = mine_powl_from_partial_orders(partial_orders)
        local_powl_visualizer.view(powl)
        # pm4py.view_powl(powl, format="SVG")
        # Simulates a task that takes 35 seconds
        print("✅ Done Visualizing!")
        end_time = datetime.datetime.now()
        print(f"time: {end_time - start_time}")


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
