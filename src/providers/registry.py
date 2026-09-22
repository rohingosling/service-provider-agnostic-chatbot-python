#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       providers/registry.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Provider registry and factory. Maps a provider name to its concrete ChatProvider class and constructs instances on demand.
# - Adding a backend is a single edit here ( register the name ); no upstream module changes.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import constants

from .base               import ProviderError
from .openai_provider    import OpenAIProvider
from .anthropic_provider import AnthropicProvider

# Constants: Provider Registry.
# - Maps each provider name to its concrete ChatProvider class.

PROVIDER_REGISTRY = {
    constants.PROVIDER_NAME_OPENAI:    OpenAIProvider,
    constants.PROVIDER_NAME_ANTHROPIC: AnthropicProvider,
}

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Create a provider instance by name.
#
# Function name:
# - create_provider
#
# Description:
# - Look up the concrete ChatProvider class registered under `name` and return a new instance of it.
#
# Parameters:
# - name : str : The registered provider name ( e.g. 'openai' ).
#
# Return Values:
# - ChatProvider : A new provider instance.
#
# Raises:
# - ProviderError : If `name` is not a registered provider.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def create_provider ( name ):

    # Look up the provider class by name.

    provider_class = PROVIDER_REGISTRY.get ( name )

    # Reject unknown provider names with a clear, actionable error.

    if provider_class is None:
        available_provider_names = ', '.join ( sorted ( PROVIDER_REGISTRY.keys () ) )
        raise ProviderError ( f"Unknown provider '{name}'. Available providers: {available_provider_names}." )

    # Construct and return the provider instance.

    return provider_class ()
