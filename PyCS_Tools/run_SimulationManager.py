"""

        Simulation Manager for use on CHPC
        Written by: Eliza Diggins

"""
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import log_print, set_log
import pathlib as pt
from colorama import Fore, Back, Style
from PyCS_System.text_utils import get_yes_no
from PyCS_System.SimulationMangement import SimulationLog
import numpy as np
import warnings
from sshkeyboard import listen_keyboard, stop_listening

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
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
__global_simulation_location = None  # This holds direct data on where we are in the global namescape.
__global_update_check = True  # We use this to know when to update the listing
__global_command = None
__subcycle_check = False

# - Aesthetic vars -#
__name_substitutions = {
    "SimulationName": "Name",
    "SimulationLocation": "Loc.",
    "Description": "Desc."
}

# - Print details -#
# - Managing the title -#
title = "Simulation Manager V. %s" % CONFIG["system"]["version"]
author = "Written By: Eliza Diggins"


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Basic Functs ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_split(a, b):
    if (b - a) % 2 == 0:
        return int((b - a) / 2), int((b - a) / 2)
    else:
        return int((b - a - 1) / 2), int(((b - a - 1) / 2) + 1)


def get_print_calculations(columns=None):
    """
    Find the correct print out calculations for the given set of columns

    Parameters
    ----------
    columns: The columns to include. (SimulationName) is always added on its own first.

    Returns: Calcs.
    -------

    """
    # Managing the columns
    ####################################################################################################################
    # - Do we have any columns? -#
    if not columns:
        columns = ["SimulationName", "Description", "SimulationLocation"]
    # - Do we have simulation name? -#
    if "SimulationName" not in columns:
        columns = ["SimulationName"] + columns

    # Fetching Values
    ####################################################################################################################
    column_values = {
        column: [str(value[column]) if column in value else "None" for value in simlog.values()]
        for column in columns
    }

    # - Managing column names -#
    column_values = {(key if key not in __name_substitutions else __name_substitutions[key]): value for key, value in
                     column_values.items()}

    # - Computing lengths
    print(column_values)
    max_lengths = {key: np.amax([len(key)] + [len(i) for i in value]) + 2 for key, value in column_values.items()}
    leftovers = {key: [max_length - len(item) for item in column_values[key]] for key, max_length in
                 max_lengths.items()}

    return max_lengths, leftovers, columns


def print_simlog(calcs=None, location=None, message=None):
    """
    Prints the simulation log with a highlight where the location is specified.
    Parameters
    ----------
    calcs: The calculations to use. If not specified, then passes.
    location: The location (should be an index)

    -------

    """
    # Setup
    ####################################################################################################################
    if not calcs:
        calcs = get_print_calculations(columns=None)

    # Header calcs
    ####################################################################################################################
    # - building the header -#
    div_string = ""
    header_string = ""
    for key, value in calcs[0].items():  # we pull max lengths
        div_string += "+" + ("-" * value)
        header_space = get_split(len(key), value)
        header_string += ("|" + (" " * header_space[0]) + Fore.GREEN + Style.BRIGHT + str(key) + Style.RESET_ALL + (
                " " * header_space[1]))
    div_string += "+"
    header_string += "|"

    # - Managing the title -#
    title_string = "|" + (" " * get_split(len(title), len(div_string) - 2)[0]) + Fore.CYAN + title + Style.RESET_ALL + (
            " " * get_split(len(title), len(div_string) - 2)[1]) + "|"
    author_string = "|" + (
            " " * get_split(len(author), len(div_string) - 2)[0]) + Fore.CYAN + author + Style.RESET_ALL + (
                            " " * get_split(len(author), len(div_string) - 2)[1]) + "|"
    # printing
    ####################################################################################################################
    # - header -#
    os.system('cls' if os.name == 'nt' else 'clear')
    print("+" + ("-" * (len(div_string) - 2)) + "+")
    print(title_string)
    print(author_string)
    print(div_string)
    print(header_string)
    print(div_string)

    # - Printing main items -#
    for id, data in enumerate(simlog.values()):
        printed_items = [str(data[col]) if col in data else "None" for col in calcs[2]]

        if not location == id:
            print_string = ""
            for string, leftovers in zip(printed_items, calcs[1].values()):
                print_string += "|" + (" " * get_split(len(string), len(string) + leftovers[id])[0]) + string + (
                        " " * get_split(len(string), len(string) + leftovers[id])[1])
        else:
            print_string = "" + Fore.BLACK + Back.WHITE
            for string, leftovers in zip(printed_items, calcs[1].values()):
                print_string += "|" + (" " * get_split(len(string), len(string) + leftovers[id])[0]) + string + (
                        " " * get_split(len(string), len(string) + leftovers[id])[1])

        print_string += "|" + Style.RESET_ALL
        print(print_string)

    print(div_string)

    # - Printing commands -#
    print(Fore.RED + "Commands: " + Style.RESET_ALL, end="")

    for command, action in zip(["x", "c", "d", "enter"], ["exit", "columns", "delete simulation", "view simulation"]):
        print("[" + Fore.RED + command + Style.RESET_ALL + "]: %s, " % action, end="")
    print("")

    # - Managing the message -#
    if message:
        print(message)


def print_columns(column_selections, location=None):
    """
    Prints the columns and their selection in a nice format.

    Parameters
    ----------
    column_selections: The dictionary containing the on off for each column.
    location: The cursor location.

    Returns: None
    -------

    """
    # - Header string -#
    h1_string = "Column Selection Tool"
    h2_string = "Use [enter] to select, [x] to exit."
    # - Calculations -#
    max_length = np.amax(
        [np.amax([len(key) for key in column_selections]), len(h1_string), len(h2_string)]) + 2  # grab the lengths

    # - Printing -#

    # - header -#
    print("+" + ("-" * max_length) + "+")
    print("|" + (" " * get_split(len(h1_string), max_length)[0]) + Fore.RED + h1_string + Style.RESET_ALL + (
            " " * get_split(len(h1_string), max_length)[1]) + "|")
    print("|" + (" " * get_split(len(h2_string), max_length)[0]) + Fore.RED + h2_string + Style.RESET_ALL + (
            " " * get_split(len(h2_string), max_length)[1]) + "|")
    print("+" + ("-" * max_length) + "+")

    # - main -#
    for id, key in enumerate(column_selections):
        if column_selections[key] and id != __global_simulation_location:
            # This is not currently selected but is on
            string_modifier = Fore.WHITE + Back.GREEN
        elif column_selections[key] and id == __global_simulation_location:
            # This is the current selection
            string_modifier = Fore.GREEN + Back.WHITE
        elif not column_selections[key] and id == __global_simulation_location:
            string_modifier = Fore.BLACK + Back.WHITE
        else:
            string_modifier = Fore.GREEN

        print("|" + string_modifier + (" " * get_split(len(key), max_length)[0]) + key + (
                " " * get_split(len(key), max_length)[1]) + Style.RESET_ALL + "|")

    print("+" + ("-" * max_length) + "+")


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------- Sub-Selection Functions -----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_columns(current_selection: list = None) -> list:
    """
    allows the user to select new columns to place in the simulation viewer.
    Returns: List of the resulting simulation columns.
    -------

    """
    # Declaring globals
    global __subcycle_check  # This is how we tell the keyboard when to end the loop
    global __global_simulation_location
    global __global_command
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%sget_columns: " % _dbg_string
    log_print("Selecting columns...", fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    __global_simulation_location = 0  # setting the location to 0.
    __global_command = None  # setting the command to None.

    # - Do we have any current selection? -#
    if not current_selection:
        current_selection = []

    # - grab available columns -#
    available_columns = simlog.columns(type="any")  # grab all of the possible column headers.
    available_columns = [col for col in available_columns if col != "SimulationName"]
    available_columns = ["SimulationName"] + available_columns

    # - constructing the on-off dict -#
    column_selection_dict = {column: (True if column in current_selection else False) for column in available_columns}

    # Main Loop
    ####################################################################################################################
    __subcycle_check = False  # Set the global loop to false. This must be reverted in the outer scope.

    while not __subcycle_check:  # we all for selection.
        os.system('cls' if os.name == 'nt' else 'clear')
        print_columns(column_selection_dict, __global_simulation_location)

        listen_keyboard(on_press=select_column_menu_on_press)

        # - Recieving commands -#
        if __global_command == "enter":
            column_selection_dict[list(column_selection_dict.keys())[__global_simulation_location]] = not \
                column_selection_dict[list(column_selection_dict.keys())[__global_simulation_location]]
            __global_command = None
        else:
            # - this is not a meaningful command
            pass
    __subcycle_check = False
    return [key for key, value in column_selection_dict.items() if value]


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------- Keyboard Surveillance -----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def navigate_menu_on_press(key):
    """
    Key press function for simulation list.
    Parameters
    ----------
    key

    Returns
    -------

    """
    # grabbing globals
    global __global_simulation_location
    global __global_command
    ## Managing key entering ##
    try:
        if key == "down":
            __global_simulation_location = (
                __global_simulation_location + 1 if __global_simulation_location != len(simlog) - 1 else 0)
            stop_listening()
        elif key == "up":
            __global_simulation_location = (
                __global_simulation_location - 1 if __global_simulation_location != 0 else len(simlog) - 1)
            stop_listening()
        elif key == "c":
            __global_command = "c"
            stop_listening()
        elif key == "x":
            __global_command = "x"
            stop_listening()
        elif key == "d":
            __global_command = "d"
            stop_listening()
        elif key == "enter":
            __global_command = "enter"
            stop_listening()
    except AttributeError as ex:
        print(ex)


def select_column_menu_on_press(key):
    """
        Key press function for column menu selection.
        Parameters
        ----------
        key

        Returns
        -------

        """
    # grabbing globals
    global __global_simulation_location
    global __global_command
    global __subcycle_check

    ## Managing key entering ##
    try:
        if key == "down":
            __global_simulation_location = (
                __global_simulation_location + 1 if __global_simulation_location != len(
                    simlog.columns(type='any')) - 1 else 0)
            stop_listening()
        elif key == "up":
            __global_simulation_location = (
                __global_simulation_location - 1 if __global_simulation_location != 0 else len(
                    simlog.columns(type='any')) - 1)
            stop_listening()
        elif key == "enter":
            __global_command = "enter"
            stop_listening()
        elif key == "x":
            __subcycle_check = True
            stop_listening()
    except AttributeError as ex:
        print(ex)


if __name__ == '__main__':
    set_log(_filename)
    # Setup
    ####################################################################################################################
    displayed_columns = ["SimulationName", "Description", "SimulationLocation"]  # The displayed columns
    message = None
    __global_simulation_location = 0
    # Main Loop
    ####################################################################################################################
    exit_loop = False  # bool for loop maintenance

    while not exit_loop:
        os.system('cls' if os.name == 'nt' else 'clear')
        # Recalculating needed values if an update has occurred
        ################################################################################################################
        if __global_update_check:  # we need to recompute the calcs based on the edits to the simlog
            calcs = get_print_calculations(columns=displayed_columns)
            __global_update_check = False  # resetting the calcs
            message = None

        # Printing
        ################################################################################################################
        print_simlog(calcs=calcs, location=__global_simulation_location, message=message)
        # Command Surveillance
        ################################################################################################################
        listen_keyboard(on_press=navigate_menu_on_press)  ### Waiting for the keyboard to select an entry.

        # - Getting commands -#
        if __global_command:
            # We have a command to manage
            if __global_command == "c":
                # We are doing a column change

                # - Saving our positions and the like -#
                temp_location = __global_simulation_location

                displayed_columns = get_columns(displayed_columns)

                __global_simulation_location = temp_location
                __global_command = None
                __global_update_check = True
            elif __global_command == "x":
                # We are exiting
                exit_loop = True
            elif __global_command == "d":
                # We are deleting the associated simulation #
                # - Grabbing necessary variables -#
                simulation = list(simlog.keys())[__global_simulation_location]
                os.system('cls' if os.name == 'nt' else 'clear')

                # - Getting user confirmation -#
                try:
                    user_sure = get_yes_no("Delete simulation %s at %s" % (
                        simlog[simulation]["SimulationName"], simlog[simulation]["SimulationLocation"]))
                except Exception:
                    # - Something was missing -#
                    message = Fore.RED + "Failed to remove the simulation %s because it does not have a location." + Style.RESET_ALL
                    user_sure = False

                # - Executing -#
                if user_sure:
                    # delete
                    del simlog[simulation]
                else:
                    pass

                # - cleanup -#
                __global_command = None
                __global_update_check = True
            elif __global_command == "enter":
                # we have selected an item #
                simulation = list(simlog.keys())[__global_simulation_location]
                os.system('cls' if os.name == 'nt' else 'clear')
                print("[%s]" % (Fore.LIGHTMAGENTA_EX + simulation + Style.RESET_ALL))

                for item, value in simlog[simulation].items():
                    print("[%s]: %s" % (Fore.GREEN + item + Style.RESET_ALL, value))

                input("\nPress [%s] to return..." % (Fore.RED + "enter" + Style.RESET_ALL))

                __global_command = None
        else:
            # There was no command
            pass
    ####################################################################################################################
    # Exiting
    ####################################################################################################################
    exit()
