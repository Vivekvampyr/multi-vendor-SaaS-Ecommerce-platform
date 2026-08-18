import pytest
from starlette.websockets import WebSocketDisconnect
from app.core.security import create_access_token


def test_rest_chat_endpoints_lifecycle(
    client,
    customer_headers,
    vendor_headers,
    test_customer,
    test_vendor,
):
    # 1. Customer sends message to vendor via REST
    msg_payload = {
        "receiver_id": test_vendor.id,
        "vendor_id": test_vendor.id,
        "message": "Hello vendor, is this product available in blue?",
    }
    send_resp = client.post("/api/v1/chat/messages", json=msg_payload, headers=customer_headers)
    assert send_resp.status_code == 201
    msg_data = send_resp.json()["data"]
    assert msg_data["sender_id"] == test_customer.id
    assert msg_data["receiver_id"] == test_vendor.id
    assert msg_data["is_read"] is False

    # 2. Check vendor's unread count
    unread_resp = client.get("/api/v1/chat/unread-count", headers=vendor_headers)
    assert unread_resp.status_code == 200
    assert unread_resp.json()["data"]["total_unread"] == 1

    # 3. Vendor views conversation list
    conv_resp = client.get("/api/v1/chat/conversations", headers=vendor_headers)
    assert conv_resp.status_code == 200
    conversations = conv_resp.json()["data"]
    assert len(conversations) == 1
    assert conversations[0]["other_user_id"] == test_customer.id
    assert conversations[0]["unread_count"] == 1

    # 4. Vendor fetches message history with customer
    hist_resp = client.get(f"/api/v1/chat/history/{test_customer.id}", headers=vendor_headers)
    assert hist_resp.status_code == 200
    messages = hist_resp.json()["data"]
    assert len(messages) == 1
    assert messages[0]["message"] == "Hello vendor, is this product available in blue?"

    # 5. Vendor marks messages as read
    read_resp = client.put(f"/api/v1/chat/read/{test_customer.id}", headers=vendor_headers)
    assert read_resp.status_code == 200

    # 6. Check unread count is now 0
    unread_resp_after = client.get("/api/v1/chat/unread-count", headers=vendor_headers)
    assert unread_resp_after.json()["data"]["total_unread"] == 0

    # 7. Vendor replies back
    reply_payload = {
        "receiver_id": test_customer.id,
        "vendor_id": test_vendor.id,
        "message": "Yes, we have 5 units of blue available in stock!",
    }
    reply_resp = client.post("/api/v1/chat/messages", json=reply_payload, headers=vendor_headers)
    assert reply_resp.status_code == 201


def test_send_message_to_self_fails(client, customer_headers, test_customer):
    payload = {
        "receiver_id": test_customer.id,
        "vendor_id": test_customer.id,
        "message": "Talking to myself",
    }
    resp = client.post("/api/v1/chat/messages", json=payload, headers=customer_headers)
    assert resp.status_code == 400


def test_websocket_chat_authentication_and_live_messaging(
    client,
    test_customer,
    test_vendor,
):
    customer_token = create_access_token(subject=test_customer.id, role=test_customer.role.value)

    # 1. Connect without token -> Should close with 1008
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/chat/ws") as ws:
            pass

    # 2. Connect with valid customer token
    with client.websocket_connect(f"/api/v1/chat/ws?token={customer_token}") as ws:
        # Receive connection acknowledgement
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"
        assert welcome["user_id"] == test_customer.id

        # Send heartbeat ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"

        # Send live message to vendor
        ws.send_json({
            "receiver_id": test_vendor.id,
            "vendor_id": test_vendor.id,
            "message": "Hello from WebSocket live chat!",
        })

        # Receive ACK packet
        ack = ws.receive_json()
        assert ack["type"] == "ack"
        assert ack["message"]["message"] == "Hello from WebSocket live chat!"
        assert ack["message"]["sender_id"] == test_customer.id
