from pm4py.objects.powl.obj import StrictPartialOrder, OperatorPOWL, POWL, Operator, SilentTransition


class TaggedGraph(StrictPartialOrder):
    skip = False
    loop = False

def detect_tagged_graphs(powl: OperatorPOWL) -> POWL:
    if powl.operator == Operator.XOR and len(powl.children) == 2:
        child_0 = powl.children[0]
        child_1 = powl.children[1]
        if isinstance(child_0, SilentTransition) and isinstance(child_1, StrictPartialOrder):
                child_1.__class__ = TaggedGraph
                child_1.skip = True
                return child_1
        if isinstance(child_1, SilentTransition) and isinstance(child_0, StrictPartialOrder):
            child_1.__class__ = TaggedGraph
            child_1.skip = True
            return child_1
    if powl.operator == Operator.LOOP:
        do = powl.children[0]
        redo = powl.children[1]
        if isinstance(redo, SilentTransition) and isinstance(do, StrictPartialOrder):
            do.__class__ = TaggedGraph
            do.loop = True
            return do
        if isinstance(do, SilentTransition) and isinstance(redo, StrictPartialOrder):
            redo.__class__ = TaggedGraph
            redo.skip = True
            redo.loop = True
            return redo

    return powl