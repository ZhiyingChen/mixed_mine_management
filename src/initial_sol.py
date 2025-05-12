from .model import Model
from .input_data import InputData
from scipy.optimize import minimize, basinhopping, linprog
import numpy as np
import logging

class InitialSolution(Model):
    def __init__(self, input_data: InputData):
        super().__init__(input_data=input_data, initial_x=dict())


    def generate_initial_x(self):
        n = len(self.input_data.material_dict)
        material_name_lt = [m for m in self.input_data.material_dict]

        # 定义目标函数（这里不需要优化，所以设置为0）
        c = [0] * n

        # 定义不等式约束
        A = []
        b = []
        for i, m in enumerate(material_name_lt):
            material = self.input_data.material_dict[m]
            A.append([-1 if j == i else 0 for j in range(n)])  # v_i >= v_min
            A.append([1 if j == i else 0 for j in range(n)])  # v_i <= v_max
            b.append(-material.ratio_bounds[0])
            b.append(material.ratio_bounds[1])
            # 定义等式约束
        A_eq = [[1] * n]
        b_eq = [100]

        # 求解
        res = linprog(c, A_ub=A, b_ub=b, A_eq=A_eq, b_eq=b_eq, method='highs')

        if res.success:
            return dict(zip(material_name_lt,res.x))
        else:
            raise ValueError("无法找到满足条件的解")


    def generate_constraints(self):
        self.constraints.extend(self.generate_material_ratio_bounds_constraint())
        self.constraints.extend(self.generate_material_ratio_sum_limit_constraint())


    def get_objective(self, initial_guess_x):
        x_ratio_var = dict(zip(self.keys, initial_guess_x))
        p_material_plan_var = self.generate_p_material_plan_var(x_ratio_var=x_ratio_var)
        pr_material_plan_ratio_var = self.generate_pr_material_plan_ratio_var(p_material_plan_var=p_material_plan_var)
        p_chemical_compound_plan_var = self.generate_p_chemical_compound_plan_var(
            x_ratio_var=x_ratio_var,
            pr_material_plan_ratio_var=pr_material_plan_ratio_var
        )

        penalty = 0
        for cc_name, cc in self.input_data.chemical_compound_dict.items():
            if p_chemical_compound_plan_var[cc_name] < cc.ratio_bounds[0]:
                penalty += (cc.ratio_bounds[0] - p_chemical_compound_plan_var[cc_name]) ** 2
            elif p_chemical_compound_plan_var[cc_name] > cc.ratio_bounds[1]:
                penalty += (cc.ratio_bounds[1] - p_chemical_compound_plan_var[cc_name]) ** 2
        return penalty

    def run_model(self):
        x_ratio_var = self.generate_initial_x()
        self.initial_x = x_ratio_var
        initial_x = []
        for key, val in x_ratio_var.items():
            self.keys.append(key)
            initial_x.append(val)
        initial_guess = np.array(initial_x)

        self.generate_constraints()

        result = minimize(
            self.get_objective,
            initial_guess,
            constraints=self.constraints,
            method="SLSQP",
            tol=1e-2,
        )
        self.check_constraints(result_x=result.x)
        logging.info("initial solution objective: {}".format(result.fun))
        return dict(zip(self.keys, result.x))