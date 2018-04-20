from flask_injector import inject
from services.raf import RafService, Beneficiary


@inject
def calculate(calc : RafService, beneficiary) -> object:
    return calc.calculate(beneficiary)