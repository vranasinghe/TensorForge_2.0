import base64
import importlib
from fastapi.testclient import TestClient


def test_private_demo_csv_and_secret_boundary(monkeypatch):
    monkeypatch.setenv('API_KEY', 'server-only-secret')
    monkeypatch.setenv('DEMO_USERNAME', 'demo')
    monkeypatch.setenv('DEMO_PASSWORD', 'demo-test-password')
    from frontend import server
    importlib.reload(server)
    with TestClient(server.app) as c:
        assert c.get('/').status_code == 401
        credentials = {'Authorization':'Basic '+base64.b64encode(b'demo:demo-test-password').decode()}
        response = c.get('/',headers=credentials)
        assert response.status_code == 200
        assert 'server-only-secret' not in response.text
        csv = 'ticket_id,channel,subject,text\na,chat,,"Tamil தமிழ்\nsecond line"\n'
        imported = c.post('/api/import',content=csv.encode(),headers=credentials)
        assert imported.status_code == 200
        assert imported.json()['tickets'][0]['text'] == 'Tamil தமிழ்\nsecond line'
        assert c.post('/api/import',content=b'bad,columns\n',headers=credentials).status_code == 422
        assert c.get('/api/../../escape',headers=credentials).status_code == 404
        assert c.post('/api/import',content=csv.encode(),headers={**credentials,'Origin':'https://unrelated.example'}).status_code == 403
        assert c.post('/api/import',content=csv.encode(),headers={**credentials,'Origin':'http://testserver'}).status_code == 200
