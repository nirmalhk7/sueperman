"""One authorized inference against existing Builder; no application state writes."""
import hashlib,json,os,sys,time
from pathlib import Path
from datetime import UTC,datetime
from uuid import uuid4
import httpx
from dotenv import dotenv_values
sys.path.insert(0,str(Path.cwd()/'services/api'))
from app.collaboration.contracts import CaseTask,CaseResult,validate_result
v=dotenv_values('.env')
config=json.loads(Path('/tmp/sueperman-lyzr-config.json').read_text())
case_id,task_id=str(uuid4()),str(uuid4())
task=CaseTask(case_id=case_id,task_id=task_id,revision=1,sender='skeptic',recipient='builder',
 kind='case_board_construction',deduplication_key=task_id,allowed_capabilities=['build_sections'],
 source_refs=['26-792'],remaining_ms=10000,mode='live')
expected={'schema_version':1,'task_id':task_id,'case_id':case_id,'revision':1,'provider':'lyzr','mode':'live',
 'status':'rejected','findings':[{'code':'condition_failed','condition':'model_number','source_ref':'26-792'}],
 'missing_conditions':[],'source_refs':['26-792'],'provider_ref':None,'duration_ms':0}
request={'synthetic_test':True,'task':task.model_dump(mode='json'),
 'product':{'product_name':'NEWDERY power bank','brand':'NEWDERY','model_number':'ZHX-PB23'},
 'evidence':{'source_id':'26-792','affected_models':['ZHX-PB22'],
 'excerpt':'This recall involves NEWDERY power banks with model number ZHX-PB22.'},
 'validated_skeptic_result':expected,
 'instruction':'Return the supplied validated result unchanged except duration_ms; retain the rejected model mismatch. No tools or actions. Synthetic connectivity and schema test only.'}
payload={'user_id':'sueperman-synthetic-probe','agent_id':v['LYZR_AGENT_ID'],
 'session_id':f'sueperman-{case_id}-builder-test','message':json.dumps(request)}
report={'provider':'lyzr','observed_at':datetime.now(UTC).isoformat(),'scope':'existing Builder connectivity/schema test',
 'configured_role':config.get('agent_role'),'required_reviewer_role':False,'post_attempts':1,
 'retries':0,'live_inference':False,'schema_valid':False,'application_gate_passed':False,
 'proof_status':'IMPLEMENTED_UNVERIFIED','request_sha256':hashlib.sha256(payload['message'].encode()).hexdigest(),
 'configuration_sha256':hashlib.sha256(Path('/tmp/sueperman-lyzr-config.json').read_bytes()).hexdigest()}
started=time.monotonic()
try:
 r=httpx.post('https://agent-prod.studio.lyzr.ai/v3/inference/chat/',json=payload,
  headers={'x-api-key':v['LYZR_API_KEY']},timeout=10,follow_redirects=False)
 report['http_status']=r.status_code
 report['response_sha256']=hashlib.sha256(r.content).hexdigest()
 fd=os.open('/tmp/sueperman-lyzr-probe-response.json',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'wb') as f:f.write(r.content)
 if r.status_code==200:
  report['live_inference']=True
  response=r.json()['response']
  result=CaseResult.model_validate_json(response)
  validate_result(task,result,{'26-792'})
  assert result.status=='rejected' and result.missing_conditions==[]
  assert [f.model_dump() for f in result.findings]==expected['findings']
  report.update(schema_valid=True,model_mismatch_preserved=True,proof_status='PARTIAL')
 else:report['failure_type']='HTTP_FAILURE'
except Exception as error:
 report['failure_type']=type(error).__name__
finally:
 report['duration_seconds']=round(time.monotonic()-started,3)
 p=Path('docs/evidence/diwali/v2.1/G5');p.mkdir(exist_ok=True)
 (p/'live-probe.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
