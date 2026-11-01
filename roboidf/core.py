"""Discrete scalar mass/damper reference model and auditable offline workflow."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import random

class IdentificationError(ValueError):
    """Identification could not produce a physically admissible model."""

@dataclass(frozen=True)
class Parameters:
    mass: float = 2.0
    damping: float = 0.4

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.mass, self.damping)) or self.mass <= 0 or self.damping < 0:
            raise ValueError('mass must be positive; damping nonnegative; both finite')

@dataclass(frozen=True)
class Dataset:
    dt: float
    velocity: tuple[float, ...]
    effort: tuple[float, ...]
    split: str
    seed: int

    def __post_init__(self):
        object.__setattr__(self, 'velocity', tuple(self.velocity))
        object.__setattr__(self, 'effort', tuple(self.effort))
        if not math.isfinite(self.dt) or self.dt <= 0:
            raise ValueError('dt must be positive and finite')
        if len(self.effort) < 3 or len(self.velocity) != len(self.effort)+1:
            raise ValueError('need N efforts and N+1 velocities, N >= 3')
        if self.split not in ('train','validation','test'):
            raise ValueError('unknown split')
        if not all(math.isfinite(x) for x in (*self.velocity,*self.effort)):
            raise ValueError('data must be finite')

    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,allow_nan=False).encode()).hexdigest()

class MockRobot:
    """Synthetic velocity plant: Euler-discrete, force N, velocity m/s, mass kg."""
    def __init__(self, parameters=None):
        self.parameters = parameters or Parameters()

    def collect(self, *, seed, split, samples=500, dt=.02):
        if not isinstance(samples,int) or samples < 3 or samples > 100000:
            raise ValueError('samples must be in [3, 100000]')
        p=self.parameters
        if not math.isfinite(dt) or dt <= 0 or dt*p.damping/p.mass >= 2:
            raise ValueError('invalid or unstable Euler step')
        rng=random.Random(seed)
        u=tuple(rng.uniform(-4,4) for _ in range(samples))
        v=[0.0]
        for force in u:
            v.append(v[-1]+dt*(force-p.damping*v[-1])/p.mass)
        return Dataset(dt,tuple(v),u,split,seed)

def fit(data):
    """Fit acceleration = alpha*force + beta*velocity; no access to ground truth."""
    if data.split != 'train':
        raise ValueError('only training data may be fitted')
    x=data.effort; z=data.velocity[:-1]
    y=[(b-a)/data.dt for a,b in zip(data.velocity,data.velocity[1:])]
    xx=sum(a*a for a in x); zz=sum(a*a for a in z); xz=sum(a*b for a,b in zip(x,z))
    determinant=xx*zz-xz*xz
    if xx <= 1e-20 or zz <= 1e-20 or determinant <= 1e-10*xx*zz:
        raise IdentificationError('UNIDENTIFIABLE: insufficient independent excitation')
    xy=sum(a*b for a,b in zip(x,y)); zy=sum(a*b for a,b in zip(z,y))
    alpha=(xy*zz-zy*xz)/determinant
    beta=(zy*xx-xy*xz)/determinant
    if not math.isfinite(alpha) or alpha <= 0 or not math.isfinite(beta):
        raise IdentificationError('INVALID_MODEL: nonphysical coefficients')
    try:
        return Parameters(1/alpha, max(0.,-beta/alpha) if beta < 1e-12 else -beta/alpha)
    except ValueError as exc:
        raise IdentificationError('INVALID_MODEL: negative damping') from exc

def rollout_rmse(model,data):
    """Free rollout from one observed initial velocity; no teacher forcing."""
    v=data.velocity[0]; errors=[]
    for u,observed in zip(data.effort,data.velocity[1:]):
        v += data.dt*(u-model.damping*v)/model.mass
        if not math.isfinite(v):
            raise IdentificationError('INVALID_MODEL: divergent rollout')
        errors.append((v-observed)**2)
    value=math.sqrt(sum(errors)/len(errors))
    if not math.isfinite(value):
        raise IdentificationError('INVALID_MODEL: nonfinite metric')
    return value

def run_demo(seed=42):
    robot=MockRobot()
    train=robot.collect(seed=seed,split='train')
    validation=robot.collect(seed=seed+1,split='validation')
    model=fit(train)
    return {'schema_version':'m0.v1','scope':'synthetic-discrete-mass-damper',
            'status':'VALIDATED','events':['CREATED','COLLECTED','FITTED','VALIDATED'],
            'seed':seed,'validation_seed':seed+1,'train_sha256':train.digest(),
            'validation_sha256':validation.digest(),'model':asdict(model),
            'rollout_rmse_m_s':rollout_rmse(model,validation),
            'parameter_relative_error':{'mass':abs(model.mass/robot.parameters.mass-1),
                                        'damping':abs(model.damping/robot.parameters.damping-1)}}
