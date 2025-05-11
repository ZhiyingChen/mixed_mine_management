from typing import Tuple


class ChemicalCompound:
    def __init__(
            self,
            chemical_compound_name: str,
            low_bound: float,
            up_bound: float
    ):
        self.chemical_compound_name: str = chemical_compound_name
        # 约束
        self.ratio_bounds: Tuple[float, float] = (low_bound, up_bound)

    def __str__(self):
        return f"{self.chemical_compound_name} {self.ratio_bounds}"