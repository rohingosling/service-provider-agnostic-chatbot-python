#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Version:      2.1
# Release Date: 2026-06-27
# Author:       Rohin Gosling
#
# Description:
#
# - General-purpose conversation agent reference application, that can be used as the starting point for an OpenAI API-style chatbot.
#
# - main_loop:
#
#   - 1. Get user input prompt. 
#   - 2.     Get application command from user input prompt. 
#   - 3.     Append user input prompt to conversation history.
#   - 4. Query language model using user input prompt.
#   - 5.     Render language model response.
#   - 6.     Append language model response to conversation history.
#   - 7. Execute application command. 
#
# Features:
#
# - Turn-based conversation agent, with conversation history.
# - Autosave conversation history to a text file.
# 
# Dependencies:
# 
# - OpenAI Library:
#
#   pip install --upgrade openai 
#
# Usage Notes:
#
# - The variable `model_client` is initialized to an instance of `OpenAI`.
#   - OpenAI.api_key is set using the environment variable `OPENAI_API_KEY`.
#   - You will need to set `OPENAI_API_KEY` to hold your OpenAI API key. 
#   - Keep the key out of source code: set it in the environment ( or load it from an OS keyring ), and never commit it.
#   - If you record it in a local `.env` file, commit only a `.env.example` with placeholder values; `.env` is git-ignored.
#
# - On first use run the following batch files in order.
#   1. `venv_create.bat` to create the Python virtual environment.
#   2. 'venv_install_requirements.bat` to install dependent packages. 
#
# - For general use, run the following batch files before use. 
#   1. `venv_activate.bat` to activate the Python virtual environment.
#
# - To-Do:
#   5. Restructure system prompt initialization, so that initialization of the system prompt takes place in the initialization function.
#   6. Add feedback in both the console and chat log files, to show the system prompt file name. Or whether the default system prompt was used.  
#   7. Add a test command to show the system prompt.
#   8. Decide where is the most logical place to put the conversation log file. In the application class, or the LLM model class.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os
import sys
import shutil
import platform
import logging
import time

import constants
from config         import load_configuration
from language_model import LanguageModel
from logging_setup  import configure_logging
from providers      import ProviderError
from renderer       import Renderer
from utility        import load_text_to_string

logger = logging.getLogger ( __name__ )

class Application:

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Constructor.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__ ( self, config = None ):

        # Load the configuration if one was not injected ( e.g. by tests ).

        if config is None:
            config = load_configuration ()

        self.config = config

        # Configure diagnostics logging from the configuration.

        configure_logging ( config.logging )

        # Initialise application.

        self.name            = 'Conversation Agent Reference Application'
        self.version         = 2.1
        self.agent_name_user = config.application.agent_name_user
        self.agent_name_ai   = config.application.agent_name_ai
        self.command         = constants.APPLICATION_COMMAND_NONE
        self.state           = constants.APPLICATION_STATE_IDLE

        # Initialise the startup introduction behaviour.

        self.introduction_behavior = config.application.introduction_behavior

        # Initialise the renderer.

        self.renderer = Renderer ( rich_enabled = config.rendering.rich_enabled, colors = config.colors )

        # Initialise the model.

        self.model = LanguageModel ( config.model, config.provider, config.prompts, config.chat_log )

        # Determine once whether the terminal can interpret ANSI cursor-control sequences, used to tidy the continuation character from
        # multi-line prompts. Off for non-interactive output ( pipes, redirects, captured test output ).

        self.terminal_ansi_enabled = self.enable_terminal_ansi_support ()

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Starts an instance of the application class.    
    #
    # Function name:
    # - run
    #
    # Description:
    # - This is the main public function that consumers of the class call to execute the application.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #
    # Preconditions:
    # - Application classes must be initialized.
    #
    # Postconditions:
    # - Main application has been executed, and has exited.
    #
    # To-Do:
    # 1. Improve error handling within the loop.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def run ( self ):

        logger.info ( 'Application starting.' )

        self.print_application_info ()

        # Emit the configurable startup introduction before entering the main loop.

        self.show_introduction ()

        # Run the main loop. Any unexpected error is rendered as a readable traceback rather than crashing with a raw stack trace.

        try:
            self.main_loop ()
        except Exception as unexpected_error:
            logger.exception ( 'Unhandled error in the main loop.' )
            self.renderer.render_error ( unexpected_error, recoverable = False )

        if self.config.logging.token_tracking:
            session_token_usage = self.model.session_token_usage
            logger.info ( 'Session token usage: prompt=%d, completion=%d, total=%d.', session_token_usage.prompt_tokens, session_token_usage.completion_tokens, session_token_usage.total_tokens )

        logger.info ( 'Application stopped.' )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Emit the configurable startup introduction.
    #
    # Function name:
    # - show_introduction
    #
    # Description:
    # - Emits the startup introduction according to `self.introduction_behavior`:
    #   - NONE                : no introduction.
    #   - UNPROMPTED_RESPONSE : render a canned greeting and seed it into history as the assistant's first turn ( no provider call ).
    #   - PROMPTED_RESPONSE   : send a seed prompt to the model, render the generated introduction, and record only the introduction.
    # - A missing or unreadable introduction asset degrades gracefully to no introduction.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def show_introduction ( self ):

        # No introduction.

        if self.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_NONE:
            return

        # Unprompted introduction: render a canned greeting and seed it into history as the assistant's first turn ( no provider call ).

        if self.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_UNPROMPTED_RESPONSE:

            introduction_text = load_text_to_string ( self.config.prompts.introduction_response )

            if not introduction_text:
                return

            terminal_prompt_ai = f'[{self.agent_name_ai}]'

            self.renderer.render_complete_response ( introduction_text, terminal_prompt_ai )
            self.model.add_message_to_conversation_history ( introduction_text, constants.MODEL_MESSAGE_ROLE_AI )

            return

        # Prompted introduction: send a seed prompt to the model, render the generated introduction, and record only the introduction.

        if self.introduction_behavior == constants.INTRODUCTION_BEHAVIOR_PROMPTED_RESPONSE:

            introduction_prompt = load_text_to_string ( self.config.prompts.introduction_prompt )

            if not introduction_prompt:
                return

            # Send the seed prompt transiently: add it, query the model, then remove it so only the generated introduction is recorded.

            self.model.add_message_to_conversation_history ( introduction_prompt, constants.MODEL_MESSAGE_ROLE_USER )

            try:
                model_response    = self.model.query_language_model ()
                introduction_text = self.render_language_model_response ( model_response )

            except ProviderError as provider_error:
                self.model.remove_last_message_from_conversation_history ()
                self.renderer.render_error ( provider_error, recoverable = True )
                return

            self.model.remove_last_message_from_conversation_history ()
            self.model.add_message_to_conversation_history ( introduction_text, constants.MODEL_MESSAGE_ROLE_AI )

            return

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Main loop of the application handling user input and querying the language model.
    #
    # Function name:
    # - main_loop
    #
    # Description:
    # - This function runs the main loop of the application.
    # - It handles user input, queries the language model, and executes application commands.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #
    # Preconditions:
    # - Application and model classes must be initialized.
    #
    # Postconditions:
    # - User input is processed and language model responses are generated and rendered.
    #
    # To-Do:
    # 1. Improve error handling within the loop.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def main_loop ( self ):
        
        # Initialise main loop.  

        self.command = constants.APPLICATION_COMMAND_NONE
        self.state   = constants.APPLICATION_STATE_RUNNING    

        # Execute the main loop.

        while self.state == constants.APPLICATION_STATE_RUNNING:
    
            # Get user input prompt.
            # 1. Get the user's input prompt from the terminal.
            # 2. Identify and initialize any application commands the user may have issued.
            # 3. Save the user's prompt to the conversation history.

            user_input   = self.get_user_prompt ()
            self.command = self.get_application_command ( user_input )                
            
            # Query language model and update conversation history.
            # 1. Append user input to conversation history. We add the user input to teh conversation history here, so that it doesn't get added in the case of a 
            #    command like `exit` for example, where we would not want the conversation history added when it is being written to the chat log later. 
            # 2. Query language model. The provider returns normalized output: an iterator of text deltas when streaming, or the complete
            #    response text otherwise. A provider failure surfaces as a ProviderError, handled below.
            # 3. Render model response. If streaming is enabled the renderer prints text deltas as they arrive; otherwise it prints the
            #    complete response text.
            # 4. Append language model response to conversation history. Skipped if the query fails, so errors never enter the history.
            # 4. Append language model response to conversation history.

            if self.command == constants.APPLICATION_COMMAND_NONE:

                self.model.add_message_to_conversation_history ( user_input, constants.MODEL_MESSAGE_ROLE_USER )

                try:
                    request_start_time  = time.monotonic ()
                    model_response      = self.model.query_language_model ()
                    model_response_text = self.render_language_model_response ( model_response )
                    self.model.add_message_to_conversation_history ( model_response_text, constants.MODEL_MESSAGE_ROLE_AI )

                    logger.info ( 'Provider response received in %.2f s ( %d characters ).', time.monotonic () - request_start_time, len ( model_response_text ) )

                    if self.config.logging.token_tracking:
                        response_token_usage = self.model.update_token_usage ()
                        if response_token_usage is not None:
                            logger.info ( 'Token usage: prompt=%d, completion=%d, total=%d ( session total=%d ).', response_token_usage.prompt_tokens, response_token_usage.completion_tokens, response_token_usage.total_tokens, self.model.session_token_usage.total_tokens )

                except ProviderError as provider_error:
                    # Report the provider failure, keep the loop alive, and do not pollute the conversation history.
                    logger.warning ( 'Provider error: %s', provider_error )
                    self.renderer.render_error ( provider_error, recoverable = True )

            # Execute application command.            

            self.execute_application_command ()

        # Shut down program.

        self.model.save_chat_log_to_file ()

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Retrieve the user prompt from the terminal.
    #
    # Function name:
    # - get_user_prompt
    #
    # Description:
    # - This function retrieves the user's input prompt from the terminal.
    # - It compiles the terminal prompt label from the user's agent name, shows it in light blue, and colours the echoed input blue ( on an
    #   ANSI-capable terminal with rich rendering enabled ); it then returns the entered prompt.
    # - A line ending with the continuation character ( PROMPT_CONTINUATION_CHARACTER, "\" ) is joined with the next line, so the user can
    #   enter a multi-line prompt by ending each line with "\" before pressing Enter. The trailing "\" is dropped from each continued line.
    # - On an ANSI-capable terminal the echoed "\" is erased from the screen as each line is submitted, so the finished multi-line prompt shows
    #   no stray "\" characters ( the prompt sent to the model never contains them either, regardless of terminal ).
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - user_prompt : str : The user's input prompt ( physical lines joined with newlines when continuation is used ).
    #
    # Preconditions:
    # - The application class must be initialized.
    #
    # Postconditions:
    # - The user's input prompt is retrieved and returned.
    #
    # To-Do:
    # 1. Add input validation for user prompt.
    # 2. Handle edge cases for empty or invalid inputs.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_user_prompt ( self ):

        # Render the prompt label ( light blue ), then colour the echoed input ( blue ) on an ANSI-capable terminal with rich enabled. The colour
        # is set once and reset only after the whole ( possibly multi-line ) prompt has been read, so every continued line is coloured too.

        terminal_prompt_user = f'[{self.agent_name_user}]'

        self.renderer.render_user_prompt_label ( terminal_prompt_user )

        colour_input = self.renderer.rich_enabled and self.terminal_ansi_enabled

        if colour_input:
            print ( self.renderer.ansi_user_text_color, end = '', flush = True )

        # Read the first physical line, then keep reading while each line ends with the continuation character ( "\" + Enter ). The trailing
        # continuation character is dropped from each continued line, and the accumulated lines are joined into a single multi-line prompt.

        input_lines  = []
        current_line = input ()

        while current_line.endswith ( constants.PROMPT_CONTINUATION_CHARACTER ):

            input_lines.append ( current_line [ : -1 ] )   # Drop the trailing continuation character.

            # Tidy the screen by erasing the continuation character the terminal echoed, so the submitted prompt shows no stray "\". Skipped when
            # ANSI is unavailable, or when the line is wide enough to have wrapped ( where the cursor maths is unreliable ) - the "\" is then left
            # in place rather than risk corrupting the display.

            if self.terminal_ansi_enabled and len ( current_line ) < shutil.get_terminal_size ().columns:
                erase_sequence = constants.TERMINAL_ANSI_ERASE_CONTINUATION_MARKER.format ( column = len ( current_line ) )
                print ( erase_sequence, end = '', flush = True )

            current_line = input ()                        # Read the next physical line ( no prompt label ).

        input_lines.append ( current_line )

        # Reset the input colour now that the whole prompt has been read.

        if colour_input:
            print ( constants.TERMINAL_ANSI_RESET, end = '', flush = True )

        user_prompt = '\n'.join ( input_lines )

        return user_prompt
    
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Determine whether ANSI cursor-control sequences may be emitted to the terminal.
    #
    # Function name:
    # - enable_terminal_ansi_support
    #
    # Description:
    # - Multi-line prompt entry tidies the echoed continuation character ( "\" ) by emitting ANSI cursor-control sequences, which are only safe
    #   on an interactive, ANSI-capable terminal.
    # - Returns False when output is not a TTY ( piped, redirected, or captured under tests ), so escape codes are never written into a file or a
    #   test's captured output.
    # - On Windows, enables ENABLE_VIRTUAL_TERMINAL_PROCESSING on the stdout console handle ( required before ANSI is interpreted ), degrading
    #   gracefully to False on any failure. Other platforms are assumed to interpret ANSI on an interactive terminal.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - bool : True if ANSI cursor-control sequences may be emitted to the terminal; otherwise False.
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def enable_terminal_ansi_support ( self ):

        # ANSI cursor control is only meaningful for an interactive terminal; skip it when output is piped, redirected, or captured ( e.g. tests ).

        if not sys.stdout.isatty ():
            return False

        # Non-Windows interactive terminals are assumed to interpret ANSI escape sequences.

        if platform.system () != 'Windows':
            return True

        # Windows: virtual-terminal processing must be enabled on the stdout handle before ANSI escape sequences are interpreted. Degrade
        # gracefully ( return False ) on any failure, so the application never emits raw escape codes to a console that cannot render them.

        try:
            import ctypes

            STANDARD_OUTPUT_HANDLE             = -11
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

            kernel32      = ctypes.windll.kernel32
            stdout_handle = kernel32.GetStdHandle ( STANDARD_OUTPUT_HANDLE )
            console_mode  = ctypes.c_uint32 ()

            if not kernel32.GetConsoleMode ( stdout_handle, ctypes.byref ( console_mode ) ):
                return False

            if not kernel32.SetConsoleMode ( stdout_handle, console_mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING ):
                return False

            return True

        except Exception:
            return False

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Convert the user prompt to an application command.
    #
    # Function name:
    # - get_application_command
    #
    # Description:
    # - This function converts the user's input prompt to an application command.
    # - It normalizes the user prompt to lowercase and identifies any application commands to execute.
    #
    # Parameters:
    # - user_prompt : str : The user's input prompt.
    #
    # Return Values:
    # - application_command : int : The application command constant.
    #
    # Preconditions:
    # - The user prompt must be a string.
    #
    # Postconditions:
    # - The appropriate application command is identified and returned.
    #
    # To-Do:
    # 1. Add more user prompt commands.
    # 2. Improve error handling for unrecognized commands.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_application_command ( self, user_prompt ):

        # Normalize the user prompt ( trim surrounding whitespace and lower-case it ), then match it against the command registry.

        application_command = constants.APPLICATION_COMMAND_NONE
        normalized_prompt   = user_prompt.strip ().lower ()

        # Identify any application command the user intends to execute. A command is the command prefix ( PROMPT_COMMAND_PREFIX ) plus a name.

        for command_entry in constants.COMMAND_REGISTRY:
            command_prompts = [ constants.PROMPT_COMMAND_PREFIX + command_name for command_name in command_entry [ 'prompts' ] ]
            if normalized_prompt in command_prompts:
                application_command = command_entry [ 'command' ]
                break

        # Return the selected command to the caller.

        return application_command

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Execute the application command.
    #
    # Function name:
    # - execute_application_command
    #
    # Description:
    # - This function executes the identified application command.
    # - It handles commands like exiting the application or clearing the terminal.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #
    # Preconditions:
    # - The application class must be initialized.
    # - A valid application command must be set.
    #
    # Postconditions:
    # - The application command is executed and the application state is updated.
    #
    # To-Do:
    # 1. Add more application commands and their handling.
    # 2. Improve error handling for command execution.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def execute_application_command ( self ):

        # Log any non-trivial command execution ( diagnostics ).

        if self.command != constants.APPLICATION_COMMAND_NONE:
            logger.info ( 'Executing application command %s `%s`.', self.command, self.command_prompt_name ( self.command ) )

        # No command.

        if self.command == constants.APPLICATION_COMMAND_NONE:
            pass

        # Exit the application.

        elif self.command == constants.APPLICATION_COMMAND_EXIT:
            self.state = constants.APPLICATION_STATE_STOPPED

        # Clear the application terminal.

        elif self.command == constants.APPLICATION_COMMAND_CLEAR_TERMINAL:
            if platform.system () == "Windows":
                os.system ( constants.TERMINAL_COMMAND_CLEAR_TERMINAL_WINDOWS )
            else:
                os.system ( constants.TERMINAL_COMMAND_CLEAR_TERMINAL_LINUX )

        # List the available commands.

        elif self.command == constants.APPLICATION_COMMAND_HELP:
            self.renderer.render_markdown ( self.build_help_text () )

        # Print the active system prompt ( raw, unformatted ).

        elif self.command == constants.APPLICATION_COMMAND_SHOW_SYSTEM_PROMPT:
            self.renderer.render_plain_text ( self.model.system_prompt )

        # Save the chat log without exiting.

        elif self.command == constants.APPLICATION_COMMAND_SAVE:
            self.model.save_chat_log_to_file ()

        # Clear the conversation history, preserving the system prompt.

        elif self.command == constants.APPLICATION_COMMAND_RESET:
            self.model.reset_conversation_history ()

        # Reset command to no command.

        self.command = constants.APPLICATION_COMMAND_NONE

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Resolve the prefixed name of a command, for diagnostics.
    #
    # Function name:
    # - command_prompt_name
    #
    # Description:
    # - Returns the canonical prompt name ( with the command prefix ) for an application command constant, e.g. 3 -> "/help". Used in log
    #   messages so the numeric command code is accompanied by a readable name.
    #
    # Parameters:
    # - command : int : An application command constant.
    #
    # Return Values:
    # - str : The prefixed command name, or an empty string if the command is not in the registry.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def command_prompt_name ( self, command ):

        # Find the registry entry for this command and return its primary prompt with the command prefix.

        for command_entry in constants.COMMAND_REGISTRY:
            if command_entry [ 'command' ] == command:
                return constants.PROMPT_COMMAND_PREFIX + command_entry [ 'prompts' ] [ 0 ]

        return ''

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Build the help text from the command registry.
    #
    # Function name:
    # - build_help_text
    #
    # Description:
    # - Assembles a Markdown list of the available commands from `constants.COMMAND_REGISTRY`, so newly added commands appear automatically.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - str : A Markdown string listing each command, its aliases, and its description.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def build_help_text ( self ):

        # Assemble a Markdown list of the available commands, prefixing each command name with the command prefix ( PROMPT_COMMAND_PREFIX ).

        help_lines = [ '**Available commands:**', '' ]

        for command_entry in constants.COMMAND_REGISTRY:
            command_names = ', '.join ( f'`{constants.PROMPT_COMMAND_PREFIX}{command_name}`' for command_name in command_entry [ 'prompts' ] )
            help_lines.append ( f'- {command_names}: {command_entry [ "description" ]}' )

        # Return the assembled Markdown help text.

        return '\n'.join ( help_lines )

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Render the language model's response.
    #
    # Function name:
    # - render_language_model_response
    #
    # Description:
    # - This function renders the language model's response, handling both streaming and non-streaming outputs.
    #
    # Parameters:    
    # - model_response : iterator | str : Streaming yields response text deltas; non-streaming is the complete response text.
    #
    # Return Values:
    # - response_text : str : The text of the language model's response.
    #
    # Preconditions:
    # - The application and model classes must be initialized.
    # - The model_response must be a valid response object.
    #
    # Postconditions:
    # - The language model's response is rendered and the response text is returned.
    #
    # To-Do:
    # 1. Improve handling of different response formats.
    # 2. Add error handling for rendering issues.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_language_model_response ( self, model_response ):

        # Compile the agent terminal prompt to label the response.

        terminal_prompt_ai = f'[{self.agent_name_ai}]'

        # Delegate rendering to the renderer. It handles streaming vs. complete responses and returns the complete response text for history.

        if self.model.streaming_enabled:
            return self.renderer.render_streaming_response ( model_response, terminal_prompt_ai )
        else:
            return self.renderer.render_complete_response ( model_response, terminal_prompt_ai )

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Display application and model information.
    #
    # Function name:
    # - print_application_info
    #
    # Description:
    # - This function prints the application's and model's information to the console.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #
    # Preconditions:
    # - The application and model classes must be initialized.
    #
    # Postconditions:
    # - The application's and model's information is printed to the console.
    #
    # To-Do:
    # - None.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def print_application_info ( self ):

        # Print application and model information to the console. 
        
        self.renderer.render_banner_header ( 'Application:' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Name:    ', f'{self.name}' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Version: ', f'{self.version}' )

        self.renderer.render_banner_header ( 'Model:' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Provider:          ', f'{self.model.provider_name}' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Name:              ', f'{self.model.name}' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Max Tokens:        ', f'{self.model.max_tokens}' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Temperature:       ', f'{self.model.temperature}' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}Streaming Enabled: ', f'{self.model.streaming_enabled}' )
        self.renderer.render_banner_field ( f'{constants.TERMINAL_BULLET}System Prompt:     ', f'{self.model.system_prompt_source}' )

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Function tagline. Short one-sentence or phrase description of function. e .g. Execute this or that. 
    #
    # Function name:
    # - function_name
    #
    # Description:
    # - bla bla bla.
    # - bla bla bla.
    #
    # Parameters:
    # - parameter_x : Description of value_x.
    # - parameter_y : Description of value_y.
    # - parameter_z : Description of value_z.
    #
    # Return Values:
    # - Description of return value. Or `none` if there is no return value. 
    #
    # Preconditions:
    # - Description of precondition 1
    # - Description of precondition 2
    # - Description of precondition 3
    #
    # Postconditions:
    # - Description of postcondition 1.
    # - Description of postcondition 2.
    # - Description of postcondition 3.
    #
    # To-Do:
    # 1. Improvement or enhancement 1.
    # 2. Improvement or enhancement 2.
    # 3. Improvement or enhancement 3.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
