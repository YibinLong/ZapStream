import { Construct } from 'constructs';
import { Stack, StackProps, Duration } from 'aws-cdk-lib';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export class ZapStreamPipelineStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // Get GitHub token from Secrets Manager
    const githubToken = secretsmanager.Secret.fromSecretNameV2(
      this,
      'GitHubToken',
      'github-token'
    );

    // S3 bucket for the website (already exists)
    const websiteBucket = s3.Bucket.fromBucketName(
      this,
      'WebsiteBucket',
      'zapstream-app-1762821749'
    );

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