/*
 * ==============================================================================
 * Smart Classroom Environmental Monitoring System
 * Production Firmware: ESP32 + DHT22 -> FastAPI Backend
 * ==============================================================================
 * Academic Context: MCA Internet of Things Assignment
 * Hardware Platform: ESP32 Dev Module (COM5, Arduino IDE 2.3.10)
 * Sensor: DHT22 / AM2302 (Digital Temperature & Relative Humidity)
 *
 * Pin Connections:
 *   DHT22 Pin 1 (VCC)  --> ESP32 3V3 (or 5V VIN)
 *   DHT22 Pin 2 (DATA) --> ESP32 GPIO 4 (G4) [with 10kΩ pull-up to 3.3V recommended]
 *   DHT22 Pin 3 (NC)   --> Not connected / Leave empty
 *   DHT22 Pin 4 (GND)  --> ESP32 GND
 *
 * Required Libraries in Arduino IDE:
 *   1. WiFi (built into the ESP32 Board Package)
 *   2. HTTPClient (built into the ESP32 Board Package)
 *   3. "DHT sensor library" by Adafruit (via Library Manager: Sketch -> Include Library -> Manage Libraries)
 *      Note: This sketch formats standard JSON natively via snprintf; no external ArduinoJson library is required!
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

// ==============================================================================
// 1. Wi-Fi Configuration
// ==============================================================================
// Replace these placeholders with your Wi-Fi network credentials (2.4 GHz required by ESP32)
const char* WIFI_SSID     = "YOUR_WIFI_SSID";         // Enter your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";     // Enter your Wi-Fi password

// ==============================================================================
// 2. Server Address Configuration
// ==============================================================================
// IMPORTANT: Do NOT use "localhost" or "127.0.0.1". Microcontrollers cannot resolve localhost!
// Use your Windows laptop's LAN IPv4 address discovered via `ipconfig`.
// Example: If your laptop is 192.168.44.93 and FastAPI runs on port 8000:
const char* SERVER_URL    = "http://192.168.44.93:8000/api/readings";

// Device identifier registered in database
const char* DEVICE_ID     = "esp32-classroom-01";

// Transmission interval in milliseconds (5 seconds as per MCA project specification)
const unsigned long TELEMETRY_INTERVAL_MS = 5000;

// ==============================================================================
// 3. Hardware Pin Definitions
// ==============================================================================
#define DHTPIN 4              // ESP32 GPIO 4 connected to DHT22 DATA pin
#define DHTTYPE DHT22         // DHT 22 (AM2302) sensor type

#ifndef LED_BUILTIN
  #define LED_BUILTIN 2       // Onboard blue status LED on most ESP32 DevKit boards
#endif

// Instantiate DHT sensor
DHT dht(DHTPIN, DHTTYPE);

// Non-blocking timer variables
unsigned long lastTelemetryTime = 0;
unsigned long lastWiFiCheckTime = 0;
const unsigned long WIFI_CHECK_INTERVAL_MS = 3000;

// ==============================================================================
// Wi-Fi Connection Helper
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

  int attempt = 0;
  while (WiFi.status() != WL_CONNECTED && attempt < 25) {
    delay(400);
    Serial.print(".");
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); // Blink LED while connecting
    attempt++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.println();
    Serial.println("[WiFi] Connected successfully!");
    Serial.print("[WiFi] ESP32 Assigned IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WiFi] Signal Strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.println("==================================================");
  } else {
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println();
    Serial.println("[WiFi Error] Could not connect to Wi-Fi. Check SSID/Password.");
    Serial.println("[WiFi] Will automatically retry in background...");
    Serial.println("==================================================");
  }
}

// ==============================================================================
// Arduino Setup Function
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000); // Allow UART to stabilize

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.println();
  Serial.println("==================================================");
  Serial.println(" Smart Classroom Environmental Monitor - ESP32    ");
  Serial.println(" MCU: ESP32 Dev Module | Sensor: DHT22 on GPIO 4  ");
  Serial.println(" Target Backend: " + String(SERVER_URL));
  Serial.println("==================================================");

  // Initialize DHT22 sensor
  dht.begin();
  Serial.println("[Hardware] DHT22 sensor initialized on GPIO 4.");

  // Connect to Wi-Fi
  connectToWiFi();
}

// ==============================================================================
// Arduino Main Execution Loop
// ==============================================================================
void loop() {
  unsigned long currentMillis = millis();

  // 1. Maintain Wi-Fi Connection without blocking telemetry
  if (currentMillis - lastWiFiCheckTime >= WIFI_CHECK_INTERVAL_MS) {
    lastWiFiCheckTime = currentMillis;
    if (WiFi.status() != WL_CONNECTED) {
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("[WiFi Alert] Wi-Fi lost. Attempting reconnection...");
      WiFi.reconnect();
    }
  }

  // 2. Telemetry Interval Check (Every 5 seconds)
  if (currentMillis - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = currentMillis;

    // Read physical DHT22 telemetry
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature(); // Temperature in Celsius

    // Validate sensor readings: check if reading failed or is NaN
    if (isnan(humidity) || isnan(temperature)) {
      Serial.println("[Sensor Error] Failed to read from DHT22! Check 3.3V power, GND, and GPIO 4 wiring.");
      return; // Do NOT transmit invalid/corrupt values to backend
    }

    // Verify readings are within physical sensor operating limits
    if (temperature < -40.0 || temperature > 80.0 || humidity < 0.0 || humidity > 100.0) {
      Serial.printf("[Sensor Warning] Out-of-range reading ignored: Temp=%.2f°C, Hum=%.2f%%\n", temperature, humidity);
      return;
    }

    // Print reading locally to Serial Monitor
    Serial.println("--------------------------------------------------");
    Serial.printf("[Sensor Reading] Temperature: %.2f °C | Humidity: %.2f %%\n", temperature, humidity);

    // If Wi-Fi is not connected, log and skip transmission
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[HTTP Warning] Cannot send: ESP32 is not connected to Wi-Fi.");
      return;
    }

    // Construct valid JSON string natively (zero external library dependency)
    char jsonPayload[128];
    snprintf(jsonPayload, sizeof(jsonPayload),
             "{\"temperature\": %.2f, \"humidity\": %.2f, \"device_id\": \"%s\"}",
             temperature, humidity, DEVICE_ID);

    Serial.printf("[HTTP POST] Transmitting payload: %s\n", jsonPayload);

    // Initialize HTTPClient
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(4000); // 4-second timeout to prevent stalling

    // Send HTTP POST request
    int httpResponseCode = http.POST(jsonPayload);

    // Evaluate HTTP response code
    if (httpResponseCode > 0) {
      String responseBody = http.getString();
      if (httpResponseCode == 201 || httpResponseCode == 200) {
        Serial.printf("[HTTP Success %d] Stored in database: %s\n", httpResponseCode, responseBody.c_str());

        // Visual LED feedback: quick pulse on successful transmission
        digitalWrite(LED_BUILTIN, LOW);
        delay(60);
        digitalWrite(LED_BUILTIN, HIGH);
      } else {
        Serial.printf("[HTTP Warning %d] Server responded with: %s\n", httpResponseCode, responseBody.c_str());
      }
    } else {
      Serial.printf("[HTTP Error] Failed to connect to server. Error: %s\n", http.errorToString(httpResponseCode).c_str());
      Serial.println("             Tips: Check that FastAPI is running on host 0.0.0.0, port 8000, and Windows Firewall permits inbound TCP 8000.");
    }

    // Free HTTP client resources
    http.end();
  }
}
