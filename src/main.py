import logging

from application import Application
from config      import load_configuration
from providers   import ProviderError
from renderer    import Renderer

logger = logging.getLogger ( __name__ )

def main ():

    # Load configuration, then build and run the application. A startup configuration error ( e.g. a missing API key ) is reported as a
    # concise message rather than a raw traceback.

    configuration = load_configuration ()

    try:
        application = Application ( configuration )
        application.run ()

    except ProviderError as startup_error:
        logger.error ( 'Startup error: %s', startup_error )
        Renderer ( rich_enabled = configuration.rendering.rich_enabled ).render_error ( startup_error, recoverable = True )

if __name__ == "__main__":
    main ()
