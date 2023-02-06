"""

            Generate Binary IC's for cluster collisions given parameters

"""
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_System.text_utils import print_title, get_options
from PyCS_System.SimulationMangement import ICLog
from PyCS_System.SpecConfigs import read_clustep_config, write_clustep_ini, write_slurm_script
import pathlib as pt
import argparse
import time
import warnings
import toml
from datetime import datetime

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

clustep_exec = CONFIG["system"]["executables"]["CLUSTEP_install"]
params_ini = os.path.join(clustep_exec, "params_cluster.ini")

### __command variables for use with SLURM
__command_variables_batch = """
#- Managing modules -#
module use $HOME/MyModules
ml miniconda3/latest
#- Moving to the correct directory -#
setenv WORKDIR %s
cd $WORKDIR # Moving to the parent directory to perform the commands.
setenv CLUSTEPDIR %s


#- Generating the first of the binary systems -#
python PyCS_Commands/ReplaceClustepIni.py %s
cd $CLUSTEPDIR
python %s/clustep.py -o %s/cluster1.dat %s

#- Generating the first of the binary systems -#
cd $WORKDIR
python PyCS_Commands/ReplaceClustepIni.py %s
cd $CLUSTEPDIR
python %s/clustep.py -o %s/cluster2.dat %s

#- Running SnapGadget -#
cd $WORKDIR
%s
"""

### no-batch commands
__command_variables_nobatch = """
echo "\x1b[36mSetting up the batch script\x1b[37m"
WORKDIR=%s
python_exec=%s
cd $WORKDIR
CLUSTEPDIR=%s
echo "\x1b[36mBuilding the first cluster\x1b[37m"
$python_exec PyCS_Commands/ReplaceClustepIni.py %s
cd $CLUSTEPDIR
$python_exec %s/clustep.py -o %s/cluster1.dat %s
echo "\x1b[36mBuilding the second cluster\x1b[37m"
cd $WORKDIR
$python_exec PyCS_Commands/ReplaceClustepIni.py %s
cd $CLUSTEPDIR
$python_exec %s/clustep.py -o %s/cluster2.dat %s
echo "\x1b[36mRunning snapgadget\x1b[37m"
#- Running SnapGadget -#
cd $WORKDIR
%s
"""
# %s --> (path to parent,temp_1,params.ini, clustep install, tmp_directory, temp2, params.ini, clustep install, temp_directory, snap join command)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    ### Starting the argparser ###
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    parser.add_argument("-nb", "--no_batch", action="store_true", help="Use batch to run.")
    args = parser.parse_args()

    ### Setting up logging ###
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    log_print("Running run_BinaryICs.py", _dbg_string, "debug")
    time.sleep(0.1)

    ### Getting the settings ###
    __binary_options_dict = {
        "General":
            {
                "Impact Parameter": (0, 0, "The impact parameter for the collision in kpc."),
                "Initial Distance": (3000, 3000, "The initial separation between the clusters (kpc)"),
                "Relative Velocity": (1000, 1000, "The initial relative velocity in km/s")
            },
        "Cluster 1": read_clustep_config(),
        "Cluster 2": read_clustep_config()
    }
    # MAIN
    ########################################################################################################################
    print_title("run_BinaryICs 1.0", "Eliza Diggins")
    # Selecting a valid slurm file #
    __binary_options_dict = get_options(__binary_options_dict, "Collision Options")

    # Getting output name
    ########################################################################################################################
    out_name = input("%sPlease enter a filename for the output. [""] to auto generate. " % _dbg_string)
    if out_name == "":
        clusters = [file for file in os.listdir(CONFIG["system"]["directories"]["initial_conditions_directory"]) if
                    "Col" in file]
        n = len(clusters) + 1
        out_name = "Col_%s.dat" % n

    log_print("Generating %s." % out_name, _dbg_string, "info")

    # Adding to the IC LOG
    ####################################################################################################################
    # - grabbing the second parameter file storage location -#
    param_file_path = str(os.path.join(CONFIG["system"]["directories"]["parameter_directory"],
                                       out_name.replace(".dat", ""),
                                       "param_%s.ini"))

    # - generating the directory if necessary -#
    if not os.path.isdir(pt.Path(param_file_path).parents[0]):
        pt.Path.mkdir(pt.Path(param_file_path).parents[0], parents=True)

    # - spawn in the correct parameters file -#
    tag_strings = {"1":"","2":""}
    for id in ["1", "2"]:
        write_clustep_ini(__binary_options_dict["Cluster %s" % id], param_file_path % id)

        ##- Writing in the correct tags -##
        for tag,item in __binary_options_dict["Cluster %s"% id]["tags"].items():
            tag_strings[id] += (tag+ " " if item[0]=="True" else "")

    #- Write the final additional parameter file which is shared. Carries the %INFO% marker on it. -#
    joint_data_path = str(os.path.join(CONFIG["system"]["directories"]["parameter_directory"],
                                       out_name.replace(".dat", ""),
                                       "params_%INFO%.ini"))

    __binary_options_dict["General"] = {key:[str(i) for i in value] for key,value in __binary_options_dict["General"].items()}
    with open(joint_data_path,"w") as f:
        toml.dump(__binary_options_dict,f)

    # - adding everything to the log -#
    iclog[out_name] = {"param_files":[param_file_path % i for i in ["1", "2"]]+[joint_data_path],
                "type":"cluster-binary",
                       "location":os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],out_name),
                       "DateCreated":datetime.now()}

    # Running
    ####################################################################################################################
    if args.no_batch:
        # Getting snapjoin set up.
        ########################################################################################################################
        snapgadet_params = (CONFIG["system"]["executables"]["python_full"],
                            os.path.join(CONFIG["system"]["executables"]["SnapGadget_install"], "snapjoin.py"),
                            os.path.join(CONFIG["system"]["directories"]["temp_directory"], "cluster1.dat"),
                            os.path.join(CONFIG["system"]["directories"]["temp_directory"], "cluster2.dat"),
                            os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], out_name),
                            __binary_options_dict["General"]["Initial Distance"][0],
                            __binary_options_dict["General"]["Impact Parameter"][0],
                            __binary_options_dict["General"]["Relative Velocity"][0])

        snapgadet_command = "%s %s %s %s %s %s %s 0 %s 0 0" % (snapgadet_params)
        # Creating the command sequence.
        command_string = __command_variables_nobatch % (
            str(pt.Path(os.path.realpath(__file__)).parents[1]),
            CONFIG["system"]["executables"]["python_full"],
            clustep_exec,
            param_file_path % "1",
            clustep_exec,
            CONFIG["system"]["directories"]["temp_directory"],
            tag_strings["1"],
            param_file_path % "2",
            clustep_exec,
            CONFIG["system"]["directories"]["temp_directory"],
            tag_strings["2"],

            snapgadet_command
        )
        os.system(command_string)
    ########################################################################################################################
    else:
        # Getting snapjoin set up.
        ########################################################################################################################
        snapgadet_params = (os.path.join(CONFIG["system"]["executables"]["SnapGadget_install"], "snapjoin.py"),
                            os.path.join(CONFIG["system"]["directories"]["temp_directory"], "cluster1.dat"),
                            os.path.join(CONFIG["system"]["directories"]["temp_directory"], "cluster2.dat"),
                            os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], out_name),
                            __binary_options_dict["General"]["Initial Distance"][0],
                            __binary_options_dict["General"]["Impact Parameter"][0],
                            __binary_options_dict["General"]["Relative Velocity"][0])

        snapgadet_command = "python %s %s %s %s %s %s 0 %s 0 0" % snapgadet_params
        # Creating the command sequence.
        ########################################################################################################################
        command_string = __command_variables_batch % (
            str(pt.Path(os.path.realpath(__file__)).parents[1]),
            clustep_exec,
            param_file_path % "1",
            clustep_exec,
            CONFIG["system"]["directories"]["temp_directory"],
            tag_strings["1"],
            param_file_path % "2",
            clustep_exec,
            CONFIG["system"]["directories"]["temp_directory"],
            tag_strings["2"],
            snapgadet_command
        )
        write_slurm_script(command_string, type="BINARY_BUILD")
