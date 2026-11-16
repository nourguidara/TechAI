"""Local-only SMTP capture fallback when Docker/Mailpit is unavailable."""
import asyncio,uuid
from pathlib import Path
from aiosmtpd.controller import Controller
class Capture:
    async def handle_DATA(self,server,session,envelope):
        directory=Path('data/mail'); directory.mkdir(parents=True,exist_ok=True)
        (directory/(uuid.uuid4().hex+'.eml')).write_bytes(envelope.original_content)
        return '250 Stored locally; no external delivery'
if __name__=='__main__':
    controller=Controller(Capture(),hostname='127.0.0.1',port=1025)
    controller.start()
    print('SMTP sandbox listening on 127.0.0.1:1025; messages saved in data/mail',flush=True)
    try: asyncio.run(asyncio.Event().wait())
    except KeyboardInterrupt: pass
    finally: controller.stop()
