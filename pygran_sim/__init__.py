"""
Created on March 30, 2016
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

Core developer and main author
Andrew Abi-Mansour, andrew.abi.mansour@pygran.org

PyGran is open-source, distributed under the terms of the GNU Public
License, version 2 or later. It is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. You should have
received a copy of the GNU General Public License along with PyGran.
If not, see http://www.gnu.org/licenses . See also top-level README
and LICENSE files.
"""

# Handle versioneer
from ._version import get_versions

versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions

import glob
import os
import pathlib

from . import engine
from .dem import *


class _findEngines:
    """Any engine module *must* follow the naming convention: engine_foo.py
    If engine `foo` is found, it will be linked via setattr to be imported
    in DEM.py as PyGranSim.engine_foo. The engine is set by the user
    as DEM.simulation.engines.foo."""

    def __init__(self):
        _dir, _ = __file__.split("__init__.py")
        engine_paths = glob.glob(os.path.join(_dir, "engine", "*"))

        for engine_path in engine_paths:
            if os.path.isdir(engine_path):
                posixPath = pathlib.Path(engine_path)
                name = posixPath.name
                setattr(self, name, f"pygran_sim.engine.{name}.engine_{name}")


engines = _findEngines()
