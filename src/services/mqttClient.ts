import { useTelemetryStore, type TelemetryTick } from '../store/telemetryStore';
import { mqtt, auth, io, iot } from 'aws-iot-device-sdk-v2/dist/browser';
import { CognitoIdentityClient, GetIdCommand, GetCredentialsForIdentityCommand } from '@aws-sdk/client-cognito-identity';

let connection: mqtt.MqttClientConnection | null = null;
let isConnecting = false;

function extractHHMMSS(isoString: string): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return new Date().toLocaleTimeString('en-US', { hour12: false });
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    const s = String(d.getSeconds()).padStart(2, '0');
    return `${h}:${m}:${s}`;
  } catch (err) {
    return new Date().toLocaleTimeString('en-US', { hour12: false });
  }
}

export async function connectMqttClient() {
  if (connection || isConnecting) return; // Already connected or connecting
  isConnecting = true;

  const endpoint = import.meta.env.VITE_AWS_IOT_ENDPOINT;
  const region = import.meta.env.VITE_AWS_REGION;
  const identityPoolId = import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID;
  const topic = import.meta.env.VITE_MQTT_TOPIC || 'ocean/wave/telemetry';

  if (!endpoint || !region || !identityPoolId) {
    console.error("MQTT Client: Missing AWS IoT endpoint, region, or Identity Pool ID in .env");
    return;
  }

  try {
    console.log("[MQTT] Fetching Cognito credentials...");
    const cognitoClient = new CognitoIdentityClient({ region });
    
    // 1. Get Identity ID
    const getIdCmd = new GetIdCommand({ IdentityPoolId: identityPoolId });
    const idResponse = await cognitoClient.send(getIdCmd);
    const identityId = idResponse.IdentityId;

    if (!identityId) throw new Error("Failed to get Cognito Identity ID");

    // 2. Get Credentials for Identity
    const getCredsCmd = new GetCredentialsForIdentityCommand({ IdentityId: identityId });
    const credsResponse = await cognitoClient.send(getCredsCmd);
    const credentials = credsResponse.Credentials;

    if (!credentials || !credentials.AccessKeyId || !credentials.SecretKey) {
      throw new Error("Failed to get AWS credentials from Cognito");
    }

    console.log("[MQTT] Credentials obtained, creating WebSocket connection...");

    const provider = new auth.StaticCredentialProvider({
      aws_access_id: credentials.AccessKeyId,
      aws_secret_key: credentials.SecretKey,
      aws_sts_token: credentials.SessionToken,
      aws_region: region
    });

    const clientBootstrap = new io.ClientBootstrap();
    const configBuilder = iot.AwsIotMqttConnectionConfigBuilder.new_builder_for_websocket()
        .with_endpoint(endpoint)
        .with_credential_provider(provider)
        .with_client_id(`web-client-${Math.random().toString(36).substring(2, 8)}`);

    const config = configBuilder.build();
    const client = new mqtt.MqttClient(clientBootstrap);
    connection = client.new_connection(config);

    connection.on('connect', () => {
      console.log("[MQTT] Connected to AWS IoT Core");
      useTelemetryStore.getState().setConnected(true);
    });

    connection.on('interrupt', (error) => {
      console.log("[MQTT] Connection interrupted:", error);
      useTelemetryStore.getState().setConnected(false);
    });

    connection.on('resume', (returnCode, sessionPresent) => {
      console.log(`[MQTT] Connection resumed (return code: ${returnCode}, session present: ${sessionPresent})`);
      useTelemetryStore.getState().setConnected(true);
      // Resubscribe if session is not present
      if (!sessionPresent) {
        connection?.subscribe(topic, mqtt.QoS.AtLeastOnce);
      }
    });

    connection.on('disconnect', () => {
      console.log("[MQTT] Disconnected");
      useTelemetryStore.getState().setConnected(false);
    });

    connection.on('message', (_receivedTopic, payload) => {
      try {
        const messageStr = new TextDecoder("utf-8").decode(payload);
        const data = JSON.parse(messageStr);
        
        // Map ESP32 payload to frontend TelemetryTick
        // ESP32: waveHeightCm (cm), waveFreqHz (Hz), ts (ISO)
        // Frontend: waveHeight (m), waveFreq (Hz), ts (HH:MM:SS)
        const tick: TelemetryTick = {
          ts: extractHHMMSS(data.ts),
          waveHeight: data.waveHeightCm !== undefined ? data.waveHeightCm / 100 : (data.waveHeight || 0),
          waveFreq: data.waveFreqHz !== undefined ? data.waveFreqHz : (data.waveFreq || 0),
          rpm: data.rpm || 0,
          power: data.power || 0,
          voltage: data.voltage || 0,
          current: data.current || 0
        };

        useTelemetryStore.getState().pushTick(tick);
      } catch (err) {
        console.error("[MQTT] Error parsing message", err);
      }
    });

    await connection.connect();
    
    // Subscribe to telemetry topic
    await connection.subscribe(topic, mqtt.QoS.AtLeastOnce);
    console.log(`[MQTT] Subscribed to ${topic}`);
    isConnecting = false;

  } catch (error) {
    console.error("[MQTT] Connection failed", error);
    useTelemetryStore.getState().setConnected(false);
    isConnecting = false;
  }
}

export async function disconnectMqttClient() {
  if (connection) {
    try {
      await connection.disconnect();
    } catch (e) {
      console.error("[MQTT] Error disconnecting:", e);
    }
    connection = null;
  }
}

export async function publishControlCommand(mode:'battery' | 'load') {
  if(!connection){
    console.error("MQTT not connected");
    return;
  }

  const payload = JSON.stringify({ relay: mode });
  try{
    await connection.publish("ocean/wave/control", payload, mqtt.QoS.AtLeastOnce);
    console.log(`[MQTT] Published control command: ${payload}`);
  } catch (err) {
    console.error("[MQTT] Failed to publish control command", err);
  }
}