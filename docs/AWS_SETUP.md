# AWS Setup Guide — SamudraGEN 3.0

> **Target:** AWS Free Tier account · One-week continuous sea-data collection from an ESP32-based OWSC prototype.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Free Tier Budget Estimation](#2-free-tier-budget-estimation)
3. [Step 1 — AWS IoT Core (MQTT Broker)](#3-step-1--aws-iot-core-mqtt-broker)
4. [Step 2 — DynamoDB (Telemetry Storage)](#4-step-2--dynamodb-telemetry-storage)
5. [Step 3 — IoT Rule (Auto-Save to DynamoDB)](#5-step-3--iot-rule-auto-save-to-dynamodb)
6. [Step 4 — Lambda Function (History API)](#6-step-4--lambda-function-history-api)
7. [Step 5 — API Gateway (REST Endpoint)](#7-step-5--api-gateway-rest-endpoint)
8. [Step 6 — Cognito (Browser Auth for WebSocket)](#8-step-6--cognito-browser-auth-for-websocket)
9. [ESP32 Firmware Configuration](#9-esp32-firmware-configuration)
10. [Frontend Environment Variables](#10-frontend-environment-variables)
11. [Testing the Full Pipeline](#11-testing-the-full-pipeline)
12. [Cleanup After Data Collection](#12-cleanup-after-data-collection)

---

## 1. Architecture Overview

```
┌─────────┐      Wi-Fi       ┌──────────────────┐     IoT Rule     ┌────────────┐
│  ESP32  │ ──── MQTT ──────>│  AWS IoT Core    │ ────────────────>│  DynamoDB  │
│ (OWSC)  │                  │  (Message Broker)│                  │  (Storage) │
└─────────┘                  └────────┬─────────┘                  └─────┬──────┘
                                      │ WebSocket                        │
                                      │ (wss://)                         │
                              ┌───────▼────────┐                  ┌──────▼──────┐
                              │  Browser SPA   │ <── REST API ──  │   Lambda    │
                              │ (SamudraGEN)   │                  │  (History)  │
                              └───────┬────────┘                  └──────▲──────┘
                                      │                                  │
                              ┌───────▼────────┐                  ┌──────┴──────┐
                              │    Cognito     │                  │ API Gateway │
                              │  (Identity)    │                  │   (REST)    │
                              └────────────────┘                  └─────────────┘
```

**Data flows in two parallel paths:**

| Path | Purpose | Latency |
|------|---------|---------|
| ESP32 → IoT Core → Browser (WebSocket) | Live digital twin & charts | ~50–200 ms |
| ESP32 → IoT Core → DynamoDB → Lambda → Browser (REST) | Historical playback & analysis | On-demand |

---

## 2. Free Tier Budget Estimation

The following calculations assume a **publish interval of 5 seconds** from the ESP32, running for **7 consecutive days**.

| Metric | Calculation | Total |
|--------|-------------|-------|
| Messages per day | 86 400 s ÷ 5 s = **17 280** | — |
| Messages per week | 17 280 × 7 | **120 960** |
| Payload size (approx.) | ~120 bytes per JSON message | — |
| DynamoDB storage per week | 120 960 × 120 B | **~14.5 MB** |

### Free Tier Limits (first 12 months)

| Service | Free Allowance | Our Usage | Status |
|---------|---------------|-----------|--------|
| **IoT Core** | 250 000 messages/month | ~120 960/week | ✅ Well within |
| **DynamoDB** | 25 GB storage, 25 WCU, 25 RCU (always free) | ~14.5 MB, ~1 WCU | ✅ Well within |
| **Lambda** | 1 000 000 requests/month, 400 000 GB-s | Minimal (on-demand queries) | ✅ Well within |
| **API Gateway** | 1 000 000 calls/month (12 months) | Minimal | ✅ Well within |
| **Cognito** | 50 000 MAUs (always free) | 1–5 users | ✅ Well within |

> [!TIP]
> At 5-second intervals, the entire one-week collection fits comfortably within the free tier. **Do not go below 2-second intervals** or you risk exceeding the 250K IoT Core message limit mid-month.

---

## 3. Step 1 — AWS IoT Core (MQTT Broker)

This creates the MQTT endpoint the ESP32 publishes to, and the browser subscribes to.

### 3.1 Create a Thing

1. Open the **AWS Console** → search **IoT Core** → select your region (e.g., `ap-south-1` Mumbai).
2. Go to **Manage → All devices → Things** → **Create things**.
3. Choose **Create single thing**.
4. Name: `SamudraGEN-ESP32`.
5. Leave *Thing type* and *Thing group* empty → **Next**.

### 3.2 Generate Certificates

1. Select **Auto-generate a new certificate (recommended)** → **Next**.
2. Skip the policy for now (we will create one next) → **Create thing**.
3. **Download all four files** on the certificate screen:
   - `<id>-certificate.pem.crt` (Device certificate)
   - `<id>-private.pem.key` (Private key)
   - `<id>-public.pem.key` (Public key — optional but keep it)
   - `AmazonRootCA1.pem` (Root CA)
4. Click **Done**. **You cannot re-download the private key after this step.**

### 3.3 Create and Attach a Policy

1. Go to **Security → Policies** → **Create policy**.
2. Name: `SamudraGEN-ESP32-Policy`.
3. Switch to **JSON** mode and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:<REGION>:<ACCOUNT_ID>:client/SamudraGEN-ESP32"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/ocean/wave/telemetry"
    }
  ]
}
```

4. Replace `<REGION>` and `<ACCOUNT_ID>` with your values.
5. **Create** the policy.
6. Go to **Security → Certificates** → select the certificate you just created → **Actions → Attach policy** → select `SamudraGEN-ESP32-Policy`.

### 3.4 Get Your IoT Endpoint

1. Go to **IoT Core → Settings** (bottom of left sidebar).
2. Copy the **Device data endpoint** — it looks like:
   ```
   a1b2c3d4e5f6g7-ats.iot.ap-south-1.amazonaws.com
   ```
3. Save this — the ESP32 and the browser will both connect to this URL.

---

## 4. Step 2 — DynamoDB (Telemetry Storage)

### 4.1 Create the Table

1. Open **DynamoDB** → **Create table**.
2. Configure:
   - **Table name:** `SamudraGEN-Telemetry`
   - **Partition key:** `date` (String) — stores the date, e.g., `2026-07-19`
   - **Sort key:** `ts` (String) — stores the timestamp, e.g., `10:30:12`
3. Under **Table settings**, select **Customize settings**.
4. **Read/write capacity settings:** choose **On-demand** (scales to zero when idle — best for bursty IoT workloads on free tier).

   > [!NOTE]
   > On-demand mode is included in the free tier for the first 12 months (25 WRU and 25 RRU). For this project's volume (~0.2 writes/sec average), on-demand is the safest choice.

5. Click **Create table**.

### 4.2 Enable TTL (Auto-Delete Old Data)

To avoid accumulating data beyond your needs and to keep storage minimal:

1. Open the `SamudraGEN-Telemetry` table → **Additional settings** tab.
2. Under **Time to Live (TTL)**, click **Turn on**.
3. **TTL attribute name:** `expireAt`
4. Your IoT Rule (next step) will set `expireAt` to a Unix timestamp 14 days from ingestion.

---

## 5. Step 3 — IoT Rule (Auto-Save to DynamoDB)

This automatically routes every message from the ESP32 into DynamoDB.

### 5.1 Create an IAM Role for IoT Rules

1. Open **IAM** → **Roles** → **Create role**.
2. **Trusted entity:** AWS service → **IoT**.
3. **Use case:** IoT (select the one under IoT, not IoT Greengrass).
4. Attach policy: **AmazonDynamoDBFullAccess** (for simplicity on a prototype — scope down later).
5. Role name: `SamudraGEN-IoT-DynamoDB-Role`.
6. **Create role**.

### 5.2 Create the IoT Rule

1. Open **IoT Core** → **Message routing → Rules** → **Create rule**.
2. **Rule name:** `SamudraGEN_SaveTelemetry`
3. **SQL statement:**

```sql
SELECT
  timestamp()                          AS ingestionTimestamp,
  parse_time("yyyy-MM-dd", timestamp()) AS date,
  ts,
  waveHeight,
  waveFreq,
  rpm,
  power,
  voltage,
  current,
  (timestamp() / 1000) + 1209600      AS expireAt
FROM
  'ocean/wave/telemetry'
```

> The `+ 1209600` adds 14 days in seconds, used for the DynamoDB TTL auto-delete.

4. **Rule actions** → **Add action** → **DynamoDBv2 (Split message into table columns)**.
5. Configure:
   - **Table name:** `SamudraGEN-Telemetry`
   - **IAM Role:** `SamudraGEN-IoT-DynamoDB-Role`
6. **Create rule**.

---

## 6. Step 4 — Lambda Function (History API)

This function queries DynamoDB to return historical telemetry for a given date.

### 6.1 Create the Function

1. Open **Lambda** → **Create function**.
2. **Author from scratch**.
3. Configure:
   - **Function name:** `SamudraGEN-GetHistory`
   - **Runtime:** Node.js 22.x
   - **Architecture:** arm64 (Graviton — more free-tier-friendly)
4. **Create function**.

### 6.2 Add the Code

Replace the default code with:

```javascript
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = "SamudraGEN-Telemetry";

// CORS headers — adjust origin for production
const HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export const handler = async (event) => {
  // Handle CORS preflight
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: HEADERS, body: "" };
  }

  const date = event.queryStringParameters?.date;

  if (!date) {
    return {
      statusCode: 400,
      headers: HEADERS,
      body: JSON.stringify({ error: "Missing 'date' query parameter (YYYY-MM-DD)" }),
    };
  }

  try {
    const result = await docClient.send(
      new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: "#d = :date",
        ExpressionAttributeNames: { "#d": "date" },
        ExpressionAttributeValues: { ":date": date },
        ScanIndexForward: true, // oldest first
      })
    );

    return {
      statusCode: 200,
      headers: HEADERS,
      body: JSON.stringify({
        date,
        count: result.Items.length,
        records: result.Items,
      }),
    };
  } catch (err) {
    console.error("DynamoDB query failed:", err);
    return {
      statusCode: 500,
      headers: HEADERS,
      body: JSON.stringify({ error: "Internal server error" }),
    };
  }
};
```

5. Click **Deploy**.

### 6.3 Grant DynamoDB Read Access

1. In the Lambda function page, go to **Configuration → Permissions**.
2. Click the **Role name** link (opens IAM).
3. **Add permissions → Attach policies** → attach `AmazonDynamoDBReadOnlyAccess`.

---

## 7. Step 5 — API Gateway (REST Endpoint)

### 7.1 Create the API

1. Open **API Gateway** → **Create API** → **REST API** (not private) → **Build**.
2. **API name:** `SamudraGEN-API`.
3. **Create API**.

### 7.2 Create the Resource & Method

1. **Actions → Create Resource**.
   - Resource path: `/`
   - Resource name: `history`
   - Enable **CORS**.
2. Select the `/history` resource → **Actions → Create Method** → **GET**.
3. Configure:
   - **Integration type:** Lambda Function
   - **Lambda Function:** `SamudraGEN-GetHistory`
   - **Use Lambda Proxy integration:** ✅ Check this
4. **Save** → Confirm Lambda permission prompt.

### 7.3 Enable CORS

1. Select `/history` resource → **Actions → Enable CORS**.
2. Accept defaults → **Enable CORS and replace existing CORS headers**.

### 7.4 Deploy

1. **Actions → Deploy API**.
2. **Stage name:** `prod`.
3. Note your **Invoke URL**:
   ```
   https://abc123xyz.execute-api.ap-south-1.amazonaws.com/prod
   ```

Your history endpoint is now live at:
```
GET https://abc123xyz.execute-api.ap-south-1.amazonaws.com/prod/history?date=2026-07-19
```

---

## 8. Step 6 — Cognito (Browser Auth for WebSocket)

The browser SPA needs temporary AWS credentials to connect to IoT Core over WebSocket. Cognito Identity Pools provide this without requiring user login.

### 8.1 Create an Identity Pool

1. Open **Cognito** → **Identity pools** (not User pools) → **Create identity pool**.
2. **Identity pool name:** `SamudraGEN-Browser`
3. **User access:** select **Guest access** (unauthenticated).
4. Under **Permissions**, create a new IAM role:
   - **Role name:** `SamudraGEN-Cognito-Unauth-Role`
5. **Create identity pool**.
6. Copy the **Identity Pool ID** — looks like:
   ```
   ap-south-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

### 8.2 Attach IoT Permissions to the Unauth Role

1. Open **IAM → Roles** → find `SamudraGEN-Cognito-Unauth-Role`.
2. **Add permissions → Create inline policy** → JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Connect",
        "iot:Subscribe",
        "iot:Receive"
      ],
      "Resource": "*"
    }
  ]
}
```

> [!WARNING]
> The `Resource: "*"` is acceptable for a prototype. For production, scope it to your specific IoT client ID and topic ARN.

3. Policy name: `SamudraGEN-IoT-Subscribe-Policy` → **Create policy**.

---

## 9. ESP32 Firmware Configuration

Flash the downloaded certificates onto the ESP32's filesystem (SPIFFS/LittleFS). Your Arduino/PlatformIO sketch needs these constants:

```cpp
// ── AWS IoT Configuration ──────────────────────────────
const char* AWS_IOT_ENDPOINT = "a1b2c3d4e5f6g7-ats.iot.ap-south-1.amazonaws.com";
const int   AWS_IOT_PORT     = 8883;        // MQTT over TLS
const char* MQTT_TOPIC       = "ocean/wave/telemetry";
const char* CLIENT_ID        = "SamudraGEN-ESP32";

// Publish interval (keep ≥ 5s to stay within free tier)
const unsigned long PUBLISH_INTERVAL_MS = 5000;
```

The ESP32 publishes JSON payloads to `ocean/wave/telemetry` on every interval:

```cpp
String payload = "{";
payload += "\"ts\":\"" + getTimeString() + "\",";
payload += "\"waveHeight\":" + String(waveHeight, 2) + ",";
payload += "\"waveFreq\":" + String(waveFreq, 2) + ",";
payload += "\"rpm\":" + String(rpm) + ",";
payload += "\"power\":" + String(power, 1) + ",";
payload += "\"voltage\":" + String(voltage, 1) + ",";
payload += "\"current\":" + String(current, 1);
payload += "}";

mqttClient.publish(MQTT_TOPIC, payload.c_str());
```

---

## 10. Frontend Environment Variables

Create a `.env` file in the project root (already listed in `.gitignore`):

```env
# AWS IoT Core WebSocket Endpoint
VITE_AWS_IOT_ENDPOINT=a1b2c3d4e5f6g7-ats.iot.ap-south-1.amazonaws.com
VITE_AWS_REGION=ap-south-1

# Cognito Identity Pool (for unauthenticated WebSocket access)
VITE_COGNITO_IDENTITY_POOL_ID=ap-south-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# MQTT Topic
VITE_MQTT_TOPIC=ocean/wave/telemetry

# API Gateway (History endpoint)
VITE_HISTORY_API_URL=https://abc123xyz.execute-api.ap-south-1.amazonaws.com/prod/history
```

> [!IMPORTANT]
> Never commit credentials or `.env` files to Git. Verify that `.env` is included in your `.gitignore`.

---

## 11. Testing the Full Pipeline

### 11.1 Test MQTT from the AWS Console

1. Open **IoT Core** → **MQTT test client**.
2. Subscribe to `ocean/wave/telemetry`.
3. Publish a test message:

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

4. Verify the message appears in the subscription panel.

### 11.2 Verify DynamoDB Ingestion

1. Wait a few seconds after publishing the test message.
2. Open **DynamoDB** → **Tables** → `SamudraGEN-Telemetry` → **Explore table items**.
3. Confirm the test record appears with the correct `date` and `ts` keys.

### 11.3 Test the History API

```bash
curl "https://abc123xyz.execute-api.ap-south-1.amazonaws.com/prod/history?date=2026-07-19"
```

Expected response:

```json
{
  "date": "2026-07-19",
  "count": 1,
  "records": [
    {
      "date": "2026-07-19",
      "ts": "10:30:12",
      "waveHeight": 1.55,
      "waveFreq": 0.25,
      "rpm": 120,
      "power": 24.0,
      "voltage": 24.1,
      "current": 1.0
    }
  ]
}
```

### 11.4 Test the Browser SPA

1. Start the dev server: `npm run dev`
2. Open the dashboard in the browser.
3. The **LIVE** badge in the header should turn green when the WebSocket connects.
4. Publish another test message from the IoT Core console and confirm the charts update.

---

## 12. Cleanup After Data Collection

After your one-week data collection is complete, clean up to avoid unexpected charges:

| Action | How |
|--------|-----|
| **Disable the IoT Rule** | IoT Core → Rules → `SamudraGEN_SaveTelemetry` → Disable |
| **Disconnect ESP32** | Power off or reflash the device |
| **Export DynamoDB data** (optional) | Use the DynamoDB Export to S3 feature, or query via Lambda |
| **Delete resources** | Delete in this order: API Gateway → Lambda → IoT Rule → IoT Thing/Certs → DynamoDB table → Cognito Identity Pool |

> [!CAUTION]
> The DynamoDB TTL will auto-delete records 14 days after ingestion. If you need the data longer, export it before the TTL expires or remove the TTL attribute.

---

## Quick Reference: All Resource Names

| Resource | Name | Service |
|----------|------|---------|
| IoT Thing | `SamudraGEN-ESP32` | IoT Core |
| IoT Policy | `SamudraGEN-ESP32-Policy` | IoT Core |
| IoT Rule | `SamudraGEN_SaveTelemetry` | IoT Core |
| DynamoDB Table | `SamudraGEN-Telemetry` | DynamoDB |
| Lambda Function | `SamudraGEN-GetHistory` | Lambda |
| API Gateway | `SamudraGEN-API` | API Gateway |
| Cognito Identity Pool | `SamudraGEN-Browser` | Cognito |
| IAM Role (IoT → DynamoDB) | `SamudraGEN-IoT-DynamoDB-Role` | IAM |
| IAM Role (Cognito Unauth) | `SamudraGEN-Cognito-Unauth-Role` | IAM |
