import pm4py

from utils.log_to_partial_orders import VARIANT_ACTIVITIES_KEY
from pm4py.objects.powl.obj import OperatorPOWL, Transition, SilentTransition
from pm4py.objects.process_tree.obj import Operator


class SelfLoopMiner:

    @classmethod
    def find_self_loops(cls, partial_orders):

        all_activities = sorted(
            set(activity for po in partial_orders for activity in po.additional_information[VARIANT_ACTIVITIES_KEY]))
        res_dict = {}
        for a in all_activities:
            can_be_skipped = False
            loop = False
            for po in partial_orders:
                po_activities = po.additional_information[VARIANT_ACTIVITIES_KEY]
                if po_activities.count(a) == 0:
                    can_be_skipped = True
                elif po_activities.count(a) > 1:
                    loop = True

            if can_be_skipped and loop:
                res_dict[a] = OperatorPOWL(Operator.LOOP, children=[SilentTransition(), Transition(a)])
            elif can_be_skipped and not loop:
                res_dict[a] = OperatorPOWL(Operator.XOR, children=[Transition(a), SilentTransition()])
            elif not can_be_skipped and loop:
                res_dict[a] = OperatorPOWL(Operator.LOOP, children=[Transition(a), SilentTransition()])
            else:
                res_dict[a] = Transition(a)

        return res_dict

    @classmethod
    def simplify_orders_by_replacing_self_loops(cls, new_orders, mapping):
        pass

