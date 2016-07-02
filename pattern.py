import argparse
import parse_lib

parser = argparse.ArgumentParser()
parser.add_argument('input', type=str, help='Path to the input svg.')
args = parser.parse_args()


def main():
  input_str = open(args.input).read()
  paths = parse_lib.ParseImage(input_str)
  print paths


if __name__ == '__main__':
  main()
