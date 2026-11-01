"""Run the offline synthetic demo and write a machine-readable report."""
import argparse
import json
from pathlib import Path
from .core import run_demo

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',type=Path,default=Path('artifacts/demo.json'))
    args=parser.parse_args()
    try:
        report=run_demo(args.seed)
    except ValueError as exc:
        report={'schema_version':'m0.v1','status':'FAILED','reason':str(exc)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps(report,sort_keys=True))
    return 0 if report['status']=='VALIDATED' else 1

if __name__=='__main__':
    raise SystemExit(main())
