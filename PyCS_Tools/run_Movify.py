"""

        Movie Generation Script for Post Processed Images
            Written by: Eliza Diggins
"""
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_System.text_utils import print_title
from PyCS_System.SpecConfigs import write_slurm_script
import pathlib as pt
from colorama import Fore, Style
from PyCS_System.text_utils import file_directory_select
import time
from PyCS_System.SimulationMangement import SimulationLog
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
simlog = SimulationLog.load_default()
# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')


#- Fixed Variables -#
ffmpeg_command = """
ffmpeg -framerate %s -pattern_type glob -i '%s' -c:v libx264 -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" -s 1920x1080 -pix_fmt yuv420p '%s'
"""
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Main ------------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')
    # Parsing Arguments
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    parser.add_argument("-nb", "--no_batch", action="store_true", help="Use to run commands without SLURM")
    parser.add_argument("-nchpc", "--no_chpc", action="store_true",
                        help="This setting will turn off the CHPC specific steps.")
    parser.add_argument("-r","--framerate",default=20,type=int,help="The frame rate of the output movies.")
    args = parser.parse_args()

    # Setup Tasks
    ########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    log_print("Running run_Movify.py.", _dbg_string, "debug")
    time.sleep(0.1)

    # - importing the necessary modules for CHPC -#
    if not args.no_chpc:
        # - We are on chpc and we need to load the correct modules.
        os.system("ml ffmpeg")  # load the ffmpeg module
    else:
        #- There is not issue here -#
        pass

    # Fetching selection
    ####################################################################################################################
    selected_figure_directories = file_directory_select({
        "Figures":CONFIG["system"]["directories"]["figures_directory"]
    })

    #- cleaning up -#
    log_print("%s items were selected for Movify: %s."%(len(selected_figure_directories),list(selected_figure_directories.keys())),
              _dbg_string,"debug")
    ##- Removing non-directories -##
    for key, item in selected_figure_directories.items():
        if os.path.isfile(item["path"]): # This is a file, not a directory.
            log_print("Removing %s from the selected items because it is not a directory."%(item["path"]),
                      _dbg_string,
                      "warning")
            del selected_figure_directories[key]
        else:
            pass

    #- grabbing the directories -#
    movify_directories = [item["path"] for item in selected_figure_directories.values()] # grab a list of all of the directories.
    log_print("Converting %s directories (%s) to movies."%(len(movify_directories),movify_directories),_dbg_string,"debug")

    # Attempting to generate movies
    ####################################################################################################################
    for movify_directory in movify_directories:
        #- Checking that the data we are interested in actually exists. -#
        png_files = [directory for directory in os.listdir(movify_directory) if os.path.isfile(os.path.join(movify_directory,directory)) and ".png" in directory]
        if len(png_files):
            # There is at least one actual file in here.
            # Managing the I/O side of things
            ############################################################################################################
            movie_directory =str(pt.Path(movify_directory.replace(
                CONFIG["system"]["directories"]["figures_directory"],
                CONFIG["system"]["directories"]["movies_directory"]
            )).parents[0])

            name = str(movify_directory.replace(str(pt.Path(movify_directory).parents[0]),"")+".mp4")[1:]

            output_path = os.path.join(movie_directory,name)
            log_print("Placing output of %s at %s."%(movify_directory,output_path),_dbg_string,"debug")

            if not os.path.isdir(movie_directory):
                pt.Path.mkdir(pt.Path(movie_directory),parents=True)
            #- grabbing the image names -#
            image_style = str(os.path.join(movify_directory,"Image_*.png"))
            # Creating the Movie
            ############################################################################################################
            os.system(ffmpeg_command%(args.framerate,image_style,output_path))
            log_print("Creating the movie %s for %s."%(output_path,movify_directory),_dbg_string,"debug")
        else:
            log_print("Failed to find images in %s."%movify_directory,_dbg_string,"error")
