/*
 * ============================================================================
 *  SamudraGEN - Wave Energy Converter / OWC Monitoring Firmware
 *  Target : ESP-WROOM-32 / ESP-32S (38-pin NodeMCU-style dev board)  -  Arduino IDE
 * ============================================================================
 *
 *  Power chain being monitored:
 *
 *    3-Phase Generator -> DB35-10 Rectifier -> Capacitor bank + TVS -> Fuse
 *        -> INA228 (V / I / P)  -> Relay COM
 *                                    |-- NC -> Battery branch -> XL4016 -> Battery
 *                                    `-- NO -> Load branch
 *
 *  Sensors:
 *    INA228     I2C   - rectified DC bus voltage, current, power, energy
 *    SR04M-2    UART  - water surface distance -> wave height / wave frequency
 *    HW-040     GPIO  - rotary encoder pulses -> shaft RPM
 *    Relay      GPIO  - selects battery-charging branch or load branch
 *
 *  Cloud: AWS IoT Core, MQTT over TLS (port 8883), mutual X.509 auth.
 *
 * ----------------------------------------------------------------------------
 *  IMPORTANT DESIGN ASSUMPTIONS  (read before wiring / calibrating)
 * ----------------------------------------------------------------------------
 *  1. The INA228 sits BEFORE the relay, so it always measures whatever branch
 *     the relay has selected. Battery mode -> it reads the XL4016 charger input.
 *     Load mode -> it reads the load branch input.
 *
 *  2. Because there is only ONE INA228, the firmware CANNOT measure battery
 *     charging power and load power at the same time. The published
 *     voltage/current/power always belong to the branch named by "relayMode".
 *
 *  3. The ultrasonic wave-height figure is an APPROXIMATION derived from the
 *     peak-to-trough spread of the distance samples inside a short window.
 *     It must be calibrated against a physical reference (see README.md).
 *
 *  4. PULSES_PER_REVOLUTION for the HW-040 must be determined experimentally.
 *     Turn the shaft exactly one revolution by hand and read the pulse count
 *     printed on the serial monitor (ENCODER_CALIBRATION_MODE below).
 *
 *  5. Relay logic (as specified by the electrical design):
 *        GPIO LOW  -> relay de-energised -> COM-NC -> BATTERY CHARGING branch
 *        GPIO HIGH -> relay energised    -> COM-NO -> LOAD branch
 *     LOW is therefore the safe power-on / reset default.
 *
 *  6. PUBLISH_INTERVAL_MS must stay >= 5000 ms. Publishing faster spams AWS IoT
 *     Core and will burn through the free-tier message allowance.
 *
 * ----------------------------------------------------------------------------
 *  ARDUINO IDE BOARD SETTINGS  (critical - the sketch will misbehave otherwise)
 * ----------------------------------------------------------------------------
 *    Board            : "ESP32 Dev Module"
 *    Flash Size       : 4MB (32Mb)   (or whatever your specific module has)
 *    Partition Scheme : Default 4MB with spiffs (or any scheme with enough app space)
 *    Upload Speed     : 921600
 *
 *    This board has no native USB - `Serial` runs over UART0 (GPIO1/3) through
 *    the on-board USB-serial bridge chip, exactly like any classic ESP32 board.
 *    Plug into the single USB port; no "USB CDC On Boot" setting exists here.
 *
 *  Libraries required (Library Manager):
 *    PubSubClient  (Nick O'Leary)
 *    ArduinoJson   (Benoit Blanchon)   v6 or v7 - both supported
 *    NTPClient     (Fabrice Weinberg)
 *  The INA228 driver is implemented locally in this file (register level), so
 *  no INA228 library needs to be installed. See the INA228 section for how to
 *  swap in a vendor library later.
 * ============================================================================
 */

// ============================================================================
//  Includes
// ============================================================================
// Arduino IDE auto-prepends this include for .ino files; the ESP-IDF +
// arduino-esp32-component build does not, so it's explicit here.
#include <Arduino.h>

#include "secrets.h"

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <string.h>
#include <strings.h>   // strcasecmp()
#include "driver/gpio.h"

// ArduinoJson v6 and v7 use different document types. This keeps the sketch
// compiling on either version.
#if ARDUINOJSON_VERSION_MAJOR >= 7
  #define JSON_DOC(name, size) JsonDocument name
#else
  #define JSON_DOC(name, size) StaticJsonDocument<size> name
#endif

// ============================================================================
//  Pin definitions  (ESP-WROOM-32 / ESP-32S, 38-pin dev board)
// ============================================================================

// INA228 I2C (ESP32 default I2C pins)
#define INA228_SDA_PIN 21
#define INA228_SCL_PIN 22

// SR04M-2 Ultrasonic Sensor - Trigger/Echo mode (R27 unwelded = module default;
// see initUltrasonic() for why this project uses this mode instead of UART).
#define ULTRASONIC_ECHO_PIN 18   // sensor TX/Echo -> ESP32 input
#define ULTRASONIC_TRIG_PIN 5    // sensor RX/Trig  <- ESP32 output

// HW-040 Rotary Encoder
#define ENCODER_CLK_PIN 32
#define ENCODER_DT_PIN  33
// Encoder switch SW is not used and not connected

// Relay
// NOTE: GPIO11 is reserved for flash (SD_CMD) on WROOM-32 modules and is not
// broken out, so this project uses GPIO27 instead.
#define RELAY_PIN 27

// ============================================================================
//  Wi-Fi and AWS IoT configuration
//  (Wi-Fi credentials and X.509 certificates live in secrets.h)
// ============================================================================
const char* AWS_IOT_ENDPOINT     = "a3ozx3ahrccyt2-ats.iot.ap-south-1.amazonaws.com";
const int   AWS_IOT_PORT         = 8883;   // MQTT over TLS

const char* MQTT_TELEMETRY_TOPIC = "ocean/wave/telemetry";
const char* MQTT_CONTROL_TOPIC   = "ocean/wave/control";
const char* MQTT_STATUS_TOPIC    = "ocean/wave/status";
const char* CLIENT_ID            = "SamudraGEN-ESP32S3-v2";
const char* DEVICE_ID            = "SamudraGEN-ESP32S3-v2";

// Telemetry cadence. MUST stay >= 5000 ms (AWS free-tier protection).
const unsigned long PUBLISH_INTERVAL_MS = 5000;

// Time zone for the ISO-8601 "ts" field. Sri Lanka / IST = +05:30 = 19800 s.
const long TIMEZONE_OFFSET_SECONDS = 19800;
const char* NTP_SERVER             = "pool.ntp.org";

// Connection management
const unsigned long WIFI_RETRY_INTERVAL_MS   = 15000;  // re-issue WiFi.begin()
const unsigned long MQTT_RETRY_INTERVAL_MS   = 5000;   // first MQTT retry delay
const unsigned long MQTT_RETRY_MAX_MS        = 60000;  // backoff ceiling
// Must fit telemetry JSON, including the batched per-sample distance/wave
// arrays collected at the sensor's native rate between publishes (see
// WAVE_BATCH_MAX_SAMPLES) - those can add several hundred bytes on top of
// the ~400 B base payload.
const uint16_t      MQTT_BUFFER_SIZE         = 2048;
const uint16_t      MQTT_KEEPALIVE_S         = 60;

// Set to a non-zero number of consecutive failed MQTT connects to force a
// reboot. NOTE: a reboot returns the relay to BATTERY mode (safe default), so
// leave this at 0 unless you are happy with that side effect.
const uint16_t MQTT_FAILURES_BEFORE_RESTART = 0;

// ============================================================================
//  Feature switches / tuning constants
// ============================================================================
#define SERIAL_DEBUG              1   // 1 = verbose serial logging
#define INCLUDE_EXTENDED_TELEMETRY 1  // adds energyWh, dieTempC, uptimeS, ...
#define INCLUDE_LEGACY_FIELDS     0   // 1 = also emit old "waveHeight"/"waveFreq" keys
#define ENCODER_CALIBRATION_MODE  0   // 1 = print raw pulse count every second
#define INA228_FAIL_AS_NULL       1   // 1 = publish null on INA228 failure, 0 = -1
// INA228 is wired up and verified via test_ina228 - enable I2C init.
#define INA228_ENABLED             1

// ---- Relay -----------------------------------------------------------------
// Most blue "SRD-05VDC" relay boards are ACTIVE-LOW (IN=LOW energises the coil).
// The electrical design for this project assumes ACTIVE-HIGH wiring:
//     GPIO LOW  = coil off = COM-NC = battery charging
//     GPIO HIGH = coil on  = COM-NO = load
// If your relay module turns out to be inverted, set this to 1. The MQTT/JSON
// semantics (relayState 0 = battery, 1 = load) do NOT change.
#define RELAY_INVERT_OUTPUT 0

// ---- INA228 ----------------------------------------------------------------
// >>> CALIBRATE THESE TWO VALUES FOR YOUR HARDWARE <<<
// Shunt resistance actually fitted on your INA228 board, in ohms.
//   Adafruit INA228 breakout .............. 0.015
//   Common AliExpress INA228 modules ...... 0.015 or 0.002
//   External 100 A / 75 mV shunt .......... 0.00075
const float INA228_SHUNT_OHMS       = 0.015f;
// Highest current you ever expect to flow through the shunt, in amps.
// Sets the resolution: current_LSB = max / 2^19.
const float INA228_MAX_CURRENT_A    = 10.0f;
// Candidate I2C addresses (A1/A0 strapping). 0x40 is the usual default.
const uint8_t INA228_ADDR_CANDIDATES[] = { 0x40, 0x41, 0x44, 0x45 };
const unsigned long INA228_READ_INTERVAL_MS  = 500;
const unsigned long INA228_RETRY_INTERVAL_MS = 5000;  // re-init after a failure

// ---- SR04M-2 ultrasonic (Trigger/Echo mode) ---------------------------------
// The SR04M-2's mode is set by a resistor (R27) on its control board, not a
// jumper: open (default, this project) = Trigger/Echo like a classic HC-SR04;
// 47k = auto UART stream; 120k = triggered UART on 0x55. Since R27 is left
// open on this board, we trigger with a 10us HIGH pulse and time the Echo
// pulse width. Distance formula per the module datasheet: cm = high_us / 58.
const unsigned long ULTRASONIC_SAMPLE_MS    = 100;   // 10 Hz sampling
const unsigned long ULTRASONIC_TIMEOUT_MS   = 3000;  // no valid echo -> sensor bad
const float    ULTRASONIC_MIN_CM            = 20.0f; // module dead zone
const float    ULTRASONIC_MAX_CM            = 600.0f;
const unsigned long ULTRASONIC_ECHO_TIMEOUT_US = 35000UL;  // ~600cm round trip + margin

// ---- Wave analysis ---------------------------------------------------------
// >>> CALIBRATE <<< Distance from the sensor face down to STILL water level, cm.
// Only used for the reported water level; wave height/frequency do not need it.
const float WAVE_REFERENCE_DISTANCE_CM = 100.0f;
// >>> CALIBRATE <<< Multiplier applied to the raw peak-to-trough spread.
// Start at 1.0, compare against a ruler in the tank, then adjust.
const float WAVE_HEIGHT_SCALE          = 1.0f;
// Analysis window. Short enough to react quickly to real motion, long enough
// to reliably catch a normal wave/hand-test cycle despite occasional echo
// misses. (1000ms is the absolute floor given the 100ms sample rate, but at
// that speed only continuous fast oscillation registers - a single motion
// often falls between valid samples.)
const unsigned long WAVE_WINDOW_MS     = 2000;
const uint16_t WAVE_BUFFER_SIZE        = 160;   // 10 s @ 10 Hz + headroom
// The sensor is still dropping a meaningful fraction of echoes (see [US]
// OFFLINE toggling), so a 2s window often only contains 1-2 valid samples
// even during real, large motion. 5 was too strict - real swings of tens of
// cm were reading back as 0 because the window never accumulated enough
// points. 2 is the practical floor (need at least a before/after pair to
// have a spread at all).
const uint8_t  WAVE_MIN_SAMPLES        = 2;     // below this, report 0
// Spread smaller than this is treated as sensor noise, not a wave.
const float WAVE_NOISE_FLOOR_CM        = 1.0f;
// Hysteresis for the mean-crossing frequency detector.
const float WAVE_MIN_HYSTERESIS_CM     = 0.5f;
const float WAVE_HYSTERESIS_FRACTION   = 0.10f; // 10 % of the peak-to-trough spread

// ---- HW-040 rotary encoder -------------------------------------------------
// >>> CALIBRATE <<< Pulses seen on CLK for one full revolution of the shaft.
// A bare KY-040/HW-040 detented encoder gives 20 detents (=20 CLK pulses) per
// turn. If you geared or direct-coupled it, measure it (ENCODER_CALIBRATION_MODE).
const float PULSES_PER_REVOLUTION = 20.0f;
// Mechanical contacts bounce. Pulses closer together than this are ignored.
// 500 us allows up to 2000 pulses/s = 6000 RPM at 20 PPR. Raise it if the RPM
// reading is noisy at standstill, lower it if high RPM readings saturate.
const uint32_t ENCODER_DEBOUNCE_US        = 500;
const unsigned long RPM_UPDATE_INTERVAL_MS = 1000;
// Exponential smoothing on RPM: 1.0 = no smoothing, 0.3 = heavy smoothing.
const float RPM_SMOOTHING_ALPHA           = 0.6f;
// No pulses for this long -> the shaft is considered stopped.
const unsigned long RPM_ZERO_TIMEOUT_MS   = 2500;

// ============================================================================
//  Relay mode enum
// ============================================================================
enum SystemMode {
  MODE_BATTERY_CHARGE = 0,   // relay LOW  -> COM-NC -> battery charging branch
  MODE_LOAD           = 1    // relay HIGH -> COM-NO -> load branch
};

// ============================================================================
//  Sensor variables / global state
// ============================================================================

// --- INA228 ---
float generatorVoltage = 0.0f;   // V   (rectified DC bus)
float generatorCurrent = 0.0f;   // A   (into the selected branch)
float generatorPower   = 0.0f;   // W
float generatorEnergyWh = 0.0f;  // Wh  (accumulated since boot / last reset)
float ina228DieTempC   = 0.0f;   // degC
bool  ina228Ok         = false;
uint8_t ina228Address  = 0x40;
float ina228CurrentLSB = 0.0f;   // A per LSB, derived in initINA228()
bool  ina228AdcRangeHigh = false; // false = +/-163.84 mV, true = +/-40.96 mV
unsigned long lastIna228ReadMs  = 0;
unsigned long lastIna228RetryMs = 0;

// --- Ultrasonic / wave ---
float distanceCm    = 0.0f;      // latest filtered distance to water surface
float waveHeightCm  = 0.0f;      // peak-to-trough over the analysis window
float waveFreqHz    = 0.0f;      // dominant frequency via mean crossings
// Publish only samples waveHeightCm once every PUBLISH_INTERVAL_MS, so real
// motion between publishes was getting overwritten and lost before the next
// snapshot. This tracks the highest waveHeightCm seen since the last publish
// so every motion gets reported at least once, not just whatever happens to
// land on a publish tick.
float waveHeightPublishPeakCm = 0.0f;
float waterLevelCm  = 0.0f;      // reference - distance (positive = higher water)
bool  ultrasonicOk  = false;
unsigned long lastUltrasonicValidMs = 0;
unsigned long lastUltrasonicSampleMs = 0;

// Batch of every valid distance reading collected since the last publish, at
// the sensor's native ~10 Hz rate (ULTRASONIC_SAMPLE_MS), sent as arrays in
// the next publish so the web can see the full-resolution wave instead of a
// single value per PUBLISH_INTERVAL_MS - without publishing more often (same
// AWS IoT message count/cost, just a bigger payload).
const uint8_t WAVE_BATCH_MAX_SAMPLES = 50;   // PUBLISH_INTERVAL_MS / ULTRASONIC_SAMPLE_MS
float         waveBatchDistCm[WAVE_BATCH_MAX_SAMPLES];
uint16_t      waveBatchOffsetMs[WAVE_BATCH_MAX_SAMPLES];
uint8_t       waveBatchCount    = 0;
unsigned long waveBatchStartMs  = 0;

// Echo pulse is timestamped from a GPIO interrupt (not polled via pulseIn())
// because pulseIn()'s busy-poll loop can be starved by Wi-Fi ISR activity for
// long enough to miss the edge entirely, misreporting a real echo as "none".
volatile unsigned long echoRiseUs   = 0;
volatile unsigned long echoPulseUs  = 0;
volatile bool          echoPulseReady = false;

struct WaveSample {
  uint32_t t;    // millis()
  float    d;    // cm
};
WaveSample waveBuf[WAVE_BUFFER_SIZE];
uint16_t   waveHead  = 0;   // next write position
uint16_t   waveCount = 0;   // number of valid entries (saturates at buffer size)

float    usMedianBuf[3] = { 0, 0, 0 };
uint8_t  usMedianCount  = 0;

// --- Encoder / RPM ---
float rpm = 0.0f;
int8_t encoderDirection = 0;     // +1 / -1, last observed rotation direction
bool   encoderOk = false;
portMUX_TYPE encoderMux = portMUX_INITIALIZER_UNLOCKED;
volatile uint32_t encoderPulseCount     = 0;
volatile uint32_t encoderTotalPulses    = 0;
volatile uint32_t encoderLastPulseUs    = 0;
volatile int8_t   encoderLastDirection  = 0;
unsigned long lastRpmUpdateMs = 0;

// --- Relay ---
SystemMode currentMode = MODE_BATTERY_CHARGE;   // safe default

// --- Networking ---
WiFiClientSecure net;
PubSubClient     mqtt(net);
WiFiUDP          ntpUDP;
NTPClient        timeClient(ntpUDP, NTP_SERVER, 0, 600000);  // UTC, refresh 10 min

unsigned long lastPublishMs      = 0;
unsigned long lastWifiAttemptMs  = 0;
unsigned long lastMqttAttemptMs  = 0;
unsigned long mqttRetryDelayMs   = MQTT_RETRY_INTERVAL_MS;
uint16_t      mqttFailureCount   = 0;
uint32_t      publishSequence    = 0;
bool          ntpSynced          = false;
bool          wasWifiConnected   = false;

// ============================================================================
//  Function declarations
// ============================================================================
// Networking
void  connectWiFi();
void  ensureWiFi();
void  connectAWS();
void  ensureMqtt();
void  mqttCallback(char* topic, byte* payload, unsigned int length);

// INA228
bool  initINA228();
void  readINA228(float &voltage, float &current, float &power);
bool  ina228ReadEnergyWh(float &wh);
bool  ina228ReadDieTemp(float &tempC);

// Ultrasonic + wave analysis
void  initUltrasonic();
void  IRAM_ATTR echoISR();
void  serviceUltrasonic();
float measureUltrasonicPulseCm();
void  pushWaveSample(float dCm);
void  computeWaveStats();

// Encoder
void  initEncoder();
void  IRAM_ATTR encoderISR();
void  updateRPM();

// Relay
void  initRelay();
void  applyMode(SystemMode mode, const char* source);
const char* modeName(SystemMode mode);

// Publishing
void  publishTelemetry();
void  publishAck();
void  publishStatus(bool online);
void  publishError(const char* message, const char* detail);

// Helpers
String isoTimestamp();
bool   parseModeToken(const char* token, SystemMode &out);

// Logging helper - compiled out when SERIAL_DEBUG is 0
#if SERIAL_DEBUG
  #define LOG(fmt, ...) Serial.printf(fmt "\n", ##__VA_ARGS__)
#else
  #define LOG(fmt, ...) do {} while (0)
#endif

// ============================================================================
//  setup()
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(1500);   // give the USB-serial bridge time to enumerate

  Serial.println();
  Serial.println(F("============================================"));
  Serial.println(F("  SamudraGEN - Wave Energy Monitor"));
  Serial.println(F("  ESP-WROOM-32 / AWS IoT Core"));
  Serial.printf ("  Device ID : %s\n", DEVICE_ID);
  Serial.println(F("============================================"));

  // ---- Relay first: guarantees the safe default before anything else ----
  initRelay();

  // ---- Sensors ----
#if INA228_ENABLED
  Wire.begin(INA228_SDA_PIN, INA228_SCL_PIN);
  Wire.setClock(400000);
  if (initINA228()) {
    LOG("[INA228] Ready at 0x%02X (shunt %.5f ohm, max %.1f A, LSB %.9f A)",
        ina228Address, INA228_SHUNT_OHMS, INA228_MAX_CURRENT_A, ina228CurrentLSB);
  } else {
    Serial.println(F("[INA228] NOT DETECTED - telemetry will report null values"));
  }
#else
  Serial.println(F("[INA228] Skipped (INA228_ENABLED=0) - sensor not wired up yet"));
#endif

  initUltrasonic();
  initEncoder();

  // ---- Network ----
  connectWiFi();

  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  mqtt.setServer(AWS_IOT_ENDPOINT, AWS_IOT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(MQTT_BUFFER_SIZE);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
  mqtt.setSocketTimeout(10);

  timeClient.begin();
  if (WiFi.status() == WL_CONNECTED) {
    connectAWS();
  }

  Serial.println(F("[SYS] Setup complete, entering main loop"));
}

// ============================================================================
//  loop()
//  Everything here is non-blocking millis()-based scheduling.
// ============================================================================
void loop() {
  // 1. Keep the network alive. The relay is NEVER touched by these functions,
  //    so a Wi-Fi or MQTT outage leaves the relay in its last commanded state.
  ensureWiFi();

  if (WiFi.status() == WL_CONNECTED) {
    ensureMqtt();
    mqtt.loop();

    if (timeClient.update()) {
      ntpSynced = true;
    } else if (!ntpSynced && timeClient.getEpochTime() > 1600000000UL) {
      ntpSynced = true;
    }
  }

  // 2. Ultrasonic: drain the UART, take a filtered sample, refresh wave stats.
  serviceUltrasonic();

  // 3. Encoder -> RPM (once per RPM_UPDATE_INTERVAL_MS).
  updateRPM();

  // 4. INA228 electrical readings.
  unsigned long now = millis();
#if INA228_ENABLED
  if (now - lastIna228ReadMs >= INA228_READ_INTERVAL_MS) {
    lastIna228ReadMs = now;
    if (ina228Ok) {
      readINA228(generatorVoltage, generatorCurrent, generatorPower);
      ina228ReadEnergyWh(generatorEnergyWh);
      ina228ReadDieTemp(ina228DieTempC);
    } else if (now - lastIna228RetryMs >= INA228_RETRY_INTERVAL_MS) {
      // Try to recover a sensor that dropped off the bus.
      lastIna228RetryMs = now;
      if (initINA228()) {
        Serial.println(F("[INA228] Recovered"));
      }
    }
  }
#endif

  // 5. Telemetry publish (>= 5 s, enforced by PUBLISH_INTERVAL_MS).
  if (now - lastPublishMs >= PUBLISH_INTERVAL_MS) {
    lastPublishMs = now;
    publishTelemetry();
  }

  // loopTask never otherwise blocks long enough to guarantee the scheduler
  // services the CPU1 idle task, which trips the 5s task watchdog (it doesn't
  // reboot - CONFIG_ESP_TASK_WDT_PANIC is off - but it prints scary errors).
  // A 1-tick yield here costs nothing at this loop rate and fixes it.
  delay(1);
}

// ============================================================================
//  Wi-Fi connection
// ============================================================================
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);          // modem sleep hurts MQTT latency/stability
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttemptMs = millis();

  Serial.printf("[WiFi] Connecting to \"%s\"", WIFI_SSID);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(400);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    wasWifiConnected = true;
    Serial.printf("[WiFi] Connected. IP=%s  RSSI=%d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println(F("[WiFi] Connect timed out - will keep retrying in the background"));
  }
}

// Non-blocking Wi-Fi watchdog. Called every loop().
void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wasWifiConnected) {
      wasWifiConnected = true;
      Serial.printf("[WiFi] Reconnected. IP=%s  RSSI=%d dBm\n",
                    WiFi.localIP().toString().c_str(), WiFi.RSSI());
    }
    return;
  }

  if (wasWifiConnected) {
    wasWifiConnected = false;
    Serial.println(F("[WiFi] Connection lost - relay stays in its last state"));
  }

  unsigned long now = millis();
  if (now - lastWifiAttemptMs >= WIFI_RETRY_INTERVAL_MS) {
    lastWifiAttemptMs = now;
    Serial.println(F("[WiFi] Retrying..."));
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
}

// ============================================================================
//  AWS IoT (MQTT over TLS) connection
// ============================================================================
void connectAWS() {
  if (WiFi.status() != WL_CONNECTED) return;

  Serial.printf("[AWS] Connecting to %s:%d as \"%s\" ...\n",
                AWS_IOT_ENDPOINT, AWS_IOT_PORT, CLIENT_ID);

  // Last Will and Testament: if this device drops off ungracefully, AWS
  // publishes an offline notice to the status topic on its behalf.
  const char* willPayload = "{\"type\":\"status\",\"deviceId\":\"" "SamudraGEN-ESP32" "\",\"online\":false}";

  bool connected = mqtt.connect(CLIENT_ID,
                                nullptr, nullptr,       // no username/password (X.509 auth)
                                MQTT_STATUS_TOPIC,      // will topic
                                1,                      // will QoS
                                false,                  // will retain
                                willPayload);

  if (connected) {
    mqttFailureCount = 0;
    mqttRetryDelayMs = MQTT_RETRY_INTERVAL_MS;
    Serial.println(F("[AWS] MQTT connected"));

    if (mqtt.subscribe(MQTT_CONTROL_TOPIC, 1)) {
      Serial.printf("[MQTT] Subscribed to %s (QoS 1)\n", MQTT_CONTROL_TOPIC);
    } else {
      Serial.printf("[MQTT] SUBSCRIBE FAILED for %s\n", MQTT_CONTROL_TOPIC);
    }

    timeClient.forceUpdate();
    if (timeClient.getEpochTime() > 1600000000UL) ntpSynced = true;

    publishStatus(true);
    publishTelemetry();          // send one immediately so the dashboard fills in
    lastPublishMs = millis();
  } else {
    mqttFailureCount++;
    // PubSubClient state codes: -4 timeout, -3 conn lost, -2 connect failed,
    // -1 disconnected, 1..5 protocol/auth refusals.
    Serial.printf("[AWS] MQTT connect failed, state=%d (attempt %u)\n",
                  mqtt.state(), mqttFailureCount);
    if (mqtt.state() == -2) {
      Serial.println(F("      state -2 usually means: wrong endpoint, wrong certificates,"));
      Serial.println(F("      certificate not ACTIVE, or the IoT policy does not allow this client ID."));
    }
    // TEMP DIAGNOSTIC: surface the raw mbedTLS error underneath PubSubClient's
    // state code, since state=-1 can mean either "clean disconnect" or "the
    // packet reader choked partway through a truncated/garbled response" -
    // this pinpoints which.
    {
      char tlsErrBuf[128];
      int tlsErr = net.lastError(tlsErrBuf, sizeof(tlsErrBuf));
      Serial.printf("      net.connected()=%d  lastError=%d (%s)\n",
                    (int)net.connected(), tlsErr, tlsErr ? tlsErrBuf : "none");
    }

    if (MQTT_FAILURES_BEFORE_RESTART > 0 && mqttFailureCount >= MQTT_FAILURES_BEFORE_RESTART) {
      Serial.println(F("[SYS] Too many MQTT failures - restarting (relay returns to BATTERY)"));
      delay(200);
      ESP.restart();
    }
  }
}

// Non-blocking MQTT watchdog with exponential backoff.
void ensureMqtt() {
  if (mqtt.connected()) return;

  unsigned long now = millis();
  if (now - lastMqttAttemptMs < mqttRetryDelayMs) return;

  lastMqttAttemptMs = now;
  connectAWS();

  if (!mqtt.connected()) {
    mqttRetryDelayMs *= 2;
    if (mqttRetryDelayMs > MQTT_RETRY_MAX_MS) mqttRetryDelayMs = MQTT_RETRY_MAX_MS;
  }
}

// ============================================================================
//  MQTT callback - relay control commands from AWS / the web interface
// ============================================================================
//  Accepted payloads (any one of these):
//     {"relay":"battery"}      {"relay":"load"}
//     {"mode":"battery"}       {"mode":"load"}
//     {"relayState":0}         {"relayState":1}
//     {"relay":0}              {"relay":1}
//     {"state":"battery"}      {"command":"load"}
//     {"relay":false}          {"relay":true}
//     {"command":"status"}     -> just re-publishes the current status
// ============================================================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Copy into a NUL-terminated buffer for logging + parsing.
  static char buf[512];
  unsigned int n = (length < sizeof(buf) - 1) ? length : sizeof(buf) - 1;
  memcpy(buf, payload, n);
  buf[n] = '\0';

  Serial.printf("[MQTT] Message on %s: %s\n", topic, buf);

  if (strcmp(topic, MQTT_CONTROL_TOPIC) != 0) {
    return;   // not a topic we act on
  }

  JSON_DOC(doc, 512);
  DeserializationError err = deserializeJson(doc, buf, n);
  if (err) {
    Serial.printf("[CTRL] Invalid JSON: %s\n", err.c_str());
    publishError("invalid_json", err.c_str());
    return;
  }

  // ---- Housekeeping command: {"command":"status"} ----
  const char* cmdStr = nullptr;
  if (doc["command"].is<const char*>())  cmdStr = doc["command"];
  else if (doc["cmd"].is<const char*>()) cmdStr = doc["cmd"];
  if (cmdStr && (strcasecmp(cmdStr, "status") == 0 || strcasecmp(cmdStr, "ping") == 0)) {
    Serial.println(F("[CTRL] Status request"));
    publishStatus(true);
    return;
  }

  // ---- Resolve the requested mode from any of the accepted key/value forms ----
  SystemMode requested;
  bool found = false;

  const char* keys[] = { "relay", "mode", "relayState", "state", "command", "cmd", "value" };
  for (uint8_t i = 0; i < sizeof(keys) / sizeof(keys[0]) && !found; i++) {
    // JsonVariantConst, not JsonVariant: a mutable variant would *create* the
    // member in the document just by probing for it (ArduinoJson v7).
    JsonVariantConst v = doc[keys[i]];
    if (v.isNull()) continue;

    if (v.is<const char*>()) {                  // "battery" / "load" / "0" / "1"
      found = parseModeToken(v.as<const char*>(), requested);
    } else if (v.is<bool>()) {                  // true = load, false = battery
      requested = v.as<bool>() ? MODE_LOAD : MODE_BATTERY_CHARGE;
      found = true;
    } else if (v.is<int>() || v.is<float>()) {  // 0 = battery, 1 = load
      int iv = v.as<int>();
      if (iv == 0 || iv == 1) {
        requested = (iv == 1) ? MODE_LOAD : MODE_BATTERY_CHARGE;
        found = true;
      }
    }
  }

  // Nested form, e.g. an AWS device-shadow style {"state":{"desired":{"relay":"load"}}}
  if (!found && doc["state"]["desired"].is<JsonObject>()) {
    const char* nestedKeys[] = { "relay", "mode", "relayState" };
    for (uint8_t i = 0; i < 3 && !found; i++) {
      JsonVariantConst v = doc["state"]["desired"][nestedKeys[i]];
      if (v.isNull()) continue;

      if (v.is<const char*>()) {
        found = parseModeToken(v.as<const char*>(), requested);
      } else if (v.is<bool>()) {
        requested = v.as<bool>() ? MODE_LOAD : MODE_BATTERY_CHARGE;
        found = true;
      } else if (v.is<int>()) {
        int iv = v.as<int>();
        if (iv == 0 || iv == 1) {
          requested = (iv == 1) ? MODE_LOAD : MODE_BATTERY_CHARGE;
          found = true;
        }
      }
    }
  }

  if (!found) {
    // SAFETY: an unrecognised command is IGNORED. The relay keeps its state.
    Serial.println(F("[CTRL] Unrecognised command - ignored, relay unchanged"));
    publishError("invalid_command",
                 "expected {\"relay\":\"battery\"|\"load\"} or {\"relayState\":0|1}");
    return;
  }

  applyMode(requested, "MQTT");
  publishAck();
}

// Maps a text token to a SystemMode. Returns false if the token is unknown.
bool parseModeToken(const char* token, SystemMode &out) {
  if (!token) return false;

  if (strcasecmp(token, "battery")  == 0 || strcasecmp(token, "batt")     == 0 ||
      strcasecmp(token, "bat")      == 0 || strcasecmp(token, "charge")   == 0 ||
      strcasecmp(token, "charging") == 0 || strcasecmp(token, "chg")      == 0 ||
      strcasecmp(token, "0")        == 0 || strcasecmp(token, "off")      == 0 ||
      strcasecmp(token, "false")    == 0 || strcasecmp(token, "low")      == 0) {
    out = MODE_BATTERY_CHARGE;
    return true;
  }

  if (strcasecmp(token, "load") == 0 || strcasecmp(token, "loads") == 0 ||
      strcasecmp(token, "1")    == 0 || strcasecmp(token, "on")    == 0 ||
      strcasecmp(token, "true") == 0 || strcasecmp(token, "high")  == 0) {
    out = MODE_LOAD;
    return true;
  }

  return false;
}

// ============================================================================
//  Relay control
// ============================================================================
void initRelay() {
  // Internal pull-down so RELAY_PIN reads LOW (not floating) during the boot
  // window before this function runs, instead of picking up noise while it's
  // still an input. The weak pulldown stays enabled harmlessly once the pin
  // becomes an OUTPUT below - the driver simply overrides it.
  gpio_pulldown_en((gpio_num_t)RELAY_PIN);

  // Preload the output latch BEFORE enabling the driver so the relay never sees
  // a HIGH glitch during boot.
  digitalWrite(RELAY_PIN, RELAY_INVERT_OUTPUT ? HIGH : LOW);
  pinMode(RELAY_PIN, OUTPUT);

  currentMode = MODE_BATTERY_CHARGE;
  digitalWrite(RELAY_PIN, RELAY_INVERT_OUTPUT ? HIGH : LOW);

  Serial.println(F("[RELAY] Boot default: LOW -> COM-NC -> BATTERY CHARGING branch"));
}

void applyMode(SystemMode mode, const char* source) {
  currentMode = mode;

  // Specified behaviour: battery -> LOW, load -> HIGH.
  int level = (mode == MODE_LOAD) ? HIGH : LOW;
#if RELAY_INVERT_OUTPUT
  level = (level == HIGH) ? LOW : HIGH;
#endif
  digitalWrite(RELAY_PIN, level);

  Serial.printf("[RELAY] %s command -> mode=%s, relayState=%d, GPIO%d=%s (%s branch)\n",
                source, modeName(mode), (int)mode, RELAY_PIN,
                (level == HIGH) ? "HIGH" : "LOW",
                (mode == MODE_LOAD) ? "COM-NO / LOAD" : "COM-NC / BATTERY");
}

const char* modeName(SystemMode mode) {
  return (mode == MODE_LOAD) ? "load" : "battery";
}

// ============================================================================
//  INA228 - initialisation and reading
// ----------------------------------------------------------------------------
//  Self-contained register-level driver, so no external INA228 library is
//  required. To swap in a vendor library later, keep the two public functions
//  (initINA228 / readINA228) and replace their bodies - nothing else in this
//  sketch touches the INA228 directly.
//
//  Wiring reminder: V+ = capacitor bank positive after the fuse,
//  V- = relay COM, VBUS tied to the same node as V-. Bus voltage must stay
//  below the INA228's 85 V absolute maximum.
// ============================================================================
#define INA228_REG_CONFIG        0x00
#define INA228_REG_ADC_CONFIG    0x01
#define INA228_REG_SHUNT_CAL     0x02
#define INA228_REG_VSHUNT        0x04
#define INA228_REG_VBUS          0x05
#define INA228_REG_DIETEMP       0x06
#define INA228_REG_CURRENT       0x07
#define INA228_REG_POWER         0x08
#define INA228_REG_ENERGY        0x09
#define INA228_REG_DIAG_ALRT     0x0B
#define INA228_REG_MANUFACTURER  0x3E
#define INA228_REG_DEVICE_ID     0x3F

#define INA228_MANUFACTURER_TI   0x5449   // "TI"

static bool ina228ReadBytes(uint8_t reg, uint8_t* buf, uint8_t len) {
  Wire.beginTransmission(ina228Address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;      // repeated start
  if (Wire.requestFrom((int)ina228Address, (int)len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

static bool ina228Write16(uint8_t reg, uint16_t value) {
  Wire.beginTransmission(ina228Address);
  Wire.write(reg);
  Wire.write((uint8_t)(value >> 8));
  Wire.write((uint8_t)(value & 0xFF));
  return Wire.endTransmission() == 0;
}

static bool ina228Read16(uint8_t reg, uint16_t &value) {
  uint8_t b[2];
  if (!ina228ReadBytes(reg, b, 2)) return false;
  value = ((uint16_t)b[0] << 8) | b[1];
  return true;
}

// VBUS / VSHUNT / CURRENT are 24-bit registers holding a 20-bit signed value in
// the upper bits; the low 4 bits are reserved.
static bool ina228Read20Signed(uint8_t reg, int32_t &value) {
  uint8_t b[3];
  if (!ina228ReadBytes(reg, b, 3)) return false;
  int32_t raw = ((int32_t)b[0] << 16) | ((int32_t)b[1] << 8) | b[2];
  raw >>= 4;
  if (raw & 0x00080000) raw |= 0xFFF00000;   // sign-extend 20 -> 32 bits
  value = raw;
  return true;
}

// POWER is a full 24-bit unsigned register.
static bool ina228Read24Unsigned(uint8_t reg, uint32_t &value) {
  uint8_t b[3];
  if (!ina228ReadBytes(reg, b, 3)) return false;
  value = ((uint32_t)b[0] << 16) | ((uint32_t)b[1] << 8) | b[2];
  return true;
}

// ENERGY is a 40-bit unsigned accumulator.
static bool ina228Read40Unsigned(uint8_t reg, uint64_t &value) {
  uint8_t b[5];
  if (!ina228ReadBytes(reg, b, 5)) return false;
  value = ((uint64_t)b[0] << 32) | ((uint64_t)b[1] << 24) |
          ((uint64_t)b[2] << 16) | ((uint64_t)b[3] << 8)  | b[4];
  return true;
}

bool initINA228() {
  ina228Ok = false;

  // ---- 1. Probe the candidate addresses for the TI manufacturer ID ----
  bool found = false;
  for (uint8_t i = 0; i < sizeof(INA228_ADDR_CANDIDATES); i++) {
    ina228Address = INA228_ADDR_CANDIDATES[i];
    uint16_t manuf = 0;
    if (ina228Read16(INA228_REG_MANUFACTURER, manuf) && manuf == INA228_MANUFACTURER_TI) {
      found = true;
      break;
    }
  }
  if (!found) {
    ina228Address = INA228_ADDR_CANDIDATES[0];
    return false;
  }

  // ---- 2. Software reset ----
  if (!ina228Write16(INA228_REG_CONFIG, 0x8000)) return false;
  delay(5);

  // ---- 3. Pick the ADC range and compute the calibration ----
  // ADCRANGE 0 = +/-163.84 mV full scale, 1 = +/-40.96 mV (4x finer).
  float maxShuntV = INA228_MAX_CURRENT_A * INA228_SHUNT_OHMS;
  ina228AdcRangeHigh = (maxShuntV <= 0.04096f);

  uint16_t config = 0x0000;
  if (ina228AdcRangeHigh) config |= (1 << 4);          // ADCRANGE bit
  if (!ina228Write16(INA228_REG_CONFIG, config)) return false;

  // current_LSB = max expected current / 2^19
  ina228CurrentLSB = INA228_MAX_CURRENT_A / 524288.0f;

  // SHUNT_CAL = 13107.2e6 * current_LSB * R_shunt   (x4 when ADCRANGE = 1)
  float shuntCalF = 13107.2e6f * ina228CurrentLSB * INA228_SHUNT_OHMS;
  if (ina228AdcRangeHigh) shuntCalF *= 4.0f;
  if (shuntCalF < 1.0f)     shuntCalF = 1.0f;
  if (shuntCalF > 65535.0f) shuntCalF = 65535.0f;
  if (!ina228Write16(INA228_REG_SHUNT_CAL, (uint16_t)(shuntCalF + 0.5f))) return false;

  // ---- 4. ADC configuration ----
  // MODE=0xF (continuous bus + shunt + temperature),
  // VBUSCT/VSHCT/VTCT = 5 (1052 us each), AVG = 2 (16 samples averaged).
  uint16_t adcConfig = (0xF << 12) | (5 << 9) | (5 << 6) | (5 << 3) | 2;
  if (!ina228Write16(INA228_REG_ADC_CONFIG, adcConfig)) return false;

  ina228Ok = true;
  return true;
}

// Reads bus voltage [V], current [A] and power [W].
// On an I2C failure the sensor is flagged bad and the previous values are kept;
// publishTelemetry() then emits null (or -1) plus sensorStatus.ina228 = false.
void readINA228(float &voltage, float &current, float &power) {
  if (!ina228Ok) return;

  int32_t  rawBus = 0, rawCurrent = 0;
  uint32_t rawPower = 0;

  if (!ina228Read20Signed(INA228_REG_VBUS, rawBus) ||
      !ina228Read20Signed(INA228_REG_CURRENT, rawCurrent) ||
      !ina228Read24Unsigned(INA228_REG_POWER, rawPower)) {
    ina228Ok = false;
    Serial.println(F("[INA228] I2C read failed - marking sensor offline"));
    return;
  }

  voltage = rawBus     * 195.3125e-6f;                  // 195.3125 uV per LSB
  current = rawCurrent * ina228CurrentLSB;
  power   = rawPower   * 3.2f * ina228CurrentLSB;       // power_LSB = 3.2 * current_LSB

  if (voltage < 0.0f) voltage = 0.0f;                   // bus voltage is unipolar
}

bool ina228ReadEnergyWh(float &wh) {
  if (!ina228Ok) return false;
  uint64_t raw = 0;
  if (!ina228Read40Unsigned(INA228_REG_ENERGY, raw)) return false;
  // Energy [J] = 16 * power_LSB * ENERGY  ->  Wh = J / 3600
  double joules = 16.0 * 3.2 * (double)ina228CurrentLSB * (double)raw;
  wh = (float)(joules / 3600.0);
  return true;
}

bool ina228ReadDieTemp(float &tempC) {
  if (!ina228Ok) return false;
  uint16_t raw = 0;
  if (!ina228Read16(INA228_REG_DIETEMP, raw)) return false;
  tempC = (int16_t)raw * 7.8125e-3f;    // 7.8125 m degC per LSB
  return true;
}

// ============================================================================
//  Ultrasonic (SR04M-2) - initialisation and reading
// ============================================================================
void initUltrasonic() {
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(ULTRASONIC_ECHO_PIN), echoISR, CHANGE);
  usMedianCount = 0;
  ultrasonicOk  = false;
  lastUltrasonicValidMs = 0;
  waveBatchCount   = 0;
  waveBatchStartMs = millis();
  Serial.printf("[US] Trigger/Echo mode (IRQ capture)  TRIG=IO%d  ECHO=IO%d\n",
                ULTRASONIC_TRIG_PIN, ULTRASONIC_ECHO_PIN);
}

// Timestamps the Echo pulse's rising/falling edges the instant they happen,
// instead of relying on the main loop polling fast enough to catch them -
// this is what makes the capture immune to Wi-Fi ISR scheduling jitter.
void IRAM_ATTR echoISR() {
  if (digitalRead(ULTRASONIC_ECHO_PIN)) {
    echoRiseUs = micros();
  } else if (echoRiseUs != 0) {
    echoPulseUs    = micros() - echoRiseUs;
    echoPulseReady = true;
  }
}

/*
 * Fires a 10us trigger pulse, then waits for echoISR() to report a captured
 * pulse width (hardware-timestamped, not polled). Still bounded by
 * ULTRASONIC_ECHO_TIMEOUT_US so a missing echo can't stall the loop.
 *
 * Returns the distance in cm, or -1.0f if no echo / out of range.
 */
float measureUltrasonicPulseCm() {
  noInterrupts();
  echoRiseUs     = 0;
  echoPulseReady = false;
  interrupts();

  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

  unsigned long waitStart = micros();
  while (!echoPulseReady) {
    if (micros() - waitStart > ULTRASONIC_ECHO_TIMEOUT_US) return -1.0f;  // no echo
  }

  unsigned long highUs;
  noInterrupts();
  highUs = echoPulseUs;
  interrupts();

  float cm = highUs / 58.0f;       // per SR04M-2 datasheet
  if (cm < ULTRASONIC_MIN_CM || cm > ULTRASONIC_MAX_CM) return -1.0f;
  return cm;
}

// Called every loop(): triggers the sensor, filters the reading, feeds the
// wave-analysis buffer and refreshes the sensor health flag.
void serviceUltrasonic() {
  unsigned long now = millis();

  if (now - lastUltrasonicSampleMs >= ULTRASONIC_SAMPLE_MS) {
    lastUltrasonicSampleMs = now;

    float raw = measureUltrasonicPulseCm();
    if (raw > 0.0f) {
      lastUltrasonicValidMs = now;

      // Median-of-3 filter: kills the single-sample spikes these modules
      // produce when the echo hits foam or a wave crest at a bad angle.
      usMedianBuf[2] = usMedianBuf[1];
      usMedianBuf[1] = usMedianBuf[0];
      usMedianBuf[0] = raw;
      if (usMedianCount < 3) usMedianCount++;

      float filtered = raw;
      if (usMedianCount == 3) {
        float a = usMedianBuf[0], b = usMedianBuf[1], c = usMedianBuf[2];
        float lo = (a < b) ? a : b;      // min(a,b)
        float hi = (a < b) ? b : a;      // max(a,b)
        float mid = (hi < c) ? hi : c;   // min(max(a,b), c)
        filtered = (lo > mid) ? lo : mid; // max(min(a,b), that) == median
      }

      distanceCm   = filtered;
      waterLevelCm = WAVE_REFERENCE_DISTANCE_CM - filtered;
      pushWaveSample(filtered);
      computeWaveStats();
      if (waveHeightCm > waveHeightPublishPeakCm) waveHeightPublishPeakCm = waveHeightCm;

      if (waveBatchCount < WAVE_BATCH_MAX_SAMPLES) {
        waveBatchDistCm[waveBatchCount]   = filtered;
        waveBatchOffsetMs[waveBatchCount] = (uint16_t)(now - waveBatchStartMs);
        waveBatchCount++;
      }
    }
  }

  // Health: a valid echo must have arrived recently.
  bool okNow = (lastUltrasonicValidMs != 0) &&
               (now - lastUltrasonicValidMs < ULTRASONIC_TIMEOUT_MS);
  if (okNow != ultrasonicOk) {
    ultrasonicOk = okNow;
    Serial.printf("[US] Sensor %s\n", okNow ? "online" : "OFFLINE (no echo)");
  }
}

// ============================================================================
//  Wave height and wave frequency calculation
// ----------------------------------------------------------------------------
//  Approach:
//    * keep a rolling WAVE_WINDOW_MS buffer of filtered distance samples
//    * wave height  = (max - min) inside the window, x WAVE_HEIGHT_SCALE
//                     (peak-to-trough, i.e. crest-to-trough height H)
//    * wave freq    = upward mean-crossings per second, with hysteresis so
//                     sensor noise around the mean is not counted as a wave
//
//  This is an approximation. Real wave analysis would use an FFT or zero-
//  up-crossing statistics over a much longer record (typically 20 minutes).
//  Calibrate against a physical scale in the tank before quoting numbers.
// ============================================================================
void pushWaveSample(float dCm) {
  waveBuf[waveHead].t = millis();
  waveBuf[waveHead].d = dCm;
  waveHead = (waveHead + 1) % WAVE_BUFFER_SIZE;
  if (waveCount < WAVE_BUFFER_SIZE) waveCount++;
}

void computeWaveStats() {
  if (waveCount < WAVE_MIN_SAMPLES) {
    waveHeightCm = 0.0f;
    waveFreqHz   = 0.0f;
    return;
  }

  uint32_t now    = millis();
  uint16_t oldest = (waveHead + WAVE_BUFFER_SIZE - waveCount) % WAVE_BUFFER_SIZE;

  // ---- Pass 1: min / max / mean inside the window ----
  float minD = 1e6f, maxD = -1e6f, sum = 0.0f;
  uint16_t used = 0;
  for (uint16_t i = 0; i < waveCount; i++) {
    uint16_t idx = (oldest + i) % WAVE_BUFFER_SIZE;
    if (now - waveBuf[idx].t > WAVE_WINDOW_MS) continue;
    float d = waveBuf[idx].d;
    if (d < minD) minD = d;
    if (d > maxD) maxD = d;
    sum += d;
    used++;
  }

  if (used < WAVE_MIN_SAMPLES) {
    waveHeightCm = 0.0f;
    waveFreqHz   = 0.0f;
    return;
  }

  float mean   = sum / used;
  float spread = maxD - minD;

  if (spread < WAVE_NOISE_FLOOR_CM) {
    // Flat water (or the sensor is stuck) - report calm rather than noise.
    waveHeightCm = 0.0f;
    waveFreqHz   = 0.0f;
    return;
  }

  waveHeightCm = spread * WAVE_HEIGHT_SCALE;

  // ---- Pass 2: upward mean-crossings with hysteresis ----
  float hyst = spread * WAVE_HYSTERESIS_FRACTION;
  if (hyst < WAVE_MIN_HYSTERESIS_CM) hyst = WAVE_MIN_HYSTERESIS_CM;
  int8_t   state      = 0;    // -1 below band, +1 above band, 0 unknown
  uint16_t crossings  = 0;
  uint32_t firstCross = 0, lastCross = 0;

  for (uint16_t i = 0; i < waveCount; i++) {
    uint16_t idx = (oldest + i) % WAVE_BUFFER_SIZE;
    if (now - waveBuf[idx].t > WAVE_WINDOW_MS) continue;

    float dev = waveBuf[idx].d - mean;
    if (dev > hyst) {
      if (state == -1) {                       // crossed upward through the mean
        crossings++;
        if (crossings == 1) firstCross = waveBuf[idx].t;
        lastCross = waveBuf[idx].t;
      }
      state = 1;
    } else if (dev < -hyst) {
      state = -1;
    }
  }

  if (crossings >= 2 && lastCross > firstCross) {
    // (crossings - 1) complete wave periods spanned (lastCross - firstCross) ms
    waveFreqHz = (crossings - 1) * 1000.0f / (float)(lastCross - firstCross);
  } else {
    waveFreqHz = 0.0f;
  }
}

// ============================================================================
//  Encoder ISR and RPM calculation
// ----------------------------------------------------------------------------
//  The HW-040 is a mechanical (contact) encoder, so every edge bounces. The ISR
//  applies a hard time-based debounce; anything faster than ENCODER_DEBOUNCE_US
//  is treated as contact bounce and discarded. That also sets the maximum
//  measurable speed: 1 / (PPR * debounce) revolutions per second.
// ============================================================================
void initEncoder() {
  pinMode(ENCODER_CLK_PIN, INPUT_PULLUP);
  pinMode(ENCODER_DT_PIN,  INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCODER_CLK_PIN), encoderISR, RISING);
  encoderOk = true;
  lastRpmUpdateMs = millis();
  Serial.printf("[ENC] CLK=IO%d DT=IO%d, %.1f pulses/rev, debounce %u us\n",
                ENCODER_CLK_PIN, ENCODER_DT_PIN, PULSES_PER_REVOLUTION,
                (unsigned)ENCODER_DEBOUNCE_US);
}

void IRAM_ATTR encoderISR() {
  uint32_t nowUs = micros();
  portENTER_CRITICAL_ISR(&encoderMux);
  if (nowUs - encoderLastPulseUs >= ENCODER_DEBOUNCE_US) {
    encoderLastPulseUs = nowUs;
    encoderPulseCount++;
    encoderTotalPulses++;
    // DT level at the CLK rising edge gives the direction of rotation.
    encoderLastDirection = (digitalRead(ENCODER_DT_PIN) == HIGH) ? 1 : -1;
  }
  portEXIT_CRITICAL_ISR(&encoderMux);
}

void updateRPM() {
  unsigned long now = millis();
  if (now - lastRpmUpdateMs < RPM_UPDATE_INTERVAL_MS) return;

  uint32_t pulses;
  uint32_t lastPulseUs;
  int8_t   dir;
  portENTER_CRITICAL(&encoderMux);
  pulses               = encoderPulseCount;
  encoderPulseCount    = 0;
  lastPulseUs          = encoderLastPulseUs;
  dir                  = encoderLastDirection;
  portEXIT_CRITICAL(&encoderMux);

  float dtSec = (now - lastRpmUpdateMs) / 1000.0f;
  lastRpmUpdateMs = now;
  if (dtSec <= 0.0f) return;

  // rpm = pulses_per_second * 60 / pulses_per_revolution
  float pulsesPerSecond = pulses / dtSec;
  float instantRpm      = pulsesPerSecond * 60.0f / PULSES_PER_REVOLUTION;

  // Shaft stopped? Snap straight to zero instead of letting the smoothing decay
  // slowly. (micros() wraps every ~71 min; unsigned subtraction handles that.)
  uint32_t sinceLastPulseUs = micros() - lastPulseUs;
  if (pulses == 0 && sinceLastPulseUs > (RPM_ZERO_TIMEOUT_MS * 1000UL)) {
    rpm = 0.0f;
    encoderDirection = 0;
    return;
  }

  rpm = (RPM_SMOOTHING_ALPHA * instantRpm) + ((1.0f - RPM_SMOOTHING_ALPHA) * rpm);
  encoderDirection = dir;

#if ENCODER_CALIBRATION_MODE
  // Turn the shaft exactly one revolution by hand and read "total" to obtain
  // the correct PULSES_PER_REVOLUTION value.
  Serial.printf("[ENC-CAL] pulses this second=%u  total=%u  dir=%d\n",
                (unsigned)pulses, (unsigned)encoderTotalPulses, (int)dir);
#endif
}

// ============================================================================
//  Telemetry JSON publishing
// ============================================================================
void publishTelemetry() {
  JSON_DOC(doc, 2048);

  doc["ts"]           = isoTimestamp();
  doc["deviceId"]     = DEVICE_ID;
  doc["relayMode"]    = modeName(currentMode);
  doc["relayState"]   = (int)currentMode;

  // Peak since the last publish, not the instantaneous value - see
  // waveHeightPublishPeakCm's declaration for why.
  float waveHeightToPublish = waveHeightPublishPeakCm;
  waveHeightPublishPeakCm = 0.0f;

  doc["waveHeightCm"] = roundf(waveHeightToPublish * 100.0f) / 100.0f;
  doc["waveFreqHz"]   = roundf(waveFreqHz   * 1000.0f) / 1000.0f;
  doc["distanceCm"]   = roundf(distanceCm   * 100.0f) / 100.0f;
  doc["rpm"]          = roundf(rpm          * 10.0f) / 10.0f;

  // Every valid distance sample collected since the last publish, at the
  // sensor's native rate - lets the web draw the actual wave shape instead
  // of one point per PUBLISH_INTERVAL_MS, without publishing more often.
  // distanceSampleOffsetMs[i] is ms since this batch window started (not
  // evenly spaced - samples are dropped whenever the sensor misses an echo).
#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonArray distSamples    = doc["distanceSamplesCm"].to<JsonArray>();
  JsonArray distSampleOffs = doc["distanceSampleOffsetMs"].to<JsonArray>();
#else
  JsonArray distSamples    = doc.createNestedArray("distanceSamplesCm");
  JsonArray distSampleOffs = doc.createNestedArray("distanceSampleOffsetMs");
#endif
  for (uint8_t i = 0; i < waveBatchCount; i++) {
    distSamples.add(roundf(waveBatchDistCm[i] * 10.0f) / 10.0f);
    distSampleOffs.add(waveBatchOffsetMs[i]);
  }
  waveBatchCount   = 0;
  waveBatchStartMs = millis();

  // INA228 values: null (or -1) when the sensor is not responding.
  if (ina228Ok) {
    doc["voltage"] = roundf(generatorVoltage * 1000.0f) / 1000.0f;
    doc["current"] = roundf(generatorCurrent * 1000.0f) / 1000.0f;
    doc["power"]   = roundf(generatorPower   * 1000.0f) / 1000.0f;
  } else {
#if INA228_FAIL_AS_NULL
    doc["voltage"] = nullptr;
    doc["current"] = nullptr;
    doc["power"]   = nullptr;
#else
    doc["voltage"] = -1;
    doc["current"] = -1;
    doc["power"]   = -1;
#endif
  }

  doc["wifiRssi"] = (WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : 0;

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonObject status = doc["sensorStatus"].to<JsonObject>();
#else
  JsonObject status = doc.createNestedObject("sensorStatus");
#endif
  status["ina228"]     = ina228Ok;
  status["ultrasonic"] = ultrasonicOk;
  status["encoder"]    = encoderOk;

#if INCLUDE_EXTENDED_TELEMETRY
  doc["energyWh"]   = ina228Ok ? (roundf(generatorEnergyWh * 1000.0f) / 1000.0f) : 0.0f;
  doc["dieTempC"]   = ina228Ok ? (roundf(ina228DieTempC * 10.0f) / 10.0f) : 0.0f;
  doc["waterLevelCm"] = roundf(waterLevelCm * 100.0f) / 100.0f;
  doc["direction"]  = (int)encoderDirection;
  doc["uptimeS"]    = (uint32_t)(millis() / 1000UL);
  doc["freeHeap"]   = (uint32_t)ESP.getFreeHeap();
  doc["seq"]        = ++publishSequence;
  doc["ntpSynced"]  = ntpSynced;
#endif

#if INCLUDE_LEGACY_FIELDS
  // Aliases for the original dashboard field names, in case the web app still
  // reads "waveHeight" / "waveFreq" instead of the *Cm / *Hz names.
  doc["waveHeight"] = roundf(waveHeightToPublish * 100.0f) / 100.0f;
  doc["waveFreq"]   = roundf(waveFreqHz   * 1000.0f) / 1000.0f;
#endif

  // static: keeps a 1 kB buffer off the 8 kB Arduino task stack, which TLS
  // writes also live on.
  static char payload[MQTT_BUFFER_SIZE];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  if (!mqtt.connected()) {
    LOG("[PUB] Skipped - MQTT offline. %s", payload);
    return;
  }

  bool ok = mqtt.publish(MQTT_TELEMETRY_TOPIC, (const uint8_t*)payload, len, false);
  if (ok) {
    LOG("[PUB] OK (%u B) -> %s", (unsigned)len, MQTT_TELEMETRY_TOPIC);
    LOG("      %s", payload);
  } else {
    Serial.printf("[PUB] FAILED (%u B, MQTT state=%d). Payload may exceed the %u B buffer.\n",
                  (unsigned)len, mqtt.state(), (unsigned)MQTT_BUFFER_SIZE);
  }

#if SERIAL_DEBUG
  Serial.printf("[SENSE] V=%.3f V  I=%.3f A  P=%.3f W | wave H=%.2f cm f=%.3f Hz d=%.1f cm | rpm=%.1f | mode=%s\n",
                generatorVoltage, generatorCurrent, generatorPower,
                waveHeightCm, waveFreqHz, distanceCm, rpm, modeName(currentMode));
#endif
}

// ============================================================================
//  Status / acknowledgement publishing
// ============================================================================
void publishAck() {
  JSON_DOC(doc, 256);
  doc["type"]       = "ack";
  doc["relayMode"]  = modeName(currentMode);
  doc["relayState"] = (int)currentMode;
#if INCLUDE_EXTENDED_TELEMETRY
  doc["deviceId"]   = DEVICE_ID;
  doc["ts"]         = isoTimestamp();
#endif

  static char payload[256];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  if (mqtt.connected() &&
      mqtt.publish(MQTT_STATUS_TOPIC, (const uint8_t*)payload, len, false)) {
    Serial.printf("[ACK] %s\n", payload);
  } else {
    Serial.printf("[ACK] publish FAILED (MQTT state=%d): %s\n", mqtt.state(), payload);
  }
}

void publishStatus(bool online) {
  JSON_DOC(doc, 384);
  doc["type"]       = "status";
  doc["deviceId"]   = DEVICE_ID;
  doc["online"]     = online;
  doc["relayMode"]  = modeName(currentMode);
  doc["relayState"] = (int)currentMode;
  doc["ip"]         = WiFi.localIP().toString();
  doc["wifiRssi"]   = (WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : 0;
  doc["ts"]         = isoTimestamp();

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonObject s = doc["sensorStatus"].to<JsonObject>();
#else
  JsonObject s = doc.createNestedObject("sensorStatus");
#endif
  s["ina228"]     = ina228Ok;
  s["ultrasonic"] = ultrasonicOk;
  s["encoder"]    = encoderOk;

  static char payload[384];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  if (mqtt.connected() &&
      mqtt.publish(MQTT_STATUS_TOPIC, (const uint8_t*)payload, len, false)) {
    Serial.printf("[STATUS] %s\n", payload);
  } else {
    Serial.printf("[STATUS] publish FAILED (MQTT state=%d)\n", mqtt.state());
  }
}

// Publishes an error notice. The relay is deliberately NOT touched here.
void publishError(const char* message, const char* detail) {
  JSON_DOC(doc, 384);
  doc["type"]       = "error";
  doc["deviceId"]   = DEVICE_ID;
  doc["message"]    = message;
  if (detail) doc["detail"] = detail;
  doc["relayMode"]  = modeName(currentMode);   // unchanged - proves nothing moved
  doc["relayState"] = (int)currentMode;
  doc["ts"]         = isoTimestamp();

  static char payload[384];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  if (mqtt.connected()) {
    mqtt.publish(MQTT_STATUS_TOPIC, (const uint8_t*)payload, len, false);
  }
  Serial.printf("[ERROR] %s\n", payload);
}

// ============================================================================
//  Helpers
// ============================================================================
// ISO-8601 timestamp with the configured UTC offset, e.g.
// "2026-08-04T20:30:12+05:30". Before NTP syncs, this returns a 1970 date;
// the extended telemetry field "ntpSynced" tells the backend whether to trust it.
String isoTimestamp() {
  time_t utc   = (time_t)timeClient.getEpochTime();     // NTPClient offset = 0
  time_t local = utc + TIMEZONE_OFFSET_SECONDS;

  struct tm tmv;
  gmtime_r(&local, &tmv);

  long off      = TIMEZONE_OFFSET_SECONDS;
  char sign     = (off < 0) ? '-' : '+';
  long offAbs   = (off < 0) ? -off : off;

  char buf[40];
  snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02d%c%02ld:%02ld",
           tmv.tm_year + 1900, tmv.tm_mon + 1, tmv.tm_mday,
           tmv.tm_hour, tmv.tm_min, tmv.tm_sec,
           sign, offAbs / 3600, (offAbs % 3600) / 60);
  return String(buf);
}
