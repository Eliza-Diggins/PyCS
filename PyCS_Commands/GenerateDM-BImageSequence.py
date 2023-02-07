"""

        Command for producing a sequence of DM-Baryon images

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
from PyCS_Core.PyCS_Errors import *
from PyCS_System.SimulationMangement import SimulationLog
from PyCS_Analysis.Images import generate_dm_baryon_image_sequence
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
    parser.add_argument("-sim", "--simulation_name", default=None, help="The simulation name to use")
    parser.add_argument("-simdir", "--simulation_directory", default=None,
                        help="The simulation directory. Only one needs to be specified")
    parser.add_argument("-vg", "--vbounds_gas", nargs="+", help="The colorbounds if desired for gas.", default=None)
    parser.add_argument("-vdm", "--vbounds_dm", nargs="+", help="The colorbounds if desired for dm.", default=None)
    parser.add_argument("-w", "--width", help="The width of the region.", default=None),
    parser.add_argument("-u", "--units", help="The output units to use")
    parser.add_argument("-tu", "--time_units", help="The time units to use in the output.")
    parser.add_argument("-r", '--resolution', help="The resolution to use", type=int)
    parser.add_argument("-i", "--integrate", help="Average through the slice", action="store_true")
    parser.add_argument("-c", "--colors", help="The two colors to use for the bandpass images.", nargs="+")
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


    if args.vbounds_gas != None:
        vmin_gas, vmax_gas = tuple([float(j) for j in args.vbounds_gas])
    else:
        vmin_gas, vmax_gas = None, None

    if args.vbounds_dm != None:
        vmin_dm, vmax_dm = tuple([float(j) for j in args.vbounds_dm])
    else:
        vmin_dm, vmax_dm = None, None

    if args.colors != None:
        colors = [str(i) for i in args.colors]
        if len(colors) != 2:
            raise ValueError("--colors must have length 2.")
    else:
        colors = None

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
        "vmin_gas": vmin_gas,
        "vmax_gas": vmax_gas,
        "vmin_dm": vmin_dm,
        "vmax_dm": vmax_dm,
        "resolution": args.resolution,
        "units": args.units,
        "time_units": args.time_units,
        "colors": colors,
        "view_kwargs":view_params
    }
    kwargs = {key: value for key, value in kwargs.items() if value != None}
    # Running
    ########################################################################################################################
    generate_dm_baryon_image_sequence(simulation_directory, multiprocess=True, nproc=args.nproc, **kwargs,
                                      width=args.width, av_z=args.integrate)
