# src/loop_miner_between_debug.py
from collections import defaultdict, deque
from src.objects       import LOOP, ActivityInstance, Graph, VARIANT_FREQUENCY_KEY

class LoopMinerBetween:

    @classmethod
    def find_loops(cls, graph: Graph):
        # ─── 0) Precompute global label-successors / predecessors ────────────────
        global_succ = defaultdict(set)
        global_pred = defaultdict(set)
        all_labels  = set()
        for s, t in graph.edges:
            if isinstance(s, ActivityInstance) and isinstance(t, ActivityInstance):
                global_succ[s.label].add(t.label)
                global_pred[t.label].add(s.label)
                all_labels |= {s.label, t.label}

        # global start/end labels (no incoming / no outgoing in the full DFG)
        global_start = {l for l in all_labels if not global_pred[l]}
        global_end   = {l for l in all_labels if not global_succ[l]}

        # ─── 1) sort instances by their .number ───────────────────────────────────
        insts = [n for n in graph.nodes if isinstance(n, ActivityInstance)]
        insts.sort(key=lambda x: x.number)

        # ─── 2) build raw "between-first-last" label sets ────────────────────────
        label_to_insts = defaultdict(list)
        for inst in insts:
            label_to_insts[inst.label].append(inst)

        raw_sets = []
        for lbl, lst in label_to_insts.items():
            if len(lst) < 2:
                continue
            first, last = lst[0], lst[-1]
            between = {first.label, last.label}
            for inst in insts:
                if first.number < inst.number < last.number:
                    between.add(inst.label)
            raw_sets.append(between)

        # ─── 3) merge any overlapping sets ───────────────────────────────────────
        merged = []
        for s in raw_sets:
            placed = False
            for m in merged:
                if m & s:
                    m |= s
                    placed = True
                    break
            if not placed:
                merged.append(set(s))

        changed = True
        while changed:
            changed = False
            new_merged = []
            while merged:
                grp = merged.pop()
                for other in merged:
                    if grp & other:
                        merged.remove(other)
                        grp |= other
                        changed = True
                        break
                new_merged.append(grp)
            merged = new_merged

        # ─── 4) attempt a loop‐cut on each merged label‐set ──────────────────────
        final_mapping    = {}
        final_frequencies = {}
        for label_set in merged:
            print(f"\n=== Trying labels: {label_set} ===")
            mapping, freqs = cls._mine_on_labels(
                graph, label_set, global_start, global_end
            )
            final_mapping   .update(mapping)
            final_frequencies.update(freqs)

        # ─── 5) identity‐map untouched nodes ─────────────────────────────────────
        for n in graph.nodes:
            if n not in final_mapping:
                final_mapping[n] = n

        return final_mapping, final_frequencies


    @classmethod
    def _mine_on_labels(cls, graph, labels, global_start, global_end):
        """
        Try a traditional redo-loop cut on the DFG induced by `labels`.
        On failure, peel off the single highest-frequency label and retry.
        """
        def build_dfg(lbls):
            dfg_freq = defaultdict(int)
            succ     = defaultdict(set)
            pred     = defaultdict(set)

            for s in graph.nodes:
                for t in graph.nodes:
                    if not (t, s) in graph.edges and (isinstance(s, ActivityInstance)
                        and isinstance(t, ActivityInstance)
                        and s.label in lbls
                        and t.label in lbls):
                        w = graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)
                        dfg_freq[(s.label, t.label)] += w
                        succ[s.label].add(t.label)
                        pred[t.label].add(s.label)
            return dfg_freq, succ, pred

        active     = set(labels)
        peeled     = set()

        while len(active) >= 2:
            dfg_freq, succ_lbl, pred_lbl = build_dfg(active)

            A_start = active & global_start
            A_end   = active & global_end
            A1      = A_start | A_end
            A2      = active - A1

            print(f" Active={active}")
            print(f"  A_start={A_start}, A_end={A_end}")
            print(f"  A1={A1}, A2={A2}")

            if A2 and cls._check_loop_cut(
                succ_lbl, pred_lbl, A_start, A_end, A1, A2
            ):
                print("  -> loop-cut ACCEPTED")
                # carve out instances
                body_nodes = {n for n in graph.nodes
                              if isinstance(n, ActivityInstance)
                                 and n.label in A1}
                redo_nodes = {n for n in graph.nodes
                              if isinstance(n, ActivityInstance)
                                 and n.label in A2}

                body_edges = {(s,t) for (s,t) in graph.edges
                              if s in body_nodes and t in body_nodes}
                redo_edges = {(s,t) for (s,t) in graph.edges
                              if s in redo_nodes and t in redo_nodes}

                body = Graph(
                    nodes=frozenset(body_nodes),
                    edges=frozenset(body_edges),
                    additional_information={
                        VARIANT_FREQUENCY_KEY:
                          graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)
                    }
                )
                redo = Graph(
                    nodes=frozenset(redo_nodes),
                    edges=frozenset(redo_edges),
                    additional_information={
                        VARIANT_FREQUENCY_KEY:
                          graph.additional_information.get(VARIANT_FREQUENCY_KEY, 1)
                    }
                )
                loop_node = LOOP(body=body, redo=redo)

                freq = sum(w for ((u,v), w) in dfg_freq.items() if u in A2 and v in A1)

                mapping = {}
                for n in graph.nodes:
                    if isinstance(n, ActivityInstance) and n.label in A2:
                        mapping[n] = loop_node
                    else:
                        mapping[n] = n

                return mapping, {loop_node: freq}

            # reject → peel off highest‐freq label
            print("  -> loop-cut REJECTED; peeling one label")
            freq_by_label = defaultdict(int)
            for (u,v), w in dfg_freq.items():
                freq_by_label[u] += w
                freq_by_label[v] += w

            if "Repair (Complex)" in freq_by_label.keys():
                drop = "Repair (Complex)"
            else:
                drop = max(freq_by_label, key=lambda l: freq_by_label[l])
            print(f"DFG: {dfg_freq}")
            print(f"    peeling: {drop} (freq={freq_by_label[drop]})")
            active.remove(drop)
            peeled.add(drop)

        print("  -> no loop found.")
        return {}, {}


    @staticmethod
    def _check_loop_cut(succ, pred, A_start, A_end, A1, A2):
        # (a) A1→A2 only from A_end
        for a in A1:
            for b in succ[a]:
                if b in A2 and a not in A_end:
                    print(f"    fail a→b rule: {a}→{b}")
                    return False

        # (b) A2→A1 only into A_start
        for b in A2:
            for a in succ[b]:
                if a in A1 and a not in A_start:
                    print(f"    fail b→a rule: {b}→{a}")
                    return False

        # (c) no edges within A2
        for x in A2:
            for y in A2:
                if x!=y and (y in succ[x] or x in succ[y]):
                    print(f"    fail internal-A2 rule: {x}↔{y}")
                    return False

        # (d) uniform arcs from A_end→A2
        for b in A2:
            preds = {p for p in pred[b] if p in A_end}
            if preds and preds != A_end:
                print(f"    fail uniform-end→A2 on {b}: preds={preds}")
                return False

        # (e) uniform arcs from A2→A_start
        for b in A2:
            succs = {s for s in succ[b] if s in A_start}
            if succs and succs != A_start:
                print(f"    fail uniform-A2→start on {b}: succs={succs}")
                return False

        return True


    @classmethod
    def apply_mapping(cls, graph: Graph, mapping: dict, loops_freq: dict):
        from src.loop_miner import LoopMiner as Legacy
        return Legacy.apply_mapping(graph, mapping, loops_freq)
