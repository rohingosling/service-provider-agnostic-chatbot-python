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
# - Chat backend access is provided through the `providers` package ( providers/base.py, providers/openai_provider.py ).
#   This module is provider-agnostic and does not import any vendor SDK directly.
#
# Usage Notes:
#
# - The active provider is resolved by name through the provider registry ( providers/registry.py ).
#   - The default provider is OpenAI, which reads its API key from the `OPENAI_API_KEY` environment variable.
#   - You will need to set `OPENAI_API_KEY` to hold your OpenAI API key.
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
import logging

import constants
from providers import create_provider, ModelParameters, TokenUsage
from utility   import load_text_to_string

logger = logging.getLogger ( __name__ )

class LanguageModel:

    # Constants: System Prompt.
    # - The default system prompt, used when the configured system-prompt file is missing or empty.

    MODEL_SYSTEM_PROMPT_DEFAULT = 'You are a general purpose AI assistant. You always provide well-reasoned answers that are both correct and helpful.'

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Constructor.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__ ( self, model, provider, prompts, chat_log ):

        # Compose the provider and model parameters from configuration.

        self.provider             = create_provider ( provider.name )
        self.provider_name        = provider.name
        self.name                 = model.name
        self.max_tokens           = model.max_tokens
        self.temperature          = model.temperature
        self.streaming_enabled    = model.streaming
        self.conversation_history = []
        self.session_token_usage  = TokenUsage ( 0, 0, 0 )

        # Initialise chat-log settings from configuration.

        self.chat_log_folder         = chat_log.directory
        self.chat_log_file_name      = chat_log.file_prefix
        self.chat_log_file_extension = chat_log.file_extension
        self.include_system_prompt   = chat_log.include_system_prompt

        # Add the system prompt to the conversation history.
        # - Load it from the configured file; if the file is missing or empty, fall back to the built-in default.

        model_system_prompt = load_text_to_string ( prompts.system_prompt )

        if not model_system_prompt:
            model_system_prompt       = self.MODEL_SYSTEM_PROMPT_DEFAULT
            self.system_prompt_source = 'default'
        else:
            self.system_prompt_source = prompts.system_prompt

        self.system_prompt = model_system_prompt

        self.add_message_to_conversation_history ( model_system_prompt, constants.MODEL_MESSAGE_ROLE_SYSTEM )

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Add a message to the conversation history.
    #
    # Function name:
    # - add_message_to_conversation_history
    #
    # Description:
    # - This function appends a message to the model's conversation history.
    #
    # Parameters:    
    # - message      : str : The message to be added to the conversation history.
    # - message_role : str : The role of the message sender (e.g., user, assistant, system).
    #
    # Return Values:
    # - None.
    #
    # Preconditions:    
    # - The message must be a string.
    # - The message_role must be a valid role string.
    #
    # Postconditions:
    # - The message is appended to the conversation history.
    #
    # To-Do:
    # 1. Validate message and message_role before appending.
    # 2. Add error handling for invalid inputs.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def add_message_to_conversation_history ( self, message, message_role ):

        self.conversation_history.append ( { 'role': message_role, 'content': message } )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Remove the most recent message from the conversation history.
    #
    # Function name:
    # - remove_last_message_from_conversation_history
    #
    # Description:
    # - Removes the last message from the conversation history, if any. Used to discard a transient message ( e.g. a one-off introduction
    #   seed prompt ) that must not be recorded.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def remove_last_message_from_conversation_history ( self ):

        if self.conversation_history:
            self.conversation_history.pop ()

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Reset the conversation history, preserving the system prompt.
    #
    # Function name:
    # - reset_conversation_history
    #
    # Description:
    # - Clears all user and assistant turns, re-seeding the history with the original system prompt so the next turn starts fresh.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - None.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def reset_conversation_history ( self ):

        # Clear all turns, preserving the seeded system prompt.

        self.conversation_history = [ { 'role': constants.MODEL_MESSAGE_ROLE_SYSTEM, 'content': self.system_prompt } ]

        print ( f'\n{constants.TERMINAL_SYSTEM}\nConversation history cleared.' )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Fold the latest response usage into the running session total.
    #
    # Function name:
    # - update_token_usage
    #
    # Description:
    # - Reads the per-response usage captured by the provider, adds it to the running session total, and returns it ( or None when the
    #   backend did not report usage ).
    #
    # Return Values:
    # - TokenUsage or None : The usage for the most recent response.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def update_token_usage ( self ):

        # Fold the latest per-response usage ( captured by the provider ) into the running session total, and return it.

        response_token_usage = self.provider.last_token_usage

        if response_token_usage is not None:
            self.session_token_usage = self.session_token_usage + response_token_usage

        return response_token_usage

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Query the language model with the conversation history.
    #
    # Function name:
    # - query_language_model
    #
    # Description:
    # - This function queries the language model using the provided conversation history.
    # - It handles both streaming and non-streaming responses.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - response : iterator | str : An iterator of response text deltas when streaming, or the complete response text when not.
    #
    # Preconditions:
    # - The model class must be initialized.
    # - The conversation history must be set.
    #
    # Postconditions:
    # - The language model is queried and the response ( an iterator of text deltas, or the complete text ) is returned.
    #
    # To-Do:
    # 1. Add more detailed error handling for the API call.
    # 2. Log the query and response for debugging.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def query_language_model ( self ):

        # Compile the per-request model parameters.

        parameters = ModelParameters (
            name        = self.name,
            max_tokens  = self.max_tokens,
            temperature = self.temperature
        )

        logger.info ( 'Provider request: provider=%s, model=%s, streaming=%s, messages=%d.', self.provider_name, self.name, self.streaming_enabled, len ( self.conversation_history ) )

        # Delegate to the active provider.
        # - Streaming mode returns an iterator of response text deltas.
        # - Non-streaming mode returns the complete response text as a string.
        # - Backend / SDK failures surface as a normalized `ProviderError`, which the application reports without terminating the loop.

        if self.streaming_enabled:
            return self.provider.stream_chat ( self.conversation_history, parameters )
        else:
            return self.provider.complete_chat ( self.conversation_history, parameters )

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Save the chat log to a file.
    #
    # Function name:
    # - save_chat_log_to_file
    #
    # Description:
    # - This function saves the conversation history to a log file.
    # - It ensures the log folder exists, determines the next available file name, and writes the conversation history to the file.
    #
    # Parameters:
    # - application                   : dict : Dictionary containing the application's state.
    # - model                         : dict : Dictionary containing the model configuration settings.
    # - include_system_prompt_enabled : bool : Boolean flag to control whether we will include the system prompt or not.
    #                                   Default value is False, i.e. Do not include system prompt. 
    #
    # Return Values:
    # - None.
    #
    # Preconditions:
    # - The application and model dictionaries must be initialized.
    # - The conversation history must be set.
    #
    # Postconditions:
    # - The conversation history is saved to a log file.
    #
    # To-Do:
    # 1. Add error handling for file operations.
    #
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    def save_chat_log_to_file ( self, include_system_prompt_enabled = None ):

        # Default to the configured chat-log setting when the caller does not specify.

        if include_system_prompt_enabled is None:
            include_system_prompt_enabled = self.include_system_prompt

        # Ensure the folder exists; if not, create it.

        if not os.path.exists ( self.chat_log_folder ):
            os.makedirs ( self.chat_log_folder )

        # Determine the next file number to use.

        file_index = 0

        while os.path.exists (
            os.path.join ( self.chat_log_folder, f'{self.chat_log_file_name}{file_index}{self.chat_log_file_extension}' )
        ):
            file_index += 1

        # Create the filename with the next index.

        file_name = os.path.join (
            self.chat_log_folder,
            f'{self.chat_log_file_name}{file_index}{self.chat_log_file_extension}'
        )

        # Write the conversation history to the file.

        with open ( file_name, 'w', encoding = 'utf-8' ) as file:

            # Write chat log header information.

            file.write ( f'\nModel:\n' )
            file.write ( f'{constants.TERMINAL_BULLET}Provider:          {self.provider_name}\n' )
            file.write ( f'{constants.TERMINAL_BULLET}Name:              {self.name}\n' )
            file.write ( f'{constants.TERMINAL_BULLET}Max Tokens:        {self.max_tokens}\n' )
            file.write ( f'{constants.TERMINAL_BULLET}Temperature:       {self.temperature}\n' )
            file.write ( f'{constants.TERMINAL_BULLET}Streaming Enabled: {self.streaming_enabled}\n' )
            file.write ( '\n' )

            # Write chat log history to file. 

            row_index = 0

            for row in self.conversation_history:
                if row_index > 0:
                    file.write ( f'[{row [ "role" ]}]\n{row [ "content" ]}\n\n' )
                elif row_index == 0 and include_system_prompt_enabled:
                    file.write ( f'[{row [ "role" ]}]\n{row [ "content" ]}\n\n' )

                row_index += 1

        logger.info ( 'Saved chat log to %s.', file_name )

        print ( f'\n{constants.TERMINAL_SYSTEM}\nConversation history saved to "{file_name}."' )

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
