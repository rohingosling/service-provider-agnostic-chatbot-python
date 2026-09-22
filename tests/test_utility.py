#---------------------------------------------------------------------------------------------------------------------------------------------------------
# tests/test_utility.py -- the text-file loader.
#---------------------------------------------------------------------------------------------------------------------------------------------------------

from utility import load_text_to_string


def test_loads_existing_file ( tmp_path ):

    file_path = tmp_path / 'sample.txt'
    file_path.write_text ( 'hello world', encoding = 'utf-8' )

    assert load_text_to_string ( str ( file_path ) ) == 'hello world'


def test_missing_file_returns_none_and_reports ( tmp_path, capsys ):

    result = load_text_to_string ( str ( tmp_path / 'does_not_exist.txt' ) )

    assert result is None
    assert 'not found' in capsys.readouterr ().out.lower ()


def test_empty_file_returns_empty_string ( tmp_path ):

    file_path = tmp_path / 'empty.txt'
    file_path.write_text ( '', encoding = 'utf-8' )

    assert load_text_to_string ( str ( file_path ) ) == ''


def test_reads_utf8_content ( tmp_path ):

    file_path = tmp_path / 'utf8.txt'
    file_path.write_text ( 'café — naïve', encoding = 'utf-8' )

    assert load_text_to_string ( str ( file_path ) ) == 'café — naïve'
