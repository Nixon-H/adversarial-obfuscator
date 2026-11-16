"""
Shared algorithm templates for honey-functions and decoy APIs.
Extracted from obfuscator/llm_resilient.py's _REAL_ALGO_SOURCES.
"""

_REAL_ALGO_SOURCES = {
    "base64_decode": """def {name}(data):
    b = []
    table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    pad = 0
    for ch in data:
        if ch == '=':
            pad += 1
    buffer = 0
    bits = 0
    for ch in data:
        if ch == '=':
            break
        idx = table.find(ch)
        if idx < 0:
            continue
        buffer = (buffer << 6) | idx
        bits += 6
        if bits >= 8:
            bits -= 8
            b.append((buffer >> bits) & 0xFF)
    return bytes(b)
""",
    "crc32": """def {name}(data, poly=0xEDB88320):
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
        table.append(crc)
    crc = 0xFFFFFFFF
    for byte in data:
        crc = table[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF
""",
    "aes_key_schedule": """def {name}(key):
    # The AES S-box is inlined here on purpose.  This template used to call
    # a bare `sbox(...)` that nothing defined: Python only resolved it when
    # the branch executed (never, at import), so the bug stayed invisible --
    # but Cython resolves names at COMPILE time and refused the whole file
    # with "undeclared name not builtin: sbox", which killed every native
    # build.  Keeping the table local makes the template self-contained.
    _SBOX = (
        0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b,
        0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0,
        0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7, 0xfd, 0x93, 0x26,
        0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
        0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2,
        0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0,
        0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed,
        0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
        0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f,
        0x50, 0x3c, 0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5,
        0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec,
        0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
        0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14,
        0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c,
        0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79, 0xe7, 0xc8, 0x37, 0x6d,
        0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
        0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f,
        0x4b, 0xbd, 0x8b, 0x8a, 0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e,
        0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11,
        0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
        0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f,
        0xb0, 0x54, 0xbb, 0x16,
    )
    rcon = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]
    w = []
    for i in range(4):
        w.append([key[4*i], key[4*i+1], key[4*i+2], key[4*i+3]])
    for i in range(4, 44):
        temp = list(w[i-1])
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            for j in range(4):
                temp[j] = _SBOX[temp[j] & 0xFF]
            temp[0] ^= rcon[i//4 - 1]
        w.append([w[i-4][j] ^ temp[j] for j in range(4)])
    return w
""",
    "hex_decode": """def {name}(hex_str):
    result = []
    hex_str = hex_str.strip()
    for i in range(0, len(hex_str), 2):
        hi = ord(hex_str[i])
        lo = ord(hex_str[i+1])
        hi_val = hi - 48 if hi >= 48 and hi <= 57 else hi - 87
        lo_val = lo - 48 if lo >= 48 and lo <= 57 else lo - 87
        result.append((hi_val << 4) | lo_val)
    return bytes(result)
""",
    "xor_block": """def {name}(data, key):
    result = bytearray(len(data))
    key_len = len(key)
    for i in range(len(data)):
        result[i] = data[i] ^ key[i % key_len]
    return bytes(result)
""",
    "json_parse": """def {name}(text):
    stack = []
    current = None
    key = None
    i = 0
    while i < len(text):
        c = text[i]
        if c in ' \\t\\n\\r':
            i += 1
            continue
        if c == '{':
            obj = {}
            if isinstance(current, list):
                current.append(obj)
            elif isinstance(current, dict) and key is not None:
                current[key] = obj
            stack.append(current)
            current = obj
            key = None
        elif c == '}':
            current = stack.pop()
        elif c == '[':
            arr = []
            if isinstance(current, list):
                current.append(arr)
            elif isinstance(current, dict) and key is not None:
                current[key] = arr
            stack.append(current)
            current = arr
        elif c == ']':
            current = stack.pop()
        elif c == '"':
            j = i + 1
            while j < len(text):
                if text[j] == '"' and text[j-1] != '\\\\':
                    break
                j += 1
            val = text[i+1:j]
            if isinstance(current, dict):
                if key is None:
                    key = val
                else:
                    current[key] = val
                    key = None
            elif isinstance(current, list):
                current.append(val)
            i = j
        elif c == ':':
            pass
        elif c == ',':
            pass
        i += 1
    return current
""",
}
