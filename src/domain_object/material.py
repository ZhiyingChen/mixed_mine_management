from typing import Dict, Tuple
from ..utils import enums


class Material:
    def __init__(
            self,
            material_name: str,
            wet_price: float,
            low_bound: float,
            up_bound: float,
    ):
        self.material_name: str = material_name
        self.wet_price: float = wet_price
        self.chemical_compound_content: Dict[str, float] = dict()

        # 约束
        self.ratio_bounds: Tuple[float, float] = (low_bound, up_bound)

    @property
    def dry_price(self):
        return self.wet_price * (1 - self.chemical_compound_content.get(enums.ChemicalCompoundName.H2O, 0) / 100)

    def __str__(self):
        return "{} {} ({} {})".format(
            self.material_name,
            self.wet_price,
            self.ratio_bounds[0],
            self.ratio_bounds[1]
        )

