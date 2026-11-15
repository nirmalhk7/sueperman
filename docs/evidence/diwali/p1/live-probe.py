"""Public GET-only P1 acceptance, synthetic records, disposable database."""
import json,os,sys,tempfile,time
from pathlib import Path
from datetime import UTC,datetime
sys.path.insert(0,str(Path.cwd()/'services/api'))
with tempfile.TemporaryDirectory(prefix='sueperman-p1-live-') as folder:
 os.environ.update({'DATABASE_URL':f'sqlite:///{folder}/live.db','P1_ENABLED':'true',
 'P1_MONITOR_ENABLED':'true','P1_MONITOR_POLL_SECONDS':'1','CPSC_LIVE_ENABLED':'true',
 'SENTRY_DSN':'','BRIGHTDATA_ENABLED':'false','OPENAI_ENABLED':'false','OPENAI_RECEIPT_ENABLED':'false',
 'GEMINI_ENABLED':'false','SYSTEM_ONE_ENABLED':'false','SETTLEMENT_LIVE_ENABLED':'false',
 'BAND_ENABLED':'false','LYZR_ENABLED':'false','AGENT37_ENABLED':'false'})
 from fastapi.testclient import TestClient
 from app.main import create_app
 from app.providers.cpsc import CPSCRecallSource
 original=CPSCRecallSource.__init__
 def isolated(self,*args,**kwargs):
  kwargs.setdefault('cache_dir',Path(folder)/'public-cache');original(self,*args,**kwargs)
 CPSCRecallSource.__init__=isolated
 report={'scope':'P1 live public CPSC and scheduled monitor; synthetic purchases only',
 'observed_at':datetime.now(UTC).isoformat(),'paid_calls':0,'claims_submitted':0,'cases':[],'status':'INCOMPLETE'}
 try:
  with TestClient(create_app(database_url=os.environ['DATABASE_URL'])) as client:
   for brand,model in [('Flaunt','E33A'),('iStore','IST-09991/W05')]:
    csv='order_id,purchased_at,merchant,product_name,brand,model_number,upc\n'
    product_name='Flaunt MagSafe Battery Charger' if brand=='Flaunt' else 'iStore Magnetic Wireless Power Bank'
    for i,value in enumerate([model,model+'X','']):
     csv+=f'SYNTHETIC-{brand}-{i},2024-09-01,Synthetic P1 shop,{product_name},{brand},{value},\n'
    upload=client.post('/api/uploads/purchases',files={'file':('synthetic.csv',csv.encode(),'text/csv')})
    assert upload.status_code==200
    run=client.post('/api/runs',json={'purchase_ids':upload.json()['purchase_ids'],'mode':'live',
      'idempotency_key':'p1-live-'+brand})
    assert run.status_code==200
    completed=client.get('/api/runs/'+run.json()['run_id']).json()
    opportunities=client.get('/api/opportunities',params={'run_id':completed['run_id']}).json()
    statuses=sorted(o['status'] for o in opportunities)
    item={'brand':brand,'model':model,'run_status':completed['status'],'outcomes':statuses,
          'provider_modes':completed['provider_modes']}
    report['cases'].append(item)
    assert completed['status']=='completed' and statuses==['needs_review','rejected','verified_match']
    opportunity=next(o for o in opportunities if o['status']=='verified_match')
    detail=client.get('/api/opportunities/'+opportunity['id']).json()
    packet=client.post('/api/opportunities/'+opportunity['id']+'/claim-packet').json()
    assert client.post('/api/claim-packets/'+packet['id']+'/approve-local',json={'confirmed':True}).status_code==200
    monitor='/api/opportunities/'+opportunity['id']+'/source-monitor'
    assert client.post(monitor,json={'enabled':True}).status_code==200
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
     result=client.get(monitor).json()
     if result['checks']:break
     time.sleep(0.2)
    assert result['checks'] and result['checks'][-1]['status']=='unchanged'
    assert client.post('/api/claim-packets/'+packet['id']+'/export').status_code==200
    assert client.post(monitor,json={'enabled':False}).status_code==200
    item.update(official_url=detail['official_url'],source_observed_at=detail['source_observed_at'],
      source_sha256=detail['evidence'][0]['content_sha256'],scheduler_observation=result['checks'][-1],
      watch_disabled=True,local_export_preserved=True)
   report['status']='PASS'
 except Exception as error:
  report['failure_type']=type(error).__name__
 finally:
  Path('docs/evidence/diwali/p1/live-source-monitor.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({'status':report['status'],'cases':[{k:v for k,v in c.items() if k in
     {'brand','model','run_status','outcomes','watch_disabled','local_export_preserved'}} for c in report['cases']],
     'failure_type':report.get('failure_type'),'paid_calls':0}))
