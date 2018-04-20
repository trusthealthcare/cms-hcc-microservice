import json
from datetime import datetime
import os

"""
    RESTful Endpoints
"""


class RafService:

    @staticmethod
    def calculate(beneficiary_in) -> object:
        beneficiary = Beneficiary(beneficiary_in['id'],
                                  beneficiary_in['sex'],
                                  beneficiary_in['dob'],
                                  beneficiary_in['originalReasonEntitlement'],
                                  beneficiary_in['ltiMedicaid'],
                                  beneficiary_in['newEnrolleeMedicaid'])
        print(beneficiary_in)
        for diagnosis in beneficiary_in['diagnosis']:
            beneficiary.add_diagnosis(Diagnosis(diagnosis['icdCode']))

        calc = RafCalculator()
        return calc.calculate(beneficiary)


"""
    Diagnosis Object to pass into the Raf Calculator. Hangs off the Beneficiary
"""


class Diagnosis:
    def __init__(self,
                 icdcode):
        super().__init__()
        self.icdcode = icdcode

    def __repr__(self):  # specifies how to display an Employee
        return str(self.icdcode)


"""
    Beneficiary Object to pass into the Raf Calculator
"""


class Beneficiary:
    def __init__(self,
                 hicno, sex, dob,
                 original_reason_entitlement=0,  # Old age and survivors benefit
                 medicaid_lti=False,
                 new_enrollee_medicaid=False,
                 dateasof=datetime.now()):
        super().__init__()
        self.hicno = hicno
        self.sex = sex
        self.dob = datetime.strptime(dob, "%Y%m%d")
        self.age = self.age_as_of(self.dob, dateasof)
        self.medicaid_lti = medicaid_lti
        self.new_enrollee_medicaid = new_enrollee_medicaid
        self.original_reason_entitlement = original_reason_entitlement
        self.diagnoses = []

    def __repr__(self):  # specifies how to display an Employees
        return "ID:" + str(self.hicno) + ",DOB:" + str(self.dob) + ",Diagnosis:" + str(self.diagnoses)

    @staticmethod
    def age_as_of(dob, date_as_of):
        return date_as_of.year - dob.year - ((date_as_of.month, date_as_of.day) < (dob.month, dob.day))

    def add_diagnosis(self, diagnosis):
        self.diagnoses.append(diagnosis)


"""
    This is a python port of the CMS-HCC Risk Adjustment Model
"""


class RafCalculator:

    """
        Initialize all parameters
    """
    def __init__(self):
        directory = os.path.dirname(__file__)
        fh = open(os.path.join(directory, "data.json"), 'r')
        self.data = json.loads(fh.read())
        fh.close()

        self.entitlement_reason_map = {}
        for entitlement_reason in self.data["entitlementReason"]:
            self.entitlement_reason_map[entitlement_reason] = \
                self.data["entitlementReason"][entitlement_reason]["value"]

    """
        Primary method to execute calculation
    """
    def calculate(self, beneficiary: Beneficiary) -> object:
        attributes = {}
        invalid = {}

        # For each diagnosis
        # 1. Check for any medicare code edits.
        # 2. Map the ICD10 code to an HCC code.
        for diagnosis in beneficiary.diagnoses:
            has_edit = self.__edit_update(beneficiary, diagnosis, attributes, invalid)
            # If no simple edits, do regular
            if not has_edit:
                self.__icd10_hcc_map(diagnosis, attributes, invalid)

        sex = "M" if beneficiary.sex == 1 else "F"

        # 3. Identify the age range for a raf calculation.  There is a slight variation for new enrollees.
        age_range = self.__identify_age_range(beneficiary.age)
        if beneficiary.age < 64 or beneficiary.age > 69 or (
                beneficiary.age == 64 and
                beneficiary.original_reason_entitlement != self.entitlement_reason_map["OASI"]):
            ne_age_range = age_range
        # This edge case is allowed on purpose: beneficiary.age == 64 and beneficiary.original_reason_entitlement == 0:
        else:
            ne_age_range = str(beneficiary.age)

        self.__add_demographic((sex + age_range), attributes)

        # 4. Determine if the patient is disabled or was disabled in the past
        disabled = True if \
            (beneficiary.age < 65 and beneficiary.original_reason_entitlement != self.entitlement_reason_map["OASI"]) \
            else False
        originally_disabled = True if \
            (beneficiary.original_reason_entitlement == self.entitlement_reason_map["DIB"] and not disabled) \
            else False

        # 5.  Add Demographics if the patient is a new enrollee.
        if not beneficiary.new_enrollee_medicaid:
            if beneficiary.age >= 65 and beneficiary.original_reason_entitlement == self.entitlement_reason_map["DIB"]:
                self.__add_demographic("NMCAID_ORIGDIS_NE" + sex + ne_age_range, attributes)
            else:
                self.__add_demographic("NMCAID_NORIGDIS_NE" + sex + ne_age_range, attributes)
        else:
            if beneficiary.age >= 65 and beneficiary.original_reason_entitlement == self.entitlement_reason_map["DIB"]:
                self.__add_demographic("MCAID_ORIGDIS_NE" + sex + ne_age_range, attributes)
            else:
                self.__add_demographic("MCAID_NORIGDIS_NE" + sex + ne_age_range, attributes)

        # 6. Add Demographics if a Long Term Institutionalized Patient or originally disabled but no longer.
        if beneficiary.medicaid_lti:
            self.__add_demographic("LTIMCAID", attributes)
        if disabled:
            self.__add_demographic("ORIGDS", attributes)

        # 7. Add interactions if they were originally disabled.
        if originally_disabled:
            if beneficiary.sex == 2:
                self.__add_interaction("OriginallyDisabled_Female", attributes)
            if beneficiary.sex == 1:
                self.__add_interaction("OriginallyDisabled_Male", attributes)

        # 8. Disable HCC's that are of lower acuity
        for disableCode in self.data["hierarchies"]:
            for key in attributes:
                if disableCode["hcc"] == key and attributes[key]["type"] == "code" and attributes[key]["valid"]:
                    for hcc in disableCode["invalidHcc"]:
                        if hcc in attributes:
                            attributes[hcc]["valid"] = False

        # 9. Create diagnostic category
        diag_cat = self.__create_categories(attributes)

        # 10. Create community models interactions
        self.__create_community_interactions(attributes, diag_cat)

        # 11. Create institutional interactions;
        self.__create_institutional_interactions(attributes, disabled, diag_cat)

        # 12.  Calculate Scores
        for attribute_name in attributes:
            for model in self.data["models"]:
                self.__calculate_attribute_score(
                    attribute_name, attributes[attribute_name], model["prefix"], model["name"])

        # 13. Calculate Totals
        totals = {}
        for model in self.data["models"]:
            total = 0
            for attribute_name in attributes:
                total += attributes[attribute_name]["coefficients"][model["name"]]
            totals[model["name"]] = total

        # 14. Done!
        return {"totals": totals, "invalid": invalid, "attributes": attributes}

    """
        Do all necessary MCE Edits 
        This is the same functionality as V22I0ED2 macro
    """
    def __edit_update(self, beneficiary, diagnosis, attributes, invalid):
        short_circuit = False
        # Do the simple edits.
        if beneficiary.sex == 2 and (diagnosis.icdcode == "D66" or diagnosis.icdcode == "D67"):
            self.__add_code(attributes, 48, diagnosis.icdcode)
            short_circuit = True
        elif beneficiary.age < 18 and diagnosis.icdcode in self.data["ageIcdCheck"]:
            self.__add_code(attributes, 112, diagnosis.icdcode)
            short_circuit = True
        elif (beneficiary.age < 6 or beneficiary.age > 18) and diagnosis.icdcode == "F3481":
            invalid[diagnosis.icdcode] = "This is only valid for children between 7 and 17"
            short_circuit = True

        if diagnosis.icdcode in self.data["sexEdits"] and self.data["sexEdits"][diagnosis.icdcode] != beneficiary.sex:
            invalid[diagnosis.icdcode] = "This is only valid for the opposite sex"
            short_circuit = True

        if diagnosis.icdcode in self.data["ageEdits"]:
            age_code = self.data["ageEdits"][diagnosis.icdcode]
            if age_code == 0 and beneficiary.age != 0:
                invalid[diagnosis.icdcode] = "This is only valid for newborns (0 yo)"
                short_circuit = True
            elif age_code == 1 and beneficiary.age > 17:
                invalid[diagnosis.icdcode] = "This is only valid for pediatric (0 - 17 yo)"
                short_circuit = True
            elif age_code == 2 and (beneficiary.age < 12 or beneficiary.age > 55):
                invalid[diagnosis.icdcode] = "This is only valid for maternity (12 - 55 yo)"
                short_circuit = True
            elif age_code == 3 and beneficiary.age < 15:
                invalid[diagnosis.icdcode] = "This is only valid for adults (15+ yo)"
                short_circuit = True
        return short_circuit

    """
        Map ICD10 codes to HCC
    """
    def __icd10_hcc_map(self, diagnosis, attributes, invalid):
        if diagnosis.icdcode in self.data["icd10"]:
            # Technically, the SAS code only supports 3.  We go through whatever exists.
            for hcc in self.data["icd10"][diagnosis.icdcode]:
                self.__add_code(attributes, ("HCC" + hcc), diagnosis.icdcode)
        else:
            invalid[diagnosis.icdcode] = "This code does not map to a medicare HCC code"

    """
        Create the age range for the coefficients.  Maintained same style as SAS code.
    """
    @staticmethod
    def __identify_age_range(age):
        if 0 <= age <= 34:
            age = "0_34"
        elif 34 < age <= 44:
            age = "35_44"
        elif 44 < age <= 54:
            age = "45_54"
        elif 54 < age <= 59:
            age = "55_59"
        elif 59 < age <= 64:
            age = "60_64"
        elif 64 < age <= 69:
            age = "65_69"
        elif 69 < age <= 74:
            age = "70-74"
        elif 74 < age <= 79:
            age = "75-79"
        elif 79 < age <= 84:
            age = "80-84"
        elif 84 < age <= 89:
            age = "85-89"
        elif 89 < age <= 94:
            age = "90-94"
        elif age > 94:
            age = "95_GT"
        return age

    """
        High level condition categories based on multiple HCC codes.  
        Used for creating the interactions
    """
    def __create_categories(self, attributes):
        diag_cat = dict()
        diag_cat["cancer"] = self.__has_hcc(["HCC8", "HCC9", "HCC10", "HCC11", "HCC12"], attributes)
        diag_cat["diabetes"] = self.__has_hcc(["HCC17", "HCC18", "HCC19"], attributes)
        diag_cat["card_resp_fail"] = self.__has_hcc(["HCC82", "HCC83", "HCC84"], attributes)
        diag_cat["chf"] = self.__has_hcc(["HCC85"], attributes)
        diag_cat["g_copd_cf"] = self.__has_hcc(["HCC110", "HCC111", "HCC112"], attributes)
        diag_cat["renal"] = self.__has_hcc(["HCC134", "HCC135", "HCC136", "HCC137"], attributes)
        diag_cat["sepsis"] = self.__has_hcc(["HCC2"], attributes)
        diag_cat["g_substance_abuse"] = self.__has_hcc(["HCC54", "HCC55"], attributes)
        diag_cat["g_psychiatric"] = self.__has_hcc(["HCC57", "HCC58"], attributes)
        return diag_cat

    """
        Community level interactions
    """
    def __create_community_interactions(self, attributes, diag_cat):
        if "HCC47" in attributes and diag_cat["cancer"]:
            self.__add_interaction("HCC47_gCancer", attributes)
        if "HCC85" in attributes and diag_cat["diabetes"]:
            self.__add_interaction("HCC85_gDiabetesMellit", attributes)
        if "HCC85" in attributes and diag_cat["g_copd_cf"]:
            self.__add_interaction("HCC85_gCopdCF", attributes)
        if "HCC85" in attributes and diag_cat["renal"]:
            self.__add_interaction("HCC85_gRenal", attributes)
        if diag_cat["card_resp_fail"] and diag_cat["g_copd_cf"]:
            self.__add_interaction("gRespDepandArre_gCopdCF", attributes)
        if "HCC85" in attributes and "HCC96" in attributes:
            self.__add_interaction("HCC85_HCC96", attributes)
        if diag_cat["g_substance_abuse"] and diag_cat["g_psychiatric"]:
            self.__add_interaction("gSubstanceAbuse_gPsychiatric", attributes)

    """
        Institutional level interactions
    """
    def __create_institutional_interactions(self, attributes, disabled, diag_cat):
        pressure_ulcer = self.__has_hcc(["HCC157", "HCC158"], attributes)
        if diag_cat["chf"] and diag_cat["g_copd_cf"]:
            self.__add_interaction("CHF_gCopdCF", attributes)
        if diag_cat["g_copd_cf"] and diag_cat["card_resp_fail"]:
            self.__add_interaction("gCopdCF_CARD_RESP_FAIL", attributes)
        if diag_cat["sepsis"] and diag_cat["pressure_ulcer"]:
            self.__add_interaction("SEPSIS_PRESSURE_ULCER", attributes)
        if diag_cat["sepsis"] and "HCC188" in attributes:
            self.__add_interaction("SEPSIS_ARTIF_OPENINGS", attributes)
        if "HCC188" in attributes and pressure_ulcer:
            self.__add_interaction("ART_OPENINGS_PRESSURE_ULCER", attributes)
        if diag_cat["diabetes"] and diag_cat["chf"]:
            self.__add_interaction("DIABETES_CHF", attributes)
        if diag_cat["g_copd_cf"] and "HCC114" in attributes:
            self.__add_interaction("gCopdCF_ASP_SPEC_BACT_PNEUM", attributes)
        if "HCC114" in attributes and pressure_ulcer:
            self.__add_interaction("ASP_SPEC_BACT_PNEUM_PRES_ULC", attributes)
        if diag_cat["sepsis"] and attributes in "HCC114":
            self.__add_interaction("SEPSIS_ASP_SPEC_BACT_PNEUM", attributes)
        if "HCC57" in attributes and diag_cat["g_copd_cf"]:
            self.__add_interaction("SCHIZOPHRENIA_gCopdCF", attributes)
        if "HCC57" in attributes and diag_cat["chf"]:
            self.__add_interaction("SCHIZOPHRENIA_CHF", attributes)
        if "HCC57" in attributes and "HCC79" in attributes:
            self.__add_interaction("SCHIZOPHRENIA_SEIZURES", attributes)

        if disabled:
            if "HCC85" in attributes:
                self.__add_interaction("DISABLED_HCC85", attributes)
            if pressure_ulcer:
                self.__add_interaction("DISABLED_PRESSURE_ULCER", attributes)
            if "HCC161" in attributes:
                self.__add_interaction("DISABLED_HCC161", attributes)
            if "HCC39" in attributes:
                self.__add_interaction("DISABLED_HCC39", attributes)
            if "HCC77" in attributes:
                self.__add_interaction("DISABLED_HCC77", attributes)
            if "HCC6" in attributes:
                self.__add_interaction("DISABLED_HCC6", attributes)

    @staticmethod
    def __add_code(attributes, hcc, icd_code):
        if hcc not in attributes:
            attributes[hcc] = {"valid": True, "type": "code", "list": [], "coefficients": {}}
        if icd_code not in attributes[hcc]["list"]:
            attributes[hcc]["list"].append(icd_code)

    @staticmethod
    def __add_interaction(interaction, attributes):
        attributes[interaction] = {"valid": True, "type": "interaction", "coefficients": {}}

    @staticmethod
    def __add_demographic(demographic, attributes):
        attributes[demographic] = {"valid": True, "type": "demographic", "coefficients": {}}

    @staticmethod
    def __has_hcc(hcc_codes, attributes):
        for hcc in hcc_codes:
            if hcc in attributes and attributes[hcc]['valid']:
                return True
        return False

    """
        Adds each coefficient for each model to the attribute.  
        If the attribute doesn't have a score, it is set to zero
    """
    def __calculate_attribute_score(self, attribute_name, attribute, prefix, description):
        coef_name = (prefix + "_" + attribute_name)
        if coef_name in self.data["coefficients"]:
            attribute["coefficients"][description] = self.data["coefficients"][coef_name]["value"]
            # TODO Move this upstream to the attribute and not on the coefficient
            attribute["description"] = self.data["coefficients"][coef_name]["description"]
        else:
            attribute["coefficients"][description] = 0.0
