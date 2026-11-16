import socket
from aiosmtpd.controller import Controller
from backend.config import settings
from backend.schemas import OrderInput,EmailInput
from backend.services.orders import create_purchase_order
from backend.services.email import send_confirmation_email
from tests.test_orders import approved

def test_actual_local_smtp(monkeypatch):
    received=[]
    class Capture:
        async def handle_DATA(self,server,session,envelope):
            received.append(envelope); return '250 OK'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    server=Controller(Capture(),hostname='127.0.0.1',port=port); server.start()
    monkeypatch.setattr(settings,'smtp_host','127.0.0.1'); monkeypatch.setattr(settings,'smtp_port',port)
    try:
        p=approved(); o=create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='sent'
        assert len(received)==1
        assert received[0].rcpt_tos==['student@example.com']
        assert b'Internal sandbox order' in received[0].original_content
    finally: server.stop()
