"""

Useful text utility functions for use in larger system. Written by: Eliza Diggins

"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from colorama import Fore, Style, Back
from PyCS_Core.Logging import set_log, log_print
from PyCS_Core.Configuration import _configuration_path, read_config
import pathlib as pt
from copy import deepcopy
import os
from functools import reduce  # forward compatibility for Python 3
import operator
import numpy as np
from sshkeyboard import listen_keyboard, stop_listening
import subprocess
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# For keyboard manipulation systems. Can store any variable as necessary temporarily. Used in many scripts.
__GSV = {}


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Sub-Functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


def pullValues(dict):
    """
    Pulls values only for the dict instead of tuple based options
    Parameters
    ----------
    dict

    Returns
    -------

    """
    ret_dict = {}
    for key, value in dict.items():
        if isinstance(value, list) or isinstance(value, tuple):
            ret_dict[key] = value[0]
        elif isinstance(value, dict):
            ret_dict[key] = pullValues(dict[key])
        else:
            pass
    return ret_dict


def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


def rclone_listdir(directory) -> tuple:
    """
    List directory for rclone
    """
    # intro debugging
    fdbg_string = _dbg_string + "rclone_listdir: "
    log_print("Attempting to listdir of %s." % directory, fdbg_string, "debug")

    # performing the command #
    output = subprocess.check_output(["rclone", "lsf", directory, "--max-depth", "1"])
    output = output.decode("utf8").split("\n")[:-1]

    ## checking for files ##
    type = [False if "/" in item else True for item in output]

    return (output, type)


def set_simulation_information():
    return pullValues(get_options({
        "SimulationName": ("None", "None", "The name of the simulation"),
        "Description": ("None", "None", "The description of the simulation"),
        "NMLFile": ("None", "None", "The name of the generated nml file")
    }, "Simulation Options"))


def print_option_dict(dict, location, header=None):
    """
    Prints the option dictionary.
    Parameters
    ----------
    dict
    header
    calcs
    color_dict

    Returns
    -------

    """
    print("#" * 100)
    if not header:
        header = ["Value", "Default"]
    for key, value in dict.items():
        ### Printing the selected item ###
        if location != key:
            print("[ %s ]" % (Fore.RED + Style.BRIGHT + str(key) + Style.RESET_ALL), end="")
        else:
            print(Fore.BLACK + Back.WHITE + Style.DIM + "[ %s ]" % str(key) + Style.RESET_ALL, end="")

        if isinstance(value, tuple):
            for id, head in enumerate(header):  # print the header section...
                if head == "Value":  # This is the value header...
                    print(Fore.CYAN + Style.BRIGHT + " Value" + Style.RESET_ALL + "=%s |" % str(value[id]), end="")
                else:
                    print(" %s=%s |" % (head, Style.DIM + str(value[id]) + Style.RESET_ALL), end="")
        else:
            # Its a dict. pass
            pass
        print("")
    print("#" * 100)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Keyboard --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_options_on_press(key):
    """
    Key press function for get options.
    Parameters
    ----------
    key

    Returns
    -------

    """
    # grabbing globals
    global __GSV

    ## Managing key entering ##
    try:
        if key == "enter":
            # do something
            sub_dict_key = __GSV["selected_key"]
            if isinstance(__GSV["sub_dict"][sub_dict_key], tuple):
                pass
            elif not len(__GSV["sub_dict"][sub_dict_key]):
                pass
            else:
                __GSV["location"].append(__GSV["selected_key"])
                __GSV["reset"] = True
            stop_listening()
        elif key == "e":
            sub_dict_key = __GSV["selected_key"]
            if isinstance(__GSV["sub_dict"][sub_dict_key], tuple):
                __GSV["command"] = "edit"
            else:
                __GSV["location"].append(__GSV["selected_key"])

            __GSV["reset"] = True
            stop_listening()
        elif key == "d":
            sub_dict_key = __GSV["selected_key"]
            if isinstance(__GSV["sub_dict"][sub_dict_key], tuple):
                __GSV["command"] = "default"
            else:
                __GSV["location"].append(__GSV["selected_key"])

            __GSV["reset"] = True
            stop_listening()
        elif key == "backspace":
            if __GSV["location"] != []:
                __GSV["location"] = __GSV["location"][:-1]
            else:
                __GSV["command"] = "exit"
            __GSV["reset"] = True
            stop_listening()
        elif key == "down":
            key_id = __GSV["keys"].index(__GSV["selected_key"])
            __GSV["selected_key"] = (
                __GSV["keys"][key_id + 1] if __GSV["selected_key"] != __GSV["keys"][-1] else __GSV["keys"][0])
            stop_listening()
        elif key == "up":
            key_id = __GSV["keys"].index(__GSV["selected_key"])
            __GSV["selected_key"] = (
                __GSV["keys"][key_id - 1] if __GSV["selected_key"] != __GSV["keys"][0] else __GSV["keys"][-1])
            stop_listening()
    except AttributeError as ex:
        print(ex)


def generate_command_on_press(key):
    """
    Key press function for get options.
    Parameters
    ----------
    key

    Returns
    -------

    """
    # grabbing globals
    global __GSV

    ## Managing key entering ##
    try:
        if key == "enter":
            __GSV["command"] = "e"
            stop_listening()
        elif key == "d":
            __GSV["command"] = "d"
            stop_listening()
        elif key == "a":
            __GSV["command"] = "a"
            stop_listening()
        elif key == "backspace":
            __GSV["command"] = "end"
            stop_listening()
        elif key == "down":
            __GSV["location_index"] = (
                __GSV["location_index"] + 1 if __GSV["location_index"] != len(__GSV["selected_commands"]) - 1 else 0)
            stop_listening()
        elif key == "up":
            __GSV["location_index"] = (
                __GSV["location_index"] - 1 if __GSV["location_index"] != 0 else len(__GSV["selected_commands"]) - 1)
            stop_listening()
    except AttributeError as ex:
        print(ex)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- Functions --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def print_title(title, author, width=64, str_struct="#-+-#", boundary="|"):
    """
    Prints the title and author for a given program without having to hard code in different scripts
    :param title: the title to print
    :param author: the author to print.
    :return: The resultant string.
    """
    ## doing the math ##
    if width % len(str_struct) != 0:  # the width is not divisible
        width -= width % len(str_struct)

    reps = int(width / len(str_struct))
    title_left_over = width - len(title)
    if title_left_over % 2 == 0:  # then this is divisible by two,
        t_shift = int(title_left_over / 2)
    else:
        t_shift = int((title_left_over - 1) / 2)
    author_left_over = width - len(author)
    if author_left_over % 2 == 0:  # then this is divisible by two,
        a_shift = int(author_left_over / 2)
    else:
        a_shift = int((author_left_over - 1) / 2)

    string = str_struct * reps + "\n"  # This is the first line.
    string += boundary + (" " * (width - 2)) + "%s\n" % boundary
    string += boundary + (" " * (t_shift - 1)) + Style.BRIGHT + Fore.RED + title + Style.RESET_ALL + (
            " " * (width - 1 - len(title) - t_shift)) + "%s\n" % boundary
    string += boundary + (" " * (a_shift - 1)) + Style.BRIGHT + Fore.RED + author + Style.RESET_ALL + (
            " " * (width - 1 - len(author) - a_shift)) + "%s\n" % boundary
    string += str_struct * reps  # This is the first line.

    print(string)


def get_options(option_dict, title):
    """
    Grab options from the given dictionary.

    Dictionary format:

    A = {option1:(default,desc),
        option2:(default,desc),
        option3: {
            option1...
        }
    :param option_dict: The dictionary to read as the option
    :param title:
    :return:
    """
    global __GSV  # using the global variable for storing the important data.
    # Intro logging #
    fdbg_string = "%sget_options: " % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "SETTING WIZARD" + Style.RESET_ALL + "]: "

    ### Pre-run data setup.
    header = ["Value", "Default", "Description"]
    setting_commands = {
        "n": "Exit/Finish - Move down a level.",
        "e": "Edit - Move to.",
        "d": "Reset option to default",
    }
    # startup copy and settting #
    settings = deepcopy(option_dict)  # create the copy we are going to use for the setting storage.

    ########################################################################################################################
    #                                       MAIN CYCLE
    ########################################################################################################################
    CHECK_DONE = False  # whole scope check for finish.
    new_calcs = True  # This flag lets us skip calculations if they aren't necessary.
    __GSV = {
        "location": [],
        "selected_key": None,
        "sub_dict": {},
        "keys": [],
        "command": None,
        "reset": True
    }
    while not CHECK_DONE:  # we are still cycling'

        ## Setting the title ##
        if __GSV["location"] == []:  # we have no location
            print_title(title, "Location: MAIN")
        else:
            loc_string = "Location: "
            for loc in __GSV["location"]:
                loc_string += "--> %s " % loc
            print_title(title, loc_string)

        #
        #       PRINTING ------------------------
        #
        # Grabbing the necessary information #
        if __GSV["reset"]:
            __GSV["sub_dict"] = getFromDict(settings, __GSV["location"])
            __GSV["keys"] = list(__GSV["sub_dict"].keys())
            __GSV["selected_key"] = list(__GSV["sub_dict"].keys())[0]
            __GSV["reset"] = False

        print_option_dict(__GSV["sub_dict"], __GSV["selected_key"], header=header)

        #
        #       NAVIGATION ------------------------
        #
        listen_keyboard(on_press=get_options_on_press)  ### Waiting for the keyboard to select an entry.

        if __GSV["command"]:  # we have a command to execute
            if __GSV["command"] == "exit":
                ### We are exiting the program
                CHECK_DONE = True
                return settings
            elif __GSV["command"] == "edit":
                ### We are editing the selection.
                inp = input(
                    "%sPlease enter a new value for %s. ['n' to return]:" % (cdbg_string, __GSV["selected_key"]))
                if inp != "n":
                    old_tuple = list(__GSV["sub_dict"][__GSV["selected_key"]])
                    old_tuple[0] = inp
                    setInDict(settings, __GSV["location"] + [__GSV["selected_key"]], tuple(old_tuple))
                    __GSV["command"] = None
                else:
                    __GSV["command"] = None
            elif __GSV["command"] == "default":
                ### We are editing the selection.
                old_tuple = list(__GSV["sub_dict"][__GSV["selected_key"]])
                old_tuple[0] = old_tuple[1]
                setInDict(settings, __GSV["location"] + [__GSV["selected_key"]], tuple(old_tuple))
                __GSV["command"] = None
            else:
                __GSV["command"] = None

        os.system('cls' if os.name == 'nt' else 'clear')
    return settings


def file_select(directory: str, conditions=None, search_for_description=True):
    """
    Allows the user to select files from a specific list based on a given directory.

    Conditions can be used to set up a discrimination system.
    :param directory: The directory, should be a string
    :param conditions: lambda function (file), returning true to include in list.
    :return:
    """
    # debug strings #
    fdbg_string = "%sfile_select:" % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: "

    # starting #
    print(("#" * 24) + " File Selection " + ("#" * 24))
    print("#" + Fore.RED + "Directory" + Style.RESET_ALL + ": " + directory)

    ### Finding valid files ###
    if conditions != None:
        files = [file for file in os.listdir(directory) if conditions(file)]
    else:
        files = os.listdir(directory)
    print("#" + Fore.RED + "Files" + Style.RESET_ALL + ": " + str(len(files)))
    print("#" * 64)

    ### checking for 0 length ###
    if not len(files):
        print("%sFailed to find any files meeting these criteria. Exiting..." % fdbg_string)
        exit()

    ### Managing descriptions ###
    descriptions = {}  # this will hold the descriptions
    if search_for_description:

        for file in files:  # cycle through each of the files
            if os.path.isfile(os.path.join(directory, file)):
                with open(os.path.join(directory, file), "r+") as f:
                    try:
                        first_line = f.readline()  # read the first line
                        if "#DESC:" in first_line:
                            # there is a description
                            descriptions[file] = (
                                first_line.replace("#DESC:", "").replace("\n", "") if first_line.replace("#DESC:",
                                                                                                         "") != "None" else "No Description...")
                        else:
                            descriptions[file] = "No Description"
                    except UnicodeError:
                        descriptions[file] = "Non-descriptable file"
            else:
                descriptions[file] = "Directory"
    else:
        for file in files:
            descriptions[file] = "No Description..."

    ### print maths ###
    max_length = np.amax([len(file) for file in files])  # grabbing the maximal length of the filename.
    length_difference = {
        file: (max_length + 2) - len(file) for file in files
    }

    ### selecting ###
    selection_check = False
    while not selection_check:
        # We have not selected our file yet.
        for id, file in enumerate(files):
            # We cycle through all of the files.
            print("[%s] %s%s|%s" % (
                Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                Fore.BLUE + Style.BRIGHT + file + Style.RESET_ALL,
                (" " * length_difference[file]),
                Fore.WHITE + descriptions[file] + Style.RESET_ALL
            ))
        print("#" * 64)
        tmp_input = input("%sPlease select a file: " % cdbg_string)  # selecting a file

        if not tmp_input.isdigit():  # the temp input is not actually a number:
            input("%sFailed to recognize option %s. Input should be an integer. Press any key to try again..." % (
                cdbg_string, tmp_input))
        else:
            # This input was a digit we need to check it.
            tmp_value = int(tmp_input) - 1  # grabbing the correct index value.

            if 0 <= tmp_value <= len(files) - 1:  # this is a valid selection
                selected_file = files[tmp_value]  # grab the selected file.
                selection_check = True
            else:
                input("%sInput %s is too large. Maximum value is %s. Press any key to try again..." % (
                    cdbg_string, tmp_input, len(files)))

        os.system('cls' if os.name == 'nt' else 'clear')

        # Re-printing
        if not selection_check:
            print(("#" * 24) + " File Selection " + ("#" * 24))
            print("#" + Fore.RED + "Directory" + Style.RESET_ALL + ": " + directory)
            print("#" + Fore.RED + "Files" + Style.RESET_ALL + ": " + str(len(files)))
            print("#" * 64)
    print("%sSelected %s." % (cdbg_string, selected_file))  # --> This cannot actually be escaped.
    return selected_file


def generate_command_sequence(commands_dict, commands_dict_data, **kwargs):
    # Intro debugging
    ########################################################################################################################
    os.system('cls' if os.name == 'nt' else 'clear')  # clearing the screen
    fdbg_string = _dbg_string + "generate_command_sequence: "
    cdbg_string = Fore.CYAN + Style.BRIGHT + fdbg_string + Style.RESET_ALL + "[" + Fore.GREEN + Style.BRIGHT + "Settings Wizard" + Style.RESET_ALL + "]: "
    log_print("Initiating the command sequence generator", fdbg_string, "debug")

    # Setup
    ########################################################################################################################
    global __GSV  # This is what we will use to interact with the keyboard logger.
    __GSV["location_index"] = 0
    selected_commands = []  # this dict stores the commands as they are selected.
    __GSV["main_cycle_update_check"] = True

    # Main Cycle: Here we are adding and removing and editing commands
    ########################################################################################################################
    main_runtime_check = False  # toggle lock for the main loop
    while not main_runtime_check:  # beginning the main loop.
        # updating
        ####################################################################################################################
        __GSV["command"] = False
        if __GSV["main_cycle_update_check"]:
            __GSV["selected_commands"] = selected_commands  # reproducing the check on selected objects.
            __GSV["main_cycle_update_check"] = False
        # Printing
        ####################################################################################################################
        # - Printing the title -#
        print_title("Command Select (version %s)" % CONFIG["system"]["version"], "Written by: Eliza Diggins")

        # - printing the main section -#
        print("+" + ("-" * 64) + "+")
        if not len(list(selected_commands)):
            print("[%s] No commands entered..." % (Fore.RED + "-" + Style.RESET_ALL))
        else:
            for index, command in enumerate(selected_commands):  # cycle through all of the commands
                if __GSV["location_index"] == index:  # We are positioned here
                    print("[%s]\t%s" % (Fore.BLACK + Back.WHITE + command["name"] + Style.RESET_ALL,
                                        Fore.CYAN + command["path"] + Style.RESET_ALL))
                else:
                    print("[%s]\t%s" % (Fore.RED + Style.BRIGHT + command["name"] + Style.RESET_ALL,
                                        Fore.CYAN + command["path"] + Style.RESET_ALL))
        print("+" + ("-" * 64) + "+")
        print("|COMMANDS:")
        print("|%s: Add a new command." % (Fore.RED + Style.BRIGHT + "a" + Style.RESET_ALL))
        print("|%s: Edit an existing command." % (Fore.RED + Style.BRIGHT + "enter" + Style.RESET_ALL))
        print("|%s: Finish." % (Fore.RED + Style.BRIGHT + "backspace" + Style.RESET_ALL))
        print("|%s: Delete." % (Fore.RED + Style.BRIGHT + "d" + Style.RESET_ALL))
        print("+" + ("-" * 64) + "+")
        # Keyboard listening
        ####################################################################################################################
        listen_keyboard(on_press=generate_command_on_press)

        # Command parsing
        ####################################################################################################################
        if __GSV["command"] != False:  # there is a command to execute.
            # We are deleting the given entry. #
            if __GSV["command"] == "d":
                del selected_commands[__GSV["location_index"]]
                __GSV["main_cycle_update_check"] = True

            # We are editing the values
            elif __GSV["command"] == "e":
                __GSV_temp_copy = deepcopy(__GSV)  # creating local copy of __GSV to free it up
                os.system('cls' if os.name == 'nt' else 'clear')
                selected_commands[__GSV_temp_copy["location_index"]]["options"] = get_options(
                    selected_commands[__GSV_temp_copy["location_index"]]["options"],
                    "%s Options" % selected_commands[__GSV_temp_copy["location_index"]]["name"])
                __GSV = __GSV_temp_copy
            # If we are ending the program
            elif __GSV["command"] == "end":
                main_runtime_check = True  # end the main runtime check.
            # We are adding a new item.
            elif __GSV["command"] == "a":
                # selecting the new command to use #
                __GSV_temp_copy = deepcopy(__GSV)  # creating local copy of __GSV to free it up

                # Selecting a new command #
                os.system('cls' if os.name == 'nt' else 'clear')
                new_command = option_menu([key for key in list(commands_dict.keys())],
                                          {key: value["desc"] for key, value in commands_dict.items()},
                                          "Command Selection")

                # We are now applying any presets that need to be used #
                option_dict = commands_dict[new_command]["options"]  # this is what we will use to get options
                for key, value in kwargs.items():  # cycle through any pre-determined kwargs.
                    if key in option_dict:  # we have a match
                        option_dict[key] = tuple([value] + list(option_dict[key][1:]))
                    else:
                        pass
                # entering settings for the command #
                os.system('cls' if os.name == 'nt' else 'clear')
                options = get_options(option_dict, "%s Options" % new_command)

                # adding the command to our list of commands #
                os.system('cls' if os.name == 'nt' else 'clear')
                new_command_dict = deepcopy(commands_dict[new_command])
                new_command_dict["name"] = new_command
                new_command_dict["options"] = options

                selected_commands.append(new_command_dict)

                __GSV = __GSV_temp_copy
        os.system('cls' if os.name == 'nt' else 'clear')

    ### Generating the command string ###
    string = ""
    for command in selected_commands:
        command_path = command["path"]
        string += "%s %s " % (CONFIG["system"]["executables"]["python_full"], command_path)

        for key, value in command["options"].items():
            if value[0] != "":  # this option is actually set and should appear.
                if key[0] == "-":  # this is a dashed command
                    if commands_dict_data[command["name"]]["options"][key] == "b":
                        if value[0] in ["true", "True"]:
                            string += "%s " % key
                        else:
                            pass
                    elif commands_dict_data[command["name"]]["options"][key] == "l":
                        string += "%s %s " % (key, value[0])
                    else:
                        string += "%s '%s' " % (key, value[0])
                else:
                    string += "'%s' " % (value[0])
        string += "\n"
    return string


def file_directory_select(directory_dict: dict):
    """
       Allows the user to select files from a specific list based on a given set of directories.

    :param directory_dict: The dictionary of paths and names to use for sorting.
    """
    dir_commands = {
        "n": "Step back a level / finish.",
        "m": "Move up a level into the selected directory",
        "s": "Select a given directory or file.",
        "r": "Remove a selected file from the selected files list."
    }  # Directory commands
    # debug strings #
    fdbg_string = "%sfile_directory_select:" % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: "

    # starting location management #
    location = "MAIN"  # this is where we store our current location in the file system.

    ### checking for 0 length ###
    if not len(directory_dict):
        print("%sNo directory_dict was passed. Exiting..." % fdbg_string)
        exit()

    ### selecting ###
    selected_directories = {}  # these are the selected directories we will use later. dict for storing recur.
    selection_check = False
    while not selection_check:
        # We have not selected our file yet.

        # printing a title #
        print_title("File / Directory Selector", "Author: Eliza Diggins")
        # printing additional useful information
        print("+" + ("-" * (16 + len(location))) + "+")
        print("|-  " + Fore.RED + Style.BRIGHT + "Location: " + Style.RESET_ALL + location + "  -|")
        print("+" + ("-" * (16 + len(location))) + "+")

        print(("#" * 23) + " Directories " + ("#" * 23))

        ### grabbing available files ###
        if location == "MAIN":
            ### We are reading the directories directly from the input, we need all three pieces of info.
            directories = {key: {
                "path": directory_dict[key],
                "source": key
            } for key in directory_dict if key not in selected_directories
            }
        else:
            # We determine source based on if the item path contains one of the directory dicts.
            directories = {
                i: {
                    "path": os.path.join(location, i),
                    "source": [item for item in directory_dict if directory_dict[item] in location][0]
                }
                for i in os.listdir(location) if i not in selected_directories
            }
        for id, directory in enumerate(directories):
            # we cycle through all of the directories
            if os.path.isfile(directories[directory]["path"]):  # this is a file.
                print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                            Fore.GREEN + Style.BRIGHT + directory + Style.RESET_ALL,
                                            Fore.WHITE + Style.DIM + directories[directory]["path"] + Style.RESET_ALL))
            else:  # this is a dir.
                print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                            Fore.BLUE + Style.BRIGHT + directory + Style.RESET_ALL,
                                            Fore.WHITE + Style.DIM + directories[directory]["path"] + Style.RESET_ALL))
        print(("#" * 59))
        print("#" + ("-" * 17) + " Selected  Directories " + ("-" * 17) + "#")
        print(("#" * 59))
        if len(selected_directories) == 0:
            print(Fore.CYAN + "None" + Style.RESET_ALL)
        else:
            for id, directory in enumerate(selected_directories):
                # we cycle through all of the directories
                if os.path.isfile(selected_directories[directory]["path"]):  # this is a file.
                    print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                                Fore.GREEN + Style.BRIGHT + directory + Style.RESET_ALL,
                                                Fore.WHITE + Style.DIM + selected_directories[
                                                    directory]["path"] + Style.RESET_ALL))
                else:  # this is a dir.
                    print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                                Fore.BLUE + Style.BRIGHT + directory + Style.RESET_ALL,
                                                Fore.WHITE + Style.DIM + selected_directories[
                                                    directory]['path'] + Style.RESET_ALL))
        print(("#" * 59))

        print(Fore.RED + "Commands:" + Style.RESET_ALL)
        for option in dir_commands:
            print("%s: %s" % (Fore.RED + option + Style.RESET_ALL, dir_commands[option]))
        print("#" * 64)
        ### DONE PRINTING ###

        ### Grabbing user input for command selection
        command_input = input("%sPlease enter a command:" % cdbg_string)

        ### Managing different command types ###
        if command_input in ["m", "M", "s", "S"]:
            ######################################################
            #
            #       These are commands which require selecting a directory
            #
            ######################################################
            check = False

            # Checking if there are actually options to choose.
            if not len(directories):  # we need to move back
                input("%sThere are no directories on this level. Press any key to proceed..." % (
                    cdbg_string))
                check = True
                command_input = "n"

            while check == False:  # We now need to select an item to actually edit.
                opinp = input(
                    "%sWhich item would you like to select? [1:%s]: " % (cdbg_string, len(directories)))
                if not opinp.isdigit() and opinp not in ["n", "N"]:  # the input wasn't a digit or "n"
                    failure_reason_string = "Invalid Selection"
                elif opinp in ["n", "N"]:
                    command_input = "n"  # this will cause us to pass through
                    check = True
                else:
                    # This is a digit and we now need to check if its reasonable.
                    if 1 <= int(opinp) <= len(directories):
                        # This is a good selection.
                        check = True
                        selected_index = int(opinp) - 1
                    else:
                        failure_reason_string = "No item %s" % int(opinp)

                if not check:
                    opinp = input("%s%s! Use 'n' to go back. Which item would you like to select? [1:%s]: " % (
                        cdbg_string, failure_reason_string, len(directories)))

            #
            ### -- We have selected an item and a command.
            #
            if command_input in ["s", "S"]:
                # We are selecting an item.
                selected_item = list(directories.keys())[selected_index]  # grab the actual name if the item.

                selected_directories[selected_item] = directories[selected_item]
            elif command_input in ["m", "M"]:
                # we are moving into a directory.
                selected_item = list(directories.keys())[selected_index]  # grab the actual name if the item.

                ### Checking for reasonability
                if os.path.isfile(directories[selected_item]["path"]):  # this is a file, not a directory.
                    input("%sThe selected item (%s) is a file, not a directory. Press any key to proceed..." % (
                        cdbg_string, selected_item))
                else:
                    ### This is a directory.
                    location = directories[selected_item]["path"]
            else:
                pass
        elif command_input in ["r", "R"]:  # We are removing from our original list
            ######################################################
            #
            #       These are commands which require selecting a selected directory
            #
            ######################################################
            check = False
            opinp = input(
                "%sWhich item would you like to select? [1:%s]: " % (cdbg_string, len(selected_directories)))
            while check == False:  # We now need to select an item to actually edit.
                if not opinp.isdigit() and opinp not in ["n", "N"]:  # the input wasn't a digit or "n"
                    failure_reason_string = "Invalid Selection"
                elif opinp in ["n", "N"]:
                    check = True
                else:
                    # This is a digit and we now need to check if its reasonable.
                    if 1 <= int(opinp) <= len(selected_directories):
                        # This is a good selection.
                        check = True
                        selected_index = int(opinp) - 1
                    else:
                        failure_reason_string = "No item %s" % int(opinp)

                if not check:
                    opinp = input("%s%s! Use 'n' to go back. Which item would you like to select? [1:%s]: " % (
                        cdbg_string, failure_reason_string, len(selected_directories)))

            #
            ### -- We have selected an item and a command.
            #
            if command_input in ["r", "R"]:
                # We are selecting an item.
                selected_item = list(selected_directories.keys())[selected_index]  # grab the actual name if the item
                del selected_directories[selected_item]
            else:
                pass
        elif command_input in ["n", "N"]:  # We are desending a level
            # We are descending a level
            if location == "MAIN":  # we are already at the bottom. This ends to setting gathering
                selection_check = True
                return selected_directories  # returning the directories we selected.
            elif location in [directory_dict[name] for name in directory_dict]:  # we are only 1 level above MAIN
                location = "MAIN"
            else:
                # We are not at the main directory. We need to actually move up a level.
                location = str(pt.Path(location).parents[0])
        else:  # that command doesn't exist.
            input("%sFailed to recognize command %s. Press any key to try again..." % (
                cdbg_string, command_input))

        os.system('cls' if os.name == 'nt' else 'clear')

    ### We have finished selecting the items
    return selected_directories


def rclone_file_directory_select():
    """
       Allows the user to select files from a specific list based on a given set of directories. [RCLONE Version]

    :param directory_dict: The dictionary of paths and names to use for sorting.
    """
    dir_commands = {
        "n": "Step back a level / finish.",
        "m": "Move up a level into the selected directory",
        "s": "Select a given directory or file.",
        "r": "Remove a selected file from the selected files list."
    }  # Directory commands
    # debug strings #
    fdbg_string = "%sfile_directory_select:" % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: "

    # starting location management #
    location = CONFIG["files"]["rclone"][
        "rclone_start_directory"]  # this is where we store our current location in the file system.

    # grabbing classification paths #
    status_items = rclone_listdir(location)[0]
    status_items = [i[:-1] for i in status_items]  # removing trailers.
    ### selecting ###
    selected_directories = {}  # these are the selected directories we will use later. dict for storing recur.
    selection_check = False
    while not selection_check:
        # We have not selected our file yet.

        # printing a title #
        print_title("File / Directory Selector [RCLONE]", "Author: Eliza Diggins")
        # printing additional useful information
        print("+" + ("-" * (16 + len(location))) + "+")
        print("|-  " + Fore.RED + Style.BRIGHT + "Location: " + Style.RESET_ALL + location + "  -|")
        print("+" + ("-" * (16 + len(location))) + "+")

        print(("#" * 23) + " Directories " + ("#" * 23))

        ### grabbing available files ###
        directories = {
            name: {"path": os.path.join(location, name), "isfile": status,
                   "source": [item for item in status_items if item in os.path.join(location, name)][0]}
            for name, status in zip(*rclone_listdir(location)) if name not in selected_directories
        }
        for id, directory in enumerate(directories):
            # we cycle through all of the directories
            if directories[directory]["isfile"]:  # this is a file.
                print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                            Fore.GREEN + Style.BRIGHT + directory + Style.RESET_ALL,
                                            Fore.WHITE + Style.DIM + directories[directory]["path"] + Style.RESET_ALL))
            else:  # this is a dir.
                print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                            Fore.BLUE + Style.BRIGHT + directory + Style.RESET_ALL,
                                            Fore.WHITE + Style.DIM + directories[directory]["path"] + Style.RESET_ALL))
        print(("#" * 59))
        print("#" + ("-" * 17) + " Selected  Directories " + ("-" * 17) + "#")
        print(("#" * 59))
        if len(selected_directories) == 0:
            print(Fore.CYAN + "None" + Style.RESET_ALL)
        else:
            for id, directory in enumerate(selected_directories):
                # we cycle through all of the directories
                if selected_directories[directory]["isfile"]:  # this is a file.
                    print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                                Fore.GREEN + Style.BRIGHT + directory + Style.RESET_ALL,
                                                Fore.WHITE + Style.DIM + selected_directories[
                                                    directory]["path"] + Style.RESET_ALL))
                else:  # this is a dir.
                    print("[%s] %s     | %s" % (Fore.RED + Style.BRIGHT + str(id + 1) + Style.RESET_ALL,
                                                Fore.BLUE + Style.BRIGHT + directory + Style.RESET_ALL,
                                                Fore.WHITE + Style.DIM + selected_directories[
                                                    directory]["path"] + Style.RESET_ALL))
        print(("#" * 59))

        print(Fore.RED + "Commands:" + Style.RESET_ALL)
        for option in dir_commands:
            print("%s: %s" % (Fore.RED + option + Style.RESET_ALL, dir_commands[option]))
        print("#" * 64)
        ### DONE PRINTING ###

        ### Grabbing user input for command selection
        command_input = input("%sPlease enter a command:" % cdbg_string)

        ### Managing different command types ###
        if command_input in ["m", "M", "s", "S"]:
            ######################################################
            #
            #       These are commands which require selecting a directory
            #
            ######################################################
            check = False

            # Checking if there are actually options to choose.
            if not len(directories):  # we need to move back
                input("%sThere are no directories on this level. Press any key to proceed..." % (
                    cdbg_string))
                check = True
                command_input = "n"

            while check == False:  # We now need to select an item to actually edit.
                opinp = input(
                    "%sWhich item would you like to select? [1:%s]: " % (cdbg_string, len(directories)))
                if not opinp.isdigit() and opinp not in ["n", "N"]:  # the input wasn't a digit or "n"
                    failure_reason_string = "Invalid Selection"
                elif opinp in ["n", "N"]:
                    command_input = "n"  # this will cause us to pass through
                    check = True
                else:
                    # This is a digit and we now need to check if its reasonable.
                    if 1 <= int(opinp) <= len(directories):
                        # This is a good selection.
                        check = True
                        selected_index = int(opinp) - 1
                    else:
                        failure_reason_string = "No item %s" % int(opinp)

                if not check:
                    opinp = input("%s%s! Use 'n' to go back. Which item would you like to select? [1:%s]: " % (
                        cdbg_string, failure_reason_string, len(directories)))

            #
            ### -- We have selected an item and a command.
            #
            if command_input in ["s", "S"]:
                # We are selecting an item.
                selected_item = list(directories.keys())[selected_index]  # grab the actual name if the item.

                selected_directories[selected_item] = directories[selected_item]
            elif command_input in ["m", "M"]:
                # we are moving into a directory.
                selected_item = list(directories.keys())[selected_index]  # grab the actual name if the item.

                ### Checking for reasonability
                if directories[selected_item]["isfile"]:  # this is a file, not a directory.
                    input("%sThe selected item (%s) is a file, not a directory. Press any key to proceed..." % (
                        cdbg_string, selected_item))
                else:
                    ### This is a directory.
                    location = directories[selected_item]["path"]
            else:
                pass
        elif command_input in ["r", "R"]:  # We are removing from our original list
            ######################################################
            #
            #       These are commands which require selecting a selected directory
            #
            ######################################################
            check = False
            opinp = input(
                "%sWhich item would you like to select? [1:%s]: " % (cdbg_string, len(selected_directories)))
            while check == False:  # We now need to select an item to actually edit.
                if not opinp.isdigit() and opinp not in ["n", "N"]:  # the input wasn't a digit or "n"
                    failure_reason_string = "Invalid Selection"
                elif opinp in ["n", "N"]:
                    check = True
                else:
                    # This is a digit and we now need to check if its reasonable.
                    if 1 <= int(opinp) <= len(selected_directories):
                        # This is a good selection.
                        check = True
                        selected_index = int(opinp) - 1
                    else:
                        failure_reason_string = "No item %s" % int(opinp)

                if not check:
                    opinp = input("%s%s! Use 'n' to go back. Which item would you like to select? [1:%s]: " % (
                        cdbg_string, failure_reason_string, len(selected_directories)))

            #
            ### -- We have selected an item and a command.
            #
            if command_input in ["r", "R"]:
                # We are selecting an item.
                selected_item = list(selected_directories.keys())[selected_index]  # grab the actual name if the item
                del selected_directories[selected_item]
            else:
                pass
        elif command_input in ["n", "N"]:  # We are desending a level
            # We are descending a level
            if location == CONFIG["files"]["rclone"][
                "rclone_start_directory"]:  # we are already at the bottom. This ends to setting gathering
                selection_check = True
                return selected_directories  # returning the directories we selected.
            else:
                # We are not at the main directory. We need to actually move up a level.
                location = str(pt.Path(location).parents[0])
        else:  # that command doesn't exist.
            input("%sFailed to recognize command %s. Press any key to try again..." % (
                cdbg_string, command_input))

        os.system('cls' if os.name == 'nt' else 'clear')

    ### We have finished selecting the items
    return selected_directories


def option_menu(options, desc=None, title=None):
    """
    Creates an options menu for a user to select from a set of options.
    Parameters
    ----------
    options: The options to use
    desc: The descriptions. Should be a dictionary
    title: The title for the menu.

    Returns: the selected option.
    -------

    """
    ### SETUP ###
    global __GSV  # Grabbing the global source variable.

    # Printing #
    if title:
        print_title(title, "Select an option")
    else:
        print_title("Menu", "Select an option")
    if desc == None:
        desc = {option: "" for option in options}

    ### CYCLE SETUP ###
    selection_check = False
    __GSV["location"] = 0  # This will store our location in the menu
    __GSV["temp_store"] = False  # This will store our choice.

    ### Defining on press items ###
    def on_press(key):
        global __GSV  # Grabbing the global source variable.
        try:
            if key == "enter":
                # do something
                stop_listening()
                __GSV["temp_store"] = options[__GSV["location"]]
            elif key == "down":
                __GSV["location"] = (__GSV["location"] + 1 if __GSV["location"] + 1 <= len(options) - 1 else 0)
                stop_listening()
            elif key == "up":
                __GSV["location"] = (__GSV["location"] - 1 if __GSV["location"] - 1 >= 0 else len(options) - 1)
                stop_listening()
                # do something else
                return False  # Stop listener
        except AttributeError as ex:
            print(ex)

    # Non-Repeat vars #
    max_length = np.amax([len(op) for op in options])  # used for printing
    excess = {option: (max_length + 2) - len(option) for option in options}
    max_len_desc = np.amax([len(des) for des in desc.values()])
    desc_excess = {option: (max_len_desc + 2) - len(desc[option]) for option in options}

    while not selection_check:  # we haven't yet chosen an option to use
        ### Printing ###
        print("+" + ("-" * (max_length + 2)) + "+-" + ("-" * (max_len_desc + 2)) + "+")
        for id, option in enumerate(options):
            if id == __GSV["location"]:
                print("|" + Back.WHITE + Fore.BLACK + option + (" " * excess[option]) + "| " + Style.DIM + desc[
                    option] + (
                              " " * desc_excess[option]) + Style.RESET_ALL + "|")
            else:
                print("|%s" % option + (" " * excess[option]) + "| " + Style.DIM + desc[option] + (
                        " " * desc_excess[option]) + Style.RESET_ALL + "|")
        print("+" + ("-" * (max_length + 2)) + "+-" + ("-" * (max_len_desc + 2)) + "+")

        ### Keyboard reading ###
        listen_keyboard(on_press=on_press)

        ### Clearing the screen ###
        os.system('cls' if os.name == 'nt' else 'clear')

        # Did we get an exit command?
        if __GSV["temp_store"] != False:
            return __GSV["temp_store"]

        # re-print title
        if title:
            print_title(title, "Select an option")
        else:
            print_title("Menu", "Select an option")


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="FILE")
    get_options({"option 1":{
        "setting":("1","1","1")
    },
    "options 2":{}},"something")
