from flask_injector import inject
from services.raf import RafService, Beneficiary
from flask import Response, stream_with_context
from openpyxl.writer.excel import save_virtual_workbook

@inject
def calculate(calc : RafService, beneficiary) -> object:
    return calc.calculate(beneficiary)

@inject
def calculate_excel(calc: RafService, excel) -> object:
    excel_response = calc.calculate_excel(excel)
    return save_virtual_workbook(excel_response)
    # response = Response()
    # response.headers['Content-Disposition'] = 'attachment;filename=results-new.xlsx'
    # response.mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    # return response
    # return send_file(calc.calculate_excel(excel), attachment_filename='testNew.xslx',
    #                  mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
