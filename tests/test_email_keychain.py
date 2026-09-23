"""The email password can come from the macOS Keychain instead of .env."""

import subprocess

from src import email_sender


def _fake_run(stdout, returncode=0):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")
    return run


def test_keychain_used_when_env_is_empty(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("EMAIL_ADDRESS", "me@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "")
    monkeypatch.setattr(email_sender.subprocess, "run", _fake_run("abcd efgh ijkl mnop\n"))
    assert email_sender._smtp_config()["password"] == "abcd efgh ijkl mnop"


def test_env_wins_over_keychain(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("EMAIL_PASSWORD", "from-env")
    monkeypatch.setattr(email_sender.subprocess, "run", _fake_run("from-keychain"))
    assert email_sender._smtp_config()["password"] == "from-env"


def test_missing_keychain_entry_is_none(monkeypatch):
    monkeypatch.setattr(email_sender.subprocess, "run", _fake_run("", returncode=44))
    assert email_sender._keychain_password() is None
