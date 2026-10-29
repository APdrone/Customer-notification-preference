import pytest
from fastapi.testclient import TestClient
from app.main import app, create_token, ADDRESS_STORE, DRAFT_FORM_STORE, Address

@pytest.fixture(autouse=True)
def reset_stores():
    ADDRESS_STORE.clear()
    DRAFT_FORM_STORE.clear()
    yield
    ADDRESS_STORE.clear()
    DRAFT_FORM_STORE.clear()

class TestGetCustomerAddress:
    def test_get_address_requires_authentication(self):
        client = TestClient(app)
        response = client.get("/customers/me/address")
        assert response.status_code == 401
        body = response.json()
        assert body["title"] == "Unauthorized"
        assert body["status"] == 401
        assert body["detail"] == "Authentication credentials were not provided or are invalid."
        assert body["instance"] == "/customers/me/address"
        assert "type" in body

    def test_get_address_returns_default_empty_address_for_new_customer(self):
        client = TestClient(app)
        token = create_token("customer-new")
        response = client.get("/customers/me/address", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        address_data = response.json()
        assert address_data == {"street": "", "city": "", "state": "", "postal_code": "", "country": ""}

    def test_get_address_returns_stored_address(self):
        client = TestClient(app)
        customer_id = "customer-789"
        token = create_token(customer_id)
        ADDRESS_STORE[customer_id] = Address(street="456 Oak Ave", city="Portland", state="OR", postal_code="97201", country="USA")
        response = client.get("/customers/me/address", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        address_data = response.json()
        assert address_data == {"street": "456 Oak Ave", "city": "Portland", "state": "OR", "postal_code": "97201", "country": "USA"}

class TestCopyAddressFromProfile:
    def test_copy_address_requires_authentication(self):
        client = TestClient(app)
        draft_id = "draft-003"
        response = client.post(f"/forms/{draft_id}/address:copyFromProfile")
        assert response.status_code == 401
        body = response.json()
        assert body["title"] == "Unauthorized"
        assert body["status"] == 401

    def test_copy_address_success_with_stored_address(self):
        client = TestClient(app)
        customer_id = "customer-123"
        draft_id = "draft-001"
        token = create_token(customer_id)
        ADDRESS_STORE[customer_id] = Address(street="123 Main St", city="Springfield", state="IL", postal_code="62701", country="USA")
        response = client.post(f"/forms/{draft_id}/address:copyFromProfile", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        body = response.json()
        assert body["draft_id"] == draft_id
        assert body["status"] == "copied"
        assert body["address"] == {"street": "123 Main St", "city": "Springfield", "state": "IL", "postal_code": "62701", "country": "USA"}
        assert draft_id in DRAFT_FORM_STORE
        assert DRAFT_FORM_STORE[draft_id]["customer_id"] == customer_id

    def test_copy_address_with_empty_default_address(self):
        client = TestClient(app)
        customer_id = "customer-456"
        draft_id = "draft-002"
        token = create_token(customer_id)
        response = client.post(f"/forms/{draft_id}/address:copyFromProfile", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        body = response.json()
        assert body["draft_id"] == draft_id
        assert body["status"] == "copied"
        assert body["address"] == {"street": "", "city": "", "state": "", "postal_code": "", "country": ""}

    def test_copy_address_isolates_draft_data_between_customers(self):
        client = TestClient(app)
        customer_1_id = "customer-draft-1"
        customer_2_id = "customer-draft-2"
        draft_1 = "draft-isolate-1"
        draft_2 = "draft-isolate-2"
        ADDRESS_STORE[customer_1_id] = Address(street="Customer 1 Street", city="City 1", state="CA", postal_code="90001", country="USA")
        ADDRESS_STORE[customer_2_id] = Address(street="Customer 2 Street", city="City 2", state="TX", postal_code="75001", country="USA")
        token_1 = create_token(customer_1_id)
        response_1 = client.post(f"/forms/{draft_1}/address:copyFromProfile", headers={"Authorization": f"Bearer {token_1}"})
        assert response_1.status_code == 200
        assert response_1.json()["address"]["street"] == "Customer 1 Street"
        token_2 = create_token(customer_2_id)
        response_2 = client.post(f"/forms/{draft_2}/address:copyFromProfile", headers={"Authorization": f"Bearer {token_2}"})
        assert response_2.status_code == 200
        assert response_2.json()["address"]["street"] == "Customer 2 Street"
        assert DRAFT_FORM_STORE[draft_1]["customer_id"] == customer_1_id
        assert DRAFT_FORM_STORE[draft_2]["customer_id"] == customer_2_id

class TestEndToEndWorkflow:
    def test_complete_address_workflow(self):
        client = TestClient(app)
        customer_id = "customer-workflow"
        draft_id = "draft-workflow"
        token = create_token(customer_id)
        ADDRESS_STORE[customer_id] = Address(street="789 Workflow Blvd", city="Integration", state="FL", postal_code="33101", country="USA")
        get_response = client.get("/customers/me/address", headers={"Authorization": f"Bearer {token}"})
        assert get_response.status_code == 200
        retrieved_address = get_response.json()
        assert retrieved_address["street"] == "789 Workflow Blvd"
        copy_response = client.post(f"/forms/{draft_id}/address:copyFromProfile", headers={"Authorization": f"Bearer {token}"})
        assert copy_response.status_code == 200
        copy_body = copy_response.json()
        assert copy_body["draft_id"] == draft_id
        assert copy_body["status"] == "copied"
        assert copy_body["address"] == retrieved_address
        assert draft_id in DRAFT_FORM_STORE
        assert DRAFT_FORM_STORE[draft_id]["address"] == retrieved_address
