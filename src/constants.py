#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Centralized constants module.
# - Collects the constants that v2 scattered (and partly duplicated) across the `Application` and `LanguageModel` classes into one place, so every
#   module imports shared literals from a single source.
# - Grouped by concern: language model meta parameters, message roles, application states, application commands, user prompt commands, OS terminal
#   commands, terminal management tags, and the startup introduction behaviour.
#
# Usage Notes:
#
# - Import the module and reference its members by name, e.g.
#
#     import constants
#     ...
#     if self.command == constants.APPLICATION_COMMAND_EXIT:
#         ...
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

# Constants: Language Model Meta Parameters.
# - Supported model names. The active model is selected in `LanguageModel.__init__`.

MODEL_NAME_GPT_3_5_TURBO   = 'gpt-3.5-turbo'
MODEL_NAME_GPT_4           = 'gpt-4'
MODEL_NAME_GPT_4O          = 'gpt-4o'
MODEL_NAME_CLAUDE_OPUS_4_8 = 'claude-opus-4-8'

# Constants: Provider Selection.
# - Names of the supported chat backends. The active provider is resolved through the provider registry in `providers/registry.py`.

PROVIDER_NAME_OPENAI    = 'openai'
PROVIDER_NAME_ANTHROPIC = 'anthropic'

# Constants: Message Roles.
# - Role tags applied to each message in the conversation history sent to the model.

MODEL_MESSAGE_ROLE_SYSTEM = 'system'
MODEL_MESSAGE_ROLE_USER   = 'user'
MODEL_MESSAGE_ROLE_AI     = 'assistant'

# Constants: Application States.
# - Application states are used to control application flow.

APPLICATION_STATE_IDLE    = 0   # Default application state. Usually used to initialise application state variables before giving them a value later.
APPLICATION_STATE_RUNNING = 1   # The application main loop is running.
APPLICATION_STATE_STOPPED = 2   # The application main loop is stopped.

# Constants: Application Commands.
# - Application commands control application state, or trigger actions.
# - Note:
#   - In a more sophisticated application we would define "events" that drive application state, in the form of a state machine. Where anything could
#     raise an event.
#   - For the sake of simplicity, this reference application will just make use of simple user triggered commands to drive application state and actions.

APPLICATION_COMMAND_NONE               = 0
APPLICATION_COMMAND_EXIT               = 1
APPLICATION_COMMAND_CLEAR_TERMINAL     = 2
APPLICATION_COMMAND_HELP               = 3
APPLICATION_COMMAND_SHOW_SYSTEM_PROMPT = 4
APPLICATION_COMMAND_SAVE               = 5
APPLICATION_COMMAND_RESET              = 6

# Constants: User Prompt Commands.
# - A command is the command prefix ( PROMPT_COMMAND_PREFIX, default "/" ) followed by a command name, e.g. "/exit". The prefix keeps commands
#   distinct from conversational input; changing it ( e.g. to "-" or "--" ) re-prefixes every command. The COMMAND_REGISTRY stores the bare
#   command names: get_application_command applies the prefix when matching input, and build_help_text applies it when listing commands.

PROMPT_COMMAND_NONE   = ''
PROMPT_COMMAND_PREFIX = '/'
PROMPT_COMMAND_EXIT   = 'exit'
PROMPT_COMMAND_STOP   = 'stop'
PROMPT_COMMAND_CLEAR  = 'clear'
PROMPT_COMMAND_HELP   = 'help'
PROMPT_COMMAND_SYSTEM = 'system'
PROMPT_COMMAND_SAVE   = 'save'
PROMPT_COMMAND_RESET  = 'reset'

# Command Registry.
# - Maps each bare command name ( and its aliases ) to an application command and a help description. `help` is generated from this registry,
#   so newly added commands appear automatically. The command prefix ( PROMPT_COMMAND_PREFIX ) is applied to these names at parse / display time.

COMMAND_REGISTRY = [
    { 'prompts': [ PROMPT_COMMAND_EXIT, PROMPT_COMMAND_STOP ], 'command': APPLICATION_COMMAND_EXIT,               'description': 'Exit the application ( saves the chat log ).' },
    { 'prompts': [ PROMPT_COMMAND_CLEAR ]                    , 'command': APPLICATION_COMMAND_CLEAR_TERMINAL,     'description': 'Clear the terminal.' },
    { 'prompts': [ PROMPT_COMMAND_HELP ]                     , 'command': APPLICATION_COMMAND_HELP,               'description': 'List the available commands.' },
    { 'prompts': [ PROMPT_COMMAND_SYSTEM ]                   , 'command': APPLICATION_COMMAND_SHOW_SYSTEM_PROMPT, 'description': 'Print the active system prompt.' },
    { 'prompts': [ PROMPT_COMMAND_SAVE ]                     , 'command': APPLICATION_COMMAND_SAVE,               'description': 'Save the chat log now, without exiting.' },
    { 'prompts': [ PROMPT_COMMAND_RESET ]                    , 'command': APPLICATION_COMMAND_RESET,              'description': 'Clear the conversation history ( keeps the system prompt ).' },
]

# Constants: User Prompt Editing.
# - Input-editing tokens recognised while reading the user's prompt ( as opposed to the PROMPT_COMMAND_* whole-line commands above ).
# - PROMPT_CONTINUATION_CHARACTER: when a physical input line ends with this character, get_user_prompt joins it with the next line, so the
#   user can enter a multi-line prompt by ending each line with "\" before pressing Enter.

PROMPT_CONTINUATION_CHARACTER = '\\'

# Constants: Terminal Commands.
# - Terminal commands that can be issued to the OS terminal.
# - When a user enters a prompt command, the command interpreter will convert the prompt command to an application command.
# - The command manager will execute the latest command. If the latest command is to issue a command to the terminal, then these constants will be used
#   to execute the actual command on the appropriate OS terminal.

TERMINAL_COMMAND_CLEAR_TERMINAL_WINDOWS = 'cls'
TERMINAL_COMMAND_CLEAR_TERMINAL_LINUX   = 'clear'

# Constants: Terminal Management.
# - Terminal formatting and rendering.

TERMINAL_PROMPT_AGENT_NAMETAG = '<agent_name>'                              # Markdown tag to be replaced with actual agent name.
TERMINAL_PROMPT_FORMAT        = '[' + TERMINAL_PROMPT_AGENT_NAMETAG + ']'   # Terminal prompt format, e.g. "[User]".
TERMINAL_ERROR                = '[Error]'
TERMINAL_SYSTEM               = '[SYSTEM]'
TERMINAL_BULLET               = '- '

# Constants: Terminal Control.
# - ANSI escape sequence used to erase the echoed continuation character ( "\" ) from the line the user just submitted, so a multi-line prompt
#   leaves no stray "\" characters on screen. Emitted only on an interactive, ANSI-capable terminal ( see Application.enable_terminal_ansi_support ).
# - { column } is substituted with the 1-based column of the continuation character. The sequence moves the cursor up one line, jumps to that
#   column, clears to the end of the line ( deleting the "\" ), then drops back down to the fresh line ready for the next line of input.

TERMINAL_ANSI_ERASE_CONTINUATION_MARKER = '\x1b[1A\x1b[{column}G\x1b[K\x1b[1B\r'

# Constants: Terminal Colours.
# - Default Rich style names for each kind of terminal output. These are the built-in defaults; each can be overridden per-install via the
#   [colors] section of config.toml ( config.py validates the configured value and falls back to these on a bad one ). The light/normal pairs
#   ( e.g. bright_red / red ) give the "light X" vs "X" distinction, and TERMINAL_COLOR_GENERAL is used as the Console's default ( light grey ) style.

TERMINAL_COLOR_GENERAL     = 'white'         # Light grey - default / general text ( ANSI 7 ).
TERMINAL_COLOR_HEADER      = 'bright_white'  # White - section headers, e.g. "Application:", "Model:" ( ANSI 15 ).
TERMINAL_COLOR_FIELD_VALUE = 'bright_black'  # Dark grey - banner field values ( ANSI 8 ).
TERMINAL_COLOR_AI_PROMPT   = 'bright_red'    # Light red - AI prompt label, e.g. "[AI]" ( ANSI 9 ).
TERMINAL_COLOR_AI_TEXT     = 'red'           # Red - AI response text, before Markdown recolours it ( ANSI 1 ).
TERMINAL_COLOR_USER_PROMPT = 'bright_blue'   # Light blue - user prompt label, e.g. "[User]" ( ANSI 12 ).
TERMINAL_COLOR_USER_TEXT   = 'blue'          # Blue - echoed user input ( ANSI 4 ).

# - The user input echo is coloured with a raw ANSI SGR sequence ( Rich cannot colour input() echo ); that "set foreground" sequence is derived
#   at runtime from the configured user-text colour ( see Renderer ), so only the universal reset is a fixed constant here.

TERMINAL_ANSI_RESET = '\x1b[0m'   # Reset all SGR attributes.

# Constants: Introduction Behaviour.
# - Selects how the agent greets the user at startup (consumed in a later phase).
# - NONE                : Silent start, no greeting.
# - UNPROMPTED_RESPONSE : Print a canned greeting and seed it into history as the assistant's first turn.
# - PROMPTED_RESPONSE   : Feed a seed prompt to the model and render a live self-introduction.

INTRODUCTION_BEHAVIOR_NONE                = 0
INTRODUCTION_BEHAVIOR_UNPROMPTED_RESPONSE = 1
INTRODUCTION_BEHAVIOR_PROMPTED_RESPONSE   = 2
