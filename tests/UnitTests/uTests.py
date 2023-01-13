"""
    Automated test cases for proper running of the system
                Written by: Eliza Diggins

"""
import pathlib as pt
import os
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[2]))
import unittest
from PyCS_Core.Configuration import read_config, _configuration_path
import warnings
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- sub_functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def dictionary_check(dictionary):
    """
    Checks the input dictionary for tupled-structure. Raises an assertion issue if something goes wrong.
    Parameters
    ----------
    dictionary: The dictionary to test.

    Returns
    -------

    """
    for key,value in dictionary.items():
        if isinstance(value,dict):
            # recheck it
            dictionary_check(value)
        elif isinstance(value,tuple) and len(value) == 3:
            # This a fine
            pass
        else:
            raise AssertionError("%sdictionary_check: %s is not correctly structured."%(_dbg_string,dictionary))

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Tests ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
class TestCore(unittest.TestCase):
    """
    Testing instances for the core functionality of the modules in the PyCS_Core directory.

    # Tests -----------------------------------------------------------------------------------------------------------#
    test_config: Tests the configuration loading system
    test_logging: Test the ability of the system to load the logging system.
    """

    def test_config(self):
        """
        Load the configuration file and make sure the output is a dictionary.
        Returns: None
        -------

        """
        fdbg_string = "%stest_config: " % _dbg_string
        # Setting up #
        warnings.filterwarnings('ignore')
        try:
            CONFIG = read_config(_configuration_path)
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string, _configuration_path))

    def test_logging(self):
        """
        Test the ability of the system to open the logging system.
        Returns
        -------

        """
        fdbg_string = "%stest_logging: " % _dbg_string
        # Setting up #
        warnings.filterwarnings('ignore')
        try:
            from PyCS_Core.Logging import set_log
            set_log(_filename)
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string, _configuration_path))


class TestSystem(unittest.TestCase):
    """
    Testing instances for the system directory of the project.

    # Tests -----------------------------------------------------------------------------------------------------------#
    test_configs: Tests the RAMSES, SLURM, and CLUSTEP reading.
    """

    def test_configs(self):
        fdbg_string = "%stest_config: " % _dbg_string
        # grab the 3 functions we want to test.
        CONFIG = read_config(_configuration_path)
        from PyCS_System.SpecConfigs import read_batch_config, read_RAMSES_config, read_clustep_config

        for function,name in zip([read_batch_config, read_RAMSES_config, read_clustep_config],
                                 ["batch_config.ini","RAMSES_config.ini","CLUSTEP_config.ini"]):
            try:
                config_data = function(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[2]),
                                                    "PyCS_Core",
                                                    "installConfigs",
                                                    name))

                # is it a dictionary?
                self.assertIsInstance(config_data, dict)

                # checking structure #
                dictionary_check(config_data)
            except Exception:
                raise AssertionError("%sFailed to read the config with %s." % (fdbg_string, function))


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Main -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
    # ------------------------------------------------------ Setup -------------------------------------------------------#
    # --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
    warnings.filterwarnings('ignore')
    _location = "Tests"
    _filename = pt.Path(__file__).name.replace(".py", "")
    _dbg_string = "%s:%s:" % (_location, _filename)

    # Running
    unittest.main()
