#---------------------------------------------------------------------------------------------------------------------------------------------------------
# tests/test_application.py -- command classification, the classify/execute split, history exclusion, introduction modes, and render dispatch.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import constants


SYSTEM = constants.MODEL_MESSAGE_ROLE_SYSTEM
USER   = constants.MODEL_MESSAGE_ROLE_USER
AI     = constants.MODEL_MESSAGE_ROLE_AI


def roles ( application ):

    return [ message [ 'role' ] for message in application.model.conversation_history ]


# ---- command classification -----------------------------------------------------------------------------------------------------------------------------

def test_classifies_each_command ( application_factory ):

    application = application_factory ()

    expected = {
        '/exit'   : constants.APPLICATION_COMMAND_EXIT,
        '/stop'   : constants.APPLICATION_COMMAND_EXIT,            # alias
        '/clear'  : constants.APPLICATION_COMMAND_CLEAR_TERMINAL,
        '/help'   : constants.APPLICATION_COMMAND_HELP,
        '/system' : constants.APPLICATION_COMMAND_SHOW_SYSTEM_PROMPT,
        '/save'   : constants.APPLICATION_COMMAND_SAVE,
        '/reset'  : constants.APPLICATION_COMMAND_RESET,
    }

    for prompt, command in expected.items ():
        assert application.get_application_command ( prompt ) == command


def test_classification_is_case_insensitive_and_trimmed ( application_factory ):

    application = application_factory ()

    assert application.get_application_command ( '  /HELP  ' ) == constants.APPLICATION_COMMAND_HELP
    assert application.get_application_command ( '/ReSeT' )    == constants.APPLICATION_COMMAND_RESET


def test_unprefixed_and_unknown_input_is_conversational ( application_factory ):

    application = application_factory ()

    assert application.get_application_command ( 'exit' )   == constants.APPLICATION_COMMAND_NONE   # no prefix -> chat
    assert application.get_application_command ( 'hello' )  == constants.APPLICATION_COMMAND_NONE
    assert application.get_application_command ( '/helpme' ) == constants.APPLICATION_COMMAND_NONE


def test_command_prompt_name ( application_factory ):

    application = application_factory ()

    assert application.command_prompt_name ( constants.APPLICATION_COMMAND_HELP ) == '/help'
    assert application.command_prompt_name ( constants.APPLICATION_COMMAND_EXIT ) == '/exit'


def test_help_text_lists_every_command ( application_factory ):

    application = application_factory ()
    help_text   = application.build_help_text ()

    for prompt in ( '/exit', '/stop', '/clear', '/help', '/system', '/save', '/reset' ):
        assert prompt in help_text


# ---- multi-line prompt continuation ---------------------------------------------------------------------------------------------------------------------

def test_single_line_prompt_is_returned_unchanged ( application_factory ):

    application = application_factory ( inputs = [ 'just one line' ] )

    assert application.get_user_prompt () == 'just one line'


def test_trailing_backslash_continues_onto_the_next_line ( application_factory ):

    application = application_factory ( inputs = [ 'first line\\', 'second line' ] )

    assert application.get_user_prompt () == 'first line\nsecond line'


def test_multiple_continuations_accumulate ( application_factory ):

    application = application_factory ( inputs = [ 'a\\', 'b\\', 'c' ] )

    assert application.get_user_prompt () == 'a\nb\nc'


def test_continuation_emits_no_ansi_when_output_is_not_a_tty ( application_factory, capsys ):

    application = application_factory ( inputs = [ 'a\\', 'b' ] )

    assert application.get_user_prompt () == 'a\nb'
    assert '\x1b' not in capsys.readouterr ().out         # no cursor-control codes when stdout is captured ( not a TTY )


# ---- terminal styling -----------------------------------------------------------------------------------------------------------------------------------

def test_user_prompt_label_is_emitted ( application_factory, capsys ):

    application = application_factory ( inputs = [ 'hello' ] )

    assert application.get_user_prompt () == 'hello'
    assert '[User]' in capsys.readouterr ().out           # the prompt label is shown above the input


def test_application_info_banner_contains_headers_and_values ( application_factory, capsys ):

    application = application_factory ()
    application.print_application_info ()

    output = capsys.readouterr ().out

    assert 'Application:' in output
    assert 'Model:'       in output
    assert 'Name:'        in output
    assert str ( application.version ) in output          # the version value appears in the banner


def test_renderer_without_colors_uses_built_in_defaults ():

    import renderer as renderer_module

    renderer = renderer_module.Renderer ( rich_enabled = False )

    assert renderer.colors.user_text     == constants.TERMINAL_COLOR_USER_TEXT
    assert renderer.ansi_user_text_color == '\x1b[34m'    # blue foreground, derived from the default user-text colour


def test_renderer_derives_user_text_ansi_from_configured_colour ( make_config ):

    import renderer as renderer_module

    configuration = make_config ( overrides = { 'colors' : { 'user_text' : 'red' } } )
    renderer      = renderer_module.Renderer ( rich_enabled = configuration.rendering.rich_enabled, colors = configuration.colors )

    assert renderer.colors.user_text     == 'red'
    assert renderer.ansi_user_text_color == '\x1b[31m'    # red foreground, derived from the configured colour


# ---- classify / execute split + history exclusion -------------------------------------------------------------------------------------------------------

def test_commands_never_enter_history ( application_factory ):

    application = application_factory ( overrides = { 'application' : { 'introduction_behavior' : 'none' } },
                                        inputs    = [ '/help', '/system', '/save', '/reset', '/exit' ] )
    application.run ()

    assert roles ( application ) == [ SYSTEM ]


def test_conversational_turn_is_appended ( application_factory ):

    application = application_factory ( overrides = { 'application' : { 'introduction_behavior' : 'none' } },
                                        deltas    = [ 'Hello' ],
                                        inputs    = [ 'hi there', '/exit' ] )
    application.run ()

    assert roles ( application ) == [ SYSTEM, USER, AI ]
    assert application.model.conversation_history [ -1 ] [ 'content' ] == 'Hello'


# ---- introduction modes ---------------------------------------------------------------------------------------------------------------------------------

def test_introduction_none ( application_factory ):

    application = application_factory ( overrides = { 'application' : { 'introduction_behavior' : 'none' } } )
    application.show_introduction ()

    assert roles ( application ) == [ SYSTEM ]


def test_introduction_unprompted ( application_factory, capsys ):

    application = application_factory ( overrides = { 'application' : { 'introduction_behavior' : 'unprompted' } } )
    application.show_introduction ()

    assert roles ( application ) == [ SYSTEM, AI ]                 # canned greeting seeded as the assistant turn
    assert application.model.provider.calls == []                 # no provider call
    assert 'Hello' in capsys.readouterr ().out


def test_introduction_prompted_drops_the_seed ( application_factory ):

    application = application_factory ( overrides = { 'application' : { 'introduction_behavior' : 'prompted' } },
                                        deltas    = [ 'Hi, ', 'I can help.' ] )
    application.show_introduction ()

    assert roles ( application ) == [ SYSTEM, AI ]                 # only the generated intro, seed dropped
    assert application.model.conversation_history [ -1 ] [ 'content' ] == 'Hi, I can help.'
    assert len ( application.model.provider.calls ) == 1          # one provider call


# ---- render dispatch ------------------------------------------------------------------------------------------------------------------------------------

def test_render_streaming_returns_accumulated_text ( application_factory ):

    application = application_factory ( overrides = { 'model' : { 'streaming' : True } } )
    text        = application.render_language_model_response ( iter ( [ 'Stream', 'ed' ] ) )

    assert text == 'Streamed'


def test_render_non_streaming_returns_text ( application_factory ):

    application = application_factory ( overrides = { 'model' : { 'streaming' : False } } )
    text        = application.render_language_model_response ( 'Complete reply' )

    assert text == 'Complete reply'


# ---- command execution ----------------------------------------------------------------------------------------------------------------------------------

def test_execute_exit_stops_the_loop ( application_factory ):

    application         = application_factory ()
    application.command = constants.APPLICATION_COMMAND_EXIT
    application.execute_application_command ()

    assert application.state == constants.APPLICATION_STATE_STOPPED


def test_execute_system_prints_raw_prompt ( application_factory, capsys ):

    application         = application_factory ()
    application.command = constants.APPLICATION_COMMAND_SHOW_SYSTEM_PROMPT
    application.execute_application_command ()

    output = capsys.readouterr ().out
    assert application.model.system_prompt [ : 16 ] in output


def test_execute_reset_clears_history ( application_factory ):

    application = application_factory ()
    application.model.add_message_to_conversation_history ( 'hi', USER )
    application.command = constants.APPLICATION_COMMAND_RESET
    application.execute_application_command ()

    assert roles ( application ) == [ SYSTEM ]


def test_execute_clear_uses_the_correct_os_command ( application_factory, monkeypatch ):

    import platform
    import os as os_module

    recorded = []
    monkeypatch.setattr ( os_module, 'system', lambda command : recorded.append ( command ) )

    application         = application_factory ()
    application.command = constants.APPLICATION_COMMAND_CLEAR_TERMINAL
    application.execute_application_command ()

    expected = 'cls' if platform.system () == 'Windows' else 'clear'
    assert recorded == [ expected ]
