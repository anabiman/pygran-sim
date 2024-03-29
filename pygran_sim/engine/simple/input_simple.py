"""
A module that provides contact models for running numerical experiments

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

.. warning::
   Only particle-wall collisions are supported

.. todo::
  Support 2-particle analysis by replacing mass, radius, etc. with 
  reduced mass, radius, etc. i.e. :math:`1/m_{ij} = 1/m_i + 1/m_j`

"""
import numpy as np
from scipy.integrate import ode
from scipy.optimize import fsolve

from pygran_sim.base import ProtoInput


class ContactModel(ProtoInput):
    def __init__(self, **kwargs):

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

        if "traj" in kwargs:
            # override default with user-def params
            traj.update(kwargs["traj"])

        kwargs["traj"] = traj
        super().__init__(**kwargs)

    def contactTime(self):
        """Computes the characteristic collision time assuming for a spring dashpot model

        :return: the contact time
        :rtype: float
        """

        if not hasattr(self, "coefficientRestitution"):
            rest = 0.9
        else:
            rest = self.coefficientRestitution

        radius = self.radius
        mass = self.mass

        # Create SpringDashpot instance to etimate contact time
        SD = SpringDashpot(material=self.materials)

        kn = SD.springStiff(radius)

        return np.sqrt(mass * (np.pi**2.0 + np.log(rest) ** 2) / kn)

    def displacement(self, dt=None):
        """Generator that computes (iteratively) the overlap distance (displacement) as a function of time

        :param dt: timestep used by the ODE integrator, by default it is 0.1% of contact duration
        :type dt: float
        :return: time, displacement, and force as numpy arrays
        :rtype: tuple

        .. todo:: Enable the user control the timestep resolution (number of timesteps).
        """

        if not hasattr(self, "characteristicVelocity"):
            self.characteristicVelocity = 0.1

        y0 = np.array([0, self.characteristicVelocity])
        t0 = 0.0

        inte = ode(self.numericalForce)
        inte.set_f_params(*())
        inte.set_integrator("dopri5")
        inte.set_initial_value(y0, t0)

        Tc = self.contactTime() * 2

        if not dt:
            dt = Tc / 1000

        time, delta, force = [], [], []
        self._contRadius = []

        def generator():
            while inte.successful() and (inte.t <= Tc):
                inte.integrate(inte.t + dt)

                yield inte.t + dt, inte.y, self.normalForce(inte.y[0], inte.y[1])

        for t, soln, f in generator():

            if soln[0] <= self.deltaf:
                break

            time.append(t)
            delta.append(soln)
            force.append(f)

            # for hysteretic models
            if hasattr(self, "maxDisp"):
                if soln[0] < self.maxDisp and self.contRadius >= self.radiusy:
                    self.unloading = True
                else:
                    self.maxDisp = soln[0]

            # for hysteretic models
            if hasattr(self, "maxForce"):
                self.maxForce = max(f, self.maxForce)

        time, delta, force = np.array(time), np.array(delta), np.array(force)

        if hasattr(self, "limitForce"):
            if self.limitForce:
                index = np.where(force < 0)

                if len(index[0]):
                    index = index[0][0]
                else:
                    index = -1

                delta = delta[:index]
                time = time[:index]
                force = force[:index]

        return time, delta, force

    @property
    def contactRadius(self):
        """Returns the contact radius.

        :return: contact radius
        :rtype: numpy array

        .. note:: This function is *not* useful since self._contRadius is not updated anywhere.

        """
        return np.array(self._contRadius)

    def _contactRadius(self, delta, radius):
        """Internal function that computes the contact radius for Hertzian and JKR models

        :param delta: normal displacement
        :type delta: float
        :param radius: effective radius
        :type radius: float
        :return: contact radius
        :rtype: float
        """

        if self.JKR:
            if hasattr(self, "cohesionEnergyDensity"):
                Gamma = self.cohesionEnergyDensity

                poiss = self.poissonsRatio
                yMod = self.youngsModulus
                yMod /= 2.0 * (1.0 - poiss**2)

                # def jkr_disp(a, *args):
                # 	delta, Gamma, yMod, radius = args
                # 	return delta - a**4.0/radius + np.sqrt(2.0 * np.pi * Gamma / yMod) * a

                # def jkr_jacob(a, *args):
                # 	_, Gamma, yMod, radius = args
                # 	return - 4.0 * a**3/radius + np.sqrt(np.pi * Gamma / (a * 2.0 * yMod))

                def contactRadius_symbolic(deltan, *args):
                    gamma, yeff, reffr = args

                    c0 = reffr * reffr * deltan * deltan
                    c1 = -4.0 / yeff * np.pi * gamma * reffr * reffr
                    c2 = -2.0 * reffr * deltan
                    P1 = -c2 * c2 / 12.0 - c0
                    Q1 = -c2 * c2 * c2 / 108.0 + c0 * c2 / 3.0 - c1 * c1 / 8.0
                    U1s = Q1 * Q1 / 4.0 + P1 * P1 * P1 / 27.0
                    U1 = (
                        (-Q1 / 2.0 + np.sqrt(U1s)) ** (1.0 / 3.0)
                        if U1s > 0
                        else (-Q1 / 2.0) ** (1.0 / 3.0)
                    )

                    s1 = (
                        -5.0 / 6.0 * c2 + U1 - P1 / (3.0 * U1)
                        if deltan != 0
                        else -5.0 / 6.0 * c2 - (Q1) ** (1.0 / 3.0)
                    )
                    w1 = np.sqrt(c2 + 2.0 * s1)

                    L1 = c1 / (2.0 * w1)
                    contactRadH = 0 if np.isnan(w1) else 0.5 * w1
                    corrJKRarg = w1 * w1 - 4.0 * (c2 + s1 + L1)
                    corrJKR = 0.5 * np.sqrt(corrJKRarg)
                    contactRad = (
                        contactRadH
                        if (np.isnan(corrJKR) or corrJKR < 0)
                        else contactRadH + corrJKR
                    )

                    if not np.isreal(contactRad):
                        contactRad = np.sqrt(reffr * delta)

                    return contactRad

                # output = fsolve(jkr_disp, x0 = 0 * np.sqrt(self._contRadius), args = (delta, Gamma, yMod, radius), full_output=True, fprime = jkr_jacob)
                # contRadius = output[0]**2
                # info = output[1]
                contRadius = contactRadius_symbolic(delta, *(Gamma, yMod, radius))

                if self._debug:
                    print(info)
            else:
                contRadius = np.sqrt(delta * radius)
        else:
            contRadius = np.sqrt(delta * radius)

        return contRadius

    def dissCoef(self, delta=None):
        raise NotImplementedError("Not yet implemented")

    def springStiff(self, delta=None):
        raise NotImplementedError("Not yet implemented")

    def elasticForce(self, delta=None):
        raise NotImplementedError("Not yet implemented")

    def dissForce(self, delta=None, deltav=None):
        raise NotImplementedError("Not yet implemented")

    def normalForce(self, delta=None, deltav=None):
        raise NotImplementedError("Not yet implemented")

    def cohesiveForce(self, delta=None):
        raise NotImplementedError("Not yet implemented")

    def numericalForce(self, time, delta):
        """Returns the force used for numerical solvers"""

        force = self.normalForce(float(delta[0]), float(delta[1]))

        mass = self.mass

        return np.array([delta[1], -force / mass])

    def tangForce(self, delta=None, deltav=None):
        raise NotImplementedError("Not yet implemented")


class SpringDashpot(ContactModel):
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

        if "cohesionEnergyDensity" in self.materials:
            self.kwargs["model-args"] = self.kwargs["model-args"] + ("cohesion sjkr",)

        self.kwargs["model-args"] = self.kwargs["model-args"] + (
            "tangential_damping on",
            "ktToKnUser on",
            "limitForce on",
        )  # the order matters here

        if "limitForce" in kwargs:
            self.limitForce = self.kwargs["limitForce"]

    def springStiff(self, delta=None):
        """Computes the spring constant (:math:`k_n`) for the normal force :math:`F_n = k_n \delta_n`.

        :param delta: normal displacement (:math:`\delta_n`)
        :type delta: float
        :return: spring stiffness (:math:`k_n`)
        :rtype: float

        """
        poiss = self.poissonsRatio
        yMod = self.youngsModulus
        radius = self.radius
        mass = self.mass

        yMod /= 2.0 * (1.0 - poiss**2)

        v0 = self.characteristicVelocity

        return (
            16.0
            / 15.0
            * np.sqrt(radius)
            * yMod
            * (15.0 * mass * v0**2.0 / (16.0 * np.sqrt(radius) * yMod)) ** (1.0 / 5.0)
        )

    def dissCoef(self, delta=None):
        """Computes the normal dissipative coefficient (:math:`c_n`) for the dissipative force :math:`F_d = - c_n \dot{\delta_n}`

        :return: dissipative coefficient (:math:`c_n`)
        :rtype: float
        """
        rest = self.coefficientRestitution
        poiss = self.poissonsRatio
        yMod = self.youngsModulus

        mass = self.mass
        yMod /= 2.0 * (1.0 - poiss**2)

        kn = self.springStiff()
        loge = np.log(rest)

        return loge * np.sqrt(4.0 * mass * kn / (np.pi**2.0 + loge**2.0))

    def dissForce(self, delta, deltav):
        """Returns the dissipative (viscous) force: :math:`F_d = - c_n \dot{\delta_n}`
        where :math:`c_n` is the dissipative coefficient.

        :param delta: normal displacement
        :type delta: float
        :param deltav: time derivative of the normal displacement
        :type deltav: float

        :return: dissipative force :math:`F_d`
        :rtype: float

        """

        return self.dissCoef() * deltav

    def displacementAnalytical(self, dt=None):
        """Computes the displacement based on the analytical solution for
        a spring-dashpot model.

        :param dt: timestep. By default, the timestep is 1% of the contact time.
        :type dt: float

        :return: time, displacement, and force arrays of size :math:`N`, :math:`N` by 2, and :math:`N`, respectively, where :math:`N` is the total number of steps taken by the integrator. The displacement array stores the overlap in its 1st column and the overlap velocity (time derivative) in its 2nd column.
        :rtype: tuple

        .. todo:: Take cohesion (simplified JKR) into account
        """

        mass = self.mass

        if not dt:
            dt = 0.01 * self.contactTime()

        v0 = self.characteristicVelocity
        kn = self.springStiff()
        cn = self.dissCoef()

        time = np.arange(int(self.contactTime() / dt)) * dt
        const = np.sqrt(kn / mass - 0.25 * (cn / mass) ** 2.0)
        phase = 0

        delta = (
            v0 / const * np.exp(0.5 * cn * time / mass) * np.sin(const * time + phase)
        )
        deltav = 0.5 * cn / mass * delta + v0 * np.cos(const * time + phase) * np.exp(
            0.5 * cn * time / mass
        )

        force = self.normalForce(delta, deltav)

        if hasattr(self, "limitForce"):
            if self.limitForce:
                delta = delta[force >= 0]
                deltav = deltav[force >= 0]
                time = time[force >= 0]
                force = force[force >= 0]

        return time, np.array([delta, deltav]).T, force

    def elasticForce(self, delta):
        """Returns the elastic force based on Hooke's law: :math:`F_n = k_n \delta_n`

        :param delta: normal displacement
        :type delta: float
        :return: elastic contact force
        :rtype: float
        """

        radius = self.radius
        kn = self.springStiff(radius)

        return kn * delta

    def cohesiveForce(self, delta):
        """Returns the cohesive force :math:`F_c` (for the SJKR model)

        :param delta: normal displacement
        :type delta: float
        :return: cohesvie force
        :rtype: float
        """
        radius = self.radius

        return self.cohesionEnergyDensity * 2.0 * np.pi * delta * 2.0 * radius

    def normalForce(self, delta, deltav):
        """Returns the total normal force :math:`F_n + F_d + F_c`

        :param delta: normal displacement
        :type delta: float
        :param deltav: time derivative of the normal displacement
        :type deltav: float
        :return: total normal force
        :rtype: float
        """

        force = self.elasticForce(delta) - self.dissForce(delta, deltav)

        if hasattr(self, "cohesionEnergyDensity"):
            force -= self.cohesiveForce(delta)

        return force

    def tangForce(self, delta, deltav):
        """Returns the total tangential force based on the Coulomb model"""
        raise NotImplementedError("Not yet implemented")


class HertzMindlin(ContactModel):
    """
    A class that implements the linear spring model for granular materials
    """

    def __init__(self, **params):
        super(HertzMindlin, self).__init__(**params)

        if "model-args" not in self.params:
            self.params["model-args"] = ("gran", "model hertz", "tangential history")

            if "cohesionEnergyDensity" in self.materials:
                self.params["model-args"] = self.params["model-args"] + (
                    "cohesion sjkr",
                )

            self.params["model-args"] = self.params["model-args"] + (
                "tangential_damping on",
                "limitForce on",
            )  # the order matters here

        if "limitForce" in params:
            self.limitForce = self.params["limitForce"]

    def springStiff(self, delta):
        """Computes the spring constant :math:`k_n` for `F_n = k_n \delta_n^{3/2}`

        :param delta: normal displacement
        :type delta: float
        :return: stiffness (:math:`k_n`)
        :rtype: float

        """
        poiss = self.poissonsRatio
        yMod = self.youngsModulus
        yEff = yMod * 0.5 / (1.0 - poiss**2)

        contRadius = self._contactRadius(delta, self.radius)

        return 4.0 / 3.0 * yEff * contRadius

    def elasticForce(self, delta):
        """Returns the Hertzian elastic force :math:`F_n = k_n \delta_n^{3/2}`

        :param delta: normal displacement
        :type delta: float
        :return: elastic normal force
        :rtype: float
        """

        force = self.springStiff(delta) * delta

        return force

    def dissCoef(self, delta):
        """Returns the dissipative force coefficient

        :param delta: normal displacement
        :type delta: float
        :return: coefficient for dissipative (viscous) normal force
        :rtype: float
        """
        rest = self.coefficientRestitution
        yMod = self.youngsModulus
        poiss = self.poissonsRatio
        yEff = yMod * 0.5 / (1.0 - poiss**2)

        mass = self.mass

        contRadius = self._contactRadius(delta, self.radius)

        return (
            2.0
            * np.sqrt(5.0 / 6.0)
            * np.log(rest)
            / np.sqrt(np.log(rest) ** 2 + np.pi**2)
            * np.sqrt(mass * 2 * yEff * contRadius)
        )

    def dissForce(self, delta, deltav):
        """Returns the dissipative force

        :param delta: normal displacement
        :type delta: float
        :param deltav: time derivative of the normal displacement
        :type deltav: float

        :return: dissipative force
        :rtype: float
        """
        return self.dissCoef(delta) * deltav

    def normalForce(self, delta, deltav):
        """Returns the total normal force :math:`F_n + F_d + F_c`

        :param delta: normal displacement
        :type delta: float
        :param deltav: time derivative of the normal displacement
        :type deltav: float

        :return: total normal force
        :rtype: float
        """

        force = self.elasticForce(delta) - self.dissForce(delta, deltav)

        if hasattr(self, "cohesionEnergyDensity"):
            force -= self.cohesiveForce(delta)

        return force

    def cohesiveForce(self, delta):
        """Returns the cohesive force for the simplified JKR model

        :param delta: normal displacement
        :type delta: float
        :return: cohesive force
        :rtype: float
        """
        radius = self.radius

        return self.cohesionEnergyDensity * 2.0 * np.pi * delta * 2.0 * radius


class ThorntonNing(ContactModel):
    """
    A basic class that implements the Thornton elasto-plastic model based on :cite:`thornton1998theoretical`.
    """

    def __init__(self, **params):

        super(ThorntonNing, self).__init__(**params)
        self.JKR = True

        if "model-args" not in self.params:
            self.params["model-args"] = (
                "gran",
                "model hysteresis_coh/thorn",
                "tangential history",
            )
        else:
            self.params["model-args"] = self.params["model-args"]

        # We check for the radius 1st since it can change in this model
        if hasattr(self, "radius"):
            self.radiusy = self.computeYieldRadius()
            self.radiusp = self.radius
            self.maxDisp = 0
            self.maxForce = 0
            self.unloading = False
            self.noCheck = False

    def computeYieldRadius(self):
        """Computes the contact radius at the yield point based on Eq. (65) in :cite:`thornton1998theoretical`

        return: yielding contact radius
        rtype: float
        """

        poiss = self.poissonsRatio
        yEff = self.youngsModulus / (2.0 * (1.0 - poiss**2))
        py = self.yieldPress

        def obj(x, *args):
            func = py * x - 2 * yEff * x**3 / (np.pi * self.radius)

            if hasattr(self, "cohesionEnergyDensity"):
                func += np.sqrt(2 * self.cohesionEnergyDensity * yEff / np.pi)

            return func

        def jacob(x, *args):
            return py - 6 * yEff * x**2 / (np.pi * self.radius)

        guess = py * np.pi * self.radius / (2.0 * yEff)

        output = fsolve(obj, x0=np.sqrt(guess), args=(), full_output=True, fprime=jacob)
        contRadius = output[0][0] * output[0][0]
        info = output[1]

        if self._debug:
            print(info)

        return contRadius

    def springStiff(self, delta):
        """Computes the spring constant :math:`k_n` for `F_n = k_n \delta_n^{3/2}`

        :param delta: normal displacement
        :type delta: float
        :return: stiffness (:math:`k_n`)
        :rtype: float

        """
        poiss = self.poissonsRatio
        yMod = self.youngsModulus
        yEff = yMod * 0.5 / (1.0 - poiss**2)

        return 4.0 / 3.0 * yEff * self._contactRadius(delta, self.radius)

    def elasticForce(self, delta):
        """Returns the Hertzian-like elastic force

        :param delta: normal displacement
        :type delta: float
        :return: elastic normal force
        :rtype: float
        """

        poiss = self.poissonsRatio
        yMod = self.youngsModulus
        yEff = yMod * 0.5 / (1.0 - poiss**2)

        if self.unloading:
            if not self.noCheck:
                self.noCheck = True

                contMaxRadius = self._contactRadius(self.maxDisp, self.radius)
                factor = self.maxForce

                if hasattr(self, "cohesionEnergyDensity"):
                    factor += np.sqrt(
                        8
                        * np.pi
                        * self.cohesionEnergyDensity
                        * yEff
                        * contMaxRadius**3
                    )

                reff = self.radius
                self.radiusp = 4.0 / 3.0 * yEff * contMaxRadius**3 / self.maxForce

                # Solve for the contact radius
                # a = 4.0 * yEff / (3 * self.radiusp)

                # if hasattr(self, "cohesionEnergyDensity"):
                #    b = -np.sqrt(8.0 * np.pi * self.cohesionEnergyDensity * yEff)
                # else:
                #    b = 0

                # c = -self.maxForce

                # x = (-b + np.sqrt(b * b - 4 * a * c)) / (2 * a)
                # contRadius = x**(2.0/3.0)
                # Why am I doing this? I commented the line above. what is contRadius used for???? This seems to be equal to contMaxRadius when cohesion = off

                self.deltap = (
                    contMaxRadius * contMaxRadius * (1.0 / reff - 1.0 / self.radiusp)
                )

                if hasattr(self, "cohesionEnergyDensity"):
                    self.deltaf = (
                        -3.0
                        / 4.0
                        * (
                            np.pi**2
                            * self.cohesionEnergyDensity**2
                            * self.radiusp
                            / yEff**2
                        )
                        ** (1.0 / 3.0)
                        + self.deltap
                    )
                    self.cutoff_force = -1.5 * self.radiusp * self.cohesionEnergyDensity
                else:
                    self.deltaf = self.deltap

                # if cohesion - 0, deltap becomes:
                # self.deltap = self.maxDisp - (self.maxForce * 3 / (4. * yEff * np.sqrt(self.radius)))**(2.0/3.0)

            self.contRadius = self._contactRadius(delta - self.deltap, self.radiusp)

            force = 4.0 / 3.0 * yEff * self.contRadius**3 / self.radiusp

            return force

        self.contRadius = self._contactRadius(delta, self.radius)

        if self.contRadius < self.radiusy:

            force = 4.0 / 3.0 * yEff * self.contRadius**3 / self.radius

            return force
        else:
            force = 4.0 / 3.0 * yEff * self.radiusy**3 / self.radius

            return force

    def dissForce(self, delta, deltav=None):
        """Computes the piece-wise defined elastic force

        :param delta: normal displacement
        :type delta: float
        :param deltav: time derivative of the normal displacement
        :type deltav: float
        :return: dissipative force
        :rtype: float
        """

        py = self.yieldPress

        if self.unloading:
            return 0

        contRadius = self._contactRadius(delta, self.radius)

        if contRadius >= self.radiusy:
            return np.pi * py * (contRadius**2 - self.radiusy**2)
        else:
            return 0

    def normalForce(self, delta, deltav):
        """Returns the total normal force

        :param delta: normal displacement
        :type delta: float
        :param deltav: time derivative of the normal displacement
        :type deltav: float
        :return: total normal force
        :rtype: float

        """

        force = self.elasticForce(delta) + self.dissForce(delta, deltav)

        if hasattr(self, "cohesionEnergyDensity"):
            force -= self.cohesiveForce()

        return force

    def cohesiveForce(self, delta=None):
        """Returns the JKR cohesive force

        :param delta: useless variable kept here for syntax consistency
        :type delta: None
        :return: cohesive force
        :rtype: float
        """

        poiss = self.poissonsRatio
        yMod = self.youngsModulus
        yEff = yMod * 0.5 / (1.0 - poiss**2)

        if hasattr(self, "cohesionEnergyDensity"):
            if self.unloading:

                force = np.sqrt(
                    8 * np.pi * self.cohesionEnergyDensity * yEff * self.contRadius**3
                )
            elif self.contRadius < self.radiusy:
                force = np.sqrt(
                    8 * np.pi * self.cohesionEnergyDensity * yEff * self.contRadius**3
                )
            else:
                force = self.radiusy * np.sqrt(
                    8 * np.pi * self.cohesionEnergyDensity * yEff * self.contRadius
                )

        return force

    @property
    def yieldVel(self):
        """Returns the minimum velocity required for a colliding particle to undergo plastic deformation

        :return: yielding velocity
        :rtype: float
        """

        poiss = self.poissonsRatio
        yEff = 0.5 * self.youngsModulus / (1.0 - poiss**2)
        density = self.density
        py = self.yieldPress

        return 1.56 * np.sqrt(py**5 / (yEff**4 * density))
