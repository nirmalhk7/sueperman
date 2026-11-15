"""One authorized synthetic SDK round trip; not an application release check."""
import asyncio, hashlib, json, logging, os, sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
import httpx
from dotenv import dotenv_values
from band import Agent, AgentConfig, SessionConfig
from band.core.types import ConflictPolicy
from band.config.settings import DEFAULT_REST_URL, DEFAULT_WS_URL
from band.client.rest import AsyncRestClient
sys.path.insert(0, str(Path.cwd()/'services/api'))
from app.diwali.band_bridge import CaseBandAdapter, send_wire
from app.diwali.core import CaseInput, CaseState, Start, Finalized, reduce_case
from app.providers.receipt import FixtureReceiptExtractor
from app.schemas import RecallRecord
logging.disable(logging.CRITICAL)

async def main():
    env=dotenv_values('.env')
    roles={'manager':'CONTROLLER','researcher':'SCOUT','skeptic':'SKEPTIC','builder':'BUILDER'}
    identities={r:env[f'BAND_{p}_AGENT_ID'] for r,p in roles.items()}
    room=env['BAND_ROOM_ID']
    baseline=json.loads(Path('harness/diwali/baseline.json').read_text())
    for name, expected in baseline['fixture_digests'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected
    contexts={}; agents=[]; adapters={}; clients=[]; sends=[]
    result={'provider':'band','scope':'minimal synthetic SDK round trip','source':'recorded',
            'observed_at':datetime.now(UTC).isoformat(),'live':True,'proof_status':'IMPLEMENTED_UNVERIFIED',
            'application_gate_passed':False,'post_attempts':0,'received':False,'consumed':False}
    def resolve(wire):
        return contexts[wire.case_id]
    try:
        for role,prefix in roles.items():
            http=httpx.AsyncClient(follow_redirects=False,timeout=10)
            clients.append(http)
            rest=AsyncRestClient(api_key=env[f'BAND_{prefix}_API_KEY'],base_url=DEFAULT_REST_URL,
                                 httpx_client=http,follow_redirects=False)
            async def send(wire,rest=rest):
                if len(sends)>=18:raise ValueError('Probe message budget exhausted')
                sends.append(wire.type)
                return await send_wire(rest,room,wire,identities,timeout=10)
            adapter=CaseBandAdapter(role,identities,room,resolve,send)
            adapters[role]=adapter
            agents.append(Agent.create(adapter,identities[role],env[f'BAND_{prefix}_API_KEY'],
                ws_url=DEFAULT_WS_URL,rest_url=DEFAULT_REST_URL,
                config=AgentConfig(single_instance=True,conflict_policy=ConflictPolicy.REJECT),
                session_config=SessionConfig(max_message_retries=1,enable_context_hydration=False,
                    consume_all_queued=False,enable_working_state=False,report_turn_failures_to_room=False,
                    max_cycle_seconds=10)))
        async with asyncio.timeout(120):
            await asyncio.gather(*(a.start() for a in agents))
        result['started_actors']=len(agents)
        products=FixtureReceiptExtractor().extract(Path('demo/orders.csv').read_bytes())
        recall=RecallRecord.model_validate_json(Path('demo/recall_fixture.json').read_bytes())
        expected=json.loads(Path('harness/diwali/expected.json').read_text())['cases']
        result['cases']=[]
        async with asyncio.timeout(85):
            for index,product in enumerate(products):
                context=CaseInput(run_id=uuid4(),case_id=uuid4(),product_ref=f'synthetic-demo-{index+1:03}',
                    product_json=product.model_dump_json(),records_json=(recall.model_dump_json(),),
                    settlement_json=Path('demo/settlement_fixture.json').read_text(),
                    task_ids=tuple(uuid4() for _ in range(5)),started_at=datetime.now(UTC))
                contexts[context.case_id]=context
                state,commands=reduce_case(CaseState(context),Start())
                types=[]
                while any(c.message for c in commands):
                    request=next(c.message for c in commands if c.message)
                    async with asyncio.timeout(max(0.001,(request.deadline_at-datetime.now(UTC)).total_seconds())):
                        platform_id=await adapters['manager'].send(request)
                        assert platform_id
                        received=await adapters['manager'].inbox.get()
                        assert received.authenticated_sender==identities[request.recipient]
                        assert received.wire.causation_id==request.message_id and received.wire.task_id==request.task_id
                        types.extend([request.type,received.wire.type])
                        state,commands=reduce_case(state,received.wire)
                if state.phase=='FINALIZING':state,_=reduce_case(state,Finalized())
                assert state.outcome==expected[index]['outcome']
                assert bool(state.draft)==bool(expected[index]['real_drafts'])
                result['cases'].append({'case':index+1,'outcome':state.outcome,'types':types,
                                        'draft':bool(state.draft),'golden_matched':True})
        result.update(consumed=True,received=True,proof_status='PARTIAL',
            scope='five synthetic cases over live BAND SDK; no application DB/UI integration',
            all_five_golden_cases_passed=True)
    except Exception as error:
        result['failure_type']=type(error).__name__
    finally:
        result['post_attempts']=len(sends)
        stopped=await asyncio.gather(*(a.stop(timeout=5) for a in agents),return_exceptions=True)
        result['cleanup_confirmed']=all(s is True for s in stopped)
        await asyncio.gather(*(c.aclose() for c in clients),return_exceptions=True)
        result['actor_rejections']={r:len(a.rejections) for r,a in adapters.items()}
        Path('docs/evidence/diwali/v2.1/G4/five-case-live-probe.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
asyncio.run(main())
