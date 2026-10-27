import pytest
from app.models.user import User, UserRole, ApprovalStatus
from app.core.security import create_access_token


def test_public_registration_creates_pending_account(client, db):
    payload = {
        "full_name": "New Candidate",
        "email": "candidate@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "agent"
    assert data["approval_status"] == "pending"
    assert data["email"] == "candidate@example.com"

    # Verify directly in DB
    user = db.query(User).filter(User.email == "candidate@example.com").first()
    assert user is not None
    assert user.role == UserRole.AGENT.value
    assert user.approval_status == ApprovalStatus.PENDING.value


def test_public_registration_cannot_self_assign_admin(client, db):
    payload = {
        "full_name": "Attacker",
        "email": "attacker@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "role": "admin",  # Attacker attempts privilege escalation
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    # Must strictly be assigned agent role regardless of payload
    assert data["role"] == "agent"
    assert data["approval_status"] == "pending"


def test_pending_user_cannot_login_or_access_crm(client, pending_user):
    # Attempt login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": pending_user.email, "password": "Password123!"},
    )
    assert login_resp.status_code == 403
    assert "pending approval" in login_resp.json()["detail"].lower()

    # Attempt direct token access
    token = create_access_token(subject=pending_user.id, role=pending_user.role)
    leads_resp = client.get(
        "/api/v1/leads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert leads_resp.status_code == 403
    assert "pending approval" in leads_resp.json()["detail"].lower()


def test_admin_approval_grants_agent_role(client, admin_token, pending_user, db):
    # Admin approves pending user
    response = client.put(
        f"/api/v1/users/{pending_user.id}/approval",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"action": "approve"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["approval_status"] == "approved"
    assert data["role"] == "agent"

    # Now the approved user can log in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": pending_user.email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_deactivated_account_loses_access(client, deactivated_user, db):
    # Deactivated user cannot log in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": deactivated_user.email, "password": "Password123!"},
    )
    assert login_resp.status_code == 403
    assert "deactivated" in login_resp.json()["detail"].lower()

    # Existing active token also gets rejected
    token = create_access_token(subject=deactivated_user.id, role=deactivated_user.role)
    leads_resp = client.get(
        "/api/v1/leads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert leads_resp.status_code == 403
    assert "deactivated" in leads_resp.json()["detail"].lower()
