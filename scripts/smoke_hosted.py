"""Read-only single/sync smoke; credentials come only from environment."""
import os
import httpx
from app.schemas import validate


def main():
    base=os.environ['BACKEND_URL'].rstrip('/')
    key=os.environ['API_KEY']
    headers={'X-API-Key':key}
    with httpx.Client(base_url=base,timeout=30) as client:
        health=client.get('/health')
        assert health.status_code==200
        validate('HealthResponse',health.json())
        ticket={'ticket_id':'smoke-ticket','channel':'chat','text':'My food has not arrived.'}
        response=client.post('/predict',json=ticket,headers=headers)
        assert response.status_code==200
        validate('PredictResponse',response.json())
        batch=client.post('/predict/batch',json={'tickets':[ticket]},headers=headers)
        assert batch.status_code==200
        validate('BatchResponse',batch.json())
        assert batch.json()['predictions'][0]==response.json()
        assert health.json()['model_version']==response.json()['model_version']
    print('Health, authenticated single and synchronous batch smoke passed.')


if __name__=='__main__':
    main()
