#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       tests/conftest.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Shared pytest fixtures. The whole suite runs offline: a FakeChatProvider stands in for any backend ( no API key, no network, the OpenAI SDK
#   is never called ), builtins.input is patched where the loop is driven, and all output paths use pytest temporary directories.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os
import sys

import pytest

# Make the application modules ( in ../src ) importable.

SRC_DIRECTORY = os.path.join ( os.path.dirname ( os.path.dirname ( os.path.abspath ( __file__ ) ) ), 'src' )

if SRC_DIRECTORY not in sys.path:
    sys.path.insert ( 0, SRC_DIRECTORY )

import config as config_module
import providers.registry as registry_module

from providers import ChatProvider

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# A configurable fake provider used in place of any real backend.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

class FakeChatProvider ( ChatProvider ):

    def __init__ ( self, deltas = None, usage = None, error = None ):

        self.deltas           = list ( deltas ) if deltas is not None else [ 'ok' ]
        self.usage            = usage
        self.error            = error
        self.last_token_usage = None
        self.calls            = []

    def stream_chat ( self, messages, parameters ):

        self.calls.append ( ( 'stream', [ dict ( message ) for message in messages ] ) )
        self.last_token_usage = None

        if self.error is not None:
            raise self.error

        for delta in self.deltas:
            yield delta

        self.last_token_usage = self.usage

    def complete_chat ( self, messages, parameters ):

        self.calls.append ( ( 'complete', [ dict ( message ) for message in messages ] ) )
        self.last_token_usage = None

        if self.error is not None:
            raise self.error

        self.last_token_usage = self.usage
        return ''.join ( self.deltas )

    @property
    def credential_environment_variable ( self ):

        return 'FAKE_KEY'

# Register the fake under a name, so Application / LanguageModel can be constructed offline ( create_provider ( 'fake' ) -> FakeChatProvider () ).

registry_module.PROVIDER_REGISTRY [ 'fake' ] = FakeChatProvider

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Helpers.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def toml_scalar ( value ):

    if isinstance ( value, bool ):
        return 'true' if value else 'false'

    if isinstance ( value, str ):
        return '"%s"' % value.replace ( '\\', '/' )

    return str ( value )

def dict_to_toml ( sections ):

    lines = []

    for section, values in sections.items ():
        lines.append ( '[%s]' % section )
        for key, value in values.items ():
            lines.append ( '%s = %s' % ( key, toml_scalar ( value ) ) )
        lines.append ( '' )

    return '\n'.join ( lines )

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Fixtures.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def fake_provider_class ():

    return FakeChatProvider

@pytest.fixture
def load_config ( tmp_path ):

    # Load a Config from raw TOML text. text=None leaves no file ( exercising the missing-file path ).

    def factory ( text = None ):

        config_path = tmp_path / 'config.toml'

        if text is not None:
            config_path.write_text ( text, encoding = 'utf-8' )

        saved_path                     = config_module.CONFIG_FILE_NAME
        config_module.CONFIG_FILE_NAME = str ( config_path )

        try:
            return config_module.load_configuration ()
        finally:
            config_module.CONFIG_FILE_NAME = saved_path

    return factory

@pytest.fixture
def make_config ( tmp_path ):

    # Build a Config for component tests: a fake provider, plain rendering, file logging off, and temp output directories, plus overrides.

    def factory ( overrides = None ):

        merged = {
            'provider'  : { 'name' : 'fake' },
            'rendering' : { 'rich_enabled' : False },
            'logging'   : { 'file_enabled' : False, 'directory' : str ( tmp_path / 'log' ) },
            'chat_log'  : { 'directory' : str ( tmp_path / 'chat_log' ) },
        }

        for section, values in ( overrides or {} ).items ():
            merged.setdefault ( section, {} ).update ( values )

        config_path = tmp_path / 'config.toml'
        config_path.write_text ( dict_to_toml ( merged ), encoding = 'utf-8' )

        saved_path                     = config_module.CONFIG_FILE_NAME
        config_module.CONFIG_FILE_NAME = str ( config_path )

        try:
            return config_module.load_configuration ()
        finally:
            config_module.CONFIG_FILE_NAME = saved_path

    return factory

@pytest.fixture
def language_model_factory ( make_config ):

    import language_model as language_model_module

    def factory ( overrides = None, deltas = None, usage = None, error = None ):

        configuration  = make_config ( overrides )
        language_model = language_model_module.LanguageModel (
            configuration.model, configuration.provider, configuration.prompts, configuration.chat_log
        )
        language_model.provider = FakeChatProvider ( deltas = deltas, usage = usage, error = error )
        return language_model

    return factory

@pytest.fixture
def application_factory ( make_config, monkeypatch ):

    import application as application_module

    def factory ( overrides = None, deltas = None, usage = None, error = None, inputs = None ):

        configuration = make_config ( overrides )
        application   = application_module.Application ( configuration )

        application.model.provider = FakeChatProvider ( deltas = deltas, usage = usage, error = error )

        if inputs is not None:
            input_iterator = iter ( inputs )
            monkeypatch.setattr ( 'builtins.input', lambda * args, ** keyword_args : next ( input_iterator ) )

        return application

    return factory
