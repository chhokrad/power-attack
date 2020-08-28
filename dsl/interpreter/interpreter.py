from textx import metamodel_from_file

class Interpreter(object):
    def __init__(self, grammar_file):
        self.meta_model = metamodel_from_file(grammar_file)
    
    def parse_sample(self, sample_model):
        self.sample_model = self.meta_model.model_from_file(sample_model)


if __name__ == '__main__':
    power_attack_inter = Interpreter('../attack.tx')
    power_attack_inter.parse_sample('../sample.atk')
    for attack in power_attack_inter.sample_model.attack_scenarios[0].attack_sequence:
        print(type(attack))
