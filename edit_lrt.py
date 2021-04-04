import os, shutil, sys, argparse

# sys.path.append("d:\\PythonProjects")

# from datetime import date, datetime

from functions_edit_lrt import (
    create_custom_logger,
    read_csv,
    is_csv,
    edit_lrt_vsr,
    create_file_DDI,
    save_output_file,
    print_menu,
    input_values_option1,
    input_values_option2,
)
from constants import LOG_PATH, INPUT_PATH


parser = argparse.ArgumentParser(prog="Daily Tasks")
parser.add_argument(
    "-f",
    "--file",
    dest="input_file",
    required=True,
    type=is_csv,
    help="Enter the CSV filename with the data to add",
)
args = parser.parse_args()

input_file_fullpath = os.path.join(INPUT_PATH, args.input_file)
my_csv = read_csv(input_file_fullpath)

task = print_menu()

if task == "1":
    my_domain, tables, vsrs = input_values_option1()

    # Initiate our custom logger for this task
    my_logger, my_logfile = create_custom_logger("Task_1", LOG_PATH)

    my_logger.info(
        "Task inputs: \n"
        "Task selected: Configure LRT(s) \n"
        f"Customer domain: {my_domain} \n"
        f"Input file: {args.input_file} \n"
        f"Session Router(s) to work: {vsrs} \n"
        f"LRT(s) to work: {tables} \n"
    )

    # Executing the task
    edit_lrt_vsr(my_domain, my_csv, vsrs, tables, my_logger)

elif task == "2":
    customer = input_values_option2()

    # Initiate our custom logger for this task
    my_logger, my_logfile = create_custom_logger("Task_2", LOG_PATH)

    my_logger.info(
        "Task inputs: \n"
        "Task selected: Generate DDI-Bidirectional file \n"
        f"Customer: {customer} \n"
        f"Input file: {args.input_file} \n"
    )

    # Executing the task
    create_file_DDI(input_file_fullpath, customer, my_logger)
    save_output_file(my_logger)

elif task == "3":
    customer = input_values_option2()
    my_domain, tables, vsrs = input_values_option1()

    # Initiate our custom logger for this task
    my_logger, my_logfile = create_custom_logger("Task_3", LOG_PATH)

    my_logger.info(
        "Task inputs: \n"
        "Task selected: Configure LRT(s) & Generate DDI-Bidirectional file \n"
        f"Customer: {customer} \n"
        f"Customer domain: {my_domain} \n"
        f"Input file: {args.input_file} \n"
        f"Session Router(s) to work: {vsrs} \n"
        f"LRT(s) to work: {tables} \n"
    )

    # Executing the task
    edit_lrt_vsr(my_domain, my_csv, vsrs, tables, my_logger)
    create_file_DDI(input_file_fullpath, customer, my_logger)
    save_output_file(my_logger)

elif task == "q":
    print("Thank you for using this script. Goodbye!")