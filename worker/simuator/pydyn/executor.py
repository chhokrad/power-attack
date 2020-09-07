import warnings
from decimal import *
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
        for a in to_be_executed:
            self.next_invocation[a] = self.t + self.automata[a].step(vprev, events)
        for a in to_be_executed:
            self.automata[a].update_interfaces()
        
        self.t = self.t + step
        # print(self.t, step)
        return events
        
