from collections import deque, defaultdict
from typing import List, Dict, Tuple, Any
import pandas as pd

from src.objects import VARIANT_FREQUENCY_KEY, ActivityInstance, Graph

DEFAULT_CASE_ID_KEY = 'case:concept:name'
DEFAULT_ACTIVITY_KEY = 'concept:name'
DEFAULT_TIMESTAMP_KEY = 'time:timestamp'
DEFAULT_LIFECYCLE_KEY = 'lifecycle:transition'
DEFAULT_LIFECYCLE_INSTANCE_KEY = None

def generate_interval_df_fifo(
    df: pd.DataFrame,
    case_id_col: str, activity_col: str, timestamp_col: str, lifecycle_col: str,
    start_transition: str, complete_transition: str, lifecycle_instance_col: str or None
) -> pd.DataFrame:
    work_df = df[[case_id_col, activity_col, timestamp_col, lifecycle_col] + ([lifecycle_instance_col] if lifecycle_instance_col else [])].copy()
    try:
        if not pd.api.types.is_datetime64_any_dtype(work_df[timestamp_col]):
            work_df[timestamp_col] = pd.to_datetime(work_df[timestamp_col], utc=True)
        elif work_df[timestamp_col].dt.tz is None:
            work_df[timestamp_col] = work_df[timestamp_col].dt.tz_localize('UTC')
        else:
            work_df[timestamp_col] = work_df[timestamp_col].dt.tz_convert('UTC')
    except Exception as e:
        raise ValueError(f"Failed to convert timestamp column '{timestamp_col}': {e}")
    work_df[lifecycle_col] = work_df[lifecycle_col].str.lower()
    work_df = work_df.sort_values([case_id_col, timestamp_col])
    interval_list = []
    for case_id, trace_df in work_df.groupby(case_id_col, sort=False):
        activities_start: Dict[Tuple, deque] = {}
        activities_ids: Dict[str, int] = {}
        for index, event in trace_df.iterrows():
            activity = event[activity_col]
            instance = event[lifecycle_instance_col] if lifecycle_instance_col else None
            activity_key = (activity, instance)
            transition = event[lifecycle_col]
            timestamp = event[timestamp_col]
            if transition == start_transition.lower():
                if activity_key not in activities_start:
                    activities_start[activity_key] = deque()
                activities_start[activity_key].append({'timestamp': timestamp, 'event_index': index})
            elif transition == complete_transition.lower():
                start_timestamp = timestamp
                if activity_key in activities_start and activities_start[activity_key]:
                    start_timestamp = activities_start[activity_key].popleft()['timestamp']
                if activity not in activities_ids:
                    activities_ids[activity] = 1
                else:
                    activities_ids[activity] = activities_ids[activity] + 1
                activity_instance = ActivityInstance(activity, activities_ids[activity])
                interval_record = { case_id_col: case_id, 'activity': activity_instance, 'start_timestamp': start_timestamp, 'end_timestamp': timestamp, **( {lifecycle_instance_col: instance} if lifecycle_instance_col else {} ) }
                interval_list.append(interval_record)
    if not interval_list:
        return pd.DataFrame()
    interval_df = pd.DataFrame(interval_list)
    interval_df['start_timestamp'] = pd.to_datetime(interval_df['start_timestamp'], utc=True)
    interval_df['end_timestamp'] = pd.to_datetime(interval_df['end_timestamp'], utc=True)
    interval_df = interval_df.sort_values([case_id_col, 'start_timestamp', 'end_timestamp']).reset_index(drop=True)
    interval_df['event_instance_id'] = interval_df.index
    print(f"Successfully created {len(interval_df)} activity intervals using FIFO logic.")
    return interval_df


def transform_log_to_partially_ordered_variants(
    df: pd.DataFrame,
    case_id_col: str = DEFAULT_CASE_ID_KEY,
    activity_col: str = DEFAULT_ACTIVITY_KEY,
    timestamp_col: str = DEFAULT_TIMESTAMP_KEY,
    lifecycle_col: str = DEFAULT_LIFECYCLE_KEY,
    start_transition: str = "start",
    complete_transition: str = "complete",
    lifecycle_instance_col: str = DEFAULT_LIFECYCLE_INSTANCE_KEY
) -> List[Any]:
    """
    Returns:
        List of variant summaries (dict) or StrictPartialOrder objects,
        sorted by frequency descending.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'log' must be a Pandas DataFrame.")


    interval_df = generate_interval_df_fifo(
        df, case_id_col, activity_col, timestamp_col, lifecycle_col,
        start_transition, complete_transition, lifecycle_instance_col
    )

    if interval_df.empty:
        raise Exception("Interval DataFrame is empty, no variants to generate.")

    # Pre-calculate All Potential Edges
    print("Calculating potential direct succession edges...")
    merged_df = pd.merge(
        interval_df[[case_id_col, 'activity', 'start_timestamp', 'end_timestamp', 'event_instance_id']],
        interval_df[[case_id_col, 'activity', 'start_timestamp', 'end_timestamp', 'event_instance_id']],
        on=case_id_col,
        suffixes=('_1', '_2')
    )
    merged_df = merged_df[merged_df['event_instance_id_1'] != merged_df['event_instance_id_2']]
    is_directly_followed = merged_df['start_timestamp_2'] > merged_df['end_timestamp_1']
    # Store edges with activity labels AND the case_id they belong to
    direct_follows_edges_df = merged_df.loc[is_directly_followed, [case_id_col, 'activity_1', 'activity_2']].copy()
    print(f"Identified {len(direct_follows_edges_df)} total edge candidates.")

    # Group edges by case for quick lookup later
    edges_by_case = direct_follows_edges_df.groupby(case_id_col)[['activity_1', 'activity_2']].apply(
        lambda g: tuple(sorted(zip(g['activity_1'], g['activity_2'])))  # Create sorted tuple of edge pairs
    ).to_dict()  # Convert to dictionary {case_id: tuple_of_edges}

    # Calculate Canonical Key per Trace and Group ---
    print("Grouping traces by canonical variant key...")
    variants_data = defaultdict(lambda: {VARIANT_FREQUENCY_KEY: 0})

    grouped_intervals = interval_df.groupby(case_id_col)
    total_cases = len(grouped_intervals)
    processed_cases = 0

    for case_id, trace_df in grouped_intervals:
        trace_activities_multiset = frozenset(trace_df['activity'].tolist())

        trace_edges = frozenset(edges_by_case.get(case_id, tuple()))

        # Canonical Variant Key
        variant_key = (trace_activities_multiset, trace_edges)

        # Update dictionary
        variants_data[variant_key][VARIANT_FREQUENCY_KEY] += 1
        if 'structure' not in variants_data[variant_key]:
            variants_data[variant_key]['structure'] = {'activities': trace_activities_multiset, 'edges': trace_edges}

        processed_cases += 1
        if processed_cases % 1000 == 0:
            print(f"Processed {processed_cases}/{total_cases} cases for grouping...")

    print(f"Found {len(variants_data)} unique variants.")

    # Format Output ---
    output_list = []
    for variant_key, data in variants_data.items():
        add_info = {
            VARIANT_FREQUENCY_KEY: data[VARIANT_FREQUENCY_KEY],
        }
        order = Graph(variant_key[0], variant_key[1], add_info)
        output_list.append(order)

    output_list.sort(
        key=lambda x: x.additional_information[VARIANT_FREQUENCY_KEY],
        reverse=True)

    return output_list
