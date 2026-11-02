/*
 * ==============================================================================
 * Smart Classroom Environmental Monitoring System
 * ESP32 + DHT22 + Multi-LED Indicator -> Live Render Cloud Dashboard
 * ==============================================================================
 * Live Dashboard: https://airquality-monitoring.onrender.com/
 * Target Endpoint: https://airquality-monitoring.onrender.com/api/readings
 *
 * Hardware Wiring:
 *   DHT22 DATA (Pin 2)  --> ESP32 GPIO 4 (with 10k pull-up to 3.3V)
 *   DHT22 VCC  (Pin 1)  --> ESP32 3V3 (or VIN 5V)
 *   DHT22 GND  (Pin 4)  --> ESP32 GND
 *
 *   Green LED  (+)      --> ESP32 GPIO 16 (via 220Ω resistor)
 *   Yellow LED (+)      --> ESP32 GPIO 17 (via 220Ω resistor)
 *   Red LED    (+)      --> ESP32 GPIO 18 (via 220Ω resistor)
 *   LED Cathodes (-)    --> ESP32 GND
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "DHT.h"

// ==============================================================================
// 1. Wi-Fi Configuration
// ==============================================================================
// Replace with your 2.4 GHz Wi-Fi credentials (ESP32 does not support 5 GHz Wi-Fi)
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ==============================================================================
// 2. Cloud Dashboard Endpoint
// ==============================================================================
const char* SERVER_URL    = "https://airquality-monitoring.onrender.com/api/readings";
const char* DEVICE_ID     = "esp32-classroom-01";

// ==============================================================================
// 3. Hardware Pin Definitions & Sensor Setup
// ==============================================================================
#define DHTPIN 4
#define DHTTYPE DHT22

// LED GPIO pins
#define GREEN_LED 16
#define YELLOW_LED 17
#define RED_LED 18

// Temperature thresholds (°C)
#define NORMAL_TEMP 25.0
#define HIGH_TEMP 30.0

DHT dht(DHTPIN, DHTTYPE);

// Non-blocking timer variables
const unsigned long TELEMETRY_INTERVAL_MS = 5000; // Transmit every 5 seconds
unsigned long lastTelemetryTime = 0;

const unsigned long WIFI_CHECK_INTERVAL_MS = 5000;
unsigned long lastWiFiCheckTime = 0;

// ==============================================================================
// LED Control Helper
// ==============================================================================
void setLEDs(bool green, bool yellow, bool red) {
  digitalWrite(GREEN_LED, green ? HIGH : LOW);
  digitalWrite(YELLOW_LED, yellow ? HIGH : LOW);
  digitalWrite(RED_LED, red ? HIGH : LOW);
}

// ==============================================================================
// Wi-Fi Connection Routine
// ==============================================================================
void connectToWiFi() {
  Serial.println();
  Serial.println("==================================================");
  Serial.print("[WiFi] Connecting to network: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("[WiFi] Connected successfully!");
    Serial.print("[WiFi] ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WiFi] Signal Strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println();
    Serial.println("[WiFi Alert] Connection failed. Will retry in background...");
  }
  Serial.println("==================================================");
}

// ==============================================================================
// Telemetry HTTPS POST Transmission
// ==============================================================================
void sendTelemetry(float temperature, float humidity) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Cannot send: ESP32 is not connected to Wi-Fi.");
    return;
  }

  // Build JSON payload
  char jsonPayload[128];
  snprintf(jsonPayload, sizeof(jsonPayload),
           "{\"temperature\": %.2f, \"humidity\": %.2f, \"device_id\": \"%s\"}",
           temperature, humidity, DEVICE_ID);

  Serial.print("[HTTP POST] Payload: ");
  Serial.println(jsonPayload);

  // Use WiFiClientSecure for HTTPS connection to Render
  WiFiClientSecure client;
  client.setInsecure(); // Bypass CA certificate check on embedded device

  HTTPClient http;
  if (http.begin(client, SERVER_URL)) {
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000); // 10-second timeout

    int httpCode = http.POST(jsonPayload);

    if (httpCode > 0) {
      String response = http.getString();
      if (httpCode == 201 || httpCode == 200) {
        Serial.printf("[HTTP %d Success] Dashboard Updated: %s\n", httpCode, response.c_str());
      } else {
        Serial.printf("[HTTP %d Warning] Server response: %s\n", httpCode, response.c_str());
      }
    } else {
      Serial.printf("[HTTP Error] Connection failed: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
  } else {
    Serial.println("[HTTP Error] Unable to connect to host.");
  }
}

// ==============================================================================
// Arduino Setup
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000); // Allow UART to stabilize

  // Initialize DHT22
  dht.begin();

  // Initialize LEDs
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  // Turn OFF all LEDs initially
  setLEDs(false, false, false);

  Serial.println();
  Serial.println("==================================================");
  Serial.println(" Smart Classroom Environmental Monitoring System  ");
  Serial.println(" Target: https://airquality-monitoring.onrender.com");
  Serial.println("==================================================");

  // Connect to Wi-Fi
  connectToWiFi();
}

// ==============================================================================
// Arduino Loop
// ==============================================================================
void loop() {
  unsigned long currentMillis = millis();

  // 1. Maintain Wi-Fi connection
  if (currentMillis - lastWiFiCheckTime >= WIFI_CHECK_INTERVAL_MS) {
    lastWiFiCheckTime = currentMillis;
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WiFi Alert] Reconnecting to Wi-Fi...");
      WiFi.reconnect();
    }
  }

  // 2. Read sensor and transmit telemetry periodically (every 5 seconds)
  if (currentMillis - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = currentMillis;

    // Read temperature and humidity
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    // Check sensor readings
    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("[Sensor Alert] Failed to read from DHT22 sensor!");
      setLEDs(false, false, false);
      return;
    }

    // Display sensor readings locally
    Serial.println("----------------------------------");
    Serial.printf("Temperature: %.2f °C | Humidity: %.2f %%\n", temperature, humidity);

    // Temperature-based LED indication
    if (temperature < NORMAL_TEMP) {
      setLEDs(true, false, false);
      Serial.println("Status: NORMAL - Green LED ON (GPIO 16)");
    } else if (temperature <= HIGH_TEMP) {
      setLEDs(false, true, false);
      Serial.println("Status: WARNING - Yellow LED ON (GPIO 17)");
    } else {
      setLEDs(false, false, true);
      Serial.println("Status: HIGH - Red LED ON (GPIO 18)");
    }

    // Transmit reading to live Render cloud dashboard
    sendTelemetry(temperature, humidity);

    Serial.println("----------------------------------");
  }
}
