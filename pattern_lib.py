import collections
import svg.path

from xml.dom import minidom

ERROR = 1e-5
NO_GROUP = '#000000'


class Edge(object):

  def __init__(self, path, group, is_fixed):
    self._path = path
    self.group = group
    self.is_fixed = is_fixed

  def Length(self):
    return sum(segment.length(error=ERROR) for segment in self._path)


def _ParseStyle(path_element, group_map):
  style_dict = {}
  for entry in path_element.getAttribute('style').split(';'):
    key, value = entry.split(':')
    style_dict[key] = value
  group_str = style_dict.get('stroke', NO_GROUP)
  if group_str not in group_map:
    group_map[group_str] = len(group_map)
  is_fixed = style_dict.get('stroke-dasharray', 'none') == 'none'
  return group_map[group_str], is_fixed


def _SortEdges(edges):
  ref_edge = None
  var_edges = []
  for edge in edges:
    if edge.is_fixed:
      if ref_edge:
        raise Exception('Group had multiple fixed edges.')
      ref_edge = edge
    else:
      var_edges.append(edge)
  if not ref_edge:
    raise Exception('Group had no fixed edges.')
  return [ref_edge] + var_edges


def ParseImage(input_str):
  edge_map = collections.defaultdict(list)
  group_map = {NO_GROUP: 0}
  tree = minidom.parseString(input_str)
  for path_element in tree.getElementsByTagName('path'):
    path = svg.path.parse_path(path_element.getAttribute('d'))
    group, is_fixed = _ParseStyle(path_element, group_map)
    edge_map[group].append(Edge(path, group, is_fixed))
  return {group: _SortEdges(edges) if group else edges
          for group, edges in edge_map.iteritems()}
