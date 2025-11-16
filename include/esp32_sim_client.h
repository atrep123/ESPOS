/**
 * ESP32 Simulator Client Library (C/C++)
 * Header-only library for communicating with the Python simulator via TCP RPC
 * 
 * Usage:
 *   #include "esp32_sim_client.h"
 *   
 *   esp32_sim_client_t client;
 *   if (esp32_sim_connect(&client, "127.0.0.1", 8765)) {
 *       esp32_sim_set_bg_rgb(&client, 255, 0, 0);
 *       esp32_sim_button_click(&client, 'A', 100);
 *       esp32_sim_disconnect(&client);
 *   }
 */

#ifndef ESP32_SIM_CLIENT_H
#define ESP32_SIM_CLIENT_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define INVALID_SOCKET_VALUE INVALID_SOCKET
    #define close_socket closesocket
#else
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    typedef int socket_t;
    #define INVALID_SOCKET_VALUE -1
    #define close_socket close
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    socket_t sock;
    char host[64];
    uint16_t port;
    bool connected;
} esp32_sim_client_t;

/**
 * Initialize Windows sockets (Windows only, call once at startup)
 */
static inline bool esp32_sim_init(void) {
#ifdef _WIN32
    WSADATA wsa_data;
    return WSAStartup(MAKEWORD(2, 2), &wsa_data) == 0;
#else
    return true;
#endif
}

/**
 * Cleanup Windows sockets (Windows only, call at shutdown)
 */
static inline void esp32_sim_cleanup(void) {
#ifdef _WIN32
    WSACleanup();
#endif
}

/**
 * Connect to simulator
 */
static inline bool esp32_sim_connect(esp32_sim_client_t *client, const char *host, uint16_t port) {
    if (!client) return false;
    
    memset(client, 0, sizeof(esp32_sim_client_t));
    strncpy(client->host, host, sizeof(client->host) - 1);
    client->port = port;
    
    client->sock = socket(AF_INET, SOCK_STREAM, 0);
    if (client->sock == INVALID_SOCKET_VALUE) {
        return false;
    }
    
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    
#ifdef _WIN32
    server_addr.sin_addr.s_addr = inet_addr(host);
#else
    inet_pton(AF_INET, host, &server_addr.sin_addr);
#endif
    
    if (connect(client->sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        close_socket(client->sock);
        client->sock = INVALID_SOCKET_VALUE;
        return false;
    }
    
    client->connected = true;
    return true;
}

/**
 * Disconnect from simulator
 */
static inline void esp32_sim_disconnect(esp32_sim_client_t *client) {
    if (!client || !client->connected) return;
    
    if (client->sock != INVALID_SOCKET_VALUE) {
        close_socket(client->sock);
        client->sock = INVALID_SOCKET_VALUE;
    }
    client->connected = false;
}

/**
 * Send raw JSON RPC message
 */
static inline bool esp32_sim_send_raw(esp32_sim_client_t *client, const char *json) {
    if (!client || !client->connected || !json) return false;
    
    char buffer[512];
    int len = snprintf(buffer, sizeof(buffer), "%s\n", json);
    
    if (len < 0 || len >= (int)sizeof(buffer)) {
        return false;
    }
    
    int sent = send(client->sock, buffer, len, 0);
    return sent == len;
}

/**
 * Set background color (RGB888)
 */
static inline bool esp32_sim_set_bg_rgb(esp32_sim_client_t *client, uint8_t r, uint8_t g, uint8_t b) {
    char json[128];
    snprintf(json, sizeof(json), "{\"method\":\"set_bg\",\"rgb\":[%d,%d,%d]}", r, g, b);
    return esp32_sim_send_raw(client, json);
}

/**
 * Set background color (RGB565)
 */
static inline bool esp32_sim_set_bg_rgb565(esp32_sim_client_t *client, uint16_t rgb565) {
    char json[128];
    snprintf(json, sizeof(json), "{\"method\":\"set_bg\",\"rgb565\":%d}", rgb565);
    return esp32_sim_send_raw(client, json);
}

/**
 * Press button
 */
static inline bool esp32_sim_button_press(esp32_sim_client_t *client, char button) {
    char json[128];
    snprintf(json, sizeof(json), "{\"method\":\"btn\",\"id\":\"%c\",\"pressed\":true}", button);
    return esp32_sim_send_raw(client, json);
}

/**
 * Release button
 */
static inline bool esp32_sim_button_release(esp32_sim_client_t *client, char button) {
    char json[128];
    snprintf(json, sizeof(json), "{\"method\":\"btn\",\"id\":\"%c\",\"pressed\":false}", button);
    return esp32_sim_send_raw(client, json);
}

/**
 * Click button (press + delay + release)
 */
static inline bool esp32_sim_button_click(esp32_sim_client_t *client, char button, int delay_ms) {
    if (!esp32_sim_button_press(client, button)) return false;
    
#ifdef _WIN32
    Sleep(delay_ms);
#else
    usleep(delay_ms * 1000);
#endif
    
    return esp32_sim_button_release(client, button);
}

/**
 * Set scene (0=HOME, 1=SETTINGS, 2=CUSTOM)
 */
static inline bool esp32_sim_set_scene(esp32_sim_client_t *client, int scene) {
    if (scene < 0) scene = 0;
    if (scene > 2) scene = 2;
    
    char json[128];
    snprintf(json, sizeof(json), "{\"method\":\"scene\",\"value\":%d}", scene);
    return esp32_sim_send_raw(client, json);
}

#ifdef __cplusplus
}
#endif

#endif // ESP32_SIM_CLIENT_H
