"""Checks for the password-protected, Stripe test-only deployment profile."""
import base64
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def load_staging(monkeypatch, tmp_path, *, stripe_key=''):
    monkeypatch.setenv('KOREN_STAGING_ONLY', '1')
    monkeypatch.setenv('STAGING_HTTP_USER', 'test-staging-user')
    monkeypatch.setenv('STAGING_HTTP_PASSWORD', 'a-different-very-long-password')
    monkeypatch.setenv('ADMIN_PASSWORD', 'strong-admin-test-password')
    monkeypatch.setenv('KOREN_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME', 'koren-staging.onrender.com')
    monkeypatch.delenv('APP_BASE_URL', raising=False)
    monkeypatch.setenv('STRIPE_SECRET_KEY', stripe_key)
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_test_dummy')
    spec = importlib.util.spec_from_file_location('isolated_staging_server', Path(__file__).resolve().parents[1]/'server.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_staging_auth_and_host(monkeypatch, tmp_path):
    server = load_staging(monkeypatch, tmp_path)
    assert server.BASE_URL == 'https://koren-staging.onrender.com'
    with TestClient(server.app) as client:
        health = client.get('/healthz')
        assert health.status_code == 200 and health.json() == {'ok': True}
        assert client.get('/').status_code == 401
        assert client.get('/api/products').status_code == 401
        # Stripe is allowed past staging password, but disabled without real TEST credentials.
        assert client.post('/api/stripe/webhook', content=b'{}').status_code == 404
        basic = lambda s: {'Authorization': 'Basic ' + base64.b64encode(s.encode()).decode()}
        assert client.get('/api/products', headers=basic('test-staging-user:bad-password')).status_code == 401
        response = client.get('/', headers=basic('test-staging-user:a-different-very-long-password'))
        assert response.status_code == 200
        assert response.headers['x-robots-tag'] == 'noindex, nofollow'
        assert client.get('/api/admin/orders', headers=basic('test-staging-user:a-different-very-long-password')).status_code == 401


def test_staging_rejects_live_stripe(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError, match='Stripe live'):
        load_staging(monkeypatch, tmp_path, stripe_key='sk_live_should-never-run')


def test_staging_requires_password(monkeypatch, tmp_path):
    monkeypatch.setenv('KOREN_STAGING_ONLY', '1')
    monkeypatch.setenv('STAGING_HTTP_PASSWORD', 'short')
    monkeypatch.setenv('STAGING_HTTP_USER', 'test')
    monkeypatch.setenv('KOREN_DATA_DIR', str(tmp_path))
    spec = importlib.util.spec_from_file_location('isolated_staging_server_2', Path(__file__).resolve().parents[1]/'server.py')
    module = importlib.util.module_from_spec(spec)
    with pytest.raises(RuntimeError, match='STAGING_HTTP_PASSWORD'):
        spec.loader.exec_module(module)
