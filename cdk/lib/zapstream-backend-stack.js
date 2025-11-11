"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ZapStreamBackendStack = void 0;
const aws_cdk_lib_1 = require("aws-cdk-lib");
const cdk = require("aws-cdk-lib");
const ec2 = require("aws-cdk-lib/aws-ec2");
const ecs = require("aws-cdk-lib/aws-ecs");
const elasticloadbalancingv2 = require("aws-cdk-lib/aws-elasticloadbalancingv2");
const rds = require("aws-cdk-lib/aws-rds");
const iam = require("aws-cdk-lib/aws-iam");
const logs = require("aws-cdk-lib/aws-logs");
class ZapStreamBackendStack extends aws_cdk_lib_1.Stack {
    constructor(scope, id, props) {
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
            removalPolicy: aws_cdk_lib_1.RemovalPolicy.DESTROY,
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
        database.connections.allowFrom(taskSecurityGroup, ec2.Port.tcp(5432), 'Allow ECS tasks to connect to RDS');
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
                DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(database.secret, 'password'),
                DATABASE_USERNAME: ecs.Secret.fromSecretsManager(database.secret, 'username'),
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
                interval: aws_cdk_lib_1.Duration.seconds(30),
                timeout: aws_cdk_lib_1.Duration.seconds(5),
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
exports.ZapStreamBackendStack = ZapStreamBackendStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiemFwc3RyZWFtLWJhY2tlbmQtc3RhY2suanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyJ6YXBzdHJlYW0tYmFja2VuZC1zdGFjay50cyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7QUFDQSw2Q0FBeUU7QUFDekUsbUNBQW1DO0FBQ25DLDJDQUEyQztBQUMzQywyQ0FBMkM7QUFDM0MsaUZBQWlGO0FBQ2pGLDJDQUEyQztBQUMzQywyQ0FBMkM7QUFFM0MsNkNBQTZDO0FBRTdDLE1BQWEscUJBQXNCLFNBQVEsbUJBQUs7SUFDOUMsWUFBWSxLQUFnQixFQUFFLEVBQVUsRUFBRSxLQUFrQjtRQUMxRCxLQUFLLENBQUMsS0FBSyxFQUFFLEVBQUUsRUFBRSxLQUFLLENBQUMsQ0FBQztRQUV4QixzQkFBc0I7UUFDdEIsTUFBTSxHQUFHLEdBQUcsSUFBSSxHQUFHLENBQUMsR0FBRyxDQUFDLElBQUksRUFBRSxjQUFjLEVBQUU7WUFDNUMsTUFBTSxFQUFFLENBQUM7WUFDVCxXQUFXLEVBQUUsQ0FBQztZQUNkLG1CQUFtQixFQUFFO2dCQUNuQjtvQkFDRSxRQUFRLEVBQUUsRUFBRTtvQkFDWixJQUFJLEVBQUUsUUFBUTtvQkFDZCxVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxNQUFNO2lCQUNsQztnQkFDRDtvQkFDRSxRQUFRLEVBQUUsRUFBRTtvQkFDWixJQUFJLEVBQUUsU0FBUztvQkFDZixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxtQkFBbUI7aUJBQy9DO2FBQ0Y7U0FDRixDQUFDLENBQUM7UUFFSCxjQUFjO1FBQ2QsTUFBTSxPQUFPLEdBQUcsSUFBSSxHQUFHLENBQUMsT0FBTyxDQUFDLElBQUksRUFBRSxrQkFBa0IsRUFBRTtZQUN4RCxHQUFHO1lBQ0gsV0FBVyxFQUFFLG1CQUFtQjtTQUNqQyxDQUFDLENBQUM7UUFFSCwwQkFBMEI7UUFDMUIsTUFBTSxRQUFRLEdBQUcsSUFBSSxHQUFHLENBQUMsZ0JBQWdCLENBQUMsSUFBSSxFQUFF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cyc7XG5pbXBvcnQgeyBTdGFjaywgU3RhY2tQcm9wcywgRHVyYXRpb24sIFJlbW92YWxQb2xpY3kgfSBmcm9tICdhd3MtY2RrLWxpYic7XG5pbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0ICogYXMgZWMyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1lYzInO1xuaW1wb3J0ICogYXMgZWNzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1lY3MnO1xuaW1wb3J0ICogYXMgZWxhc3RpY2xvYWRiYWxhbmNpbmd2MiBmcm9tICdhd3MtY2RrLWxpYi9hd3MtZWxhc3RpY2xvYWRiYWxhbmNpbmd2Mic7XG5pbXBvcnQgKiBhcyByZHMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXJkcyc7XG5pbXBvcnQgKiBhcyBpYW0gZnJvbSAnYXdzLWNkay1saWIvYXdzLWlhbSc7XG5pbXBvcnQgKiBhcyBzMyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtczMnO1xuaW1wb3J0ICogYXMgbG9ncyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtbG9ncyc7XG5cbmV4cG9ydCBjbGFzcyBaYXBTdHJlYW1CYWNrZW5kU3RhY2sgZXh0ZW5kcyBTdGFjayB7XG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzPzogU3RhY2tQcm9wcykge1xuICAgIHN1cGVyKHNjb3BlLCBpZCwgcHJvcHMpO1xuXG4gICAgLy8gVlBDIGZvciB0aGUgYmFja2VuZFxuICAgIGNvbnN0IHZwYyA9IG5ldyBlYzIuVnBjKHRoaXMsICdaYXBTdHJlYW1WUEMnLCB7XG4gICAgICBtYXhBenM6IDIsXG4gICAgICBuYXRHYXRld2F5czogMSxcbiAgICAgIHN1Ym5ldENvbmZpZ3VyYXRpb246IFtcbiAgICAgICAge1xuICAgICAgICAgIGNpZHJNYXNrOiAyNCxcbiAgICAgICAgICBuYW1lOiAncHVibGljJyxcbiAgICAgICAgICBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QVUJMSUMsXG4gICAgICAgIH0sXG4gICAgICAgIHtcbiAgICAgICAgICBjaWRyTWFzazogMjQsXG4gICAgICAgICAgbmFtZTogJ3ByaXZhdGUnLFxuICAgICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfV0lUSF9FR1JFU1MsXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgIH0pO1xuXG4gICAgLy8gRUNTIENsdXN0ZXJcbiAgICBjb25zdCBjbHVzdGVyID0gbmV3IGVjcy5DbHVzdGVyKHRoaXMsICdaYXBTdHJlYW1DbHVzdGVyJywge1xuICAgICAgdnBjLFxuICAgICAgY2x1c3Rlck5hbWU6ICd6YXBzdHJlYW0tY2x1c3RlcicsXG4gICAgfSk7XG5cbiAgICAvLyBSRFMgUG9zdGdyZVNRTCBEYXRhYmFzZVxuICAgIGNvbnN0IGRhdGFiYXNlID0gbmV3IHJkcy5EYXRhYmFzZUluc3RhbmNlKHRoaXMsICdaYXBTdHJlYW1EYXRhYmFzZScsIHtcbiAgICAgIGVuZ2luZTogcmRzLkRhdGFiYXNlSW5zdGFuY2VFbmdpbmUucG9zdGdyZXMoe1xuICAgICAgICB2ZXJzaW9uOiByZHMuUG9zdGdyZXNFbmdpbmVWZXJzaW9uLlZFUl8xNV80LFxuICAgICAgfSksXG4gICAgICBpbnN0YW5jZVR5cGU6IGVjMi5JbnN0YW5jZVR5cGUub2YoZWMyLkluc3RhbmNlQ2xhc3MuQlVSU1RBQkxFMywgZWMyLkluc3RhbmNlU2l6ZS5NSUNSTyksXG4gICAgICB2cGMsXG4gICAgICB2cGNTdWJuZXRzOiB7XG4gICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfV0lUSF9FR1JFU1MsXG4gICAgICB9LFxuICAgICAgYWxsb2NhdGVkU3RvcmFnZTogMjAsXG4gICAgICBkYXRhYmFzZU5hbWU6ICd6YXBzdHJlYW0nLFxuICAgICAgcmVtb3ZhbFBvbGljeTogUmVtb3ZhbFBvbGljeS5ERVNUUk9ZLFxuICAgICAgZGVsZXRpb25Qcm90ZWN0aW9uOiBmYWxzZSxcbiAgICB9KTtcblxuICAgIC8vIEFwcGxpY2F0aW9uIExvYWQgQmFsYW5jZXJcbiAgICBjb25zdCBsb2FkQmFsYW5jZXIgPSBuZXcgZWxhc3RpY2xvYWRiYWxhbmNpbmd2Mi5BcHBsaWNhdGlvbkxvYWRCYWxhbmNlcih0aGlzLCAnWmFwU3RyZWFtQUxCJywge1xuICAgICAgdnBjLFxuICAgICAgaW50ZXJuZXRGYWNpbmc6IHRydWUsXG4gICAgICBsb2FkQmFsYW5jZXJOYW1lOiAnemFwc3RyZWFtLWFsYicsXG4gICAgfSk7XG5cbiAgICAvLyBTZWN1cml0eSBncm91cCBmb3IgRUNTIHRhc2tzXG4gICAgY29uc3QgdGFza1NlY3VyaXR5R3JvdXAgPSBuZXcgZWMyLlNlY3VyaXR5R3JvdXAodGhpcywgJ1Rhc2tTZWN1cml0eUdyb3VwJywge1xuICAgICAgdnBjLFxuICAgICAgYWxsb3dBbGxPdXRib3VuZDogdHJ1ZSxcbiAgICAgIGRlc2NyaXB0aW9uOiAnU2VjdXJpdHkgZ3JvdXAgZm9yIEVDUyB0YXNrcycsXG4gICAgfSk7XG5cbiAgICAvLyBBbGxvdyBFQ1MgdGFza3MgdG8gY29ubmVjdCB0byBSRFNcbiAgICBkYXRhYmFzZS5jb25uZWN0aW9ucy5hbGxvd0Zyb20oXG4gICAgICB0YXNrU2VjdXJpdHlHcm91cCxcbiAgICAgIGVjMi5Qb3J0LnRjcCg1NDMyKSxcbiAgICAgICdBbGxvdyBFQ1MgdGFza3MgdG8gY29ubmVjdCB0byBSRFMnXG4gICAgKTtcblxuICAgIC8vIEZhcmdhdGUgVGFzayBEZWZpbml0aW9uXG4gICAgY29uc3QgdGFza0RlZmluaXRpb24gPSBuZXcgZWNzLkZhcmdhdGVUYXNrRGVmaW5pdGlvbih0aGlzLCAnWmFwU3RyZWFtVGFza0RlZmluaXRpb24nLCB7XG4gICAgICBtZW1vcnlMaW1pdE1pQjogNTEyLFxuICAgICAgY3B1OiAyNTYsXG4gICAgICBydW50aW1lUGxhdGZvcm06IHtcbiAgICAgICAgY3B1QXJjaGl0ZWN0dXJlOiBlY3MuQ3B1QXJjaGl0ZWN0dXJlLkFSTTY0LFxuICAgICAgICBvcGVyYXRpbmdTeXN0ZW1GYW1pbHk6IGVjcy5PcGVyYXRpbmdTeXN0ZW1GYW1pbHkuTElOVVgsXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gSUFNIFJvbGUgZm9yIEVDUyBUYXNrXG4gICAgY29uc3QgdGFza1JvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ1phcFN0cmVhbVRhc2tSb2xlJywge1xuICAgICAgYXNzdW1lZEJ5OiBuZXcgaWFtLlNlcnZpY2VQcmluY2lwYWwoJ2Vjcy10YXNrcy5hbWF6b25hd3MuY29tJyksXG4gICAgfSk7XG5cbiAgICAvLyBBZGQgcGVybWlzc2lvbnMgZm9yIHRoZSB0YXNrIHJvbGVcbiAgICB0YXNrUm9sZS5hZGRUb1BvbGljeShuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICBhY3Rpb25zOiBbXG4gICAgICAgICdsb2dzOkNyZWF0ZUxvZ0dyb3VwJyxcbiAgICAgICAgJ2xvZ3M6Q3JlYXRlTG9nU3RyZWFtJyxcbiAgICAgICAgJ2xvZ3M6UHV0TG9nRXZlbnRzJyxcbiAgICAgIF0sXG4gICAgICByZXNvdXJjZXM6IFsnKiddLFxuICAgIH0pKTtcblxuICAgIC8vIFRhc2sgRGVmaW5pdGlvbiB3aXRoIEZhc3RBUEkgY29udGFpbmVyXG4gICAgY29uc3QgY29udGFpbmVyID0gdGFza0RlZmluaXRpb24uYWRkQ29udGFpbmVyKCdaYXBTdHJlYW1Db250YWluZXInLCB7XG4gICAgICBpbWFnZTogZWNzLkNvbnRhaW5lckltYWdlLmZyb21Bc3NldCgnLi4vJywge1xuICAgICAgICBleGNsdWRlOiBbJ2Nkay8qKicsICdub2RlX21vZHVsZXMvKionLCAnLmdpdC8qKicsICcubmV4dC8qKicsICdvdXQvKionXSxcbiAgICAgIH0pLFxuICAgICAgcG9ydE1hcHBpbmdzOiBbXG4gICAgICAgIHtcbiAgICAgICAgICBjb250YWluZXJQb3J0OiA4MDAwLFxuICAgICAgICAgIHByb3RvY29sOiBlY3MuUHJvdG9jb2wuVENQLFxuICAgICAgICB9LFxuICAgICAgXSxcbiAgICAgIGVudmlyb25tZW50OiB7XG4gICAgICAgIFNUT1JBR0VfQkFDS0VORDogJ3Bvc3RncmVzJyxcbiAgICAgICAgREFUQUJBU0VfSE9TVDogZGF0YWJhc2UuaW5zdGFuY2VFbmRwb2ludC5ob3N0bmFtZSB8fCAnbG9jYWxob3N0JyxcbiAgICAgICAgREFUQUJBU0VfUE9SVDogZGF0YWJhc2UuaW5zdGFuY2VFbmRwb2ludC5wb3J0Py50b1N0cmluZygpIHx8ICc1NDMyJyxcbiAgICAgICAgREFUQUJBU0VfTkFNRTogJ3phcHN0cmVhbScsXG4gICAgICAgIENPUlNfQUxMT1dFRF9PUklHSU5TOiAnaHR0cHM6Ly95b3VyLWRvbWFpbi5jb20saHR0cDovL2xvY2FsaG9zdDozMDAwJyxcbiAgICAgICAgTE9HX0xFVkVMOiAnSU5GTycsXG4gICAgICB9LFxuICAgICAgc2VjcmV0czoge1xuICAgICAgICBEQVRBQkFTRV9QQVNTV09SRDogZWNzLlNlY3JldC5mcm9tU2VjcmV0c01hbmFnZXIoZGF0YWJhc2Uuc2VjcmV0ISwgJ3Bhc3N3b3JkJyksXG4gICAgICAgIERBVEFCQVNFX1VTRVJOQU1FOiBlY3MuU2VjcmV0LmZyb21TZWNyZXRzTWFuYWdlcihkYXRhYmFzZS5zZWNyZXQhLCAndXNlcm5hbWUnKSxcbiAgICAgIH0sXG4gICAgICBsb2dnaW5nOiBlY3MuTG9nRHJpdmVycy5hd3NMb2dzKHtcbiAgICAgICAgc3RyZWFtUHJlZml4OiAnemFwc3RyZWFtJyxcbiAgICAgICAgbG9nUmV0ZW50aW9uOiBsb2dzLlJldGVudGlvbkRheXMuT05FX1dFRUssXG4gICAgICB9KSxcbiAgICB9KTtcblxuICAgIC8vIEVDUyBTZXJ2aWNlXG4gICAgY29uc3QgZWNzU2VydmljZSA9IG5ldyBlY3MuRmFyZ2F0ZVNlcnZpY2UodGhpcywgJ1phcFN0cmVhbVNlcnZpY2UnLCB7XG4gICAgICBjbHVzdGVyLFxuICAgICAgdGFza0RlZmluaXRpb24sXG4gICAgICBhc3NpZ25QdWJsaWNJcDogZmFsc2UsXG4gICAgICB2cGNTdWJuZXRzOiB7XG4gICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfV0lUSF9FR1JFU1MsXG4gICAgICB9LFxuICAgICAgc2VjdXJpdHlHcm91cHM6IFt0YXNrU2VjdXJpdHlHcm91cF0sXG4gICAgICBkZXNpcmVkQ291bnQ6IDEsXG4gICAgICBtaW5IZWFsdGh5UGVyY2VudDogNTAsXG4gICAgICBtYXhIZWFsdGh5UGVyY2VudDogMjAwLFxuICAgICAgZGVwbG95bWVudENvbnRyb2xsZXI6IHtcbiAgICAgICAgdHlwZTogZWNzLkRlcGxveW1lbnRDb250cm9sbGVyVHlwZS5FQ1MsXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gTG9hZCBCYWxhbmNlciBUYXJnZXQgR3JvdXBcbiAgICBjb25zdCB0YXJnZXRHcm91cCA9IG5ldyBlbGFzdGljbG9hZGJhbGFuY2luZ3YyLkFwcGxpY2F0aW9uVGFyZ2V0R3JvdXAodGhpcywgJ1phcFN0cmVhbVRhcmdldEdyb3VwJywge1xuICAgICAgdnBjLFxuICAgICAgcG9ydDogODAwMCxcbiAgICAgIHByb3RvY29sOiBlbGFzdGljbG9hZGJhbGFuY2luZ3YyLkFwcGxpY2F0aW9uUHJvdG9jb2wuSFRUUCxcbiAgICAgIGhlYWx0aENoZWNrOiB7XG4gICAgICAgIHBhdGg6ICcvaGVhbHRoJyxcbiAgICAgICAgaW50ZXJ2YWw6IER1cmF0aW9uLnNlY29uZHMoMzApLFxuICAgICAgICB0aW1lb3V0OiBEdXJhdGlvbi5zZWNvbmRzKDUpLFxuICAgICAgICBoZWFsdGh5VGhyZXNob2xkQ291bnQ6IDIsXG4gICAgICAgIHVuaGVhbHRoeVRocmVzaG9sZENvdW50OiAzLFxuICAgICAgfSxcbiAgICAgIHRhcmdldFR5cGU6IGVsYXN0aWNsb2FkYmFsYW5jaW5ndjIuVGFyZ2V0VHlwZS5JUCxcbiAgICB9KTtcblxuICAgIC8vIExvYWQgQmFsYW5jZXIgTGlzdGVuZXJcbiAgICBjb25zdCBsaXN0ZW5lciA9IGxvYWRCYWxhbmNlci5hZGRMaXN0ZW5lcignWmFwU3RyZWFtTGlzdGVuZXInLCB7XG4gICAgICBwb3J0OiA4MCxcbiAgICAgIG9wZW46IHRydWUsXG4gICAgICBkZWZhdWx0VGFyZ2V0R3JvdXBzOiBbdGFyZ2V0R3JvdXBdLFxuICAgIH0pO1xuXG4gICAgLy8gQXR0YWNoIHRhcmdldCBncm91cCB0byBFQ1Mgc2VydmljZVxuICAgIGVjc1NlcnZpY2UuYXR0YWNoVG9BcHBsaWNhdGlvblRhcmdldEdyb3VwKHRhcmdldEdyb3VwKTtcblxuICAgIC8vIE91dHB1dHNcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnTG9hZEJhbGFuY2VyRE5TJywge1xuICAgICAgdmFsdWU6IGxvYWRCYWxhbmNlci5sb2FkQmFsYW5jZXJEbnNOYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdETlMgbmFtZSBvZiB0aGUgbG9hZCBiYWxhbmNlcicsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnRGF0YWJhc2VFbmRwb2ludCcsIHtcbiAgICAgIHZhbHVlOiBkYXRhYmFzZS5pbnN0YW5jZUVuZHBvaW50Lmhvc3RuYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdSRFMgZGF0YWJhc2UgZW5kcG9pbnQnLFxuICAgIH0pO1xuICB9XG59Il19