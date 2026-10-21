"""Run the requested repository checks with its bundled FFmpeg on PATH."""
import json
import argparse
import os
from pathlib import Path
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report-dir',default=str(ROOT/'reports/dna-audit-2026-10-16'))
REPORT=Path(parser.parse_args().report_dir).resolve()
REPORT.mkdir(parents=True,exist_ok=True)
os.environ['PATH']=str(ROOT/'.tools/ffmpeg/unpacked/ffmpeg-master-latest-win64-gpl/bin')+os.pathsep+os.environ.get('PATH','')
sys.path.insert(0,str(ROOT/'tests'))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
with (REPORT/'test-run.txt').open('w',encoding='utf-8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
summary={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
         'skipped':len(result.skipped),'success':result.wasSuccessful(),
         'python':sys.executable,'ffmpeg':shutil.which('ffmpeg'),
         'scope':'Repository behavior checks; separate from editorial sample scores and audience performance.'}
(REPORT/'test-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not result.wasSuccessful():
    print((REPORT/'test-run.txt').read_text(encoding='utf-8')[-10000:])
sys.exit(0 if result.wasSuccessful() else 1)
