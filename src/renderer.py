#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Application   Conversation Agent Reference Application
# Module:       renderer.py
# Version:      2.1
# Author:       Rohin Gosling
#
# Description:
#
# - Terminal presentation layer. Wraps a `rich` Console to render model responses as formatted Markdown ( headings, lists, emphasis, code
#   blocks ) and to render errors as readable tracebacks. Consumes only plain `str` text, so it is independent of which provider produced it.
# - Honours a `rich_enabled` flag: when disabled ( dumb terminal, piping to a file, or tests ), it falls back to plain `print()` with identical
#   textual content and no `rich` formatting.
#
#---------------------------------------------------------------------------------------------------------------------------------------------------------

import traceback
import types

from rich.color    import Color, ColorParseError
from rich.console  import Console
from rich.live     import Live
from rich.markdown import Markdown
from rich.styled   import Styled
from rich.text     import Text

import constants

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Module helpers.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

def default_color_scheme ():

    # The built-in colour scheme, mirroring the defaults in constants. Used when a Renderer is constructed without an explicit scheme ( e.g.
    # standalone or in tests ). Returns a simple attribute namespace, compatible with the ColorsConfig the application normally injects.

    return types.SimpleNamespace (
        general     = constants.TERMINAL_COLOR_GENERAL,
        header      = constants.TERMINAL_COLOR_HEADER,
        field_value = constants.TERMINAL_COLOR_FIELD_VALUE,
        ai_prompt   = constants.TERMINAL_COLOR_AI_PROMPT,
        ai_text     = constants.TERMINAL_COLOR_AI_TEXT,
        user_prompt = constants.TERMINAL_COLOR_USER_PROMPT,
        user_text   = constants.TERMINAL_COLOR_USER_TEXT,
    )

def ansi_foreground_sequence ( color_name ):

    # Build the raw ANSI SGR sequence that sets the terminal foreground to the given `rich` colour, used to colour the text the user types at
    # input() ( which `rich` cannot style ). Returns an empty string if the colour cannot be parsed, so a bad value just leaves input uncoloured.

    try:
        ansi_codes = Color.parse ( color_name ).get_ansi_codes ()
        return '\x1b[' + ';'.join ( ansi_codes ) + 'm'
    except ColorParseError:
        return ''

#---------------------------------------------------------------------------------------------------------------------------------------------------------
# Terminal renderer.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

class Renderer:

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Constructor.
    #
    # Function name:
    # - __init__
    #
    # Parameters:
    # - rich_enabled : bool         : When True, render with `rich`; when False, fall back to plain text with identical content.
    # - colors       : ColorsConfig : The colour scheme ( from config ); when None, the built-in default scheme ( from constants ) is used.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__ ( self, rich_enabled = True, colors = None ):

        # Initialise the renderer and its console, falling back to the built-in colour scheme when one was not supplied.

        self.rich_enabled = rich_enabled
        self.colors       = colors if colors is not None else default_color_scheme ()
        self.console      = Console ( style = self.colors.general )

        # Pre-compute the raw ANSI sequence that colours the user input echo ( `rich` cannot colour input(), so the caller sets it directly ).

        self.ansi_user_text_color = ansi_foreground_sequence ( self.colors.user_text )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Emit the agent label that heads a response.
    #
    # Function name:
    # - emit_response_header
    #
    # Parameters:
    # - header : str : The agent label ( e.g. '[AI]' ), or None to emit nothing.
    # - style  : str : Optional `rich` style name applied to the label ( e.g. the AI prompt colour ), or None for the console default.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def emit_response_header ( self, header, style = None ):

        # Print the response header. The label is plain text, never interpreted as Markdown or `rich` markup.

        if header is None:
            return

        if self.rich_enabled:
            self.console.print ( Text ( f'\n{header}', style = style ) )
        else:
            print ( f'\n{header}' )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Emit a white section header for the information banner.
    #
    # Function name:
    # - render_banner_header
    #
    # Parameters:
    # - text : str : The header text ( e.g. 'Application:' ). Printed on its own line, preceded by a blank line.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_banner_header ( self, text ):

        # Print the banner section header in the header ( white ) style, preceded by a blank line.

        if self.rich_enabled:
            self.console.print ( Text ( f'\n{text}', style = self.colors.header ) )
        else:
            print ( f'\n{text}' )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Emit a "label value" field line for the information banner.
    #
    # Function name:
    # - render_banner_field
    #
    # Description:
    # - Print a banner field as a single line: the label ( bullet + name + alignment padding ) in the general ( light grey ) style, and the value
    #   in the field-value ( dark grey ) style. `rich` auto-highlighting is disabled so numeric and path values are not recoloured.
    #
    # Parameters:
    # - label : str : The leading label segment, including the bullet and any alignment padding.
    # - value : str : The field value segment.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_banner_field ( self, label, value ):

        # Print the label and value as one line, each in its own style. The plain-text fallback prints the same content with no colour.

        if self.rich_enabled:
            field_line = Text ()
            field_line.append ( label, style = self.colors.general )
            field_line.append ( value, style = self.colors.field_value )
            self.console.print ( field_line, highlight = False )
        else:
            print ( f'{label}{value}' )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Emit the user prompt label.
    #
    # Function name:
    # - render_user_prompt_label
    #
    # Description:
    # - Print the user prompt label ( e.g. '[User]' ) in the user-prompt ( light blue ) style, preceded by a blank line, leaving the cursor on the
    #   next line ready for input. Colouring the text the user then types is the caller's responsibility ( `rich` cannot colour input() echo ).
    #
    # Parameters:
    # - label : str : The user prompt label.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_user_prompt_label ( self, label ):

        # Print the user prompt label in the user-prompt ( light blue ) style, preceded by a blank line.

        if self.rich_enabled:
            self.console.print ( Text ( f'\n{label}', style = self.colors.user_prompt ) )
        else:
            print ( f'\n{label}' )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Render a streaming response, then re-render it as Markdown.
    #
    # Function name:
    # - render_streaming_response
    #
    # Description:
    # - Consume the provider's text deltas, displaying them live as they arrive, then re-render the completed text as formatted Markdown.
    # - The complete response text is accumulated and returned so the caller can store it in the conversation history.
    #
    # Parameters:
    # - response_deltas : iterator : An iterator of response text deltas ( str ).
    # - header          : str      : The agent label to print above the response, or None.
    #
    # Return Values:
    # - str : The complete, accumulated response text.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_streaming_response ( self, response_deltas, header = None ):

        # Print the response header.

        self.emit_response_header ( header, self.colors.ai_prompt )

        # Stream the response, accumulating the complete text.

        accumulated_text = ''

        if self.rich_enabled:

            # Show the text live as it arrives, then replace the final frame with rendered Markdown.

            with Live ( console = self.console, auto_refresh = True, refresh_per_second = 10, vertical_overflow = 'visible' ) as live:
                for response_delta in response_deltas:
                    accumulated_text += response_delta
                    live.update ( Text ( accumulated_text, style = self.colors.ai_text ) )
                live.update ( Styled ( Markdown ( accumulated_text ), self.colors.ai_text ) )

        else:

            # Plain fallback: print each delta as it arrives.

            for response_delta in response_deltas:
                print ( response_delta, end = '', flush = True )
                accumulated_text += response_delta
            print ()

        # Return the complete response text to the caller.

        return accumulated_text

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Render a complete ( non-streaming ) response as Markdown.
    #
    # Function name:
    # - render_complete_response
    #
    # Description:
    # - Render an already-complete response string as formatted Markdown, and return it so the caller can store it in history.
    #
    # Parameters:
    # - response_text : str : The complete response text.
    # - header        : str : The agent label to print above the response, or None.
    #
    # Return Values:
    # - str : The response text, unchanged.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_complete_response ( self, response_text, header = None ):

        # Print the response header.

        self.emit_response_header ( header, self.colors.ai_prompt )

        # Render the response as Markdown, or as plain text in the fallback path.

        if self.rich_enabled:
            self.console.print ( Styled ( Markdown ( response_text ), self.colors.ai_text ) )
        else:
            print ( response_text )

        # Return the response text to the caller.

        return response_text

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Render a standalone Markdown string.
    #
    # Function name:
    # - render_markdown
    #
    # Description:
    # - Render an arbitrary Markdown string ( e.g. a canned introduction ). No header, no return value.
    #
    # Parameters:
    # - text : str : The Markdown text to render.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_markdown ( self, text ):

        # Render the text as Markdown, or as plain text in the fallback path.

        if self.rich_enabled:
            self.console.print ( Markdown ( text ) )
        else:
            print ( text )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Render literal text without Markdown formatting.
    #
    # Function name:
    # - render_plain_text
    #
    # Description:
    # - Print text verbatim, with no Markdown interpretation ( used to show the raw system prompt ). Even with `rich` enabled, the text is
    #   not parsed as markup or Markdown.
    #
    # Parameters:
    # - text : str : The literal text to print.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_plain_text ( self, text ):

        if self.rich_enabled:
            self.console.print ( text, markup = False, highlight = False )
        else:
            print ( text )

    #---------------------------------------------------------------------------------------------------------------------------------------------------------
    # Render an error.
    #
    # Function name:
    # - render_error
    #
    # Description:
    # - For a recoverable error ( e.g. a provider failure mid-conversation ), print a concise one-line message.
    # - For an unexpected error ( a crash ), print a readable `rich` traceback. Local variables are never shown, so secrets are not leaked.
    #
    # Parameters:
    # - exception   : Exception : The exception to report.
    # - recoverable : bool      : True for a concise message; False for a full traceback.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------

    def render_error ( self, exception, recoverable = True ):

        # Recoverable error: a concise, actionable one-line message.

        if recoverable:

            message = f'\n{constants.TERMINAL_ERROR} {exception}\n'

            if self.rich_enabled:
                self.console.print ( Text ( message, style = 'red' ) )
            else:
                print ( message )

        # Unexpected error: a readable traceback, without local variables ( no secret leakage ).

        else:

            if self.rich_enabled:
                self.console.print_exception ( show_locals = False )
            else:
                traceback.print_exc ()
