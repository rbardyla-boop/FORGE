from __future__ import annotations
import hashlib,json,os,shutil,signal,stat,subprocess,sys,tempfile
from pathlib import Path
from typing import Any
from .contract import verify_contract
from .doctor import BLOCKED_EXTERNAL,EXTERNAL_PREFIX,OUTPUT_LIMIT
from .lifecycle import CANDIDATE_VERIFIED,RUN_SCHEMA
FINAL_SCHEMA="forge.final-evaluation.v0.1";FINAL_FILE="FINAL_EVALUATION.json";EVALUATOR_LIMIT_BYTES=1024*1024;EVALUATOR_TIMEOUT_SECONDS=30.0;PASS="PASS";REPAIR_REQUIRED="REPAIR_REQUIRED"
class ForgeGateError(RuntimeError): pass
def _sha256(b):return "sha256:"+hashlib.sha256(b).hexdigest()
def _bounded(v):
 t=v or "";return (t,False) if len(t)<=OUTPUT_LIMIT else (t[:OUTPUT_LIMIT],True)
def _read_regular(path,label,limit):
 flags=os.O_RDONLY|(os.O_NOFOLLOW if hasattr(os,"O_NOFOLLOW") else 0)
 try:fd=os.open(path,flags)
 except OSError as e:
  if path.is_symlink():raise ForgeGateError(f"{label} must not be a symlink") from e
  raise ForgeGateError(f"{label} is unreadable") from e
 try:
  m=os.fstat(fd)
  if not stat.S_ISREG(m.st_mode):raise ForgeGateError(f"{label} must be a regular file")
  if m.st_size>limit:raise ForgeGateError(f"{label} exceeds {limit} bytes")
  out=[];total=0
  while True:
   c=os.read(fd,min(65536,limit+1-total))
   if not c:break
   out.append(c);total+=len(c)
   if total>limit:raise ForgeGateError(f"{label} exceeds {limit} bytes")
  return b"".join(out)
 finally:os.close(fd)
def _gt(g,r,*a):return subprocess.run([g,"-C",str(r),*a],text=True,capture_output=True,check=False,timeout=10)
def _gb(g,r,*a):return subprocess.run([os.fsencode(g),b"-C",os.fsencode(r),*[os.fsencode(x) for x in a]],capture_output=True,check=False,timeout=10)
def _attempt(root,unit):
 a=root/".forge"/"runs"/unit/"attempt-0001"
 for p in [root/".forge",root/".forge"/"runs",root/".forge"/"runs"/unit,a]:
  if p.is_symlink():raise ForgeGateError("F4 attempt evidence path must not be symlinked")
 if not a.is_dir():raise ForgeGateError("F4 attempt evidence does not exist")
 return a
def _load(root,unit):
 a=_attempt(root,unit);eb=_read_regular(a/"EVIDENCE.json","F4 evidence",EVALUATOR_LIMIT_BYTES)
 try:e=json.loads(eb.decode())
 except Exception as x:raise ForgeGateError("F4 evidence is invalid JSON") from x
 if not isinstance(e,dict) or e.get("schema")!=RUN_SCHEMA:raise ForgeGateError("F4 evidence schema mismatch")
 if e.get("unit_id")!=unit:raise ForgeGateError("F4 evidence unit mismatch")
 if e.get("terminal_state")!=CANDIDATE_VERIFIED:raise ForgeGateError("final PASS requires F4 CANDIDATE_VERIFIED evidence")
 if e.get("completion_authority")!="harness":raise ForgeGateError("F4 evidence completion authority mismatch")
 db=_read_regular(a/"APPLIED.diff","F4 applied diff",EVALUATOR_LIMIT_BYTES)
 if e.get("applied_diff_sha256")!=_sha256(db) or e.get("applied_diff_bytes")!=len(db):raise ForgeGateError("F4 applied diff binding mismatch")
 return a,eb,e,db
def _symlinks(g,w):
 x=_gt(g,w,"ls-files","-z","-s")
 if x.returncode!=0:return False
 root=w.resolve()
 for rec in x.stdout.split("\0"):
  if not rec:continue
  meta,rel=rec.split("\t",1)
  if meta.split(" ",1)[0]!="120000":continue
  link=w/rel
  if not link.is_symlink():return False
  try:link.resolve(strict=False).relative_to(root)
  except (OSError,ValueError):return False
 return True
def _eval(ep,candidate,timeout):
 env=os.environ.copy();env["PWD"]=str(ep.parent)
 for k in ("GIT_DIR","GIT_WORK_TREE","GIT_INDEX_FILE","GIT_COMMON_DIR"):env.pop(k,None)
 base={"argv":[sys.executable,ep.name,"<candidate-root>"],"exit_code":None,"stdout":"","stderr":"","stdout_truncated":False,"stderr_truncated":False,"result":REPAIR_REQUIRED,"reason_code":"EVALUATOR_LAUNCH_FAILED"}
 try:p=subprocess.Popen([sys.executable,str(ep),str(candidate)],cwd=ep.parent,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,start_new_session=(os.name=="posix"))
 except OSError as e:base["stderr"]=str(e);return base
 try:o,e=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  if os.name=="posix":
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  else:p.kill()
  o,e=p.communicate();base["reason_code"]="EVALUATOR_TIMEOUT"
 out,ot=_bounded(o);err,et=_bounded(e);base.update(exit_code=p.returncode,stdout=out,stderr=err,stdout_truncated=ot,stderr_truncated=et)
 if base["reason_code"]=="EVALUATOR_TIMEOUT":return base
 if p.returncode==0:base["result"]=PASS;base["reason_code"]="EVALUATOR_PASS"
 elif p.returncode==75 and any(x.startswith(EXTERNAL_PREFIX) for x in e.splitlines()):base["result"]=BLOCKED_EXTERNAL;base["reason_code"]="EVALUATOR_EXTERNAL_DEPENDENCY"
 else:base["result"]=REPAIR_REQUIRED;base["reason_code"]="EVALUATOR_FAILED"
 return base
def run_final_gate(root:Path,unit_id:str,evaluator_file:Path,*,timeout_seconds:float=EVALUATOR_TIMEOUT_SECONDS):
 root=root.resolve();attempt,eb,evidence,diff=_load(root,unit_id);final=attempt/FINAL_FILE
 if final.exists() or final.is_symlink():raise ForgeGateError("final evaluation already exists for this attempt")
 contract=verify_contract(root,unit_id)
 if contract["contract_digest"]!=evidence["contract_digest"] or contract["revision"]!=evidence["contract_revision"]:raise ForgeGateError("F4 evidence no longer binds current frozen contract")
 baseline=evidence.get("baseline_commit")
 if not isinstance(baseline,str) or not baseline:raise ForgeGateError("F4 evidence missing baseline commit")
 try:evaluator_file.resolve().relative_to(root)
 except ValueError:pass
 else:raise ForgeGateError("independent evaluator must live outside the product repository")
 eval_bytes=_read_regular(evaluator_file,"evaluator",EVALUATOR_LIMIT_BYTES)
 git=shutil.which("git")
 if not git:raise ForgeGateError("Git is required for final gate")
 tb=_gt(git,root,"status","--porcelain=v1","--untracked-files=no");wb=_gt(git,root,"worktree","list","--porcelain")
 if tb.returncode!=0 or wb.returncode!=0 or tb.stdout:raise ForgeGateError("operator tracked worktree must be clean before final gate")
 temp=Path(tempfile.mkdtemp(prefix="forge-gate-"));cand=temp/"candidate";ep=temp/"evaluator.py";dp=temp/"APPLIED.diff";ep.write_bytes(eval_bytes);dp.write_bytes(diff);added=False;state=REPAIR_REQUIRED;reason="GATE_NOT_EVALUATED";er={"result":REPAIR_REQUIRED,"reason_code":"EVALUATOR_NOT_RUN","exit_code":None,"stdout":"","stderr":"","stdout_truncated":False,"stderr_truncated":False}
 try:
  a=_gt(git,root,"worktree","add","--detach","--quiet",str(cand),baseline)
  if a.returncode!=0:reason="WORKTREE_CREATE_FAILED"
  else:
   added=True;ap=subprocess.run([git,"-C",str(cand),"apply","--index","--whitespace=error-all",str(dp)],text=True,capture_output=True,timeout=10)
   if ap.returncode!=0:reason="CANDIDATE_REPLAY_FAILED"
   else:
    st=_gb(git,cand,"diff","--cached","--binary","--full-index","--no-ext-diff","--no-renames");us=_gb(git,cand,"diff","--binary","--full-index","--no-ext-diff","--no-renames")
    if st.stdout!=diff or us.stdout:reason="CANDIDATE_REPLAY_MISMATCH"
    elif not _symlinks(git,cand):reason="CANDIDATE_SYMLINK_UNSAFE"
    else:
     er=_eval(ep,cand,timeout_seconds);sa=_gb(git,cand,"diff","--cached","--binary","--full-index","--no-ext-diff","--no-renames");ua=_gb(git,cand,"diff","--binary","--full-index","--no-ext-diff","--no-renames")
     if sa.stdout!=diff or ua.stdout:state=REPAIR_REQUIRED;reason="EVALUATOR_MUTATED_CANDIDATE"
     else:state=er["result"];reason=er["reason_code"]
 finally:
  if added:_gt(git,root,"worktree","remove","--force",str(cand))
  shutil.rmtree(temp,ignore_errors=True)
 ta=_gt(git,root,"status","--porcelain=v1","--untracked-files=no");wa=_gt(git,root,"worktree","list","--porcelain");osu=ta.returncode==0 and ta.stdout==tb.stdout;wtu=wa.returncode==0 and wa.stdout==wb.stdout
 if not osu or not wtu:state=REPAIR_REQUIRED;reason="OPERATOR_POSTCONDITION_FAILED"
 report={"schema":FINAL_SCHEMA,"unit_id":unit_id,"attempt":"attempt-0001","f4_evidence_sha256":_sha256(eb),"contract_digest":evidence["contract_digest"],"contract_revision":evidence["contract_revision"],"baseline_commit":baseline,"applied_diff_sha256":evidence["applied_diff_sha256"],"evaluator_sha256":_sha256(eval_bytes),"evaluator_bytes":len(eval_bytes),"evaluator":er,"operator_status_unchanged":osu,"worktree_registry_unchanged":wtu,"completion_authority":"final_gate","terminal_state":state,"reason_code":reason}
 if final.exists() or final.is_symlink():raise ForgeGateError("final evaluation evidence already exists; refusing overwrite")
 final.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 return report,0 if state==PASS else (5 if state==BLOCKED_EXTERNAL else 3)
