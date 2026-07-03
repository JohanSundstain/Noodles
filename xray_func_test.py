import subprocess

import pytest

from xray import create_external_user, load_user_dict, load_user_link, remove_external_user


class DummyPopen:
    def __init__(self, stdout, stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def communicate(self, input=None, timeout=None):
        return self.stdout, self.stderr


def test_load_user_dict_success(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=['userlist'], returncode=0, stdout='1. alice\n2. bob\n', stderr=''  # type: ignore[arg-type]
    )

    monkeypatch.setattr('xray.subprocess.run', lambda *args, **kwargs: completed)

    assert load_user_dict() == {'alice': 1, 'bob': 2}


def test_load_user_dict_failure(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=['userlist'], returncode=1, stdout='', stderr='error'  # type: ignore[arg-type]
    )

    monkeypatch.setattr('xray.subprocess.run', lambda *args, **kwargs: completed)

    assert load_user_dict() == {}


def test_load_user_link_success(monkeypatch):
    monkeypatch.setattr('xray.subprocess.Popen', lambda *args, **kwargs: DummyPopen('vless://token', '', 0))

    assert load_user_link(42) == 'vless://token'


def test_load_user_link_no_url(monkeypatch):
    monkeypatch.setattr('xray.subprocess.Popen', lambda *args, **kwargs: DummyPopen('no-link-here', '', 0))

    assert load_user_link(42) is None


def test_load_user_link_failure(monkeypatch):
    monkeypatch.setattr('xray.subprocess.Popen', lambda *args, **kwargs: DummyPopen('', 'error', 1))

    assert load_user_link(42) is None


def test_create_external_user_success(monkeypatch):
    def fake_run(*args, **kwargs):
        assert kwargs['input'] == '123\n'
        return subprocess.CompletedProcess(
            args=['newuser'], returncode=0, stdout='vless://created', stderr=''  # type: ignore[arg-type]
        )

    monkeypatch.setattr('xray.subprocess.run', fake_run)

    assert create_external_user(123) == 'vless://created'


def test_create_external_user_failure(monkeypatch):
    monkeypatch.setattr(
        'xray.subprocess.run',
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=['newuser'], returncode=1, stdout='', stderr='failed'  # type: ignore[arg-type]
        )
    )

    assert create_external_user(123) is None


def test_remove_external_user_success(monkeypatch):
    monkeypatch.setattr(
        'xray.subprocess.run',
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=['rmuser'], returncode=0, stdout='', stderr=''  # type: ignore[arg-type]
        )
    )

    assert remove_external_user(5) is True


def test_remove_external_user_failure(monkeypatch):
    monkeypatch.setattr(
        'xray.subprocess.run',
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=['rmuser'], returncode=2, stdout='', stderr='error'  # type: ignore[arg-type]
        )
    )

    assert remove_external_user(5) is False


def test_remove_external_user_exception(monkeypatch):
    def fake_run(*args, **kwargs):
        raise RuntimeError('process error')

    monkeypatch.setattr('xray.subprocess.run', fake_run)
    assert remove_external_user(5) is False
