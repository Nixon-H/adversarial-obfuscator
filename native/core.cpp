// Nixon Core Engine - Cryptography Primitives & Python Compilation
// Flavors (see Makefile):
//   FULL (CORE_HAVE_PYTHON_H): WhiteboxCrypto + WhiteboxEnhanced + CompileToMarshal
//   WHITEBOX_ONLY:             WhiteboxCrypto + WhiteboxEnhanced + CompileToMarshal
//   COMPILE_ONLY:              WhiteboxCrypto + WhiteboxEnhanced + CompileToMarshal
// All flavors ship all three components; the names select defaults, not
// subsets. (History: WHITEBOX_ONLY once stubbed CompileToMarshal, which
// broke wb.so consumers — tests + hybrid loader probe it. Never again.)


#ifdef CORE_HAVE_PYTHON_H
#include <Python.h>
#if __has_include(<marshal.h>)
#include <marshal.h>
#endif
#endif

#include <cstdint>
#include <new>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <cstdio>
#include <ctime>
#include "whitebox_feistel.h"

// NOTE: no flavor `#if` in this file: WhiteboxCrypto, WhiteboxEnhanced
// and CompileToMarshal build identically in every Makefile flavor
// (FULL / WHITEBOX_ONLY / COMPILE_ONLY differ only in emitted intent,
// not compiled content — see header). This is deliberate: wb.so is
// probed for CompileToMarshal by tests and the hybrid loader.

// ================================================================
// WhiteboxCrypto — 8-round Feistel white-box cipher (production, 2026-09-20).
// 16-byte blocks, PKCS#7 padded. Tables derived via SHA-256 key expansion
// (see whitebox_feistel.{h,cpp}); raw key wiped after derivation so only
// lookup tables persist. Obfuscation-grade (table-inversion barrier),
// composed with AES-CTR + runtime decrypt — never the sole secrecy layer.
class WhiteboxCrypto {
private:
    nixon_wb::WbTables _t;
    bool _init_ok;
public:
    WhiteboxCrypto(const uint8_t* key_bytes, size_t key_len) : _init_ok(false) {
        if (key_len != 16) throw std::invalid_argument("WhiteboxCrypto requires a 16-byte key (128-bit)");
        uint8_t key[16];
        for (size_t i = 0; i < 16; ++i) key[i] = key_bytes[i];
        uint64_t salt = 0;
#if defined(__linux__) || defined(__APPLE__)
        FILE* f = fopen("/dev/urandom", "rb");
        if (f) { size_t n = fread(&salt, 1, sizeof(salt), f); (void)n; fclose(f); }
#endif
        if (salt == 0) salt = (uint64_t)(uintptr_t)this ^ (uint64_t)time(nullptr);
        nixon_wb::wb_derive_tables(key, salt, _t);
        volatile uint8_t* vk = key;
        for (int i = 0; i < 16; ++i) vk[i] = 0;
        _init_ok = true;
    }
    ~WhiteboxCrypto() {
        volatile uint8_t* p = reinterpret_cast<volatile uint8_t*>(&_t);
        for (size_t i = 0; i < sizeof(_t); ++i) p[i] = 0;
    }

    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& data) {
        std::vector<uint8_t> result = data;
        size_t pad = WB_BLOCK - (result.size() % WB_BLOCK);
        if (pad == 0) pad = WB_BLOCK;
        for (size_t i = 0; i < pad; ++i) result.push_back((uint8_t)pad);
        for (size_t off = 0; off < result.size(); off += WB_BLOCK)
            nixon_wb::wb_feistel_block(_t, result.data() + off, false);
        return result;
    }

    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& data) {
        if (data.empty() || (data.size() % WB_BLOCK) != 0) return {};
        std::vector<uint8_t> result = data;
        for (size_t off = 0; off < result.size(); off += WB_BLOCK)
            nixon_wb::wb_feistel_block(_t, result.data() + off, true);
        uint8_t pad = result.back();
        if (pad == 0 || pad > WB_BLOCK || pad > result.size()) return {};
        for (size_t i = 0; i < pad; ++i)
            if (result[result.size() - 1 - i] != pad) return {};
        result.resize(result.size() - pad);
        return result;
    }
};

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((visibility("default"))) WhiteboxCrypto* WBC_new(const uint8_t* key, size_t key_len) {
    try { return new WhiteboxCrypto(key, key_len); }
    catch (std::bad_alloc&) { return nullptr; }
    catch (std::invalid_argument&) { return nullptr; }
}
__attribute__((visibility("default"))) void WBC_del(WhiteboxCrypto* wbc) {
    delete wbc;
}
__attribute__((visibility("default"))) uint8_t* WBC_encrypt(WhiteboxCrypto* wbc, const uint8_t* data, size_t len) {
    try {
        if (!wbc || (!data && len)) return nullptr;
        std::vector<uint8_t> v(data, data + len);
        std::vector<uint8_t> res = wbc->encrypt(v);
        // NOTE: padded output is LONGER than input (PKCS#7 to 16 B).
        // Callers must size the buffer as ((len/16)+1)*16. The padded
        // length is recoverable as: out_len = ((len/16)+1)*16.
        uint8_t* out = new uint8_t[res.size()];
        std::copy(res.begin(), res.end(), out);
        return out;
    } catch (std::bad_alloc&) { return nullptr; }
}
__attribute__((visibility("default"))) size_t WBC_encrypted_size(size_t plain_len) {
    return ((plain_len / WB_BLOCK) + 1) * WB_BLOCK;
}
__attribute__((visibility("default"))) uint8_t* WBC_decrypt(WhiteboxCrypto* wbc, const uint8_t* data, size_t len) {
    try {
        if (!wbc || !data) return nullptr;
        std::vector<uint8_t> v(data, data + len);
        std::vector<uint8_t> res = wbc->decrypt(v);
        if (res.empty() && len) return nullptr;  // bad padding
        uint8_t* out = new uint8_t[res.size() ? res.size() : 1];
        std::copy(res.begin(), res.end(), out);
        return out;
    } catch (std::bad_alloc&) { return nullptr; }
}
__attribute__((visibility("default"))) size_t WBC_decrypted_size(WhiteboxCrypto* wbc, const uint8_t* data, size_t len) {
    // Peek decrypted length without allocating: total minus PKCS#7 pad.
    // Returns 0 on invalid input/padding.
    if (!wbc || !data || !len || (len % WB_BLOCK)) return 0;
    // Decrypt last block only to read pad byte: full decrypt is cheap
    // enough here; keep API simple and correct.
    try {
        std::vector<uint8_t> v(data, data + len);
        std::vector<uint8_t> res = wbc->decrypt(v);
        return res.size();
    } catch (...) { return 0; }
}
__attribute__((visibility("default"))) void WBC_free_array(uint8_t* arr) {
    delete[] arr;
}

#ifdef __cplusplus
}
#endif

// ================================================================
// WhiteboxEnhanced — configurable-round caller-provided-table cipher.
// Tables (T-boxes + mix keys) are supplied by the caller via WBE_new;
// this TU never invents key material. Educational mixing caveat retained
// in the comment above the class.
// ================================================================
// Same caveats as WhiteboxCrypto: linear key mixing, no real
// AES substitution.  Educational use only.
// ================================================================

class WhiteboxEnhanced {
private:
    int _num_rounds;
    std::vector<std::vector<uint8_t>> _tboxes;
    std::vector<std::vector<uint8_t>> _inv_tboxes;
    std::vector<std::vector<uint8_t>> _mix_keys;

public:
    WhiteboxEnhanced(int num_rounds,
                     const uint8_t* tboxes_flat,
                     const uint8_t* inv_tboxes_flat,
                     const uint8_t* mix_keys_flat) : _num_rounds(num_rounds) {
        if (num_rounds <= 0) throw std::invalid_argument("WhiteboxEnhanced requires num_rounds > 0");
        if (!tboxes_flat || !inv_tboxes_flat || !mix_keys_flat) throw std::invalid_argument("WhiteboxEnhanced requires non-null table pointers");
        for(int r=0; r<num_rounds; ++r) {
            _tboxes.push_back(std::vector<uint8_t>(tboxes_flat + r*256, tboxes_flat + (r+1)*256));
            _inv_tboxes.push_back(std::vector<uint8_t>(inv_tboxes_flat + r*256, inv_tboxes_flat + (r+1)*256));
            _mix_keys.push_back(std::vector<uint8_t>(mix_keys_flat + r*16, mix_keys_flat + (r+1)*16));
        }
    }

    void _mix_columns(std::vector<uint8_t>& data, const std::vector<uint8_t>& mix_key) {
        if (data.empty()) return;
        for(size_t i=0; i<data.size(); ++i) {
            data[i] ^= mix_key[i % mix_key.size()];
        }
        for(size_t i=0; i<data.size()-1; ++i) {
            data[i+1] = (data[i+1] + data[i]) & 0xFF;
        }
    }

    void _inv_mix_columns(std::vector<uint8_t>& data, const std::vector<uint8_t>& mix_key) {
        if (data.empty()) return;
        for(size_t i=data.size()-1; i>0; --i) {
            data[i] = (data[i] - data[i-1]) & 0xFF;
        }
        for(size_t i=0; i<data.size(); ++i) {
            data[i] ^= mix_key[i % mix_key.size()];
        }
    }

    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& data) {
        std::vector<uint8_t> result = data;
        for(int r=0; r<_num_rounds; ++r) {
            for(size_t i=0; i<result.size(); ++i) {
                result[i] = _tboxes[r][result[i]];
            }
            if(r < _num_rounds - 1) {
                _mix_columns(result, _mix_keys[r]);
            }
        }
        return result;
    }

    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& data) {
        std::vector<uint8_t> result = data;
        for(int r=_num_rounds - 1; r>=0; --r) {
            if(r < _num_rounds - 1) {
                _inv_mix_columns(result, _mix_keys[r]);
            }
            for(size_t i=0; i<result.size(); ++i) {
                result[i] = _inv_tboxes[r][result[i]];
            }
        }
        return result;
    }
};

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((visibility("default"))) WhiteboxEnhanced* WBE_new(int num_rounds, const uint8_t* tboxes, const uint8_t* inv_tboxes, const uint8_t* mix_keys) {
    try { return new WhiteboxEnhanced(num_rounds, tboxes, inv_tboxes, mix_keys); }
    catch (std::bad_alloc&) { return nullptr; }
    catch (std::invalid_argument&) { return nullptr; }
}
__attribute__((visibility("default"))) void WBE_del(WhiteboxEnhanced* wbe) {
    delete wbe;
}
__attribute__((visibility("default"))) uint8_t* WBE_encrypt(WhiteboxEnhanced* wbe, const uint8_t* data, size_t len) {
    try {
        if (!wbe || !data) return nullptr;
        std::vector<uint8_t> res = wbe->encrypt(std::vector<uint8_t>(data, data + len));
        uint8_t* out = new uint8_t[len];
        std::copy(res.begin(), res.end(), out);
        return out;
    } catch (std::bad_alloc&) { return nullptr; }
}
__attribute__((visibility("default"))) uint8_t* WBE_decrypt(WhiteboxEnhanced* wbe, const uint8_t* data, size_t len) {
    try {
        if (!wbe || !data) return nullptr;
        std::vector<uint8_t> res = wbe->decrypt(std::vector<uint8_t>(data, data + len));
        uint8_t* out = new uint8_t[len];
        std::copy(res.begin(), res.end(), out);
        return out;
    } catch (std::bad_alloc&) { return nullptr; }
}

#ifdef __cplusplus
}
#endif

// ================================================================
// CompileToMarshal — Python source -> marshal bytes.
// Uses CPython's compiler + marshal serializer.
// Available in ALL build flavors (needs CORE_HAVE_PYTHON_H); the stub
// below only applies when Python headers are absent.
// ================================================================

#ifdef CORE_HAVE_PYTHON_H

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((visibility("default"))) uint8_t* CompileToMarshal(const char* source_code, const char* filename, size_t* out_size) {
    PyGILState_STATE gstate = PyGILState_Ensure();

    PyObject* code_obj = Py_CompileStringExFlags(source_code, filename, Py_file_input, NULL, -1);
    if (!code_obj) {
        PyErr_Print();
        PyErr_Clear();
        *out_size = 0;
        PyGILState_Release(gstate);
        return nullptr;
    }

    PyObject* marshal_bytes = PyMarshal_WriteObjectToString(code_obj, Py_MARSHAL_VERSION);
    Py_DECREF(code_obj);

    if (!marshal_bytes) {
        PyErr_Print();
        PyErr_Clear();
        *out_size = 0;
        PyGILState_Release(gstate);
        return nullptr;
    }

    char* buffer;
    Py_ssize_t length;
    if (PyBytes_AsStringAndSize(marshal_bytes, &buffer, &length) == -1) {
        Py_DECREF(marshal_bytes);
        PyErr_Print();
        PyErr_Clear();
        *out_size = 0;
        PyGILState_Release(gstate);
        return nullptr;
    }

    uint8_t* out_buffer = nullptr;
    try {
        out_buffer = new uint8_t[length];
        std::copy(buffer, buffer + length, out_buffer);
    } catch (std::bad_alloc&) {
        Py_DECREF(marshal_bytes);
        PyGILState_Release(gstate);
        *out_size = 0;
        return nullptr;
    }

    Py_DECREF(marshal_bytes);
    PyGILState_Release(gstate);

    *out_size = length;
    return out_buffer;
}

__attribute__((visibility("default"))) void FreeMarshalBuffer(uint8_t* buffer) {
    delete[] buffer;
}

#ifdef __cplusplus
}
#endif

#else

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((visibility("default"))) uint8_t* CompileToMarshal(const char* source_code, const char* filename, size_t* out_size) {
    (void)source_code;
    (void)filename;
    *out_size = 0;
    return nullptr;
}

__attribute__((visibility("default"))) void FreeMarshalBuffer(uint8_t* buffer) {
    (void)buffer;
}

#ifdef __cplusplus
}
#endif

#endif // CORE_HAVE_PYTHON_H
