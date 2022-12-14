"""

    Tools for remote file management using RClone or single transfer.

"""
import sys
import pathlib as pt
import os

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
import pathlib as pt
import toml
from datetime import datetime
from PyCS_System.text_utils import get_options
import subprocess
from tqdm import tqdm

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# - _file_header_dict is a set of all of the directories where we will find things we want to transfer.
_file_header_dict = {
    "Figures": CONFIG["system"]["directories"]["figures_directory"],
    "Movies": CONFIG["system"]["directories"]["movies_directory"],
    "Initial Conditions": CONFIG["system"]["directories"]["initial_conditions_directory"],
    "NML Files": CONFIG["system"]["directories"]["RAMSES_nml_directory"]
}

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def send_items_to_rclone(location_dict):
    """
    Sends the items in the location dict to rclone.

    To perform this operation, we break the entire structure down into just raw files. Then we rebuild the file structure
    on Rclone / box using the underlying structure.
    Parameters
    ----------
    location_dict: the location dictionary to send to rclone.
    delete: True to delete from local machine after upload
    threaded: True to use threading. False to avoid threading.
    """
    fdbg_string = _dbg_string+"send_items_to_rclone: "
    log_print("Sending %s to box."%location_dict,fdbg_string,"debug")

    ### Running transfer ###
    for item in tqdm(location_dict,disable=CONFIG["system"]["logging"]["use_progress_bars"],
                     position=0,desc="Uploading files/directories to box..."): # cycle through all of the locations
        rclone_directory = os.path.join("box:/PyCS",
                                        location_dict[item]["source"],
                                        location_dict[item]["path"].replace(_file_header_dict[location_dict[item]["source"]],""))


        command = "rclone copy %s '%s'"%(location_dict[item]["path"],rclone_directory)

        log_print("running %s"%command,fdbg_string,"debug")

        os.system(command)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT")
    from PyCS_System.text_utils import file_directory_select
    send_items_to_rclone(file_directory_select({"Initial Conditions":"/home/ediggins/PyCS"}))
