#---------------------------------------------------------------------------------------------------------------------------------------------------------
# tests/test_language_model.py -- conversation history, system-prompt loading + fallback, chat-log writing, and token accounting.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os

import constants
from providers import TokenUsage


# ---- conversation history -------------------------------------------------------------------------------------------------------------------------------

def test_history_is_seeded_with_the_system_prompt ( language_model_factory ):

    language_model = language_model_factory ()

    assert len ( language_model.conversation_history ) == 1
    assert language_model.conversation_history [ 0 ] [ 'role' ] == constants.MODEL_MESSAGE_ROLE_SYSTEM


def test_add_message_appends_role_and_content ( language_model_factory ):

    language_model = language_model_factory ()
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )

    assert language_model.conversation_history [ -1 ] == { 'role' : 'user', 'content' : 'hi' }


def test_remove_last_message ( language_model_factory ):

    language_model = language_model_factory ()
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )
    language_model.remove_last_message_from_conversation_history ()

    assert [ message [ 'role' ] for message in language_model.conversation_history ] == [ constants.MODEL_MESSAGE_ROLE_SYSTEM ]


def test_reset_preserves_only_the_system_prompt ( language_model_factory ):

    language_model = language_model_factory ()
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )
    language_model.add_message_to_conversation_history ( 'hello', constants.MODEL_MESSAGE_ROLE_AI )
    language_model.reset_conversation_history ()

    assert [ message [ 'role' ] for message in language_model.conversation_history ] == [ constants.MODEL_MESSAGE_ROLE_SYSTEM ]
    assert language_model.conversation_history [ 0 ] [ 'content' ] == language_model.system_prompt


# ---- system prompt --------------------------------------------------------------------------------------------------------------------------------------

def test_system_prompt_loaded_from_file ( language_model_factory ):

    language_model = language_model_factory ()

    assert language_model.system_prompt_source.endswith ( 'system_prompt.txt' )
    assert language_model.system_prompt == language_model.conversation_history [ 0 ] [ 'content' ]


def test_system_prompt_falls_back_to_default ( language_model_factory ):

    language_model = language_model_factory ( overrides = { 'prompts' : { 'system_prompt' : 'data/no_such_prompt.txt' } } )

    assert language_model.system_prompt_source == 'default'
    assert language_model.system_prompt == language_model.MODEL_SYSTEM_PROMPT_DEFAULT


# ---- query delegation -----------------------------------------------------------------------------------------------------------------------------------

def test_query_streaming_returns_iterator ( language_model_factory ):

    language_model = language_model_factory ( overrides = { 'model' : { 'streaming' : True } }, deltas = [ 'a', 'b' ] )
    response       = language_model.query_language_model ()

    assert not isinstance ( response, str )
    assert list ( response ) == [ 'a', 'b' ]


def test_query_non_streaming_returns_string ( language_model_factory ):

    language_model = language_model_factory ( overrides = { 'model' : { 'streaming' : False } }, deltas = [ 'one ', 'shot' ] )
    response       = language_model.query_language_model ()

    assert response == 'one shot'


# ---- token accounting -----------------------------------------------------------------------------------------------------------------------------------

def test_update_token_usage_accumulates ( language_model_factory ):

    language_model                   = language_model_factory ()
    language_model.provider.last_token_usage = TokenUsage ( 4, 1, 5 )

    first = language_model.update_token_usage ()

    assert first == TokenUsage ( 4, 1, 5 )
    assert language_model.session_token_usage == TokenUsage ( 4, 1, 5 )

    language_model.provider.last_token_usage = TokenUsage ( 6, 2, 8 )
    language_model.update_token_usage ()

    assert language_model.session_token_usage == TokenUsage ( 10, 3, 13 )


def test_update_token_usage_handles_none ( language_model_factory ):

    language_model                           = language_model_factory ()
    language_model.provider.last_token_usage = None

    assert language_model.update_token_usage () is None
    assert language_model.session_token_usage == TokenUsage ( 0, 0, 0 )


# ---- chat-log writing -----------------------------------------------------------------------------------------------------------------------------------

def read_only_log ( folder ):

    files = sorted ( os.listdir ( folder ) )
    return files, open ( os.path.join ( folder, files [ 0 ] ), encoding = 'utf-8' ).read ()


def test_chat_log_filename_numbering ( language_model_factory ):

    language_model = language_model_factory ()
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )

    language_model.save_chat_log_to_file ()
    language_model.save_chat_log_to_file ()

    files = sorted ( os.listdir ( language_model.chat_log_folder ) )
    assert files == [ 'chat_log_0.txt', 'chat_log_1.txt' ]


def test_chat_log_header_and_content ( language_model_factory ):

    language_model = language_model_factory ()
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )
    language_model.add_message_to_conversation_history ( 'hello', constants.MODEL_MESSAGE_ROLE_AI )
    language_model.save_chat_log_to_file ()

    _, content = read_only_log ( language_model.chat_log_folder )

    assert 'Provider:' in content
    assert 'Streaming Enabled:' in content
    assert '[user]' in content and 'hi' in content
    assert '[assistant]' in content and 'hello' in content


def test_chat_log_excludes_system_prompt_by_default ( language_model_factory ):

    language_model = language_model_factory ()
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )
    language_model.save_chat_log_to_file ()

    _, content = read_only_log ( language_model.chat_log_folder )
    assert '[system]' not in content


def test_chat_log_includes_system_prompt_when_configured ( language_model_factory ):

    language_model = language_model_factory ( overrides = { 'chat_log' : { 'include_system_prompt' : True } } )
    language_model.add_message_to_conversation_history ( 'hi', constants.MODEL_MESSAGE_ROLE_USER )
    language_model.save_chat_log_to_file ()                         # default arg -> uses the configured flag

    _, content = read_only_log ( language_model.chat_log_folder )
    assert '[system]' in content
