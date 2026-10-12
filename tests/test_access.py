from fastapi.testclient import TestClient
from backend.main import app

def test_workspace_auth_and_key_not_exposed(monkeypatch):
    monkeypatch.setenv('RAILFORM_ACCESS_TOKEN','test-only-workspace-token')
    monkeypatch.setenv('OPENAI_API_KEY','test-only-private-api-key')
    with TestClient(app) as c:
        assert c.get('/api/health').status_code==200
        assert c.get('/api/access').json()['required']
        assert c.get('/api/status').status_code==401
        assert c.post('/api/access/login',json={'token':'wrong'}).status_code==401
        login=c.post('/api/access/login',json={'token':'test-only-workspace-token'})
        assert login.status_code==200 and 'HttpOnly' in login.headers['set-cookie']
        assert c.get('/api/status').status_code==200
        status=c.get('/api/ai/status');assert status.json()['configured']
        assert 'test-only-private-api-key' not in status.text
        assert c.post('/api/reset',headers={'Origin':'https://attacker.invalid'}).status_code==403
