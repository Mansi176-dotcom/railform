from fastapi.testclient import TestClient
from backend.main import app
from backend import persistence as db

def test_stream_workflow_end_to_end():
    with TestClient(app) as c:
        assert c.get('/api/ready').json()['status']=='ready'
        config=c.get('/api/config').json();config.update(position=100,preset=3,playback=30)
        assert c.post('/api/config',json=config).status_code==200
        with c.websocket_connect('/ws') as ws:
            assert ws.receive_json()['status']=='idle'
            c.post('/api/start')
            packet=None
            for _ in range(30):
                packet=ws.receive_json()
                if packet['alerts']:break
            assert packet['sequence']>0 and packet['alerts']
            event=packet['alerts'][0];assert event['explanation'] and event['ratios']
            result=c.post('/api/alerts/'+event['id'],json={'status':'Acknowledged','note':'Verified measured evidence'}).json()
            assert result['status']=='Acknowledged'
            assert db.get(event['id'])['history'][-1]['note']=='Verified measured evidence'
            c.post('/api/pause');assert c.get('/api/status').json()['status']=='paused'
            assert c.get('/api/analysis').json()['wavelet']['data']
            c.post('/api/start');assert c.get('/api/status').json()['status']=='running'
            c.post('/api/pause')
            assert 'Verified measured evidence' in c.get('/api/report/'+event['id']).text
            assert c.get('/api/export?format=json').json()['alerts']
            assert 'Acknowledged' in c.get('/api/export?format=csv').text
            old=packet['run_id'];c.post('/api/reset')
            assert c.get('/api/status').json()['run_id']!=old
            assert c.get('/api/alerts').json()==[]
        assert c.post('/api/config',json={'speed':0}).status_code==422
        assert c.get('/api/analysis?sensor=99').status_code==422
