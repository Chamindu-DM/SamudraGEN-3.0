import { DynamoDBClient, QueryCommand } from "@aws-sdk/client-dynamodb";
import { unmarshall } from "@aws-sdk/util-dynamodb";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-provider-cognito-identity";

import fs from 'fs';
const envFile = fs.readFileSync('.env', 'utf8');
const identityPoolId = envFile.match(/VITE_COGNITO_IDENTITY_POOL_ID=(.*)/)[1].trim();
const awsRegion = envFile.match(/VITE_AWS_REGION=(.*)/)[1].trim();

const dynamoClient = new DynamoDBClient({
  region: awsRegion,
  credentials: fromCognitoIdentityPool({
    identityPoolId,
    clientConfig: { region: awsRegion },
  }),
});

async function run() {
  try {
    const today = new Date().toISOString().split('T')[0];
    console.log("Querying for date:", today);
    const command = new QueryCommand({
      TableName: "SamudraGEN-Telemetry",
      KeyConditionExpression: "#pk = :date AND #sk BETWEEN :start AND :end",
      ExpressionAttributeNames: { "#pk": "date", "#sk": "ts" },
      ExpressionAttributeValues: {
        ":date": { S: today },
        ":start": { S: "00:00:00" },
        ":end": { S: "23:59:59" },
      },
      Limit: 10,
    });
    const response = await dynamoClient.send(command);
    console.log("Response:", JSON.stringify(response, null, 2));
  } catch (err) {
    console.error("Error:", err);
  }
}
run();
