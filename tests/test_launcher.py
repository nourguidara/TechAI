import os
from unittest.mock import MagicMock

import pytest

from scripts import run


@pytest.mark.parametrize('mode,expected_count', [('sandbox', 3), ('real', 2), (None, 3)])
def test_launcher_email_modes(monkeypatch, tmp_path, capsys, caplog, mode, expected_count):
    monkeypatch.chdir(tmp_path)
    for key in ('EMAIL_MODE', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_PASSWORD'):
        monkeypatch.delenv(key, raising=False)
    lines = ['SMTP_HOST=smtp.gmail.com', 'SMTP_PORT=587', 'SMTP_PASSWORD=synthetic-test-password']
    if mode is not None:
        lines.insert(0, 'EMAIL_MODE=' + mode)
    (tmp_path / '.env').write_text('\n'.join(lines), encoding='utf-8')
    launches = []

    def start(command):
        launches.append((command, os.environ['SMTP_HOST'], os.environ['SMTP_PORT']))
        process = MagicMock()
        process.poll.return_value = 0
        return process

    monkeypatch.setattr(run.subprocess, 'Popen', start)
    run.main()

    commands = [item[0] for item in launches]
    assert len(commands) == expected_count
    local_server = [c for c in commands if 'sandbox.mail_server' in c]
    assert len(local_server) == (0 if mode == 'real' else 1)
    assert any('uvicorn' in c for c in commands)
    assert any('streamlit' in c for c in commands)
    expected = ('smtp.gmail.com', '587') if mode == 'real' else ('127.0.0.1', '1025')
    assert all((host, port) == expected for _, host, port in launches)
    assert (os.environ['SMTP_HOST'], os.environ['SMTP_PORT']) == expected
    output = capsys.readouterr()
    assert 'synthetic-test-password' not in output.out + output.err + caplog.text
    assert all('synthetic-test-password' not in ' '.join(c) for c in commands)
