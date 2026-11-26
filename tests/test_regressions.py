import os
import sys

import pytest
from starlette.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_settings_do_not_advertise_retired_model(client, monkeypatch):
    monkeypatch.delenv('GROQ_MODEL', raising=False)
    model = client.get('/api/v1/settings').json()['integrations']['groq_api']['model']
    assert 'llama-3.3-70b-versatile' not in model


def test_env_example_uses_a_live_model():
    with open(os.path.join(ROOT, '.env.example')) as fh:
        assert 'llama-3.3-70b-versatile' not in fh.read()


def test_gateway_health_without_key_is_not_connected(client, monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.delenv('BIFROST_GATEWAY_URL', raising=False)
    body = client.get('/api/v1/integrations/bifrost/health').json()
    assert body['status'] == 'not_configured'


def test_site_has_no_invented_testimonials(client):
    html = client.get('/').text
    assert 'quote-grid' not in html
    assert 'security@aegistrace.io' not in html
