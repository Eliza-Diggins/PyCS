"""

        Command for producing sequence of a given qty image.

"""

import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
import pathlib as pt
from colorama import Fore, Style
from matplotlib.pyplot import cm
from PyCS_Core.PyCS_Errors import *
from PyCS_System.SimulationMangement import SimulationLog
from PyCS_Analysis.Images import generate_image_sequence
import warnings
import pynbody as pyn

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Commands"
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

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # Argument Parsing
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("qty", help="The quantity to plot")
    parser.add_argument("-sim", "--simulation_name", default=None, help="The simulation name to use")
    parser.add_argument("-simdir", "--simulation_directory", default=None,
                        help="The simulation directory. Only one needs to be specified")
    parser.add_argument("-v", "--vbounds", nargs="+", help="The colorbounds if desired.", default=None)
    parser.add_argument("-t", "--title", help="The title to add to the plot.")
    parser.add_argument("-w", "--width", help="The width of the region.", default=None),
    parser.add_argument("-u", "--units", help="The output units to use")
    parser.add_argument("-tu", "--time_units", help="The time units to use in the output.")
    parser.add_argument("-r", '--resolution', help="The resolution to use", type=int)
    parser.add_argument("-f", "--families", help="The families to include.", nargs="+", default=None)
    parser.add_argument("-i", "--integrate", help="Average through the slice", action="store_true")
    parser.add_argument("-log", "--logarithmic", action="store_true", help="Use a logarithmic plotting profile.")
    parser.add_argument("-cmap", "--colormap", default="inferno", help="The colormap to use.")
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    parser.add_argument("-np", "--nproc", type=int, default=1, help="The number of processors to use.")
    parser.add_argument("-orig","--origin",help="The location of the origin. Array floats in kpc.",nargs="+",default=None)
    parser.add_argument("-cam","--camera",help="The location of the camera (az,elev).",nargs="+",default=None)
    args = parser.parse_args()

    # Setup
    ########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    cdbg_string = Fore.CYAN + Style.BRIGHT + _dbg_string + Style.RESET_ALL + " [" + Fore.GREEN + "Command Wizard" + Style.RESET_ALL + "]"
    # ArgCHECK
    ########################################################################################################################
    # Camera Management
    #------------------------------------------------------------------------------------------------------------------#
    if not args.origin:
        origin = pyn.array.SimArray([0,0,0],"kpc")
    else:
        # The args.origin should be a list of kpcs
        origin = pyn.array.SimArray([float(val) for val in args.origin],"kpc")

    if not args.camera:
        camera = (0,0)
    else:
        camera = [float(val) for val in args.camera]

    if len(camera) != 2:
        raise ValueError("The length of args.camera should be 2, not %s."%len(camera))

    if len(origin) != 3:
        raise ValueError("The length of args.origin should be 3, not %s."%len(camera))

    view_params = {"center":origin,"angles":camera}

    if args.vbounds != None:
        vmin, vmax = tuple([float(j) for j in args.vbounds])
    else:
        vmin, vmax = None, None

    if args.families != None:
        families = args.families
    else:
        families = None

    cmap = cm.get_cmap(args.colormap)

    if not (args.simulation_name or args.simulation_directory):
        raise OSError("%s: Failed to find either -sim or -simdir. At least one is necessary..." % cdbg_string)

    if args.simulation_name:  # we were given a simulation name
        matches = simlog.match("SimulationName", "SimulationLocation", args.simulation_name)
        simulation_name = args.simulation_name
        if len(matches) == 1:
            simulation_directory = matches[0]
        elif not len(matches):
            raise SimulationBackendError("%s: Failed to find simulation %s." % (cdbg_string, args.simulation_name))
        else:
            log_print("Found more than one matching directories. Using %s." % matches[0], _dbg_string, "info")
            simulation_directory = matches[0]

    else:
        # args.simulation_directory was specified.
        simulation_directory = args.simulation_directory

        try:
            simulation_name = simlog.match("SimulationLocation", "SimulationName", args.simulation_directory)[0]
        except KeyError:
            simulation_name = pt.Path(simulation_directory).name

    kwargs = {
        "vmin": vmin,
        "vmax": vmax,
        "cmap": cmap,
        "resolution": args.resolution,
        "units": args.units,
        "time_units": args.time_units,
        "view_kwargs":view_params
    }
    kwargs = {key: value for key, value in kwargs.items() if value != None}
    # Running
    ########################################################################################################################
    generate_image_sequence(simulation_directory, args.qty, True, args.nproc, **kwargs, width=args.width,
                            log=args.logarithmic, av_z=args.integrate, families=families)
