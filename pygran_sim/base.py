"""
A module that provides contact models for running numerical experiments or DEM simulation

Created on July 1, 2016

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

.. warning::
   Only particle-wall collisions are supported

.. todo::
  Support 2-particle analysis by replacing mass, radius, etc. with 
  reduced mass, radius, etc. i.e. :math:`1/m_{ij} = 1/m_i + 1/m_j`

"""
import os


try:
    from mpi4py import MPI
except Exception:
    MPI = None


class ProtoInput:
    """Input prototype class for engine params. It can be used to run a DEM simulation (e.g. with LIGGGHTS)
    for simulating particle-wall collisions.

    :param mesh: a dictionary that defines all meshes and their properties
    :type mesh: dict

    :param box: simulation box size boundaries (xmin, xmax, ymin, ymax, zmin, zmax)
    :type box: tuple

    :param restart: specify restart options via (freq=int, dirname=str, filename=str, restart=bool, frame=int)
    :type restart: tuple

    :param nSim: number of concurrent simulations to run (default 1)
    :type nSim: int

    :param units: unit system (default 'si'). See `here <https://www.cfdem.com/media/DEM/docu/units.html>`_ for available options.
    :type units: str

    :param comm: MPI communicator (default COMM_WORLD)
    :type comm: MPI Intracomm

    :param rank: processor rank
    :type rank: int

    :param debug: set debug mode on (default False)
    :type debug: bool

    :param engine: DEM engine (default 'engine_liggghts')
    :type engine: str

    :param species: defines the number and properties of all species
    :type species: tuple

    .. todo:: Support particle-particle collisions
    """

    def __init__(self, **kwargs):

        self.kwargs = kwargs
        self.kwargs["nSS"] = 0
        self.JKR = False  # Assume JKR cohesion model is by default OFF
        self.limitForce = (
            True  # for visco-elastic models, make sure the attractive force
        )
        # at the end of the contact is ZERO.
        self.deltaf = 0  # when to end contact

        if "debug" in kwargs:
            self._debug = kwargs["debug"]
        else:
            self._debug = False

        if "engine" not in self.kwargs:
            self.kwargs["engine"] = "pygran_sim.engine.liggghts.engine_liggghts"

        if "species" in self.kwargs:
            self.kwargs["nSS"] += len(self.kwargs["species"])

        idc = 1

        if "species" in self.kwargs:
            for ss in self.kwargs["species"]:

                if "id" not in ss:
                    ss["id"] = idc
                    idc += 1

        # Treat any mesh as an additional component
        if "mesh" in self.kwargs:
            for mesh in self.kwargs["mesh"]:

                # Make sure only mesh keywords supplied with files are counter, otherwise, they're args to the mesh wall!
                if "file" in self.kwargs["mesh"][mesh]:
                    self.kwargs["species"] += (
                        {"material": self.kwargs["mesh"][mesh]["material"]},
                    )
                    self.kwargs["nSS"] += 1

                    # Get absolute path filename
                    self.kwargs["mesh"][mesh]["file"] = os.path.abspath(
                        self.kwargs["mesh"][mesh]["file"]
                    )

                    # By default all meshes are imported
                    if "import" not in self.kwargs["mesh"][mesh]:
                        self.kwargs["mesh"][mesh]["import"] = True

                    if "id" not in self.kwargs["mesh"][mesh]:
                        self.kwargs["mesh"][mesh]["id"] = idc
                        idc += 1

                    if "args" not in self.kwargs["mesh"][mesh]:
                        self.kwargs["mesh"][mesh]["args"] = ()

        if "units" not in self.kwargs:
            self.kwargs["units"] = "si"

        if "box" in self.kwargs:
            self.kwargs["dim"] = int(len(self.kwargs["box"]) / 2)
        elif "cylinder" in self.kwargs:
            self.kwargs["dim"] = 3

        if "nns_type" not in self.kwargs:
            self.kwargs["nns_type"] = "bin"

        if "restart" not in self.kwargs:
            self.kwargs["restart"] = (5000, "restart", "restart.binary", False, None)

        if "dump_modify" not in self.kwargs:
            self.kwargs["dump_modify"] = ("append", "yes")

        if "nSim" not in self.kwargs:
            self.kwargs["nSim"] = 1

        if "read_data" not in self.kwargs:
            self.kwargs["read_data"] = False

        self.materials = {}

        # Expand material properties based on number of components
        if "species" in self.kwargs:
            for ss in self.kwargs["species"]:

                if "style" not in ss:
                    ss["style"] = "sphere"  # treat walls as spheres

                # See if we're running PyGran in multi-mode, them reduce lists to floats/ints
                if self.kwargs["nSim"] > 1:

                    if not MPI:
                        raise ModuleNotFoundError(
                            "You must have mpi4py and an MPI library installed to set nSim > 1."
                        )
                    # Make sure total number of colors <= total number of cores
                    if self.kwargs["nSim"] > MPI.COMM_WORLD.Get_size():
                        raise ValueError(
                            "Total number of simulations cannot exceed the number of allocated cores."
                        )

                    rank = MPI.COMM_WORLD.Get_rank()

                    # Get color of each rank
                    pProcs = MPI.COMM_WORLD.Get_size() // self.kwargs["nSim"]
                    for i in range(self.kwargs["nSim"]):
                        if rank < pProcs * (i + 1):
                            self.color = i
                            break
                        else:
                            # In case of odd number of procs, place the one left on the last communicator
                            self.color = self.kwargs["nSim"]
