import os
import socket
import tempfile

import tools.recon as recon
from tools.recon import (
    DnsLookupTool,
    FileMetadataTool,
    HashIdentifyTool,
    PortScanTool,
    SubdomainEnumTool,
    TlsProbeTool,
    WhoisLookupTool,
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self, *args):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_hash_identify_md5():
    result = HashIdentifyTool().execute(hash_value="5f4dcc3b5aa765d61d8327deb882cf99")
    assert result["success"] is True
    assert "MD5" in " ".join(t["name"] for t in result["possible_types"])
    assert result["length"] == 32


def test_hash_identify_sha256():
    result = HashIdentifyTool().execute(hash_value="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")
    assert "SHA-256" in " ".join(t["name"] for t in result["possible_types"])


def test_hash_identify_bcrypt():
    value = "$2b$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW"
    result = HashIdentifyTool().execute(hash_value=value)
    assert "bcrypt" in " ".join(t["name"] for t in result["possible_types"])


def test_dns_lookup_localhost_offline():
    result = DnsLookupTool().execute(domain="localhost", types=["A"])
    assert result["success"] is True
    assert "127.0.0.1" in result["A"]


def test_subdomain_enum_crtsh(monkeypatch):
    fake = b'[{"name_value": "www.example.com\\nmail.example.com"}, {"name_value": "example.com"}]'
    monkeypatch.setattr(recon.urllib.request, "urlopen", lambda *a, **k: FakeResponse(fake))
    result = SubdomainEnumTool().execute(domain="example.com")
    assert result["success"] is True
    assert "www.example.com" in result["subdomains"]
    assert "mail.example.com" in result["subdomains"]
    assert result["count"] == 2


def test_whois_lookup_rdap(monkeypatch):
    fake = (
        b'{"events": [{"eventAction": "registration", "eventDate": "1995-08-14"}],'
        b'"nameservers": [{"ldhName": "A.IANA-SERVERS.NET."}],'
        b'"entities": [{"roles": ["registrar"], "vcardArray": ["vcard",'
        b'[["fn", {}, "text", "IANA"]]]}]}'
    )
    monkeypatch.setattr(recon.urllib.request, "urlopen", lambda *a, **k: FakeResponse(fake))
    result = WhoisLookupTool().execute(domain="example.com")
    assert result["success"] is True
    assert result["registrar"] == "IANA"
    assert result["nameservers"] == ["A.IANA-SERVERS.NET"]
    assert result["created"] == "1995-08-14"


def test_file_metadata():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"PNG_DATA_HERE_0" * 10)
        path = f.name
    try:
        result = FileMetadataTool().execute(path=path, extract_strings=True)
        assert result["success"] is True
        assert result["magic"] == "PNG image"
        assert result["mime"] == "image/png"
        assert len(result["hashes"]["sha256"]) == 64
        assert any("PNG" in s for s in result["strings"])
    finally:
        os.unlink(path)


def test_file_metadata_missing():
    result = FileMetadataTool().execute(path="/nonexistent/archivo.bin")
    assert result["success"] is False


def test_port_scan_rejects_external_target():
    result = PortScanTool().execute(target="example.com", ports=[80])
    assert result["success"] is False
    assert ("NEX_SCAN_ALLOWLIST" in result["error"]
            or "Could not resolve" in result["error"])


def test_port_scan_finds_open_port():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        result = PortScanTool().execute(target="127.0.0.1", ports=[port], timeout=0.5)
        assert result["success"] is True
        assert any(p["port"] == port for p in result["open_ports"])
    finally:
        listener.close()


def test_port_scan_allowlist(monkeypatch):
    monkeypatch.setenv("NEX_SCAN_ALLOWLIST", "10.0.0.0/8,192.168.1.5")
    result = PortScanTool().execute(target="10.0.0.99", ports=[22], timeout=0.3)
    assert result["success"] is True
    assert result["scanned"] == 1


def test_tls_probe_connection_refused():
    result = TlsProbeTool().execute(host="127.0.0.1", port=1, timeout=1)
    assert result["success"] is False


def test_registry_has_recon_tools():
    from tools.registry import create_default_registry
    registry = create_default_registry()
    for name in ("dns_lookup", "whois_lookup", "http_fingerprint",
                 "tls_probe", "hash_identify", "file_metadata"):
        assert registry.get(name) is not None
