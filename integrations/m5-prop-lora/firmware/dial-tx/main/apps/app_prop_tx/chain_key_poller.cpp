#include "chain_key_poller.h"

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <cstring>

namespace MOONCAKE
{
    namespace USER_APP
    {
        namespace PROP_TX
        {
            namespace
            {
#ifndef PROP_TX_CHAIN_TX_GPIO
#define PROP_TX_CHAIN_TX_GPIO 2
#endif

#ifndef PROP_TX_CHAIN_RX_GPIO
#define PROP_TX_CHAIN_RX_GPIO 1
#endif

                constexpr const char* TAG = "prop_chain_key";
                constexpr uart_port_t CHAIN_KEY_UART_PORT = UART_NUM_2;
                constexpr int CHAIN_KEY_BAUD = 115200;
                // CONFIGURE-ME: default M5Dial Port B is G2=TX, G1=RX. These may need swapping on real HW.
                constexpr int CHAIN_KEY_TX_GPIO = PROP_TX_CHAIN_TX_GPIO;
                constexpr int CHAIN_KEY_RX_GPIO = PROP_TX_CHAIN_RX_GPIO;

                constexpr uint8_t PACK_HEAD_HIGH = 0xAA;
                constexpr uint8_t PACK_HEAD_LOW = 0x55;
                constexpr uint8_t PACK_END_HIGH = 0x55;
                constexpr uint8_t PACK_END_LOW = 0xAA;
                constexpr size_t PACK_SIZE_MIN = 0x09;
                constexpr size_t CHAIN_RESPONSE_MAX = 32;

                constexpr uint8_t CHAIN_HEARTBEAT = 0xFD;
                constexpr uint8_t CHAIN_ENUM = 0xFE;
                constexpr uint8_t CHAIN_GET_DEVICE_TYPE = 0xFB;
                constexpr uint8_t CHAIN_BUTTON_GET_STATUS = 0xE1;
                constexpr uint16_t CHAIN_KEY_TYPE_CODE = 0x0003;
                constexpr uint8_t CHAIN_BROADCAST_ID = 0xFF;
                constexpr uint8_t CHAIN_KEY_ID = 1;

                constexpr uint32_t CHAIN_DETECT_TIMEOUT_MS = 100;
                constexpr uint32_t CHAIN_HEARTBEAT_TIMEOUT_MS = 20;
                constexpr uint32_t CHAIN_KEY_READ_TIMEOUT_MS = 20;

                uint32_t now_ms()
                {
                    return static_cast<uint32_t>(esp_timer_get_time() / 1000ULL);
                }

                uint8_t chain_crc(const uint8_t* packet, size_t packet_size)
                {
                    uint8_t crc = 0;
                    for (size_t i = 4; i < packet_size - 3; ++i)
                    {
                        crc = static_cast<uint8_t>(crc + packet[i]);
                    }
                    return crc;
                }

                bool check_packet(const uint8_t* packet, size_t packet_size)
                {
                    if (packet_size < PACK_SIZE_MIN)
                    {
                        return false;
                    }

                    if (packet[0] != PACK_HEAD_HIGH || packet[1] != PACK_HEAD_LOW ||
                        packet[packet_size - 2] != PACK_END_HIGH || packet[packet_size - 1] != PACK_END_LOW)
                    {
                        return false;
                    }

                    const uint16_t length = static_cast<uint16_t>(packet[2]) |
                                            (static_cast<uint16_t>(packet[3]) << 8);
                    if (static_cast<size_t>(length) + 6 != packet_size)
                    {
                        return false;
                    }

                    return chain_crc(packet, packet_size) == packet[packet_size - 3];
                }
            }

            bool ChainKeyPoller::begin()
            {
                _detected = false;
                _rx_size = 0;

                uart_config_t uart_config = {};
                uart_config.baud_rate = CHAIN_KEY_BAUD;
                uart_config.data_bits = UART_DATA_8_BITS;
                uart_config.parity = UART_PARITY_DISABLE;
                uart_config.stop_bits = UART_STOP_BITS_1;
                uart_config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
                uart_config.rx_flow_ctrl_thresh = 0;

                esp_err_t ret = uart_param_config(CHAIN_KEY_UART_PORT, &uart_config);
                if (ret != ESP_OK)
                {
                    ESP_LOGW(TAG, "UART2 param config failed: %d", ret);
                    return false;
                }

                ret = uart_set_pin(
                    CHAIN_KEY_UART_PORT, CHAIN_KEY_TX_GPIO, CHAIN_KEY_RX_GPIO, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
                if (ret != ESP_OK)
                {
                    ESP_LOGW(TAG, "UART2 pin config failed: %d", ret);
                    return false;
                }

                ret = uart_driver_install(CHAIN_KEY_UART_PORT, 512, 0, 0, nullptr, 0);
                if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE)
                {
                    ESP_LOGW(TAG, "UART2 driver install failed: %d", ret);
                    return false;
                }

                _driver_ready = true;
                uart_flush_input(CHAIN_KEY_UART_PORT);

                _detected = _detect_key();
                if (!_detected)
                {
                    ESP_LOGW(TAG, "Chain Key id 1 not detected on UART2");
                    // Fail clean: do NOT leave the UART2 driver installed with _driver_ready
                    // set when detection failed, so a later retry starts from a known state.
                    uart_driver_delete(CHAIN_KEY_UART_PORT);
                    _driver_ready = false;
                    _rx_size = 0;
                }
                return _detected;
            }

            void ChainKeyPoller::end()
            {
                if (!_driver_ready)
                {
                    return;
                }

                uart_driver_delete(CHAIN_KEY_UART_PORT);
                _driver_ready = false;
                _detected = false;
                _rx_size = 0;
            }

            bool ChainKeyPoller::readPressed(bool* pressed)
            {
                if (pressed == nullptr)
                {
                    return false;
                }
                *pressed = false;

                if (!_driver_ready || !_detected)
                {
                    return false;
                }

                uint8_t response[CHAIN_RESPONSE_MAX] = {0};
                size_t response_size = sizeof(response);
                if (!_request(CHAIN_KEY_ID,
                              CHAIN_BUTTON_GET_STATUS,
                              nullptr,
                              0,
                              response,
                              &response_size,
                              CHAIN_KEY_READ_TIMEOUT_MS) ||
                    response_size < 1)
                {
                    return false;
                }

                // Fire-button interlock: accept ONLY a well-formed 0/1 status. A corrupted
                // (but CRC-valid) frame carrying any other value must NOT read as "pressed".
                if (response[0] > 1)
                {
                    return false;
                }
                *pressed = (response[0] == 1);
                return true;
            }

            bool ChainKeyPoller::_detect_key()
            {
                uint8_t response[CHAIN_RESPONSE_MAX] = {0};
                size_t response_size = sizeof(response);
                if (!_request(CHAIN_BROADCAST_ID,
                              CHAIN_HEARTBEAT,
                              nullptr,
                              0,
                              response,
                              &response_size,
                              CHAIN_HEARTBEAT_TIMEOUT_MS))
                {
                    return false;
                }

                uint8_t enum_payload = 0x00;
                response_size = sizeof(response);
                if (!_request(CHAIN_BROADCAST_ID,
                              CHAIN_ENUM,
                              &enum_payload,
                              1,
                              response,
                              &response_size,
                              CHAIN_DETECT_TIMEOUT_MS) ||
                    response_size < 1 || response[0] < CHAIN_KEY_ID)
                {
                    return false;
                }

                response_size = sizeof(response);
                if (!_request(CHAIN_KEY_ID,
                              CHAIN_GET_DEVICE_TYPE,
                              nullptr,
                              0,
                              response,
                              &response_size,
                              CHAIN_DETECT_TIMEOUT_MS) ||
                    response_size < 2)
                {
                    return false;
                }

                const uint16_t device_type = static_cast<uint16_t>(response[0]) |
                                             (static_cast<uint16_t>(response[1]) << 8);
                return device_type == CHAIN_KEY_TYPE_CODE;
            }

            bool ChainKeyPoller::_request(uint8_t id,
                                          uint8_t command,
                                          const uint8_t* payload,
                                          size_t payload_size,
                                          uint8_t* response_payload,
                                          size_t* response_payload_size,
                                          uint32_t timeout_ms)
            {
                if (!_driver_ready)
                {
                    return false;
                }

                _rx_size = 0;
                uart_flush_input(CHAIN_KEY_UART_PORT);

                if (!_write_packet(id, command, payload, payload_size))
                {
                    return false;
                }
                return _wait_for_packet(id, command, response_payload, response_payload_size, timeout_ms);
            }

            bool ChainKeyPoller::_write_packet(uint8_t id,
                                               uint8_t command,
                                               const uint8_t* payload,
                                               size_t payload_size)
            {
                if (payload_size > CHAIN_RESPONSE_MAX)
                {
                    return false;
                }

                uint8_t packet[CHAIN_RESPONSE_MAX + 9] = {0};
                const uint16_t length = static_cast<uint16_t>(3 + payload_size);
                const size_t packet_size = payload_size + 9;

                packet[0] = PACK_HEAD_HIGH;
                packet[1] = PACK_HEAD_LOW;
                packet[2] = static_cast<uint8_t>(length & 0xFF);
                packet[3] = static_cast<uint8_t>((length >> 8) & 0xFF);
                packet[4] = id;
                packet[5] = command;
                if (payload_size > 0 && payload != nullptr)
                {
                    memcpy(packet + 6, payload, payload_size);
                }
                packet[packet_size - 3] = chain_crc(packet, packet_size);
                packet[packet_size - 2] = PACK_END_HIGH;
                packet[packet_size - 1] = PACK_END_LOW;

                const int written = uart_write_bytes(CHAIN_KEY_UART_PORT, packet, packet_size);
                return written == static_cast<int>(packet_size);
            }

            bool ChainKeyPoller::_wait_for_packet(uint8_t id,
                                                  uint8_t command,
                                                  uint8_t* response_payload,
                                                  size_t* response_payload_size,
                                                  uint32_t timeout_ms)
            {
                const uint32_t start = now_ms();
                while (now_ms() - start < timeout_ms)
                {
                    if (_extract_packet(id, command, response_payload, response_payload_size))
                    {
                        return true;
                    }

                    uint8_t bytes[32] = {0};
                    const int read_count = uart_read_bytes(CHAIN_KEY_UART_PORT, bytes, sizeof(bytes), pdMS_TO_TICKS(1));
                    if (read_count > 0)
                    {
                        const size_t available = sizeof(_rx_buffer) - _rx_size;
                        const size_t copy_count = (static_cast<size_t>(read_count) < available) ?
                                                      static_cast<size_t>(read_count) :
                                                      available;
                        if (copy_count > 0)
                        {
                            memcpy(_rx_buffer + _rx_size, bytes, copy_count);
                            _rx_size += copy_count;
                        }
                        if (copy_count < static_cast<size_t>(read_count))
                        {
                            _rx_size = 0;
                        }
                    }
                }

                return _extract_packet(id, command, response_payload, response_payload_size);
            }

            bool ChainKeyPoller::_extract_packet(uint8_t id,
                                                 uint8_t command,
                                                 uint8_t* response_payload,
                                                 size_t* response_payload_size)
            {
                size_t start = 0;
                while (_rx_size >= start + PACK_SIZE_MIN)
                {
                    if (_rx_buffer[start] != PACK_HEAD_HIGH || _rx_buffer[start + 1] != PACK_HEAD_LOW)
                    {
                        ++start;
                        continue;
                    }

                    const uint16_t length = static_cast<uint16_t>(_rx_buffer[start + 2]) |
                                            (static_cast<uint16_t>(_rx_buffer[start + 3]) << 8);
                    const size_t packet_size = static_cast<size_t>(length) + 6;
                    if (packet_size < PACK_SIZE_MIN || packet_size > sizeof(_rx_buffer))
                    {
                        ++start;
                        continue;
                    }
                    if (_rx_size - start < packet_size)
                    {
                        break;
                    }

                    uint8_t* packet = _rx_buffer + start;
                    if (!check_packet(packet, packet_size))
                    {
                        ++start;
                        continue;
                    }

                    const bool matched = (packet[4] == id && packet[5] == command);
                    if (matched)
                    {
                        const size_t payload_size = static_cast<size_t>(length) - 3;
                        if (response_payload != nullptr && response_payload_size != nullptr)
                        {
                            if (*response_payload_size < payload_size)
                            {
                                _drop_rx_bytes(start + packet_size);
                                return false;
                            }
                            memcpy(response_payload, packet + 6, payload_size);
                            *response_payload_size = payload_size;
                        }
                    }

                    _drop_rx_bytes(start + packet_size);
                    if (matched)
                    {
                        return true;
                    }
                    start = 0;
                }

                if (start > 0)
                {
                    _drop_rx_bytes(start);
                }
                return false;
            }

            void ChainKeyPoller::_drop_rx_bytes(size_t count)
            {
                if (count >= _rx_size)
                {
                    _rx_size = 0;
                    return;
                }

                memmove(_rx_buffer, _rx_buffer + count, _rx_size - count);
                _rx_size -= count;
            }
        }
    }
}
