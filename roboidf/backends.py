"""Bounded SciPy optimization for an offline scalar mass/damper only."""
from dataclasses import asdict, dataclass
import json
import math
import platform
from pathlib import Path
import sys
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from .core import Dataset, MockRobot, Parameters, rollout_rmse, IdentificationError

@dataclass(frozen=True)
class FitConfig:
    lower: tuple = (.2, 0.)
    upper: tuple = (20., 10.)
    initial: tuple = (1., 1.)
    max_evaluations: int = 200
    validation_rmse_limit: float = .02
    max_condition: float = 1e8

    def __post_init__(self):
        if any(len(x) != 2 for x in (self.lower, self.upper, self.initial)):
            raise ValueError('two parameter bounds required')
        values = (*self.lower, *self.upper, *self.initial, self.validation_rmse_limit, self.max_condition)
        if not all(math.isfinite(x) for x in values): raise ValueError('finite configuration required')
        if self.lower[0] <= 0 or self.lower[1] < 0 or any(not lo < x < hi for lo,x,hi in zip(self.lower,self.initial,self.upper)):
            raise ValueError('physical bounds and interior initial required')
        if type(self.max_evaluations) is not int or self.max_evaluations < 1: raise ValueError('positive integer budget required')
        if self.validation_rmse_limit <= 0 or self.max_condition <= 1: raise ValueError('invalid thresholds')

def _rollout(theta, effort, dt, initial):
    m,b = theta
    if dt*b/m >= 2: raise ValueError('unstable Euler parameters')
    v = float(initial); output = []
    for u in effort:
        v += dt*(u-b*v)/m
        output.append(v)
    return np.asarray(output)

def _diagnose(jac):
    singular = np.linalg.svd(jac, compute_uv=False)
    if not np.isfinite(singular).all(): raise FloatingPointError("nonfinite singular values")
    rank = int(np.linalg.matrix_rank(jac))
    condition = float(singular[0]/singular[-1]) if singular[-1] > 0 else None
    return {'rank': rank, 'singular_values': singular.tolist(), 'condition_number': condition}

class _BudgetExceeded(Exception): pass

def fit_bounded(train, validation, config=None):
    config = config or FitConfig()
    if (train.dt, train.velocity, train.effort) == (validation.dt, validation.velocity, validation.effort):
        raise ValueError('train and validation contents are identical')
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            return _fit_bounded(train, validation, config)
    except (FloatingPointError, OverflowError, np.linalg.LinAlgError, IdentificationError) as exc:
        return {'schema_version':'backend.v1', 'backend':'scipy.optimize.least_squares',
                'versions':{'scipy':scipy.__version__,'numpy':np.__version__,'python':platform.python_version()},
                'scope':'synthetic-discrete-scalar-mass-damper', 'status':'REJECTED',
                'failure':'NUMERICAL_FAILURE','message':str(exc),'config':asdict(config),
                'data_hashes':{'train':train.digest(),'validation':validation.digest()},
                'seeds':{'train':train.seed,'validation':validation.seed},
                'model':None,'diagnostics':{},'errors':{}}


def _fit_bounded(train, validation, config=None):
    """Fit training free rollout; validation is used only as a final rejection gate."""
    config = config or FitConfig()
    if train.split != 'train' or validation.split != 'validation': raise ValueError('train/validation split required; test forbidden')
    # Enforce stability over the entire box, not just a successful initial point.
    if max(train.dt, validation.dt)*config.upper[1]/config.lower[0] >= 2:
        raise ValueError('parameter box permits unstable Euler rollout; reduce dt/bounds')
    report = {'schema_version':'backend.v1', 'backend':'scipy.optimize.least_squares',
              'versions':{'scipy':scipy.__version__, 'numpy':np.__version__, 'python':platform.python_version()},
              'scope':'synthetic-discrete-scalar-mass-damper', 'status':'REJECTED', 'failure':None,
              'config':asdict(config), 'data_hashes':{'train':train.digest(),'validation':validation.digest()},
              'seeds':{'train':train.seed,'validation':validation.seed}, 'model':None,
              'diagnostics':{}, 'errors':{}}
    design = np.column_stack((train.effort, train.velocity[:-1]))
    diag = _diagnose(design); report['diagnostics'] = diag
    diag['residual_evaluations'] = 0
    if diag['rank'] < 2 or diag['condition_number'] is None or diag['condition_number'] > config.max_condition:
        report['failure']='UNIDENTIFIABLE'; return report
    def residual(theta):
        if diag['residual_evaluations'] >= config.max_evaluations: raise _BudgetExceeded()
        diag['residual_evaluations'] += 1
        return _rollout(theta, train.effort, train.dt, train.velocity[0])-np.asarray(train.velocity[1:])
    try:
        solution = least_squares(residual, config.initial, bounds=(config.lower,config.upper), max_nfev=config.max_evaluations,
                                 ftol=1e-10, xtol=1e-10, gtol=1e-10)
    except _BudgetExceeded:
        report['failure']='BUDGET_EXHAUSTED'; return report
    diag.update({'optimizer_success':bool(solution.success), 'optimizer_message':solution.message,
                 'optimizer_nfev':int(solution.nfev), 'active_bounds':solution.active_mask.tolist(),
                 'rollout_jacobian':_diagnose(solution.jac)})
    if not solution.success: report['failure']='OPTIMIZATION_FAILED'; return report
    sensitivity = diag['rollout_jacobian']
    if sensitivity['rank'] < 2 or sensitivity['condition_number'] is None or sensitivity['condition_number'] > config.max_condition:
        report['failure']='UNIDENTIFIABLE'; return report
    model = Parameters(*solution.x)
    report['model']=asdict(model)
    report['errors']={'train_rmse_m_s':rollout_rmse(model,train),'validation_rmse_m_s':rollout_rmse(model,validation)}
    if report['errors']['validation_rmse_m_s'] > config.validation_rmse_limit:
        report['failure']='VALIDATION_FAILED'
    else: report['status']='VALIDATED'
    return report

def select_excitation(candidates, nominal, dt, *, max_effort=4., max_slew=400., max_candidates=16, max_samples=1000):
    """Rank declared inputs by local log-det information at a supplied nominal model.

    No observations, ground truth, validation or test data are accepted. Limits
    are offline declarations and do not authorize real robot movement.
    """
    if type(max_candidates) is not int or max_candidates < 1 or not 1 <= len(candidates) <= max_candidates:
        raise ValueError('candidate budget exceeded or empty')
    if type(max_samples) is not int or max_samples < 3 or not all(math.isfinite(x) and x > 0 for x in (dt,max_effort,max_slew)):
        raise ValueError('positive finite limits required')
    scores={}; rejected={}
    for name, values in candidates.items():
        u = np.asarray(values, dtype=float)
        if u.ndim != 1 or len(u)<3 or len(u)>max_samples or not np.isfinite(u).all():
            rejected[name]='INVALID_INPUT'; continue
        if np.max(np.abs(u))>max_effort: rejected[name]='EFFORT_LIMIT'; continue
        # Include entry from and exit back to zero effort in the slew check.
        if np.max(np.abs(np.diff(np.r_[0.,u,0.])))/dt>max_slew: rejected[name]='SLEW_LIMIT'; continue
        theta=np.array([nominal.mass,nominal.damping]); base=_rollout(theta,u,dt,0.)
        columns=[]
        for index in range(2):
            delta=1e-5*max(1.,theta[index]); perturbed=theta.copy(); perturbed[index]+=delta
            columns.append((_rollout(perturbed,u,dt,0.)-base)/delta)
        jac=np.column_stack(columns); diag=_diagnose(jac)
        if diag['rank']<2: rejected[name]='UNIDENTIFIABLE'; continue
        logdet=2*sum(math.log(x) for x in diag["singular_values"])
        if not math.isfinite(logdet): rejected[name]='UNIDENTIFIABLE'; continue
        scores[name]={'log_determinant_information':float(logdet),'diagnostics':diag}
    selected=max(scores,key=lambda name:scores[name]['log_determinant_information']) if scores else None
    return {'schema_version':'excitation.v1','selected':selected,'status':'SELECTED' if selected else 'REJECTED',
            'scores':scores,'rejected':rejected,'nominal':asdict(nominal),
            'constraints':{'max_effort':max_effort,'max_slew':max_slew,'max_candidates':max_candidates,'max_samples':max_samples,'dt':dt}}

def simulate_continuous(parameters, effort, dt, *, split, seed, initial=0.):
    """Piecewise constant effort solve_ivp plant, distinct from Euler fitting."""
    effort=tuple(effort)
    Dataset(dt, (float(initial),)*(len(effort)+1), effort, split, seed)
    v=[float(initial)]
    for force in effort:
        result=solve_ivp(lambda t,y:(force-parameters.damping*y)/parameters.mass, (0.,dt), [v[-1]], rtol=1e-10, atol=1e-12)
        if not result.success: raise ValueError('continuous simulation failed: '+result.message)
        v.append(float(result.y[0,-1]))
    return Dataset(dt,tuple(v),effort,split,seed)

def main():
    # Narrow bounds ensure stable Euler discretization for this demo.
    result=fit_bounded(MockRobot().collect(seed=42,split='train'),MockRobot().collect(seed=43,split='validation'),FitConfig(lower=(.2,0.)))
    payload=json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/backend.json').write_text(payload+'\n',encoding='utf-8')
    print(payload)
    return 0 if result['status']=='VALIDATED' else 1

if __name__=='__main__': sys.exit(main())
