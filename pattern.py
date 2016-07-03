import argparse
import pattern_lib

parser = argparse.ArgumentParser()
parser.add_argument('input', type=str, help='Path to the input svg.')
args = parser.parse_args()


def main():
  input_str = open(args.input).read()
  edge_map = pattern_lib.ParseImage(input_str)
  for group, edges in edge_map.iteritems():
    print 'Group %d:' % group
    for i, edge in enumerate(edges):
      print '  Edge %d (%s) length=%f' % (
          i, 'ref' if edge.is_fixed else 'var', edge.Length())


if __name__ == '__main__':
  main()
