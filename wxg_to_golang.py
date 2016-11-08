import argparse
import os
import sys

import wxg_golang_converter


def contents(input_filename):
    with open(input_filename, "r") as handle:
        return handle.read()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", required=True,
                        help=".wxg file to generate code for",
                        dest="input")
    parser.add_argument("--out", required=True,
                        help="golang file to output with generated code")
    parser.add_argument("--force", "-f",
                        default=False, action="store_true",
                        help="overwrite existing file")
    return parser.parse_args()


def die(msg):
    print >> sys.stderr, msg
    sys.exit(1)


def main():
    options = parse_args()

    input_filename = options.input
    output_filename = options.out

    if not os.path.exists(input_filename):
        die("Input file '%s' not found" % input_filename)

    if not options.force and os.path.exists(output_filename):
        die("Output file '%s' already exists; use -f to overwrite" % output_filename)

    wxg_golang_converter.convert(input_filename, output_filename)


if __name__ == "__main__":
    main()
