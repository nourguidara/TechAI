from unittest.mock import patch,MagicMock
from backend.schemas import OrderInput,EmailInput
from backend.services.orders import create_purchase_order
from backend.services.email import send_confirmation_email
from tests.test_orders import approved

def test_email_idempotent():
    p=approved(); o=create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
    smtp=MagicMock()
    with patch('smtplib.SMTP',return_value=smtp):
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='sent'
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='sent'
    assert smtp.__enter__.return_value.send_message.call_count==1
    msg=smtp.__enter__.return_value.send_message.call_args.args[0]
    assert msg['To']=='student@example.com'

def test_email_failure_preserves_order():
    p=approved(); o=create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
    with patch('smtplib.SMTP',side_effect=ConnectionRefusedError):
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='failed'
    assert create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))['id']==o['id']


def test_email_ambiguous():
    p=approved(); o=create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
    smtp=MagicMock(); smtp.__enter__.return_value.send_message.side_effect=TimeoutError
    with patch('smtplib.SMTP',return_value=smtp):
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='delivery_unknown'
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='delivery_unknown'
    assert smtp.__enter__.return_value.send_message.call_count==1


def test_real_email_tls_auth_and_idempotency(monkeypatch, capsys, caplog):
    from backend.config import settings
    monkeypatch.setattr(settings, 'email_mode', 'real')
    monkeypatch.setattr(settings, 'smtp_host', 'smtp.gmail.com')
    monkeypatch.setattr(settings, 'smtp_port', 587)
    monkeypatch.setattr(settings, 'smtp_user', 'sender@example.com')
    monkeypatch.setattr(settings, 'smtp_password', 'synthetic-test-password')
    monkeypatch.setattr(settings, 'smtp_allowed_recipients', 'student@example.com')
    p=approved(); o=create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
    smtp=MagicMock()
    with patch('smtplib.SMTP', return_value=smtp) as connect:
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='sent'
        assert send_confirmation_email(EmailInput(order_id=o['id']))['status']=='sent'
    connect.assert_called_once_with('smtp.gmail.com', 587, timeout=10)
    client=smtp.__enter__.return_value
    client.starttls.assert_called_once_with()
    client.login.assert_called_once_with('sender@example.com', 'synthetic-test-password')
    assert [call[0] for call in client.method_calls] == ['starttls', 'login', 'send_message']
    assert client.send_message.call_args.args[0]['To']=='student@example.com'
    output=capsys.readouterr()
    assert 'synthetic-test-password' not in output.out + output.err + caplog.text


def test_real_email_rejects_unauthorized_recipient(monkeypatch):
    import pytest
    from backend.config import settings
    monkeypatch.setattr(settings, 'email_mode', 'real')
    monkeypatch.setattr(settings, 'smtp_allowed_recipients', 'someone-else@example.com')
    p=approved(); o=create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
    with patch('smtplib.SMTP') as connect:
        with pytest.raises(ValueError, match='recipient_not_authorized'):
            send_confirmation_email(EmailInput(order_id=o['id']))
        connect.assert_not_called()
