/*
 * Copyright 2010-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * Additions Copyright 2016 Espressif Systems (Shanghai) PTE LTD
 *
 * Licensed under the Apache License, Version 2.0.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#include "aws_iot_config.h"
#include "aws_iot_log.h"
#include "aws_iot_mqtt_client_interface.h"
#include "aws_iot_version.h"

static const char *TAG = "pillbuddy";

#define EXAMPLE_WIFI_SSID CONFIG_WIFI_SSID
#define EXAMPLE_WIFI_PASS CONFIG_WIFI_PASSWORD

#define SLOT_COUNT 3
#define WIFI_CONNECTED_BIT BIT0
#define MQTT_READY_BIT BIT1
#define ENABLE_STARTUP_SLOT_STATE_PUBLISH 1 /* Set to 0 to disable startup slot-state events. */

#define TOPIC_BUF_LEN 128
#define MQTT_CMD_PAYLOAD_BUF_LEN 160
#define MQTT_EVENT_PAYLOAD_BUF_LEN 128

#define SENSOR_IRQ_QUEUE_LEN 16
#define PUBLISH_QUEUE_LEN 16

#define SENSOR_TASK_STACK 4096
#define PUBLISHER_TASK_STACK 4096
#define MQTT_TASK_STACK 10240
#define SENSOR_TASK_PRIO 6
#define PUBLISHER_TASK_PRIO 5
#define MQTT_TASK_PRIO 5
#define TASK_CORE_ID 1

#define MQTT_MUTEX_TIMEOUT_MS 2000
#define MQTT_CONNECT_RETRY_DELAY_MS 1500
#define MQTT_INIT_RETRY_DELAY_MS 1000
#define MQTT_LOOP_LOCK_RETRY_DELAY_MS 200
#define MQTT_PUBLISH_FAIL_DELAY_MS 500
#define MQTT_YIELD_FAIL_DELAY_MS 400
#define MQTT_YIELD_TIMEOUT_MS 50
#define MQTT_LOOP_BACKOFF_MS 25
#define SENSOR_QUEUE_WAIT_MS 50
#define QUEUE_SEND_TIMEOUT_MS 100

typedef struct {
    uint8_t slot_idx; /* 0..2 */
} sensor_irq_event_t;

typedef struct {
    uint8_t slot; /* 1..3 */
    bool in_holder;
} slot_state_event_t;

static EventGroupHandle_t s_event_group;
static QueueHandle_t s_sensor_irq_queue;
static QueueHandle_t s_publish_queue;
static SemaphoreHandle_t s_mqtt_mutex;

static AWS_IoT_Client s_mqtt_client;
static bool s_mqtt_initialized = false;

static char s_event_topic[TOPIC_BUF_LEN];
static char s_cmd_topic[TOPIC_BUF_LEN];

static const gpio_num_t s_switch_gpios[SLOT_COUNT] = {
    CONFIG_PILL_SLOT1_SW_GPIO,
    CONFIG_PILL_SLOT2_SW_GPIO,
    CONFIG_PILL_SLOT3_SW_GPIO,
};

static const gpio_num_t s_led_gpios[SLOT_COUNT] = {
    CONFIG_PILL_SLOT1_LED_GPIO,
    CONFIG_PILL_SLOT2_LED_GPIO,
    CONFIG_PILL_SLOT3_LED_GPIO,
};

static int s_last_stable_levels[SLOT_COUNT];
static bool s_led_states[SLOT_COUNT];
static int s_pending_levels[SLOT_COUNT];
static uint64_t s_pending_since_ms[SLOT_COUNT];
static bool s_pending_active[SLOT_COUNT];
static bool s_startup_slot_state_published = false;

static inline const char *level_to_state_name(int level) {
    return (level == 0) ? "in_holder" : "not_in_holder";
}

static inline bool level_to_in_holder(int level) {
    return (level == 0);
}

static const char *iot_error_to_str(IoT_Error_t rc) {
    switch (rc) {
        case SUCCESS:
            return "SUCCESS";
        case SSL_CONNECTION_ERROR:
            return "SSL_CONNECTION_ERROR";
        case NETWORK_SSL_CERT_ERROR:
            return "NETWORK_SSL_CERT_ERROR";
        case NETWORK_SSL_READ_ERROR:
            return "NETWORK_SSL_READ_ERROR";
        case NETWORK_SSL_READ_TIMEOUT_ERROR:
            return "NETWORK_SSL_READ_TIMEOUT_ERROR";
        case NETWORK_X509_ROOT_CRT_PARSE_ERROR:
            return "NETWORK_X509_ROOT_CRT_PARSE_ERROR";
        case NETWORK_X509_DEVICE_CRT_PARSE_ERROR:
            return "NETWORK_X509_DEVICE_CRT_PARSE_ERROR";
        case NETWORK_PK_PRIVATE_KEY_PARSE_ERROR:
            return "NETWORK_PK_PRIVATE_KEY_PARSE_ERROR";
        case NETWORK_ERR_NET_UNKNOWN_HOST:
            return "NETWORK_ERR_NET_UNKNOWN_HOST";
        case NETWORK_ERR_NET_CONNECT_FAILED:
            return "NETWORK_ERR_NET_CONNECT_FAILED";
        case MQTT_CONNACK_NOT_AUTHORIZED_ERROR:
            return "MQTT_CONNACK_NOT_AUTHORIZED_ERROR";
        default:
            return "UNMAPPED_IOT_ERROR";
    }
}

static const char *wifi_disc_reason_to_str(uint8_t reason) {
    switch (reason) {
        case WIFI_REASON_AUTH_EXPIRE:
            return "AUTH_EXPIRE";
        case WIFI_REASON_AUTH_LEAVE:
            return "AUTH_LEAVE";
        case WIFI_REASON_ASSOC_EXPIRE:
            return "ASSOC_EXPIRE";
        case WIFI_REASON_ASSOC_TOOMANY:
            return "ASSOC_TOOMANY";
        case WIFI_REASON_NOT_AUTHED:
            return "NOT_AUTHED";
        case WIFI_REASON_NOT_ASSOCED:
            return "NOT_ASSOCED";
        case WIFI_REASON_ASSOC_LEAVE:
            return "ASSOC_LEAVE";
        case WIFI_REASON_ASSOC_NOT_AUTHED:
            return "ASSOC_NOT_AUTHED";
        case WIFI_REASON_DISASSOC_PWRCAP_BAD:
            return "DISASSOC_PWRCAP_BAD";
        case WIFI_REASON_DISASSOC_SUPCHAN_BAD:
            return "DISASSOC_SUPCHAN_BAD";
        case WIFI_REASON_IE_INVALID:
            return "IE_INVALID";
        case WIFI_REASON_MIC_FAILURE:
            return "MIC_FAILURE";
        case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
            return "4WAY_HANDSHAKE_TIMEOUT";
        case WIFI_REASON_GROUP_KEY_UPDATE_TIMEOUT:
            return "GROUP_KEY_UPDATE_TIMEOUT";
        case WIFI_REASON_IE_IN_4WAY_DIFFERS:
            return "IE_IN_4WAY_DIFFERS";
        case WIFI_REASON_GROUP_CIPHER_INVALID:
            return "GROUP_CIPHER_INVALID";
        case WIFI_REASON_PAIRWISE_CIPHER_INVALID:
            return "PAIRWISE_CIPHER_INVALID";
        case WIFI_REASON_AKMP_INVALID:
            return "AKMP_INVALID";
        case WIFI_REASON_UNSUPP_RSN_IE_VERSION:
            return "UNSUPP_RSN_IE_VERSION";
        case WIFI_REASON_INVALID_RSN_IE_CAP:
            return "INVALID_RSN_IE_CAP";
        case WIFI_REASON_802_1X_AUTH_FAILED:
            return "802_1X_AUTH_FAILED";
        case WIFI_REASON_CIPHER_SUITE_REJECTED:
            return "CIPHER_SUITE_REJECTED";
        case WIFI_REASON_BEACON_TIMEOUT:
            return "BEACON_TIMEOUT";
        case WIFI_REASON_NO_AP_FOUND:
            return "NO_AP_FOUND";
        case WIFI_REASON_AUTH_FAIL:
            return "AUTH_FAIL";
        case WIFI_REASON_ASSOC_FAIL:
            return "ASSOC_FAIL";
        case WIFI_REASON_HANDSHAKE_TIMEOUT:
            return "HANDSHAKE_TIMEOUT";
        case WIFI_REASON_CONNECTION_FAIL:
            return "CONNECTION_FAIL";
        default:
            return "UNKNOWN";
    }
}

#if defined(CONFIG_EXAMPLE_EMBEDDED_CERTS)
extern const uint8_t aws_root_ca_pem_start[] asm("_binary_aws_root_ca_pem_start");
extern const uint8_t aws_root_ca_pem_end[] asm("_binary_aws_root_ca_pem_end");
extern const uint8_t pillBuddy_cert_pem_start[] asm("_binary_pillBuddy_cert_pem_start");
extern const uint8_t pillBuddy_cert_pem_end[] asm("_binary_pillBuddy_cert_pem_end");
extern const uint8_t pillBuddy_private_key_start[] asm("_binary_pillBuddy_private_key_start");
extern const uint8_t pillBuddy_private_key_end[] asm("_binary_pillBuddy_private_key_end");
#elif defined(CONFIG_EXAMPLE_FILESYSTEM_CERTS)
static const char *DEVICE_CERTIFICATE_PATH = CONFIG_EXAMPLE_CERTIFICATE_PATH;
static const char *DEVICE_PRIVATE_KEY_PATH = CONFIG_EXAMPLE_PRIVATE_KEY_PATH;
static const char *ROOT_CA_PATH = CONFIG_EXAMPLE_ROOT_CA_PATH;
#else
#error "Invalid method for loading certs"
#endif

static void led_set(uint8_t slot_idx, bool on) {
    if (slot_idx >= SLOT_COUNT) {
        return;
    }
    s_led_states[slot_idx] = on;
    gpio_set_level(s_led_gpios[slot_idx], on ? 1 : 0);
    ESP_LOGI(TAG, "LED slot=%u -> %s", (unsigned int)(slot_idx + 1), on ? "ON" : "OFF");
}

static bool led_get(uint8_t slot_idx) {
    if (slot_idx >= SLOT_COUNT) {
        return false;
    }
    return s_led_states[slot_idx];
}

static const char *skip_ws(const char *s) {
    while (s != NULL && (*s == ' ' || *s == '\n' || *s == '\r' || *s == '\t')) {
        s++;
    }
    return s;
}

static bool parse_json_string_field(const char *json, const char *key, char *out, size_t out_len) {
    char key_pat[32];
    const char *key_pos;
    const char *colon;
    const char *q1;
    const char *q2;
    size_t len;

    if (json == NULL || key == NULL || out == NULL || out_len == 0) {
        return false;
    }
    snprintf(key_pat, sizeof(key_pat), "\"%s\"", key);
    key_pos = strstr(json, key_pat);
    if (key_pos == NULL) {
        return false;
    }
    colon = strchr(key_pos, ':');
    if (colon == NULL) {
        return false;
    }
    q1 = strchr(colon, '"');
    if (q1 == NULL) {
        return false;
    }
    q1++;
    q2 = strchr(q1, '"');
    if (q2 == NULL) {
        return false;
    }

    len = (size_t)(q2 - q1);
    if (len >= out_len) {
        len = out_len - 1;
    }
    memcpy(out, q1, len);
    out[len] = '\0';
    return true;
}

static bool parse_json_int_field(const char *json, const char *key, int *out) {
    char key_pat[32];
    const char *key_pos;
    const char *colon;
    const char *val;
    char *endptr = NULL;
    long parsed;

    if (json == NULL || key == NULL || out == NULL) {
        return false;
    }
    snprintf(key_pat, sizeof(key_pat), "\"%s\"", key);
    key_pos = strstr(json, key_pat);
    if (key_pos == NULL) {
        return false;
    }
    colon = strchr(key_pos, ':');
    if (colon == NULL) {
        return false;
    }
    val = skip_ws(colon + 1);
    if (val == NULL) {
        return false;
    }
    parsed = strtol(val, &endptr, 10);
    if (endptr == val) {
        return false;
    }
    *out = (int)parsed;
    return true;
}

static bool parse_led_command(const char *json, int *slot_one_based, bool *turn_on) {
    char action[24];
    int slot = 0;

    if (!parse_json_string_field(json, "action", action, sizeof(action))) {
        return false;
    }
    if (!parse_json_int_field(json, "slot", &slot)) {
        return false;
    }
    if (slot < 1 || slot > SLOT_COUNT) {
        return false;
    }

    if (strcmp(action, "turn_on") == 0) {
        *turn_on = true;
    } else if (strcmp(action, "turn_off") == 0) {
        *turn_on = false;
    } else {
        return false;
    }

    *slot_one_based = slot;
    return true;
}

static bool mqtt_lock(TickType_t wait_ticks) {
    return (xSemaphoreTake(s_mqtt_mutex, wait_ticks) == pdTRUE);
}

static void mqtt_unlock(void) {
    xSemaphoreGive(s_mqtt_mutex);
}

static IoT_Error_t mqtt_subscribe_command_topic(void);
static IoT_Error_t publish_slot_event(const slot_state_event_t *evt);

static void mqtt_disconnect_handler(AWS_IoT_Client *pClient, void *data) {
    IOT_UNUSED(pClient);
    IOT_UNUSED(data);
    xEventGroupClearBits(s_event_group, MQTT_READY_BIT);
    ESP_LOGW(TAG, "MQTT disconnected");
}

static void mqtt_command_callback(AWS_IoT_Client *pClient, char *topicName, uint16_t topicNameLen,
                                  IoT_Publish_Message_Params *params, void *pData) {
    char payload[MQTT_CMD_PAYLOAD_BUF_LEN];
    int slot = 0;
    bool turn_on = false;

    IOT_UNUSED(pClient);
    IOT_UNUSED(pData);

    if (params == NULL || params->payload == NULL) {
        return;
    }

    size_t copy_len = params->payloadLen;
    if (copy_len >= sizeof(payload)) {
        copy_len = sizeof(payload) - 1;
    }
    memcpy(payload, params->payload, copy_len);
    payload[copy_len] = '\0';

    ESP_LOGI(TAG, "CMD topic=%.*s payload=%s", topicNameLen, topicName, payload);

    if (!parse_led_command(payload, &slot, &turn_on)) {
        ESP_LOGW(TAG, "Invalid command payload: %s", payload);
        return;
    }

    led_set((uint8_t)(slot - 1), turn_on);
    ESP_LOGI(TAG, "Command applied: slot=%d action=%s", slot, turn_on ? "turn_on" : "turn_off");
}

static void build_topics(void) {
    snprintf(s_event_topic, sizeof(s_event_topic), "%s/%s", CONFIG_PILL_EVENT_TOPIC_BASE, CONFIG_PILL_DEVICE_ID);
    snprintf(s_cmd_topic, sizeof(s_cmd_topic), "%s/%s", CONFIG_PILL_COMMAND_TOPIC_BASE, CONFIG_PILL_DEVICE_ID);
    ESP_LOGI(TAG, "Event topic: %s", s_event_topic);
    ESP_LOGI(TAG, "Command topic: %s", s_cmd_topic);
}

static bool validate_gpio_config(void) {
    int i;
    bool ok = true;

    for (i = 0; i < SLOT_COUNT; i++) {
        int sw = (int)s_switch_gpios[i];
        int led = (int)s_led_gpios[i];

        if (!GPIO_IS_VALID_GPIO(sw)) {
            ESP_LOGE(TAG, "Slot %d switch GPIO %d is invalid", i + 1, sw);
            ok = false;
        }
        if (!GPIO_IS_VALID_OUTPUT_GPIO(led)) {
            ESP_LOGE(TAG, "Slot %d LED GPIO %d is not valid as output", i + 1, led);
            ok = false;
        }
        if (sw == led) {
            ESP_LOGE(TAG, "Slot %d uses same GPIO %d for switch and LED", i + 1, sw);
            ok = false;
        }
    }

    for (i = 0; i < SLOT_COUNT; i++) {
        int sw = (int)s_switch_gpios[i];
        int j;
        for (j = i + 1; j < SLOT_COUNT; j++) {
            if (sw == (int)s_switch_gpios[j]) {
                ESP_LOGE(TAG, "Switch GPIO conflict: slot %d and slot %d both use GPIO %d", i + 1, j + 1, sw);
                ok = false;
            }
            if ((int)s_led_gpios[i] == (int)s_led_gpios[j]) {
                ESP_LOGE(TAG, "LED GPIO conflict: slot %d and slot %d both use GPIO %d", i + 1, j + 1, (int)s_led_gpios[i]);
                ok = false;
            }
        }
    }

#if CONFIG_PILL_SWITCH_USE_INTERNAL_PULLUP
    for (i = 0; i < SLOT_COUNT; i++) {
        int sw = (int)s_switch_gpios[i];
        if (sw >= 34 && sw <= 39) {
            ESP_LOGW(TAG,
                     "Slot %d switch GPIO %d is input-only and has no internal pull-up on ESP32; add external pull-up.",
                     i + 1,
                     sw);
        }
    }
#endif

    return ok;
}

static IoT_Error_t mqtt_init_once(void) {
    IoT_Client_Init_Params mqtt_init_params = iotClientInitParamsDefault;
    IoT_Error_t rc;

    if (s_mqtt_initialized) {
        return SUCCESS;
    }

    mqtt_init_params.enableAutoReconnect = false;
    mqtt_init_params.pHostURL = AWS_IOT_MQTT_HOST;
    mqtt_init_params.port = AWS_IOT_MQTT_PORT;
#if defined(CONFIG_EXAMPLE_EMBEDDED_CERTS)
    mqtt_init_params.pRootCALocation = (char *)aws_root_ca_pem_start;
    mqtt_init_params.pDeviceCertLocation = (char *)pillBuddy_cert_pem_start;
    mqtt_init_params.pDevicePrivateKeyLocation = (char *)pillBuddy_private_key_start;
#elif defined(CONFIG_EXAMPLE_FILESYSTEM_CERTS)
    mqtt_init_params.pRootCALocation = ROOT_CA_PATH;
    mqtt_init_params.pDeviceCertLocation = DEVICE_CERTIFICATE_PATH;
    mqtt_init_params.pDevicePrivateKeyLocation = DEVICE_PRIVATE_KEY_PATH;
#endif
    mqtt_init_params.mqttCommandTimeout_ms = 20000;
    mqtt_init_params.tlsHandshakeTimeout_ms = 5000;
    mqtt_init_params.isSSLHostnameVerify = true;
    mqtt_init_params.disconnectHandler = mqtt_disconnect_handler;
    mqtt_init_params.disconnectHandlerData = NULL;

    rc = aws_iot_mqtt_init(&s_mqtt_client, &mqtt_init_params);
    if (rc == SUCCESS) {
        s_mqtt_initialized = true;
    }
    return rc;
}

static IoT_Error_t mqtt_connect_client(void) {
    IoT_Client_Connect_Params connect_params = iotClientConnectParamsDefault;
    IoT_Error_t rc;

    connect_params.keepAliveIntervalInSec = 10;
    connect_params.isCleanSession = true;
    connect_params.MQTTVersion = MQTT_3_1_1;
    connect_params.pClientID = CONFIG_AWS_EXAMPLE_CLIENT_ID;
    connect_params.clientIDLen = (uint16_t)strlen(CONFIG_AWS_EXAMPLE_CLIENT_ID);
    connect_params.isWillMsgPresent = false;

    rc = aws_iot_mqtt_connect(&s_mqtt_client, &connect_params);
    if (rc != SUCCESS) {
        return rc;
    }

    rc = aws_iot_mqtt_autoreconnect_set_status(&s_mqtt_client, true);
    if (rc != SUCCESS) {
        return rc;
    }

    return SUCCESS;
}

static IoT_Error_t mqtt_subscribe_command_topic(void) {
    return aws_iot_mqtt_subscribe(&s_mqtt_client,
                                  s_cmd_topic,
                                  (uint16_t)strlen(s_cmd_topic),
                                  QOS0,
                                  mqtt_command_callback,
                                  NULL);
}

static IoT_Error_t publish_startup_slot_states_locked(void) {
#if ENABLE_STARTUP_SLOT_STATE_PUBLISH
    int i;
    for (i = 0; i < SLOT_COUNT; i++) {
        slot_state_event_t evt = {
            .slot = (uint8_t)(i + 1),
            .in_holder = level_to_in_holder(gpio_get_level(s_switch_gpios[i])),
        };

        IoT_Error_t rc = publish_slot_event(&evt);
        if (rc != SUCCESS) {
            ESP_LOGW(TAG, "Startup slot-state publish failed slot=%d rc=%d", i + 1, rc);
            return rc;
        }
    }

    ESP_LOGI(TAG, "Published startup slot states for all %d slots", SLOT_COUNT);
    return SUCCESS;
#else
    return SUCCESS;
#endif
}

static void IRAM_ATTR switch_isr_handler(void *arg) {
    sensor_irq_event_t evt;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    evt.slot_idx = (uint8_t)(uint32_t)arg;
    xQueueSendFromISR(s_sensor_irq_queue, &evt, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

static void init_leds(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = 0,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    int i;

    for (i = 0; i < SLOT_COUNT; i++) {
        io_conf.pin_bit_mask |= (1ULL << s_led_gpios[i]);
    }
    ESP_ERROR_CHECK(gpio_config(&io_conf));

    for (i = 0; i < SLOT_COUNT; i++) {
        s_led_states[i] = true;
        led_set((uint8_t)i, true);
    }
}

static void init_switches(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = 0,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = CONFIG_PILL_SWITCH_USE_INTERNAL_PULLUP ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_ANYEDGE,
    };
    esp_err_t err;
    int i;

    for (i = 0; i < SLOT_COUNT; i++) {
        io_conf.pin_bit_mask |= (1ULL << s_switch_gpios[i]);
    }
    ESP_ERROR_CHECK(gpio_config(&io_conf));

    err = gpio_install_isr_service(0);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_ERROR_CHECK(err);
    }

    for (i = 0; i < SLOT_COUNT; i++) {
        ESP_ERROR_CHECK(gpio_isr_handler_add(s_switch_gpios[i], switch_isr_handler, (void *)(uint32_t)i));
        s_last_stable_levels[i] = gpio_get_level(s_switch_gpios[i]);
        ESP_LOGI(TAG,
                 "Initial slot=%d switch gpio=%d level=%d -> state=%s",
                 i + 1,
                 s_switch_gpios[i],
                 s_last_stable_levels[i],
                 level_to_state_name(s_last_stable_levels[i]));
    }
}

static void wifi_event_handler(void *handler_args, esp_event_base_t base, int32_t id, void *event_data) {
    IOT_UNUSED(handler_args);

    if (base == WIFI_EVENT) {
        if (id == WIFI_EVENT_STA_START) {
            ESP_LOGI(TAG, "Wi-Fi started, connecting...");
            esp_wifi_connect();
            xEventGroupClearBits(s_event_group, WIFI_CONNECTED_BIT);
        } else if (id == WIFI_EVENT_STA_CONNECTED) {
            wifi_event_sta_connected_t *conn = (wifi_event_sta_connected_t *)event_data;
            ESP_LOGI(TAG,
                     "Wi-Fi connected to SSID=%.*s channel=%d authmode=%d",
                     conn ? conn->ssid_len : 0,
                     conn ? (const char *)conn->ssid : "",
                     conn ? conn->channel : -1,
                     conn ? conn->authmode : -1);
        } else if (id == WIFI_EVENT_STA_DISCONNECTED) {
            wifi_event_sta_disconnected_t *disc = (wifi_event_sta_disconnected_t *)event_data;
            ESP_LOGW(TAG,
                     "Wi-Fi disconnected, reason=%d (%s). Reconnecting...",
                     disc ? disc->reason : -1,
                     disc ? wifi_disc_reason_to_str(disc->reason) : "UNKNOWN");
            esp_wifi_connect();
            xEventGroupClearBits(s_event_group, WIFI_CONNECTED_BIT);
        }
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_event_group, WIFI_CONNECTED_BIT);
    }
}

static void initialise_wifi(void) {
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = EXAMPLE_WIFI_SSID,
            .password = EXAMPLE_WIFI_PASS,
            .threshold.authmode = WIFI_AUTH_OPEN,
            .pmf_cfg = {
                .capable = true,
                .required = false,
            },
        },
    };

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(
        esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_LOGI(TAG,
             "Connecting to Wi-Fi SSID: %s (password_len=%u)",
             EXAMPLE_WIFI_SSID,
             (unsigned int)strlen(EXAMPLE_WIFI_PASS));
    if (strlen(EXAMPLE_WIFI_PASS) > 0 && strlen(EXAMPLE_WIFI_PASS) < 8) {
        ESP_LOGW(TAG, "Wi-Fi password length looks too short for WPA/WPA2");
    }
    ESP_ERROR_CHECK(esp_wifi_start());
}

static bool enqueue_publish_event(const slot_state_event_t *evt) {
    if (xQueueSend(s_publish_queue, evt, pdMS_TO_TICKS(QUEUE_SEND_TIMEOUT_MS)) == pdTRUE) {
        return true;
    }
    ESP_LOGW(TAG, "Publish queue full, dropping slot event for slot=%u", (unsigned int)evt->slot);
    return false;
}

static void sensor_emit_slot_change(uint8_t slot_idx, int stable_level) {
    bool in_holder = level_to_in_holder(stable_level);

    s_last_stable_levels[slot_idx] = stable_level;
    s_pending_active[slot_idx] = false;

    if (!in_holder && led_get(slot_idx)) {
        led_set(slot_idx, false);
    }

    slot_state_event_t evt = {
        .slot = (uint8_t)(slot_idx + 1),
        .in_holder = in_holder,
    };

    ESP_LOGI(TAG, "Slot %u %s", (unsigned int)evt.slot, evt.in_holder ? "IN HOLDER" : "REMOVED");
    enqueue_publish_event(&evt);
}

static void sensor_sample_slot(uint8_t slot_idx, int level, uint64_t now_ms) {
    if (level == s_last_stable_levels[slot_idx]) {
        s_pending_active[slot_idx] = false;
        return;
    }

    if (!s_pending_active[slot_idx] || s_pending_levels[slot_idx] != level) {
        s_pending_active[slot_idx] = true;
        s_pending_levels[slot_idx] = level;
        s_pending_since_ms[slot_idx] = now_ms;
        return;
    }

    if ((now_ms - s_pending_since_ms[slot_idx]) >= (uint64_t)CONFIG_PILL_SENSOR_DEBOUNCE_MS) {
        sensor_emit_slot_change(slot_idx, level);
    }
}

static void sensor_task(void *param) {
    sensor_irq_event_t irq_evt;
    int i;

    IOT_UNUSED(param);

    while (1) {
        if (xQueueReceive(s_sensor_irq_queue, &irq_evt, pdMS_TO_TICKS(SENSOR_QUEUE_WAIT_MS)) == pdTRUE) {
            IOT_UNUSED(irq_evt);
        }

        uint64_t now_ms = (uint64_t)(esp_timer_get_time() / 1000);
        for (i = 0; i < SLOT_COUNT; i++) {
            int level = gpio_get_level(s_switch_gpios[i]);
            sensor_sample_slot((uint8_t)i, level, now_ms);
        }
    }
}

static IoT_Error_t publish_slot_event(const slot_state_event_t *evt) {
    char payload[MQTT_EVENT_PAYLOAD_BUF_LEN];
    IoT_Publish_Message_Params paramsQOS1 = {0};

    int len = snprintf(payload,
                       sizeof(payload),
                       "{\"event_type\":\"slot_state_changed\",\"slot\":%u,\"in_holder\":%s}",
                       (unsigned int)evt->slot,
                       evt->in_holder ? "true" : "false");
    if (len <= 0 || len >= (int)sizeof(payload)) {
        return FAILURE;
    }

    paramsQOS1.qos = QOS1;
    paramsQOS1.payload = payload;
    paramsQOS1.payloadLen = (size_t)len;
    paramsQOS1.isRetained = 0;

    return aws_iot_mqtt_publish(&s_mqtt_client, s_event_topic, (uint16_t)strlen(s_event_topic), &paramsQOS1);
}

static void publisher_task(void *param) {
    slot_state_event_t evt;

    IOT_UNUSED(param);

    while (1) {
        if (xQueueReceive(s_publish_queue, &evt, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        xEventGroupWaitBits(s_event_group, MQTT_READY_BIT, false, true, portMAX_DELAY);

        if (!mqtt_lock(pdMS_TO_TICKS(MQTT_MUTEX_TIMEOUT_MS))) {
            ESP_LOGW(TAG, "MQTT lock timeout, dropping publish (mqtt_task likely busy in yield/connect)");
            continue;
        }

        IoT_Error_t rc = publish_slot_event(&evt);
        mqtt_unlock();

        if (rc == MQTT_REQUEST_TIMEOUT_ERROR) {
            ESP_LOGW(TAG, "QOS1 publish ACK timeout for slot=%u", (unsigned int)evt.slot);
            continue;
        }
        if (rc != SUCCESS) {
            ESP_LOGW(TAG, "Publish failed rc=%d; waiting for reconnect", rc);
            xEventGroupClearBits(s_event_group, MQTT_READY_BIT);
            vTaskDelay(pdMS_TO_TICKS(MQTT_PUBLISH_FAIL_DELAY_MS));
            continue;
        }

        ESP_LOGI(TAG, "Event sent: slot=%u in_holder=%s", (unsigned int)evt.slot, evt.in_holder ? "true" : "false");
    }
}

static void mqtt_task(void *param) {
    IoT_Error_t rc = FAILURE;

    IOT_UNUSED(param);

    ESP_LOGI(TAG, "AWS IoT SDK %d.%d.%d-%s", VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_TAG);
    build_topics();

    while (1) {
        xEventGroupWaitBits(s_event_group, WIFI_CONNECTED_BIT, false, true, portMAX_DELAY);

        if (!mqtt_lock(pdMS_TO_TICKS(MQTT_MUTEX_TIMEOUT_MS))) {
            vTaskDelay(pdMS_TO_TICKS(MQTT_LOOP_LOCK_RETRY_DELAY_MS));
            continue;
        }

        if (!s_mqtt_initialized) {
            rc = mqtt_init_once();
            if (rc != SUCCESS) {
                mqtt_unlock();
                ESP_LOGE(TAG, "aws_iot_mqtt_init failed rc=%d", rc);
                vTaskDelay(pdMS_TO_TICKS(MQTT_INIT_RETRY_DELAY_MS));
                continue;
            }
        }

        if ((xEventGroupGetBits(s_event_group) & MQTT_READY_BIT) == 0) {
            rc = mqtt_connect_client();
            if (rc == SUCCESS) {
                rc = mqtt_subscribe_command_topic();
            }

            if (rc == SUCCESS) {
                xEventGroupSetBits(s_event_group, MQTT_READY_BIT);
                ESP_LOGI(TAG, "MQTT connected and subscribed to %s", s_cmd_topic);

#if ENABLE_STARTUP_SLOT_STATE_PUBLISH
                if (!s_startup_slot_state_published) {
                    IoT_Error_t snap_rc = publish_startup_slot_states_locked();
                    if (snap_rc == SUCCESS) {
                        s_startup_slot_state_published = true;
                        ESP_LOGI(TAG, "Startup slot-state publish complete");
                    } else {
                        ESP_LOGW(TAG, "Startup slot-state publish failed rc=%d", snap_rc);
                    }
                }
#endif
            } else {
                mqtt_unlock();
                ESP_LOGE(TAG, "MQTT connect/subscribe failed rc=%d (%s)", rc, iot_error_to_str(rc));
                if (rc == NETWORK_SSL_READ_ERROR) {
                    ESP_LOGE(TAG,
                             "TLS read failed. Most common causes: cert/private-key mismatch, inactive/unattached AWS "
                             "IoT certificate, or endpoint/certificate account mismatch.");
                }
                vTaskDelay(pdMS_TO_TICKS(MQTT_CONNECT_RETRY_DELAY_MS));
                continue;
            }
        }

        rc = aws_iot_mqtt_yield(&s_mqtt_client, MQTT_YIELD_TIMEOUT_MS);
        mqtt_unlock();

        if (rc == NETWORK_ATTEMPTING_RECONNECT) {
            ESP_LOGW(TAG, "MQTT reconnect in progress...");
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }
        if (rc == NETWORK_RECONNECTED) {
            ESP_LOGI(TAG, "MQTT reconnected, re-subscribing...");
            if (mqtt_lock(pdMS_TO_TICKS(MQTT_MUTEX_TIMEOUT_MS))) {
                IoT_Error_t sub_rc = mqtt_subscribe_command_topic();
                mqtt_unlock();
                if (sub_rc != SUCCESS) {
                    ESP_LOGW(TAG, "Re-subscribe failed rc=%d", sub_rc);
                    xEventGroupClearBits(s_event_group, MQTT_READY_BIT);
                } else {
                    xEventGroupSetBits(s_event_group, MQTT_READY_BIT);
                }
            }
            continue;
        }
        if (rc != SUCCESS) {
            ESP_LOGW(TAG, "mqtt_yield rc=%d", rc);
            xEventGroupClearBits(s_event_group, MQTT_READY_BIT);
            vTaskDelay(pdMS_TO_TICKS(MQTT_YIELD_FAIL_DELAY_MS));
            continue;
        }

        /* Give publisher_task a chance to acquire the MQTT mutex and flush queued events. */
        vTaskDelay(pdMS_TO_TICKS(MQTT_LOOP_BACKOFF_MS));
    }
}

void app_main(void) {
    esp_err_t err;

    err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    ESP_LOGI(TAG, "Booting PillBuddy firmware");
    ESP_LOGI(TAG, "Device ID: %s", CONFIG_PILL_DEVICE_ID);
    ESP_LOGI(TAG, "Switch GPIOs: [%d, %d, %d]",
             CONFIG_PILL_SLOT1_SW_GPIO,
             CONFIG_PILL_SLOT2_SW_GPIO,
             CONFIG_PILL_SLOT3_SW_GPIO);
    ESP_LOGI(TAG, "LED GPIOs: [%d, %d, %d]",
             CONFIG_PILL_SLOT1_LED_GPIO,
             CONFIG_PILL_SLOT2_LED_GPIO,
             CONFIG_PILL_SLOT3_LED_GPIO);
    ESP_LOGI(TAG, "Debounce: %d ms", CONFIG_PILL_SENSOR_DEBOUNCE_MS);

    if (!validate_gpio_config()) {
        ESP_LOGE(TAG, "GPIO configuration invalid; fix sdkconfig slot pin assignments");
        abort();
    }

    s_event_group = xEventGroupCreate();
    s_sensor_irq_queue = xQueueCreate(SENSOR_IRQ_QUEUE_LEN, sizeof(sensor_irq_event_t));
    s_publish_queue = xQueueCreate(PUBLISH_QUEUE_LEN, sizeof(slot_state_event_t));
    s_mqtt_mutex = xSemaphoreCreateMutex();

    if (s_event_group == NULL || s_sensor_irq_queue == NULL || s_publish_queue == NULL || s_mqtt_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to allocate RTOS primitives");
        abort();
    }

    init_leds();
    init_switches();
    initialise_wifi();

    xTaskCreatePinnedToCore(&sensor_task, "sensor_task", SENSOR_TASK_STACK, NULL, SENSOR_TASK_PRIO, NULL, TASK_CORE_ID);
    xTaskCreatePinnedToCore(
        &publisher_task, "publisher_task", PUBLISHER_TASK_STACK, NULL, PUBLISHER_TASK_PRIO, NULL, TASK_CORE_ID);
    xTaskCreatePinnedToCore(&mqtt_task, "mqtt_task", MQTT_TASK_STACK, NULL, MQTT_TASK_PRIO, NULL, TASK_CORE_ID);
}
