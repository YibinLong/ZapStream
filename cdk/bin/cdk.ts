#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ZapStreamPipelineStack } from '../lib/zapstream-pipeline-stack';
import { ZapStreamBackendStack } from '../lib/zapstream-backend-stack';

const app = new cdk.App();

// Frontend deployment pipeline (existing)
new ZapStreamPipelineStack(app, 'ZapStreamPipelineStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

// Backend infrastructure
new ZapStreamBackendStack(app, 'ZapStreamBackendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});