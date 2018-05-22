import unittest
from services.raf import Beneficiary, Diagnosis, RafCalculator, RafService
from datetime import datetime


# TODO Improve this
class CalculatorTestCase(unittest.TestCase):

    def setUp(self):
        print("setup")

    def tearDown(self):
        print("teardown")

    # TODO write this properly
    def testCalculator(self):
        jane = Beneficiary(2, "female", datetime.strptime("19740824", "%Y%m%d"), 1, True)
        jane.add_diagnosis(Diagnosis("D66"))
        jane.add_diagnosis(Diagnosis("C182"))
        jane.add_diagnosis(Diagnosis("C638"))
        jane.add_diagnosis(Diagnosis("C9330"))
        jane.add_diagnosis(Diagnosis("I071"))

        daniel = Beneficiary(1, "male", datetime.strptime("19530824", "%Y%m%d"), 0)
        daniel.add_diagnosis(Diagnosis("A0223"))  # 51
        daniel.add_diagnosis(Diagnosis("A0224"))  # 52
        daniel.add_diagnosis(Diagnosis("D66"))
        daniel.add_diagnosis(Diagnosis("C163"))
        daniel.add_diagnosis(Diagnosis("C163"))
        daniel.add_diagnosis(Diagnosis("C182"))
        daniel.add_diagnosis(Diagnosis("C800"))
        daniel.add_diagnosis(Diagnosis("A072"))
        daniel.add_diagnosis(Diagnosis("C153"))

        no_cancer = Beneficiary(2, "female", datetime.strptime("19740824", "%Y%m%d"), 1, True)
        no_cancer.add_diagnosis(Diagnosis("D66"))
        no_cancer.add_diagnosis(Diagnosis("A3681"))
        no_cancer.add_diagnosis(Diagnosis("E0800"))

        calc = RafCalculator()
        print(calc.calculate(jane))
        print(calc.calculate(daniel))
        print(calc.calculate(no_cancer))

    def testExcel(self):
        print("here")
        RafService.calculateExcel()    


if __name__ == '__main__':
    unittest.main()


# Convert ICD10 to CC to JSON
# def load_cc_facts(f):
#   dict = {}
#   dir = os.path.dirname(__file__)
#   file = open(os.path.join(dir,f), 'r')
#   for line in file:
#     vals = line.split()
#     if vals[0] not in dict:
#         dict[vals[0]] = []
#     dict[vals[0]].append(vals[1])
#   print(json.dumps(dict))
#
# load_cc_facts("icd10.txt")
