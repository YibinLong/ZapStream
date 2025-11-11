#!/usr/bin/env python3
"""
Script to package the ZapStream Lambda function.
"""
import os
import sys
import subprocess
import tempfile
import shutil
import zipfile

def create_lambda_zip():
    """Create a zip file for AWS Lambda deployment."""

    # Install dependencies in a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        deps_dir = os.path.join(temp_dir, 'deps')
        os.makedirs(deps_dir, exist_ok=True)

        print("Installing Lambda dependencies...")
        subprocess.run([
            sys.executable, '-m', 'pip', 'install',
            '-r', 'requirements.txt',
            '-t', deps_dir,
            '--no-deps'
        ], check=True)

        # Install additional dependencies needed for Lambda
        lambda_deps = [
            'mangum',
            'fastapi',
            'sqlmodel',
            'aiosqlite',
            'boto3',
            'botocore',
            'pydantic',
            'pydantic-settings',
            'uvicorn[standard]',
            'python-multipart'
        ]

        for dep in lambda_deps:
            print(f"Installing {dep}...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                dep,
                '-t', deps_dir
            ], check=True)

        # Create zip file
        print("Creating lambda.zip...")
        with zipfile.ZipFile('lambda.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add dependencies
            for root, dirs, files in os.walk(deps_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

            # Add backend files
            for root, dirs, files in os.walk('backend'):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(root, file)
                        zipf.write(file_path, arcname)

            # Add lambda handler
            zipf.write('lambda_function.py', 'lambda_function.py')

            # Add __init__.py files to make packages
            zipf.writestr('__init__.py', '')
            zipf.writestr('backend/__init__.py', '')
            zipf.writestr('backend/storage/__init__.py', '')
            zipf.writestr('backend/routes/__init__.py', '')

        print("lambda.zip created successfully!")

if __name__ == "__main__":
    create_lambda_zip()