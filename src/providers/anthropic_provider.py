#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       providers/anthropic_provider.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Concrete ChatProvider backed by the Anthropic Python SDK. This is the only module in the project that imports the `anthropic` package; all
#   Anthropic-specific access is confined here, behind the normalized ChatProvider interface.
#
# - Two normalization concerns are handled here, both invisible to upstream code:
#   - System prompt : Anthropic carries the system prompt as a top-level `system` argument, not as a `role: system` message. System-role
#                     messages are lifted out of the history; the remaining user / assistant turns are sent as `messages`.
#   - Token usage   : Anthropic reports `input_tokens` / `output_tokens`; these are mapped onto the normalized TokenUsage ( prompt / completion / total ).
#
# - Temperature is intentionally not sent. The recommended Claude models ( Opus 4.8 / 4.7, Fable 5 ) reject `temperature` and instead use
#   adaptive thinking and an effort level. To target an older model that accepts temperature ( Sonnet 4.6, Haiku 4.5, Opus 4.6 ), add
#   `temperature = parameters.temperature` to each request below.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import os

from anthropic import Anthropic
from .base     import ChatProvider, ProviderError, TokenUsage

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Anthropic chat provider.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

class AnthropicProvider ( ChatProvider ):

    # Constants: Credentials.

    CREDENTIAL_ENVIRONMENT_VARIABLE = 'ANTHROPIC_API_KEY'

    # Constants: Message roles.
    # - The role identifying a system message in the normalized history. Anthropic carries the system prompt as a top-level argument, so
    #   messages with this role are lifted out of the history before the request is sent.

    MESSAGE_ROLE_SYSTEM = 'system'

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Constructor.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__ ( self ):

        # Read the API key from the environment, failing with a clear, actionable error if it is not set.

        api_key = os.environ.get ( self.CREDENTIAL_ENVIRONMENT_VARIABLE )

        if not api_key:
            raise ProviderError ( f"Environment variable '{self.CREDENTIAL_ENVIRONMENT_VARIABLE}' is not set. Set it to your Anthropic API key and try again." )

        # Construct the Anthropic client.

        self.client = Anthropic ( api_key = api_key )

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
    # Split the normalized history into a top-level system prompt and the user / assistant turns.
    #
    # Function name:
    # - split_conversation
    #
    # Description:
    # - Anthropic carries the system prompt as a top-level `system` argument rather than as a message. This helper lifts every system-role
    #   message out of the normalized history, joins their content into a single system string, and returns the remaining turns unchanged.
    #
    # Parameters:
    # - messages : list : The normalized conversation history; a list of { role, content } dictionaries.
    #
    # Return Values:
    # - ( str, list ) : The joined system prompt ( '' when none ), and the list of remaining user / assistant messages.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def split_conversation ( self, messages ):

        system_prompt_parts = [ message [ 'content' ] for message in messages if message [ 'role' ] == self.MESSAGE_ROLE_SYSTEM ]
        conversation_turns  = [ message               for message in messages if message [ 'role' ] != self.MESSAGE_ROLE_SYSTEM ]

        return '\n\n'.join ( system_prompt_parts ), conversation_turns

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Stream a chat completion as text deltas.
    #
    # Function name:
    # - stream_chat
    #
    # Description:
    # - Open a streaming response and yield response text deltas as they arrive. Any SDK failure is wrapped as a ProviderError.
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

            # Reset usage and split the system prompt out of the history.

            self.last_token_usage = None

            system_prompt, conversation_turns = self.split_conversation ( messages )

            # Open a streaming response and yield each text delta as it arrives.

            with self.client.messages.stream (
                model      = parameters.name,
                max_tokens = parameters.max_tokens,
                system     = system_prompt,
                messages   = conversation_turns
            ) as response_stream:

                for response_delta in response_stream.text_stream:
                    if response_delta:
                        yield response_delta

                # Capture the token usage reported on the final, fully-assembled message.

                usage = response_stream.get_final_message ().usage

                if usage is not None:
                    self.last_token_usage = TokenUsage ( usage.input_tokens, usage.output_tokens, usage.input_tokens + usage.output_tokens )

        except Exception as exception:

            raise ProviderError ( str ( exception ) ) from exception

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Return a complete chat completion.
    #
    # Function name:
    # - complete_chat
    #
    # Description:
    # - Request a complete response and return the full response text. Any SDK failure is wrapped as a ProviderError.
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

            # Reset usage and split the system prompt out of the history.

            self.last_token_usage = None

            system_prompt, conversation_turns = self.split_conversation ( messages )

            # Request a complete response.

            response = self.client.messages.create (
                model      = parameters.name,
                max_tokens = parameters.max_tokens,
                system     = system_prompt,
                messages   = conversation_turns
            )

            # Capture the reported token usage.

            if response.usage is not None:
                self.last_token_usage = TokenUsage ( response.usage.input_tokens, response.usage.output_tokens, response.usage.input_tokens + response.usage.output_tokens )

            # Concatenate the text blocks of the response into a single string.

            return ''.join ( block.text for block in response.content if block.type == 'text' )

        except Exception as exception:

            raise ProviderError ( str ( exception ) ) from exception
