#!/bin/bash

# Set default values
STACK_NAME="aws-lambda-ssl-pinning-stack"
REGION="us-east-1"

# Display help information
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Deploy the AWS Lambda SSL Pinning function stack"
    echo ""
    echo "Options:"
    echo "  -n, --stack-name NAME    Set CloudFormation stack name (default: aws-lambda-ssl-pinning-stack)"
    echo "  -r, --region REGION      Set AWS region (default: us-east-1)"
    echo "  -u, --url URL            Set server URL for SSL pinning (required)"
    echo "  -p, --port PORT          Set server port (default: 443)"
    echo "  -s, --secret NAME        Set secret name (default: ServerSSLConfig)"
    echo "  -l, --log-level LEVEL    Set log level (default: INFO)"
    echo "  --server-cert CERT       Base64 encoded server certificate"
    echo "  --intermediate-cert CERT Base64 encoded intermediate certificate"
    echo "  --root-cert CERT         Base64 encoded root certificate"
    echo "  -h, --help               Display this help and exit"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n | --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r | --region)
            REGION="$2"
            shift 2
            ;;
        -u | --url)
            SERVER_URL="$2"
            shift 2
            ;;
        -p | --port)
            SERVER_PORT="$2"
            shift 2
            ;;
        -s | --secret)
            SECRET_NAME="$2"
            shift 2
            ;;
        -l | --log-level)
            LOGGER_LEVEL="$2"
            shift 2
            ;;
        --server-cert)
            SERVER_CERTIFICATE="$2"
            shift 2
            ;;
        --intermediate-cert)
            INTERMEDIATE_CERTIFICATE="$2"
            shift 2
            ;;
        --root-cert)
            ROOT_CERTIFICATE="$2"
            shift 2
            ;;
        -h | --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check for required parameters
if [ -z "$SERVER_URL" ]; then
    echo "ERROR: Server URL is required"
    show_help
    exit 1
fi

# Set default values for optional parameters
SERVER_PORT=${SERVER_PORT:-443}
SECRET_NAME=${SECRET_NAME:-ServerSSLConfig}
LOGGER_LEVEL=${LOGGER_LEVEL:-INFO}

# Check if AWS CLI is installed
if ! command -v aws &>/dev/null; then
    echo "ERROR: AWS CLI is not installed. Please install it and configure your credentials."
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "ERROR: AWS CLI is not configured. Please run 'aws configure' to set up your credentials."
    exit 1
fi

# Prepare parameter overrides
PARAMS="ServerURL=$SERVER_URL ServerPort=$SERVER_PORT SecretName=$SECRET_NAME LoggerLevel=$LOGGER_LEVEL"

# Add certificate parameters if provided
if [ -n "$SERVER_CERTIFICATE" ]; then
    PARAMS="$PARAMS ServerCertificate=$SERVER_CERTIFICATE"
fi

if [ -n "$INTERMEDIATE_CERTIFICATE" ]; then
    PARAMS="$PARAMS IntermediateCertificate=$INTERMEDIATE_CERTIFICATE"
fi

if [ -n "$ROOT_CERTIFICATE" ]; then
    PARAMS="$PARAMS RootCertificate=$ROOT_CERTIFICATE"
fi

# Deploy the CloudFormation stack
echo "Deploying stack: $STACK_NAME to region: $REGION"
if aws cloudformation deploy \
    --template-file template.yaml \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "$PARAMS"; then
    echo "Deployment successful!"

    # Provide different message based on whether certificates were provided
    if [ -z "$SERVER_CERTIFICATE" ] && [ -z "$INTERMEDIATE_CERTIFICATE" ] && [ -z "$ROOT_CERTIFICATE" ]; then
        echo "You need to update the certificates in AWS Secrets Manager."
        echo "Use the AWS console to navigate to Secrets Manager and update the '$SECRET_NAME' secret."
    else
        echo "Certificates were provided during deployment. The SSL Pinning function is ready to use."
    fi
else
    echo "ERROR: Deployment failed! Check the AWS CloudFormation console for more details."
fi
