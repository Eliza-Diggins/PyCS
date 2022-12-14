"""

Useful text utility functions for use in larger system. Written by: Eliza Diggins

"""
import sys
import pathlib as pt
import os

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from colorama import Fore, Style
from PyCS_Core.Logging import set_log, log_print
from PyCS_Core.Configuration import _configuration_path, read_config
import pathlib as pt
from copy import deepcopy
import os
from functools import reduce  # forward compatibility for Python 3
import operator
import numpy as np
import subprocess

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Sub-Functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


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

    A = {option1:default,
        option2:default,
        option3: {
            option1...
        }
    :param option_dict: The dictionary to read as the option
    :param title:
    :return:
    """
    # Intro logging #
    fdbg_string = "%sget_options: " % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "SETTING WIZARD" + Style.RESET_ALL + "]: "

    setting_commands = {
        "n": "Exit/Finish - Move down a level.",
        "e": "Edit - Move to.",
        "d": "Reset option to default",
    }
    # startup copy and settting #
    settings = deepcopy(option_dict)  # create the copy we are going to use for the setting storage.

    # starting the cycle #
    CHECK_DONE = False
    location = []  # this is where we will store the location
    while not CHECK_DONE:  # we are still cycling'
        ## Setting the title ##
        if location == []:  # we have no location
            print_title(title, "Location: MAIN")
        else:
            loc_string = "Location: "
            for loc in location:
                loc_string += "--> %s " % loc
            print_title(title, loc_string)

        ### Mangaging the print statements ###
        print("#" * 64)
        sub_dict = getFromDict(settings, location)
        for index, option in enumerate(sub_dict):
            if not isinstance(sub_dict[option], dict):  # This is a dictionary.
                print("[%s] %s = %s   - default: %s" % (Fore.RED + str(index + 1) + Style.RESET_ALL,
                                                        Fore.CYAN + Style.BRIGHT + str(option) + Style.RESET_ALL,
                                                        Fore.GREEN + Style.BRIGHT + str(
                                                            sub_dict[option]) + Style.RESET_ALL,
                                                        Style.DIM + Fore.WHITE + str(getFromDict(option_dict, location)[
                                                                                         option]) + Style.RESET_ALL))
            else:
                print("[%s] %s" % (Fore.RED + str(index + 1) + Style.RESET_ALL,
                                   Fore.BLUE + Style.BRIGHT + option + Style.RESET_ALL))

        print("\n" + "#" * 64)

        ### Grabbing actual Setting options ###
        print(Fore.RED + "Commands:" + Style.RESET_ALL)
        for option in setting_commands:
            print("%s: %s" % (Fore.RED + option + Style.RESET_ALL, setting_commands[option]))
        print("#" * 64)
        ### Setting Selection ###
        inp = input("%sPlease enter a command:" % cdbg_string)

        # parsing command #
        if inp in ["e", "E", "d", "D"]:  # we need to select a option
            check = False
            opinp = input(
                "%sWhich item would you like to select? [1:%s]: " % (cdbg_string, len(list(sub_dict.keys()))))
            while check == False:  # We now need to select an item to actually edit.
                if not opinp.isdigit() and opinp not in ["n", "N"]:  # the input wasn't a digit or "n"
                    failure_reason_string = "Invalid Selection"
                elif opinp in ["n", "N"]:
                    check = True
                else:
                    # This is a digit and we now need to check if its reasonable.
                    if 1 <= int(opinp) <= len(list(sub_dict.keys())):
                        # This is a good selection.
                        check = True
                        selected_index = int(opinp) - 1
                    else:
                        failure_reason_string = "No item %s" % int(opinp)

                if not check:
                    opinp = input("%s%s! Use 'n' to go back. Which item would you like to select? [1:%s]: " % (
                        cdbg_string, failure_reason_string, len(list(sub_dict.keys()))))

            ### Executing the selected command ###
            if inp in ["e", "E"]:
                # We are editing / moving #
                selected_option = list(sub_dict.keys())[selected_index]  # we grab the correct item

                if isinstance(sub_dict[selected_option], dict):  # we are moving into another dict.
                    location.append(selected_option)
                else:
                    # We are actually going to be editing the value
                    edited_value_str = input(
                        "%sEnter a new value for %s: ('n' to go back) " % (cdbg_string, selected_option))
                    if edited_value_str not in ["n", "N"]:
                        setInDict(settings, location + [selected_option], edited_value_str)
                    else:
                        pass
            elif inp in ["d", "D"]:
                # We are returning an item to the default.
                selected_option = list(sub_dict.keys())[selected_index]  # we grab the correct item
                setInDict(settings, location + [selected_option],
                          getFromDict(option_dict, location + [selected_option]))
            else:  # We are returning out of this option
                pass
        elif inp in ["n", "N"]:
            # We need to return #
            if len(location):  # we need to back up a level.
                location = location[:-1]
            else:
                CHECK_DONE = True  # We are exiting the whole program

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
                "path":directory_dict[key],
                "source":key
            } for key in directory_dict if key not in selected_directories
            }
        else:
            # We determine source based on if the item path contains one of the directory dicts.
            directories = {
                i:{
                    "path":os.path.join(location, i),
                    "source":[item for item in directory_dict if directory_dict[item] in location][0]
                }
                for i in os.listdir(location) if i not in selected_directories
            }
        print(directories,selected_directories)
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
    status_items = [i[:-1] for i in status_items] # removing trailers.
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
            name: {"path": os.path.join(location, name), "isfile": status, "source":[item for item in status_items if item in os.path.join(location,name)][0]}
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


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="FILE")
    print(rclone_file_directory_select())
