import collections
import copy
import math
import numpy
import numpy.linalg
import scipy.optimize
import svg.path

from xml.dom import minidom

ERROR = 1e-5
NO_GROUP = '#000000'


class KState(object):

  def __init__(self, lengths, angles, pos0, v0):
    self.lengths = lengths
    self.angles = angles
    self.pos0 = pos0
    self.v0 = v0


class Edge(object):

  def __init__(self, path, group, is_fixed):
    self._path = path
    self.group = group
    self.is_fixed = is_fixed

  def Length(self):
    return sum(segment.length(error=ERROR) for segment in self._path)

  def Reduce(self):
    r_path = svg.path.Path(*[svg.path.Line(s.start, s.end) for s in self._path])
    return Edge(r_path, self.group, self.is_fixed)


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


def _IsLine(segment):
  return type(segment) is svg.path.Line


def _DirVec(start, end):
  v = end - start
  return v / abs(v)


def _Angle(u, v):
  return math.copysign(
      math.acos((u.real * v.real + u.imag * v.imag) / (abs(u) * abs(v))),
      u.real * v.imag - u.imag * v.real)


def _Rotate(v, theta):
    return (v.real * math.cos(theta) - v.imag * math.sin(theta) +
            (v.real * math.sin(theta) + v.imag * math.cos(theta)) * 1j)


def _PathToState(path):
  lengths = []
  angles = []
  v0 = _DirVec(path[0].start, path[-1].end)
  v = v0
  for segment in path:
    lengths.append(segment.length(error=ERROR))
    n_v = _DirVec(segment.start, segment.end)
    angles.append(_Angle(v, n_v))
    v = n_v
  return KState(lengths, angles, path[0].start, v0)


def _ChainToPath(chain):
  segments = []
  start = chain[0]
  for end in chain[1:]:
    segments.append(svg.path.Line(start, end))
    start = end
  return svg.path.Path(*segments)


def _ForwardK(state):
  chain = [state.pos0]
  v = state.v0
  for length, angle in zip(state.lengths, state.angles):
    v = _Rotate(v, angle)
    chain.append(chain[-1] + length * v)
  return chain


def _ResizeReducedEdge(edge, target_length):
  # Get starting state
  state0 = _PathToState(edge._path)

  # Scale state
  scale = target_length / edge.Length()
  state0.lengths = [scale * l for l in state0.lengths]

  # Optimize state
  def _ObjectiveF(angles):
    def _Distance(a, b):
      return abs(a - b)
    return sum(_Distance(a, b) for a, b in zip(angles, state0.angles))
  def _ConstraintXF(angles):
    state = copy.copy(state0)
    state.angles = angles
    return _ForwardK(state)[-1].real - edge._path[-1].end.real
  def _ConstraintYF(angles):
    state = copy.copy(state0)
    state.angles = angles
    return _ForwardK(state)[-1].imag - edge._path[-1].end.imag
  constraints = [
      {'type': 'eq', 'fun': _ConstraintXF},
      {'type': 'eq', 'fun': _ConstraintYF},
  ]
  r = scipy.optimize.minimize(
      _ObjectiveF, state0.angles, constraints=constraints)
  if not r.success:
    raise Exception('Optimization failed:\n%s' % r)
  final_state = copy.copy(state0)
  final_state.angles = r.x

  # Output edge
  return Edge(_ChainToPath(_ForwardK(final_state)), edge.group, edge.is_fixed)


def _TransformPoint(pos, T):
  x = numpy.array([pos.real, pos.imag, 1])
  y = numpy.dot(T, x)
  y /= y[2]
  return y[0] + y[1] * 1j


def _TransformCurve(curve, line):
  v = curve.end - curve.start
  vt = line.end - line.start
  s = abs(vt) / abs(v)
  theta = -1 * _Angle(v, vt)
  T = numpy.array([
      [s * math.cos(theta),
       s * math.sin(theta),
       (-1 * s * curve.start.real * math.cos(theta) -
        s * curve.start.imag * math.sin(theta) +
        line.start.real)],
      [-s * math.sin(theta),
       s * math.cos(theta),
       (s * curve.start.real * math.sin(theta) -
        s * curve.start.imag * math.cos(theta) +
        line.start.imag)],
      [0, 0, 1]])

  # Build transformed curve
  return svg.path.CubicBezier(
      line.start, _TransformPoint(curve.control1, T),
      _TransformPoint(curve.control2, T), line.end)


def _EnforceSmoothness(edge, target_edge):
  def _SegmentAngle(segment1, segment2):
    u = _DirVec(segment1.control2, segment1.end)
    v = _DirVec(segment2.start, segment2.control1)
    return _Angle(u, v)
  for i in xrange(1, len(edge._path)):
    if _IsLine(edge._path[i - 1]) or _IsLine(edge._path[i]):
      continue
    if abs(_SegmentAngle(target_edge._path[i - 1],
                         target_edge._path[i])) < ERROR:
      angle = _SegmentAngle(edge._path[i - 1], edge._path[i])
      if abs(angle) > ERROR:
        u = edge._path[i - 1].control2 - edge._path[i - 1].end
        u = _Rotate(u, angle / 2)
        edge._path[i - 1].control2 = u + edge._path[i - 1].end

        v = edge._path[i].control1 - edge._path[i].start
        v = _Rotate(v, -1 * angle / 2)
        edge._path[i].control1 = v + edge._path[i].start


def _ScaleSegment(segment, factor):
  segment.control1 = factor * (segment.control1 - segment.start) + segment.start
  segment.control2 = factor * (segment.control2 - segment.end) + segment.end


def _FinalResizeSegment(segment, target_length):
  def _ObjectiveF(factors):
    return (factors[0] - 1) ** 2
  def _ConstraintF(factors):
    scaled_segment = copy.copy(segment)
    _ScaleSegment(scaled_segment, factors[0])
    return scaled_segment.length(error=ERROR) - target_length
  constraints = [{'type': 'eq', 'fun': _ConstraintF}]
  r = scipy.optimize.minimize(
      _ObjectiveF, [1.], constraints=constraints)
  if not r.success:
    raise Exception('Optimization failed:\n%s' % r)
  _ScaleSegment(segment, r.x[0])


def _FinalResize(edge, target_edge, scale):
  for segment, target_segment in zip(edge._path, target_edge._path):
    if _IsLine(segment):
      continue
    _FinalResizeSegment(segment, scale * target_segment.length(error=ERROR))


def ResizeEdge(edge, target_length):
  # Resize reduced edge
  scale = target_length / edge.Length()
  r_edge = edge.Reduce()
  scaled_r_edge = _ResizeReducedEdge(edge, scale * r_edge.Length())

  # Rough scaling of curve segments
  segments = []
  for segment, scaled_r_segment in zip(edge._path, scaled_r_edge._path):
    if _IsLine(segment):
      segments.append(scaled_r_segment)
    else:
      segments.append(_TransformCurve(segment, scaled_r_segment))
  scaled_edge = Edge(svg.path.Path(*segments), edge.group, edge.is_fixed)

  # Enforce smoothness
  _EnforceSmoothness(scaled_edge, edge)

  # Final resize
  _FinalResize(scaled_edge, edge, scale)

  return scaled_edge
