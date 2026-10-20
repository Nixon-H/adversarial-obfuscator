import hashlib
import math
import os

def greet(name):
    return f'Hello, {name}!'

def aes_encrypt(data, key):
    _nx_opaque = 53410 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 65
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c0_0 = 1
        _nx_d0_1 = 163
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c0_1 = 1
        _nx_d0_2 = 16
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c0_2 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 205
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c1_0 = 1
        _nx_d1_1 = 217
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c1_1 = 1
        _nx_d1_2 = 141
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c1_2 = 1
    if _nx_opaque == False:
        _nx_d2_0 = 162
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c2_0 = 1
        _nx_d2_1 = 127
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c2_1 = 1
        _nx_d2_2 = 253
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c2_2 = 1
    if _nx_opaque == False:
        _nx_d3_0 = 181
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c3_0 = 1
        _nx_d3_1 = 213
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c3_1 = 1
        _nx_d3_2 = 84
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c3_2 = 1
    if _nx_opaque == False:
        _nx_d4_0 = 161
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c4_0 = 1
        _nx_d4_1 = 25
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c4_1 = 1
        _nx_d4_2 = 252
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c4_2 = 1
    if _nx_opaque == False:
        _nx_d5_0 = 19
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c5_0 = 1
        _nx_d5_1 = 250
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c5_1 = 1
        _nx_d5_2 = 35
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c5_2 = 1
    if _nx_opaque == False:
        _nx_d6_0 = 203
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c6_0 = 1
        _nx_d6_1 = 218
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c6_1 = 1
        _nx_d6_2 = 23
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c6_2 = 1
    if _nx_opaque == False:
        _nx_d7_0 = 235
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c7_0 = 1
        _nx_d7_1 = 34
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c7_1 = 1
        _nx_d7_2 = 148
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c7_2 = 1
    if _nx_opaque == False:
        _nx_d8_0 = 155
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c8_0 = 1
        _nx_d8_1 = 146
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c8_1 = 1
        _nx_d8_2 = 213
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c8_2 = 1
    if _nx_opaque == False:
        _nx_d9_0 = 211
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c9_0 = 1
        _nx_d9_1 = 3
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c9_1 = 1
        _nx_d9_2 = 205
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c9_2 = 1
    if _nx_opaque == False:
        _nx_d10_0 = 139
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c10_0 = 1
        _nx_d10_1 = 22
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c10_1 = 1
        _nx_d10_2 = 220
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c10_2 = 1
    if _nx_opaque == False:
        _nx_d11_0 = 153
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c11_0 = 1
        _nx_d11_1 = 229
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c11_1 = 1
        _nx_d11_2 = 120
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c11_2 = 1
    if _nx_opaque == False:
        _nx_d12_0 = 96
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c12_0 = 1
        _nx_d12_1 = 181
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c12_1 = 1
        _nx_d12_2 = 64
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c12_2 = 1
    if _nx_opaque == False:
        _nx_d13_0 = 227
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c13_0 = 1
        _nx_d13_1 = 58
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c13_1 = 1
        _nx_d13_2 = 207
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c13_2 = 1
    if _nx_opaque == False:
        _nx_d14_0 = 174
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c14_0 = 1
        _nx_d14_1 = 92
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c14_1 = 1
        _nx_d14_2 = 140
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c14_2 = 1
    if _nx_opaque == False:
        _nx_d15_0 = 119
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c15_0 = 1
        _nx_d15_1 = 250
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c15_1 = 1
        _nx_d15_2 = 25
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c15_2 = 1
    if _nx_opaque == False:
        _nx_d16_0 = 193
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c16_0 = 1
        _nx_d16_1 = 141
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c16_1 = 1
        _nx_d16_2 = 45
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c16_2 = 1
    if _nx_opaque == False:
        _nx_d17_0 = 216
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c17_0 = 1
        _nx_d17_1 = 178
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c17_1 = 1
        _nx_d17_2 = 198
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c17_2 = 1
    if _nx_opaque == False:
        _nx_d18_0 = 229
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c18_0 = 1
        _nx_d18_1 = 134
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c18_1 = 1
        _nx_d18_2 = 215
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c18_2 = 1
    if _nx_opaque == False:
        _nx_d19_0 = 21
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        _nx_c19_0 = 1
        _nx_d19_1 = 88
        state = [b ^ k for b, k in zip(data, key)]
        _nx_c19_1 = 1
        _nx_d19_2 = 10
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        _nx_c19_2 = 1
    if not _nx_opaque:
        pass
    else:
        sbox = [99, 124, 119, 123, 242, 107, 111, 197]
        state = [b ^ k for b, k in zip(data, key)]
        for _ in range(10):
            for i in range(16):
                state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 15)]
            for i in range(4):
                a = state[4 * i:4 * (i + 1)]
                state[4 * i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        return bytes(state)

def gmul(a, b):
    _nx_opaque = 10508 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 156
        p = 0
        _nx_c0_0 = 1
        _nx_d0_1 = 14
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c0_1 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 104
        p = 0
        _nx_c1_0 = 1
        _nx_d1_1 = 112
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c1_1 = 1
    if _nx_opaque == False:
        _nx_d2_0 = 196
        p = 0
        _nx_c2_0 = 1
        _nx_d2_1 = 233
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c2_1 = 1
    if _nx_opaque == False:
        _nx_d3_0 = 38
        p = 0
        _nx_c3_0 = 1
        _nx_d3_1 = 102
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c3_1 = 1
    if _nx_opaque == False:
        _nx_d4_0 = 8
        p = 0
        _nx_c4_0 = 1
        _nx_d4_1 = 186
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c4_1 = 1
    if _nx_opaque == False:
        _nx_d5_0 = 69
        p = 0
        _nx_c5_0 = 1
        _nx_d5_1 = 148
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c5_1 = 1
    if _nx_opaque == False:
        _nx_d6_0 = 60
        p = 0
        _nx_c6_0 = 1
        _nx_d6_1 = 103
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c6_1 = 1
    if _nx_opaque == False:
        _nx_d7_0 = 211
        p = 0
        _nx_c7_0 = 1
        _nx_d7_1 = 232
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c7_1 = 1
    if _nx_opaque == False:
        _nx_d8_0 = 178
        p = 0
        _nx_c8_0 = 1
        _nx_d8_1 = 173
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c8_1 = 1
    if _nx_opaque == False:
        _nx_d9_0 = 196
        p = 0
        _nx_c9_0 = 1
        _nx_d9_1 = 224
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c9_1 = 1
    if _nx_opaque == False:
        _nx_d10_0 = 114
        p = 0
        _nx_c10_0 = 1
        _nx_d10_1 = 99
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c10_1 = 1
    if _nx_opaque == False:
        _nx_d11_0 = 198
        p = 0
        _nx_c11_0 = 1
        _nx_d11_1 = 28
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c11_1 = 1
    if _nx_opaque == False:
        _nx_d12_0 = 111
        p = 0
        _nx_c12_0 = 1
        _nx_d12_1 = 247
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c12_1 = 1
    if _nx_opaque == False:
        _nx_d13_0 = 204
        p = 0
        _nx_c13_0 = 1
        _nx_d13_1 = 49
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c13_1 = 1
    if _nx_opaque == False:
        _nx_d14_0 = 183
        p = 0
        _nx_c14_0 = 1
        _nx_d14_1 = 14
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c14_1 = 1
    if _nx_opaque == False:
        _nx_d15_0 = 151
        p = 0
        _nx_c15_0 = 1
        _nx_d15_1 = 247
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c15_1 = 1
    if _nx_opaque == False:
        _nx_d16_0 = 179
        p = 0
        _nx_c16_0 = 1
        _nx_d16_1 = 117
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c16_1 = 1
    if _nx_opaque == False:
        _nx_d17_0 = 214
        p = 0
        _nx_c17_0 = 1
        _nx_d17_1 = 208
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c17_1 = 1
    if _nx_opaque == False:
        _nx_d18_0 = 133
        p = 0
        _nx_c18_0 = 1
        _nx_d18_1 = 76
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c18_1 = 1
    if _nx_opaque == False:
        _nx_d19_0 = 133
        p = 0
        _nx_c19_0 = 1
        _nx_d19_1 = 176
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        _nx_c19_1 = 1
    if not _nx_opaque:
        pass
    else:
        p = 0
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 128
            a = a << 1 & 255
            if hi:
                a ^= 27
            b >>= 1
        return p

def verify_license(key):
    _nx_opaque = 5904 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 234
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c0_0 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 108
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c1_0 = 1
    if _nx_opaque == False:
        _nx_d2_0 = 239
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c2_0 = 1
    if _nx_opaque == False:
        _nx_d3_0 = 27
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c3_0 = 1
    if _nx_opaque == False:
        _nx_d4_0 = 10
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c4_0 = 1
    if _nx_opaque == False:
        _nx_d5_0 = 93
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c5_0 = 1
    if _nx_opaque == False:
        _nx_d6_0 = 13
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c6_0 = 1
    if _nx_opaque == False:
        _nx_d7_0 = 186
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c7_0 = 1
    if _nx_opaque == False:
        _nx_d8_0 = 216
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c8_0 = 1
    if _nx_opaque == False:
        _nx_d9_0 = 107
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c9_0 = 1
    if _nx_opaque == False:
        _nx_d10_0 = 170
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c10_0 = 1
    if _nx_opaque == False:
        _nx_d11_0 = 55
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c11_0 = 1
    if _nx_opaque == False:
        _nx_d12_0 = 250
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c12_0 = 1
    if _nx_opaque == False:
        _nx_d13_0 = 54
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c13_0 = 1
    if _nx_opaque == False:
        _nx_d14_0 = 254
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c14_0 = 1
    if _nx_opaque == False:
        _nx_d15_0 = 204
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c15_0 = 1
    if _nx_opaque == False:
        _nx_d16_0 = 97
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c16_0 = 1
    if _nx_opaque == False:
        _nx_d17_0 = 214
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c17_0 = 1
    if _nx_opaque == False:
        _nx_d18_0 = 177
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c18_0 = 1
    if _nx_opaque == False:
        _nx_d19_0 = 221
        valid = ['ABCD-1234', 'WXYZ-5678']
        _nx_c19_0 = 1
    if not _nx_opaque:
        pass
    else:
        valid = ['ABCD-1234', 'WXYZ-5678']
        return _affine_enc.decode(key_enc, 12532789731825362141, 5268135796077200060) in valid

def derive_key(password, salt):
    _nx_opaque = 4212 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 122
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c0_0 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 135
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c1_0 = 1
    if _nx_opaque == False:
        _nx_d2_0 = 159
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c2_0 = 1
    if _nx_opaque == False:
        _nx_d3_0 = 148
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c3_0 = 1
    if _nx_opaque == False:
        _nx_d4_0 = 200
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c4_0 = 1
    if _nx_opaque == False:
        _nx_d5_0 = 208
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c5_0 = 1
    if _nx_opaque == False:
        _nx_d6_0 = 107
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c6_0 = 1
    if _nx_opaque == False:
        _nx_d7_0 = 193
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c7_0 = 1
    if _nx_opaque == False:
        _nx_d8_0 = 214
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c8_0 = 1
    if _nx_opaque == False:
        _nx_d9_0 = 113
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c9_0 = 1
    if _nx_opaque == False:
        _nx_d10_0 = 224
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c10_0 = 1
    if _nx_opaque == False:
        _nx_d11_0 = 126
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c11_0 = 1
    if _nx_opaque == False:
        _nx_d12_0 = 4
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c12_0 = 1
    if _nx_opaque == False:
        _nx_d13_0 = 87
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c13_0 = 1
    if _nx_opaque == False:
        _nx_d14_0 = 144
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c14_0 = 1
    if _nx_opaque == False:
        _nx_d15_0 = 78
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c15_0 = 1
    if _nx_opaque == False:
        _nx_d16_0 = 120
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c16_0 = 1
    if _nx_opaque == False:
        _nx_d17_0 = 29
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c17_0 = 1
    if _nx_opaque == False:
        _nx_d18_0 = 37
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c18_0 = 1
    if _nx_opaque == False:
        _nx_d19_0 = 241
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        _nx_c19_0 = 1
    if not _nx_opaque:
        pass
    else:
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return dk + os.urandom(16)

def compute_hash(data):
    return hashlib.sha256(_affine_enc.decode(data_enc, 9542852174600270569, 13785204644127800875).encode()).hexdigest()

def analyze_data(values):
    _nx_opaque = 26334 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 103
        n = len(values)
        _nx_c0_0 = 1
        _nx_d0_1 = 135
        mean = sum(values) / n
        _nx_c0_1 = 1
        _nx_d0_2 = 200
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c0_2 = 1
        _nx_d0_3 = 197
        std = math.sqrt(variance)
        _nx_c0_3 = 1
        _nx_d0_4 = 61
        median = sorted(values)[n // 2]
        _nx_c0_4 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 255
        n = len(values)
        _nx_c1_0 = 1
        _nx_d1_1 = 251
        mean = sum(values) / n
        _nx_c1_1 = 1
        _nx_d1_2 = 201
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c1_2 = 1
        _nx_d1_3 = 15
        std = math.sqrt(variance)
        _nx_c1_3 = 1
        _nx_d1_4 = 40
        median = sorted(values)[n // 2]
        _nx_c1_4 = 1
    if _nx_opaque == False:
        _nx_d2_0 = 76
        n = len(values)
        _nx_c2_0 = 1
        _nx_d2_1 = 250
        mean = sum(values) / n
        _nx_c2_1 = 1
        _nx_d2_2 = 108
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c2_2 = 1
        _nx_d2_3 = 207
        std = math.sqrt(variance)
        _nx_c2_3 = 1
        _nx_d2_4 = 219
        median = sorted(values)[n // 2]
        _nx_c2_4 = 1
    if _nx_opaque == False:
        _nx_d3_0 = 58
        n = len(values)
        _nx_c3_0 = 1
        _nx_d3_1 = 159
        mean = sum(values) / n
        _nx_c3_1 = 1
        _nx_d3_2 = 212
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c3_2 = 1
        _nx_d3_3 = 203
        std = math.sqrt(variance)
        _nx_c3_3 = 1
        _nx_d3_4 = 61
        median = sorted(values)[n // 2]
        _nx_c3_4 = 1
    if _nx_opaque == False:
        _nx_d4_0 = 204
        n = len(values)
        _nx_c4_0 = 1
        _nx_d4_1 = 246
        mean = sum(values) / n
        _nx_c4_1 = 1
        _nx_d4_2 = 123
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c4_2 = 1
        _nx_d4_3 = 123
        std = math.sqrt(variance)
        _nx_c4_3 = 1
        _nx_d4_4 = 242
        median = sorted(values)[n // 2]
        _nx_c4_4 = 1
    if _nx_opaque == False:
        _nx_d5_0 = 44
        n = len(values)
        _nx_c5_0 = 1
        _nx_d5_1 = 173
        mean = sum(values) / n
        _nx_c5_1 = 1
        _nx_d5_2 = 216
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c5_2 = 1
        _nx_d5_3 = 205
        std = math.sqrt(variance)
        _nx_c5_3 = 1
        _nx_d5_4 = 202
        median = sorted(values)[n // 2]
        _nx_c5_4 = 1
    if _nx_opaque == False:
        _nx_d6_0 = 240
        n = len(values)
        _nx_c6_0 = 1
        _nx_d6_1 = 114
        mean = sum(values) / n
        _nx_c6_1 = 1
        _nx_d6_2 = 172
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c6_2 = 1
        _nx_d6_3 = 17
        std = math.sqrt(variance)
        _nx_c6_3 = 1
        _nx_d6_4 = 16
        median = sorted(values)[n // 2]
        _nx_c6_4 = 1
    if _nx_opaque == False:
        _nx_d7_0 = 177
        n = len(values)
        _nx_c7_0 = 1
        _nx_d7_1 = 147
        mean = sum(values) / n
        _nx_c7_1 = 1
        _nx_d7_2 = 90
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c7_2 = 1
        _nx_d7_3 = 203
        std = math.sqrt(variance)
        _nx_c7_3 = 1
        _nx_d7_4 = 35
        median = sorted(values)[n // 2]
        _nx_c7_4 = 1
    if _nx_opaque == False:
        _nx_d8_0 = 150
        n = len(values)
        _nx_c8_0 = 1
        _nx_d8_1 = 75
        mean = sum(values) / n
        _nx_c8_1 = 1
        _nx_d8_2 = 111
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c8_2 = 1
        _nx_d8_3 = 57
        std = math.sqrt(variance)
        _nx_c8_3 = 1
        _nx_d8_4 = 50
        median = sorted(values)[n // 2]
        _nx_c8_4 = 1
    if _nx_opaque == False:
        _nx_d9_0 = 117
        n = len(values)
        _nx_c9_0 = 1
        _nx_d9_1 = 30
        mean = sum(values) / n
        _nx_c9_1 = 1
        _nx_d9_2 = 149
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c9_2 = 1
        _nx_d9_3 = 243
        std = math.sqrt(variance)
        _nx_c9_3 = 1
        _nx_d9_4 = 1
        median = sorted(values)[n // 2]
        _nx_c9_4 = 1
    if _nx_opaque == False:
        _nx_d10_0 = 59
        n = len(values)
        _nx_c10_0 = 1
        _nx_d10_1 = 155
        mean = sum(values) / n
        _nx_c10_1 = 1
        _nx_d10_2 = 170
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c10_2 = 1
        _nx_d10_3 = 100
        std = math.sqrt(variance)
        _nx_c10_3 = 1
        _nx_d10_4 = 177
        median = sorted(values)[n // 2]
        _nx_c10_4 = 1
    if _nx_opaque == False:
        _nx_d11_0 = 72
        n = len(values)
        _nx_c11_0 = 1
        _nx_d11_1 = 16
        mean = sum(values) / n
        _nx_c11_1 = 1
        _nx_d11_2 = 56
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c11_2 = 1
        _nx_d11_3 = 185
        std = math.sqrt(variance)
        _nx_c11_3 = 1
        _nx_d11_4 = 93
        median = sorted(values)[n // 2]
        _nx_c11_4 = 1
    if _nx_opaque == False:
        _nx_d12_0 = 58
        n = len(values)
        _nx_c12_0 = 1
        _nx_d12_1 = 27
        mean = sum(values) / n
        _nx_c12_1 = 1
        _nx_d12_2 = 228
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c12_2 = 1
        _nx_d12_3 = 75
        std = math.sqrt(variance)
        _nx_c12_3 = 1
        _nx_d12_4 = 63
        median = sorted(values)[n // 2]
        _nx_c12_4 = 1
    if _nx_opaque == False:
        _nx_d13_0 = 196
        n = len(values)
        _nx_c13_0 = 1
        _nx_d13_1 = 208
        mean = sum(values) / n
        _nx_c13_1 = 1
        _nx_d13_2 = 240
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c13_2 = 1
        _nx_d13_3 = 139
        std = math.sqrt(variance)
        _nx_c13_3 = 1
        _nx_d13_4 = 255
        median = sorted(values)[n // 2]
        _nx_c13_4 = 1
    if _nx_opaque == False:
        _nx_d14_0 = 179
        n = len(values)
        _nx_c14_0 = 1
        _nx_d14_1 = 52
        mean = sum(values) / n
        _nx_c14_1 = 1
        _nx_d14_2 = 73
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c14_2 = 1
        _nx_d14_3 = 11
        std = math.sqrt(variance)
        _nx_c14_3 = 1
        _nx_d14_4 = 14
        median = sorted(values)[n // 2]
        _nx_c14_4 = 1
    if _nx_opaque == False:
        _nx_d15_0 = 218
        n = len(values)
        _nx_c15_0 = 1
        _nx_d15_1 = 3
        mean = sum(values) / n
        _nx_c15_1 = 1
        _nx_d15_2 = 179
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c15_2 = 1
        _nx_d15_3 = 69
        std = math.sqrt(variance)
        _nx_c15_3 = 1
        _nx_d15_4 = 107
        median = sorted(values)[n // 2]
        _nx_c15_4 = 1
    if _nx_opaque == False:
        _nx_d16_0 = 98
        n = len(values)
        _nx_c16_0 = 1
        _nx_d16_1 = 248
        mean = sum(values) / n
        _nx_c16_1 = 1
        _nx_d16_2 = 60
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c16_2 = 1
        _nx_d16_3 = 54
        std = math.sqrt(variance)
        _nx_c16_3 = 1
        _nx_d16_4 = 158
        median = sorted(values)[n // 2]
        _nx_c16_4 = 1
    if _nx_opaque == False:
        _nx_d17_0 = 190
        n = len(values)
        _nx_c17_0 = 1
        _nx_d17_1 = 27
        mean = sum(values) / n
        _nx_c17_1 = 1
        _nx_d17_2 = 97
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c17_2 = 1
        _nx_d17_3 = 205
        std = math.sqrt(variance)
        _nx_c17_3 = 1
        _nx_d17_4 = 106
        median = sorted(values)[n // 2]
        _nx_c17_4 = 1
    if _nx_opaque == False:
        _nx_d18_0 = 84
        n = len(values)
        _nx_c18_0 = 1
        _nx_d18_1 = 244
        mean = sum(values) / n
        _nx_c18_1 = 1
        _nx_d18_2 = 150
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c18_2 = 1
        _nx_d18_3 = 246
        std = math.sqrt(variance)
        _nx_c18_3 = 1
        _nx_d18_4 = 243
        median = sorted(values)[n // 2]
        _nx_c18_4 = 1
    if _nx_opaque == False:
        _nx_d19_0 = 89
        n = len(values)
        _nx_c19_0 = 1
        _nx_d19_1 = 134
        mean = sum(values) / n
        _nx_c19_1 = 1
        _nx_d19_2 = 141
        variance = sum(((x - mean) ** 2 for x in values)) / n
        _nx_c19_2 = 1
        _nx_d19_3 = 154
        std = math.sqrt(variance)
        _nx_c19_3 = 1
        _nx_d19_4 = 43
        median = sorted(values)[n // 2]
        _nx_c19_4 = 1
    if not _nx_opaque:
        pass
    else:
        n = len(values)
        mean = sum(values) / n
        variance = sum(((x - mean) ** 2 for x in values)) / n
        std = math.sqrt(variance)
        median = sorted(values)[n // 2]
        return {'mean': mean, 'median': median, 'std': std, 'variance': variance}

def add(a, b):
    return a + b

def do_nothing():
    pass
if __name__ == '__main__':
    print('All functions loaded.')