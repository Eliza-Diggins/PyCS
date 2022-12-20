"""

        RUN RAMSES script
            Written by: Eliza Diggins
"""
import os
import sys
import pathlib as pt

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_System.text_utils import file_select, print_title
from PyCS_System.SpecConfigs import read_RAMSES_config, read_batch_config, write_nml, write_slurm_script
import pathlib as pt
import toml
from datetime import datetime
from colorama import Fore,Style
from PyCS_System.text_utils import generate_command_sequence, option_menu
import time
from PyCS_System.SimulationMangement import add_simulation,read_simulation_log

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_pycs_head = str(pt.Path(os.path.realpath(__file__)).parents[1])
commands_dict = {
    "Generate Image Sequence": {
        "path": os.path.join(_pycs_head, "PyCS_Commands", "GenerateImageSequence.py"),
        "desc": "Plot a sequence of images with a selection of kwargs for the selected simulation.",
        "options": {
            "qty": ("", "", "The quantity to plot."),
            "-sim": ("", "", "The simulation name to use. Only one of -sim / -simdir is needed."),
            "-simdir": ("", "", "The simulation directory."),
            "-v": ("", "", "The output range boundaries. (should be a string 'vmin vmax'"),
            "-w": (str(CONFIG["Visualization"]["Images"]["default_width"]),str(CONFIG["Visualization"]["Images"]["default_width"]),"The width of the plotting area."),
            "-t": ("", "", "The title to put on the simulation"),
            "-u": ("", "", "The output units"),
            "-tu": (str(CONFIG["units"]["default_time_unit"]), str(CONFIG["units"]["default_time_unit"]), "The time units to use in the simulation"),
            "-r": (str(CONFIG["Visualization"]["Images"]["default_resolution"]), str(CONFIG["Visualization"]["Images"]["default_resolution"]), "The resolution to use for the image."),
            "-f": ("", "", "The families to include in the plotting."),
            "-i": (str(CONFIG["Visualization"]["Images"]["default_integration"]), str(CONFIG["Visualization"]["Images"]["default_integration"]), "True to integrate through the line of sight."),
            "-log": (str(CONFIG["Visualization"]["Images"]["default_log"]), str(CONFIG["Visualization"]["Images"]["default_log"]), "Use a logarithmic colormap?"),
            "-cmap": (str(CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"].name), str(CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"].name), "The colormap to use for the plotting."),
            "-o": ("", "", "The logging output."),
            "-l": ("", "", "The debugging level."),
            "-np": ("$SLURM_NTASKS", "$SLURM_NTASKS", "The number of processors to use.")
        }
    },
    "Plot Single Snapshot": {
        "path": os.path.join(_pycs_head, "PyCS_Commands", "PlotSingleSnapshot.py"),
        "desc": "Plot a sequence of images with a selection of kwargs for the selected simulation.",
        "options": {
            "qty": ("", "", "The quantity to plot."),
            "ns":("","","The snapshot number to plot."),
            "-sim": ("", "", "The simulation name to use. Only one of -sim / -simdir is needed."),
            "-simdir": ("", "", "The simulation directory."),
            "-v": ("", "", "The output range boundaries. (should be a string 'vmin vmax'"),
            "-t": ("", "", "The title to put on the simulation"),
            "-s": ("","","Save the image or show it?"),
            "-w": (str(CONFIG["Visualization"]["Images"]["default_width"]),str(CONFIG["Visualization"]["Images"]["default_width"]),"The width of the plotting area."),
            "-u": ("", "", "The output units"),
            "-tu": (str(CONFIG["units"]["default_time_unit"]), str(CONFIG["units"]["default_time_unit"]), "The time units to use in the simulation"),
            "-r": (str(CONFIG["Visualization"]["Images"]["default_resolution"]), str(CONFIG["Visualization"]["Images"]["default_resolution"]), "The resolution to use for the image."),
            "-f": ("", "", "The families to include in the plotting."),
            "-i": (str(CONFIG["Visualization"]["Images"]["default_integration"]), str(CONFIG["Visualization"]["Images"]["default_integration"]), "True to integrate through the line of sight."),
            "-log": (str(CONFIG["Visualization"]["Images"]["default_log"]), str(CONFIG["Visualization"]["Images"]["default_log"]), "Use a logarithmic colormap?"),
            "-cmap": (str(CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"].name), str(CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"].name), "The colormap to use for the plotting."),
            "-o": ("", "", "The logging output."),
            "-l": ("", "", "The debugging level.")
        }
    }
}
commands_dict_data = {
    "Generate Image Sequence": {
        "path": os.path.join(_pycs_head, "PyCS_Commands", "GenerateImageSequence.py"),
        "desc": "Plot a sequence of images with a selection of kwargs for the selected simulation.",
        "options": {
            "qty": "s",
            "-sim":  "s",
            "-simdir":  "s",
            "-v": "l",
            "-w": "s",
            "-t": "s",
            "-u": "s",
            "-tu":  "s",
            "-r":  "s",
            "-f":  "l",
            "-i":  "b",
            "-log":  "b",
            "-cmap":  "s",
            "-o":  "s",
            "-l":  "s",
            "-np":  "s",
        }
    },
    "Plot Single Snapshot": {
        "path": os.path.join(_pycs_head, "PyCS_Commands", "PlotSingleSnapshot.py"),
        "desc": "Plot a sequence of images with a selection of kwargs for the selected simulation.",
        "options": {
            "qty":  "s",
            "ns": "s",
            "-sim":  "s",
            "-simdir":  "s",
            "-v":  "l",
            "-t":  "s",
            "-s":  "b",
            "-w":  "s",
            "-u":  "s",
            "-tu":  "s",
            "-r":  "s",
            "-f":  "l",
            "-i":  "b",
            "-log":  "b",
            "-cmap":  "s",
            "-o": "s",
            "-l":  "s",
        }
    }
}
main_command_string = """
#- directory management -#
setenv WORKDIR %s
cd $WORKDIR

#- Module Management -#
module use $HOME/MyModules
ml miniconda3/latest

#- running commands -#

"""%str(pt.Path(os.path.realpath(__file__)).parents[1])
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')
    # Parsing Arguments
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    parser.add_argument("-nb", "--no_batch", action="store_true", help="Use to run commands without SLURM")
    args = parser.parse_args()

    # Setup Tasks
########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    log_print("Running run_PostProcessingPipeline.py.", _dbg_string, "debug")
    time.sleep(0.1)

    simlog = read_simulation_log() # reading the simulation log.
    ### Setting up the run ###
########################################################################################################################
    #- printing the title -#
    print_title("run_PostProcessingPipeline (version %s)"%CONFIG["system"]["version"], "Eliza Diggins")

    #- selecting a simulation -#
    available_simulations = [value["SimulationName"] for key,value in simlog.items() if "SimulationLocation" in value] # get avail sims.
    available_simulations_key = [key for key,value in simlog.items() if "SimulationLocation" in value]

    if not len(available_simulations):
        print("%s There are no available simulations..."%(Fore.CYAN+Style.BRIGHT+_dbg_string+Style.RESET_ALL))
        exit()

    selected_simulation = option_menu(available_simulations,{sim_name:str(Fore.GREEN+Style.BRIGHT+simlog[key]["SimulationLocation"]+Style.RESET_ALL) for sim_name,key in zip(available_simulations,available_simulations_key)},title="Simulations Menu")

    kwargs = {"-sim":selected_simulation,
              "-t":selected_simulation} # setting the kwargs to pass to the command sequence

    # Running the command generator #
########################################################################################################################
    command_string = generate_command_sequence(commands_dict,commands_dict_data,**kwargs)

    final_command_string = main_command_string+command_string
    # batching
########################################################################################################################
    if args.no_batch:
        print("%s: Running command %s"%(_dbg_string,command_string))
        os.chdir(str(pt.Path(os.path.realpath(__file__)).parents[1]))
        os.system(command_string)
    else:
        batch_settings = write_slurm_script(final_command_string,type="POST_PROCESSING")
