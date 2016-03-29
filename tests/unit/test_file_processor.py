"""Tests for the FileProcessor class."""
import ast
import optparse

from flake8 import processor

import mock
import pytest


def options_from(**kwargs):
    """Generate a Values instances with our kwargs."""
    kwargs.setdefault('hang_closing', True)
    kwargs.setdefault('max_line_length', 79)
    kwargs.setdefault('verbose', False)
    return optparse.Values(kwargs)


def test_read_lines_splits_lines():
    """Verify that read_lines splits the lines of the file."""
    file_processor = processor.FileProcessor(__file__, options_from())
    lines = file_processor.lines
    assert len(lines) > 5
    assert '"""Tests for the FileProcessor class."""\n' in lines


@pytest.mark.parametrize('first_line', [
    '\xEF\xBB\xBF"""Module docstring."""\n',
    u'\uFEFF"""Module docstring."""\n',
])
def test_strip_utf_bom(first_line):
    r"""Verify that we strip '\xEF\xBB\xBF' from the first line."""
    lines = [first_line]
    file_processor = processor.FileProcessor('-', options_from(), lines[:])
    assert file_processor.lines != lines
    assert file_processor.lines[0] == '"""Module docstring."""\n'


@pytest.mark.parametrize('lines, expected', [
    (['\xEF\xBB\xBF"""Module docstring."""\n'], False),
    ([u'\uFEFF"""Module docstring."""\n'], False),
    (['#!/usr/bin/python', '# flake8 is great', 'a = 1'], False),
    (['#!/usr/bin/python', '# flake8: noqa', 'a = 1'], True),
    (['# flake8: noqa', '#!/usr/bin/python', 'a = 1'], True),
    (['#!/usr/bin/python', 'a = 1', '# flake8: noqa'], True),
])
def test_should_ignore_file(lines, expected):
    """Verify that we ignore a file if told to."""
    file_processor = processor.FileProcessor('-', options_from(), lines)
    assert file_processor.should_ignore_file() is expected


@mock.patch('flake8.utils.stdin_get_value')
def test_read_lines_from_stdin(stdin_get_value):
    """Verify that we use our own utility function to retrieve stdin."""
    stdin_value = mock.Mock()
    stdin_value.splitlines.return_value = []
    stdin_get_value.return_value = stdin_value
    file_processor = processor.FileProcessor('-', options_from())
    stdin_get_value.assert_called_once_with()
    stdin_value.splitlines.assert_called_once_with(True)


@mock.patch('flake8.utils.stdin_get_value')
def test_read_lines_sets_filename_attribute(stdin_get_value):
    """Verify that we update the filename attribute."""
    stdin_value = mock.Mock()
    stdin_value.splitlines.return_value = []
    stdin_get_value.return_value = stdin_value
    file_processor = processor.FileProcessor('-', options_from())
    assert file_processor.filename == 'stdin'


def test_line_for():
    """Verify we grab the correct line from the cached lines."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'Line 1',
        'Line 2',
        'Line 3',
    ])

    for i in range(1, 4):
        assert file_processor.line_for(i) == 'Line {0}'.format(i)


def test_next_line():
    """Verify we update the file_processor state for each new line."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'Line 1',
        'Line 2',
        'Line 3',
    ])

    for i in range(1, 4):
        assert file_processor.next_line() == 'Line {}'.format(i)
        assert file_processor.line_number == i


@pytest.mark.parametrize('error_code, line, expected_indent_char', [
    ('E101', '\t\ta = 1', '\t'),
    ('E101', '    a = 1', ' '),
    ('W101', 'frobulate()', None),
    ('F821', 'class FizBuz:', None),
])
def test_check_physical_error(error_code, line, expected_indent_char):
    """Verify we update the indet char for the appropriate error code."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'Line 1',
    ])

    file_processor.check_physical_error(error_code, line)
    assert file_processor.indent_char == expected_indent_char


@pytest.mark.parametrize('params, args, expected_kwargs', [
    (['blank_before', 'blank_lines'], None, {'blank_before': 0,
                                             'blank_lines': 0}),
    (['noqa', 'fake'], {'fake': 'foo'}, {'noqa': False, 'fake': 'foo'}),
    (['blank_before', 'blank_lines', 'noqa'],
        {'blank_before': 10, 'blank_lines': 5, 'noqa': True},
        {'blank_before': 10, 'blank_lines': 5, 'noqa': True}),
    ([], {'fake': 'foo'}, {'fake': 'foo'}),
])
def test_keyword_arguments_for(params, args, expected_kwargs):
    """Verify the keyword args are generated properly."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'Line 1',
    ])
    kwargs_for = file_processor.keyword_arguments_for

    assert kwargs_for(params, args) == expected_kwargs


def test_keyword_arguments_for_does_not_handle_attribute_errors():
    """Verify we re-raise AttributeErrors."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'Line 1',
    ])

    with pytest.raises(AttributeError):
        file_processor.keyword_arguments_for(['fake'])


@pytest.mark.parametrize('unsplit_line, expected_lines', [
    ('line', []),
    ('line 1\n', ['line 1']),
    ('line 1\nline 2\n', ['line 1', 'line 2']),
    ('line 1\n\nline 2\n', ['line 1', '', 'line 2']),
])
def test_split_line(unsplit_line, expected_lines):
    """Verify the token line spliting."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'Line 1',
    ])

    actual_lines = list(file_processor.split_line((1, unsplit_line)))
    assert expected_lines == actual_lines

    assert len(actual_lines) == file_processor.line_number


def test_build_ast():
    """Verify the logic for how we build an AST for plugins."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'a = 1\n'
    ])

    module = file_processor.build_ast()
    assert isinstance(module, ast.Module)


def test_next_logical_line_updates_the_previous_logical_line():
    """Verify that we update our tracking of the previous logical line."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'a = 1\n'
    ])

    file_processor.indent_level = 1
    file_processor.logical_line = 'a = 1'
    assert file_processor.previous_logical == ''
    assert file_processor.previous_indent_level is 0

    file_processor.next_logical_line()
    assert file_processor.previous_logical == 'a = 1'
    assert file_processor.previous_indent_level == 1


def test_visited_new_blank_line():
    """Verify we update the number of blank lines seen."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'a = 1\n'
    ])

    assert file_processor.blank_lines == 0
    file_processor.visited_new_blank_line()
    assert file_processor.blank_lines == 1


def test_inside_multiline():
    """Verify we update the line number and reset multiline."""
    file_processor = processor.FileProcessor('-', options_from(), lines=[
        'a = 1\n'
    ])

    assert file_processor.multiline is False
    assert file_processor.line_number == 0
    with file_processor.inside_multiline(10):
        assert file_processor.multiline is True
        assert file_processor.line_number == 10

    assert file_processor.multiline is False
