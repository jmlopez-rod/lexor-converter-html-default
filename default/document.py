"""LEXOR to HTML DOCUMENT NodeConverter

"""

import os
from imp import load_source
from lexor.core import NodeConverter, DocumentType, Element


def find_element(name, node, index=0, **keywords):
    """Looks for an element in the node children. If it is not found,
    a new element is created and placed before the specified index.
    """
    result = None
    for ele in node.child:
        if ele.name.lower() == name:
            result = ele
            break
    if result is None and keywords.get('insert', True):
        args = keywords.get('args', None)
        etype = keywords.get('etype', Element)
        if args is None:
            result = etype(name)
        else:
            result = etype(*args)
        node.insert_before(index, result)
    return result


class DocumentClassNC(NodeConverter):
    """Appends a DocumentType node. """
    num = 0
    ref = None

    def start(self, node):
        self.num += 1
        if self.num > 1:
            self.msg('E001', node)
        document = node.owner
        self.ref = find_element(
            '#doctype', document, 0, etype=DocumentType, args=['html']
        )
        return self.converter.remove_node(node)

    def convert(self):
        """Append an html node and the header node. """
        node = self.ref
        if len(self.converter.doc) != 1 or node is None:
            return
        document = node.owner
        find_element(
            '#doctype', document, 0, etype=DocumentType, args=['html']
        )
        html = find_element('html', document, 1)
        head = find_element('head', document, insert=False)
        if head is None:
            head = find_element('head', html, 0)
        else:
            html.insert_before(0, head)
        body = find_element('body', document, insert=False)
        if body is None:
            body = find_element('body', html, 1)
        else:
            head.extend_children(document[html.index+1:body.index])
            html.insert_before(1, body)
        body.extend_children(document[body.parent.index+1:])


class UsePackageNC(NodeConverter):
    """Loads an external python script. """

    def start(self, node):
        pkg = [item.strip() for item in node.data.split(',')]
        self.converter.doc[0].namespace['usepackage'].extend(pkg)
        return self.converter.remove_node(node)

    def get_module(self, src):
        """Load the module specified by name. """
        name = os.path.basename(src)
        name = os.path.splitext(name)[0]
        if src[0] != '/':
            base = os.path.dirname(self.converter.doc[0].uri_)
            if base != '':
                base += '/'
            path = '%s%s' % (base, src)
            if not path.endswith('.py'):
                path += '.py'
            try:
                return load_source('lexor-package_%s' % name, path)
            except IOError:
                try:
                    lexorinputs = os.environ['LEXORINPUTS']
                except KeyError:
                    raise ImportError
                for directory in lexorinputs.split(':'):
                    path = '%s/%s.py' % (directory, name)
                    if os.path.exists(path):
                        modname = 'lexor-package_%s' % name
                        return load_source(modname, path)
                raise ImportError

    def convert(self):
        """Calls the convert function in each of the packages. """
        if len(self.converter.doc) != 1:
            return
        doc = self.converter.doc[0]
        pkg = doc.meta.get('usepackage', None)
        if pkg:
            pkg = [item.strip() for item in pkg.split(',')]
            doc.namespace['usepackage'][0:0] = pkg
        for src in doc.namespace['usepackage']:
            if not src:
                continue
            try:
                mod = self.get_module(src)
            except ImportError:
                self.msg('E100', None, [src])
                continue
            if hasattr(mod, 'convert'):
                if mod.convert.func_code.co_argcount == 2:
                    mod.convert(self.converter, self.converter.doc[0])
                else:
                    self.msg('E102', None, [src])
            else:
                self.msg('E101', None, [src])

MSG = {
    'E001': 'more than one documentclass node found',
    'E100': 'package `{0}` not found',
    'E101': 'package `{0}` does not declare the `convert` function',
    'E102': 'package `{0}` convert function argument count != 2'
}
MSG_EXPLANATION = [
    """
    - There can only be one documentclass node in a document. Make
      sure that documents included within a document do not contain
      such nodes.

    - Make sure the body node is declared when using the
      documentclass node.

    Reports error E001 and E002.

""",
    """
    - A "lexor" package is a python script which declares the
      function convert with two arguments: converter and document.

    - If the package is not found in the same directory as the
      document or some relative location to the document then it it
      searches in each of the paths declared by the enviroment
      variable `LEXORINPUTS`.

    Reports error E100, E101 and E102.

""",
]
