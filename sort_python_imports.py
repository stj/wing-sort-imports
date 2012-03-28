################################################################################
# sort_python_imports.vim - sorts python imports alphabetically
# Author: Krzysiek Goj <bin-krzysiek#at#poczta.gazeta.pl>
# Version: 1.3
# Last Change: 2012-03-08
# URL: http://tbw13.blogspot.com
# Requires: Python and Vim compiled with +python option
# Licence: This script is released under the Vim License.
# Installation: Put into plugin directory
# Usage:
# Use :PyFixImports, command to fix imports in the beginning of
# currently edited file.
#
# You can also use visual mode to select range of lines and then
# use <C-i> to sort imports in those lines.
#
# Changelog:
#  1.3 - A future statement must appear near the top of the module
#        http://docs.python.org/reference/simple_stmts.html#future
#  1.2 - bugfix: from foo import (bar, baz)
#        Now requires only python 2.3 (patch from Konrad Delong)
#  1.1 - bugfix: from foo.bar import baz
#  1.0 - initial upload
#
################################################################################

import wingapi
import re
from sets import Set

__future_import_re = re.compile('(?P<indent>\s*)from\s+__future__\s+import\s(?P<items>[^#]*)(?P<comment>(#.*)?)')
__global_import_re = re.compile('(?P<indent>\s*)import\s(?P<items>[^#]*)(?P<comment>(#.*)?)')
__from_import_re = re.compile('(?P<indent>\s*)from\s+(?P<module>\S*)\s+import\s(?P<items>[^#]*)(?P<comment>(#.*)?)')
__boring_re = re.compile('\s*(#.*)?$')
__endl_re = re.compile('\n?$')

def _sorted(l, key=lambda x: x):
    l = map(lambda x: (key(x), x), list(l))
    l.sort()
    l = map(lambda pair: pair[1], l)
    return l


def _is_future_import(line):
    """checks if line is a 'from __future__ import ...'"""
    return __future_import_re.match(line) is not None


def _is_global_import(line):
    """checks if line is a 'import ...'"""
    return __global_import_re.match(line) is not None


def _is_from_import(line):
    """checks if line is a 'from ... import ...'"""
    return __from_import_re.match(line) is not None


def _is_boring(line):
    """checks if line is boring (empty or comment)"""
    return __boring_re.match(line) is not None


def _has_leading_ws(line):
    if not line: return False
    return line[0].isspace()


def _is_unindented_import(line):
    """checks if line is an unindented import"""
    return not _has_leading_ws(line) and (_is_global_import(line) or _is_from_import(line))


def _make_template(indent, comment):
    """makes template out of indentation and comment"""
    if comment:
        comment = ' ' + comment
    return indent + '%s' + comment


def _split_import(regex, line):
    """splits import line (using regex) intro triple: module (may be None), set_of_items, line_template"""
    imports = regex.match(line)
    if not imports:
        raise ValueError, 'this line isn\'t an import'
    indent, items, comment = map(lambda name: imports.groupdict()[name], 'indent items comment'.split())
    module = imports.groupdict().get('module')
    if items.startswith('(') and items.endswith(')'):
        items = items[1:-1]
    return module, Set(map(lambda item: item.strip(), items.split(','))), _make_template(indent, comment)


def _split_globals(line):
    """splits 'import ...' line intro pair: set_of_items, line_template"""
    return _split_import(__global_import_re, line)[1:] # ignore module


def _split_from(line):
    """splits 'from ... import ...' line intro triple: module_name, set_of_items, line_template"""
    return _split_import(__from_import_re, line)


def _get_lines(lines):
    """returns numbers -- [from, to) -- of first lines with unindented imports"""
    start, end = 0, 0
    start_found = False
    for num, line in enumerate(lines):
        if _is_unindented_import(line):
            if not start_found:
                start = num
                start_found = True
            end = num + 1
        elif end and not _is_boring(line):
            break
    return start, end


def _sort_and_join(items):
    """returns alphabetically (case insensitive) sorted and comma-joined collection"""
    return ', '.join(_sorted(items, key=lambda x: x.upper()))


def _make_global_import(items, template='%s'):
    return template % 'import %s' % _sort_and_join(items)


def _make_from_import(module, items, template='%s'):
    return template % 'from %s import %s' % (module, _sort_and_join(items))


def _repair_any(line):
    """repairs any import line (doesn't affect boring lines)"""
    suffix = __endl_re.search(line).group()
    if _is_global_import(line):
        return _make_global_import(*_split_globals(line)) + suffix
    elif _is_from_import(line):
        return _make_from_import(*_split_from(line)) + suffix
    elif _is_boring(line):
        return line
    else:
        raise ValueError, '"%s" isn\'t an import line' % line.rstrip()


def _fixed(lines):
    """returns fixed lines"""
    def rank(line):
        if _is_future_import(line): return 3
        if _is_global_import(line): return 2
        if _is_from_import(line): return 1
        if _is_boring(line): return 0
    lines = filter(lambda line: line.strip(), lines)
    lines = map(lambda line: _repair_any(line), lines)
    return _sorted(lines, key=lambda x: (-rank(x), x.upper()))


def _fix_safely(lines):
    """fixes all unindented imports in the beginning of list of lines"""
    start, end = _get_lines(lines)
    lines[start:end] = _fixed(lines[start:end])
    return lines


def sort_imports(editor=wingapi.kArgEditor):
    """WingIDE command entry point for sorting imports"""
    document = editor.GetDocument()
    document.BeginUndoAction()
    fixed = _fix_safely(document.GetText().split('\n'))
    document.SetText('\n'.join(fixed))
    document.EndUndoAction()
