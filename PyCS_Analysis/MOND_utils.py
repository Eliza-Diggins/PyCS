"""

Useful subroutines for producing mond specific data.

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import numpy as np
import scipy.ndimage
from scipy.interpolate import interp1d
from scipy.integrate import cumulative_trapezoid
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Analysis.plot_utils import get_color_binary_colormap
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Analysis.Analysis_Utils import get_families, align_snapshot, make_pseudo_entropy, make_mach_number, \
    generate_xray_emissivity, SnapView, generate_speed_of_sound
from PyCS_Core.PyCS_Errors import *
import matplotlib.pyplot as plt
from sympy import lambdify,symbols
from matplotlib.lines import Line2D
from PyCS_System.SimulationMangement import SimulationLog
from utils import split
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import current_process
import matplotlib as mpl
import gc
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
simlog = SimulationLog.load_default()

#- CONSTANTS -#
G = 6.674e-11 * pyn.units.Unit("m^3 kg^-1 s^-2")
m_p = 1.672e-27 * pyn.units.Unit("kg")
mu = 0.6
k_bn = 1.38e-23 * pyn.units.Unit("J K^-1")
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Base Function -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def dehnen_profile(mass,
                   gamma,
                   a,
                   independent_unit=CONFIG["units"]["default_length_unit"],
                   dependent_unit=CONFIG["units"]["default_density_unit"]):
    """
    Returns a lambda function for a Dehnen_profile (Dehnen 1993) with the specified gamma, a, and mass.
    Parameters
    ----------
    independent_unit: the length unit to use.
    dependent_unit: the density unit to use.
    mass: the total mass.
    gamma: the gamma parameter.
    a: the scale length

    Returns: lambda function
    -------

    """
    # intro debugging
    ####################################################################################################################
    fdbg_string = "%sdehnen_profile: " % _dbg_string
    log_print("Generating a dehnen profile with parameters (%s,%s,%s)" % (mass, gamma, a), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - assigning units as necessary -#
    if not isinstance(mass, pyn.units.CompositeUnit):
        mass = mass * pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    if not isinstance(a, pyn.units.CompositeUnit):
        a = a * pyn.units.Unit(CONFIG["units"]["default_length_unit"])

    independent_unit, dependent_unit = (pyn.units.Unit(unit) if isinstance(unit, str) else unit for unit in
                                        [independent_unit, dependent_unit])

    # Unit Coercion
    ####################################################################################################################
    # - Setting core parameters to managable units -#
    # mass now takes the default unit and a is coverted to the input.
    mass, a = mass.in_units(CONFIG["units"]["default_mass_unit"]), a.in_units(independent_unit)

    # mass conversion fact to multiply by in order to get the intended values
    conversion_factor = (pyn.units.Unit(CONFIG["units"]["default_mass_unit"]) / independent_unit ** 3).ratio(
        dependent_unit)

    # generating the lambda function
    ####################################################################################################################
    return lambda r: (((3 - gamma) * mass) / (4 * np.pi)) * (
            a / ((r ** gamma) * ((r + a) ** (4 - gamma)))) * conversion_factor


def dehnen_mass_profile(mass,
                        gamma,
                        a,
                        independent_unit=CONFIG["units"]["default_length_unit"],
                        dependent_unit=CONFIG["units"]["default_mass_unit"]):
    """
    Returns a lambda function for a Dehnen_profile (Dehnen 1993) integrated with the specified gamma, a, and mass.
    Parameters
    ----------
    independent_unit: the length unit to use.
    dependent_unit: the density unit to use.
    mass: the total mass.
    gamma: the gamma parameter.
    a: the scale length

    Returns: lambda function
    -------

    """
    # intro debugging
    ####################################################################################################################
    fdbg_string = "%sdehnen_mas_profile: " % _dbg_string
    log_print("Generating a dehnen profile with parameters (%s,%s,%s)" % (mass, gamma, a), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - assigning units as necessary -#
    if not isinstance(mass, pyn.units.CompositeUnit):
        mass = mass * pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    if not isinstance(a, pyn.units.CompositeUnit):
        a = a * pyn.units.Unit(CONFIG["units"]["default_length_unit"])

    independent_unit, dependent_unit = (pyn.units.Unit(unit) if isinstance(unit, str) else unit for unit in
                                        [independent_unit, dependent_unit])

    # Unit Coercion
    ####################################################################################################################
    # - Setting core parameters to managable units -#
    # mass now takes the default unit and a is coverted to the input.
    mass, a = mass.in_units(CONFIG["units"]["default_mass_unit"]), a.in_units(independent_unit)

    # mass conversion fact to multiply by in order to get the intended values
    conversion_factor = (pyn.units.Unit(CONFIG["units"]["default_mass_unit"])).ratio(dependent_unit)

    # generating the lambda function
    ####################################################################################################################
    return lambda r: conversion_factor * mass * ((r) / (r + a)) ** (3 - gamma)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- IC Functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_MOND_dm_profile(m_dm,m_g,interpolation_function=None):
    """
    ``get_MOND_dm_profile`` takes the NEWTONIAN distributions ``m_dm,m_g`` as input and returns the corresponding ``m_dm``
    function for the MOND gravity case.

    **Notes**:

    1. We recognize that the first profile is N-HSE: M(<r) = (-r^2/G)*(GAMMA(T,rho)). We can therefore solve for GAMMA
    such that
                                    GAMMA = -M(<r)G/r^2

    2. We then know that GAMMA (depending only on rho,T which don't change) is related to the MOND mass by

                                    M_M(<r) = (-r^2/G)*GAMMA*eta(|GAMMA/a_0|)

                    Thus,
                                    M_dm(<r) = M_M(<r) - M_g(<r).

    Parameters
    ----------
    m_dm: The lambda function for the DM mass distribution.
    m_g: The lambda function for the gas distribution.
    interpolation_function: The MOND interpolation function to utilize.

    Returns: The lambda function for the DM mass distribution in MOND
    -------

    """

    # Startup / Debug
    #------------------------------------------------------------------------------------------------------------------#
    G = 1.4e-19
    a_0 = 1.2e-10

    fdbg_string = "%s:get_MOND_dm_profile: "%_dbg_string
    log_print("Grabbing a MOND dm profile.",fdbg_string,"debug")

    # Sanitizing input #
    if not interpolation_function:
        interpolation_function = lambdify(symbols("x"),CONFIG["analysis"]["MOND"]["default_interp_function"],"numpy")
    else:
        pass

    # Building profile
    #------------------------------------------------------------------------------------------------------------------#
    M_newt = lambda r: m_g(r)+m_dm(r)
    return lambda r: (M_newt(r)*interpolation_function(np.abs((G/(a_0*r**2))*M_newt(r)))) - m_g(r)

def get_temperature_profile(m_dm,
                                 m_g,
                                 r,
                                mode="Newtonian",
                                 interpolation_function=None,
                                 independent_units=None,
                                 dependent_units=None,
                                 output_units=None,
                                 sample_frequency=1
                                 ):
    # Setup and Debug
    #------------------------------------------------------------------------------------------------------------------#
    fdbg_string = "%s:get_MOND_temperature_profile: "%_dbg_string
    log_print("Finding a MOND temperature profile for the given distributions.",fdbg_string,"debug")

    # Cleaning / Sanitizing input data
    #------------------------------------------------------------------------------------------------------------------#
    #- Interpolation Function -#
    if not interpolation_function: #-> grabbing an interpolation function if necessary.
        interpolation_function = lambdify(symbols("x"),CONFIG["analysis"]["MOND"]["default_interp_function"],"numpy")
    else:
        pass

    #- Mass Management -#
    if isinstance(m_dm,(int,float)): #-> Converting float to array.
        m_dm = m_dm*np.ones(len(r))
    else: #-> We assume this is a lambda function
        try:
            m_dm = m_dm(r)
        except TypeError as msg:
            make_error(TypeError,fdbg_string,"Failed to create m_dm array from r. Errors was:%s"%repr(msg))

    if isinstance(m_g,(int,float)):
        m_g = m_g*np.ones(len(r))
    else:
        try:
            m_g = m_g(r)
        except TypeError as msg:
            make_error(TypeError,fdbg_string,"Failed to create m_g array from r. Errors was:%s"%repr(msg))


    #- Unit management -#
    if not independent_units:
        independent_units = CONFIG["units"]["default_length_unit"]
    if not output_units:
        output_units = CONFIG["units"]["default_temperature_unit"]
    if not dependent_units:
        dependent_units = CONFIG["units"]["default_mass_unit"]


    if independent_units != CONFIG["units"]["default_length_unit"]: #-> Converting to base unit choice.
        r = r*pyn.units.Unit(independent_units).in_units(CONFIG["units"]["default_length_unit"])

    if dependent_units != CONFIG["units"]["default_mass_unit"]:
        m_g = m_g*pyn.units.Unit(dependent_units).in_units(CONFIG["units"]["default_mass_unit"])
        m_dm = m_dm * pyn.units.Unit(dependent_units).in_units(CONFIG["units"]["default_mass_unit"])

    #- Quantity Calculations -#
    m_tot = m_g+m_dm
    rho_dm,rho_g,rho = (1/(4*np.pi*r**2))*np.gradient(m_dm,r), (1/(4*np.pi*r**2))*np.gradient(m_g,r), (1/(4*np.pi*r**2))*np.gradient(m_tot,r)

    #------------------------------------------------------------------------------------------------------------------#
    #  Computing the gravitational field strength
    #------------------------------------------------------------------------------------------------------------------#
    # Notes: We utilize that dphi/a_0 = x, then we need to solve eta(x)*x = -G/(r^2a_0) * M(<r)
    #
    #
    #------------------------------------------------------------------------------------------------------------------#
    #- Unit Manipulation -#
    G_unit = G.in_units("%s^2 m %s^-1 s^-2"%(CONFIG["units"]["default_length_unit"],
                                             CONFIG["units"]["default_mass_unit"]))

    a_0 = 1.2e-10

    if mode == "MOND":
        #- Setting up the solver -#
        solving_array = r[::sample_frequency]
        solving_mass = m_tot[::sample_frequency]
        solver_func = lambda x: interpolation_function(np.sqrt(x ** 2 + 1e-5)) * x + (G_unit / (a_0 * solving_array ** 2)) * solving_mass

        #- Solving -#
        alph = (G_unit/(a_0*solving_array**2))*solving_mass
        guess = -(alph/2) - np.sqrt(alph**2+4*alph)/2
        temp_field = a_0*fsolve(solver_func,guess,xtol=1e-7)

        #- interpolating -#
        interp = interp1d(solving_array,temp_field,fill_value="extrapolate")
        field = interp(r)
    else:
        field = -G_unit*m_tot/(r**2)


    #------------------------------------------------------------------------------------------------------------------#
    # Solving the temperature equation!
    #------------------------------------------------------------------------------------------------------------------#
    integrand = np.flip(cumulative_trapezoid(np.flip(rho_g*field),np.flip(r),initial=0))
    T = (1*pyn.units.Unit("J").in_units("keV"))*(m_p.in_units("kg")*mu)/(rho_g*(1*pyn.units.Unit("m").in_units(CONFIG["units"]["default_length_unit"]))) * integrand

    return T*(pyn.units.Unit("keV").in_units(output_units))

if __name__ == '__main__':
    set_log(_filename)
    from scipy.optimize import fsolve,minimize
    import numpy as np
    from PyCS_Analysis.MOND_utils import dehnen_mass_profile
    import matplotlib.pyplot as plt

    # Constants #
    a_0 = 1.2e-10  # MOND acceleration regime


    # settings #
    r = np.logspace(0,np.log10(2500),6000) #-> kpc
    m_t = np.array([[1e14,2.5e14,5e14,7.5e14,1e15],
                    [1e14,2.5e14,5e14,7.5e14,1e15],
                    [1e14,2.5e14,5e14,7.5e14,1e15]])
    m_g = m_t/10
    rs = np.array([[200,200,200,200,200],
                   [400,400,400,400,400],
                   [600,600,600,600,600]])




    plt.rcParams["text.usetex"] = True


    figure,axes = plt.subplots(nrows=3,ncols=5,sharex=True,sharey=True,gridspec_kw={"hspace":0,"wspace":0})


    for i in range(3):
        for j in range(5):
            mass = dehnen_mass_profile(m_t[i,j]*pyn.units.Unit("Msol"),1,rs[i,j]*pyn.units.Unit("kpc"),independent_unit="kpc") #-> mass in Solar Masses
            mass_g = dehnen_mass_profile(m_g[i,j]*pyn.units.Unit("Msol"),1,rs[i,j]*pyn.units.Unit("kpc"),independent_unit="kpc")
            T = get_temperature_profile(mass, mass_g, r, sample_frequency=8, independent_units="kpc")
            TM = get_temperature_profile(mass, mass_g, r, mode="MOND", sample_frequency=8, independent_units="kpc")
            ax1 = axes[i,j].twinx()
            axes[i,j].semilogx(r,T,"m-.")
            axes[i,j].semilogx(r,TM,"m:")
            axes[i,j].grid()
            ax1.loglog(r,mass(r),"k-")
            ax1.loglog(r,mass_g(r),"k-.")
            ax1.loglog(r,mass(r)+mass_g(r),"k:")

            if i == 2:
                axes[i,j].tick_params(top=False, bottom=True, right=False, labelright=False, labeltop=False,
                                   labelbottom=True)
            else:
                axes[i, j].tick_params(top=False, bottom=False, right=False, labelright=False, labeltop=False,
                                       labelbottom=False)

            if j == 0:
                axes[i,j].tick_params(top=False, left=True, right=False, labelright=False, labeltop=False,
                                   labelleft=True)
                ax1.tick_params(top=False, left=False, right=False, labelright=False, labeltop=False,
                                   labelleft=False)
            elif j == 4:
                axes[i, j].tick_params(top=False, left=False, right=False, labelright=False, labeltop=False,
                                   labelleft=False)
                ax1.tick_params(top=False, left=False, right=True, labelright=True, labeltop=False,
                                   labelleft=False)
            else:
                axes[i, j].tick_params(top=False, left=False, right=False, labelright=False, labeltop=False,
                                   labelleft=False)
                ax1.tick_params(top=False, left=False, right=False, labelright=False, labeltop=False,
                                   labelleft=False)

    axes[-1,2].set_xlabel(r"Cluster Radius /[$\mathrm{kpc}$]")
    axes[1,-1].set_ylabel(r"Cluster Mass /[$\mathrm{M}_\odot$]",labelpad=30)
    axes[1,-1].yaxis.set_label_position("right")
    axes[1, 0].set_ylabel(r"ICM Temperature /[$\mathrm{keV}$]")

    plt.suptitle("MOND and Newtonian Equilibrium Temperatures")
    plt.subplots_adjust(bottom=0.1,top=0.9,left=0.1,right=0.9)
    plt.show()
