# backend/tools/recon.py
"""
Security Toolkit de Nex: herramientas de OSINT, forense y reconocimiento de redes.

Todo es pasivo y legal:
  - OSINT usa fuentes públicas (RDAP/WHOIS, Certificate Transparency, DNS).
  - El escaneo de puertos solo funciona contra localhost o hosts en
    NEX_SCAN_ALLOWLIST (lista blanca configurable).
"""
import datetime
import hashlib
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from tools.tool import Tool

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Nex/1.0"


class DnsLookupTool(Tool):
    name = "dns_lookup"
    description = "Resolve DNS records (A, AAAA, MX, NS, TXT, CNAME) for a domain. Useful for OSINT and network recon."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "The domain to resolve, e.g. 'example.com'."},
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Record types to query. Default: A, AAAA, MX, NS, TXT, CNAME.",
                },
            },
            "required": ["domain"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        domain = kwargs["domain"].strip().lower()
        types = [t.upper() for t in (kwargs.get("types") or ["A", "AAAA", "MX", "NS", "TXT", "CNAME"])]

        result: dict[str, Any] = {"domain": domain}
        for rtype in types:
            if rtype in ("A", "AAAA"):
                result[rtype] = self._resolve_address(domain, rtype)
            else:
                result[rtype] = self._query_dig(domain, rtype)
        return {"success": True, **result}

    @staticmethod
    def _resolve_address(domain: str, rtype: str) -> list[str]:
        family = socket.AF_INET if rtype == "A" else socket.AF_INET6
        try:
            infos = socket.getaddrinfo(domain, None, family, socket.SOCK_STREAM)
            return sorted({info[4][0] for info in infos})
        except socket.gaierror:
            return []

    @staticmethod
    def _query_dig(domain: str, rtype: str) -> list[Any]:
        try:
            proc = subprocess.run(
                ["dig", domain, rtype, "+noall", "+answer", "+time=3", "+tries=1"],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        if proc.returncode != 0:
            return []

        records: list[Any] = []
        pattern = re.compile(rf"^\S+\s+\d+\s+IN\s+{rtype}\s+(.+)$")
        for line in proc.stdout.strip().splitlines():
            match = pattern.match(line)
            if not match:
                continue
            value = match.group(1).split()
            if rtype == "MX" and len(value) >= 2:
                try:
                    records.append({"preference": int(value[0]), "exchange": value[1].rstrip(".")})
                    continue
                except ValueError:
                    pass
            records.append(" ".join(value).strip('"').rstrip("."))
        return records


class WhoisLookupTool(Tool):
    name = "whois_lookup"
    description = "Look up domain registration data (registrar, creation/expiry dates, nameservers) using RDAP (modern WHOIS). OSINT."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "The domain to look up, e.g. 'example.com'."},
            },
            "required": ["domain"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        domain = kwargs["domain"].strip().lower()

        data = self._query_rdap(domain)
        if not data:
            data = self._query_whois_command(domain)
        if not data:
            return {
                "success": False,
                "domain": domain,
                "error": "No WHOIS/RDAP data available for this domain.",
            }
        return {"success": True, "domain": domain, **data}

    @staticmethod
    def _query_rdap(domain: str) -> dict[str, Any]:
        url = f"https://rdap.org/domain/{urllib.parse.quote(domain)}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/rdap+json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception:
            return {}

        events = {}
        for ev in data.get("events", []):
            action = ev.get("eventAction", "unknown").replace("event", "")
            events[action] = ev.get("eventDate", "")

        nameservers = []
        for ns in data.get("nameservers", []):
            name = ns.get("ldhName") or ns.get("unicodeName")
            if name:
                nameservers.append(name.rstrip("."))

        return {
            "registrar": WhoisLookupTool._find_registrar(data.get("entities", [])),
            "created": events.get("registration", ""),
            "expires": events.get("expiration", ""),
            "last_changed": events.get("last changed", ""),
            "nameservers": sorted(nameservers),
            "source": "rdap",
        }

    @staticmethod
    def _find_registrar(entities: list[dict[str, Any]]) -> str:
        for ent in entities:
            roles = [r.lower() for r in ent.get("roles", [])]
            if "registrar" in roles:
                vcard = ent.get("vcardArray", [[], []])
                for item in vcard[1] if len(vcard) > 1 else []:
                    if isinstance(item, list) and item and item[0] == "fn":
                        return str(item[3])
        return ""

    @staticmethod
    def _query_whois_command(domain: str) -> dict[str, Any]:
        try:
            proc = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=15)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {}
        out = proc.stdout

        patterns = {
            "registrar": r"(?i)^registrar:\s*(.+)",
            "created": r"(?i)^(?:creation date|created|registered on)\s*:\s*(.+)",
            "expires": r"(?i)^(?:expiry date|expiration date|expires|paid-till)\s*:\s*(.+)",
        }
        parsed = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, out, re.MULTILINE)
            if match:
                parsed[key] = match.group(1).strip()

        nameservers = re.findall(r"(?i)^name server:\s*(.+)", out, re.MULTILINE)
        if nameservers:
            parsed["nameservers"] = sorted({ns.strip().rstrip(".") for ns in nameservers})
            parsed["source"] = "whois"

        return parsed


class SubdomainEnumTool(Tool):
    name = "subdomain_enum"
    description = "Passively enumerate subdomains of a domain using Certificate Transparency logs (crt.sh). OSINT; never contacts the target directly."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "The domain to enumerate, e.g. 'example.com'."},
                "max_results": {"type": "integer", "description": "Maximum subdomains to return (default 50)."},
            },
            "required": ["domain"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        domain = kwargs["domain"].strip().lower()
        max_results = int(kwargs.get("max_results", 50))

        subs: list[str] = []
        for name in self._query_crtsh(domain):
            name = name.strip().lower().rstrip(".")
            if name.endswith("." + domain) and name != domain and name not in subs:
                subs.append(name)
            if len(subs) >= max_results:
                break

        return {
            "success": True,
            "domain": domain,
            "count": len(subs),
            "subdomains": sorted(subs),
            "source": "crt.sh (certificate transparency)",
        }

    @staticmethod
    def _query_crtsh(domain: str) -> list[str]:
        url = f"https://crt.sh/?q=%25.{urllib.parse.quote(domain)}&output=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                entries = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception:
            return []

        names: list[str] = []
        for entry in entries:
            raw = entry.get("name_value", "")
            for name in raw.splitlines():
                name = name.strip()
                if name and name not in names:
                    names.append(name)
        return names


TECH_SIGNATURES: dict[str, list[str]] = {
    "nginx": ["nginx"],
    "apache": ["apache"],
    "microsoft-iis": ["microsoft-iis", "iis/"],
    "cloudflare": ["cloudflare"],
    "openresty": ["openresty"],
    "php": ["php/", "x-powered-by: php"],
    "asp.net": ["x-aspnet-version"],
    "wordpress": ["x-powered-by: wordpress", "wp-content"],
    "drupal": ["x-drupal-cache", "x-generator: drupal"],
    "github-pages": ["x-github-request-id"],
    "laravel": ["laravel"],
}


class HttpFingerprintTool(Tool):
    name = "http_fingerprint"
    description = "Probe an HTTP(S) URL and fingerprint the server: status code, headers, technology stack, final URL after redirects."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to probe, e.g. 'https://example.com'."},
                "timeout": {"type": "integer", "description": "Request timeout in seconds (default 15)."},
            },
            "required": ["url"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        url = kwargs["url"].strip()
        timeout = int(kwargs.get("timeout", 15))
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                final_url = resp.url
                status = resp.status
                body = resp.read(65536)
                headers = {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as e:
            final_url = getattr(e, "url", url)
            status = e.code
            body = b""
            headers = {k.lower(): v for k, v in e.headers.items()}
        except Exception as e:
            return {"success": False, "url": url, "error": str(e)}

        haystack = " ".join(headers.values()).lower()
        haystack += " " + body.decode("utf-8", "ignore").lower()
        technologies = sorted(name for name, needles in TECH_SIGNATURES.items() if any(n in haystack for n in needles))

        return {
            "success": True,
            "url": url,
            "final_url": final_url,
            "status": status,
            "server": headers.get("server", ""),
            "technologies": technologies,
            "headers": headers,
        }


class TlsProbeTool(Tool):
    name = "tls_probe"
    description = "Inspect the TLS certificate of a host: subject, issuer, validity dates, subject alternative names (SANs) and TLS version. Uses raw sockets + ssl."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "Hostname or IP to inspect."},
                "port": {"type": "integer", "description": "TLS port (default 443)."},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 10)."},
            },
            "required": ["host"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        host = kwargs["host"].strip()
        port = int(kwargs.get("port", 443))
        timeout = float(kwargs.get("timeout", 10))

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            with socket.create_connection((host, port), timeout=timeout) as raw:
                with context.wrap_socket(raw, server_hostname=host) as tls:
                    cert = tls.getpeercert()
                    tls_version = tls.version()
        except Exception as e:
            return {"success": False, "host": host, "port": port, "error": str(e)}

        if not cert:
            return {
                "success": True,
                "host": host,
                "port": port,
                "tls_version": tls_version,
                "certificate": None,
                "note": "Certificate not available (self-signed or unusual setup).",
            }

        def _fmt_date(raw: str) -> str:
            try:
                return datetime.datetime.strptime(raw, "%b %d %H:%M:%S %Y %Z").isoformat()
            except Exception:
                return raw

        subject = {k: v for k, v in (x[0] for x in cert.get("subject", ()))}
        issuer = {k: v for k, v in (x[0] for x in cert.get("issuer", ()))}
        sans = [f"{kind}:{value}" for kind, value in cert.get("subjectAltName", ())]

        return {
            "success": True,
            "host": host,
            "port": port,
            "tls_version": tls_version,
            "certificate": {
                "subject": subject,
                "issuer": issuer,
                "valid_from": _fmt_date(cert.get("notBefore", "")),
                "valid_to": _fmt_date(cert.get("notAfter", "")),
                "san": sans,
                "serial": cert.get("serialNumber", ""),
            },
        }


_CRYPT_PREFIXES = [
    ("$2a$", "bcrypt (hashcat -m 3200)", 1.0),
    ("$2b$", "bcrypt (hashcat -m 3200)", 1.0),
    ("$2y$", "bcrypt (hashcat -m 3200)", 1.0),
    ("$1$", "MD5 crypt (hashcat -m 500)", 0.95),
    ("$5$", "SHA-256 crypt (hashcat -m 7400)", 0.95),
    ("$6$", "SHA-512 crypt (hashcat -m 1800)", 0.95),
    ("$apr1$", "Apache MD5 (hashcat -m 1600)", 0.95),
    ("$sha1$", "SHA-1 crypt (hashcat -m 120)", 0.95),
]

_HEX_CANDIDATES = {
    32: [("MD5 (hashcat -m 0)", 0.95), ("NTLM (hashcat -m 1000)", 0.5), ("LM hash", 0.2)],
    40: [("SHA-1 (hashcat -m 100)", 0.95), ("MySQL 5.x (hashcat -m 300)", 0.4)],
    56: [("SHA-224 (hashcat -m 1300)", 0.95)],
    64: [("SHA-256 (hashcat -m 1400)", 0.95), ("SHA3-256 (hashcat -m 5000)", 0.5)],
    96: [("SHA-384 (hashcat -m 10800)", 0.95)],
    128: [("SHA-512 (hashcat -m 1700)", 0.95), ("SHA3-512 (hashcat -m 5100)", 0.5)],
}


class HashIdentifyTool(Tool):
    name = "hash_identify"
    description = "Identify the likely type of a hash (MD5, SHA-1, SHA-256, bcrypt, etc.) by its length, character set and prefix. Forensics."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hash_value": {"type": "string", "description": "The hash to identify."},
            },
            "required": ["hash_value"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        value = kwargs["hash_value"].strip()
        candidates: list[dict[str, Any]] = []

        for prefix, name, confidence in _CRYPT_PREFIXES:
            if value.startswith(prefix):
                candidates.append({"name": name, "confidence": confidence})

        is_hex = bool(re.fullmatch(r"[0-9a-fA-F]+", value))
        if is_hex:
            for length, possible in _HEX_CANDIDATES.items():
                if len(value) == length:
                    for name, confidence in possible:
                        candidates.append({"name": name, "confidence": confidence})

        if not candidates:
            candidates.append({"name": "Unknown / custom format", "confidence": 0.1})

        return {
            "success": True,
            "length": len(value),
            "hex": is_hex,
            "possible_types": candidates,
            "note": "Confidence is a heuristic: verify with 'hashcat --identify' or crack with hashcat using the suggested mode.",
        }


MAGIC_SIGNATURES = [
    (b"\x7fELF", "ELF executable (Linux)", "application/x-executable"),
    (b"MZ", "PE executable (Windows)", "application/x-dosexec"),
    (b"\x89PNG\r\n\x1a\n", "PNG image", "image/png"),
    (b"\xff\xd8\xff", "JPEG image", "image/jpeg"),
    (b"PK\x03\x04", "ZIP archive", "application/zip"),
    (b"%PDF-", "PDF document", "application/pdf"),
    (b"GIF8", "GIF image", "image/gif"),
    (b"\x1f\x8b", "GZIP compressed", "application/gzip"),
    (b"#!", "Script with shebang", "text/plain"),
]


class FileMetadataTool(Tool):
    name = "file_metadata"
    description = "Extract forensic metadata from a file: type (magic bytes), size, timestamps, hashes (SHA-256/SHA-1/MD5) and printable strings."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file (absolute or workspace-relative)."},
                "extract_strings": {"type": "boolean", "description": "Also extract printable strings (default false)."},
                "max_strings": {"type": "integer", "description": "Maximum strings to extract (default 20)."},
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        workspace_root = kwargs.get("workspace_root")
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(workspace_root or ".", path))
        if not os.path.isfile(path):
            return {"success": False, "path": path, "error": f"File not found: {path}"}

        st = os.stat(path)
        result: dict[str, Any] = {
            "path": path,
            "size": st.st_size,
            "magic": self._detect_type(path)[0],
            "mime": self._detect_type(path)[1],
            "hashes": self._hash_file(path),
            "created": datetime.datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "modified": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if kwargs.get("extract_strings"):
            result["strings"] = self._extract_strings(path, int(kwargs.get("max_strings", 20)))

        return {"success": True, **result}

    @staticmethod
    def _detect_type(path: str) -> tuple[str, str]:
        with open(path, "rb") as f:
            head = f.read(16)
        for signature, name, mime in MAGIC_SIGNATURES:
            if head.startswith(signature):
                return name, mime
        return "Unknown / plain data", "application/octet-stream"

    @staticmethod
    def _hash_file(path: str) -> dict[str, str]:
        sha256, sha1, md5 = hashlib.sha256(), hashlib.sha1(), hashlib.md5()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
                sha1.update(chunk)
                md5.update(chunk)
        return {"sha256": sha256.hexdigest(), "sha1": sha1.hexdigest(), "md5": md5.hexdigest()}

    @staticmethod
    def _extract_strings(path: str, max_strings: int) -> list[str]:
        with open(path, "rb") as f:
            data = f.read(65536)
        strings = re.findall(rb"[\x20-\x7e]{4,}", data)
        return [s.decode("ascii", "ignore") for s in strings[:max_strings]]


COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
                1723, 3306, 3389, 5432, 5900, 6379, 8000, 8080, 8443, 8888, 9200, 27017]

PORT_SERVICES = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http",
    110: "pop3", 143: "imap", 443: "https", 445: "smb", 631: "ipp", 993: "imaps",
    995: "pop3s", 1723: "pptp", 3306: "mysql", 3389: "rdp", 5432: "postgresql",
    5900: "vnc", 6379: "redis", 8080: "http-alt", 8443: "https-alt",
    9200: "elasticsearch", 27017: "mongodb",
}


def _parse_allowlist(raw: str) -> list[ipaddress.IPv4Network]:
    networks = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return networks


class PortScanTool(Tool):
    name = "port_scan"
    description = "TCP connect scan of a host. Only allowed on loopback addresses or hosts inside NEX_SCAN_ALLOWLIST. Use only on systems you own or have explicit permission to test."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "IP or hostname to scan (default 127.0.0.1)."},
                "ports": {"type": "array", "items": {"type": "integer"}, "description": "Ports to scan (default: common ports)."},
                "timeout": {"type": "number", "description": "Connect timeout per port in seconds (default 1.0)."},
                "concurrency": {"type": "integer", "description": "Parallel connections (default 32)."},
            },
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        target = kwargs.get("target", "127.0.0.1").strip()
        ports = [int(p) for p in (kwargs.get("ports") or COMMON_PORTS)]
        timeout = float(kwargs.get("timeout", 1.0))
        concurrency = int(kwargs.get("concurrency", 32))

        allowed, reason, ip = self._check_scope(target)
        if not allowed:
            return {"success": False, "target": target, "error": reason}

        start = time.monotonic()
        open_ports = self._scan(str(ip), ports, timeout, concurrency)
        elapsed = round(time.monotonic() - start, 2)

        return {
            "success": True,
            "target": target,
            "open_ports": [{"port": p, "service": PORT_SERVICES.get(p, "")} for p in open_ports],
            "open_count": len(open_ports),
            "scanned": len(ports),
            "scan_time": elapsed,
            "note": "TCP connect scan, limited to authorized scope.",
        }

    @staticmethod
    def _check_scope(target: str) -> tuple[bool, str, ipaddress.IPv4Address]:
        try:
            ip = ipaddress.ip_address(target)
        except ValueError:
            try:
                resolved = socket.getaddrinfo(target, None, socket.AF_INET)
                ip = ipaddress.ip_address(resolved[0][4][0])
            except Exception:
                return False, f"Could not resolve or parse target '{target}'.", ipaddress.ip_address("0.0.0.0")

        if ip.is_loopback:
            return True, "", ip

        from storage.settings import get_settings
        networks = _parse_allowlist(os.environ.get("NEX_SCAN_ALLOWLIST", ""))
        networks += _parse_allowlist(get_settings().get("scan_allowlist", ""))
        for net in networks:
            if ip in net:
                return True, "", ip

        return False, (
            f"Target {ip} is outside the authorized scan scope. Add it to the 'scan_allowlist' "
            f"setting or set NEX_SCAN_ALLOWLIST. Example: 192.168.1.0/24,10.0.0.5"
        ), ip

    @staticmethod
    def _scan(ip: str, ports: list[int], timeout: float, concurrency: int) -> list[int]:
        open_ports: list[int] = []
        lock = threading.Lock()

        def check(port: int) -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                if sock.connect_ex((ip, port)) == 0:
                    with lock:
                        open_ports.append(port)

        with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(ports)))) as executor:
            list(executor.map(check, ports))
        return sorted(open_ports)
