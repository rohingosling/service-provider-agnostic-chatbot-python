#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       providers/openai_provider.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Concrete ChatProvider backed by the OpenAI Python SDK. This is the only module in the project that imports the `openai` package; all
#   OpenAI-specific access is confined here, behind the normalized ChatProvider interface.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os

from openai import OpenAI
from .base  import ChatProvider, ProviderError, TokenUsage

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# OpenAI chat provider.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

class OpenAIProvider ( ChatProvider ):

    # Constants: Credentials.

    CREDENTIAL_ENVIRONMENT_VARIABLE = 'OPENAI_API_KEY'

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Constructor.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__ ( self ):

        # Read the API key from the environment, failing with a clear, actionable error if it is not set.

        api_key = os.environ.get ( self.CREDENTIAL_ENVIRONMENT_VARIABLE )

        if not api_key:
            raise ProviderError ( f"Environment variable '{self.CREDENTIAL_ENVIRONMENT_VARIABLE}' is not set. Set it to your OpenAI API key and try again." )

        # Construct the OpenAI client.

        self.client = OpenAI ( api_key = api_key )

        # No token usage captured yet.

        self.last_token_usage = None

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Name of the environment variable holding this backend's API key.
    #
    # Function name:
    # - credential_environment_variable
    #
    # Return Values:
    # - str : The environment variable name.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    @property
    def credential_environment_variable ( self ):

        return self.CREDENTIAL_ENVIRONMENT_VARIABLE

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Stream a chat completion as text deltas.
    #
    # Function name:
    # - stream_chat
    #
    # Description:
    # - Open a streaming chat completion and yield response text deltas as they arrive. Any SDK failure is wrapped as a ProviderError.
    #
    # Parameters:
    # - messages   : list            : The normalized conversation history; a list of { role, content } dictionaries.
    # - parameters : ModelParameters : The per-request model parameters ( name, max_tokens, temperature ).
    #
    # Return Values:
    # - Iterator of str : Response text deltas, yielded in order.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def stream_chat ( self, messages, parameters ):

        try:

            # Reset usage and open a streaming chat completion ( requesting usage on the final chunk ).

            self.last_token_usage = None

            response_stream = self.client.chat.completions.create (
                model          = parameters.name,
                messages       = messages,
                max_tokens     = parameters.max_tokens,
                temperature    = parameters.temperature,
                stream         = True,
                stream_options = { 'include_usage': True }
            )

            # Yield each non-empty text delta as it arrives, and capture the token usage reported on the final ( choice-less ) chunk.

            for chunk in response_stream:
                if chunk.choices:
                    response_delta = chunk.choices [ 0 ].delta.content
                    if response_delta:
                        yield response_delta
                if chunk.usage is not None:
                    self.last_token_usage = TokenUsage ( chunk.usage.prompt_tokens, chunk.usage.completion_tokens, chunk.usage.total_tokens )

        except Exception as exception:

            raise ProviderError ( str ( exception ) ) from exception

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Return a complete chat completion.
    #
    # Function name:
    # - complete_chat
    #
    # Description:
    # - Request a complete chat completion and return the full response text. Any SDK failure is wrapped as a ProviderError.
    #
    # Parameters:
    # - messages   : list            : The normalized conversation history; a list of { role, content } dictionaries.
    # - parameters : ModelParameters : The per-request model parameters ( name, max_tokens, temperature ).
    #
    # Return Values:
    # - str : The complete response text.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def complete_chat ( self, messages, parameters ):

        try:

            # Reset usage and request a complete chat completion.

            self.last_token_usage = None

            response = self.client.chat.completions.create (
                model       = parameters.name,
                messages    = messages,
                max_tokens  = parameters.max_tokens,
                temperature = parameters.temperature,
                stream      = False
            )

            # Capture the reported token usage, then return the complete response text.

            if response.usage is not None:
                self.last_token_usage = TokenUsage ( response.usage.prompt_tokens, response.usage.completion_tokens, response.usage.total_tokens )

            return response.choices [ 0 ].message.content

        except Exception as exception:

            raise ProviderError ( str ( exception ) ) from exception
