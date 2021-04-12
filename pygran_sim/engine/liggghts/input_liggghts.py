"""
A module that provides input models for running DEM simulation with LIGGGHTS

Created on April 11, 2021

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
"""

from pygran_sim.base import ProtoInput
from pygran_sim.tools import pygranToLIGGGHTS
import math


def template_tablet(nspheres, radius, length):
    """This function creates a multi-sphere tablet (cylinder) of
    radius "radius" and height "length" constituting "nspheres" spheres.
    This is used for multisphere simulations.

    .. todo:: Move this function elsewhere.

    :param nspheres: number of spheres each tablet consists of
    :type nspheres: int
    :param radius: particle radius
    :type radius: float
    :param length: length of the tablet
    :type length: float

    :return: DEM representation of the tablet
    :rtype: tuple
    """

    delta = (2 * radius * nspheres - length) / (nspheres - 1)
    ms = ("nspheres {}".format(nspheres), "ntry 1000000 spheres")

    for i in range(nspheres):
        ms = ms + ((2 * radius - delta) * i, 0, 0, radius)

    ms = ms + ("type 1",)

    return ms


def template_multisphere(func):
    """This function creates a generic multi-sphere particle
    based on a user-supplied function.

    :param func: returns a list of tuples: [(x1,y1,z1,radius1), ...]
    :type func: function
    """

    parts = func()
    nspheres = len(parts)
    ms = ("nspheres {}".format(nspheres), "ntry 1000000 spheres")

    for part in parts:
        ms = ms + part

    ms = ms + ("type 1",)

    return ms


class LIGGGHTSInput(ProtoInput):
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        if "species" in self.kwargs:
            for ss in self.kwargs["species"]:

                if self.kwargs["nSim"] > 1:
                    # Make sure this is not a wall
                    if "radius" in ss:

                        if isinstance(ss["material"], list):
                            ss["material"] = ss["material"][self.color]

                        if isinstance(ss["radius"], list):
                            ss["radius"] = ss["radius"][self.color]

                        if ss["style"] == "multisphere/tablet":

                            # user might have defined the length and nspheres or maybe just passed args
                            if "length" in ss:
                                if isinstance(ss["length"], list):
                                    ss["length"] = ss["length"][self.color]

                            if "nspheres" in ss:
                                if isinstance(ss["nspheres"], list):
                                    ss["nspheres"] = ss["nspheres"][self.color]

                            if "args" in ss:
                                if "length" in ss or "nspheres" in ss:
                                    raise ValueError(
                                        "args cannot be defined along with nspheres/length for multisphere."
                                    )
                                elif isinstance(ss["args"], list):
                                    ss["args"] = ss["args"][self.color]
                        elif ss["style"] == "multisphere":
                            raise NotImplementedError(
                                "SSMP mode not yet supported for a custom multisphere class."
                            )

                ss["material"] = pygranToLIGGGHTS(**ss["material"])

                if ss["style"] == "multisphere/tablet":
                    # Now we can treat this as if it's a general multisphere case
                    ss["style"] = "multisphere"
                    if "args" not in ss:
                        if (
                            "nspheres" not in ss
                            or "radius" not in ss
                            or "length" not in ss
                        ):
                            raise ValueError(
                                "With multisphere/tablet, nspheres, radius, and length must be supplied."
                            )
                        ss["args"] = template_tablet(
                            ss["nspheres"], ss["radius"], ss["length"]
                        )
                        del ss["radius"], ss["length"]

                elif ss["style"] == "multisphere" and "args" not in ss:
                    if "function" not in ss:
                        raise ValueError(
                            'style multisphere requires "function" definition.'
                        )
                    ss["args"] = template_multisphere(ss["function"])

            # Use 1st component to find all material params ~ hackish!!!
            ss = self.kwargs["species"][0]

            if "material" in ss:
                for item in ss["material"]:
                    if not isinstance(ss["material"][item], float):
                        # register each material proprety then populate per number of components
                        if ss["material"][item][1] == "peratomtype":
                            self.materials[item] = ss["material"][item][:2]
                        elif ss["material"][item][1] == "peratomtypepair":
                            self.materials[item] = ss["material"][item][:2] + (
                                "{}".format(self.kwargs["nSS"]),
                            )
                        elif ss["material"][item][1] == "scalar":
                            self.materials[item] = ss["material"][item][:2]

            for ss in self.kwargs["species"]:
                for item in ss["material"]:
                    if isinstance(ss["material"][item], float):

                        # This is for running DEM sim
                        ss[item] = ss["material"][item]

            for item in self.materials:
                if not isinstance(ss["material"][item], float):

                    for ss in self.kwargs["species"]:

                        if ss["material"][item][1] == "peratomtype":
                            self.materials[item] = self.materials[item] + (
                                ("{}").format(ss["material"][item][2]),
                            )

                        elif ss["material"][item][1] == "peratomtypepair":
                            # assume the geometric mean suffices for estimating binary properties
                            for nss in range(self.kwargs["nSS"]):

                                prop = math.sqrt(
                                    float(ss["material"][item][2])
                                    * float(
                                        self.kwargs["species"][nss]["material"][item][2]
                                    )
                                )
                                self.materials[item] = self.materials[item] + (
                                    ("{}").format(prop),
                                )

                        # we should set this based on species type
                        elif ss["material"][item][1] == "scalar":
                            self.materials[item] = self.materials[item] + (
                                ("{}").format(ss["material"][item][2]),
                            )

                        else:
                            raise ValueError("Error: Material database flawed.")

            self.kwargs["materials"] = self.materials

        # Default traj I/O args
        ms = False
        if "species" in self.kwargs:
            for ss in self.kwargs["species"]:
                if ss["style"].startswith("multisphere"):
                    ms = True

        # default traj args
        traj = {
            "sel": "all",
            "freq": 1000,
            "dir": "traj",
            "style": "custom",
            "pfile": "traj.dump",
            "args": (
                "id",
                "type",
                "x",
                "y",
                "z",
                "radius",
                "vx",
                "vy",
                "vz",
                "fx",
                "fy",
                "fz",
            ),
        }

        traj.update(self.kwargs["traj"])
        self.kwargs["traj"] = traj
        
        if "style" not in self.kwargs:
            self.kwargs["style"] = "sphere"

        if ms:
            if "args" in self.kwargs["traj"]:
                if "mol" not in self.kwargs["traj"]["args"]:
                    self.kwargs["traj"]["args"] = self.kwargs["traj"]["args"] + ("mol",)

        # Need to generalize this: April 11, 2021
        if "dt" not in self.kwargs:
            # Estimate the allowed sim timestep
            try:
                self.kwargs["dt"] = (0.25 * self.contactTime()).min()
            except Exception:
                self.kwargs["dt"] = 1e-6

                if "model" in self.kwargs:
                    print(
                        "Model {} does not yet support estimation of contact period. Using a default value of {}".format(
                            self.kwargs["model"], self.kwargs["dt"]
                        )
                    )


class SpringDashpot(LIGGGHTSInput):
    """
    A class that implements the linear spring model for granular materials

    :param material: a python dictionary that specifies the material properties
    :type material: dict
    :param limitForce: turns on a limitation on the force, preventing it from becoming attractive at the end of a contact
    :type limitForce: bool
    """

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        # the order is very imp in model-args ~ stupid LIGGGHTS!
        if "model-args" not in self.kwargs:
            self.kwargs["model-args"] = ("gran", "model hooke", "tangential history")

        if "cohesionEnergyDensity" in self.kwargs["materials"]:
            self.kwargs["model-args"] = self.kwargs["model-args"] + ("cohesion sjkr",)

        self.kwargs["model-args"] = self.kwargs["model-args"] + (
            "tangential_damping on",
            "ktToKnUser on",
            "limitForce on",
        )  # the order matters here
