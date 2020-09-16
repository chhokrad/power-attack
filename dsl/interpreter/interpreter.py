from pypower import loadcase
from textx import metamodel_from_file
import warnings

class Interpreter(object):
    def __init__(self, meta_model):
        # TODO check if file exists
        self.meta_model = metamodel_from_file(meta_model)

    def get_setup_config(self):
        for config in self.sample_model.setup_configs:
            kind = config.__class__.__name__
            if kind == "Breaker_config":
                self.get_breaker_config(config)
            elif kind == "Relay_config":
                self.get_relay_config(config)
            elif kind == "Controller_config":
                self.get_controller_config
            elif kind == "Tracer_config":
                self.get_tracer_config(config)
            elif kind == "Generator_config":
                self.get_generator_config(config)
            elif kind == "Simulator_config":
                self.get_simulator_config(config)
            else:
                warnings.warn("Ignoring config type {}".format(kind))
    

    def get_breaker_config(self, config):
        pass

    def get_relay_config(self, config):
        pass

    def get_controller_config(self, config):
        pass

    def get_tracer_config(self, config):
        pass

    def get_generator_config(self, config):
        pass

    def get_simulator_config(self, config):
        pass

    def get_preconditions(self):
        for precondition in self.sample_model.preconditions:
            type = precondition.__class__.__name__
            if type == "Trip_node":
                self.get_trip_events(precondition)
            elif type == "Load_change":
                self.get_load_changes(precondition)
            elif type == "Fault_injection":
                self.get_fault_injections(precondition)
            else:
                warnings.warn("Ignoring precondition type {}".format(type))

    def get_load_changes(self, precondition):
        pass

    def get_fault_injections(self, precondition):
        pass
    
    def get_trip_events(self, precondition):
        pass
    
    def get_attack_scenarios(self):
        for attack_scenario in self.sample_model.attack_scenarios:
            self.get_attack_sequence(attack_scenario)
            
    def get_attack_sequence(self, scenario):
        label = scenario.label
        print(label)
        for attack in scenario.attack_sequence:
            self.get_attack(attack)


    def get_attack(self, attack):
        type = attack.element.__class__.__name__
        time = self.extract_value(attack.time)
        if type == "Generator_attack":
            self.get_generator_attack(attack.element)
        elif type == "Breaker_attack":
            self.get_breaker_attack(attack.element)
        elif type == "Relay_attack":
            self.get_relay_attack(attack.element)
        else:
            warnings.warn("Ignoring attack type {}".format(type))

    def get_generator_attack(self, attack):
        return None

    def get_relay_attack(self, attack):
        return None

    def get_breaker_attack(self, attack):
        return None

    def extract_value(self, val):
        return None

    def parse_sample_model(self, sample_model):
        self.sample_model = self.meta_model.model_from_file(sample_model)
        # TODO check if the file exists through object processors
        # self.ppc = loadcase(self.sample_model.case_file.case_file)
        self.get_setup_config()
        self.get_preconditions()
        self.get_attack_scenarios()

if __name__ == "__main__":
    power_attack_interpreter = Interpreter(meta_model="../grammar/attack.tx")
    power_attack_interpreter.parse_sample_model(sample_model="../sample-models/test.atk")
