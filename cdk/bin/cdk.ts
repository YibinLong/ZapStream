#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ZapStreamPipelineStack } from '../lib/zapstream-pipeline-stack';
import { ZapStreamServerlessStack } from '../lib/zapstream-serverless-stack';

const app = new cdk.App();

// Frontend deployment pipeline (existing)
new ZapStreamPipelineStack(app, 'ZapStreamPipelineStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

// Serverless Backend infrastructure (no Docker required)
new ZapStreamServerlessStack(app, 'ZapStreamServerlessStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});