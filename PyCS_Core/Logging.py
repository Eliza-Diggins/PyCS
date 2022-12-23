"""
            Logging Management Scripts
            -- Last Check: 12/16 --
"""
import logging
import sys
import logging as log
from PyCS_Core.Configuration import read_config, _configuration_path
import os
import pathlib as pt
from datetime import datetime
from colorama import Fore, Style, init

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Variables ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Core"
_filename = pt.Path(__file__).name.replace(".py", "")
CONFIG = read_config(_configuration_path)  # reads the configuration file.
_dbg_string = "%s:%s:" % (_location, _filename)
__output_log_type = None
# Grabbing colors #
init(autoreset=True)
_loc_color = getattr(Fore, CONFIG["system"]["logging"]["text"]["location_color"])
_loc_style = getattr(Style, CONFIG["system"]["logging"]["text"]["location_style"])

# Setting DBG levels #
lvls = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50
}
_log_colors = {
    key: getattr(Fore, CONFIG["system"]["logging"]["text"]["%s_color" % key]) for key in list(lvls.keys())
}

_log_style = {
    key: getattr(Style, CONFIG["system"]["logging"]["text"]["%s_style" % key]) for key in list(lvls.keys())
}


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Classes--------- ---------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
class CustomFormatter(log.Formatter):
    """
    Custom logging formatter for file logging.
    """
    format = CONFIG["system"]["logging"]["logging_format"]

    FORMATS = {
        log.DEBUG: format,
        log.INFO: format,
        log.WARNING: format,
        log.ERROR: format,
        log.CRITICAL: format
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = log.Formatter(log_fmt)
        return formatter.format(record)


class CustomCFormatter(log.Formatter):
    """
    This is the custom colored formatter for our system.
    """
    format = CONFIG["system"]["logging"]["logging_format"]
    FORMATS = {}
    for level in list(lvls.keys()):
        FORMATS[getattr(log, level.upper())] = str(_log_style[level]) + str(_log_colors[level]) + format


    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = log.Formatter(log_fmt)
        return formatter.format(record)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- SIMPLE FUNCTIONS ---------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def make_error(error, loc, str):
    """
    Raises an error, properly formatted with the given string.
    :param error:
    :param str:
    :return:
    """
    raise error(_loc_style + _loc_color + loc + " " + _log_style["error"] + _log_colors["error"] + str)


def log_print(text, loc, level):
    """
    Prints the text to the log in whatever manner is set up.
    :param text: The text to send to the log
    :param level: The level to use
    :return: None
    """
    _fdg_string = "%slog_print: " % _dbg_string
    ### checking that the output type is valid ###
    if __output_log_type == None:  # its not a valid output type
        make_error(SystemError, _fdg_string,
                   "global variable __output_log_type not yet define. Please load the log system.")

    ### Creating the alert ###
    if __output_log_type == "FILE":
        try:
            log.log(lvls[level], loc + " "+text)
        except Exception:
            pass
    elif __output_log_type == "STDOUT":
        try:
            log.log(lvls[level], _loc_color + loc + " "+ _log_colors[level] + text)
        except Exception:
            pass


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

def set_log(script_name: str,
            output_type: str = CONFIG["system"]["logging"]["logging_output"],
            level=CONFIG["system"]["logging"]["level"]) -> bool:
    """
    Sets the global logger for the system.
    :param script_name: The current script which is being run on main
    :param output_type: The type of output to use. options are 'STDOUT' and "FILE".
    :param kwargs: Additional kwargs to pass to log.BasicConfig
    :return: True if passed without error. False if an error occurred.
    """
    global __output_log_type
    ### Generating the correct file location ###
    if not os.path.exists(os.path.join(CONFIG["system"]["directories"]["bin_directory"],"Logging", script_name)):
        # This path doesn't yet exist and therefore needs to be generated.
        pt.Path.mkdir(pt.Path(os.path.join(CONFIG["system"]["directories"]["bin_directory"],"Logging", script_name)),
                      parents=True)  # make the directory

    ### Setting the logger ###
    if output_type == "FILE":  # we are outputting to a file
        __output_log_type = output_type
        handler_sh_file = logging.FileHandler(
            filename=os.path.join(CONFIG["system"]["directories"]["bin_directory"],"Logging", script_name,
                                  "%s.log" % datetime.now().strftime('%m-%d-%Y_%H-%M-%S')))
        handler_sh_file.setFormatter(CustomFormatter())
        log.basicConfig(handlers=[handler_sh_file], level=level)
        log.info("PPCC:PCCC_Core:Logging:set_log: Initialized log. level=%s." % level)

    elif output_type == "STDOUT":  # We are printing
        __output_log_type = output_type
        handler_sh_stderr = logging.StreamHandler(sys.stderr)  # Creating the handler
        handler_sh_stderr.setFormatter(CustomCFormatter())  # Using the formatter
        log.basicConfig(level=level, handlers=[handler_sh_stderr])  # setting the basic config.
    else:
        return False

    mpl_logger = logging.getLogger('matplotlib')
    mpl_logger.setLevel(logging.WARNING)
    stream_logger = logging.getLogger("PIL")
    stream_logger.setLevel(logging.WARNING)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------------  MAIN  --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    ### Setting the log ###
    set_log(_filename, output_type="FILE")
    log_print("ooops",_filename+": ","debug")
