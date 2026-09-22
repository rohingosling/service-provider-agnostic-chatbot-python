#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       config.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - External configuration. Loads data/config.toml with the standard-library tomllib and merges it over a built-in defaults structure, so a
#   missing file, section, or key still yields a complete, valid configuration. Malformed TOML or out-of-range values fall back to the default
#   ( with a logged warning ) rather than crashing.
# - Exposes a nested Config object ( one small dataclass per TOML section ) that Application distributes to the other components.
# - All configured paths are resolved relative to the project root via __file__, preserving working-directory independence.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os
import logging
import tomllib

from dataclasses import dataclass
from rich.color  import Color, ColorParseError

import constants

logger = logging.getLogger ( __name__ )

# Resolve the configuration file relative to the project root ( the parent of this src/ directory ).

PROJECT_ROOT_DIRECTORY = os.path.dirname ( os.path.dirname ( os.path.abspath ( __file__ ) ) )
CONFIG_FILE_NAME       = os.path.join ( PROJECT_ROOT_DIRECTORY, 'data', 'config.toml' )

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Configuration data classes ( one per config.toml section, composed into Config ).
#---------------------------------------------------------------------------------------------------------------------------------------------------------

@dataclass
class ApplicationConfig:

    agent_name_user:       str
    agent_name_ai:         str
    introduction_behavior: int   # mapped from the config string to an INTRODUCTION_BEHAVIOR_* constant

@dataclass
class ProviderConfig:

    name: str

@dataclass
class ModelConfig:

    name:        str
    max_tokens:  int
    temperature: float
    streaming:   bool

@dataclass
class RenderingConfig:

    rich_enabled: bool

@dataclass
class ColorsConfig:

    general:     str
    header:      str
    field_value: str
    ai_prompt:   str
    ai_text:     str
    user_prompt: str
    user_text:   str

@dataclass
class PromptsConfig:

    system_prompt:         str   # absolute path
    introduction_prompt:   str   # absolute path
    introduction_response: str   # absolute path

@dataclass
class LoggingConfig:

    level:          str
    file_enabled:   bool
    directory:      str   # absolute path
    token_tracking: bool

@dataclass
class ChatLogConfig:

    directory:             str   # absolute path
    file_prefix:           str
    file_extension:        str
    include_system_prompt: bool

@dataclass
class Config:

    application: ApplicationConfig
    provider:    ProviderConfig
    model:       ModelConfig
    rendering:   RenderingConfig
    colors:      ColorsConfig
    prompts:     PromptsConfig
    logging:     LoggingConfig
    chat_log:    ChatLogConfig

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Built-in defaults and lookups.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

# Built-in defaults. Mirror data/config.toml; a missing file, section, or key falls back to these values.

DEFAULT_CONFIG = {
    'application' : { 'agent_name_user' : 'User', 'agent_name_ai' : 'AI', 'introduction_behavior' : 'unprompted' },
    'provider'    : { 'name' : 'openai' },
    'model'       : { 'name' : 'gpt-4o', 'max_tokens' : 1024, 'temperature' : 0.7, 'streaming' : True },
    'rendering'   : { 'rich_enabled' : True },
    'colors'      : {
                      'general'     : constants.TERMINAL_COLOR_GENERAL,
                      'header'      : constants.TERMINAL_COLOR_HEADER,
                      'field_value' : constants.TERMINAL_COLOR_FIELD_VALUE,
                      'ai_prompt'   : constants.TERMINAL_COLOR_AI_PROMPT,
                      'ai_text'     : constants.TERMINAL_COLOR_AI_TEXT,
                      'user_prompt' : constants.TERMINAL_COLOR_USER_PROMPT,
                      'user_text'   : constants.TERMINAL_COLOR_USER_TEXT,
                    },
    'prompts'     : {
                      'system_prompt'         : 'data/system_prompt.txt',
                      'introduction_prompt'   : 'data/prompts/introduction_prompt.txt',
                      'introduction_response' : 'data/prompts/introduction_response.txt',
                    },
    'logging'     : { 'level' : 'info', 'file_enabled' : True, 'directory' : 'log', 'token_tracking' : False },
    'chat_log'    : {
                      'directory'             : 'chat_log',
                      'file_prefix'           : 'chat_log_',
                      'file_extension'        : '.txt',
                      'include_system_prompt' : False,
                    },
}

# Map the introduction_behavior config string to its application constant.

INTRODUCTION_BEHAVIOR_BY_NAME = {
    'none'       : constants.INTRODUCTION_BEHAVIOR_NONE,
    'unprompted' : constants.INTRODUCTION_BEHAVIOR_UNPROMPTED_RESPONSE,
    'prompted'   : constants.INTRODUCTION_BEHAVIOR_PROMPTED_RESPONSE,
}

# Permitted logging levels.

LOGGING_LEVELS = ( 'debug', 'info', 'warning', 'error' )

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Resolve a configured path relative to the project root.
#
# Function name:
# - resolve_path
#
# Parameters:
# - path : str : A path from the configuration, absolute or relative to the project root.
#
# Return Values:
# - str : The absolute, normalized path.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def resolve_path ( path ):

    if os.path.isabs ( path ):
        return os.path.normpath ( path )

    return os.path.normpath ( os.path.join ( PROJECT_ROOT_DIRECTORY, path ) )

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Read and parse config.toml.
#
# Function name:
# - read_raw_config
#
# Description:
# - Reads data/config.toml and returns the parsed dict. A missing file returns an empty dict ( defaults apply ). Malformed TOML or a read
#   error logs a warning and returns an empty dict, so loading never crashes ( CFG-1 ).
#
# Return Values:
# - dict : The raw parsed configuration, or an empty dict on absence / error.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def read_raw_config ():

    if not os.path.exists ( CONFIG_FILE_NAME ):
        return {}

    try:
        with open ( CONFIG_FILE_NAME, 'rb' ) as config_file:
            return tomllib.load ( config_file )

    except ( tomllib.TOMLDecodeError, OSError ) as exception:
        logger.warning ( "Could not read config file '%s': %s. Using defaults.", CONFIG_FILE_NAME, exception )
        return {}

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Merge the loaded configuration over the built-in defaults.
#
# Function name:
# - merge_over_defaults
#
# Description:
# - For each known section and key, takes the loaded value when present, otherwise the default. Unknown sections / keys are ignored.
#
# Parameters:
# - loaded : dict : The raw parsed configuration.
#
# Return Values:
# - dict : A complete configuration dict with every known key populated.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def merge_over_defaults ( loaded ):

    # Start with an empty result, to be populated section by section.

    merged = {}

    # Process every known section defined in the defaults.

    for section, default_values in DEFAULT_CONFIG.items ():

        # Seed the section from a copy of its defaults, then look up the matching loaded section.

        merged [ section ] = dict ( default_values )
        loaded_section     = loaded.get ( section )

        # When the section was supplied, override each known key with the loaded value.

        if isinstance ( loaded_section, dict ):

            for key in default_values:

                if key in loaded_section:
                    
                    merged [ section ] [ key ] = loaded_section [ key ]

    return merged

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Validation helpers. Each returns the value when valid, otherwise logs a warning and returns the default ( CFG-4, CFG-5 ).
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def validated_choice ( value, choices, default, name ):

    if value in choices:
        return value

    logger.warning ( "Invalid value %r for '%s'; using default %r.", value, name, default )
    return default

def validated_int ( value, default, name, minimum = 1 ):

    if isinstance ( value, int ) and not isinstance ( value, bool ) and value >= minimum:
        return value

    logger.warning ( "Invalid value %r for '%s'; using default %r.", value, name, default )
    return default

def validated_float ( value, default, name, low, high ):

    if isinstance ( value, ( int, float ) ) and not isinstance ( value, bool ) and low <= value <= high:
        return float ( value )

    logger.warning ( "Invalid value %r for '%s'; using default %r.", value, name, default )
    return default

def validated_bool ( value, default, name ):

    if isinstance ( value, bool ):
        return value

    logger.warning ( "Invalid value %r for '%s'; using default %r.", value, name, default )
    return default

def validated_color ( value, default, name ):

    # Accept any value `rich` can parse as a colour ( a palette name, "color(N)", a hex "#rrggbb", or "rgb(r,g,b)" ); otherwise warn and use the default.

    if isinstance ( value, str ):
        try:
            Color.parse ( value )
            return value
        except ColorParseError:
            pass

    logger.warning ( "Invalid value %r for '%s'; using default %r.", value, name, default )
    return default

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Load the application configuration.
#
# Function name:
# - load_configuration
#
# Description:
# - Reads config.toml, merges it over the built-in defaults, validates each value ( falling back with a warning on bad input ), resolves all
#   paths relative to the project root, and returns a fully-populated, nested Config object. This function never raises.
#
# Return Values:
# - Config : The complete, validated configuration.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def load_configuration ():

    # Read and merge.

    merged = merge_over_defaults ( read_raw_config () )

    # Application.

    application_section   = merged [ 'application' ]
    introduction_name     = validated_choice ( application_section [ 'introduction_behavior' ], INTRODUCTION_BEHAVIOR_BY_NAME, 'unprompted', 'application.introduction_behavior' )

    application_config = ApplicationConfig (
        agent_name_user       = str ( application_section [ 'agent_name_user' ] ),
        agent_name_ai         = str ( application_section [ 'agent_name_ai' ] ),
        introduction_behavior = INTRODUCTION_BEHAVIOR_BY_NAME [ introduction_name ],
    )

    # Provider.

    provider_config = ProviderConfig ( name = str ( merged [ 'provider' ] [ 'name' ] ) )

    # Model.

    model_section = merged [ 'model' ]

    model_config = ModelConfig (
        name        = str ( model_section [ 'name' ] ),
        max_tokens  = validated_int   ( model_section [ 'max_tokens' ],  1024, 'model.max_tokens' ),
        temperature = validated_float ( model_section [ 'temperature' ], 0.7,  'model.temperature', 0.0, 2.0 ),
        streaming   = validated_bool  ( model_section [ 'streaming' ],   True, 'model.streaming' ),
    )

    # Rendering.

    rendering_config = RenderingConfig (
        rich_enabled = validated_bool ( merged [ 'rendering' ] [ 'rich_enabled' ], True, 'rendering.rich_enabled' ),
    )

    # Colours.

    colors_section = merged [ 'colors' ]

    colors_config = ColorsConfig (
        general     = validated_color ( colors_section [ 'general' ],     constants.TERMINAL_COLOR_GENERAL,     'colors.general' ),
        header      = validated_color ( colors_section [ 'header' ],      constants.TERMINAL_COLOR_HEADER,      'colors.header' ),
        field_value = validated_color ( colors_section [ 'field_value' ], constants.TERMINAL_COLOR_FIELD_VALUE, 'colors.field_value' ),
        ai_prompt   = validated_color ( colors_section [ 'ai_prompt' ],   constants.TERMINAL_COLOR_AI_PROMPT,   'colors.ai_prompt' ),
        ai_text     = validated_color ( colors_section [ 'ai_text' ],     constants.TERMINAL_COLOR_AI_TEXT,     'colors.ai_text' ),
        user_prompt = validated_color ( colors_section [ 'user_prompt' ], constants.TERMINAL_COLOR_USER_PROMPT, 'colors.user_prompt' ),
        user_text   = validated_color ( colors_section [ 'user_text' ],   constants.TERMINAL_COLOR_USER_TEXT,   'colors.user_text' ),
    )

    # Prompts ( paths resolved relative to the project root ).

    prompts_section = merged [ 'prompts' ]

    prompts_config = PromptsConfig (
        system_prompt         = resolve_path ( str ( prompts_section [ 'system_prompt' ] ) ),
        introduction_prompt   = resolve_path ( str ( prompts_section [ 'introduction_prompt' ] ) ),
        introduction_response = resolve_path ( str ( prompts_section [ 'introduction_response' ] ) ),
    )

    # Logging.

    logging_section = merged [ 'logging' ]

    logging_config = LoggingConfig (
        level          = validated_choice ( logging_section [ 'level' ], LOGGING_LEVELS, 'info', 'logging.level' ),
        file_enabled   = validated_bool   ( logging_section [ 'file_enabled' ], True, 'logging.file_enabled' ),
        directory      = resolve_path ( str ( logging_section [ 'directory' ] ) ),
        token_tracking = validated_bool   ( logging_section [ 'token_tracking' ], False, 'logging.token_tracking' ),
    )

    # Chat log.

    chat_log_section = merged [ 'chat_log' ]

    chat_log_config = ChatLogConfig (
        directory             = resolve_path ( str ( chat_log_section [ 'directory' ] ) ),
        file_prefix           = str ( chat_log_section [ 'file_prefix' ] ),
        file_extension        = str ( chat_log_section [ 'file_extension' ] ),
        include_system_prompt = validated_bool ( chat_log_section [ 'include_system_prompt' ], False, 'chat_log.include_system_prompt' ),
    )

    # Compose and return the configuration.

    return Config (
        application = application_config,
        provider    = provider_config,
        model       = model_config,
        rendering   = rendering_config,
        colors      = colors_config,
        prompts     = prompts_config,
        logging     = logging_config,
        chat_log    = chat_log_config,
    )
