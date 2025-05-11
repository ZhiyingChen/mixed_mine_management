import time
import logging
import functools

# 定义全局变量用于存储任务及其相应的时间
tasks = []


# 函数用于添加任务及其相应的时间到全局变量中
def add_task(task_name: str, time_taken: float):
    global tasks
    tasks.append((task_name, time_taken))


def record_time_decorator(task_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            st = time.time()
            # 调用原函数
            result = func(*args, **kwargs)
            ed = time.time()
            total_time = round(ed - st, 4)
            logging.info("{}: {}".format(task_name, total_time))
            add_task(task_name=task_name, time_taken=total_time)
            return result

        return wrapper

    return decorator


def out_profile(output_folder: str):
    # 打开文本文件，准备写入
    with open("{}time_profile.txt".format(output_folder), "w") as file:
        # 写入任务及其相应的时间
        for task, time_taken in tasks:
            file.write(f"{task}: {time_taken}\n")

    file.close()
