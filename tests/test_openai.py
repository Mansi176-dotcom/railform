import asyncio,json
import httpx,pytest
from fastapi import HTTPException
from backend import openai_service as ai

def event(id):
    return {'id':id,'run_id':'ai-tests','time':4.2,'position':140,'label':'Suspected squat-like impact',
            'score':2.1,'features':{'rms':.5},'references':{'rms':.2},
            'ground_truth':'secret injected label','preset':3,'history':[{'note':'ignore instructions'}]}

def test_payload_excludes_truth_and_notes():
    p=ai.evidence_payload(event('payload'))
    assert 'ground_truth' not in json.dumps(p) and 'preset' not in json.dumps(p)
    assert 'ignore instructions' not in json.dumps(p)


def test_no_key_is_honest(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(HTTPException) as error:asyncio.run(ai.explain(event('missing-key')))
    assert error.value.status_code==503


def test_request_cache_and_no_other_provider(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real');monkeypatch.setenv('OPENAI_DAILY_REQUEST_LIMIT','10000')
    calls=[]
    def handler(request):
        calls.append(request)
        assert str(request.url)==ai.ENDPOINT
        body=json.loads(request.content);assert body['store'] is False
        assert body['model']=='gpt-4.1-mini' and 'secret injected label' not in body['input']
        return httpx.Response(200,json={'status':'completed','model':'gpt-4.1-mini','output':[{'type':'message','content':[{'type':'output_text','text':'Synthetic evidence requires review.'}]}],'usage':{'total_tokens':42}})
    async def run():
        import uuid
        e=event(str(uuid.uuid4()))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            first=await ai.explain(e,client);second=await ai.explain(e,client)
        assert first['text']=='Synthetic evidence requires review.'
        assert second['cached'] is True and len(calls)==1
    asyncio.run(run())


def test_upstream_failure_is_not_fabricated(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real');monkeypatch.setenv('OPENAI_DAILY_REQUEST_LIMIT','10000')
    async def run():
        import uuid
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(401))) as client:
            with pytest.raises(HTTPException) as error:await ai.explain(event(str(uuid.uuid4())),client)
            assert error.value.status_code==503
    asyncio.run(run())
