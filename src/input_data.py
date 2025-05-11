import pandas as pd
import logging
from typing import Dict, Tuple
from .utils import enums
from . import domain_object as do
from .utils import field as fd
from .utils import header


class InputData:
    def __init__(
            self,
            exe_folder: str
    ):
        self.exe_folder = exe_folder
        # 基本信息
        self.material_dict: Dict[str, do.Material] = dict()
        self.chemical_compound_dict: Dict[str, do.ChemicalCompound] = dict()

    def read_chemical_compound_df(self):
        cch = header.ChemicalCompoundHeader
        chemical_compound_df = pd.read_excel(
            '{}{}'.format(self.exe_folder, fd.ROCK_FILENAME)
            , sheet_name=fd.CHEMICAL_COMPOUND_SHEET
        )
        chemical_compound_df = chemical_compound_df.dropna(subset=[cch.chemical_compound_name])
        return chemical_compound_df

    def load_chemical_compound_dict(self):
        cch = header.ChemicalCompoundHeader
        chemical_compound_df = self.read_chemical_compound_df()

        chemical_compound_dict = dict()
        for _, row in chemical_compound_df.iterrows():
            if row[cch.chemical_compound_name] not in enums.CHEMICAL_COMPONENT_LT:
                continue
            chemical_compound = do.ChemicalCompound(
                chemical_compound_name=row[cch.chemical_compound_name],
                low_bound=row[cch.low_bound],
                up_bound=row[cch.up_bound]
            )
            chemical_compound_dict[row[cch.chemical_compound_name]] = chemical_compound
        self.chemical_compound_dict = chemical_compound_dict
        logging.info("{}".format(len(chemical_compound_dict)))

    def read_material_df(self):
        mh = header.MaterialHeader
        material_df = pd.read_excel(
            '{}{}'.format(self.exe_folder, fd.ROCK_FILENAME)
            , sheet_name=fd.MATERIAL_SHEET
        )
        material_df = material_df.dropna(
            subset=[mh.material_name]
        )
        return material_df

    def load_material_dict(self):
        mh = header.MaterialHeader

        material_df = self.read_material_df()

        material_dict = dict()
        for _, row in material_df.iterrows():
            material = do.Material(
                material_name=row[mh.material_name],
                wet_price=row[mh.wet_price],
                low_bound=row[mh.low_bound],
                up_bound=row[mh.up_bound],
            )
            for chemical_compound_name in enums.CHEMICAL_COMPONENT_LT:
                material.chemical_compound_content[chemical_compound_name] = row[chemical_compound_name]
            material_dict[material.material_name] = material

        self.material_dict = material_dict
        logging.info("{}".format(len(material_dict)))

    def read_data(self):
        self.load_chemical_compound_dict()
        self.load_material_dict()
