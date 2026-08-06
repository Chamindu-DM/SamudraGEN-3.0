# Grafana Integration Guide — SamudraGEN 3.0

> **Purpose:** To monitor the SamudraGEN-3.0 hardware and AWS infrastructure, visualize telemetry in real-time, detect anomalies, and trigger alerts when things go wrong (e.g., hardware failure, AWS throttling).

---

## Table of Contents

1. [What Can We Monitor with Grafana?](#1-what-can-we-monitor-with-grafana)
2. [Integration Architecture](#2-integration-architecture)
3. [Step-by-Step Implementation](#3-step-by-step-implementation)
4. [Recommended Dashboards](#4-recommended-dashboards)
5. [Alerting & Notifications](#5-alerting--notifications)

---

## 1. What Can We Monitor with Grafana?

Grafana excels at time-series visualization and alerting. For SamudraGEN-3.0, you can implement the following monitoring use cases:

### A. Hardware & Telemetry Monitoring
- **Sensor Freezes / Disconnects:** Detect if the ESP32 stops sending data or if values remain completely static (indicating a sensor failure).
- **Voltage Drops:** Monitor the internal battery/system voltage and alert if it drops below a safe operational threshold.
- **Power Efficiency Anomalies:** Detect scenarios where **Wave Height is High** but **Power Output is Low**, indicating mechanical failure in the OWSC (Oscillating Wave Surge Converter).

### B. Device Connectivity (Lifecycle Events)
- **Online/Offline Status:** Track exactly when the ESP32 connects and disconnects from AWS IoT Core using MQTT lifecycle events (`$aws/events/presence/connected/+`).

### C. AWS Infrastructure Health
- **IoT Rule Failures:** Monitor if AWS IoT rules fail to insert data into DynamoDB.
- **DynamoDB Throttling:** Track Read/Write Capacity Unit (RCU/WCU) usage to ensure you aren't hitting Free Tier limits.
- **Lambda Errors:** Monitor the `SamudraGEN-GetHistory` Lambda function for timeouts or 5xx errors.

---

## 2. Integration Architecture

Currently, SamudraGEN-3.0 routes data from the ESP32 to AWS IoT Core and saves it to **DynamoDB**. While Grafana *can* query DynamoDB using an enterprise plugin, the industry standard for IoT telemetry in Grafana is to route time-series data to **Amazon CloudWatch** or **Amazon Timestream**.

**Recommended Dual-Database Architecture:**
1. **DynamoDB** (Existing): Continues to serve the SamudraGEN React Frontend for fast historical lookups.
2. **Amazon CloudWatch** (New): Receives a copy of the telemetry for Grafana's heavy analytical queries, dashboards, and alerting without incurring heavy costs.

```text
┌─────────┐      ┌──────────────┐     IoT Rule 1     ┌────────────┐     REST     ┌──────────┐
│  ESP32  │ ───> │ AWS IoT Core │ ─────────────────> │  DynamoDB  │ ──> Lambda ─>│ React UI │
└─────────┘      └──────┬───────┘                    └────────────┘              └──────────┘
                        │
                        │ IoT Rule 2 (NEW)           ┌────────────┐     Query    ┌──────────┐
                        └──────────────────────────> │ CloudWatch │ <─────────── │ Grafana  │
                                                     └────────────┘              └──────────┘
```

---

## 3. Step-by-Step Implementation

### Step 3.1: Choose Your Grafana Hosting (Grafana Cloud)
To ensure 24/7 monitoring and alerting without keeping your local computer running, we will use **Grafana Cloud's "Forever Free" tier**.

1. Go to [grafana.com](https://grafana.com/) and create a free account.
2. The Free tier includes 10k metrics, 50GB logs, and supports up to 3 users—perfect for the SamudraGEN prototype.
3. Once logged in, launch your Grafana Cloud instance. You won't need to install anything locally.

### Step 3.2: Route Telemetry to CloudWatch Metrics
CloudWatch is natively supported by Grafana and requires no extra plugins.

1. Go to **AWS IoT Core** -> **Message Routing** -> **Rules**.
2. Click **Create Rule** (Name: `SamudraGEN_Grafana_Metrics`).
3. **SQL Statement:**
   ```sql
   SELECT * FROM 'ocean/wave/telemetry'
   ```
4. **Rule Actions:** Add action -> **CloudWatch metrics**.
5. Configure the action to extract numeric fields (`voltage`, `power`, `waveHeight`, etc.) and send them to the `SamudraGEN/Telemetry` namespace.
6. Create or assign an IAM Role `SamudraGEN-IoT-CloudWatch-Role` allowing IoT Core to put metric data to CloudWatch.

### Step 3.3: Route ESP32 Connectivity Events
To know when the ESP32 goes offline:
1. Create a new IoT Rule: `SamudraGEN_Device_Status`.
2. **SQL Statement:**
   ```sql
   SELECT * FROM '$aws/events/presence/#'
   ```
3. **Action:** Send to CloudWatch Metrics (Namespace: `SamudraGEN/Lifecycle`, Metric Name: `Status`, Value: `1` for connected, `0` for disconnected).

### Step 3.4: Connect Grafana Cloud to AWS
1. Open your Grafana Cloud dashboard.
2. Go to **Configuration (Gear icon)** -> **Data Sources** -> **Add Data Source**.
3. Search for **Amazon CloudWatch** and select it.
4. **Authentication:** 
   - Create an IAM User in AWS with `CloudWatchReadOnlyAccess`.
   - Generate an Access Key and Secret Key for this user.
   - Enter these credentials into Grafana under **Auth Provider: Access & secret key**.
5. Set the Default Region to your AWS region (e.g., `ap-south-1`) and click **Save & Test**.

---

## 4. Recommended Dashboards

Create a new Dashboard in Grafana and add the following panels:

### Panel 1: System Health (Stat / Gauge)
- **Metric:** `voltage` (from CloudWatch).
- **Thresholds:** Green ( > 23V ), Yellow ( 20V - 23V ), Red ( < 20V ).
- **Purpose:** Immediate visual cue if the system battery is dying.

### Panel 2: Power Generation vs Wave Height (Time Series)
- **Metrics:** Add two queries to the same chart — `power` (Watts) and `waveHeight` (Meters).
- **Axes:** Use a Dual Y-Axis so Wave Height (0-3m) doesn't flatten the Power (0-100W) line.
- **Purpose:** Monitor mechanical efficiency. If waves are high but power is 0, the generator has a mechanical failure.

### Panel 3: Device Uptime (State Timeline)
- **Metric:** `Status` (from the Lifecycle rule).
- **Visualization:** State Timeline.
- **Purpose:** Visually track exactly when the ESP32 dropped off the Wi-Fi or lost power throughout the day.

### Panel 4: AWS Backend Health (Time Series)
- **Data Source:** CloudWatch (Native AWS Metrics).
- **Query 1:** `AWS/DynamoDB` -> `ConsumedReadCapacityUnits` & `ConsumedWriteCapacityUnits`.
- **Query 2:** `AWS/Lambda` -> `Errors` for `SamudraGEN-GetHistory`.
- **Purpose:** Ensure you are not being rate-limited by AWS Free Tier limits and that your backend REST API is functioning.

---

## 5. Alerting & Notifications

Grafana can actively notify you when things go wrong so you don't have to manually stare at the dashboard.

### How to Set Up an Alert:
1. Go to **Alerting** in the Grafana sidebar -> **Alert rules** -> **New alert rule**.
2. **Condition 1 (Low Voltage Warning):**
   - Query the `voltage` metric.
   - Set condition: `WHEN min() OF query(A, 5m, now) IS BELOW 20.0`
   - *Meaning:* If the voltage drops below 20V for 5 continuous minutes, trigger the alert.
3. **Condition 2 (No Data / Disconnect):**
   - Query the `power` metric.
   - Set condition: `WHEN count() OF query(A, 10m, now) IS 0` (or configure Grafana's built-in `No Data` handling state).
   - *Meaning:* If no telemetry is received for 10 minutes, assume the ESP32 is offline.

### Contact Points (Where alerts go)
1. Go to **Alerting** -> **Contact points**.
2. Add a new contact point:
   - **Discord/Slack:** Paste a webhook URL from your Discord server or Slack workspace. Grafana will send a formatted message instantly tagging you when the ESP32 fails.
   - **Email:** Configure SMTP settings to receive email alerts.

---

## Summary of Next Steps
1. **AWS Setup:** Create the new AWS IoT Rules to forward telemetry and `$aws/events/presence/#` to CloudWatch Metrics.
2. **IAM Setup:** Create an IAM User for Grafana read-only access.
3. **Grafana Setup:** Create a free Grafana Cloud account and connect CloudWatch as a Data Source.
4. **Dashboards:** Build the dashboards to track Voltage, Power vs Waves, and Uptime.
5. **Alerts:** Setup Discord/Slack Webhook alerts for "No Data" and "Low Voltage" scenarios.
