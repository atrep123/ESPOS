#include <mbedtls/md.h>

#include "sha256.h"

#include <string.h>

struct mbedtls_md_info_t {
    int type;
};

static const mbedtls_md_info_t sha256_info = { MBEDTLS_MD_SHA256 };

const mbedtls_md_info_t* mbedtls_md_info_from_type(mbedtls_md_type_t type) {
    if (type != MBEDTLS_MD_SHA256) {
        return 0;
    }
    return &sha256_info;
}

int mbedtls_md_hmac(const mbedtls_md_info_t* info,
                    const unsigned char* key,
                    size_t keylen,
                    const unsigned char* input,
                    size_t ilen,
                    unsigned char* output) {
    unsigned char key_hash[32];
    unsigned char block[64];
    unsigned char inner_hash[32];
    unsigned char ipad[64];
    unsigned char opad[64];
    size_t i;
    sha256_ctx ctx;

    if (info == 0 || info->type != MBEDTLS_MD_SHA256 || key == 0 || output == 0) {
        return -1;
    }
    if (input == 0 && ilen != 0) {
        return -1;
    }

    memset(block, 0, sizeof(block));
    if (keylen > sizeof(block)) {
        sha256_init(&ctx);
        sha256_update(&ctx, key, keylen);
        sha256_final(&ctx, key_hash);
        memcpy(block, key_hash, sizeof(key_hash));
    } else if (keylen > 0) {
        memcpy(block, key, keylen);
    }

    for (i = 0; i < sizeof(block); ++i) {
        ipad[i] = (unsigned char)(block[i] ^ 0x36U);
        opad[i] = (unsigned char)(block[i] ^ 0x5cU);
    }

    sha256_init(&ctx);
    sha256_update(&ctx, ipad, sizeof(ipad));
    sha256_update(&ctx, input, ilen);
    sha256_final(&ctx, inner_hash);

    sha256_init(&ctx);
    sha256_update(&ctx, opad, sizeof(opad));
    sha256_update(&ctx, inner_hash, sizeof(inner_hash));
    sha256_final(&ctx, output);

    return 0;
}
