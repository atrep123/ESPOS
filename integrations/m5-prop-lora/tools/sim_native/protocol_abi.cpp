#include "prop_protocol.h"

#include <cstdint>
#include <cstring>
#include <vector>

extern "C" int proto_encode(unsigned char type,
                            unsigned char key_id,
                            unsigned char src,
                            unsigned char dst,
                            unsigned int seq,
                            unsigned long long nonce,
                            const unsigned char* payload,
                            int payload_len,
                            const unsigned char* key,
                            int key_len,
                            unsigned char* out,
                            int out_cap) {
    if (payload_len < 0 || key_len < 0 || out == nullptr || out_cap < 0) {
        return -1;
    }
    if (payload_len > 0 && payload == nullptr) {
        return -1;
    }

    prop_protocol::Frame frame;
    frame.type = static_cast<prop_protocol::FrameType>(type);
    frame.keyId = key_id;
    frame.source = src;
    frame.destination = dst;
    frame.sequence = static_cast<uint32_t>(seq);
    frame.nonce = static_cast<uint64_t>(nonce);
    frame.payload.assign(payload, payload + payload_len);

    std::vector<uint8_t> encoded;
    if (!prop_protocol::encodeFrame(frame, key, static_cast<size_t>(key_len), encoded)) {
        return -1;
    }
    if (encoded.size() > static_cast<size_t>(out_cap)) {
        return -1;
    }
    std::memcpy(out, encoded.data(), encoded.size());
    return static_cast<int>(encoded.size());
}

extern "C" int proto_decode(const unsigned char* data,
                            int len,
                            const unsigned char* key,
                            int key_len,
                            unsigned char* out_payload,
                            int out_cap,
                            unsigned char* out_fields) {
    if (len < 0 || key_len < 0 || out_cap < 0 || out_fields == nullptr) {
        return -1;
    }
    if (len > 0 && data == nullptr) {
        return -1;
    }

    prop_protocol::Frame frame;
    if (!prop_protocol::decodeFrame(data, static_cast<size_t>(len), key, static_cast<size_t>(key_len), frame)) {
        return -1;
    }
    if (frame.payload.size() > static_cast<size_t>(out_cap)) {
        return -1;
    }
    if (!frame.payload.empty() && out_payload == nullptr) {
        return -1;
    }

    if (!frame.payload.empty()) {
        std::memcpy(out_payload, frame.payload.data(), frame.payload.size());
    }

    out_fields[0] = static_cast<unsigned char>(frame.type);
    out_fields[1] = frame.keyId;
    out_fields[2] = frame.source;
    out_fields[3] = frame.destination;
    out_fields[4] = static_cast<unsigned char>((frame.sequence >> 24) & 0xffU);
    out_fields[5] = static_cast<unsigned char>((frame.sequence >> 16) & 0xffU);
    out_fields[6] = static_cast<unsigned char>((frame.sequence >> 8) & 0xffU);
    out_fields[7] = static_cast<unsigned char>(frame.sequence & 0xffU);
    out_fields[8] = static_cast<unsigned char>((frame.nonce >> 56) & 0xffU);
    out_fields[9] = static_cast<unsigned char>((frame.nonce >> 48) & 0xffU);
    out_fields[10] = static_cast<unsigned char>((frame.nonce >> 40) & 0xffU);
    out_fields[11] = static_cast<unsigned char>((frame.nonce >> 32) & 0xffU);
    out_fields[12] = static_cast<unsigned char>((frame.nonce >> 24) & 0xffU);
    out_fields[13] = static_cast<unsigned char>((frame.nonce >> 16) & 0xffU);
    out_fields[14] = static_cast<unsigned char>((frame.nonce >> 8) & 0xffU);
    out_fields[15] = static_cast<unsigned char>(frame.nonce & 0xffU);

    return static_cast<int>(frame.payload.size());
}
