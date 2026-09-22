#---------------------------------------------------------------------------------------------------------------------------------------------------------
# tests/test_providers.py -- provider registry, the ChatProvider contract, and OpenAIProvider conformance against a mocked SDK.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import types

import pytest

from providers import ChatProvider, ModelParameters, ProviderError, TokenUsage, create_provider
from providers.openai_provider import OpenAIProvider
from providers.registry import PROVIDER_REGISTRY


# ---- registry -------------------------------------------------------------------------------------------------------------------------------------------

def test_registry_maps_openai ():

    assert PROVIDER_REGISTRY [ 'openai' ] is OpenAIProvider


def test_create_known_provider_returns_instance ( fake_provider_class ):

    provider = create_provider ( 'fake' )

    assert isinstance ( provider, ChatProvider )
    assert isinstance ( provider, fake_provider_class )


def test_unknown_provider_raises_clear_error ():

    with pytest.raises ( ProviderError ) as error_info:
        create_provider ( 'no_such_provider' )

    message = str ( error_info.value )
    assert 'no_such_provider' in message
    assert 'openai' in message


def test_chat_provider_is_abstract ():

    with pytest.raises ( TypeError ):
        ChatProvider ()


# ---- TokenUsage -----------------------------------------------------------------------------------------------------------------------------------------

def test_token_usage_addition ():

    assert TokenUsage ( 10, 5, 15 ) + TokenUsage ( 3, 7, 10 ) == TokenUsage ( 13, 12, 25 )


# ---- OpenAIProvider -------------------------------------------------------------------------------------------------------------------------------------

def test_missing_api_key_raises_clear_error ( monkeypatch ):

    monkeypatch.delenv ( 'OPENAI_API_KEY', raising = False )

    with pytest.raises ( ProviderError ) as error_info:
        OpenAIProvider ()

    assert 'OPENAI_API_KEY' in str ( error_info.value )


def make_usage ( prompt, completion, total ):

    return types.SimpleNamespace ( prompt_tokens = prompt, completion_tokens = completion, total_tokens = total )


def content_chunk ( text ):

    return types.SimpleNamespace ( choices = [ types.SimpleNamespace ( delta = types.SimpleNamespace ( content = text ) ) ], usage = None )


def final_usage_chunk ( usage ):

    # The include_usage final chunk carries usage and NO choices.
    return types.SimpleNamespace ( choices = [], usage = usage )


def build_openai_provider ( monkeypatch, completions ):

    monkeypatch.setenv ( 'OPENAI_API_KEY', 'sk-test-dummy' )
    provider        = OpenAIProvider ()
    provider.client = types.SimpleNamespace ( chat = types.SimpleNamespace ( completions = completions ) )
    return provider


def test_complete_chat_returns_text_and_captures_usage ( monkeypatch ):

    class Completions:
        def create ( self, ** keyword_args ):
            assert keyword_args [ 'stream' ] is False
            return types.SimpleNamespace (
                choices = [ types.SimpleNamespace ( message = types.SimpleNamespace ( content = 'Hello there' ) ) ],
                usage   = make_usage ( 7, 2, 9 ),
            )

    provider   = build_openai_provider ( monkeypatch, Completions () )
    parameters = ModelParameters ( 'gpt-4o', 1024, 0.7 )

    text = provider.complete_chat ( [ { 'role' : 'user', 'content' : 'hi' } ], parameters )

    assert text == 'Hello there'
    assert provider.last_token_usage == TokenUsage ( 7, 2, 9 )


def test_stream_chat_yields_deltas_and_captures_usage ( monkeypatch ):

    class Completions:
        def create ( self, ** keyword_args ):
            assert keyword_args [ 'stream' ] is True
            assert keyword_args [ 'stream_options' ] == { 'include_usage' : True }
            return iter ( [ content_chunk ( 'Hel' ), content_chunk ( 'lo' ), final_usage_chunk ( make_usage ( 5, 2, 7 ) ) ] )

    provider   = build_openai_provider ( monkeypatch, Completions () )
    parameters = ModelParameters ( 'gpt-4o', 1024, 0.7 )

    deltas = list ( provider.stream_chat ( [ { 'role' : 'user', 'content' : 'hi' } ], parameters ) )

    assert deltas == [ 'Hel', 'lo' ]                          # the choice-less final chunk yielded nothing
    assert provider.last_token_usage == TokenUsage ( 5, 2, 7 )


def test_complete_chat_wraps_sdk_errors ( monkeypatch ):

    class Completions:
        def create ( self, ** keyword_args ):
            raise RuntimeError ( 'boom' )

    provider   = build_openai_provider ( monkeypatch, Completions () )
    parameters = ModelParameters ( 'gpt-4o', 1024, 0.7 )

    with pytest.raises ( ProviderError ):
        provider.complete_chat ( [ { 'role' : 'user', 'content' : 'hi' } ], parameters )


def test_stream_chat_wraps_sdk_errors ( monkeypatch ):

    class Completions:
        def create ( self, ** keyword_args ):
            raise RuntimeError ( 'boom' )

    provider   = build_openai_provider ( monkeypatch, Completions () )
    parameters = ModelParameters ( 'gpt-4o', 1024, 0.7 )

    with pytest.raises ( ProviderError ):
        list ( provider.stream_chat ( [ { 'role' : 'user', 'content' : 'hi' } ], parameters ) )
