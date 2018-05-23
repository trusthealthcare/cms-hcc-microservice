import unittest
from services.raf import Beneficiary, Diagnosis, RafCalculator, RafService
from datetime import datetime
from openpyxl import load_workbook


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

    def testSasCompare(self):
        print("Test Sas Compare")
        wb = load_workbook('../test_data/unit-test.xlsx', data_only=True)
        data_name = wb['data']
        result_sheet = wb['results']

        row = 2
        calc = RafCalculator()
        while True:
            if not data_name['A' + str(row)].value:
                break
            beneficiary = Beneficiary(data_name['A' + str(row)].value,
                                      data_name['B' + str(row)].value,
                                      data_name['C' + str(row)].value,
                                      data_name['D' + str(row)].value,
                                      data_name['E' + str(row)].value,
                                      data_name['F' + str(row)].value,
                                      datetime.strptime("20180201", "%Y%m%d")
                                      )
            for i in ['G', 'H', 'I','J','K', 'L', 'M', 'N', 'O', 'P']:
                if data_name[i + str(row)].value != '':
                    beneficiary.add_diagnosis(Diagnosis(data_name[i + str(row)].value))

            results = calc.calculate(beneficiary)
            # 5 is an arbitrary large enough number to round.  avoids trailing 0000001.
            assert round(results['totals']['Community NA'], 5) == result_sheet['HP' + str(row)].value
            assert round(results['totals']['Community ND'], 5) == result_sheet['HQ' + str(row)].value
            assert round(results['totals']['Community FBA'], 5) == result_sheet['HR' + str(row)].value
            assert round(results['totals']['Community FBD'], 5) == result_sheet['HS' + str(row)].value
            assert round(results['totals']['Community PBA'], 5) == result_sheet['HT' + str(row)].value
            assert round(results['totals']['Community PBD'], 5) == result_sheet['HU' + str(row)].value
            assert round(results['totals']['Institutional'], 5) == result_sheet['HV' + str(row)].value
            assert round(results['totals']['New Enrollee'], 5) == result_sheet['HW' + str(row)].value
            assert round(results['totals']['SNP New Enrollee'], 5) == result_sheet['HX' + str(row)].value

            print(row)
            row += 1
        assert True


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
