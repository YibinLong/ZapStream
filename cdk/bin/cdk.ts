#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ZapStreamPipelineStack } from '../lib/zapstream-pipeline-stack';

const app = new cdk.App();
new ZapStreamPipelineStack(app, 'ZapStreamPipelineStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});