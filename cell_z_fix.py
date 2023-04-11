#!/usr/bin/env python3

# Description : Fix broken cells of POSCAR/CONTCAR files based on z-component of atom positions
# Last update : 11-04-2023
# Author      : Sergio Boneta


import argparse


def z_fix(input_file:str, output_file:str, z:float=0.6) -> None:
    """
    Fix broken cells of POSCAR/CONTCAR files based on z-component of atom positions

    Parameters
    ----------
    input_file : str
        input file (POSCAR/CONTCAR format)
    output_file : str
        output file
    z : float, optional
        z-component threshold for moving the atom to the next cell (def: 0.6)
    """
    # read input file
    with open(input_file, 'r') as f:
        lines = f.read().splitlines(False)
    # find 'Direct' line
    try:
        direct_index = lines.index('Direct')
    except ValueError:
        raise
    # fix z-component of atoms
    for i in range(direct_index+1, len(lines)):
        if lines[i].strip() == '':
            break
        line = lines[i].split()
        if float(line[2]) > z:
            line[2] = f"{float(line[2]) - 1.0:.16f}"
            lines[i] = '  ' + '  '.join(line)
    # write output file
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Fix broken cells of POSCAR/CONTCAR files based on z-component of atom positions')
    parser.add_argument('input', type=str, nargs='+',
                        help='input file(s) [POSCAR/CONTCAR format]')
    parser.add_argument('-o', '--output', metavar='<>', type=str,
                        help='output file (default: input file with suffix "_fix")')
    parser.add_argument('-z', '--z', metavar='#', type=float, default=0.6,
                        help='z-component threshold for moving the atom to the next cell (def: 0.6)')
    args = parser.parse_args()

    for input_file in args.input:
        if args.output:
            output_file = args.output
        else:
            output_file = input_file + '_fix'
        try:
            z_fix(input_file, output_file, args.z)
        except ValueError:
            print(f"Skipping '{input_file}'. No 'Direct' line found in file.")
            continue
        print(f"Fixed:  {input_file} -> {output_file}")

