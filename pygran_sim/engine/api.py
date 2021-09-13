"""
The simple DEM Engine for basic contact analysis

Created on April 10, 2021

Author: Andrew Abi-Mansour

This is the::

  ██████╗ ██╗   ██╗ ██████╗ ██████╗  █████╗ ███╗   ██╗
  ██╔══██╗╚██╗ ██╔╝██╔════╝ ██╔══██╗██╔══██╗████╗  ██║
  ██████╔╝ ╚████╔╝ ██║  ███╗██████╔╝███████║██╔██╗ ██║
  ██╔═══╝   ╚██╔╝  ██║   ██║██╔══██╗██╔══██║██║╚██╗██║
  ██║        ██║   ╚██████╔╝██║  ██║██║  ██║██║ ╚████║
  ╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝

DEM simulation and analysis toolkit
http://www.pygran.org, support@pygran.org

Core developer and main author:
Andrew Abi-Mansour, andrew.abi.mansour@pygran.org

PyGran is open-source, distributed under the terms of the GNU Public
License, version 2 or later. It is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. You should have
received a copy of the GNU General Public License along with PyGran.
If not, see http://www.gnu.org/licenses . See also top-level README
and LICENSE files.

This file was modified from the LAMMPS source code.

LAMMPS - Large-scale Atomic/Molecular Massively Parallel Simulator
http://lammps.sandia.gov, Sandia National Laboratories
Steve Plimpton, sjplimp@sandia.gov

Copyright (2003) Sandia Corporation.  Under the terms of Contract
DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains
certain rights in this software.  This software is distributed under
the GNU General Public License.

See the README file in the top-level LAMMPS directory.

"""

import sys, traceback
import os
import glob
import sys
import logging
from typing import List


class EngineAPI:
    """A class that implements a python interface for DEM computations

    :param units: unit system (default 'si'). See `ref <https://www.cfdem.com/media/DEM/docu/units.html>`_.
    :type units: str

    :param style: particle type ('spherical' by default)
    :type style: str

    :param split: MPI communicator
    :type comm: MPI Intracomm

    :param species: defines the number and properties of all species
    :type species: tuple

    :param output: output dir name
    :type output: str

    :param print: specify which variables to print to stdout: (freq, 'varName1', 'varName2', ...). Default is (10**4, 'time', 'dt', 'atoms').
    :type print: tuple

    :param library: full path to the LIGGGHTS-PUBLIC module (.so file)
    :type library: str

    :param dim: simulation box dimension (2 or 3)
    :type dim: int

    :param restart: specify restart options via (freq=int, dirname=str, filename=str, restart=bool, frame=int)
    :type restart: tuple

    :param boundary: setup boundary conditions (see `ref <https://www.cfdem.com/media/DEM/docu/boundary.html>`_), e.g. ('p', 'p', 'p') -> periodic boundaries in 3D.
    :type boundary: tuple

    .. todo:: This class should be generic (not specific to liggghts), must handle all I/O, garbage collection, etc. and then moved to DEM.py
    """

    def __init__(
        self, *, split, library, style, comm=None, dim=3, units="si", **kwargs
    ):
        """Initialize some settings and specifications"""

        if kwargs.get("rank"):
            raise NotImplementedError

        rank = comm.Get_rank() if comm is not None else 0

        if not rank:
            logging.info("Using " + library + " for DEM computations")

        try:
            self.lib = self.load_library(library)
        except RuntimeError:
            etype, value, tb = sys.exc_info()
            traceback.print_exception(etype, value, tb)
            raise RuntimeError(f"Could not load dynamic library: {library}")

        self.kwargs = kwargs
        path = os.getcwd()

        if "__version__" in kwargs:
            self.__version__ = kwargs["__version__"]

        if not rank:
            logging.info("Working in {}".format(path))
            logging.info("Creating i/o directories")

            if not os.path.exists(kwargs["traj"]["dir"]):
                os.makedirs(kwargs["traj"]["dir"])

            if kwargs["restart"]:
                if not os.path.exists(kwargs["restart"][1]):
                    os.makedirs(kwargs["restart"][1])

            logging.info("Instantiated DEMPy object")

    def load_library(self, library):
        """Function for loading library file.

        :param file: input filename
        :type file: str

        """
        raise NotImplementedError

    def load_file(self, file):
        """Function for loading input file scripts to executables.

        :param file: input filename
        :type file: str

        """
        raise NotImplementedError

    def command(self, cmd):
        """Function for executing a line command

        :param cmd: input LIGGGHTS command
        :type cmd: str

        """
        raise NotImplementedError

    def get_variable(self, name):
        raise NotImplementedError

    def set_variable(self, name, value):
        raise NotImplementedError

    def get_natoms(self):
        raise NotImplementedError

    def scatter_atoms(self, name, type, count, data):
        return self.lmp.scatter_atoms(name, type, count, data)

    def gather_atoms(self, name, type, count):
        return self.lmp.gather_atoms(name, type, count)

    def insert(self, species, value, **kwargs) -> str:
        """
        This function inserts particles, and assigns particle velocities if requested by the user. If species is 'all',
        all components specified in SS are inserted. Otherwise, species must be the id of the component to be inserted.
        For available region shapes, see `ref <https://www.cfdem.com/media/DEM/docu/region.html>`_. The default region is
        the whole system.

        :param species: species id ('all', or 1, 2, ... )
        :type param: int or str

        :param value: number of particles, or volume fraction, or mass fraction, or etc.
        :type value: float

        :param region: define region via ('shape', (xmin, xmax, ymin, ymax, zmin, zmax)) or ('shape', xmin, xmax, ymin, ymax, zmin, zmax)
        :type region: tuple

        .. todo:: Support insertion of all or multiple species at the same time for multiple regions.
        """
        raise NotImplementedError

    def importMeshes(self, name=None):
        """Imports all meshes and sets them up as walls. Can import only one mesh specified by the 'name' keyword.
        @file: mesh filename
        @mtype: mesh type
        @args: additional args
        """
        raise NotImplementedError

    def importMesh(self, name, file, mtype, material, **args):
        """
        Imports a specific surface mesh requested by the user
        """
        raise NotImplementedError

    ### Constructor/destructor methods
    def remove(self, name) -> bool:
        """
        Deletes a specified fix. If the fix is for a mesh, we must unfix it and re-import all meshes again and setup them
        up as walls. Very tedious!
        """
        raise NotImplementedError

    def createGroup(self, *group) -> bool:
        """Create groups of atoms. If group is empty, groups{i} are created for every i species."""
        raise NotImplementedError

    def createParticles(self, type, style, *args) -> bool:
        """
        Creates particles of type 'type' (1,2, ...) using style 'style' (box or region or single or random)
        @[args]: 'basis' or 'remap' or 'units' or 'all_in'
        """
        raise NotImplementedError

    def createProperty(self, name, *args):
        """
        Material and interaction properties required
        """
        raise NotImplementedError

    ### Setup methods
    def initialize(self, **kwargs):
        """..."""
        raise NotImplementedError

    def setupParticles(self):
        """Setup particle for insertion if requested by the user"""
        raise NotImplementedError

    def resume(self):
        """..."""
        rdir = "{}/*".format(self.pargs["restart"][1])

        if self.pargs["restart"][-1]:
            rfile = self.pargs["restart"][1] + "/" + self.pargs["restart"][-1]
        else:
            rfile = max(glob.iglob(rdir), key=os.path.getctime)

        return rfile

    def set(self, *args):
        """Set group/atom attributes"""
        raise NotImplementedError

    def setupWall(self, wtype, species=None, plane=None, peq=None) -> str:
        """
        Creates a wall
        @ wtype: type of the wall (primitive or mesh)
        @ plane: x, y, or z plane for primitive walls
        @ peq: plane equation for primitive walls

        This function can be called only ONCE for setting up all mesh walls (restriction from LIGGGHTS)

        .. todo:: Support additional keywords (shear, etc.) for primitive walls
        """
        raise NotImplementedError

    def setupPrint(self):
        """
        Specify which variables to write to file, and their format
        """
        if not self.rank:
            logging.info("Setting up printing options")

    def setupWrite(self, only_mesh=False, name=None):
        """
        This creates dumps for particles and meshes in the system. In LIGGGHTS, all meshes must be declared once, so if a mesh is removed during
        the simulation, this function has to be called again, usually with only_mesh=True to keep the particle dump intact.
        """
        raise NotImplementedError

    def setupPotential(self):
        """
        Specify the interation forces
        """
        raise NotImplementedError

    def setupIntegrate(self, itype=None, group=None) -> List[str]:
        """
        Specify how Newton's eqs are integrated in time. MUST BE EXECUTED ONLY ONCE.
        .. todo:: Extend this to super-quadric particles

        Returns list of integrator names.
        """
        raise NotImplementedError

    ### Dynamical methods
    def run(self, nsteps, dt=None, itype=None):
        """Runs a simulation for number of steps specified by the user

        :param nsteps: number of steps the integrator should take
        :type nsteps: int

        :param itype: specifies integrator type: 'sphere' (rotational motion on) or 'rigid_sphere' (rotational motion off)
        :type itype: str

        :param dt: timestep
        :type dt: float
        """

        name = self.setupIntegrate(itype=itype)

        if not dt:
            if "dt" in self.pargs:
                dt = self.pargs["dt"]
            else:
                if not self.rank:
                    print("Could not find dt in user-supplied dictionary. Aborting ...")
                sys.exit()

        self.integrate(nsteps, dt)

        # See if any variables were set to be monitered by the user
        if self._monitor:
            for vname, fname in self._monitor:
                getattr(self, vname).append(np.loadtxt(fname))

        return name

    def moveMesh(self, name, **args):
        """Control how a mesh (specified by name) moves in time

        @name: string specifying mesh ID/name
        @args: keywords specific to LIGGGHTS's move/mesh command: https://www.cfdem.com/media/DEM/docu/fix_move_mesh.html
        """
        raise NotImplementedError

    def applyVelocity(self, *args):
        """
        Assigns velocity to selected particles.
        :param args: group-ID style args keyword value
        :type args: tuple

        :note: See `link <https://www.cfdem.com/media/DEM/docu/velocity.html>`_
               for info on keywords and their associated values.
        """
        raise NotImplementedError

    def applyForce(self):
        """
        Specify in which direction the gravitational force acts
        """
        raise NotImplementedError

    def integrate(self, steps, dt=None):
        """
        Run simulation in time
        """
        if not self.rank:
            logging.info("Integrating the system for {} steps".format(steps))

        for tup in self.monitorList:
            self.lmp.command("compute {} {} {}".format(*tup))

        if dt is not None:
            self.lmp.command("timestep {}".format(dt))

        self.lmp.command("run {}".format(steps))

    ### Extraction methods
    def extractCoords(self):
        """
        Extracts atomic positions from a certian frame and adds it to coords
        """
        raise NotImplementedError

    def extractVelocities(self):
        """
        Extracts atomic positions from a certian frame and adds it to coords
        """
        raise NotImplementedError

    def extractForces(self):
        """
        Extracts atomic positions from a certian frame and adds it to coords
        """
        raise NotImplementedError

    ### Misc methods
    def readData(self):
        raise NotImplementedError

    def close(self):
        pass

    def __del__(self):
        """Destructor"""
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass
