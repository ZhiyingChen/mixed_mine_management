from src.utils import log
from src.input_data import InputData

# 按装订区域中的绿色按钮以运行脚本。
if __name__ == "__main__":
    exe_folder = "./"
    logger = log.setup_log(log_dir=exe_folder)

    input_data = InputData(exe_folder=exe_folder)
    input_data.read_data()



