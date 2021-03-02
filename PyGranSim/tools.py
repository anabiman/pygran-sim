"""
  Created on April 25, 2016
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

import os
import sys


def dictToTuple(**args):
    """ Converts a dictionary (args) to a tuple 

	:param args: dictionary used mainly by liggghts API
	:type args: dict

	:Example:
	   args = {'key_1': value1, 'key_2': value2}
	   dictToTuple(**args) -> ('key_1', value1, 'key_2', value2)

	:note: If value1 is a tuple, it is broken into a string
	:Example:
	   args = {'key_1': (1,2,3)}
	   dictToTuple(**args) -> ('key_1', '1 2 3')

	:return: dictionary key/values refactored if needed
	:rtype: tuple
	"""

    keys = args.keys()
    vals = args.values()

    tup = ()
    for pair in zip(keys, vals):
        if isinstance(pair[1], tuple):
            pair = (pair[0], ("{} " * len(pair[1])).format(*pair[1]).strip())
        tup = tup + pair

    return tup


def pygranToLIGGGHTS(**material):
    """ Transform a PyGran material database into a LIGGGHTS material dictionary

	:param material: definition of material(s) used mainly by liggghts API
	:type material: dict

	return: definition of material(s) in LIGGGHTS-compatible format
	:rtype: dict
 	"""

    for key in material:
        if key is "youngsModulus" or key is "poissonsRatio" or key is "yieldPress":
            material[key] = (key, "peratomtype", str(material[key]))
        elif (
            key is "coefficientFriction"
            or key is "coefficientRollingFriction"
            or key is "cohesionEnergyDensity"
            or key is "coefficientRestitution"
            or key is "coefficientRollingViscousDamping"
        ):
            material[key] = (key, "peratomtypepair", str(material[key]))
        elif key is "characteristicVelocity":
            material[key] = (key, "scalar", str(material[key]))

    return material


def find(fname, path):
    """ Finds a filename (fname) along the path `path' 

	:param fname: filename
	:type fname: str

	:param path: search path
	:type path: str

	:return: absolute path of the fname if found, else None
	:rtype: str/None
	"""
    for root, dirs, files in os.walk(path):
        if fname in files:
            return os.path.join(root, fname)

    return None


def run(program):
    """ Unix only: launches an executable program available in the PATH environment variable.

	:param program: name of the executable to search for
	:type program: str

	:return: 0 if successful and 1 otherwise
	:rtype: bool
	 """
    paths = os.environ["PATH"]

    for path in paths.split(":"):
        found = Tools.find(program, path)

        if found:
            print("Launching {}".format(found))
            os.system(found + " &")
            return 0

    print("Could not find {} in {}".format(program, paths))
    return 1


def configure(path, version=None, src=None):
    """ Configures PyGran to use a specific DEM/engine library

	:param path: path to library
	:type path: str

	:param version: a set of numbers and/or characters indicating the version of the library, e.g. 1.5a
	:type version: str

	:param src: path to library source code
	:type src: str
	 """
    _setLIGGGHTS(path, version, src)


def _setLIGGGHTS(path, version=None, src=None):
    """ Write libliggghts path to ~/.config/liggghts.ini file

        :param path: path to LIGGGHTS library
        :type path: str

        :param version: a set of numbers and/or characters indicating the version of the library, e.g. 1.5a
        :type version: str

        :param src: path to LIGGGHTS source code
        :type src: str
	"""

    _configdir = os.path.join(os.path.expanduser("~"), ".config", "PyGran")
    liggghts_ini = os.path.join(_configdir, "liggghts.ini")

    with open(liggghts_ini, "w") as fp:

        fp.seek(0, 0)
        fp.write("library=" + path)

        if src:
            fp.write("\nsrc=" + src)

        if version:
            fp.write("\nversion=" + version)


def _findEngines(engine):
    """ Searches for and lists all available libraries for a specific engine

	:param engine: DEM engine specification
	:type engine: str

	:return: all DEM engines found on the system
	:rtype: list
	 """

    engines = [
        os.path.join(root, engine)
        for root, dirs, files in os.walk("/")
        if engine in files
    ]

    if engines:
        print("Engine(s) found:")
        for engine in engines:
            print(engine)
    else:
        print("No engines found.")

    return engines


def _setConfig(wdir, engine):
    """ Reads/writes DEM library to config .ini file

	:param wdir: working directory
	:type wdir: str

	:param engine: DEM engine specification
	:type engine: str

	:return: path to library, source, and version of DEM library
	:rtype: tuple

	.. todo: Make this function platform and liggghts independent
	"""
    library, src, version = "", None, None

    _configdir = os.path.join(os.path.expanduser("~"), ".config", "PyGran")
    liggghts_ini = os.path.join(_configdir, "liggghts.ini")

    # Make sure ~/.config/PyGran dir exists else create it
    if not os.path.isdir(_configdir):
        if not os.path.isdir(os.path.join(os.path.expanduser("~"), ".config")):
            os.mkdir(os.path.join(os.path.expanduser("~"), ".config"))
        os.mkdir(_configdir)

    if os.path.isfile(liggghts_ini):

        if os.stat(liggghts_ini).st_size:  # file not empty

            with open(liggghts_ini, "r+") as fp:  # r+ is for reading and writing
                for line in fp.readlines():
                    if "library=" in line:
                        library = line.split("=")[-1].rstrip()
                    elif "src" in line:
                        src = line.split("=")[-1].rstrip()
                    elif "version" in line:
                        version = float(line.split("=")[-1].rstrip())

            # Make sure the library exists; else, find it somewhere else
            if not os.path.isfile(library):
                library = find("lib" + engine + ".so", "/")
                _setLIGGGHTS(library)
                print(
                    "WARNING: Could not find user-specified library. Will use {} instead ...".format(
                        library
                    )
                )

            return library, src, version

    with open(liggghts_ini, "w") as fp:
        library = find("lib" + engine + ".so", "/")

        if library:
            print(
                "No config file found. Creating one for {} in {}".format(
                    library, os.path.abspath(liggghts_ini)
                )
            )
            _setLIGGGHTS(library)
        else:
            print(
                "No installation of {} was found. Make sure your selected DEM engine is properly installed first.".format(
                    engine
                )
            )
            print(
                "PyGran looked for "
                + "lib"
                + engine
                + ".so"
                + ". If the file exists, make sure it can be executed by the user."
            )
            sys.exit()

    return library, src, version
