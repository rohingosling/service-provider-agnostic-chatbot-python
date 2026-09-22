#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       providers/base.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Provider abstraction contract. Defines the normalized interface every chat backend must implement, so that no upstream module observes
#   vendor-specific objects. The interface speaks only in normalized types: message dictionaries in, plain `str` text out.
#
# Contents:
#
# - ModelParameters : Dataclass carrying the per-request model parameters ( name, max_tokens, temperature ).
# - ProviderError   : Normalized exception raised by providers; upstream layers catch it without knowing the backend.
# - ChatProvider    : Abstract base class defining stream_chat, complete_chat, and credential_environment_variable.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

from abc         import ABC, abstractmethod
from dataclasses import dataclass

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Per-request model parameters passed to a provider on each request.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

@dataclass
class ModelParameters:

    name:        str
    max_tokens:  int
    temperature: float

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Normalized token usage reported by a provider for one response.
#
# - prompt_tokens / completion_tokens / total_tokens. Each provider maps its own backend's usage into this shape, so upstream code never
#   sees vendor-specific usage objects. Adding two TokenUsage values accumulates a running total.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

@dataclass
class TokenUsage:

    prompt_tokens:     int
    completion_tokens: int
    total_tokens:      int

    def __add__ ( self, other ):

        return TokenUsage (
            prompt_tokens     = self.prompt_tokens + other.prompt_tokens,
            completion_tokens = self.completion_tokens + other.completion_tokens,
            total_tokens      = self.total_tokens + other.total_tokens,
        )

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Normalized provider exception.
#
# - Providers wrap any backend / SDK failure as a `ProviderError`, so upstream layers can handle failures uniformly without importing or
#   catching vendor-specific exception types.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

class ProviderError ( Exception ):
    pass

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Chat provider interface.
#
# - The abstract contract every concrete backend must implement. All members speak in normalized types only.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

class ChatProvider ( ABC ):

    # After stream_chat is fully consumed, or complete_chat returns, this holds the normalized TokenUsage for the latest response ( or None
    # if the backend did not report usage ). Concrete providers populate it.

    last_token_usage = None

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Stream a chat completion as text deltas.
    #
    # Function name:
    # - stream_chat
    #
    # Description:
    # - Send the conversation history to the backend and yield response text deltas ( str ) in order as they arrive.
    #
    # Parameters:
    # - messages   : list            : The normalized conversation history; a list of { role, content } dictionaries.
    # - parameters : ModelParameters : The per-request model parameters ( name, max_tokens, temperature ).
    #
    # Return Values:
    # - Iterator of str : Response text deltas, yielded in order.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    @abstractmethod
    def stream_chat ( self, messages, parameters ):

        ...

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Return a complete chat completion.
    #
    # Function name:
    # - complete_chat
    #
    # Description:
    # - Send the conversation history to the backend and return the complete response text ( str ) in one call.
    #
    # Parameters:
    # - messages   : list            : The normalized conversation history; a list of { role, content } dictionaries.
    # - parameters : ModelParameters : The per-request model parameters ( name, max_tokens, temperature ).
    #
    # Return Values:
    # - str : The complete response text.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    @abstractmethod
    def complete_chat ( self, messages, parameters ):

        ...

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Name of the environment variable holding this backend's API key.
    #
    # Function name:
    # - credential_environment_variable
    #
    # Description:
    # - Return the name of the environment variable from which this backend reads its API key.
    #
    # Parameters:
    # - None
    #
    # Return Values:
    # - str : The environment variable name ( e.g. 'OPENAI_API_KEY' ).
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    @property
    @abstractmethod
    def credential_environment_variable ( self ):

        ...
