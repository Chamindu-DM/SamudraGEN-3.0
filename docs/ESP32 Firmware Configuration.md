# ESP32 Firmware Configuration Guide

> **Note:** This guide is written for configuring the ESP32 to send ocean wave telemetry data to AWS IoT Core. It assumes you will be uploading code to the ESP32 using the Arduino IDE.

## 1. Prerequisites

Before writing the code, ensure you have the following installed in your Arduino IDE:

1.  **ESP32 Board Support:** Installed via the Boards Manager.
2.  **Required Libraries:** (Install these via `Sketch` -> `Include Library` -> `Manage Libraries`)
    *   `PubSubClient` by Nick O'Leary (for MQTT communication)
    *   `NTPClient` by Fabrice Weinberg (optional, but highly recommended for getting accurate timestamps from the internet)

## 2. Handling the AWS Certificates

AWS IoT requires the ESP32 to authenticate using the certificates provided. You should have received 3 certificate files.

There are two ways to include them. We **highly recommend Option A** for its simplicity.

### Option A: Hardcode in the sketch (Easiest & Recommended)
Create a new tab in your Arduino IDE, name it `secrets.h`, and paste the certificates as raw strings. *Make sure to copy the entire contents of the files, including the `-----BEGIN...` and `-----END...` lines!*

```cpp
// secrets.h
#include <pgmspace.h>

const char WIFI_SSID[] = "YOUR_WIFI_NETWORK_NAME";
const char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";

// 1. Amazon Root CA 1 (AmazonRootCA1.pem)
static const char AWS_CERT_CA[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
... paste the contents of AmazonRootCA1.pem here ...
-----END CERTIFICATE-----
)EOF";

// 2. Device Certificate (xxx-certificate.pem.crt)
static const char AWS_CERT_CRT[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
... paste the contents of the .crt file here ...
-----END CERTIFICATE-----
)EOF";

// 3. Device Private Key (xxx-private.pem.key)
static const char AWS_CERT_PRIVATE[] PROGMEM = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
... paste the contents of the private .key file here ...
-----END RSA PRIVATE KEY-----
)EOF";
```

### Option B: Upload to SPIFFS/LittleFS (Advanced)
If you prefer not to hardcode them, you can upload the `.pem` and `.crt` files directly to the ESP32's internal flash memory using the "ESP32 Sketch Data Upload" tool in the Arduino IDE. If you do this, your code will need to include the `SPIFFS.h` or `LittleFS.h` library to read these files during the setup phase.

---

## 3. Configuration Variables

In your main `.ino` file, you need to define the AWS connection details. (Make sure to replace the endpoint with the actual endpoint from AWS, you might need to ask for this if you don't have it).

```cpp
#include "secrets.h"
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// ── AWS IoT Configuration ──────────────────────────────
// REPLACE THIS with the actual endpoint URL
const char* AWS_IOT_ENDPOINT = "a1b2c3d4e5f6g7-ats.iot.ap-south-1.amazonaws.com"; 
const int   AWS_IOT_PORT     = 8883;        // MQTT over TLS (Secure port)
const char* MQTT_TOPIC       = "ocean/wave/telemetry";
const char* CLIENT_ID        = "SamudraGEN-ESP32";

// Publish interval (Keep ≥ 5 seconds to stay within the AWS Free Tier limits!)
const unsigned long PUBLISH_INTERVAL_MS = 5000;
```

---

## 4. Connecting and Publishing Data

Here is a simplified outline of how to connect to Wi-Fi, authenticate with AWS, and publish the sensor data.

### Connecting to AWS IoT
```cpp
WiFiClientSecure net = WiFiClientSecure();
PubSubClient mqttClient(net);

void connectAWS() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.println("Connecting to Wi-Fi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Connected!");

  // Configure WiFiClientSecure to use the AWS IoT certificates
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  // Connect to the MQTT broker on the AWS endpoint
  mqttClient.setServer(AWS_IOT_ENDPOINT, AWS_IOT_PORT);

  Serial.println("Connecting to AWS IOT...");
  while (!mqttClient.connect(CLIENT_ID)) {
    Serial.print(".");
    delay(100);
  }

  if (!mqttClient.connected()) {
    Serial.println("\nAWS IoT Timeout!");
    return;
  }
  Serial.println("\nAWS IoT Connected!");
}

void setup() {
  Serial.begin(115200);
  connectAWS();
  
  // (Initialize your physical sensors here)
}
```

### Formatting and Publishing the Data

You need to send a JSON payload exactly like this structure:
```json
{
  "ts": "10:30:12",
  "waveHeight": 1.55,
  "waveFreq": 0.25,
  "rpm": 120,
  "power": 24.0,
  "voltage": 24.1,
  "current": 1.0
}
```

Inside your `loop()`, you can construct this string and publish it every `PUBLISH_INTERVAL_MS`:

```cpp
unsigned long lastPublish = 0;

void loop() {
  mqttClient.loop();

  // Check if it's time to publish (every 5 seconds)
  if (millis() - lastPublish > PUBLISH_INTERVAL_MS) {
    
    // 1. Collect your actual sensor readings here!
    // (Replace these dummy values with variables from your sensor code)
    float waveHeight = 1.55; 
    float waveFreq = 0.25;
    int rpm = 120;
    float power = 24.0;
    float voltage = 24.1;
    float current = 1.0;
    
    // Get the current time string (e.g., using an NTP library or RTC)
    // For this example, we use a placeholder string.
    String timeString = "10:30:12"; 

    // 2. Build the JSON string payload
    String payload = "{";
    payload += "\"ts\":\"" + timeString + "\",";
    payload += "\"waveHeight\":" + String(waveHeight, 2) + ",";
    payload += "\"waveFreq\":" + String(waveFreq, 2) + ",";
    payload += "\"rpm\":" + String(rpm) + ",";
    payload += "\"power\":" + String(power, 1) + ",";
    payload += "\"voltage\":" + String(voltage, 1) + ",";
    payload += "\"current\":" + String(current, 1);
    payload += "}";

    // 3. Publish the data to the topic
    mqttClient.publish(MQTT_TOPIC, payload.c_str());
    Serial.println("Published: " + payload);

    lastPublish = millis();
  }
}
```

---

## 5. Summary Checklist ✅

1.  [ ] I have installed the **PubSubClient** library in Arduino IDE.
2.  [ ] I have the 3 certificates downloaded (Root CA, Device Cert, Private Key).
3.  [ ] I created a `secrets.h` file and pasted the certificate contents exactly as they appear inside the `R"EOF(...)EOF"` blocks.
4.  [ ] I updated my **Wi-Fi Name** and **Password** in `secrets.h`.
5.  [ ] I have code to get the current real time (`ts` field) - *Tip: Use an `NTPClient` library to fetch it from the internet via Wi-Fi.*
6.  [ ] I replaced the dummy sensor values (`waveHeight`, `rpm`, etc.) in the loop with my actual physical sensor readings.
7.  [ ] **CRITICAL:** I verified that the `PUBLISH_INTERVAL_MS` is set to `5000` (5 seconds) so we don't accidentally spam the AWS server and exceed the free tier limits!
