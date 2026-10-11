"""Read-only live official-source checks; never claims blocked sources were validated."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from macro_calendar import fetch_calendar, evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/macro-live-validation.json'))
    args=parser.parse_args()
    data=fetch_calendar()
    assessment=evaluate(data)
    summary=dict(checked_at=datetime.now(timezone.utc).isoformat(),assessment=assessment,
                 sources={name:{k:v for k,v in report.items() if k!='raw'} for name,report in data['sources'].items()},
                 events=data['events'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n')
    for name,report in summary['sources'].items():
        print(name,report['http_status'],report['status'],report.get('error',''))
    print('Macro safety:',assessment['reason_code'],'; clear=',assessment['clear'])
    return int(any(r['status']!='parsed' for r in data['sources'].values()))


if __name__=='__main__':
    raise SystemExit(main())
