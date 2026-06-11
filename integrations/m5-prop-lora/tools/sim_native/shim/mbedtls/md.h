#ifndef SIM_NATIVE_MBEDTLS_MD_H
#define SIM_NATIVE_MBEDTLS_MD_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MBEDTLS_MD_SHA256 = 6
} mbedtls_md_type_t;

typedef struct mbedtls_md_info_t mbedtls_md_info_t;

const mbedtls_md_info_t* mbedtls_md_info_from_type(mbedtls_md_type_t type);
int mbedtls_md_hmac(const mbedtls_md_info_t* info,
                    const unsigned char* key,
                    size_t keylen,
                    const unsigned char* input,
                    size_t ilen,
                    unsigned char* output);

#ifdef __cplusplus
}
#endif

#endif
