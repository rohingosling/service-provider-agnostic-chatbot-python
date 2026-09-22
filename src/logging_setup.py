#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       logging_setup.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Diagnostics logging. Configures Python's standard-library logging with a console handler ( warnings and above, on stderr ) and a rotating
#   file handler under the configured log directory ( at the configured level ).
# - Logging is for diagnostics only and is strictly separate from the user-facing chat output, which always goes through the Renderer ( stdout ).
#   Secrets ( API keys ) are never logged.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os
import logging

from logging.handlers import RotatingFileHandler

# Map the configured level name to a logging level.

LOGGING_LEVEL_BY_NAME = {
    'debug'   : logging.DEBUG,
    'info'    : logging.INFO,
    'warning' : logging.WARNING,
    'error'   : logging.ERROR,
}

# Rotating file handler settings.

LOG_FILE_NAME         = 'application.log'
LOG_FILE_MAX_BYTES    = 1048576   # 1 MiB per file before rotation
LOG_FILE_BACKUP_COUNT = 5

# Log record format.

LOG_FORMAT       = '%(asctime)s  %(levelname)-8s  %(name)s  %(message)s'
LOG_DATE_FORMAT  = '%Y-%m-%d %H:%M:%S'

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Configure diagnostics logging.
#
# Function name:
# - configure_logging
#
# Description:
# - Installs a console handler ( warnings and above, on stderr ) and, when enabled, a rotating file handler under the configured directory at the
#   configured level. Existing handlers are removed first, so re-configuration ( e.g. in tests ) does not accumulate duplicate handlers.
#
# Parameters:
# - logging_config : LoggingConfig : The logging configuration ( level, file_enabled, directory ).
#
# Return Values:
# - None.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def configure_logging ( logging_config ):

    # Resolve the configured level.

    level = LOGGING_LEVEL_BY_NAME.get ( logging_config.level, logging.INFO )

    # Reset the root logger so re-configuration does not accumulate handlers.

    root_logger = logging.getLogger ()

    for handler in list ( root_logger.handlers ):
        root_logger.removeHandler ( handler )

    # The root level must pass whatever the most verbose handler needs: the file handler ( configured level ) or the console ( warnings ).

    root_logger.setLevel ( min ( level, logging.WARNING ) )

    formatter = logging.Formatter ( LOG_FORMAT, datefmt = LOG_DATE_FORMAT )

    # Console handler: warnings and above, on stderr, so it never shares the chat output channel ( stdout ).

    console_handler = logging.StreamHandler ()
    console_handler.setLevel ( logging.WARNING )
    console_handler.setFormatter ( formatter )
    root_logger.addHandler ( console_handler )

    # Rotating file handler: full detail at the configured level.

    if logging_config.file_enabled:

        os.makedirs ( logging_config.directory, exist_ok = True )

        log_file_path = os.path.join ( logging_config.directory, LOG_FILE_NAME )
        file_handler  = RotatingFileHandler (
            log_file_path,
            maxBytes    = LOG_FILE_MAX_BYTES,
            backupCount = LOG_FILE_BACKUP_COUNT,
            encoding    = 'utf-8',
        )
        file_handler.setLevel ( level )
        file_handler.setFormatter ( formatter )
        root_logger.addHandler ( file_handler )
