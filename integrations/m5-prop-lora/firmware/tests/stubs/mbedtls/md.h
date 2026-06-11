#pragma once
// Compile-ONLY stub of the tiny mbedtls/md.h surface referenced by
// shared/protocol/prop_protocol.h (HMAC-SHA256 frame authentication).
//
// Why: it lets host unit tests that include prop_protocol.h but DO NOT exercise
// frame crypto (e.g. test_palette.cpp -- palette encode/decode only) COMPILE
// with a bare host toolchain that has no real mbedtls installed.
//
// These are DECLARATIONS ONLY and are intentionally left undefined. The inline
// HMAC helpers in prop_protocol.h are not ODR-used by such tests, so nothing
// links against them. A host test that DOES call encodeFrame/decodeFrame/
// hmacSha256Truncated will fail to LINK (undefined reference) instead of
// silently "passing" with fake crypto -- a loud, safe failure. Provide a real
// mbedtls (or a vetted SHA-256/HMAC implementation) before adding such a test.

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MBEDTLS_MD_NONE = 0,
    MBEDTLS_MD_SHA256,
} mbedtls_md_type_t;

typedef struct mbedtls_md_info_t mbedtls_md_info_t;

const mbedtls_md_info_t *mbedtls_md_info_from_type(mbedtls_md_type_t md_type);

int mbedtls_md_hmac(const mbedtls_md_info_t *md_info,
                    const unsigned char *key, size_t keylen,
                    const unsigned char *input, size_t ilen,
                    unsigned char *output);

#ifdef __cplusplus
}
#endif
