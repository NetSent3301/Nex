# Security Toolkit de Nex

Módulo `backend/tools/recon.py` — herramientas de **OSINT, forense y reconocimiento de redes** para el agente Nex.

Todo es **pasivo y legal**: OSINT usa fuentes públicas y el escaneo de puertos está limitado por scope.

## Herramientas

| Tool | Categoría | Qué hace |
|---|---|---|
| `dns_lookup` | OSINT | Resuelve registros A, AAAA, MX, NS, TXT, CNAME |
| `whois_lookup` | OSINT | Datos de registro del dominio (RDAP/WHOIS) |
| `subdomain_enum` | OSINT | Enumeración pasiva vía crt.sh (Certificate Transparency) |
| `http_fingerprint` | Redes | Headers HTTP, servidor, tecnologías detectadas |
| `tls_probe` | Redes | Certificado TLS: emisor, validez, SANs |
| `hash_identify` | Forense | Identifica el tipo de hash por formato/longitud |
| `file_metadata` | Forense | Magic bytes, MIME, hashes, timestamps, strings |
| `port_scan` | Redes | Escaneo TCP connect (solo scope autorizado) |

## Ejemplos de uso

Puedes probarlas desde Python (o pídeselo directamente a Nex en el chat):

```python
from tools.recon import DnsLookupTool, HashIdentifyTool, PortScanTool

DnsLookupTool().execute(domain="example.com")
# {'success': True, 'domain': 'example.com', 'A': ['93.184.216.34'],
#  'MX': [{'preference': 10, 'exchange': 'mail.example.com'}], 'NS': ['a.iana-servers.net'], ...}

HashIdentifyTool().execute(hash_value="5f4dcc3b5aa765d61d8327deb882cf99")
# {'length': 32, 'hex': True,
#  'possible_types': [{'name': 'MD5 (hashcat -m 0)', 'confidence': 0.95}, ...]}

PortScanTool().execute(target="127.0.0.1", ports=[22, 80, 443])
# {'target': '127.0.0.1', 'open_ports': [{'port': 22, 'service': 'ssh'}, ...],
#  'open_count': 2, 'scanned': 3, 'scan_time': 0.2}
```

Preguntas de ejemplo para el chat de Nex:

- *"Enumera subdominios de example.com"* → `subdomain_enum`
- *"¿Qué tipo de hash es `e10adc3949ba59abbe56e057f20f883e`?"* → `hash_identify`
- *"Analiza el archivo ./pruebas/ejemplo.bin"* → `file_metadata`
- *"¿Qué servidor usa github.com y cuándo expira su certificado?"* → `http_fingerprint` + `tls_probe`

## Scope de escaneo (ética y legalidad)

`port_scan` **solo** acepta:

1. Direcciones loopback (`127.0.0.1`, `localhost`, `::1`)
2. Hosts dentro del ajuste `scan_allowlist` (⚙️ → Security) o la variable
   `NEX_SCAN_ALLOWLIST` (IPs o CIDRs separados por coma)

```bash
export NEX_SCAN_ALLOWLIST="192.168.1.0/24,10.0.0.5"
```

Cualquier otro objetivo es rechazado con un error explicativo. Escanea únicamente
sistemas propios o con autorización explícita.

## Conceptos que se aprenden aquí

- **DNS**: registros A/AAAA (direcciones), MX (correo), NS (autoridad), TXT (SPF/DKIM), CNAME (alias). Se resuelve con `socket.getaddrinfo` + `dig`.
- **RDAP**: el sucesor moderno y JSON de WHOIS (`rdap.org`), sin depender del comando `whois`.
- **Certificate Transparency**: cada certificado público se registra en logs; crt.sh permite buscar por dominio → subdominios que jamás se anunciaron.
- **Banner grabbing**: los headers HTTP (`Server`, `X-Powered-By`) delatan la pila tecnológica.
- **Magic bytes**: las primeras bytes de un archivo identifican su tipo real (`\x7fELF` = ejecutable, `\x89PNG` = imagen), sin importar la extensión.
- **Hashes**: MD5/SHA-1/SHA-256 se distinguen por longitud (32/40/64 hex); bcrypt lleva prefijo `$2`. `hashcat -m <modo>` se indica en cada candidato.
- **TCP connect scan**: abrir un socket TCP y ver si el handshake completa (`connect_ex() == 0`) revela puertos abiertos, sin nmap.

## Tests

```bash
cd backend
../.venv/bin/python -m pytest tests/test_recon.py -v
```
