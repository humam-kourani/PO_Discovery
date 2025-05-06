from pm4py.objects.powl.obj import StrictPartialOrder, Transition, OperatorPOWL, SilentTransition
from pm4py.objects.process_tree.obj import Operator
from unicodedata import normalize

VARIANT_FREQUENCY_KEY = "@@variant_frequency"
ENABLE_DUPLICATION = True


class XOR:
    def __init__(self, children: frozenset):
        """
        Initialize an XOR node.

        Args:
            children (frozenset): A frozenset of child nodes (e.g., ActivityInstance, XOR, LOOP).
        """
        if not isinstance(children, frozenset):
            raise TypeError("Children must be provided as a frozenset.")
        if len(children) < 1:
            raise ValueError("XOR must have at least one child.")
        self.children = children

    def __repr__(self):
        return f"XOR({', '.join(repr(child) for child in sorted(self.children))})"

    def __eq__(self, other):
        if isinstance(other, XOR):
            return self.children == other.children
        return False

    def __hash__(self):
        return hash(('XOR', self.children))

    def __lt__(self, other):
        if isinstance(other, XOR):
            return sorted(self.children) < sorted(other.children)
        elif isinstance(other, LOOP) or isinstance(other, Graph): # ActivityInstance < XOR < Loop < Graph
            return True
        elif isinstance(other, ActivityInstance):
            return False
        else:
            return NotImplemented

    def normalize(self):
        normalized_children = {child.normalize() for child in self.children}
        return XOR(frozenset(normalized_children))


class LOOP:
    def __init__(self, body, redo):
        """
        Initialize a LOOP node.

        Args:
            body (Any): The main body node (e.g., ActivityInstance, XOR, LOOP).
            redo (Any): The redo node (after a failed loop execution).
        """
        self.body = body
        self.redo = redo

    def __repr__(self):
        return f"LOOP(body={repr(self.body)}, redo={repr(self.redo)})"

    def __eq__(self, other):
        if isinstance(other, LOOP):
            return self.body == other.body and self.redo == other.redo
        return False

    def __hash__(self):
        return hash(('LOOP', self.body, self.redo))

    def __lt__(self, other):
        if isinstance(other, LOOP):
            return (self.body, self.redo) < (other.body, other.redo)
        elif isinstance(other, Graph): # ActivityInstance < XOR < Loop < Graph
            return True
        elif isinstance(other, XOR) or isinstance(other, ActivityInstance):
            return False
        else:
            return NotImplemented

    def normalize(self):
        normalized_body = self.body.normalize()
        normalized_redo = self.redo.normalize()
        return LOOP(normalized_body, normalized_redo)


class ActivityInstance:
    def __init__(self, label: str|None, number: int):
        """
        Initialize an ActivityInstance.

        Args:
            label (str): The label of the activity (e.g., 'A', 'Review').
            number (int): The occurrence number of this activity (e.g., 1st, 2nd instance).
        """
        if not ENABLE_DUPLICATION:
            number = 1
        if number < 1:
            raise ValueError("Activity number must be at least 1.")
        self.label = label
        self.number = number

    def __repr__(self):
        if self.number == 1:
            return f"{self.label}"
        return f"({self.label}, {self.number})"

    def __eq__(self, other):
        if isinstance(other, ActivityInstance):
            return self.label == other.label and self.number == other.number
        return False

    def __hash__(self):
        return hash((self.label, self.number))

    def __lt__(self, other):
        if isinstance(other, ActivityInstance):
            if self.label and not other.label:
                return False
            elif not self.label and other.label:
                return True
            return (self.label, self.number) < (other.label, other.number)
        # ActivityInstance < XOR < Loop < Graph
        elif isinstance(other, Graph) or isinstance(other, XOR) or isinstance(other, LOOP):
            return True
        else:
            return NotImplemented

    def normalize(self):
        return ActivityInstance(self.label, 1)


class Graph:
    def __init__(self, nodes: frozenset, edges: frozenset, additional_information=None):
        """
        Initialize a Graph Instance with nodes and edges.

        Args:
            nodes (frozenset): A frozenset of nodes (ActivityInstance, XOR, LOOP).
            edges (frozenset): A frozenset of (source, target) tuples where source and target are in nodes.
        """
        if additional_information is None:
            additional_information = {}
        if not isinstance(nodes, frozenset):
            raise TypeError("Nodes must be a frozenset.")
        if not isinstance(edges, frozenset):
            raise TypeError("Edges must be a frozenset.")
        for edge in edges:
            if not (isinstance(edge, tuple) and len(edge) == 2):
                raise ValueError(f"Each edge must be a (source, target) tuple, found: {edge}")
            if edge[0] not in nodes or edge[1] not in nodes:
                raise ValueError(f"Edge {edge} refers to nodes not in the node set.")

        self.nodes = nodes
        self.edges = edges
        self.additional_information = additional_information if additional_information else {}

    def __repr__(self):
        nodes_repr = ', '.join(sorted(map(repr, self.nodes)))
        edges_repr = ', '.join(f"{repr(src)}->{repr(tgt)}" for src, tgt in sorted(self.edges))
        return f"Graph(Nodes: {{{nodes_repr}}}, Edges: {{{edges_repr}}}, {self.additional_information})"

    def __eq__(self, other):
        if isinstance(other, Graph):
            return self.nodes == other.nodes and self.edges == other.edges
        return False

    def __hash__(self):
        return hash(('Graph', self.nodes, self.edges))

    def __lt__(self, other):
        if isinstance(other, Graph):
            return (sorted(self.nodes), sorted(self.edges)) < (sorted(other.nodes), sorted(other.edges))
        # ActivityInstance < XOR < Loop < Graph
        elif isinstance(other, XOR) or isinstance(other, ActivityInstance) or isinstance(other, LOOP):
            return False
        else:
            return NotImplemented

    def normalize(self):
        normalized_children_mapping = {node: node.normalize() for node in self.nodes}
        from src.mapping import apply_node_mapping_on_single_graph
        return apply_node_mapping_on_single_graph(self, normalized_children_mapping)


def simplified_model_to_powl(model, add_instance_number = False):
    if isinstance(model, ActivityInstance):
        if not model.label:
            return SilentTransition()
        if add_instance_number:
            label = f"({model.label}, {model.number})"
        else:
            label = model.label
        return Transition(label=label)
    elif isinstance(model, XOR):
        return OperatorPOWL(operator=Operator.XOR, children=[simplified_model_to_powl(child) for child in model.children])
    elif isinstance(model, LOOP):
        return OperatorPOWL(operator=Operator.LOOP, children=[simplified_model_to_powl(model.body), simplified_model_to_powl(model.redo)])
    elif not isinstance(model, Graph):
        raise NotImplementedError


    po = StrictPartialOrder([])
    submodels = model.nodes
    edges = model.edges

    powl_map = {}
    for submodel in submodels:
        powl_child = simplified_model_to_powl(submodel)
        powl_map[submodel] = powl_child
        po.order.add_node(powl_child)

    for m1, m2 in edges:
        po.add_edge(powl_map[m1], powl_map[m2])

    len_all = len(po.order.nodes)

    start_len = len(po.order.get_start_nodes())
    if start_len > 1 and start_len != len_all:
        start = SilentTransition()
        po.order.add_node(start)
        for node in set(po.order.nodes) - {start}:
            po.add_edge(start, node)

    end_len = len(po.order.get_end_nodes())
    if end_len > 1 and end_len != len_all:
        end = SilentTransition()
        po.order.add_node(end)
        for node in set(po.order.nodes) - {end}:
            po.add_edge(node, end)

    # po.order.add_transitive_edges

    if not po.order.is_irreflexive():
        raise ValueError('Not irreflexive!')

    if not po.order.is_transitive():
        raise ValueError('Not transitive!')

    return po