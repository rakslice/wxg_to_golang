import xml.dom.minidom


def child_elements(node, name):
    """Iterate through direct child elements of a node that have the given tag name"""
    assert isinstance(node, xml.dom.minidom.Node), "child element was %r, not node" % type(node)
    for subnode in node.childNodes:
        if subnode.nodeType != xml.dom.minidom.Node.ELEMENT_NODE:
            continue
        assert isinstance(subnode, xml.dom.minidom.Element)
        if subnode.nodeName != name:
            continue
        yield subnode


def child_element_text(node, name, default_value=""):
    """Get the text of the direct child element(s) of a node"""
    parts = []
    found = False
    for element in child_elements(node, name):
        found = True
        for node in element.childNodes:
            if node.nodeType == element.TEXT_NODE:
                assert isinstance(node, xml.dom.minidom.Text)
                # noinspection PyUnresolvedReferences
                parts.append(node.nodeValue)
    if not found:
        return default_value
    return "".join(parts)
