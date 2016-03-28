import logging
import sys

LOGGING_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
FILE_LOGGING_FORMAT = '%(asctime)s,%(levelname)s,%(name)s,%(message)s'

# captureWarnings exists only since 2.7
_nh = None
if sys.hexversion > 0x2070000:
    logging.captureWarnings(True)
    _nh = logging.NullHandler()
else:
    # doesn't exists in older versions
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    _nh = NullHandler()

logging.root.name = 'aeriscloud'

_logger = logging.root
_logger.addHandler(_nh)
# disable all logs
_logger.setLevel(60)
# prevent root logger from outputting
_logger.propagate = False


def get_logger(name=None, parent=_logger):
    if name:
        if not hasattr(parent, 'getChild'):
            return parent.manager.getLogger('.'.join([parent.name, name]))
        return parent.getChild(name)
    return parent


def set_log_level(lvl):
    # custom stream handler by default
    if _nh in _logger.handlers:
        _logger.removeHandler(_nh)
        _handler = logging.StreamHandler()
        _handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        _logger.addHandler(_handler)
    _logger.setLevel(lvl)


def set_log_file(filename):
    _logger.removeHandler(_nh)
    _file_handler = logging.FileHandler(filename)
    _file_handler.setFormatter(logging.Formatter(FILE_LOGGING_FORMAT))
    _logger.addHandler(_file_handler)
