"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ZapStreamPipelineStack = void 0;
const aws_cdk_lib_1 = require("aws-cdk-lib");
const codepipeline = require("aws-cdk-lib/aws-codepipeline");
const codepipeline_actions = require("aws-cdk-lib/aws-codepipeline-actions");
const s3 = require("aws-cdk-lib/aws-s3");
const codebuild = require("aws-cdk-lib/aws-codebuild");
const secretsmanager = require("aws-cdk-lib/aws-secretsmanager");
class ZapStreamPipelineStack extends aws_cdk_lib_1.Stack {
    constructor(scope, id, props) {
        super(scope, id, props);
        // Get GitHub token from Secrets Manager
        const githubToken = secretsmanager.Secret.fromSecretNameV2(this, 'GitHubToken', 'github-token');
        // S3 bucket for the website (already exists)
        const websiteBucket = s3.Bucket.fromBucketName(this, 'WebsiteBucket', 'zapstream-app-1762821749');
        // Artifact for the pipeline
        const sourceOutput = new codepipeline.Artifact('SourceOutput');
        // CodeBuild project to build the Next.js app
        const buildProject = new codebuild.PipelineProject(this, 'BuildProject', {
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
                computeType: codebuild.ComputeType.SMALL,
            },
            buildSpec: codebuild.BuildSpec.fromObject({
                version: '0.2',
                phases: {
                    install: {
                        'runtime-versions': {
                            nodejs: '18',
                        },
                        commands: [
                            'npm ci',
                        ],
                    },
                    build: {
                        commands: [
                            'npm run build',
                            'aws s3 sync out/ s3://${WEBSITE_BUCKET} --delete',
                        ],
                    },
                },
            }),
            environmentVariables: {
                WEBSITE_BUCKET: {
                    value: websiteBucket.bucketName,
                },
            },
        });
        // Grant the build project permissions to deploy to S3
        websiteBucket.grantReadWrite(buildProject);
        // Create the pipeline
        const pipeline = new codepipeline.Pipeline(this, 'ZapStreamPipeline', {
            pipelineName: 'ZapStreamDeploymentPipeline',
            crossAccountKeys: false,
        });
        // GitHub source action
        const sourceAction = new codepipeline_actions.GitHubSourceAction({
            actionName: 'GitHub_Source',
            owner: 'YibinLong',
            repo: 'ZapStream',
            branch: 'main',
            oauthToken: githubToken.secretValue,
            output: sourceOutput,
        });
        // Build and deploy action
        const buildAction = new codepipeline_actions.CodeBuildAction({
            actionName: 'Build_and_Deploy',
            project: buildProject,
            input: sourceOutput,
        });
        // Add stages to the pipeline
        pipeline.addStage({
            stageName: 'Source',
            actions: [sourceAction],
        });
        pipeline.addStage({
            stageName: 'BuildAndDeploy',
            actions: [buildAction],
        });
    }
}
exports.ZapStreamPipelineStack = ZapStreamPipelineStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiemFwc3RyZWFtLXBpcGVsaW5lLXN0YWNrLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiemFwc3RyZWFtLXBpcGVsaW5lLXN0YWNrLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUNBLDZDQUEwRDtBQUMxRCw2REFBNkQ7QUFDN0QsNkVBQTZFO0FBQzdFLHlDQUF5QztBQUV6Qyx1REFBdUQ7QUFDdkQsaUVBQWlFO0FBRWpFLE1BQWEsc0JBQXVCLFNBQVEsbUJBQUs7SUFDL0MsWUFBWSxLQUFnQixFQUFFLEVBQVUsRUFBRSxLQUFrQjtRQUMxRCxLQUFLLENBQUMsS0FBSyxFQUFFLEVBQUUsRUFBRSxLQUFLLENBQUMsQ0FBQztRQUV4Qix3Q0FBd0M7UUFDeEMsTUFBTSxXQUFXLEdBQUcsY0FBYyxDQUFDLE1BQU0sQ0FBQyxnQkFBZ0IsQ0FDeEQsSUFBSSxFQUNKLGFBQWEsRUFDYixjQUFjLENBQ2YsQ0FBQztRQUVGLDZDQUE2QztRQUM3QyxNQUFNLGFBQWEsR0FBRyxFQUFFLENBQUMsTUFBTSxDQUFDLGNBQWMsQ0FDNUMsSUFBSSxFQUNKLGVBQWUsRUFDZiwwQkFBMEIsQ0FDM0IsQ0FBQztRQUVGLDRCQUE0QjtRQUM1QixNQUFNLFlBQVksR0FBRyxJQUFJLFlBQVksQ0FBQyxRQUFRLENBQUMsY0FBYyxDQUFDLENBQUM7UUFFL0QsNkNBQTZDO1FBQzdDLE1BQU0sWUFBWSxHQUFHLElBQUksU0FBUyxDQUFDLGVBQWUsQ0FBQyxJQUFJLEVBQUUsY0FBYyxFQUFFO1lBQ3ZFLFdBQVcsRUFBRTtnQkFDWCxVQUFVLEVBQUUsU0FBUyxDQUFDLGVBQWUsQ0FBQyxZQUFZO2dCQUNsRCxXQUFXLEVBQUUsU0FBUyxDQUFDLFdBQVcsQ0FBQyxLQUFLO2FBQ3pDO1lBQ0QsU0FBUyxFQUFFLFNBQVMsQ0FBQyxTQUFTLENBQUMsVUFBVSxDQUFDO2dCQUN4QyxPQUFPLEVBQUUsS0FBSztnQkFDZCxNQUFNLEVBQUU7b0JBQ04sT0FBTyxFQUFFO3dCQUNQLGtCQUFrQixFQUFFOzRCQUNsQixNQUFNLEVBQUUsSUFBSTt5QkFDYjt3QkFDRCxRQUFRLEVBQUU7NEJBQ1IsUUFBUTt5QkFDVDtxQkFDRjtvQkFDRCxLQUFLLEVBQUU7d0JBQ0wsUUFBUSxFQUFFOzRCQUNSLGVBQWU7NEJBQ2Ysa0RBQWtEO3lCQUNuRDtxQkFDRjtpQkFDRjthQUNGLENBQUM7WUFDRixvQkFBb0IsRUFBRTtnQkFDcEIsY0FBYyxFQUFFO29CQUNkLEtBQUssRUFBRSxhQUFhLENBQUMsVUFBVTtpQkFDaEM7YUFDRjtTQUNGLENBQUMsQ0FBQztRQUVILHNEQUFzRDtRQUN0RCxhQUFhLENBQUMsY0FBYyxDQUFDLFlBQVksQ0FBQyxDQUFDO1FBRTNDLHNCQUFzQjtRQUN0QixNQUFNLFFBQVEsR0FBRyxJQUFJLFlBQVksQ0FBQyxRQUFRLENBQUMsSUFBSSxFQUFFLG1CQUFtQixFQUFFO1lBQ3BFLFlBQVksRUFBRSw2QkFBNkI7WUFDM0MsZ0JBQWdCLEVBQUUsS0FBSztTQUN4QixDQUFDLENBQUM7UUFFSCx1QkFBdUI7UUFDdkIsTUFBTSxZQUFZLEdBQUcsSUFBSSxvQkFBb0IsQ0FBQyxrQkFBa0IsQ0FBQztZQUMvRCxVQUFVLEVBQUUsZUFBZTtZQUMzQixLQUFLLEVBQUUsV0FBVztZQUNsQixJQUFJLEVBQUUsV0FBVztZQUNqQixNQUFNLEVBQUUsTUFBTTtZQUNkLFVBQVUsRUFBRSxXQUFXLENBQUMsV0FBVztZQUNuQyxNQUFNLEVBQUUsWUFBWTtTQUNyQixDQUFDLENBQUM7UUFFSCwwQkFBMEI7UUFDMUIsTUFBTSxXQUFXLEdBQUcsSUFBSSxvQkFBb0IsQ0FBQyxlQUFlLENBQUM7WUFDM0QsVUFBVSxFQUFFLGtCQUFrQjtZQUM5QixPQUFPLEVBQUUsWUFBWTtZQUNyQixLQUFLLEVBQUUsWUFBWTtTQUNwQixDQUFDLENBQUM7UUFFSCw2QkFBNkI7UUFDN0IsUUFBUSxDQUFDLFFBQVEsQ0FBQztZQUNoQixTQUFTLEVBQUUsUUFBUTtZQUNuQixPQUFPLEVBQUUsQ0FBQyxZQUFZLENBQUM7U0FDeEIsQ0FBQyxDQUFDO1FBRUgsUUFBUSxDQUFDLFFBQVEsQ0FBQztZQUNoQixTQUFTLEVBQUUsZ0JBQWdCO1lBQzNCLE9BQU8sRUFBRSxDQUFDLFdBQVcsQ0FBQztTQUN2QixDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUExRkQsd0RBMEZDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IHsgQ29uc3RydWN0IH0gZnJvbSAnY29uc3RydWN0cyc7XG5pbXBvcnQgeyBTdGFjaywgU3RhY2tQcm9wcywgRHVyYXRpb24gfSBmcm9tICdhd3MtY2RrLWxpYic7XG5pbXBvcnQgKiBhcyBjb2RlcGlwZWxpbmUgZnJvbSAnYXdzLWNkay1saWIvYXdzLWNvZGVwaXBlbGluZSc7XG5pbXBvcnQgKiBhcyBjb2RlcGlwZWxpbmVfYWN0aW9ucyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY29kZXBpcGVsaW5lLWFjdGlvbnMnO1xuaW1wb3J0ICogYXMgczMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXMzJztcbmltcG9ydCAqIGFzIGlhbSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtaWFtJztcbmltcG9ydCAqIGFzIGNvZGVidWlsZCBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY29kZWJ1aWxkJztcbmltcG9ydCAqIGFzIHNlY3JldHNtYW5hZ2VyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zZWNyZXRzbWFuYWdlcic7XG5cbmV4cG9ydCBjbGFzcyBaYXBTdHJlYW1QaXBlbGluZVN0YWNrIGV4dGVuZHMgU3RhY2sge1xuICBjb25zdHJ1Y3RvcihzY29wZTogQ29uc3RydWN0LCBpZDogc3RyaW5nLCBwcm9wcz86IFN0YWNrUHJvcHMpIHtcbiAgICBzdXBlcihzY29wZSwgaWQsIHByb3BzKTtcblxuICAgIC8vIEdldCBHaXRIdWIgdG9rZW4gZnJvbSBTZWNyZXRzIE1hbmFnZXJcbiAgICBjb25zdCBnaXRodWJUb2tlbiA9IHNlY3JldHNtYW5hZ2VyLlNlY3JldC5mcm9tU2VjcmV0TmFtZVYyKFxuICAgICAgdGhpcyxcbiAgICAgICdHaXRIdWJUb2tlbicsXG4gICAgICAnZ2l0aHViLXRva2VuJ1xuICAgICk7XG5cbiAgICAvLyBTMyBidWNrZXQgZm9yIHRoZSB3ZWJzaXRlIChhbHJlYWR5IGV4aXN0cylcbiAgICBjb25zdCB3ZWJzaXRlQnVja2V0ID0gczMuQnVja2V0LmZyb21CdWNrZXROYW1lKFxuICAgICAgdGhpcyxcbiAgICAgICdXZWJzaXRlQnVja2V0JyxcbiAgICAgICd6YXBzdHJlYW0tYXBwLTE3NjI4MjE3NDknXG4gICAgKTtcblxuICAgIC8vIEFydGlmYWN0IGZvciB0aGUgcGlwZWxpbmVcbiAgICBjb25zdCBzb3VyY2VPdXRwdXQgPSBuZXcgY29kZXBpcGVsaW5lLkFydGlmYWN0KCdTb3VyY2VPdXRwdXQnKTtcblxuICAgIC8vIENvZGVCdWlsZCBwcm9qZWN0IHRvIGJ1aWxkIHRoZSBOZXh0LmpzIGFwcFxuICAgIGNvbnN0IGJ1aWxkUHJvamVjdCA9IG5ldyBjb2RlYnVpbGQuUGlwZWxpbmVQcm9qZWN0KHRoaXMsICdCdWlsZFByb2plY3QnLCB7XG4gICAgICBlbnZpcm9ubWVudDoge1xuICAgICAgICBidWlsZEltYWdlOiBjb2RlYnVpbGQuTGludXhCdWlsZEltYWdlLlNUQU5EQVJEXzdfMCxcbiAgICAgICAgY29tcHV0ZVR5cGU6IGNvZGVidWlsZC5Db21wdXRlVHlwZS5TTUFMTCxcbiAgICAgIH0sXG4gICAgICBidWlsZFNwZWM6IGNvZGVidWlsZC5CdWlsZFNwZWMuZnJvbU9iamVjdCh7XG4gICAgICAgIHZlcnNpb246ICcwLjInLFxuICAgICAgICBwaGFzZXM6IHtcbiAgICAgICAgICBpbnN0YWxsOiB7XG4gICAgICAgICAgICAncnVudGltZS12ZXJzaW9ucyc6IHtcbiAgICAgICAgICAgICAgbm9kZWpzOiAnMTgnLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIGNvbW1hbmRzOiBbXG4gICAgICAgICAgICAgICducG0gY2knLFxuICAgICAgICAgICAgXSxcbiAgICAgICAgICB9LFxuICAgICAgICAgIGJ1aWxkOiB7XG4gICAgICAgICAgICBjb21tYW5kczogW1xuICAgICAgICAgICAgICAnbnBtIHJ1biBidWlsZCcsXG4gICAgICAgICAgICAgICdhd3MgczMgc3luYyBvdXQvIHMzOi8vJHtXRUJTSVRFX0JVQ0tFVH0gLS1kZWxldGUnLFxuICAgICAgICAgICAgXSxcbiAgICAgICAgICB9LFxuICAgICAgICB9LFxuICAgICAgfSksXG4gICAgICBlbnZpcm9ubWVudFZhcmlhYmxlczoge1xuICAgICAgICBXRUJTSVRFX0JVQ0tFVDoge1xuICAgICAgICAgIHZhbHVlOiB3ZWJzaXRlQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICAgIH0sXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gR3JhbnQgdGhlIGJ1aWxkIHByb2plY3QgcGVybWlzc2lvbnMgdG8gZGVwbG95IHRvIFMzXG4gICAgd2Vic2l0ZUJ1Y2tldC5ncmFudFJlYWRXcml0ZShidWlsZFByb2plY3QpO1xuXG4gICAgLy8gQ3JlYXRlIHRoZSBwaXBlbGluZVxuICAgIGNvbnN0IHBpcGVsaW5lID0gbmV3IGNvZGVwaXBlbGluZS5QaXBlbGluZSh0aGlzLCAnWmFwU3RyZWFtUGlwZWxpbmUnLCB7XG4gICAgICBwaXBlbGluZU5hbWU6ICdaYXBTdHJlYW1EZXBsb3ltZW50UGlwZWxpbmUnLFxuICAgICAgY3Jvc3NBY2NvdW50S2V5czogZmFsc2UsXG4gICAgfSk7XG5cbiAgICAvLyBHaXRIdWIgc291cmNlIGFjdGlvblxuICAgIGNvbnN0IHNvdXJjZUFjdGlvbiA9IG5ldyBjb2RlcGlwZWxpbmVfYWN0aW9ucy5HaXRIdWJTb3VyY2VBY3Rpb24oe1xuICAgICAgYWN0aW9uTmFtZTogJ0dpdEh1Yl9Tb3VyY2UnLFxuICAgICAgb3duZXI6ICdZaWJpbkxvbmcnLFxuICAgICAgcmVwbzogJ1phcFN0cmVhbScsXG4gICAgICBicmFuY2g6ICdtYWluJyxcbiAgICAgIG9hdXRoVG9rZW46IGdpdGh1YlRva2VuLnNlY3JldFZhbHVlLFxuICAgICAgb3V0cHV0OiBzb3VyY2VPdXRwdXQsXG4gICAgfSk7XG5cbiAgICAvLyBCdWlsZCBhbmQgZGVwbG95IGFjdGlvblxuICAgIGNvbnN0IGJ1aWxkQWN0aW9uID0gbmV3IGNvZGVwaXBlbGluZV9hY3Rpb25zLkNvZGVCdWlsZEFjdGlvbih7XG4gICAgICBhY3Rpb25OYW1lOiAnQnVpbGRfYW5kX0RlcGxveScsXG4gICAgICBwcm9qZWN0OiBidWlsZFByb2plY3QsXG4gICAgICBpbnB1dDogc291cmNlT3V0cHV0LFxuICAgIH0pO1xuXG4gICAgLy8gQWRkIHN0YWdlcyB0byB0aGUgcGlwZWxpbmVcbiAgICBwaXBlbGluZS5hZGRTdGFnZSh7XG4gICAgICBzdGFnZU5hbWU6ICdTb3VyY2UnLFxuICAgICAgYWN0aW9uczogW3NvdXJjZUFjdGlvbl0sXG4gICAgfSk7XG5cbiAgICBwaXBlbGluZS5hZGRTdGFnZSh7XG4gICAgICBzdGFnZU5hbWU6ICdCdWlsZEFuZERlcGxveScsXG4gICAgICBhY3Rpb25zOiBbYnVpbGRBY3Rpb25dLFxuICAgIH0pO1xuICB9XG59Il19