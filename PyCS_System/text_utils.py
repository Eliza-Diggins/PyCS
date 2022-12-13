"""

Useful text utility functions for use in larger system. Written by: Eliza Diggins

"""
import sys
import pathlib as pt
import os
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from colorama import Fore,Style
from PyCS_Core.Logging import set_log,log_print
from PyCS_Core.Configuration import _configuration_path,read_config
import pathlib as pt
from copy import deepcopy
import os
from functools import reduce  # forward compatibility for Python 3
import operator


#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#------------------------------------------------------ Setup ----------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG=read_config(_configuration_path)
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#-------------------------------------------------- Sub-Functions ------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)
def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#---------------------------------------------------- Functions --------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def print_title(title,author,width=64,str_struct="#-+-#",boundary="|"):
    """
    Prints the title and author for a given program without having to hard code in different scripts
    :param title: the title to print
    :param author: the author to print.
    :return: The resultant string.
    """
    ## doing the math ##
    if width%len(str_struct) != 0: # the width is not divisible
        width -= width%len(str_struct)

    reps = int(width/len(str_struct))
    title_left_over = width-len(title)
    if title_left_over%2 == 0: # then this is divisible by two,
        t_shift = int(title_left_over/2)
    else:
        t_shift = int((title_left_over-1)/2)
    author_left_over = width-len(author)
    if author_left_over%2 == 0: # then this is divisible by two,
        a_shift = int(author_left_over/2)
    else:
        a_shift = int((author_left_over-1)/2)

    string = str_struct*reps + "\n" # This is the first line.
    string += boundary + (" "*(width-2))+"%s\n"%boundary
    string += boundary+(" "*(t_shift-1)) + Style.BRIGHT+Fore.RED+title+Style.RESET_ALL + (" "*(width-1-len(title)-t_shift))+"%s\n"%boundary
    string += boundary + (" " * (a_shift - 1)) + Style.BRIGHT+Fore.RED+author+Style.RESET_ALL + (" " * (width - 1 - len(author) - a_shift)) + "%s\n"%boundary
    string +=  str_struct*reps  # This is the first line.

    print(string)

def get_options(option_dict,title):
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
    fdbg_string = "%sget_options: "%_dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "SETTING WIZARD" + Style.RESET_ALL + "]: "

    setting_commands={
        "n":"Exit/Finish - Move down a level.",
        "e":"Edit - Move to.",
        "d":"Reset option to default",
    }
    # startup copy and settting #
    settings = deepcopy(option_dict) # create the copy we are going to use for the setting storage.

    # starting the cycle #
    CHECK_DONE = False
    location = [] # this is where we will store the location
    while not CHECK_DONE: # we are still cycling'
        ## Setting the title ##
        if location == []: # we have no location
            print_title(title,"Location: MAIN")
        else:
            loc_string = "Location: "
            for loc in location:
                loc_string += "--> %s "%loc
            print_title(title,loc_string)

        ### Mangaging the print statements ###
        print("#" * 64)
        sub_dict = getFromDict(settings,location)
        for index,option in enumerate(sub_dict):
            if not isinstance(sub_dict[option],dict): # This is a dictionary.
                print("[%s] %s = %s   - default: %s" % (Fore.RED + str(index + 1) + Style.RESET_ALL,
                                                        Fore.CYAN+Style.BRIGHT +str(option) + Style.RESET_ALL,
                                                        Fore.GREEN+Style.BRIGHT+str(sub_dict[option])+Style.RESET_ALL,
                                                        Style.DIM+ Fore.WHITE + str(getFromDict(option_dict, location)[option])+Style.RESET_ALL))
            else:
                print("[%s] %s"%(Fore.RED+str(index+1)+Style.RESET_ALL,
                                                  Fore.BLUE+Style.BRIGHT+option + Style.RESET_ALL))

        print("\n" + "#" * 64)

        ### Grabbing actual Setting options ###
        print(Fore.RED+"Commands:"+Style.RESET_ALL)
        for option in setting_commands:
            print("%s: %s"%(Fore.RED+option+Style.RESET_ALL,setting_commands[option]))
        print("#" * 64)
        ### Setting Selection ###
        inp=input("%sPlease enter a command:"%cdbg_string)

        # parsing command #
        if inp in ["e","E","d","D"]: # we need to select a option
            check = False
            opinp = input(
                "%sWhich item would you like to select? [1:%s]: " % (cdbg_string, len(list(sub_dict.keys()))))
            while check == False: # We now need to select an item to actually edit.
                if not opinp.isdigit() and opinp not in ["n","N"]: # the input wasn't a digit or "n"
                    failure_reason_string = "Invalid Selection"
                elif opinp in ["n","N"]:
                    check = True
                else:
                    # This is a digit and we now need to check if its reasonable.
                    if 1 <= int(opinp) <= len(list(sub_dict.keys())):
                        # This is a good selection.
                        check = True
                        selected_index = int(opinp)-1
                    else:
                        failure_reason_string = "No item %s"%int(opinp)

                if not check:
                    opinp=input("%s%s! Use 'n' to go back. Which item would you like to select? [1:%s]: "%(cdbg_string,failure_reason_string,len(list(sub_dict.keys()))))

            ### Executing the selected command ###
            if inp in ["e","E"]:
                # We are editing / moving #
                selected_option = list(sub_dict.keys())[selected_index] # we grab the correct item

                if isinstance(sub_dict[selected_option],dict): # we are moving into another dict.
                    location.append(selected_option)
                else:
                    # We are actually going to be editing the value
                    edited_value_str = input("%sEnter a new value for %s: ('n' to go back) "%(cdbg_string,selected_option))
                    if edited_value_str not in ["n","N"]:
                        setInDict(settings,location + [selected_option],edited_value_str)
                    else:
                        pass
            elif inp in ["d","D"]:
                # We are returning an item to the default.
                selected_option = list(sub_dict.keys())[selected_index]  # we grab the correct item
                setInDict(settings,location + [selected_option],getFromDict(option_dict,location+[selected_option]))
            else: # We are returning out of this option
                pass
        elif inp in ["n","N"]:
            # We need to return #
            if len(location): # we need to back up a level.
                location = location[:-1]
            else:
                CHECK_DONE = True # We are exiting the whole program

        os.system('cls' if os.name == 'nt' else 'clear')
    return settings
        


#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#------------------------------------------------------- Main ----------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename,output_type="STDOUT")
    print(get_options({"name":"Eliza",
                 "options":{
                     "option1":2,
                     "option2":4
                 }},"Title"))