import warnings
from decimal import *
from worker.simulator.pydyn.protection import EventInjector
getcontext().prec = 6

class Executor(object):
    def __init__(self, automata_list):
        self.t = Decimal(0)
        self.automata = {a.label : a for a in automata_list}
        self.next_invocation = {a : Decimal(0) for a in self.automata}
        # print(self.next_invocation)
    def process_timestep(self, step, vprev, events):
        # print("time inside executor {}".format(self.t))
        to_be_executed = []
        missed_execution = []
        for a in self.next_invocation:
            if (self.next_invocation[a] == self.t):
                to_be_executed.append(a)
                print("Evaluating {}".format(a))
            elif (self.next_invocation[a] < self.t):
                missed_execution.append(a)
            else :
                pass
        for a in missed_execution:
            warnings.warn("Missed Execution step for automaton {}, and thus suspending further operation".format(a))
        # Moving EventInjector in front
        index = [i for i, val in enumerate(to_be_executed)if isinstance(val, EventInjector)]
        if len(index) > 0:
            injector = to_be_executed.pop(index[0])
            to_be_executed.insert(0, injector)
        
        for a in to_be_executed:
            next_inv = self.automata[a].step(vprev, events)
            if next_inv is None:
                if a in self.next_invocation.keys():
                    del self.next_invocation[a]
                else:
                    pass
            else:
                self.next_invocation[a] = self.t + next_inv
        for a in to_be_executed:
            self.automata[a].update_interfaces()
        
        self.t = self.t + step
        # print(self.t, step)
        return events
        
