from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

class Sanitizer(Treeprocessor):
  def __init__(self, allowed):
    self.allowed = allowed

  def run(self, root):
    allowed = self.allowed
    garbage = []
    queue = [root]
    while queue:
      parent = queue.pop()
      for el in parent:
        if el.tag in allowed:
          queue.append(el)
        else:
          # we can't remove elements during the loop
          garbage.append(el)
      for el in garbage: # empty garbage
        parent.remove(el)
      garbage.clear()
      # there seems to be no way of deleting attributes, their
      # structure is an implementation detail, and I don't want to
      # recreate a copy of the element, so we set them to None
      for attr in parent.attrib.keys():
        allowed_attr = allowed.get(parent.tag, [])
        if attr not in allowed_attr:
          garbage.append(attr)
      for attr in garbage:
        del parent.attrib[attr]
      garbage.clear()


class SanitizeExtension(Extension):
  def __init__(self, allowed={'div': ['class']}):
    self.allowed = allowed

  def extendMarkdown(self, md):
    md.treeprocessors.register(Sanitizer(self.allowed), 'sanitizer', 8)
    md.registerExtension(self)
