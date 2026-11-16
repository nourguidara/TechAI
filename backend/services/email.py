import smtplib
from email.message import EmailMessage
from sqlalchemy import select, text
from backend.config import settings
from backend.database import Session
from backend.models import Notification, Order, now

def send_confirmation_email(data):
    # Claim durably before SMTP. An interrupted send is ambiguous and is never auto-retried.
    with Session() as db:
        db.execute(text('BEGIN IMMEDIATE'))
        n=db.scalar(select(Notification).where(Notification.order_id==data.order_id))
        o=db.get(Order,data.order_id)
        if not n or not o or o.approval_status!='approved': raise ValueError('approved_order_required')
        if n.status in ('sent','sending','delivery_unknown'): return dict(status=n.status)
        if settings.email_mode=='sandbox' and settings.smtp_host not in ('localhost','127.0.0.1','mailpit'):
            raise ValueError('sandbox_smtp_host_not_allowed')
        if settings.email_mode not in ('sandbox','real'): raise ValueError('invalid_email_mode')
        if settings.email_mode=='real' and n.recipient not in settings.smtp_allowed_recipients.split(','):
            raise ValueError('recipient_not_authorized')
        msg=EmailMessage(); msg['From']=settings.smtp_from; msg['To']=n.recipient
        msg['Subject']='TechStock AI - Purchase Order Confirmation ['+o.order_reference+']'
        msg['Message-ID']='<'+n.idempotency_key+'@techstock.test>'
        lines=[o.order_reference,str(o.created_at),'Internal sandbox order. No retailer purchase submitted.']
        lines += [f'{i.product_name_snapshot} | {i.supplier_snapshot} | {i.quantity} x {i.unit_price_tnd} TND' for i in o.items]
        lines += [f'Total: {o.total_amount_tnd} TND']
        msg.set_content('\n'.join(lines))
        n.status='sending'; n.attempts+=1; nid=n.id; db.commit()
    connected=False
    try:
        with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as smtp:
            if settings.email_mode=='real':
                smtp.starttls()
                if settings.smtp_user: smtp.login(settings.smtp_user,settings.smtp_password)
            connected=True
            smtp.send_message(msg)
        status,error='sent',None
    except Exception as exc:
        status='delivery_unknown' if connected else 'failed'
        error=type(exc).__name__
    with Session.begin() as db:
        n=db.get(Notification,nid); n.status=status; n.last_error=error
        if status=='sent': n.sent_at=now()
    return dict(status=status,error=error)
