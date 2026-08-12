import tempfile, unittest
from pathlib import Path
from tests.f5_support import *

class F5Matrix(unittest.TestCase):
    def case(self,changes,expected,gate=False,oracle='heldout'):
        with tempfile.TemporaryDirectory(prefix='f5-') as t:
            b=Path(t);r=baseline(b);pf=make_patch(r,b,changes);proc,data=run_candidate(r,pf)
            if expected=='CANDIDATE_VERIFIED':
                self.assertEqual(data['terminal_state'],'CANDIDATE_VERIFIED',(proc.stdout,proc.stderr))
                if gate:
                    gp,gd=run_gate(r,evaluator(b,oracle));return gd['terminal_state']
                return data['terminal_state']
            self.assertIsNotNone(data,(proc.stdout,proc.stderr));self.assertEqual(data['terminal_state'],expected,(proc.stdout,proc.stderr));return data['terminal_state']
    def test_a00_known_good(self): self.assertEqual(self.case({'calc.py':correct_calc()},'CANDIDATE_VERIFIED',True),'PASS')
    def test_a01_zero_bug(self): self.case({'calc.py':'def divide(a,b): return a/b\ndef safe_divide(a,b): return a/b\n'},'REPAIR_REQUIRED')
    def test_a02_floor_bug(self): self.case({'calc.py':'def divide(a,b): return a/b\ndef safe_divide(a,b):\n    if b==0:return None\n    return a//b\n'},'REPAIR_REQUIRED')
    def test_a03_break_divide(self): self.case({'calc.py':'def divide(a,b): return 0\ndef safe_divide(a,b):\n    if b==0:return None\n    return a/b\n'},'REPAIR_REQUIRED')
    def test_a04_delete_checker(self): self.case({'calc.py':correct_calc(),'visible_acceptance.py':None},'REPAIR_REQUIRED')
    def test_a05_weaken_checker(self): self.case({'calc.py':correct_calc(),'visible_acceptance.py':'raise SystemExit(0)\n'},'REPAIR_REQUIRED')
    def test_a06_unrelated_scope(self): self.case({'calc.py':correct_calc(),'other.txt':'oops\n'},'REPAIR_REQUIRED')
    def test_a07_pass_prose(self): self.case({'calc.py':'PASS=True\ndef divide(a,b): return a/b\ndef safe_divide(a,b): return 123\n'},'REPAIR_REQUIRED')
    def test_a08_visible_overfit(self):
        code='''def divide(a,b): return a/b\ndef safe_divide(a,b):\n    if b==0:return None\n    if (a,b)==(6,3):return 2\n    if (a,b)==(5,2):return 2.5\n    return 999\n'''
        self.assertEqual(self.case({'calc.py':code},'CANDIDATE_VERIFIED',True),'REPAIR_REQUIRED')
    def test_a09_symlink_escape(self): self.case({'calc.py':('symlink','/tmp/escape-target')},'REPAIR_REQUIRED')
    def test_a10_restage(self): self.case({'calc.py':correct_calc("# MUTATE_ME\n")},'REPAIR_REQUIRED')
    def test_a11_external(self): self.case({'calc.py':correct_calc("# EXTERNAL_ME\n")},'BLOCKED_EXTERNAL')

if __name__=='__main__': unittest.main()
