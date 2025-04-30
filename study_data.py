from collections import defaultdict
from typing import Dict

import pm4py
import pandas as pd
from pm4py.objects.powl.obj import StrictPartialOrder, Transition

from test import mine
from src.log_to_partial_orders import VARIANT_FREQUENCY_KEY

pd.set_option('display.max_columns', None)


def transform_study_log_to_partially_ordered_variants(df, activity_key, case_key, order_key, build_po_objects=True):
    df = df.sort_values([case_key, order_key])
    df['event_instance_id'] = df.index

    merged_df = pd.merge(
        df,
        df,
        on=case_key,
        suffixes=('_1', '_2')
    )
    merged_df = merged_df[merged_df['event_instance_id_1'] != merged_df['event_instance_id_2']]
    is_directly_followed = merged_df[f'{order_key}_2'] > merged_df[f'{order_key}_1']
    # Store edges with activity labels AND the case_id they belong to
    direct_follows_edges_df = merged_df.loc[is_directly_followed, [case_key, f'{activity_key}_1', f'{activity_key}_2']].copy()
    print(f"Identified {len(direct_follows_edges_df)} total edge candidates.")

    # Group edges by case for quick lookup later
    edges_by_case = direct_follows_edges_df.groupby(case_key)[[f'{activity_key}_1', f'{activity_key}_2']].apply(
        lambda g: tuple(sorted(zip(g[f'{activity_key}_1'], g[f'{activity_key}_2'])))  # Create sorted tuple of edge pairs
    ).to_dict()  # Convert to dictionary {case_id: tuple_of_edges}

    # Calculate Canonical Key per Trace and Group ---
    print("Grouping traces by canonical variant key...")
    variants_data = defaultdict(lambda: {VARIANT_FREQUENCY_KEY: 0, 'cases': []})

    grouped_intervals = df.groupby(case_key)
    total_cases = len(grouped_intervals)
    processed_cases = 0

    for case_id, trace_df in grouped_intervals:
        # Sort all activity occurrences in the trace
        trace_activities_multiset = tuple(sorted(trace_df[activity_key].tolist()))

        # Look up pre-calculated edges for this case
        trace_edges = edges_by_case.get(case_id, tuple())  # Get edges tuple, default to empty tuple if no edges

        # Canonical Variant Key
        variant_key = (trace_activities_multiset, trace_edges)

        # Update dictionary
        variants_data[variant_key][VARIANT_FREQUENCY_KEY] += 1
        variants_data[variant_key]['cases'].append(case_id)
        # Store the structure once if not already present (needed for building PO later)
        if 'structure' not in variants_data[variant_key]:
            variants_data[variant_key]['structure'] = {'activities': trace_activities_multiset, 'edges': trace_edges}

        processed_cases += 1
        if processed_cases % 1000 == 0:
            print(f"Processed {processed_cases}/{total_cases} cases for grouping...")

    print(f"Found {len(variants_data)} unique variants.")

    # Format Output ---
    output_list = []
    for variant_key, data in variants_data.items():
        if build_po_objects:
            # Build the StrictPartialOrder object ONLY for unique variants
            po = StrictPartialOrder([])
            structure = data['structure']
            activity_labels = structure['activities']
            edge_labels = structure['edges']

            transitions_map: Dict[str, Transition] = {}
            node_counter = defaultdict(int)
            for act_label in activity_labels:
                node_counter[act_label] += 1
                trans = Transition(label=act_label)
                if act_label not in transitions_map:
                    transitions_map[act_label] = trans
                po.order.add_node(trans)

            for act1_label, act2_label in edge_labels:

                if act1_label in transitions_map and act2_label in transitions_map:
                    po.add_edge(transitions_map[act1_label], transitions_map[act2_label])

            po.additional_information = {VARIANT_FREQUENCY_KEY: data[VARIANT_FREQUENCY_KEY],
                                         VARIANT_ACTIVITIES_KEY: list(activity_labels)}
            output_list.append(po)
        else:
            # Return summary dictionary
            summary = {
                VARIANT_ACTIVITIES_KEY: list(variant_key[0]),  # Convert tuple back to list
                'edges': list(variant_key[1]),  # Convert tuple back to list
                VARIANT_FREQUENCY_KEY: data[VARIANT_FREQUENCY_KEY],
                'num_cases': len(data['cases'])
                # 'case_ids': data['cases'] # Optionally include case IDs
            }
            output_list.append(summary)

    # Sort output by frequency
    output_list.sort(
        key=lambda x: x.additional_information[VARIANT_FREQUENCY_KEY] if build_po_objects else x[VARIANT_FREQUENCY_KEY],
        reverse=True)

    return output_list


if __name__ == "__main__":
    log = pm4py.read_xes(r"C:\Users\kourani\Downloads\studybuddy_data\Filtered_Bachelor_Informatik_course_IDs_wo_duplicate_NTW.xes.gz", variant="rustxes")
    print(log.columns)
    activity_key = 'course_number'
    case_key = 'case:personId'
    order_key = 'relativeTerm'


    log = log[[activity_key, case_key, order_key]]
    # top_values = log[activity_key].value_counts().nlargest(18).index
    #
    # log = log[log[activity_key].isin(top_values)]

    # cases_with_thesis = log[log[activity_key] == 'Bachelorarbeit'][case_key].unique().tolist()

    # log = log[log[case_key].isin(cases_with_thesis)]

    print(len(log[activity_key].unique()))

    partial_orders = transform_study_log_to_partially_ordered_variants(log, activity_key, case_key, order_key, build_po_objects=True)


    print(partial_orders[:10])
    print("HI")

    powl_model = mine(partial_orders)

    pn, im, fm = pm4py.convert_to_petri_net(powl_model)
    pm4py.view_petri_net(pn, im, fm, format='svg')

    pm4py.view_powl(powl_model, format='svg')

    # pn, im, fm = pm4py.convert_to_petri_net(powl_model)
    # print(pm4py.fitness_token_based_replay(complete_log, pn, im, fm))