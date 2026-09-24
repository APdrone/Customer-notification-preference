import os

from fastapi.testclient import TestClient

from app.main import app, create_token


def test_get_preferences_requires_auth():
    client = TestClient(app)
    response = client.get('/customers/me/preferences')

    assert response.status_code == 401
    body = response.json()
    assert body['title'] == 'Unauthorized'
    assert body['status'] == 401


def test_get_preferences_returns_current_preferences():
    client = TestClient(app)
    token = create_token('customer-123')

    response = client.get(
        '/customers/me/preferences',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    assert response.json() == {
        'email': False,
        'sms': False,
        'push_notification': False,
    }


def test_update_preferences_persists_and_returns_updated_values():
    client = TestClient(app)
    token = create_token('customer-456')

    response = client.put(
        '/customers/me/preferences',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': True, 'sms': True, 'push_notification': False},
    )

    assert response.status_code == 200
    assert response.json() == {
        'email': True,
        'sms': True,
        'push_notification': False,
    }

    verify = client.get(
        '/customers/me/preferences',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert verify.status_code == 200
    assert verify.json() == {
        'email': True,
        'sms': True,
        'push_notification': False,
    }


def test_customer_cannot_access_other_customer_preferences():
    client = TestClient(app)
    customer_1 = create_token('customer-1')
    customer_2 = create_token('customer-2')

    client.put(
        '/customers/me/preferences',
        headers={'Authorization': f'Bearer {customer_1}'},
        json={'email': True, 'sms': False, 'push_notification': True},
    )

    response = client.get(
        '/customers/me/preferences',
        headers={'Authorization': f'Bearer {customer_2}'},
    )

    assert response.status_code == 200
    assert response.json() == {
        'email': False,
        'sms': False,
        'push_notification': False,
    }
