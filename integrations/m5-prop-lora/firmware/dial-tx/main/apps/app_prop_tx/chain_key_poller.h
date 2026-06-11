#pragma once

#include <cstddef>
#include <cstdint>

namespace MOONCAKE
{
    namespace USER_APP
    {
        namespace PROP_TX
        {
            class ChainKeyPoller
            {
                public:
                    bool begin();
                    void end();
                    bool detected() const { return _detected; }
                    bool readPressed(bool* pressed);

                private:
                    bool _driver_ready = false;
                    bool _detected = false;
                    uint8_t _rx_buffer[128] = {0};
                    size_t _rx_size = 0;

                    bool _detect_key();
                    bool _request(uint8_t id,
                                  uint8_t command,
                                  const uint8_t* payload,
                                  size_t payload_size,
                                  uint8_t* response_payload,
                                  size_t* response_payload_size,
                                  uint32_t timeout_ms);
                    bool _write_packet(uint8_t id, uint8_t command, const uint8_t* payload, size_t payload_size);
                    bool _wait_for_packet(uint8_t id,
                                          uint8_t command,
                                          uint8_t* response_payload,
                                          size_t* response_payload_size,
                                          uint32_t timeout_ms);
                    bool _extract_packet(uint8_t id,
                                         uint8_t command,
                                         uint8_t* response_payload,
                                         size_t* response_payload_size);
                    void _drop_rx_bytes(size_t count);
            };
        }
    }
}
