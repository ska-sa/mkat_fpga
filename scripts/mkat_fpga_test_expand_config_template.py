import argparse
import os

parser = argparse.ArgumentParser(description='Expand at test configuration template',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('input_template', action='store', help=
                    'corr2 config template')
parser.add_argument('output_template', action='store', help=
                    'Output expanded template to this file')
parser.add_argument('--bitstream-home', action='store', help=
                    'Home directory for bitsream files, defaults to '
                    '$PWD/bitstreams', default=os.path.join(
                        os.getcwd(), 'bitstreams'))
def fix_path(path):
    return os.path.abspath(os.path.expanduser(path))

args = parser.parse_args()
input_template = fix_path(args.input_template)
output_template = fix_path(args.output_template)
template_vars = dict(
    BITSTREAM_HOME=fix_path(args.bitstream_home))

with open(input_template) as inpt_f:
    template_str = inpt_f.read()

with open(output_template, 'w') as outpt_f:
    outpt_f.write(template_str.format(**template_vars))




