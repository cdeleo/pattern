import argparse
import pattern_lib
import svg.path

from xml.dom import minidom

parser = argparse.ArgumentParser()
parser.add_argument('input', type=str, help='Path to the input svg.')
parser.add_argument('output', type=str, help='Path for the output svg.')
args = parser.parse_args()


def DrawSvg(edges):
  doc = minidom.Document()
  root = doc.createElement('svg')
  root.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  doc.appendChild(root)
  for edge in edges:
    path_element = doc.createElement('path')
    path_element.setAttribute('style', 'fill:none;stroke:#000000')
    path_element.setAttribute('d', edge._path.d())
    root.appendChild(path_element)
  return doc.toxml()


def main():
  input_str = open(args.input).read()
  edge_map = pattern_lib.ParseImage(input_str)
  for group, edges in edge_map.iteritems():
    edge = edges[0]
    break

  scaled_edge = pattern_lib.ResizeEdge(edge, 1.5 * edge.Length())

  edges = [edge, scaled_edge]
  with open(args.output, 'w') as output_file:
    output_file.write(DrawSvg(edges))


if __name__ == '__main__':
  main()
