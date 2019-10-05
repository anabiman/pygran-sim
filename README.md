# Welcome to the PyGranSim webpage!

PyGranSim is part of the PyGran project, an open-source toolkit primarily designed for analyzing DEM simulation data. In addition to performing basic and custom post-processing, PyGran enables running DEM simulation with the PyGranSim module. For more info on PyGran, see [here](http://www.pygran.org).

**If your find PyGran useful in your research, please consider citing the following paper:**

[![DOI for Citing PyGran](https://img.shields.io/badge/DOI-10.1021%2Facs.jctc.5b00056-blue.svg)](https://doi.org/10.1016/j.softx.2019.01.016)

```
@article{aam2019pygran,
  title={PyGran: An object-oriented library for DEM simulation and analysis},
  author={Abi-Mansour, Andrew},
  journal={SoftwareX},
  volume={9},
  pages={168--174},
  year={2019},
  publisher={Elsevier},
  doi={10.1016/j.softx.2019.01.016}
}
```

## Quick Installation
PyGranSim is typically installed with other PyGran submodules. See [here](http://andrew-abimansour.github.io/PyGran/docs/introduction.html#installation) for more info. For a solo PyGranSim local installation, simply clone this repository and then use pip (or pip3) to run from the source dir:
```bash
pip install . --user
```
You can alternatively run ``setup.py`` to build and/install the package. See ``setup.py -h`` for more info.


## Basic Usage
PyGranSim provides an interface for running DEM simulation with [LIGGGHTS](https://www.cfdem.com/liggghtsr-open-source-discrete-element-method-particle-simulation-code). This is achieved by importing the <i>simulation</i> module as shown in the script below for simulating granular flow in a hopper.

<p style="text-align:center;"><img src="http://andrew-abimansour.github.io/PyGran/images/hopper.png" width="600"></p>

```python
import PyGranSim as simulation
from PyGranParams import organic

# Create a DEM parameter dictionary
param = {

	'model': simulation.models.SpringDashpot,
	'boundary': ('f','f','f'),
	'box':  (-1e-3, 1e-3, -1e-3, 1e-3, 0, 4e-3),

	'species': ({'material': params.stearicAcid, 'radius': 5e-5,}, 
		),
		
	'gravity': (9.81, 0, 0, -1),

	'mesh': { 'hopper': {'file': 'silo.stl', 'mtype': 'mesh/surface', \
		'material': params.steel}, },
}

# Instantiate a DEM class
sim = simulation.DEM(**param['model'])

# Insert 1000 particles for species 1 (stearic acid)
insert = sim.insert(species=1, value=1000) 

# Evolve the system in time 
sim.run(nsteps=1e6, dt=1e-6)
```

For more examples on using PyGranSim for running DEM simulation, check out the <a href="http://andrew-abimansour.github.io/PyGran/tests/examples.html">examples</a> page.
