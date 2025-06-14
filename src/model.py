import numpy as np
from scipy.optimize import minimize, basinhopping
import logging
import random
from .utils import field, enums
from .input_data import InputData
from typing import Dict


class Model:
    def __init__(
            self,
            input_data: InputData,
            initial_x: Dict[str, float]
    ):
        self.input_data = input_data
        self.constraints = []
        self.keys = []
        self.initial_x = initial_x

    # region 变量定义
    def generate_initial_x(self):
        initial_x = {
            material_name: material.initial_ratio
            for material_name, material in self.input_data.material_dict.items()
        }
        return initial_x

    def generate_p_material_plan_var(self, x_ratio_var):
        p_material_plan_var = {
            material_name: x_value / (
                1-
                self.input_data.material_dict[material_name].chemical_compound_content[enums.ChemicalCompoundName.H2O]
                / 100
            )
            for material_name, x_value in x_ratio_var.items()
        }
        return p_material_plan_var



    @staticmethod
    def generate_pr_material_plan_ratio_var(p_material_plan_var):
        total_p_material_plan = sum(p_material_plan_var.values())
        pr_material_plan_ratio_var = {
            material_name: p_value * 100 / total_p_material_plan
            for material_name, p_value in p_material_plan_var.items()
            }
        return pr_material_plan_ratio_var

    def generate_p_chemical_compound_plan_var(self, x_ratio_var, pr_material_plan_ratio_var):
        p_chemical_compound_plan_var = {
            chemical_compound_name: sum(
                x_ratio_var[material_name] * material.chemical_compound_content[chemical_compound_name]
                for material_name, material in self.input_data.material_dict.items()
            ) / sum(
                x_ratio_var[material_name]
                for material_name, material in self.input_data.material_dict.items()
            )
            for chemical_compound_name, chemical_compound in self.input_data.chemical_compound_dict.items()
            if chemical_compound_name != enums.ChemicalCompoundName.H2O
        }
        p_chemical_compound_plan_var[enums.ChemicalCompoundName.H2O] = sum(
                pr_material_plan_ratio_var[material_name] * material.chemical_compound_content[enums.ChemicalCompoundName.H2O]
                for material_name, material in self.input_data.material_dict.items()
            ) / sum(
                pr_material_plan_ratio_var[material_name]
                for material_name, material in self.input_data.material_dict.items()
            )
        return p_chemical_compound_plan_var

    def generate_dry_price_var(self, x_ratio_var):
        dry_price_var = sum(
            x_ratio_var[material_name] * material.dry_price
            for material_name, material in self.input_data.material_dict.items()
        ) / sum(
            x_ratio_var[material_name]
            for material_name, material in self.input_data.material_dict.items()
        )
        return dry_price_var

    @staticmethod
    def generate_ton_price_var(dry_price_var, p_chemical_compound_plan_var):
        ton_price_var = dry_price_var / p_chemical_compound_plan_var[enums.ChemicalCompoundName.TFe]
        return ton_price_var


    # endregion

    # region 约束定义
    def generate_constraints(self):
        self.constraints.extend(self.generate_material_ratio_bounds_constraint())
        self.constraints.extend(self.generate_material_ratio_sum_limit_constraint())
        self.constraints.extend(self.generate_z_cc_bounds_constraint())

    def fun_material_ratio_sum_limit_constraint(self, x):
        x_ratio_var = dict(zip(self.keys, x))
        return 100 - sum(
            x_ratio_var[material_name]
            for material_name in self.input_data.material_dict
        )

    def generate_material_ratio_sum_limit_constraint(self):
        constraints = []
        constraint = {
            "type": "eq",
            "fun": self.fun_material_ratio_sum_limit_constraint,
            "name": "material_ratio_sum_limit_constraint",
        }
        constraints.append(constraint)
        return constraints

    def fun_material_ratio_bounds_constraint(
            self, x, material_name: str, is_lower: bool
    ):
        x_ratio_var = dict(zip(self.keys, x))
        if is_lower:
            return (
                    x_ratio_var[material_name]
                    - self.input_data.material_dict[material_name].ratio_bounds[0]
            )
        else:
            return (
                    self.input_data.material_dict[material_name].ratio_bounds[1]
                    - x_ratio_var[material_name]
            )

    def generate_material_ratio_bounds_constraint(self):
        constraints = []
        for mat_name, material in self.input_data.material_dict.items():
            for lower in [True, False]:
                bound_name = "lower" if lower else "upper"
                constraint = {
                    "type": "ineq",
                    "fun": lambda x, material_name=mat_name, is_lower=lower: self.fun_material_ratio_bounds_constraint(
                        x=x, material_name=material_name, is_lower=is_lower
                    ),
                    "name": "material_{}_ratio_{}_bound_constraint".format(
                        mat_name, bound_name
                    ),
                }
                constraints.append(constraint)
        return constraints

    def fun_z_cc_bounds_constraint(
            self, initial_guess_x, param: str, is_lower: bool
    ):
        x_ratio_var = dict(zip(self.keys, initial_guess_x))
        p_material_plan_var = self.generate_p_material_plan_var(x_ratio_var=x_ratio_var)
        pr_material_plan_ratio_var = self.generate_pr_material_plan_ratio_var(p_material_plan_var=p_material_plan_var)
        p_chemical_compound_plan_var = self.generate_p_chemical_compound_plan_var(
            x_ratio_var=x_ratio_var,
            pr_material_plan_ratio_var=pr_material_plan_ratio_var
        )

        cc = self.input_data.chemical_compound_dict[param]
        if is_lower:
            return p_chemical_compound_plan_var[param] - cc.ratio_bounds[0]
        else:
            return cc.ratio_bounds[1] - p_chemical_compound_plan_var[param]

    def generate_z_cc_bounds_constraint(self):
        constraints = []
        for cc_name in self.input_data.chemical_compound_dict:
            for lower in [True, False]:
                bound_name = "lower" if lower else "upper"
                constraint = {
                    "type": "ineq",
                    "fun": lambda x, param=cc_name, is_lower=lower: self.fun_z_cc_bounds_constraint(
                        initial_guess_x=x, param=param, is_lower=is_lower
                    ),
                    "name": "cc_{}_{}_bounds_constraint".format(
                        cc_name, bound_name
                    ),
                }
                constraints.append(constraint)
        return constraints

    # endregion

    # region 目标
    def get_objective(self, initial_guess_x):
        x_ratio_var = dict(zip(self.keys, initial_guess_x))
        p_material_plan_var = self.generate_p_material_plan_var(x_ratio_var=x_ratio_var)
        pr_material_plan_ratio_var = self.generate_pr_material_plan_ratio_var(p_material_plan_var=p_material_plan_var)
        dry_price_var = self.generate_dry_price_var(x_ratio_var=x_ratio_var)
        p_chemical_compound_plan_var = self.generate_p_chemical_compound_plan_var(
            x_ratio_var=x_ratio_var,
            pr_material_plan_ratio_var=pr_material_plan_ratio_var
        )
        ton_price_var = self.generate_ton_price_var(
            dry_price_var=dry_price_var,
            p_chemical_compound_plan_var=p_chemical_compound_plan_var
        )

        return ton_price_var

    # endregion
    def run_model(self):
        x_ratio_var = self.initial_x
        initial_x = []
        for key, val in x_ratio_var.items():
            self.keys.append(key)
            initial_x.append(val)
        initial_guess = np.array(initial_x)

        self.generate_constraints()

        # 定义 accept_test 函数
        def accept_test(f_new, x_new, f_old, x_old):
            # 检查新解是否满足所有约束条件
            for constraint in self.constraints:
                if constraint['type'] == 'ineq' and constraint['fun'](x_new) < -1e-2:
                    return False
                if constraint['type'] == 'eq' and abs(constraint['fun'](x_new)) > 1e-2:
                    return False
            return True

        random_results = []
        # 定义回调函数
        def callback(x, f, accepted):
            if callback.iteration == 0:
                callback.best_f = f
                callback.no_improvement_count = 0
            else:
                if f < callback.best_f:
                    callback.best_f = f
                    callback.no_improvement_count = 0
                else:
                    callback.no_improvement_count += 1
                    if callback.no_improvement_count >= 50:
                        return True  # 返回 True 表示停止迭代
            if random.random() < 0.2:
                # 添加新解到结果列表
                random_results.append((x.copy(), f))
                # 保持列表中三个解
                if len(random_results) > 2:
                    random_results.pop(0)

            callback.iteration += 1

        callback.iteration = 0

        result = basinhopping(
            self.get_objective,
            initial_guess,
            minimizer_kwargs={
                "constraints": self.constraints,
                "method": "SLSQP",
                "options": {'disp': True},
                "tol": 1e-2
            },
            niter=500,
            # 增加迭代次数以提高找到全局最优解的概率
            accept_test=accept_test,
            callback=callback
        )

        if not result.success:
            logging.error(
                "Unsuccessful solution, message: {}".format(result.message)
            )
        else:
            logging.info("Successful solution, message: {}".format(result.message))
            logging.info("Objective: {}".format(result.fun))

        self.check_constraints(result_x=result.x)
        logging.info("model solution objective: {}".format(result.fun))
        multi_results = [(result.x.copy(), result.fun)] + random_results
        return result, multi_results

    def check_constraints(self, result_x, tolerance=0.001):
        constraints = self.constraints

        violations = []
        for i, constraint in enumerate(constraints):
            constraint_type = constraint["type"]
            constraint_fun = constraint["fun"]
            constraint_name = constraint["name"]
            constraint_value = constraint_fun(result_x)

            if isinstance(constraint_value, list) or isinstance(
                constraint_value, np.ndarray
            ):
                for j, value in enumerate(constraint_value):
                    if constraint_type == "ineq" and value < -tolerance:
                        violations.append(
                            f"Constraint '{constraint_name}' (inequality) not satisfied: value = {value}"
                        )
                    elif constraint_type == "eq" and not np.isclose(
                        value, 0, atol=tolerance
                    ):
                        violations.append(
                            f"Constraint '{constraint_name}' (equality) not satisfied: value = {value}"
                        )
            else:
                if constraint_type == "ineq" and constraint_value < -tolerance:
                    violations.append(
                        f"Constraint '{constraint_name}' (inequality) not satisfied: value = {constraint_value}"
                    )
                elif constraint_type == "eq" and not np.isclose(
                    constraint_value, 0, atol=tolerance
                ):
                    violations.append(
                        f"Constraint {i + 1} (equality) not satisfied: value = {constraint_value}"
                    )
                    violations.append(
                        f"Constraint '{constraint_name}' (equality) not satisfied: value = {constraint_value}"
                    )

        if violations:
            logging.error("以下约束条件未满足:")
            for violation in violations:
                logging.error(violation)