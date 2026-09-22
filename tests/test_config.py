#---------------------------------------------------------------------------------------------------------------------------------------------------------
# tests/test_config.py -- configuration loading, defaults-merge, path resolution, and invalid-value handling.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os

import constants


def test_defaults_when_no_file ( load_config ):

    configuration = load_config ( None )

    assert configuration.provider.name == 'openai'
    assert configuration.model.name == 'gpt-4o'
    assert configuration.model.max_tokens == 1024
    assert configuration.model.temperature == 0.7
    assert configuration.model.streaming is True
    assert configuration.rendering.rich_enabled is True
    assert configuration.application.agent_name_user == 'User'
    assert configuration.application.agent_name_ai == 'AI'
    assert configuration.application.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_UNPROMPTED_RESPONSE
    assert configuration.logging.level == 'info'
    assert configuration.logging.token_tracking is False


def test_override_changes_values ( load_config ):

    configuration = load_config (
        '[model]\nname = "gpt-4"\ntemperature = 1.5\nstreaming = false\n'
        '[rendering]\nrich_enabled = false\n'
    )

    assert configuration.model.name == 'gpt-4'
    assert configuration.model.temperature == 1.5
    assert configuration.model.streaming is False
    assert configuration.rendering.rich_enabled is False


def test_partial_section_merges_over_defaults ( load_config ):

    # Only model.name is provided; the other model keys fall back to their defaults.

    configuration = load_config ( '[model]\nname = "gpt-4"\n' )

    assert configuration.model.name == 'gpt-4'
    assert configuration.model.max_tokens == 1024
    assert configuration.model.temperature == 0.7


def test_missing_file_falls_back_to_defaults ( load_config ):

    assert load_config ( None ).model.name == 'gpt-4o'


def test_malformed_toml_falls_back_without_crashing ( load_config ):

    configuration = load_config ( 'this is not = = valid toml [[[\n' )

    assert configuration.model.name == 'gpt-4o'


def test_invalid_introduction_behavior_uses_default ( load_config ):

    configuration = load_config ( '[application]\nintroduction_behavior = "banana"\n' )

    assert configuration.application.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_UNPROMPTED_RESPONSE


def test_negative_max_tokens_uses_default ( load_config ):

    assert load_config ( '[model]\nmax_tokens = -5\n' ).model.max_tokens == 1024


def test_out_of_range_temperature_uses_default ( load_config ):

    assert load_config ( '[model]\ntemperature = 9.9\n' ).model.temperature == 0.7


def test_invalid_logging_level_uses_default ( load_config ):

    assert load_config ( '[logging]\nlevel = "loud"\n' ).logging.level == 'info'


def test_invalid_value_logs_a_warning ( load_config, caplog ):

    import logging

    with caplog.at_level ( logging.WARNING ):
        load_config ( '[model]\nmax_tokens = -5\n' )

    assert any ( 'max_tokens' in record.getMessage () for record in caplog.records )


def test_introduction_behavior_mapping ( load_config ):

    assert load_config ( '[application]\nintroduction_behavior = "none"\n'      ).application.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_NONE
    assert load_config ( '[application]\nintroduction_behavior = "prompted"\n'  ).application.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_PROMPTED_RESPONSE


def test_paths_are_absolute_and_project_anchored ( load_config ):

    configuration = load_config ( None )

    assert os.path.isabs ( configuration.prompts.system_prompt )
    assert configuration.prompts.system_prompt.endswith ( os.path.join ( 'data', 'system_prompt.txt' ) )
    assert os.path.isabs ( configuration.chat_log.directory )
    assert os.path.isabs ( configuration.logging.directory )


def test_token_tracking_flag ( load_config ):

    assert load_config ( None ).logging.token_tracking is False
    assert load_config ( '[logging]\ntoken_tracking = true\n' ).logging.token_tracking is True


def test_default_colors ( load_config ):

    colors = load_config ( None ).colors

    assert colors.general     == constants.TERMINAL_COLOR_GENERAL
    assert colors.header      == constants.TERMINAL_COLOR_HEADER
    assert colors.field_value == constants.TERMINAL_COLOR_FIELD_VALUE
    assert colors.ai_prompt   == constants.TERMINAL_COLOR_AI_PROMPT
    assert colors.user_text   == constants.TERMINAL_COLOR_USER_TEXT


def test_color_override_changes_values ( load_config ):

    colors = load_config ( '[colors]\nai_text = "magenta"\nuser_text = "cyan"\n' ).colors

    assert colors.ai_text   == 'magenta'
    assert colors.user_text == 'cyan'
    assert colors.header    == constants.TERMINAL_COLOR_HEADER   # unspecified keys keep their default


def test_invalid_color_uses_default ( load_config ):

    colors = load_config ( '[colors]\nheader = "not-a-real-colour"\n' ).colors

    assert colors.header == constants.TERMINAL_COLOR_HEADER


def test_hex_and_rgb_colors_are_accepted ( load_config ):

    colors = load_config ( '[colors]\nai_text = "#1e90ff"\nuser_text = "rgb(30,144,255)"\n' ).colors

    assert colors.ai_text   == '#1e90ff'
    assert colors.user_text == 'rgb(30,144,255)'
