from pypower import loadcase
from textx import metamodel_from_file
import warnings
import pprint

class Interpreter(object):
    def __init__(self, meta_model):
        # TODO check if file exists

        # type of value is tuple size 2 -> scalar
        # type of value is tuple size 3 -> p_scalar
        # type of value is list size 2 -> vector
        self.meta_model = metamodel_from_file(meta_model)
        self.params = {}
        self.breaker_params = {}
        self.relay_params = {}
        self.controller_params = {}
        self.generator_params = {}
        self.simulation_params = {}

    def get_setup_config(self):
        for config in self.sample_model.setup_configs:
            kind = config.__class__.__name__
            if kind == "Breaker_config":
                self.get_breaker_config(config)
            elif kind == "Relay_config":
                self.get_relay_config(config)
            elif kind == "Controller_config":
                self.get_controller_config(config)
            elif kind == "Tracer_config":
                self.get_tracer_config(config)
            elif kind == "Generator_config":
                self.get_generator_config(config)
            elif kind == "Simulator_config":
                self.get_simulator_config(config)
            else:
                warnings.warn("Ignoring config type {}".format(kind))
    

    def get_breaker_config(self, config):
        from_bus = config.id.from_bus.id
        to_bus = config.id.to_bus.id
        label = "PA_BR_{}_{}".format(from_bus, to_bus)
        params = self.extract_params(config.params)
        for key in params:
            self.breaker_params[label+"_{}".format(key)] = params[key]
        
        
    def get_relay_config(self, config):
        from_bus = config.id.from_bus.id
        to_bus = config.id.to_bus.id
        type = "DR" 
        if config.type == "over-current":
            type = "OR"
        label = "PA_{}_{}_{}".format(type, from_bus, to_bus)
        params = self.extract_params(config.params)
        for key in params:
            self.relay_params[label+"_{}".format(key)] = params[key]

    def get_controller_config(self, config):
        bus = config.id.id
        label = "LFC_{}".format(bus)
        params = self.extract_params(config.params)
        for key in params:
            self.controller_params[label+"_{}".format(key)] = params[key]

    def get_tracer_config(self, config):
        self.params['Tracer'] = config.metrics

    def get_generator_config(self, config):
        bus = config.id.id
        label = "GEN_{}".format(bus)
        params = self.extract_params(config.params)
        for key in params:
            self.generator_params[label+"_{}".format(key)] = params[key]

    def get_simulator_config(self, config):
        label = "SIM"
        params = self.extract_params(config.params)
        for key in params:
            self.simulation_params[label+"_{}".format(key)] = params[key]

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
        # value should be a tuple ()
        # first element is actual value, second is whether is random or not
        # actual value can be scalar or a vector
        # in case of scalar -> (x, false)
        # in case of vector -> ([x,y], false)
        # in case of random scalar -> ([dist, params], false)
        # in case of random vector -> [(x, false), ([dist, params], true)]
        #                          -> [([dist, params], true), ([dist, params], true)]
        type = val.__class__.__name__
        if type == "Probablistic_scalar":
            return (True, [val.distribution, self.extract_params(val.params)])
        elif type == "Vector":
            return [self.extract_value(val.real), self.extract_value(val.imag)]
        else:
            return (False, val) 
    
    def extract_params(self, params):
        params_dict = {}
        for keyval in params:
            x = keyval.key
            params_dict[x] = self.extract_value(keyval.val)
        return params_dict

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
    pp = pprint.PrettyPrinter(depth=4)
    pp.pprint(power_attack_interpreter.breaker_params)
    print("-"*150)
    pp.pprint(power_attack_interpreter.relay_params)
    print("-"*150)
    pp.pprint(power_attack_interpreter.controller_params)
    print("-"*150)
    pp.pprint(power_attack_interpreter.params['Tracer'])
    print("-"*150)
    pp.pprint(power_attack_interpreter.simulation_params)
    print("-"*150)
    pp.pprint(power_attack_interpreter.generator_params)

