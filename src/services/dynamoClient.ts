import { DynamoDBClient, QueryCommand } from "@aws-sdk/client-dynamodb";
import { unmarshall } from "@aws-sdk/util-dynamodb";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-provider-cognito-identity";
import type { TelemetryTick } from "../store/telemetryStore";

let dynamoClient: DynamoDBClient | null = null;

export function getDynamoClient() {
  if (dynamoClient) return dynamoClient;

  const region = import.meta.env.VITE_AWS_REGION;
  const identityPoolId = import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID;

  if (!region || !identityPoolId) {
    console.error("DynamoDB Client: Missing AWS region or Identity Pool ID in .env");
    return null;
  }

  dynamoClient = new DynamoDBClient({
    region,
    credentials: fromCognitoIdentityPool({
      identityPoolId,
      clientConfig: { region },
    }),
  });

  return dynamoClient;
}

export async function fetchHistoricalData(
  localDateStr: string,
  _token: any = null // Keeping for signature compat, but unused now
): Promise<{ items: TelemetryTick[]; nextKey: any | null }> {
  const client = getDynamoClient();
  if (!client) throw new Error("DynamoDB Client not initialized");

  // Determine the previous date to cover timezone overlaps
  const targetDate = new Date(localDateStr);
  targetDate.setUTCDate(targetDate.getUTCDate() - 1);
  const prevDateStr = targetDate.toISOString().split('T')[0];
  
  const partitionsToFetch = [prevDateStr, localDateStr];
  let allItems: TelemetryTick[] = [];

  for (const date of partitionsToFetch) {
    let lastKey: any | undefined = undefined;
    let hasMore = true;

    while (hasMore) {
      const command = new QueryCommand({
        TableName: "SamudraGEN-Telemetry",
        KeyConditionExpression: "#pk = :date",
        ExpressionAttributeNames: {
          "#pk": "date",
        },
        ExpressionAttributeValues: {
          ":date": { S: date },
        },
        ScanIndexForward: false, // get newest first
        ExclusiveStartKey: lastKey,
      });

      try {
        const response = await client.send(command);
        const parsedItems = (response.Items || []).map((item) => unmarshall(item) as TelemetryTick);
        allItems.push(...parsedItems);
        
        lastKey = response.LastEvaluatedKey;
        if (!lastKey) hasMore = false;
      } catch (error) {
        console.error(`Error fetching historical data for ${date}:`, error);
        hasMore = false;
      }
    }
  }

  // Filter exactly by the requested localDateStr in the timestamp
  const filteredItems = allItems.filter(item => item.ts.startsWith(localDateStr));
  
  // Sort by time descending (since we fetched two partitions, they need re-sorting)
  filteredItems.sort((a, b) => b.ts.localeCompare(a.ts));

  return {
    items: filteredItems,
    nextKey: null, // Frontend pagination handles the rest
  };
}

export async function fetchLast24HoursPowerData(): Promise<{ ts: string, power: number }[]> {
  const client = getDynamoClient();
  if (!client) throw new Error("DynamoDB Client not initialized");

  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 3600 * 1000);
  
  // The database partitions are in UTC
  const partitionsToFetch = [
    yesterday.toISOString().split('T')[0],
    now.toISOString().split('T')[0]
  ];

  // Unique partitions to avoid duplicate fetches if now and yesterday are the same UTC day
  const uniquePartitions = [...new Set(partitionsToFetch)];
  
  let allItems: { ts: string, power: number }[] = [];
  const twentyFourHoursAgo = now.getTime() - 24 * 3600 * 1000;

  for (const date of uniquePartitions) {
    let lastKey: any | undefined = undefined;
    let hasMore = true;

    while (hasMore) {
      const command = new QueryCommand({
        TableName: "SamudraGEN-Telemetry",
        KeyConditionExpression: "#pk = :date",
        ExpressionAttributeNames: {
          "#pk": "date",
          "#ts": "ts",
          "#p": "power"
        },
        ExpressionAttributeValues: {
          ":date": { S: date },
        },
        ProjectionExpression: "#ts, #p",
        ScanIndexForward: true, // get oldest first so the chart plots left to right
        ExclusiveStartKey: lastKey,
      });

      try {
        const response = await client.send(command);
        if (response.Items) {
            for (const item of response.Items) {
                const unmarshalled = unmarshall(item) as TelemetryTick;
                const itemTime = new Date(unmarshalled.ts).getTime();
                if (itemTime >= twentyFourHoursAgo) {
                    allItems.push({
                        ts: unmarshalled.ts,
                        power: Number(unmarshalled.power) || 0
                    });
                }
            }
        }
        
        lastKey = response.LastEvaluatedKey;
        if (!lastKey) hasMore = false;
      } catch (error) {
        console.error(`Error fetching 24h power data for ${date}:`, error);
        hasMore = false;
      }
    }
  }

  // Sort chronologically (left to right for the chart)
  allItems.sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());

  return allItems;
}
