"""

        Command for producing a single plot of an output

"""

import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_Analysis.Images import make_plot
from PyCS_Analysis.Analysis_Utils import SnapView
from PyCS_Core.PyCS_Errors import *
import pathlib as pt
from PyCS_System.SimulationMangement import SimulationLog
from colorama import Fore, Style
from matplotlib.pyplot import cm
import pynbody as pyn
import gc
from datetime import datetime
import warnings

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
    #- Required Arguments -#
    parser.add_argument("qty", help="The quantity to plot")
    parser.add_argument("ns", help="Then number of the snapshot to plot")
    parser.add_argument("-sim", "--simulation_name", default=None, help="The simulation name to use")
    parser.add_argument("-simdir", "--simulation_directory", default=None,
                        help="The simulation directory. Only one needs to be specified")
    #- Figure Options -#
    parser.add_argument("-s", "--save", action="store_true", help="Use to save the image.")
    parser.add_argument("-v", "--vbounds", nargs="+", help="The colorbounds if desired.", default=None)
    parser.add_argument("-t", "--title", help="The title to add to the plot.")
    parser.add_argument("-u", "--units", help="The output units to use")
    parser.add_argument("-tu", "--time_units", help="The time units to use in the output.")
    parser.add_argument("-r", '--resolution', help="The resolution to use", type=int)
    parser.add_argument("-i", "--integrate", help="Average through the slice", action="store_true")
    parser.add_argument("-log", "--logarithmic", action="store_true", help="Use a logarithmic plotting profile.")
    parser.add_argument("-cmap", "--colormap", default="inferno", help="The colormap to use.")
    parser.add_argument("-f", "--families", nargs="+", help="The families to include")
    #- Contour Options -#
    parser.add_argument("-c","--contours",action="store_true",help="Include contours?")
    parser.add_argument("-c_qty","--contour_qty",type=str,default="rho",help="The preferred contour quantity.")
    parser.add_argument("-c_lvls","--contour_levels",nargs="+",default=None,help="The levels to set the contours at.")
    parser.add_argument("-c_nlvl","--contour_nlevels",type=int,default=10,help="The number of levels to use in the contour map. Overridden by -c_lvls.")
    parser.add_argument("-c_log","--contour_log",action="store_true",help="Use logarithmically spaced levels?")
    parser.add_argument("-c_proj","--contour_project",action="store_true",help='Use the projected quantity?')
    parser.add_argument("-c_smooth","--contour_smooth",type=int,default=None,help="The smoothing kernel for the contours.")
    parser.add_argument("-c_fam","--contour_families",nargs="+",default=None,help="The families to use in the contour map.")
    parser.add_argument("-c_color","--contour_color",default="white",help="The color to use for the contours.")
    #- Logging Options -#
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    #- Camera / View Options -#
    parser.add_argument("-orig","--origin",help="The location of the origin. Array floats in kpc.",nargs="+",default=None)
    parser.add_argument("-cam","--camera",help="The location of the camera (az,elev).",nargs="+",default=None)
    parser.add_argument("-w", "--width", help="The width of the region.", default=None)
    args = parser.parse_args()

    # Setup
    ########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    cdbg_string = Fore.CYAN + Style.BRIGHT + _dbg_string + Style.RESET_ALL + " [" + Fore.GREEN + "Command Wizard" + Style.RESET_ALL + "]"
    # ArgCHECK
    ########################################################################################################################
    if args.vbounds != None:
        vmin, vmax = tuple([float(j) for j in args.vbounds])
    else:
        vmin, vmax = None, None

    if args.families != None:
        families = args.families
    else:
        families = None

    # Contour Management
    #------------------------------------------------------------------------------------------------------------------#
    if args.contours:
        # We are going to be using contours.
        contour_kwargs = {
            "contours":True,
            "nlevels":args.contour_nlevels,
            "levels":args.contour_levels,
            "qty":args.contour_qty,
            "log":args.contour_log,
            "families":args.contour_families,
            "color":args.contour_color,
            "smoothing_kernel":args.contour_smooth,
            "av_z":args.contour_project
        }
    else:
        contour_kwargs = None # This won't even make it into the command.
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


    # Further argument management
    #------------------------------------------------------------------------------------------------------------------#

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

    # Making sure saving works
    ########################################################################################################################
    if args.save:  # we need to save
        end_file = os.path.join(CONFIG["system"]["directories"]["figures_directory"], simulation_name,
                                "%s-(I-%s)" % (args.qty, "True"), datetime.now().strftime('%m-%d-%Y_%H-%M-%S'),
                                "Image_%s.png" % args.ns)
        if not os.path.exists(pt.Path(end_file).parents[0]):
            pt.Path.mkdir(pt.Path(end_file).parents[0], parents=True)
    else:
        end_file = None

    # Running
    ########################################################################################################################
    view = SnapView(view_parameters=view_params) # grabbing the view
    view.load_snapshot(os.path.join(simulation_directory, "output_%s" % args.ns))
    simSnap = view.snapshot
    view.snapshot = None
    gc.collect()


    kwargs = {
        "vmin": vmin,
        "vmax": vmax,
        "cmap": cmap,
        "resolution": args.resolution,
        "units": args.units,
        "time_units": args.time_units,
        "contour_kwargs": contour_kwargs
    }
    kwargs = {key: value for key, value in kwargs.items() if value != None}
    # PLOTTING
    ########################################################################################################################
    make_plot(simSnap, args.qty, save=args.save, end_file=end_file, log=args.logarithmic, av_z=args.integrate,
              title=args.title, width=args.width, families=families, **kwargs)
