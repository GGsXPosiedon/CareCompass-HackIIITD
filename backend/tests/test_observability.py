import io
import json
import logging

from fastapi.testclient import TestClient

from app.main import create_app
from app.observability import JsonFormatter


def test_request_logs_correlate_success_validation_and_exceptions_without_patient_data():
    app = create_app()

    @app.get('/test-log-ok')
    def ok():
        return {'status': 'ok'}

    @app.get('/test-log-failure')
    def failure():
        raise RuntimeError('private-patient-data')

    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger('carecompass')
    logger.addHandler(handler)
    try:
        with TestClient(app) as client:
            for path, status in [('/test-log-ok', 200), ('/test-log-failure', 500)]:
                response = client.get(path + '?secret=private-patient-data', headers={'X-Request-ID': 'test-reference'})
                assert response.status_code == status
                assert response.headers['x-request-id'] == 'test-reference'
            assert response.json() == {'error': 'INTERNAL_SERVER_ERROR'}
            response = client.post('/triage', json={'user_input': ''})
            assert response.status_code == 422
            assert response.headers['x-request-id']
            response = client.get('/test-log-ok', headers={'X-Request-ID': 'invalid id'})
            assert response.headers['x-request-id'] != 'invalid id'
        entries = [json.loads(line) for line in output.getvalue().splitlines()]
        assert [entry['status'] for entry in entries] == [200, 500, 422, 200]
        assert entries[1]['error_type'] == 'RuntimeError'
        assert entries[1]['stack']
        assert entries[1]['request_id'] == 'test-reference'
        assert all(entry['duration_ms'] >= 0 for entry in entries)
        assert 'private-patient-data' not in output.getvalue()
    finally:
        logger.removeHandler(handler)
