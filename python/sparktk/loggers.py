"""
Logging - simple helpers for now
"""
import logging
import sys
import inspect

# Constants
LINE_FORMAT = '%(asctime)s|%(name)s|%(levelname)-5s|%(message)s'

# add a null handler to root logger to avoid handler warning messages
class NullHandler(logging.Handler):
    name = "NullHandler"

    def emit(self, record):
        pass

# this line avoids the 'no handler' warning msg when no logging is set at all
_null_handler = NullHandler()
_null_handler.name = ''  # add name explicitly for python 2.6
logging.getLogger('').addHandler(_null_handler)


class Loggers(object):
    """
    Collection of loggers to stderr, wrapped for simplicity
    """
    # todo - WIP, this will get more sophisticated!

    # map first character of level to actual level setting, for convenience
    _level_map = {'c': logging.CRITICAL,
                  'f': logging.FATAL,
                  'e': logging.ERROR,
                  'w': logging.WARN,
                  'i': logging.INFO,
                  'd': logging.DEBUG,
                  'n': logging.NOTSET}

    def __init__(self):
        self._user_logger_names = []

    def __repr__(self):
        header = ["{0:<8}  {1:<50}  {2:<14}".format("Level", "Logger", "# of Handlers"),
                  "{0:<8}  {1:<50}  {2:<14}".format("-"*8, "-"*50, "-"*14)]
        entries = []
        for name in self._user_logger_names:
            entries.append(self._get_repr_line(name, None))
        return "\n".join(header + entries)

    @staticmethod
    def _get_repr_line(name, alias):
        logger = logging.getLogger(name)
        if alias:
            name += " (%s)" % alias
        return "{0:<8}  {1:<50}  {2:<14}".format(logging.getLevelName(logger.level),
                                                 name,
                                                 len(logger.handlers))

    @staticmethod
    def get(logger_name):
        """returns the logger of the given name"""
        return logging.getLogger(logger_name)

    def set(self, level=logging.DEBUG, logger_name='', output=None, line_format=None):
        """
        Sets the level and adds handlers to the given logger

        Parameters
        ----------
        level : int, str or logging.*, optional
            The level to which the logger will be set.  May be 0,10,20,30,40,50
            or "DEBUG", "INFO", etc.  (only first letter is requirecd)
            Setting to None disables the logging to stderr
            See `https://docs.python.org/2/library/logging.html`
            If not specified, DEBUG is used
            To turn OFF the logger, set level to 0 or None
        logger_name: str, optional
            The name of the logger.  If empty string, then the trustedanalytics root logger is set
        output: file or str, or list of such, optional
            The file object or name of the file to log to.  If empty, then stderr is used

        Examples
        --------
        # to enable INFO level logging to file 'log.txt' and no printing to stderr:
        >>> loggers.set('INFO', 'trustedanalytics.rest.frame','log.txt', False)
        """
        logger_name = logger_name if logger_name != 'root' else ''
        if not level:
            return self._turn_logger_off(logger_name)

        line_format = line_format if line_format is not None else LINE_FORMAT
        logger = logging.getLogger(logger_name)
        if not output:
            output = sys.stderr
        if isinstance(output, basestring):
            handler = logging.FileHandler(output)
        elif isinstance(output, list) or isinstance(output, tuple):
            logger = None
            for o in output:
                logger = self.set(level, logger_name, o, line_format)
            return logger
        else:
            try:
                handler = logging.StreamHandler(output)
            except:
                raise ValueError("Bad output argument %s.  Expected stream or file name." % output)

        try:
            handler_name = output.name
        except:
            handler_name = str(output)

        if isinstance(level, basestring):
            c = str(level)[0].lower()  # only require first letter
            level = self._level_map[c]
        logger.setLevel(level)

        self._add_handler_to_logger(logger, handler, handler_name, line_format)

        # store logger name
        if logger_name not in self._user_logger_names:
            self._user_logger_names.append(logger_name)
        return logger

    @staticmethod
    def _logger_has_handler(logger, handler_name):
        return logger.handlers and any([h.name for h in logger.handlers if h.name == handler_name])

    @staticmethod
    def _add_handler_to_logger(logger, handler, handler_name, line_format):
        handler.setLevel(logging.DEBUG)
        handler.name = handler_name
        formatter = logging.Formatter(line_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _turn_logger_off(self, logger_name):
        logger = logging.getLogger(logger_name)
        logger.level = logging.CRITICAL
        victim_handlers = [x for x in logger.handlers]
        for h in victim_handlers:
            logger.removeHandler(h)
        try:
            self._user_logger_names.remove(logger_name)
        except ValueError:
            pass
        return logger

    def set_spark(self, sc, level):
        logger = sc._jvm.org.apache.log4j
        if not level:
            level = "unspecified"
        new_level = {
            "d": logger.Level.DEBUG,
            "e": logger.Level.ERROR,
            "w": logger.Level.WARN,
            "i": logger.Level.INFO,
            "o": logger.Level.OFF,
        }[level.lower()[0]]
        logger.LogManager.getLogger("org").setLevel(new_level)
        logger.LogManager.getLogger("akka").setLevel(new_level)

loggers = Loggers()


# Logging backdoor
#
# If env variable is set, we will call loggers.set immediately, so the loggers
# can run during the rest of the trustedanalytics package import
#
# The value of this env var is a JSON list containing map, each of which
# represents a call to loggers.set.  The map holds the **kwargs for the
# call to loggers.set
#
# Example:  This sets the module logger to debug for core/frame.py
#
# $ export TRUSTEDANALYTICS_LOGGERS='[{"logger_name": "trustedanalytics.core.frame", "level": "debug"}]'
#
import os
loggers_env_name = "SPARK_TK_LOGGERS"
loggers_env = os.getenv(loggers_env_name)
if loggers_env:
    print "$SPARK_TK_LOGGERS=%s" % loggers_env
    try:
        import json
        for entry in json.loads(loggers_env):
            loggers.set(**entry)
    except Exception as e:
        import sys
        sys.stderr.write("!! Error trying to ingest logging env variable $%s\n" % loggers_env_name)
        raise