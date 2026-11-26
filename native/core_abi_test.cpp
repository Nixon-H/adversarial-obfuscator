// Native regression harness for the white-box C ABI.
// Build and run under ASan/UBSan with:
//   g++ -std=c++17 -O1 -g -Wall -Wextra -Werror
//       -fsanitize=address,undefined -fno-omit-frame-pointer
//       native/core_abi_test.cpp native/core.cpp native/whitebox_feistel.cpp
//       -o /tmp/opencode/core_abi_test
//   ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1
//       /tmp/opencode/core_abi_test

#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <vector>

struct WhiteboxCrypto;
struct WhiteboxEnhanced;

extern "C" {
WhiteboxCrypto* WBC_new(const uint8_t* key, size_t key_len);
void WBC_del(WhiteboxCrypto* wbc);
uint8_t* WBC_encrypt(WhiteboxCrypto* wbc, const uint8_t* data, size_t len);
int WBC_encrypt_ex(
    WhiteboxCrypto* wbc, const uint8_t* data, size_t len,
    uint8_t** out, size_t* out_len);
uint8_t* WBC_decrypt(WhiteboxCrypto* wbc, const uint8_t* data, size_t len);
int WBC_decrypt_ex(
    WhiteboxCrypto* wbc, const uint8_t* data, size_t len,
    uint8_t** out, size_t* out_len);
size_t WBC_encrypted_size(size_t plain_len);
size_t WBC_decrypted_size(WhiteboxCrypto* wbc, const uint8_t* data, size_t len);
void WBC_free_array(uint8_t* arr);

WhiteboxEnhanced* WBE_new(
    int num_rounds, const uint8_t* tboxes, const uint8_t* inv_tboxes,
    const uint8_t* mix_keys);
void WBE_del(WhiteboxEnhanced* wbe);
uint8_t* WBE_encrypt(WhiteboxEnhanced* wbe, const uint8_t* data, size_t len);
uint8_t* WBE_decrypt(WhiteboxEnhanced* wbe, const uint8_t* data, size_t len);
}

namespace {

constexpr int WBC_OK = 0;
constexpr int WBC_ERR_INVALID_ARGUMENT = -1;
constexpr int WBC_ERR_OVERFLOW = -2;

std::vector<uint8_t> encrypt(WhiteboxCrypto* wbc, const std::vector<uint8_t>& plain) {
    const size_t length = WBC_encrypted_size(plain.size());
    assert(length >= 16);
    uint8_t* raw = WBC_encrypt(wbc, plain.empty() ? nullptr : plain.data(), plain.size());
    assert(raw != nullptr);
    std::vector<uint8_t> result(raw, raw + length);
    WBC_free_array(raw);
    return result;
}

void test_size_arithmetic(WhiteboxCrypto* wbc) {
    const size_t max = std::numeric_limits<size_t>::max();
    assert(WBC_encrypted_size(0) == 16);
    assert(WBC_encrypted_size(15) == 16);
    assert(WBC_encrypted_size(16) == 32);
    assert(WBC_encrypted_size(max - 16) == max - 15);
    assert(WBC_encrypted_size(max - 15) == 0);
    assert(WBC_encrypted_size(max) == 0);

    uint8_t byte = 0x41;
    assert(WBC_encrypt(wbc, &byte, max) == nullptr);
    uint8_t* out = reinterpret_cast<uint8_t*>(1);
    size_t out_len = 123;
    assert(WBC_encrypt_ex(wbc, &byte, max, &out, &out_len) == WBC_ERR_OVERFLOW);
    assert(out == nullptr);
    assert(out_len == 0);
}

void test_empty_roundtrip(WhiteboxCrypto* wbc) {
    uint8_t* encrypted = WBC_encrypt(wbc, nullptr, 0);
    assert(encrypted != nullptr);
    const size_t encrypted_len = WBC_encrypted_size(0);
    assert(encrypted_len == 16);
    assert(WBC_decrypted_size(wbc, encrypted, encrypted_len) == 0);

    uint8_t* decrypted = WBC_decrypt(wbc, encrypted, encrypted_len);
    assert(decrypted != nullptr);
    WBC_free_array(decrypted);

    uint8_t* ex_encrypted = nullptr;
    size_t ex_encrypted_len = 0;
    assert(WBC_encrypt_ex(
               wbc, nullptr, 0, &ex_encrypted, &ex_encrypted_len) == WBC_OK);
    assert(ex_encrypted != nullptr);
    assert(ex_encrypted_len == 16);

    uint8_t* ex_decrypted = nullptr;
    size_t ex_decrypted_len = 123;
    assert(WBC_decrypt_ex(
               wbc, ex_encrypted, ex_encrypted_len,
               &ex_decrypted, &ex_decrypted_len) == WBC_OK);
    assert(ex_decrypted != nullptr);
    assert(ex_decrypted_len == 0);
    WBC_free_array(ex_decrypted);
    WBC_free_array(ex_encrypted);
    WBC_free_array(encrypted);
}

void assert_bad_padding(WhiteboxCrypto* wbc, const std::vector<uint8_t>& ciphertext) {
    assert(WBC_decrypt(wbc, ciphertext.data(), ciphertext.size()) == nullptr);
    assert(WBC_decrypted_size(wbc, ciphertext.data(), ciphertext.size()) == 0);
    uint8_t* out = reinterpret_cast<uint8_t*>(1);
    size_t out_len = 123;
    assert(WBC_decrypt_ex(
               wbc, ciphertext.data(), ciphertext.size(), &out, &out_len) ==
           WBC_ERR_INVALID_ARGUMENT);
    assert(out == nullptr);
    assert(out_len == 0);
}

void test_malformed_padding(WhiteboxCrypto* wbc) {
    const std::vector<uint8_t> zero(16, 0x00);
    const std::vector<uint8_t> high(16, 0x11);
    std::vector<uint8_t> inconsistent(16, 0x10);
    inconsistent.back() = 0x0f;

    const auto zero_ciphertext = encrypt(wbc, zero);
    const auto high_ciphertext = encrypt(wbc, high);
    const auto mixed_ciphertext = encrypt(wbc, inconsistent);

    auto malformed = zero_ciphertext;
    std::copy(zero_ciphertext.begin(), zero_ciphertext.begin() + 16,
              malformed.begin() + 16);
    assert_bad_padding(wbc, malformed);  // pad == 0

    malformed = high_ciphertext;
    std::copy(high_ciphertext.begin(), high_ciphertext.begin() + 16,
              malformed.begin() + 16);
    assert_bad_padding(wbc, malformed);  // pad == 17

    malformed = zero_ciphertext;
    std::copy(mixed_ciphertext.begin(), mixed_ciphertext.begin() + 16,
              malformed.begin() + 16);
    assert_bad_padding(wbc, malformed);  // inconsistent trailing bytes

    assert_bad_padding(wbc, std::vector<uint8_t>(zero_ciphertext.begin(),
                                                 zero_ciphertext.begin() + 15));
    malformed = zero_ciphertext;
    malformed.push_back(0);
    assert_bad_padding(wbc, malformed);
}

void test_wbe_size_max_is_contained() {
    std::vector<uint8_t> identity(256);
    for (size_t i = 0; i < identity.size(); ++i) identity[i] = static_cast<uint8_t>(i);
    const std::vector<uint8_t> mix_keys(16, 0);
    WhiteboxEnhanced* wbe = WBE_new(
        1, identity.data(), identity.data(), mix_keys.data());
    assert(wbe != nullptr);
    uint8_t byte = 0x41;
    assert(WBE_encrypt(wbe, &byte, std::numeric_limits<size_t>::max()) == nullptr);
    assert(WBE_decrypt(wbe, &byte, std::numeric_limits<size_t>::max()) == nullptr);
    WBE_del(wbe);
}

}  // namespace

int main() {
    const uint8_t key[16] = {0, 1, 2, 3, 4, 5, 6, 7,
                             8, 9, 10, 11, 12, 13, 14, 15};
    WhiteboxCrypto* wbc = WBC_new(key, sizeof(key));
    assert(wbc != nullptr);
    test_size_arithmetic(wbc);
    test_empty_roundtrip(wbc);
    test_malformed_padding(wbc);
    WBC_del(wbc);
    test_wbe_size_max_is_contained();
    std::cout << "core ABI regressions passed\n";
    return 0;
}
