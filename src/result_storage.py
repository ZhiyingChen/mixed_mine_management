from typing import List
import openpyxl
import logging

from .input_data import InputData
from .utils import field, header, functions


class ResultStorage:
    def __init__(
        self,
        input_data: InputData,
        keys: List[str],
        result,
    ):
        self.input_data: InputData = input_data
        self.keys = keys
        self.result = result

    def write_to_excel(self):
        if not self.result.success:
            logging.error(
                "Unsuccessful solution, message: {}".format(self.result.message)
            )
        else:
            logging.info("Successful solution, message: {}".format(self.result.message))

        sh = header.MaterialHeader
        # 加载当前工作簿
        file_name = "{}{}".format(self.input_data.exe_folder, field.ROCK_FILENAME)
        wb = openpyxl.load_workbook(file_name)

        # 选择指定的 sheet
        sheet = wb[field.MATERIAL_SHEET]  # 替换为你的 sheet 名
        sheet_header_dict = functions.get_header_dict(sheet=sheet)
        # 要输出的数据
        data_to_write = dict(zip(self.keys, self.result.x))
        data_key = [
            cell.value
            for cell in sheet["A"]
            if cell.value is not None and cell.value != sh.material_name
        ]
        data_val = [data_to_write[key] for key in data_key]
        # 替换为你要写入的数据
        # 指定要写入的列（例如，第2列）
        column_index = sheet_header_dict[sh.ratio]
        # A=1, B=2, C=3, ...
        # 遍历每一行
        for row_index, value in enumerate(data_val, start=2):  # 从第1行开始
            sheet.cell(row=row_index, column=column_index, value=value)
        # 保存工作簿
        wb.save(file_name)

