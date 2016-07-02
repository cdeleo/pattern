import math


class Point(object):

  def __init__(self, x, y):
    self.x = x
    self.y = y

  def norm(self):
    return math.sqrt(self.x ** 2 + self.y ** 2)

  def __add__(self, other):
    return Point(self.x + other.x, self.y + other.y)

  def __sub__(self, other):
    return Point(self.x - other.x, self.y - other.y)

  def __repr__(self):
    return '(%f, %f)' % (self.x, self.y)


class Segment(object):
  NAME = 'Segment'
  N_POINTS = None

  def __init__(self, points):
    if len(points) != self.N_POINTS:
      raise Exception(
          '%s segment expects %d points, go %d.' %
          (self.NAME, self.N_POINTS, len(points)))
    self.points = points

  def Length(self):
    raise NotImplementedError()

  def __repr__(self):
    return '<%s %s>' % (self.NAME, self.points)


class Line(Segment):
  NAME = 'Line'
  N_POINTS = 2

  def Length(self):
    return (self.p0 - self.p1).norm()


class Curve(Segment):
  NAME = 'Curve'
  N_POINTS = 4


class Path(object):

  def __init__(self, segments, group, is_fixed):
    self.segments = segments
    self.group = group
    self.is_fixed = is_fixed

  def __repr__(self):
    return '<Path %s>' % self.segments
