#!/usr/bin/env python3
"""运行 V2 的统一检查入口。 / Run all V2 checks."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
commands=[
 [sys.executable,"-B","-m","unittest","discover","-s",str(ROOT/"skills/develop-robotics-idea/tests"),"-v"],
 [sys.executable,"-B","-m","unittest","discover","-s",str(ROOT/"skills/design-robotics-experiment/tests"),"-v"],
 [sys.executable,"-B","-m","unittest","discover","-s",str(ROOT/"skills/write-robotics-paper/tests"),"-v"],
 [sys.executable,"-B","-m","unittest","discover","-s",str(ROOT/"skills/review-robotic-feedback/tests"),"-v"],
 [sys.executable,"-B",str(ROOT/"tests/check_contract_alignment.py")],
 [sys.executable,"-B",str(ROOT/"scripts/check_bilingual_layout.py"),str(ROOT)]
]
for cmd in commands:
 print("+"," ".join(cmd));r=subprocess.run(cmd,cwd=ROOT)
 if r.returncode:raise SystemExit(r.returncode)
print("ALL_CHECKS: PASS")
