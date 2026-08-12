import json,tempfile,unittest
from pathlib import Path
from tests.f5_support import *
class GateTests(unittest.TestCase):
 def candidate(self,b):
  r=baseline(b);pf=make_patch(r,b,{'calc.py':correct_calc()});p,d=run_candidate(r,pf);self.assertEqual(d['terminal_state'],'CANDIDATE_VERIFIED');return r
 def test_good(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);_,d=run_gate(r,evaluator(b));self.assertEqual(d['terminal_state'],'PASS')
 def test_fail(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);_,d=run_gate(r,evaluator(b,'fail'));self.assertEqual(d['terminal_state'],'REPAIR_REQUIRED')
 def test_external(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);_,d=run_gate(r,evaluator(b,'external'));self.assertEqual(d['terminal_state'],'BLOCKED_EXTERNAL')
 def test_mutation(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);_,d=run_gate(r,evaluator(b,'mutate'));self.assertEqual(d['terminal_state'],'REPAIR_REQUIRED')
 def test_overwrite(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);ev=evaluator(b);self.assertEqual(run_gate(r,ev)[0].returncode,0);self.assertEqual(run_gate(r,ev)[0].returncode,2)
 def test_tamper_diff(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);(r/'.forge/runs/U-0001/attempt-0001/APPLIED.diff').write_text('bad');p,_=run_gate(r,evaluator(b));self.assertEqual(p.returncode,2)
 def test_tamper_evidence(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);p=r/'.forge/runs/U-0001/attempt-0001/EVIDENCE.json';x=json.loads(p.read_text());x['terminal_state']='PASS';p.write_text(json.dumps(x));q,_=run_gate(r,evaluator(b));self.assertEqual(q.returncode,2)
 def test_evaluator_symlink(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);real=evaluator(b);link=b/'link.py';link.symlink_to(real);p,_=run_gate(r,link);self.assertEqual(p.returncode,2)
 def test_evaluator_inside_repo(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=self.candidate(b);ev=r/'evil.py';ev.write_text('raise SystemExit(0)\n');p,_=run_gate(r,ev);self.assertEqual(p.returncode,2)
 def test_non_candidate(self):
  with tempfile.TemporaryDirectory() as t:b=Path(t);r=baseline(b);pf=make_patch(r,b,{'calc.py':'def divide(a,b):return a/b\ndef safe_divide(a,b):return 1\n'});run_candidate(r,pf);p,_=run_gate(r,evaluator(b));self.assertEqual(p.returncode,2)
if __name__=='__main__':unittest.main()
