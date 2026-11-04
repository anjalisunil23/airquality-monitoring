/*
 * ==============================================================================
 * Smart Classroom Environmental Monitoring System
 * ESP32 + DHT22 + Dual Bulb Control (White & Red) -> Live Render Cloud Dashboard
 * ==============================================================================
 * Dashboard : https://airquality-monitoring.onrender.com/
 * Endpoint  : https://airquality-monitoring.onrender.com/api/readings
 *
 * Hardware Wiring:
 *   DHT22 DATA (Pin 2)  --> ESP32 GPIO 4 (with 10k resistor to 3.3V)
 *   DHT22 VCC  (Pin 1)  --> ESP32 3V3
 *   DHT22 GND  (Pin 4)  --> ESP32 GND
 *
 *   White Bulb/LED (+)  --> ESP32 GPIO 17 (via 220Ω resistor or relay)
 *   Red Bulb/LED (+)    --> ESP32 GPIO 18 (via 220Ω resistor or relay)
 *   Bulb/LED Cathodes(-)-> ESP32 GND
 * ==============================================================================
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "DHT.h"

// ==============================================================================
// 1. Wi-Fi Configuration
// ==============================================================================
const char* WIFI_SSID     = "Anjali";     // Wi-Fi or Hotspot Name (2.4 GHz)
const char* WIFI_PASSWORD = "12345678";   // Wi-Fi Password

// ==============================================================================
// 2. Cloud Server Endpoint
// ==============================================================================
const char* SERVER_URL    = "https://airquality-monitoring.onrender.com/api/readings";
const char* DEVICE_ID     = "esp32-classroom-01";

// ==============================================================================
// 3. Hardware Pin Definitions
// ==============================================================================
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define WHITE_LED 17  // White Bulb (GPIO 17)
#define RED_LED   18  // Red Bulb (GPIO 18)

// Temperature Threshold (°C)
#define COMFORTABLE_TEMP 25.0

// ==============================================================================
// 4. Timing Variables
// ==============================================================================
const unsigned long SENSOR_INTERVAL = 2500; // Read sensor every 2.5s
const unsigned long UPLOAD_INTERVAL = 5000; // Upload telemetry every 5s

unsigned long lastSensorRead = 0;
unsigned long lastUpload     = 0;
unsigned long lastWiFiCheck  = 0;

float temperature = 0.0;
float humidity    = 0.0;
bool hasValidReading = false;

// ==============================================================================
// 5. Bulb / LED Control Logic
// ==============================================================================
void updateBulbs(float temp) {
  if (temp < COMFORTABLE_TEMP) {
    // Below 25.0°C: Comfortable -> White Bulb ON, Red Bulb OFF
    digitalWrite(WHITE_LED, HIGH);
    digitalWrite(RED_LED, LOW);
    Serial.printf("[BULB] Temp: %.2f °C | Status: COMFORTABLE (< 25°C) -> WHITE BULB ON\n", temp);
  } else {
    // 25.0°C and above: Warm / Alert -> Red Bulb ON, White Bulb OFF
    digitalWrite(WHITE_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    Serial.printf("[BULB] Temp: %.2f °C | Status: WARM / ALERT (>= 25°C) -> RED BULB ON\n", temp);
  }
}

// ==============================================================================
// 6. Connect to Wi-Fi (With Full Reset & Diagnostics)
// ==============================================================================
void connectWiFi() {
  Serial.println("\nConnecting to Wi-Fi...");
  Serial.printf("SSID: [%s]  Password Length: %d\n", WIFI_SSID, strlen(WIFI_PASSWORD));

  WiFi.disconnect(true, true); // Full radio reset + clear stored credentials
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Give hotspot up to 20 seconds (40 x 500ms)
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n==================================");
    Serial.println("  WI-FI CONNECTED SUCCESSFULLY!   ");
    Serial.println("==================================");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
    Serial.printf("Signal (RSSI): %d dBm\n\n", WiFi.RSSI());
  } else {
    // Print the actual WiFi status code to help diagnose
    Serial.printf("\n[!] Wi-Fi FAILED. Status code: %d\n", WiFi.status());
    Serial.println("    Codes: 1=NoSSID, 2=ScanCompleted, 3=Connected,");
    Serial.println("           4=ConnectFailed, 5=ConnLost, 6=Disconnected");
    Serial.println("    Check: hotspot ON? 2.4GHz? SSID/password correct?");
  }
}

// ==============================================================================
// 7. Read DHT22 Sensor
// ==============================================================================
void readSensor() {
  float newHum  = dht.readHumidity();
  float newTemp = dht.readTemperature();

  if (isnan(newHum) || isnan(newTemp)) {
    Serial.println("[Sensor Alert] Failed to read from DHT22!");
    return;
  }

  temperature = newTemp;
  humidity    = newHum;
  hasValidReading = true;

  Serial.println("---------------------------------------");
  Serial.printf("Sensor Reading: %.2f °C | Humidity: %.2f %%\n", temperature, humidity);
  updateBulbs(temperature);
}

// ==============================================================================
// 8. Upload Telemetry to Live Cloud Dashboard
// ==============================================================================
void uploadData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Upload] Skipped: Waiting for Wi-Fi...");
    return;
  }

  if (!hasValidReading) {
    Serial.println("[Upload] Skipped: Waiting for first valid sensor reading...");
    return;
  }

  WiFiClientSecure client;
  client.setInsecure(); // Required for Render HTTPS connection

  HTTPClient http;
  http.setTimeout(10000);

  if (http.begin(client, SERVER_URL)) {
    http.addHeader("Content-Type", "application/json");

    char payload[128];
    snprintf(payload, sizeof(payload),
             "{\"temperature\": %.2f, \"humidity\": %.2f, \"device_id\": \"%s\"}",
             temperature, humidity, DEVICE_ID);

    Serial.printf("[HTTP POST] Uploading: %s\n", payload);
    int httpCode = http.POST(payload);

    if (httpCode == 200 || httpCode == 201) {
      Serial.println("[SUCCESS 201] Live Dashboard Updated Successfully!");
    } else {
      Serial.printf("[HTTP %d] Server Response: %s\n", httpCode, http.getString().c_str());
    }
    http.end();
  } else {
    Serial.println("[HTTP Error] Unable to connect to Render host.");
  }
  Serial.println("---------------------------------------");
}

// ==============================================================================
// 9. Setup
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n======================================");
  Serial.println(" SMART CLASSROOM ENVIRONMENTAL MONITOR");
  Serial.println(" Target: airquality-monitoring.onrender.com");
  Serial.println("======================================");

  // Initialize Bulb Pins
  pinMode(WHITE_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  // Quick Self-Test: Flash White then Red
  digitalWrite(WHITE_LED, HIGH); delay(400); digitalWrite(WHITE_LED, LOW);
  digitalWrite(RED_LED, HIGH);   delay(400); digitalWrite(RED_LED, LOW);

  // Initialize Sensor
  dht.begin();
  delay(1000);

  // Connect to Wi-Fi
  connectWiFi();

  Serial.println("System Initialized.\n");
}

// ==========================================
// 10. Main Loop
// ==========================================
void loop() {
  unsigned long currentMillis = millis();

  // Reconnect Wi-Fi every 10 seconds if disconnected (full reset)
  if (currentMillis - lastWiFiCheck >= 10000) {
    lastWiFiCheck = currentMillis;
    if (WiFi.status() != WL_CONNECTED) {
      Serial.printf("[WiFi] Disconnected (status %d). Reconnecting...\n", WiFi.status());
      WiFi.disconnect();
      delay(500);
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
  }

  // Read DHT22 every 2.5 seconds
  if (currentMillis - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = currentMillis;
    readSensor();
  }

  // Upload to Render every 5 seconds
  if (currentMillis - lastUpload >= UPLOAD_INTERVAL) {
    lastUpload = currentMillis;
    uploadData();
  }

  delay(50);
}
