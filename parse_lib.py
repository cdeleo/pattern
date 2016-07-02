import geo_lib

import collections

from xml.dom import minidom

Mode = collections.namedtuple('Mode', ['expected_points', 'next_mode'])
MODE_MAP = {'m': Mode(1, 'l'),
            'l': Mode(1, 'l'),
            'c': Mode(3, 'c')}
NO_GROUP = '#000000'


def _ParseSegments(path):
  segments = []
  pos = geo_lib.Point(0, 0)
  mode = None
  relative = None
  point_buffer = []

  for token in path.getAttribute('d').split(' '):
    if token.lower() in MODE_MAP:
      if point_buffer:
        raise Exception('Malformed path data: %s' % path.getAttribute('d'))
      mode = token.lower()
      relative = token == mode
    else:
      x, y = token.split(',')
      point = geo_lib.Point(float(x), float(y))
      if relative:
        point_buffer.append(pos + point)
      else:
        point_buffer.append(point)
      if len(point_buffer) == MODE_MAP[mode].expected_points:
        point_buffer = [pos] + point_buffer
        if mode == 'm':
          pass
        elif mode == 'l':
          segments.append(geo_lib.Line(point_buffer))
        elif mode == 'c':
          segments.append(geo_lib.Curve(point_buffer))
        pos = point_buffer[-1]
        mode = MODE_MAP[mode].next_mode
        point_buffer = []
  return segments


def _ParseStyle(path, group_map):
  style_dict = {}
  for entry in path.getAttribute('style').split(';'):
    key, value = entry.split(':')
    style_dict[key] = value
  group_str = style_dict.get('stroke', NO_GROUP)
  if group_str not in group_map:
    group_map[group_str] = len(group_map)
  is_fixed = style_dict.get('stroke-dasharray', 'none') == 'none'
  return group_map[group_str], is_fixed


def _SortPaths(paths):
  ref_path = None
  var_paths = []
  for path in paths:
    if path.is_fixed:
      if ref_path:
        raise Exception('Group had multiple fixed paths.')
      ref_path = path
    else:
      var_paths.append(path)
  if not ref_path:
    raise Exception('Group had no fixed paths.')
  return [ref_path] + var_paths


def ParseImage(input_str):
  paths = collections.defaultdict(list)
  group_map = {NO_GROUP: 0}
  tree = minidom.parseString(input_str)
  for path in tree.getElementsByTagName('path'):
    segments = _ParseSegments(path)
    group, is_fixed = _ParseStyle(path, group_map)
    paths[group].append(geo_lib.Path(segments, group, is_fixed))
  return {group: _SortPaths(paths) for group, paths in paths.iteritems()}
