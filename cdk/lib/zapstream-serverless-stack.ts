import { Construct } from 'constructs';
import { Stack, StackProps, Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';

export class ZapStreamServerlessStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // DynamoDB table for events storage
    const eventsTable = new dynamodb.Table(this, 'ZapStreamEventsTable', {
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'event_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
    });

    // Secondary indexes
    eventsTable.addGlobalSecondaryIndex({
      indexName: 'TenantStatusIndex',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
    });

    eventsTable.addGlobalSecondaryIndex({
      indexName: 'IdempotencyIndex',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'idempotency_key', type: dynamodb.AttributeType.STRING },
    });

    // S3 bucket for logs and assets
    const logsBucket = new s3.Bucket(this, 'ZapStreamLogsBucket', {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // IAM role for Lambda function
    const lambdaRole = new iam.Role(this, 'ZapStreamLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    // Add permissions for the Lambda role
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'dynamodb:PutItem',
        'dynamodb:GetItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:Query',
        'dynamodb:Scan',
      ],
      resources: [
        eventsTable.tableArn,
        `${eventsTable.tableArn}/*`,
      ],
    }));

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        's3:GetObject',
        's3:PutObject',
      ],
      resources: [
        logsBucket.bucketArn,
        `${logsBucket.bucketArn}/*`,
      ],
    }));

    // Lambda function for the FastAPI backend
    const apiLambda = new lambda.Function(this, 'ZapStreamAPIFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_function.lambda_handler',
      role: lambdaRole,
      timeout: Duration.seconds(30),
      memorySize: 512,
      environment: {
        STORAGE_BACKEND: 'dynamodb',
        DYNAMODB_TABLE: eventsTable.tableName,
        LOG_LEVEL: 'INFO',
        CORS_ALLOWED_ORIGINS: '*',
        API_KEYS: 'dev_key_123=tenant_dev,prod_key_456=tenant_prod',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
      code: lambda.Code.fromAsset('../lambda.zip'), // We'll create this zip
      layers: [
        // Add Lambda layer for dependencies if needed
      ],
    });

    // API Gateway
    const api = new apigw.RestApi(this, 'ZapStreamAPI', {
      restApiName: 'ZapStream API',
      description: 'ZapStream Backend API',
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: apigw.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
          'X-Amz-User-Agent',
          'X-Idempotency-Key',
        ],
      },
      deployOptions: {
        stageName: 'v1',
        loggingLevel: apigw.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
      },
    });

    // API Gateway integration with Lambda
    const integration = new apigw.LambdaIntegration(apiLambda, {
      proxy: true,
      allowTestInvoke: true,
    });

    // API Gateway resources
    const health = api.root.addResource('health');
    health.addMethod('GET', integration);

    const events = api.root.addResource('events');
    events.addMethod('POST', integration);

    const inbox = api.root.addResource('inbox');
    inbox.addMethod('GET', integration);

    const inboxEvent = inbox.addResource('{event_id}');
    inboxEvent.addMethod('POST', integration); // for ack
    inboxEvent.addMethod('DELETE', integration);

    const inboxAck = inboxEvent.addResource('ack');
    inboxAck.addMethod('POST', integration);

    // CloudWatch Alarms
    new cloudwatch.Alarm(this, 'ZapStreamAPIErrors', {
      metric: apiLambda.metricErrors({
        period: Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 10,
      evaluationPeriods: 2,
      alarmDescription: 'ZapStream API error rate is high',
    });

    new cloudwatch.Alarm(this, 'ZapStreamAPIThrottles', {
      metric: apiLambda.metricThrottles({
        period: Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 5,
      evaluationPeriods: 2,
      alarmDescription: 'ZapStream API throttle rate is high',
    });

    // Outputs
    new cdk.CfnOutput(this, 'APIGatewayURL', {
      value: api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'DynamoDBTableName', {
      value: eventsTable.tableName,
      description: 'DynamoDB table name for events',
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: apiLambda.functionName,
      description: 'Lambda function name',
    });
  }
}