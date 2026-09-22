
#-------------------------------------------------------------------------------------------------------------------------------------------------------------
# Load the contents of a text file into a string.
#
# Function name:
# - load_text_to_string
#
# Description:
# - This function loads the contents of a text file into a string.
# - Example:
# 
#   text_string = load_text_to_string ( 'text_file.txt' )
#
# Parameters:
# - file_name : string : File name of the text file whose text content we wish to load into a string. 
#
# Return Values:
# - text_string : string : A string populated with the text loaded from a text file. 
#
# Preconditions:
# - The text file exists. If the text file is empty, the loaded string will just be an empty string. 
#
# Postconditions:
# - The content of the file referenced by `file_name` is returned as a string to the caller.
#
# To-Do:
# 1. Add error handling for file operations.
#
#-------------------------------------------------------------------------------------------------------------------------------------------------------------

def load_text_to_string ( file_name ):
    
    try:
        with open ( file_name, 'r', encoding = 'utf-8' ) as file:
            return file.read ()
        
    except FileNotFoundError:
        print ( f"\nError: The file {file_name} was not found." )

    except IOError:
        print (f"\nError: An IOError occurred while reading the file {file_name}." )