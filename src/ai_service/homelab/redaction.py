from __future__ import annotations

import hashlib
import hmac
import re


SECRET_KEYWORDS_RE = re.compile(
    r"(?i)(api[-_]?key|secret|token|password|passwd|private[-_]?key)(\s*[:=]\s*)[\"']?([a-zA-Z0-9_\-\.\/]{8,})[\"']?"
)
IP_ADDRESS_RE = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")


def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected_sig = signature_header[len("sha256="):]
    computed_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_sig, expected_sig)


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_secrets(text: str) -> str:
    text = SECRET_KEYWORDS_RE.sub(r"\1\2<REDACTED_SECRET>", text)

    def ip_replacer(match: re.Match) -> str:
        ip = match.group(0)
        if ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.31.")):
            return ip
        return "<REDACTED_IP>"

    return IP_ADDRESS_RE.sub(ip_replacer, text)
