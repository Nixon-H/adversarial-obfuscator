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
    rcon = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]
    w = []
    for i in range(4):
        w.append([key[4*i], key[4*i+1], key[4*i+2], key[4*i+3]])
    for i in range(4, 44):
        temp = list(w[i-1])
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            for j in range(4):
                temp[j] = sbox(temp[j])
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
