from __future__ import annotations
import json, os, subprocess, sys, textwrap
from pathlib import Path

REPO_ROOT=Path(__file__).resolve().parents[1]
FORGE=REPO_ROOT/'forge'

def sh(root,*args,check=True):
    p=subprocess.run(list(args),cwd=root,text=True,capture_output=True)
    if check and p.returncode!=0: raise AssertionError((args,p.stdout,p.stderr))
    return p

def git(root,*args,check=True): return sh(root,'git',*args,check=check)
def run_forge(root,*args): return sh(root,str(FORGE),*args,check=False)

def baseline(base:Path):
    root=base/'repo';root.mkdir()
    (root/'calc.py').write_text('def divide(a, b):\n    return a / b\n')
    (root/'visible_acceptance.py').write_text(textwrap.dedent('''
        import calc, sys
        def ok():
            if calc.safe_divide(6, 3) != 2: return False
            if calc.safe_divide(5, 2) != 2.5: return False
            if calc.safe_divide(1, 0) is not None: return False
            if calc.divide(8, 4) != 2: return False
            if 'MUTATE_ME' in open('calc.py').read():
                open('calc.py','a').write('\\n# mutated by check\\n')
                import subprocess; subprocess.run(['git','add','calc.py'],check=False)
            if 'EXTERNAL_ME' in open('calc.py').read():
                print('FORGE_BLOCKED_EXTERNAL: fixture dependency unavailable', file=sys.stderr)
                raise SystemExit(75)
            return True
        raise SystemExit(0 if ok() else 1)
    ''').strip()+'\n')
    git(root,'init','-q');git(root,'config','user.name','F5');git(root,'config','user.email','f5@example.invalid');git(root,'add','.');git(root,'commit','-qm','baseline')
    r=run_forge(root,'init'); assert r.returncode==0,(r.stdout,r.stderr)
    authority={
      'objective':'Add safe_divide(a,b) without breaking divide.',
      'deliverables':['calc.py'],
      'success_criteria':[{'id':'SAFE_DIVIDE','statement':'safe_divide handles visible cases and divide remains stable','check_ids':['PREFLIGHT','ACCEPT']}],
      'scope':{'allowed_paths':['calc.py'],'forbidden_paths':['visible_acceptance.py','other.txt']},
      'checks':[
        {'id':'PREFLIGHT','required':True,'preflight':True,'argv':['python3','-m','py_compile','calc.py']},
        {'id':'ACCEPT','required':True,'preflight':False,'argv':['python3','visible_acceptance.py']},
      ],
      'terminal_states':['PASS','REPAIR_REQUIRED','BLOCKED_EXTERNAL'],
      'non_goals':[], 'forbidden_actions':[]}
    af=base/'authority.json';af.write_text(json.dumps(authority))
    assert run_forge(root,'contract','create','U-0001','--file',str(af)).returncode==0
    assert run_forge(root,'contract','freeze','U-0001').returncode==0
    return root

def make_patch(root:Path,base:Path,changes:dict[str,object],name='input.patch'):
    for rel,val in changes.items():
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(val,tuple) and val[0]=='symlink':
            if p.exists() or p.is_symlink(): p.unlink()
            p.symlink_to(val[1])
        elif val is None:
            p.unlink()
        else:p.write_text(str(val))
    tracked_before={rel: git(root,'ls-files','--error-unmatch',rel,check=False).returncode==0 for rel in changes}
    git(root,'add','-A','--',*changes.keys())
    diff=git(root,'diff','--cached','--binary','--full-index','--no-ext-diff','--no-renames').stdout
    pf=base/name;pf.write_text(diff)
    git(root,'reset','--hard','HEAD')
    for rel, was_tracked in tracked_before.items():
        p=root/rel
        if not was_tracked and (p.exists() or p.is_symlink()):
            if p.is_dir() and not p.is_symlink():
                import shutil; shutil.rmtree(p)
            else: p.unlink()
    return pf

def correct_calc(marker=''):
    return f'''def divide(a, b):\n    return a / b\n\ndef safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n{marker}'''

def evaluator(base:Path,mode='heldout'):
    p=base/f'evaluator-{mode}.py'
    if mode=='heldout': body='''
import importlib.util, pathlib, sys
root=pathlib.Path(sys.argv[1]); spec=importlib.util.spec_from_file_location('calc',root/'calc.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[m.safe_divide(9,3)==3,m.safe_divide(7,2)==3.5,m.safe_divide(-8,2)==-4,m.safe_divide(3,0) is None,m.divide(10,2)==5]
raise SystemExit(0 if all(checks) else 1)
'''
    elif mode=='fail': body='raise SystemExit(1)\n'
    elif mode=='external': body="import sys; print('FORGE_BLOCKED_EXTERNAL: evaluator fixture',file=sys.stderr); raise SystemExit(75)\n"
    elif mode=='mutate': body="import pathlib,sys; p=pathlib.Path(sys.argv[1])/'calc.py'; p.write_text(p.read_text()+'\\n# evaluator mutation\\n'); raise SystemExit(0)\n"
    else: body='raise SystemExit(0)\n'
    p.write_text(textwrap.dedent(body).lstrip());return p

def run_candidate(root,pf):
    r=run_forge(root,'unit','run','U-0001','--patch',str(pf)); data=json.loads(r.stdout) if r.stdout.strip().startswith('{') else None;return r,data

def run_gate(root,ev):
    r=run_forge(root,'gate','run','U-0001','--evaluator',str(ev)); data=json.loads(r.stdout) if r.stdout.strip().startswith('{') else None;return r,data
