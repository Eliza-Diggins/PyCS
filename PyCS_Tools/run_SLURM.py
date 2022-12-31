"""

Quick Script for running an existing slurm script

"""
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_System.text_utils import file_select, print_title
import pathlib as pt
import argparse
import time
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    ### Starting the argparser ###
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")

    args = parser.parse_args()

    ### Setting up logging ###
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    log_print("Running run_SLURM.py", _dbg_string, "debug")
    time.sleep(0.1)
    print_title("run_SLURM 1.0", "Eliza Diggins")
    # Selecting a valid slurm file #
    selected_slurm_file = file_select(os.path.join(CONFIG["system"]["directories"]["SLURM_directory"], "scripts"),
                                      lambda file: ".slurm" in file,
                                      search_for_description=True)

    full_path = os.path.join(
        os.path.join(CONFIG["system"]["directories"]["SLURM_directory"], "scripts", selected_slurm_file))
    os.system("sbatch %s" % full_path)
    log_print("Sent %s to the scheduler." % full_path, _dbg_string, "debug")
    os.system("squeue -u $USER")
