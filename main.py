from src.utils import log
from src.input_data import InputData
from src.model import Model
from src.initial_sol import InitialSolution
from src.result_storage import ResultStorage
import time
import logging

# 按装订区域中的绿色按钮以运行脚本。
if __name__ == "__main__":
    exe_folder = "./"
    logger = log.setup_log(log_dir=exe_folder)

    st = time.time()
    input_data = InputData(exe_folder=exe_folder)
    input_data.read_data()

    initial_run = InitialSolution(input_data=input_data)
    initial_x_ratio_sol = initial_run.run_model()

    model = Model(input_data=input_data, initial_x=initial_x_ratio_sol)
    result = model.run_model()

    result_storage = ResultStorage(
        input_data=input_data,
        keys=model.keys,
        result=result
    )
    result_storage.write_to_excel()
    logging.info("total time: {}s".format(time.time() - st))