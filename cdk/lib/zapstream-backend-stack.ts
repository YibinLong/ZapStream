import { Construct } from 'constructs';
import { Stack, StackProps, Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elasticloadbalancingv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as logs from 'aws-cdk-lib/aws-logs';

export class ZapStreamBackendStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // VPC for the backend
    const vpc = new ec2.Vpc(this, 'ZapStreamVPC', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
      ],
    });

    // ECS Cluster
    const cluster = new ecs.Cluster(this, 'ZapStreamCluster', {
      vpc,
      clusterName: 'zapstream-cluster',
    });

    // RDS PostgreSQL Database
    const database = new rds.DatabaseInstance(this, 'ZapStreamDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_4,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      allocatedStorage: 20,
      databaseName: 'zapstream',
      removalPolicy: RemovalPolicy.DESTROY,
      deletionProtection: false,
    });

    // Application Load Balancer
    const loadBalancer = new elasticloadbalancingv2.ApplicationLoadBalancer(this, 'ZapStreamALB', {
      vpc,
      internetFacing: true,
      loadBalancerName: 'zapstream-alb',
    });

    // Security group for ECS tasks
    const taskSecurityGroup = new ec2.SecurityGroup(this, 'TaskSecurityGroup', {
      vpc,
      allowAllOutbound: true,
      description: 'Security group for ECS tasks',
    });

    // Allow ECS tasks to connect to RDS
    database.connections.allowFrom(
      taskSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow ECS tasks to connect to RDS'
    );

    // Fargate Task Definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'ZapStreamTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.ARM64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    // IAM Role for ECS Task
    const taskRole = new iam.Role(this, 'ZapStreamTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // Add permissions for the task role
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    // Task Definition with FastAPI container
    const container = taskDefinition.addContainer('ZapStreamContainer', {
      image: ecs.ContainerImage.fromAsset('../', {
        exclude: ['cdk/**', 'node_modules/**', '.git/**', '.next/**', 'out/**'],
      }),
      portMappings: [
        {
          containerPort: 8000,
          protocol: ecs.Protocol.TCP,
        },
      ],
      environment: {
        STORAGE_BACKEND: 'postgres',
        DATABASE_HOST: database.instanceEndpoint.hostname || 'localhost',
        DATABASE_PORT: database.instanceEndpoint.port?.toString() || '5432',
        DATABASE_NAME: 'zapstream',
        CORS_ALLOWED_ORIGINS: 'https://your-domain.com,http://localhost:3000',
        LOG_LEVEL: 'INFO',
      },
      secrets: {
        DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(database.secret!, 'password'),
        DATABASE_USERNAME: ecs.Secret.fromSecretsManager(database.secret!, 'username'),
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'zapstream',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
    });

    // ECS Service
    const ecsService = new ecs.FargateService(this, 'ZapStreamService', {
      cluster,
      taskDefinition,
      assignPublicIp: false,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [taskSecurityGroup],
      desiredCount: 1,
      minHealthyPercent: 50,
      maxHealthyPercent: 200,
      deploymentController: {
        type: ecs.DeploymentControllerType.ECS,
      },
    });

    // Load Balancer Target Group
    const targetGroup = new elasticloadbalancingv2.ApplicationTargetGroup(this, 'ZapStreamTargetGroup', {
      vpc,
      port: 8000,
      protocol: elasticloadbalancingv2.ApplicationProtocol.HTTP,
      healthCheck: {
        path: '/health',
        interval: Duration.seconds(30),
        timeout: Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
      targetType: elasticloadbalancingv2.TargetType.IP,
    });

    // Load Balancer Listener
    const listener = loadBalancer.addListener('ZapStreamListener', {
      port: 80,
      open: true,
      defaultTargetGroups: [targetGroup],
    });

    // Attach target group to ECS service
    ecsService.attachToApplicationTargetGroup(targetGroup);

    // Outputs
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: loadBalancer.loadBalancerDnsName,
      description: 'DNS name of the load balancer',
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: database.instanceEndpoint.hostname,
      description: 'RDS database endpoint',
    });
  }
}