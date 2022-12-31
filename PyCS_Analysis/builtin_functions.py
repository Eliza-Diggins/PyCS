"""

    Useful pre-defined functions for analysis
        Written by: Eliza Diggins
"""
import os
import sys
import pathlib as pt
import numpy as np
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.PyCS_Errors import *
import pynbody as pyn
import types
import numpy as np

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# - Fixed constants -#
mass_fraction = 0.6  # The standard mass fraction. This value is from Schneider (Extragalactic astronomy)
boltzmann_constant = 1.381e-23 * pyn.units.Unit("J K^-1")
G = 6.675e-11 * pyn.units.Unit("N m^2 kg^-2")
m_p = 1.672621911e-27 * pyn.units.Unit("kg")

#- smoothing kernel -#
smth_kern = lambda x: (1/np.sqrt(2*np.pi))*np.exp((-(x)**2)/5)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- Sub-Functions ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def smooth_func(function,bandwidth=10):
    return lambda r: np.convolve(function(r),np.ones(bandwidth)/bandwidth,mode="same")
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Profiles -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -
# These functions are all Lambda-generators, i.e. they produce lambda functions based on the inputs.
# -
def hydrostatic_mass(subsnap,
                     mu:float=mass_fraction,
                     independent_unit=CONFIG["units"]["default_length_unit"],
                     dependent_unit=CONFIG["units"]["default_mass_unit"],
                     **kwargs):
    """
    Constructs the mass profile base on the hydrostatic assumption and spherical symmetry.

    M(<r) = ((k*T*r^2)/(mu*m_p*G))*[(dln(rho)/dr) + (dln(T)/dr)]

    Parameters
    ----------
    kwargs: additional kwargs to pass to pyn.analysis.profile.Profile()
    subsnap: the Pynbody snapshot or sub-snapshot to analyze. **Must be pre-aligned and centered**
    mu: The ICM mass fraction.
    independent_unit: The length unit to use as input. Must match the data length unit.
    dependent_unit: The output unit to use as the mass unit. Must match the data mass unit.

    Returns: Lambda function - M(<r) - in ``dependent_units`` = Lf(r - in ``independent_units``)
    -------

    """
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%shydrostatic_mass: " % _dbg_string
    log_print("Constructing a hydrostatic mass lambda for %s." % subsnap, fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - managing unit types -#
    if isinstance(independent_unit, str):
        independent_unit = pyn.units.Unit(independent_unit)
    if isinstance(dependent_unit, str):
        dependent_unit = pyn.units.Unit(dependent_unit)

    # Collecting necessary datasets
    ####################################################################################################################
    try:
        # - generating the profile -#
        gas_profile = pyn.analysis.profile.Profile(subsnap.g, ndim=3, **kwargs)

        # - extracting important arrays
        temp_g = gas_profile["temp"].in_units("K")
        rho_g = gas_profile["rho"].in_units("Msol kpc^-3")
        dtemp_g = gas_profile["d_temp"].in_units("K %s^-1" % str(independent_unit))
        drho_g = gas_profile["d_rho"].in_units("Msol kpc^-3 %s^-1" % str(independent_unit))
        r_vals = gas_profile["rbins"].in_units(independent_unit)
    except Exception:
        make_error(SnapshotError, fdbg_string, "Failed to extract a gas profile from %s." % subsnap)
        return None  # IDE calming

    # Generate the r-lambda
    ####################################################################################################################
    r_index = lambda r:np.piecewise(r,
                                    [(r >= r_vals[i])&(r < r_vals[i+1]) for i,rs in enumerate(r_vals[:-1])]+[(r>= r_vals[-1])],
                                    [int(i) for i in list(range(len(r_vals)))])  # generates the r-indexing array function
    print(r_index(np.linspace(0,5,1000)).astype("int32"))
    # Generating the lambda-function
    ####################################################################################################################
    # - Coercing units -#
    k_temp = boltzmann_constant.in_units("%s m^2 s^-2 K^-1" % str(dependent_unit))  # convert k to M m^2/s^2
    G_temp = G.in_units("m^2 s^-2 kg^-1 %s" % str(independent_unit))
    m_p_temp = m_p.in_units("kg")

    # - constructing the lambda function -#
    hydro_func = lambda r: -1*((k_temp) / (mu * G_temp * m_p_temp)) * (
                (temp_g[r_index(r).astype("int32")]) * (r_vals[r_index(r).astype("int32")] ** 2)) * (((1 / rho_g[r_index(r).astype("int32")]) * (drho_g[r_index(r).astype("int32")]))
                                                                     + ((1/ temp_g[r_index(r).astype("int32")]) * (dtemp_g[r_index(r).astype("int32")])))


    return smooth_func(hydro_func)

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
    fdbg_string = "%sdehnen_profile: "%_dbg_string
    log_print("Generating a dehnen profile with parameters (%s,%s,%s)"%(mass,gamma,a),fdbg_string,"debug")

    # Setup
    ####################################################################################################################
    #- assigning units as necessary -#
    if not isinstance(mass,pyn.units.CompositeUnit):
        mass = mass*pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    if not isinstance(a,pyn.units.CompositeUnit):
        a = a*pyn.units.Unit(CONFIG["units"]["default_length_unit"])

    independent_unit,dependent_unit = (pyn.units.Unit(unit) if isinstance(unit,str) else unit for unit in  [independent_unit,dependent_unit])

    # Unit Coercion
    ####################################################################################################################
    #- Setting core parameters to managable units -#
    # mass now takes the default unit and a is coverted to the input.
    mass, a = mass.in_units(CONFIG["units"]["default_mass_unit"]),a.in_units(independent_unit)

    # mass conversion fact to multiply by in order to get the intended values
    conversion_factor = (pyn.units.Unit(CONFIG["units"]["default_mass_unit"])/independent_unit**3).ratio(dependent_unit)

    # generating the lambda function
    ####################################################################################################################
    return lambda r: (((3-gamma)*mass)/(4*np.pi))*(a/((r**gamma)*((r+a)**(4-gamma))))*conversion_factor

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
    fdbg_string = "%sdehnen_mas_profile: "%_dbg_string
    log_print("Generating a dehnen profile with parameters (%s,%s,%s)"%(mass,gamma,a),fdbg_string,"debug")

    # Setup
    ####################################################################################################################
    #- assigning units as necessary -#
    if not isinstance(mass,pyn.units.CompositeUnit):
        mass = mass*pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    if not isinstance(a,pyn.units.CompositeUnit):
        a = a*pyn.units.Unit(CONFIG["units"]["default_length_unit"])

    independent_unit,dependent_unit = (pyn.units.Unit(unit) if isinstance(unit,str) else unit for unit in  [independent_unit,dependent_unit])

    # Unit Coercion
    ####################################################################################################################
    #- Setting core parameters to managable units -#
    # mass now takes the default unit and a is coverted to the input.
    mass, a = mass.in_units(CONFIG["units"]["default_mass_unit"]),a.in_units(independent_unit)

    # mass conversion fact to multiply by in order to get the intended values
    conversion_factor = (pyn.units.Unit(CONFIG["units"]["default_mass_unit"])).ratio(dependent_unit)

    # generating the lambda function
    ####################################################################################################################
    return lambda r: conversion_factor*mass*((r)/(r+a))**(3-gamma)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    set_log(_filename,output_type="STDOUT")

    h = dehnen_profile(1000e12*pyn.units.Unit("Msol"),1,200*pyn.units.Unit("kpc"),dependent_unit="Msol kpc^-3",independent_unit="Mpc")
    x = np.linspace(0,5,3000)
    plt.loglog(x,h(x))
    plt.show()

    data = pyn.load("/home/ediggins/PyCS/initial_conditions/Clu_3.dat")
    data.g["smooth"] = pyn.sph.smooth(data.g)
    data.g["rho"] = pyn.sph.rho(data.g)
    plt.show()
