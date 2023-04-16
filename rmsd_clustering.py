#!/usr/bin/env python3

"""
=======================================================================
    RMSD CLUSTERING
=======================================================================

Calculate the RMSD between small molecules and group them into clusters

"""

import argparse
import itertools
import multiprocessing as mp
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
from numpy import ndarray
import rmsd

# OpenBabel for extended I/O support of file formats
try:
    from openbabel import pybel
except ImportError:
    pybel = None

# Matplotlib/Seaborn for plotting
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    plt = None
    sns = None


__version__ = '0.1.1'


class Cluster():
    """
    A class to hold a group of molecules

    Attributes
    ----------
    molecs : list[tuple[ndarray, ndarray]]
        A list of tuples of (atoms, coordinates) for each molecule
    titles : list
        A list of titles for each molecule

    """

    reorder_methods = {
        'hungarian': rmsd.reorder_hungarian,
        'intertia-hungarian': rmsd.reorder_inertia_hungarian,
        'brute': rmsd.reorder_brute,
        'distance': rmsd.reorder_distance }
    
    def __init__(self):
        self.molecs = []
        self.titles = []

    @property
    def n_atoms(self) -> int:
        return len(self.molecs[0][0])

    @property
    def n_molecs(self) -> int:
        return len(self.molecs)

    @property
    def atoms(self) -> list:
        return [molec[0] for molec in self.molecs]

    @property
    def coords(self) -> list:
        return [molec[1] for molec in self.molecs]

    def read_xyz(self, filename:str, atoms_as_int:bool=True) -> None:
        """
        Read a group of molecules from an xyz file

        Parameters
        ----------
        filename : str
            Path to the xyz file
        atoms_as_int : bool, optional
            Whether to store the atoms as integers or strings (def: True)
        """
        with open(filename, 'r') as f:
            xyz_lines = f.readlines()
        n = 0
        while n < len(xyz_lines):
            n_atoms = int(xyz_lines[n].strip())
            self.titles.append(str(xyz_lines[n+1].strip()))
            self.molecs.append(rmsd.get_coordinates_xyz_lines(xyz_lines[n:n+2+n_atoms], return_atoms_as_int=atoms_as_int))
            n += n_atoms + 2

    def read_openbabel(self, filename:str, format:str=None, atoms_as_int:bool=True) -> None:
        """
        Read a group of molecules from a file using OpenBabel

        Parameters
        ----------
        filename : str
            Path to the file
        format : {None, str}, optional
            Format of the file, otherwise guessed from the name or suffix (def: None)
        atoms_as_int : bool, optional
            Whether to store the atoms as integers or strings (def: True)
        """
        if not pybel:
            raise ImportError('\'openbabel\' not found, please install it to use this function')
        # guess format
        if format is None:
            if Path(filename).name in pybel.informats:
                format = Path(filename).name
            else:
                format = Path(filename).suffix[1:]
        # check format
        if format not in pybel.informats:
            raise ValueError('Unknown format')
        # read and convert to store
        for mol in pybel.readfile(format, filename, {'b':None}):
            self.titles.append(mol.title)
            if atoms_as_int:
                atoms = np.array([atom.atomicnum for atom in mol.atoms])
            else:
                atoms = np.array([atom.type for atom in mol.atoms])
            coords = np.array([atom.coords for atom in mol.atoms])
            self.molecs.append((atoms, coords))
            if format in {'POSCAR', 'CONTCAR'}:
                break

    @staticmethod
    def reorder(molec1:tuple, molec2:tuple, reorder_method='brute') -> tuple:
        """
        Reorder the atoms in molecule 2 to match molecule 1

        Parameters
        ----------
        molec1 : tuple[ndarray, ndarray]
            Reference molecule, tuple of (atoms, coordinates)
        molec2 : tuple[ndarray, ndarray]
            Molecule to reorder, tuple of (atoms, coordinates)
        reorder_method : {'hungarian', 'intertia-hungarian', 'brute', 'distance'}, optional
            Method to reorder the atoms (def: 'brute')

        Returns
        -------
        tuple[ndarray, ndarray]
            The reordered molecule, tuple of (atoms, coordinates)
        """
        if reorder_method not in Cluster.reorder_methods:
            raise ValueError('Unknown reorder method')
        molec2_reorder = Cluster.reorder_methods[reorder_method](molec1[0], molec2[0], molec1[1], molec2[1])
        return molec2[0][molec2_reorder], molec2[1][molec2_reorder]

    @staticmethod
    def rmsd(molec1:tuple, molec2:tuple, reorder_method='brute') -> float:
        """
        Calculate the RMSD between two molecules

        Parameters
        ----------
        molec1 : tuple[ndarray, ndarray]
            Molecule 1, tuple of (atoms, coordinates)
        molec2 : tuple[ndarray, ndarray]
            Molecule 2, tuple of (atoms, coordinates)
        reorder_method : {None, 'hungarian', 'intertia-hungarian', 'brute', 'distance'}, optional
            Method to reorder the atoms (def: 'brute')

        Returns
        -------
        float
            The RMSD between the two molecules
        """
        if reorder_method is not None:
            molec2 = Cluster.reorder(molec1, molec2, reorder_method)
        return rmsd.kabsch_rmsd(molec1[1], molec2[1])

    def rmsd_ndx(self, ndx1:int, ndx2:int, reorder_method='brute') -> float:
        """
        Calculate the RMSD between two molecular entries in the cluster

        Parameters
        ----------
        ndx1 : int
            Index of the first molecule
        ndx2 : int
            Index of the second molecule
        reorder_method : {None, 'hungarian', 'intertia-hungarian', 'brute', 'distance'}, optional
            Method to reorder the atoms (def: 'brute')

        Returns
        -------
        float
            The RMSD between the two molecules
        """
        molec1 = deepcopy(self.molecs[ndx1])
        molec2 = deepcopy(self.molecs[ndx2])
        return self.rmsd(molec1, molec2, reorder_method)

    def rmsd_matrix(self, reorder_method='brute') -> ndarray:
        """
        Calculate the RMSD matrix for the cluster

        Parameters
        ----------
        reorder_method : {None, 'hungarian', 'intertia-hungarian', 'brute', 'distance'}, optional
            Method to reorder the atoms (def: 'brute')

        Returns
        -------
        ndarray(n_molecs, n_molecs)
            The RMSD matrix
        """
        pairs = list(itertools.combinations(range(self.n_molecs), 2))
        with mp.Pool(processes=mp.cpu_count()) as pool:
            rmsds = pool.starmap(self.rmsd_ndx, [(i, j, reorder_method) for i, j in pairs])
        rmsd_matrix = np.zeros((self.n_molecs, self.n_molecs))
        for pair, rmsd in zip(pairs, rmsds):
            rmsd_matrix[pair] = rmsd
        rmsd_matrix += rmsd_matrix.T
        return rmsd_matrix

    @staticmethod
    def matrix_stat(matrix:ndarray) -> tuple:
        """
        Calculate statistics of a matrix

        Parameters
        ----------
        matrix : ndarray
            The matrix to calculate the statistics for

        Returns
        -------
        tuple
            mean of upper triangle (without diagonal), standard deviation of upper triangle (without diagonal)
        """
        if matrix.size == 1:
            mean = 0.0
            std = 0.0
        else:
            mean = np.mean(matrix[np.triu_indices(matrix.shape[0], k=1)])
            std = np.std(matrix[np.triu_indices(matrix.shape[0], k=1)])
        return mean, std

    @staticmethod
    def matrix_fmt(matrix:ndarray, header_init=1) -> str:
        """
        Format a matrix as a string

        Parameters
        ----------
        matrix : ndarray
            The matrix to format
        header_init : int, optional
            The initial value for the header (def: 1)

        Returns
        -------
        str
            The matrix as a formatted string
        """
        s = ' '*7 + ' '.join([f'{i:8d}' for i in range(header_init, header_init + matrix.shape[0])])
        for i in range(matrix.shape[0]):
            s += f'\n{i+header_init:6d} ' + ' '.join([f' {matrix[i,j]:7.4f}' for j in range(matrix.shape[1])])
        return s

    @staticmethod
    def matrix_heatmap(matrix:ndarray, header_init=1, filename=None) -> None:
        """
        Generate a heatmap of a matrix

        Parameters
        ----------
        matrix : ndarray
            The matrix to format
        header_init : int, optional
            The initial value for the header (def: 1)
        filename : str, optional
            Filename to save the heatmap image to (def: None)
        """
        if not plt or not sns:
            raise ImportError('\'matplotlib\' and/or \'seaborn\' not found, please install them to use this function')
        #TODO: better handlig of tick labels
        sns.heatmap(
            matrix,
            xticklabels=range(header_init, header_init + matrix.shape[0]),
            yticklabels=range(header_init, header_init + matrix.shape[0]),
            linewidth=0.0,
            cmap='viridis',
            cbar_kws={'label': 'RMSD'},
            square=True
            )
        if filename:
            plt.savefig(filename, dpi=300)

    def cluster(self, cutoff:float, reorder_method='brute', rmsd_matrix=None) -> list:
        """
        Cluster the molecules

        Parameters
        ----------
        cutoff : float
            The RMSD cutoff for clustering
        reorder_method : {None, 'hungarian', 'intertia-hungarian', 'brute', 'distance'}, optional
            Method to reorder the atoms (def: 'brute')
        rmsd_matrix : ndarray, optional
            The RMSD matrix to use instead of calculating (def: None)

        Returns
        -------
        list[list[int]]
            List of cluster's indexes
        """
        rmsd_matrix = rmsd_matrix if rmsd_matrix is not None else self.rmsd_matrix(reorder_method)
        clusters = []
        for i in range(self.n_molecs):
            for cluster in clusters:
                if all(rmsd_matrix[i,j] < cutoff for j in cluster):
                    cluster.append(i)
                    break
            else:
                clusters.append([i])
        return clusters

    def copy_ndx(self, ndx:list) -> 'Cluster':
        """
        Partial copy of the cluster object based on a list of molecules

        Parameters
        ----------
        ndx : list[int]
            List of indexes to copy

        Returns
        -------
        Cluster
            New cluster
        """
        new_cluster = Cluster()
        new_cluster.molecs = deepcopy([self.molecs[i] for i in ndx])
        new_cluster.titles = deepcopy([self.titles[i] for i in ndx])
        return new_cluster


def main():

    ## CLI parser
    parser = argparse.ArgumentParser(description='Simple RMSD based clustering',
                                     formatter_class=argparse.RawTextHelpFormatter)
    help_pybel = ("\nonly 'xyz' available, install 'OpenBabel' for support of more formats", argparse.SUPPRESS) if not pybel else (", mix formats supported", "input format supported by OpenBabel (def: auto-detect)")
    parser.add_argument('-v', '--version', action='version', version=f'RMSD Clustering - v{__version__}')
    parser.add_argument('input', nargs='+',
                        help='file(s) with one or multiple structures'+help_pybel[0])
    parser.add_argument('--input-format', metavar='<>', type=str, default=None,
                        help=help_pybel[1])
    parser.add_argument('--reorder-method', metavar='<>', type=str, default='brute',
                        choices=['none', 'hungarian', 'intertia-hungarian', 'brute', 'distance'],
                        help='method to reorder the atoms (none/hungarian/inertia-hungarian/brute/distance) (def: brute)')
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('--cutoff', metavar='#', type=float, default=0.1,
                        help='RMSD cutoff for clustering (def: 0.1)')
    group1.add_argument('--n-clusters', metavar='#', type=int, default=None,
                        help='number of clusters to generate, overrides cutoff')
    help_plot = 'save the RMSD matrix as a heatmap image to a file' if plt and sns else argparse.SUPPRESS
    parser.add_argument('--heatmap', metavar='<>', type=str, default=None,
                        help=help_plot)
    parser.add_argument('--rmsd-matrix', metavar='<>', type=str, default=None,
                        help='read/write the RMSD matrix from/to a .csv file')
    args = parser.parse_args()
    input_files = args.input
    input_format = args.input_format
    reorder_method = args.reorder_method if args.reorder_method != 'none' else None
    cutoff = args.cutoff
    n_clusters = args.n_clusters
    heatmap = args.heatmap
    rmsd_matrix_file = args.rmsd_matrix

    ## read input files
    mol = Cluster()
    print(f'\n ## Files:\n', flush=True)
    for input_file in input_files:
        n_molecs_prev = mol.n_molecs
        if not pybel:
            mol.read_xyz(input_file)
        else:
            mol.read_openbabel(input_file, input_format)
        n_molecs_last = mol.n_molecs - n_molecs_prev
        ending_molec = '' if n_molecs_last == 1 else f' - {mol.n_molecs}'
        print(f'    {input_file} ({n_molecs_last}):  {n_molecs_prev + 1}{ending_molec}', flush=True)

    ## RMSD matrix
    if rmsd_matrix_file and Path(rmsd_matrix_file).exists():
        print(f'\n ## RMSD matrix (loaded from \'{rmsd_matrix_file}\')', end="", flush=True)
        rmsd_matrix = np.loadtxt(rmsd_matrix_file, delimiter=',')
        if not mol.n_molecs == rmsd_matrix.shape[0] == rmsd_matrix.shape[1]:
            raise ValueError(f'Number of molecules in the input files ({mol.n_molecs}) does not match the RMSD matrix ({rmsd_matrix.shape[0]}x{rmsd_matrix.shape[1]})')
    else:
        print(f'\n ## RMSD matrix (reorder_method = {reorder_method})', end="", flush=True)
        rmsd_matrix = mol.rmsd_matrix(reorder_method=reorder_method)
        if rmsd_matrix_file:
            print(f' - saved to \'{rmsd_matrix_file}\'', end="", flush=True)
            np.savetxt(rmsd_matrix_file, rmsd_matrix, delimiter=',')
    rmsd_matrix_stat = mol.matrix_stat(rmsd_matrix)
    print(f' :  {rmsd_matrix_stat[0]:.4f} +/- {rmsd_matrix_stat[1]:.4f}')
    if heatmap:
        heatmap = heatmap if Path(heatmap).suffix[1:] in plt.gcf().canvas.get_supported_filetypes() else heatmap + '.png'
        print(f'\n ## Heatmap image saved to \'{heatmap}\'\n', flush=True)
        mol.matrix_heatmap(rmsd_matrix, filename=heatmap)
    ## clustering
    if n_clusters is not None:
        # check number of clusters requested
        if n_clusters > mol.n_molecs:
            print(f'ERROR: n_clusters ({n_clusters}) > n_molecs ({mol.n_molecs})')
            sys.exit(1)
        clusters = mol.cluster(cutoff=cutoff, rmsd_matrix=rmsd_matrix)
        while len(clusters) != n_clusters:
            if len(clusters) > n_clusters:
                cutoff += cutoff * 0.5
            else:
                cutoff -= cutoff * 0.5
            clusters = mol.cluster(cutoff=cutoff, rmsd_matrix=rmsd_matrix)
    else:
        clusters = mol.cluster(cutoff=cutoff, rmsd_matrix=rmsd_matrix)

    ## output
    print(f'\n ## Clusters (cutoff = {cutoff:.4f}) (intra-RMSD mean +/- intra-RMSD std):\n')
    for i, cluster_ndx in enumerate(clusters):
        cluster = mol.copy_ndx(cluster_ndx)
        cluster_rmsd_matrix = cluster.rmsd_matrix(reorder_method=reorder_method)
        cluster_stat = Cluster.matrix_stat(cluster_rmsd_matrix)
        cluster_ndx = ', '.join([str(ndx+1) for ndx in cluster_ndx])
        print(f'{i+1:6d}:  {cluster_ndx:50s}     {cluster_stat[0]:.4f} +/- {cluster_stat[1]:.4f}')
    print()

    sys.exit(0)


if __name__ == '__main__':
    main()
