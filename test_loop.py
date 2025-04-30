# test_loop_recursive.py

from src.objects import ActivityInstance, Graph, VARIANT_FREQUENCY_KEY, LOOP
from src.loop_miner import LoopMiner

# Build: A1 → B1 → A2 → B2 → A3
A1, A2, A3 = ActivityInstance("A",1), ActivityInstance("A",2), ActivityInstance("A",3)
B1, B2       = ActivityInstance("B",1), ActivityInstance("B",2)

nodes = frozenset({A1, B1, A2, B2, A3})
edges = frozenset({
    (A1, B1),
    (B1, A2),
    (A2, B2),
    (B2, A3),
})
g = Graph(nodes, edges, additional_information={VARIANT_FREQUENCY_KEY: 1})

print("Before recursive loop‐mining:")
print(g)

g_rec = LoopMiner.mine_recursively(g)

print("\nAfter recursive loop‐mining:")
print(g_rec)

# Sanity checks:
outer = next(n for n in g_rec.nodes if isinstance(n, type(LOOP(body=A1, redo=B1))))
assert outer.body == ActivityInstance("A",1)

# Outer redo must be a Graph containing the inner B‐loop
inner_graph = outer.redo
assert isinstance(inner_graph, Graph)

inners = [n for n in inner_graph.nodes if isinstance(n, type(outer))]
assert len(inners) == 1

inner = inners[0]
assert inner.body == ActivityInstance("B",1)
assert inner.redo == ActivityInstance(None,1)

print("✅ Nested loops found correctly!")
