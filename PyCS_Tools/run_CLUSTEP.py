"""

        Run_Clustep script
        Eliza Diggins

"""
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log
from PyCS_System.SpecConfigs import read_clustep_config, write_slurm_script, write_clustep_ini
import pathlib as pt
from datetime import datetime
from PyCS_System.text_utils import get_options
from PyCS_System.SimulationMangement import ICLog
import time
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
iclog = ICLog.load_default()
# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Setting up the command string to feed into the slurm generator.
command_string = """
#- Module Setup -#
ml purge
module use $HOME/MyModules
ml miniconda3/latest

#- Environment Management -#
setenv WORKDIR %s
setenv CMDDIR %s

#- moving the param file -#
cd $CMDDIR
%s %s '%s'


cd $WORKDIR

#- Main Command -#
%s clustep.py -o '%s' %s
"""
clustep_exec = CONFIG["system"]["executables"]["CLUSTEP_install"]  # this is the location of the clustep.py exec.
python_exec = CONFIG["system"]["executables"]["python_full"]  # this is the command of the full python implementation.
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # Argument Parsing
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    parser.add_argument("-nb", "--no_batch", action="store_true", help="Use batch to run.")
    args = parser.parse_args()

    # Setup
    ########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)

    # Grabbing CLUSTEP data
    ########################################################################################################################
    clustep_config_default = read_clustep_config()  # reading the config from file
    clustep_config = get_options(clustep_config_default, "Clustep Initialization Settings")  # grabbing settings

    # - Writing the clustep config to the install location -#
    # - We need to write it specially because it cannot be written by TOML
    params_dir = os.path.join(CONFIG["system"]["executables"]["CLUSTEP_install"], "params_cluster.ini")

    time.sleep(0.1)

    # Grabbing basic simulation info
    # We need an output name, a slurm script name
    ########################################################################################################################
    out_name = input("%sPlease enter a filename for the output. [""] to auto generate. " % _dbg_string)
    if out_name == "":
        clusters = [file for file in os.listdir(CONFIG["system"]["directories"]["initial_conditions_directory"]) if
                    "Clu" in file]
        n = len(clusters) + 1
        out_name = "Clu_%s.dat" % n

    # Adding to IC log
    ####################################################################################################################
    # - grabbing the second parameter file storage location -#
    param_file_path = os.path.join(CONFIG["system"]["directories"]["parameter_directory"],
                                   out_name.replace(".dat", ""),
                                   "param_1.ini")

    # - generating the directory if necessary -#
    if not os.path.isdir(pt.Path(param_file_path).parents[0]):
        pt.Path.mkdir(pt.Path(param_file_path).parents[0], parents=True)

    # - spawn in the correct parameters file -#
    write_clustep_ini(clustep_config, param_file_path)

    #- creating tags -#
    tag_string = ""
    for tag,value in clustep_config["tags"].items():
        # Cycling through all of the tags and checking them
        if value[0] == "True":
            tag_string += "%s "%tag
        else:
            pass

    # - adding everything to the log -#
    iclog[out_name] = {"param_files":[param_file_path],
                       "type":"cluster-single",
                       "DateCreated":datetime.now(),
                       "location":os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], out_name)}

    ### RUNNING THE PROGRAM ###
    if args.no_batch:
        ### We are not using the scheduler for this job ###
        usr_dir = os.getcwd()  # get a current dir to return to.

        # - copying the parameter file -#
        os.chdir(str(pt.Path(os.path.realpath(__file__)).parents[1]))
        os.system("%s %s '%s'" % (python_exec, os.path.join("PyCS_Commands", "ReplaceClustepIni.py"), param_file_path))

        # - executing -#
        os.chdir(clustep_exec)  # go to installation location

        # running the command in the correct python version #
        os.system("%s %s -o %s %s" % (python_exec, "clustep.py",
                                   os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                                out_name),tag_string))
        # returning to correct directory.
        os.chdir(usr_dir)
    else:
        ### We are going to send things to SLURM ###
        slurm_name = "SLURM_CLUSTEP_%s_%s.slurm" % (
        out_name.replace(".dat", ""), datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))

        write_slurm_script(command_string % (clustep_exec,
                                             str(pt.Path(os.path.realpath(__file__)).parents[1]),
                                             python_exec,
                                             os.path.join("PyCS_Commands", "ReplaceClustepIni.py"),
                                             param_file_path,
                                             python_exec,
                                             os.path.join(
                                                 CONFIG["system"]["directories"]["initial_conditions_directory"],
                                                 out_name),
                                             tag_string),
                           name=slurm_name,
                           type="CLUSTEP",
                           batch=True)
