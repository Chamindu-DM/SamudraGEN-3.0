# Grafana Cloud Integration Guide — SamudraGEN 3.0

> **Purpose:** Monitor the SamudraGEN-3.0 ESP32 hardware and AWS infrastructure 24/7 using Grafana Cloud's **Forever Free** tier. Detect hardware failures, sensor anomalies, connectivity drops, and AWS throttling — and get notified via Discord/Slack/Email the moment something goes wrong.

---

## Table of Contents

1. [Why Grafana Cloud (Not Local)?](#1-why-grafana-cloud-not-local)
2. [Grafana Cloud Free Tier — What You Get](#2-grafana-cloud-free-tier--what-you-get)
3. [What Can We Monitor?](#3-what-can-we-monitor)
4. [Integration Architecture](#4-integration-architecture)
5. [⚠️ AWS Free Tier Cost Impact](#5-️-aws-free-tier-cost-impact)
6. [Step-by-Step Implementation](#6-step-by-step-implementation)
7. [Recommended Dashboards](#7-recommended-dashboards)
8. [Alerting & Notifications](#8-alerting--notifications)
9. [Additional Features on the Free Tier](#9-additional-features-on-the-free-tier)
10. [Summary of Next Steps](#10-summary-of-next-steps)

---

## 1. Why Grafana Cloud (Not Local)?

Running Grafana locally on your laptop means:
- ❌ Dashboards only work while your laptop is **on and awake**.
- ❌ Alerts **cannot fire** if the laptop is asleep — so if the ESP32 dies at 3 AM, you won't know until morning.
- ❌ Your teammate cannot access the dashboards from their machine.

**Grafana Cloud** solves all of this:
- ✅ Runs **24/7** in the cloud — no laptop required.
- ✅ Alerts fire around the clock, even while you sleep.
- ✅ Accessible from any browser, any device, by up to 3 team members.
- ✅ **No credit card** required for the Forever Free tier.

---

## 2. Grafana Cloud Free Tier — What You Get

| Feature | Free Tier Allowance | SamudraGEN Usage |
|---------|---------------------|------------------|
| **Metrics** | 10,000 active series | ~7 metrics × 1 device = **7 series** ✅ |
| **Logs** | 50 GB/month ingested | Minimal (optional) ✅ |
| **Traces** | 50 GB/month ingested | Not needed ✅ |
| **Profiles** | 50 GB/month ingested | Not needed ✅ |
| **Alerting** | ✅ Included (unlimited rules) | ~5–10 alert rules ✅ |
| **Retention** | 14 days | Sufficient for 7-day data collection ✅ |
| **Active Users** | 3 users max | Perfect (you + teammate + mentor) ✅ |
| **Dashboards** | Up to 1,000 | We need ~2–3 ✅ |
| **AI Assistant** | ✅ Included | Helps write PromQL queries ✅ |

> [!TIP]
> SamudraGEN uses ~7 metrics from a single ESP32. The free tier allows 10,000 active series — you are using **0.07%** of the limit. You will never hit this cap.

---

## 3. What Can We Monitor?

### A. Hardware & Telemetry Health

| Monitor | What it Catches | Alert Condition |
|---------|----------------|-----------------|
| **Voltage Drops** | Battery dying, power regulator failure | Voltage < 20V for 5 minutes |
| **Sensor Freeze** | A sensor returning the exact same value repeatedly (stuck/broken) | Standard deviation of `waveHeight` = 0 over 15 minutes |
| **Power vs Wave Mismatch** | Mechanical failure — waves are coming but generator isn't producing power | `waveHeight > 0.5m` AND `power < 1W` for 10 minutes |
| **RPM Anomalies** | Generator shaft jammed or slipping | `rpm = 0` while `waveHeight > 0.3m` |
| **Current Spike / Drop** | Short circuit or open circuit in the generator | `current > 5A` (spike) or `current = 0` (open) |
| **Out-of-Range Values** | Broken sensor returning garbage data | `waveHeight > 10m` or `voltage < 0` or `voltage > 50V` |

### B. Device Connectivity

| Monitor | What it Catches | Alert Condition |
|---------|----------------|-----------------|
| **ESP32 Online/Offline** | Wi-Fi dropout, power loss, firmware crash | No data received for 10 minutes |
| **MQTT Lifecycle Events** | Exact connect/disconnect timestamps | `$aws/events/presence/connected/+` and `disconnected/+` |
| **Message Frequency Drop** | ESP32 slowing down (overheating, low memory) | Messages per minute drops below 10 (expected: 12/min at 5s interval) |

### C. AWS Infrastructure Health

| Monitor | What it Catches | Alert Condition |
|---------|----------------|-----------------|
| **IoT Rule Failures** | IoT rule failing to write to DynamoDB | `RuleMessageThrottled` or `Failure` count > 0 |
| **DynamoDB Throttling** | Exceeding free tier read/write capacity | `ThrottledRequests` > 0 |
| **DynamoDB Consumed Capacity** | Approaching free tier WCU/RCU limits | `ConsumedWriteCapacityUnits` approaching 25 |
| **Lambda Errors** | `SamudraGEN-GetHistory` crashing or timing out | `Errors` count > 0 or `Duration` > 10s |
| **Lambda Throttles** | Hitting Lambda concurrency limits | `Throttles` count > 0 |
| **API Gateway 5xx** | REST API returning server errors to the React frontend | `5XXError` count > 0 |
| **API Gateway Latency** | Slow API responses degrading the user experience | `Latency` p99 > 3000ms |

### D. Data Quality Monitoring

| Monitor | What it Catches | Alert Condition |
|---------|----------------|-----------------|
| **Missing Fields** | ESP32 firmware bug sending incomplete JSON | Count of records where a field is `null` |
| **Timestamp Gaps** | Missed publishes or clock drift | Gap between consecutive `ts` values > 15 seconds |
| **Duplicate Data** | IoT rule firing twice or retry storms | Identical `ts` values appearing multiple times |

---

## 4. Integration Architecture

The existing SamudraGEN pipeline sends data from ESP32 → IoT Core → DynamoDB → React Frontend. We add a **second IoT Rule** that mirrors the same telemetry to **Amazon CloudWatch**, which Grafana Cloud queries natively.

```text
                                                       IoT Rule 1 (Existing)
┌─────────┐      ┌──────────────┐    ─────────────────────────────>  ┌────────────┐     REST     ┌──────────┐
│  ESP32  │ ───> │ AWS IoT Core │                                    │  DynamoDB  │ ──> Lambda ─>│ React UI │
│ (OWSC)  │      │  (MQTT)      │                                    └────────────┘              └──────────┘
└─────────┘      └──────┬───────┘
                        │
                        │  IoT Rule 2 (NEW - Grafana)
                        │
                        ▼
                 ┌──────────────┐     CloudWatch       ┌───────────────┐
                 │  CloudWatch  │ <──── Data Source ──> │ Grafana Cloud │
                 │  (Metrics)   │                       │  (Free Tier)  │
                 └──────────────┘                       └───────┬───────┘
                                                                │
                                                         ┌──────▼──────┐
                                                         │   Alerts    │
                                                         │ Discord /   │
                                                         │ Slack /     │
                                                         │ Email       │
                                                         └─────────────┘
```

**Key design decision:** We use CloudWatch as the bridge between AWS and Grafana because:
1. Grafana Cloud has a **built-in CloudWatch plugin** — no extra setup needed.
2. CloudWatch already collects native AWS service metrics (DynamoDB, Lambda, API Gateway) for free.
3. We only need to add **custom metrics** for our telemetry data via a new IoT Rule.

---

## 5. ⚠️ AWS Free Tier Cost Impact

> [!CAUTION]
> Connecting Grafana to AWS CloudWatch **can generate costs** if not configured carefully. This section explains exactly what is free and what is not.

### 5.1 What AWS Gives You for Free (Monthly)

| CloudWatch Resource | Free Tier Allowance | Notes |
|---------------------|---------------------|-------|
| **Custom Metrics** | 10 metrics | We need ~7 (one per telemetry field) ✅ |
| **Standard API Requests** (`PutMetricData`, `ListMetrics`, etc.) | 1,000,000 requests | We use ~120K `PutMetricData` calls/week ✅ |
| **`GetMetricData` API** | ❌ **NOT FREE** | **$0.01 per 1,000 metrics requested** |
| **Standard Alarms** | 10 alarms | We need ~5–8 ✅ |
| **Dashboard API Widgets** | 3 dashboards (50 metrics/dashboard) | Built-in CloudWatch dashboards only |

### 5.2 The Hidden Cost: `GetMetricData` API Calls

When Grafana Cloud queries your CloudWatch metrics, it uses the `GetMetricData` API. This API is **never free** — you pay from the very first call.

**Cost estimation for SamudraGEN:**

| Factor | Value |
|--------|-------|
| Number of dashboard panels | ~6 panels |
| Metrics per panel (average) | ~2 metrics |
| Dashboard auto-refresh interval | Every 60 seconds (recommended) |
| Hours per day the dashboard is open | ~2 hours (realistic estimate) |
| Grafana alert evaluation interval | Every 5 minutes (24/7) |
| Alert rules | ~8 rules |

**Dashboard viewing cost:**
```
6 panels × 2 metrics × 60 refreshes/hr × 2 hrs/day × 30 days
= 43,200 GetMetricData requests/month
= 43.2 × $0.01 = ~$0.43/month
```

**Alert evaluation cost (24/7):**
```
8 rules × 1 metric each × 12 evaluations/hr × 24 hrs × 30 days
= 69,120 GetMetricData requests/month
= 69.12 × $0.01 = ~$0.69/month
```

**Total estimated cost: ~$1.12/month** 💰

> [!IMPORTANT]
> The Grafana integration will cost approximately **$1–2/month** on your AWS bill due to `GetMetricData` API calls. This is NOT covered by the AWS Free Tier. However, it is a very small and predictable cost.

### 5.3 Cost Optimization Tips

To keep costs as low as possible:

1. **Set Grafana dashboard auto-refresh to 5 minutes** (instead of the default 1 minute). This alone reduces dashboard API calls by 80%.
2. **Use Grafana alerting instead of CloudWatch Alarms** where possible. Grafana alerts query CloudWatch but don't require creating paid CloudWatch Alarm resources.
3. **Don't leave dashboards open 24/7** in a browser tab. Alerts will still fire regardless — you only need the dashboard open when actively investigating.
4. **Limit the query time range.** Querying "Last 1 hour" is far cheaper than "Last 7 days" because fewer data points are scanned.

**Optimized cost estimate (5-min refresh, 30 min/day viewing):**
```
Dashboard: 6 × 2 × 12/hr × 0.5 hr/day × 30 = 2,160 requests → $0.02/month
Alerts:    8 × 1 × 12/hr × 24 × 30             = 69,120 requests → $0.69/month
Total: ~$0.71/month
```

### 5.4 Impact on Other AWS Free Tier Services

| Service | Impact from Grafana | Risk |
|---------|---------------------|------|
| **IoT Core Messages** | New IoT Rule publishes a duplicate of every message to CloudWatch. This **doubles** your IoT Core message count from ~121K/week to ~242K/week. Monthly: ~968K vs 250K free limit. | ⚠️ **HIGH RISK** — See mitigation below |
| **DynamoDB** | No impact. Grafana reads from CloudWatch, not DynamoDB. | ✅ None |
| **Lambda** | No impact. Grafana doesn't invoke your Lambda functions. | ✅ None |
| **API Gateway** | No impact. | ✅ None |
| **Cognito** | No impact. | ✅ None |

> [!WARNING]
> **IoT Core Message Doubling Problem:** Adding a second IoT Rule means every ESP32 message triggers TWO rule actions instead of one. At 5-second intervals, you'd use ~968K messages/month, **exceeding the 250K free tier limit** by ~718K messages. This would cost approximately **$0.72/month** at $1.00 per million messages.

### 5.5 Mitigation: Avoid Doubling IoT Core Messages

**Option A — Combine Into a Single IoT Rule (Recommended):**
Instead of creating a second IoT Rule, modify the **existing** `SamudraGEN_SaveTelemetry` rule to have **two actions**:
1. Action 1: DynamoDB (existing)
2. Action 2: CloudWatch Metric (new)

A single rule with multiple actions still counts as **one message**, not two. This completely avoids the doubling problem.

**Option B — Reduce the Publish Interval to 10 Seconds:**
If you prefer separate rules, increase the ESP32 publish interval from 5s to 10s. This halves your message count:
```
2 rules × 8,640 messages/day × 30 days = ~518K messages/month
```
This is still over the 250K limit, so Option A is strongly preferred.

### 5.6 Total Cost Summary

| Cost Item | Monthly Estimate |
|-----------|-----------------|
| Grafana Cloud | **$0.00** (Forever Free tier) |
| CloudWatch `GetMetricData` (Grafana queries) | **~$0.71 – $1.12** |
| IoT Core messages (if using single-rule approach) | **$0.00** (within 250K free tier) |
| CloudWatch Custom Metrics (7 metrics) | **$0.00** (within 10 free metrics) |
| CloudWatch Alarms | **$0.00** (using Grafana alerting instead) |
| **Total** | **~$0.71 – $1.12/month** |

---

## 6. Step-by-Step Implementation

### Step 6.1: Create a Grafana Cloud Account

1. Go to [grafana.com](https://grafana.com/) and click **Create free account**.
2. Sign up with your Google or GitHub account — no credit card required.
3. The Free tier includes 10K metrics, 50 GB logs, alerting, and up to 3 users — more than enough for SamudraGEN.
4. Once logged in, you'll land on your Grafana Cloud dashboard. Note your instance URL (e.g., `https://yourusername.grafana.net`).

### Step 6.2: Add CloudWatch Metrics to the Existing IoT Rule

Instead of creating a new IoT Rule, we modify the existing `SamudraGEN_SaveTelemetry` rule to also push metrics to CloudWatch. This avoids doubling IoT Core message counts.

1. Open **AWS IoT Core** → **Message Routing** → **Rules**.
2. Select the existing rule: `SamudraGEN_SaveTelemetry`.
3. Under **Rule actions**, click **Add action** → select **CloudWatch metric**.
4. Configure **7 separate CloudWatch metric actions**, one for each telemetry field:

| # | Metric Namespace | Metric Name | Metric Value | Unit |
|---|-----------------|-------------|--------------|------|
| 1 | `SamudraGEN/Telemetry` | `voltage` | `${voltage}` | None |
| 2 | `SamudraGEN/Telemetry` | `current` | `${current}` | None |
| 3 | `SamudraGEN/Telemetry` | `power` | `${power}` | None |
| 4 | `SamudraGEN/Telemetry` | `waveHeight` | `${waveHeight}` | None |
| 5 | `SamudraGEN/Telemetry` | `waveFreq` | `${waveFreq}` | None |
| 6 | `SamudraGEN/Telemetry` | `rpm` | `${rpm}` | None |
| 7 | `SamudraGEN/Telemetry` | `deviceId` | `SamudraGEN-ESP32` | None |

> [!NOTE]
> The `deviceId` dimension acts as a label so you can filter by device if you ever add a second ESP32 in the future.

5. For the IAM Role, create a new role `SamudraGEN-IoT-CloudWatch-Role` with the following inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*"
    }
  ]
}
```

6. Save the updated rule.

### Step 6.3: Route ESP32 Lifecycle Events to CloudWatch

To track when the ESP32 goes online or offline:

1. Create a **new** IoT Rule: `SamudraGEN_Device_Status`.
2. **SQL Statement:**
   ```sql
   SELECT
     clientId AS deviceId,
     timestamp() AS eventTimestamp,
     CASE eventType
       WHEN 'connected' THEN 1
       WHEN 'disconnected' THEN 0
     END AS status
   FROM '$aws/events/presence/#'
   ```
3. **Action:** CloudWatch Metric
   - **Namespace:** `SamudraGEN/Lifecycle`
   - **Metric Name:** `DeviceStatus`
   - **Metric Value:** `${status}`

> [!TIP]
> Lifecycle events are very infrequent (only on connect/disconnect), so this rule adds a negligible number of IoT Core messages to your count.

### Step 6.4: Create an IAM User for Grafana

Grafana Cloud needs read-only access to your CloudWatch data:

1. Open **IAM** → **Users** → **Create user**.
2. **User name:** `SamudraGEN-Grafana-ReadOnly`.
3. **Attach policies directly:**
   - `CloudWatchReadOnlyAccess`
4. **Create user** → Go to the user → **Security credentials** → **Create access key**.
5. Select **Third-party service** as the use case.
6. **Download the Access Key ID and Secret Access Key** — you'll enter these into Grafana.

> [!CAUTION]
> Never commit these credentials to Git. Store them securely.

### Step 6.5: Connect Grafana Cloud to AWS CloudWatch

1. Open your Grafana Cloud instance (e.g., `https://yourusername.grafana.net`).
2. Go to **⚙ Configuration** → **Data Sources** → **Add data source**.
3. Search for **Amazon CloudWatch** and select it.
4. Configure:
   - **Auth Provider:** `Access & secret key`
   - **Access Key ID:** (paste from Step 6.4)
   - **Secret Access Key:** (paste from Step 6.4)
   - **Default Region:** `ap-south-1` (or your AWS region)
5. Click **Save & Test** — you should see a green "Data source is working" message.

---

## 7. Recommended Dashboards

Create a new Dashboard in Grafana (Dashboards → New → New Dashboard) and add the following panels.

> [!TIP]
> Set the dashboard **auto-refresh** to **5 minutes** (top-right corner) to minimize AWS API costs.

### Panel 1: System Voltage (Gauge)

- **Visualization:** Gauge
- **Query:** CloudWatch → Namespace: `SamudraGEN/Telemetry` → Metric: `voltage` → Stat: `Average` → Period: `300`
- **Thresholds:**
  - 🟢 Green: > 23V (Healthy)
  - 🟡 Yellow: 20V – 23V (Warning)
  - 🔴 Red: < 20V (Critical)
- **Purpose:** Instant visual cue if the system power supply is failing.

### Panel 2: Power Output vs Wave Height (Time Series — Dual Y-Axis)

- **Visualization:** Time Series
- **Query A:** `power` (Watts) — Left Y-Axis
- **Query B:** `waveHeight` (Meters) — Right Y-Axis
- **Purpose:** The critical "mechanical health" panel. If the blue line (waves) is high but the orange line (power) is flat at zero, the OWSC generator has a **mechanical failure** (shaft jam, belt slip, bearing seizure).

### Panel 3: RPM & Current (Time Series)

- **Visualization:** Time Series
- **Query A:** `rpm` — Left Y-Axis
- **Query B:** `current` (Amps) — Right Y-Axis
- **Purpose:** Correlate generator speed with electrical output. If RPM is high but current is zero, the generator windings may be damaged. If current spikes while RPM drops, something is mechanically resisting rotation.

### Panel 4: ESP32 Online/Offline (State Timeline)

- **Visualization:** State Timeline
- **Query:** CloudWatch → Namespace: `SamudraGEN/Lifecycle` → Metric: `DeviceStatus` → Stat: `Maximum` → Period: `60`
- **Value Mappings:** `1` = "Online" (green), `0` = "Offline" (red)
- **Purpose:** A horizontal bar showing exactly when the device was connected vs disconnected over the past 24 hours. Makes it easy to spot patterns (e.g., "it drops every day at 2 PM" = Wi-Fi congestion).

### Panel 5: Message Rate (Stat + Time Series)

- **Visualization:** Stat (big number) + optional Time Series below
- **Query:** CloudWatch → Namespace: `AWS/IoT` → Metric: `PublishIn.Success` → Stat: `Sum` → Period: `300`
- **Purpose:** Shows how many messages the ESP32 published in the last 5 minutes. Expected: ~60. If it drops to 0, the device is offline. If it's lower than expected (e.g., 30), the ESP32 might be struggling.

### Panel 6: AWS Backend Health (Time Series)

- **Visualization:** Time Series
- **Queries:**
  - `AWS/DynamoDB` → `ConsumedWriteCapacityUnits` (for table `SamudraGEN-Telemetry`)
  - `AWS/DynamoDB` → `ThrottledRequests`
  - `AWS/Lambda` → `Errors` (for function `SamudraGEN-GetHistory`)
  - `AWS/Lambda` → `Duration` (to spot slow queries)
  - `AWS/ApiGateway` → `5XXError`
- **Purpose:** A single panel to monitor the entire AWS backend. If any line spikes, something is broken or throttled.

### Panel 7: Wave Frequency Histogram (Bar Gauge)

- **Visualization:** Bar Gauge or Histogram
- **Query:** `waveFreq` — `Average` over 5 min periods
- **Purpose:** Understand the wave frequency distribution to correlate with power output efficiency. Helps the mechanical engineering team tune the OWSC resonance.

---

## 8. Alerting & Notifications

Grafana Cloud alerting runs **24/7** even when you're not looking at the dashboard. This is the key advantage over running Grafana locally.

### 8.1 Set Up a Contact Point (Where Alerts Go)

1. In Grafana Cloud, go to **Alerting** → **Contact points** → **Add contact point**.
2. Choose your preferred notification channel:

| Channel | How to Set Up |
|---------|---------------|
| **Discord** | Create a webhook in your Discord server (Server Settings → Integrations → Webhooks → New Webhook). Paste the URL in Grafana. |
| **Slack** | Create an Incoming Webhook in your Slack workspace. Paste the URL in Grafana. |
| **Email** | Enter your email address. Grafana Cloud handles SMTP for you — no server config needed. |
| **Telegram** | Create a bot via BotFather, get the chat ID, and enter the bot token in Grafana. |

> [!TIP]
> **Discord is the easiest** — it takes 30 seconds to set up and gives you instant mobile push notifications on your phone.

### 8.2 Recommended Alert Rules

Create these alert rules under **Alerting** → **Alert rules** → **New alert rule**:

#### Alert 1: ESP32 Offline (No Data)
- **Query:** CloudWatch → `SamudraGEN/Telemetry` → `power` → `Sum` → Period: `300`
- **Condition:** `WHEN last() OF query(A, 10m, now) IS 0` or use the **No Data** state (set to `Alerting` after 10 minutes).
- **Severity:** Critical 🔴
- **Message:** `⚠️ SamudraGEN ESP32 has stopped sending data! No telemetry received in the last 10 minutes. Check Wi-Fi, power supply, and device firmware.`

#### Alert 2: Low Voltage
- **Query:** CloudWatch → `SamudraGEN/Telemetry` → `voltage` → `Minimum` → Period: `300`
- **Condition:** `WHEN min() OF query(A, 5m, now) IS BELOW 20`
- **Severity:** Warning 🟡
- **Message:** `🔋 SamudraGEN voltage dropped below 20V (currently: {{ $value }}V). Battery may be dying or the power regulator is failing.`

#### Alert 3: Zero Power Despite Waves
- **Query A:** `waveHeight` → `Average` → Period: `300`
- **Query B:** `power` → `Average` → Period: `300`
- **Condition:** `WHEN avg(A) > 0.5 AND avg(B) < 1.0` for 10 minutes
- **Severity:** Critical 🔴
- **Message:** `🌊⚡ Mechanical failure detected! Wave height is {{ $values.A }}m but power output is only {{ $values.B }}W. The OWSC generator may have a jammed shaft or broken belt.`

#### Alert 4: DynamoDB Throttling
- **Query:** CloudWatch → `AWS/DynamoDB` → `ThrottledRequests` → `Sum` → Period: `300`
- **Condition:** `WHEN sum() OF query(A, 5m, now) IS ABOVE 0`
- **Severity:** Warning 🟡
- **Message:** `🗄️ DynamoDB is throttling requests! You may be exceeding the Free Tier write capacity. Check the SamudraGEN-Telemetry table settings.`

#### Alert 5: Lambda API Errors
- **Query:** CloudWatch → `AWS/Lambda` → `Errors` → `Sum` → Period: `300` → Function: `SamudraGEN-GetHistory`
- **Condition:** `WHEN sum() OF query(A, 5m, now) IS ABOVE 0`
- **Severity:** Warning 🟡
- **Message:** `🔴 Lambda function SamudraGEN-GetHistory is throwing errors! The history API may be returning 500s to the React frontend.`

#### Alert 6: Sensor Anomaly (Out-of-Range)
- **Query:** `voltage` → `Maximum` → Period: `60`
- **Condition:** `WHEN max() IS ABOVE 50` OR `WHEN min() IS BELOW 0`
- **Severity:** Critical 🔴
- **Message:** `📡 Sensor anomaly detected! Voltage reading is out of expected range (0–50V). The sensor may be damaged or returning garbage data.`

---

## 9. Additional Features on the Free Tier

These are extra capabilities you can leverage at no additional cost:

### 9.1 Annotations (Event Markers)

You can manually or programmatically add **annotations** to your time-series charts to mark significant events:
- "Deployed firmware v2.1"
- "Moved device to new wave tank location"
- "Started 7-day data collection"

This creates vertical markers on all your graphs so you can correlate changes in telemetry with real-world actions.

**How:** Dashboard → Panel → Edit → Annotations → Add annotation query → Manual or via the Grafana HTTP API.

### 9.2 Dashboard Variables (Filters)

Add dropdown filters at the top of your dashboard:
- **Time range presets:** "Last 1 hour", "Last 6 hours", "Today"
- **Device ID filter:** Useful if you ever add a second ESP32

**How:** Dashboard Settings → Variables → Add variable → Type: `Custom` or `Query`.

### 9.3 Dashboard Playlists

Set up a **playlist** that automatically cycles through multiple dashboards (e.g., Telemetry → AWS Health → Connectivity) on a TV or monitor in your lab.

**How:** Dashboards → Playlists → New playlist → Add dashboards → Set rotation interval.

### 9.4 Dashboard Snapshots (Sharing)

Share a **read-only snapshot** of your dashboard with your mentor or supervisor without giving them a Grafana account. Snapshots capture the current state of all panels.

**How:** Dashboard → Share → Snapshot → Publish to snapshots.raintank.io → Copy the link.

### 9.5 Log Exploration (Optional)

If you want to go beyond metrics, you can also send raw JSON telemetry payloads as **logs** to Grafana Cloud's Loki backend. This lets you:
- Search through raw payloads using text queries
- Correlate log entries with metric spikes
- Keep a detailed audit trail of every single message

This would require an additional Lambda function that forwards IoT messages to Grafana Cloud's Loki push API. For the prototype, metrics are sufficient.

### 9.6 Grafana AI Assistant

The free tier includes access to Grafana's **AI Assistant** which can:
- Help you write CloudWatch metric queries
- Explain anomalies in your data
- Suggest alert thresholds based on historical patterns

**How:** Click the AI Assistant icon (✨) in any panel editor.

---

## 10. Summary of Next Steps

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | **Create Grafana Cloud account** at [grafana.com](https://grafana.com/) | 2 minutes |
| 2 | **Modify existing IoT Rule** `SamudraGEN_SaveTelemetry` to add CloudWatch metric actions | 15 minutes |
| 3 | **Create Lifecycle IoT Rule** `SamudraGEN_Device_Status` for connect/disconnect events | 10 minutes |
| 4 | **Create IAM User** `SamudraGEN-Grafana-ReadOnly` with `CloudWatchReadOnlyAccess` | 5 minutes |
| 5 | **Connect Grafana Cloud** to CloudWatch as a data source | 5 minutes |
| 6 | **Build Dashboards** (7 panels as described in Section 7) | 30 minutes |
| 7 | **Set up Discord/Slack Contact Point** for alert notifications | 5 minutes |
| 8 | **Create 6 Alert Rules** (as described in Section 8.2) | 20 minutes |
| | **Total estimated setup time** | **~1.5 hours** |

---

## Quick Reference: New AWS Resources

| Resource | Name | Service |
|----------|------|---------|
| IoT Rule Action (modified) | `SamudraGEN_SaveTelemetry` + CloudWatch actions | IoT Core |
| IoT Rule (new) | `SamudraGEN_Device_Status` | IoT Core |
| IAM Role | `SamudraGEN-IoT-CloudWatch-Role` | IAM |
| IAM User | `SamudraGEN-Grafana-ReadOnly` | IAM |
| CloudWatch Namespace | `SamudraGEN/Telemetry` | CloudWatch |
| CloudWatch Namespace | `SamudraGEN/Lifecycle` | CloudWatch |
