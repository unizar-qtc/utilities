#!/usr/bin/env python3

# Description : Convert the last coordinates of a Gaussian .log to a input file
# Last update : 04-10-2022
# Author      : Julen Munarriz & Sergio Boneta

import argparse
import os
from textwrap import dedent


# Parse command line arguments
parser = argparse.ArgumentParser(description='Convert the last coordinates of a Gaussian .log to a input file')
parser.add_argument('log', type=str, help='Gaussian output file (.log)')
parser.add_argument('com', type=str, help='Gaussian input file (.com/.gjf)')
parser.add_argument('--name', type=str, required=False, default='test', help='Name of the new calculation (def: test)')
parser.add_argument('--charge', metavar='#', type=int, required=False, help='Charge (otherwise readed from .log)')
parser.add_argument('--multi', metavar='#', type=int, required=False, help='Multiplicity (otherwise readed from .log)')
parser.add_argument('--func', metavar='<>', type=str, required=False, default='B3LYP', help='DFT Functional (def: B3LYP)')
parser.add_argument('--basis', metavar='<>', type=str, required=False, default='Def2SVP', help='Basis set (def: Def2SVP)')
parser.add_argument('--calc', metavar='<>', type=str, nargs='*', required=False, default=['opt', 'freq=noraman'], help='Calculation parameters, can be empty (def: \'opt freq=noraman\')')
parser.add_argument('--dispersion', action='store_true', required=False, help='Add GD3BJ Empirical Dispersion')
args = parser.parse_args()
file_log = args.log
file_inp = args.com
name     = args.name
charge   = args.charge
multi    = args.multi
func     = args.func
basis    = args.basis
calc_param = f"{' '.join(args.calc)}"
dispersion = "EmpiricalDispersion=GD3BJ" if args.dispersion else ""

# Read .log file
with open(file_log, 'r') as f:
    datos = f.readlines()

# Guardamos las coordenadas como texto en un vector y utilizamos la variable pos_coord para movernos por el
coordenadas = []
pos_coord = 0

# Para buscar las coordenadas buscamos "Standard orientation", debemos tomar la ultima vez que aparezca
# num_veces es el numero de veces que esta escrito "Standard orientation" en el fichero y "num_veces" la posicion en la que nos encontramos al recorrer la lista la segunda vez
# linea_coord es la linea en la que empezaremos a leer las coordenadas 
num_veces = 0
for a in datos:
    if "Standard orientation" in a:
        num_veces += 1

num_busca = 0
linea_coord = 0
for a in datos:
    if "Standard orientation" in a:
        num_busca += 1

        if (num_busca == num_veces):
            linea_coord += 5
            break
    linea_coord += 1

# Guardamos las coordenadas
while '-----------' not in datos[linea_coord]:
    coordenadas.append(" ")
    coordenadas[pos_coord] = datos[linea_coord][14:22]+datos[linea_coord][34:]
    linea_coord += 1
    pos_coord += 1

# Buscamos la carga y la multiplicidad
for a in datos:
    if "Charge =" in a:
        carga = charge or a[10:12].strip()
        multiplicidad = multi or a[27:].strip()
        break

# Ensure that final file has the right extension
file_com_name, file_com_extension = os.path.splitext(file_inp)
if file_com_extension not in ['.com', '.gjf']:
    file_inp = file_com_name + '.com'

# Write new Gaussian input file
with open(file_inp, 'w') as f:
    f.write(dedent(f"""\
        # {func} {basis} {calc_param} {dispersion}
        # int=(grid=ultrafine)

        {name}

        {carga} {multiplicidad}
        """))
    for a in coordenadas:
        f.writelines(a)
    f.write("\n")

print(f"{file_log} -> {file_inp}")
