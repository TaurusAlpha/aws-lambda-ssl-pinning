# AWS Lambda SSL Pinning

This project contains an AWS Lambda function that performs SSL pinning by verifying the server's certificate chain against stored certificates in AWS Secrets Manager. It is designed to enhance security by ensuring that the server's identity is authentic.

## Features

- Retrieves server certificate chains using SSL.
- Compares the retrieved certificates with stored certificates.
- Generates IAM policies to allow or deny access based on certificate validation.
- Includes CloudFormation template for easy deployment.
- Supports providing certificates during deployment or updating them later.

## Prerequisites

- Python 3.13 or higher.
- AWS account with appropriate permissions.
- AWS CLI installed and configured.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/aws-lambda-ssl-pinning.git
   cd aws-lambda-ssl-pinning
   ```

2. Make the deployment script executable:
   ```bash
   chmod +x deploy.sh
   ```

3. Deploy using the script (basic method):
   ```bash
   ./deploy.sh --url example.com --port 443 --stack-name my-ssl-pinning
   ```

4. After deployment, update the certificates in AWS Secrets Manager:
   - Navigate to Secrets Manager in the AWS console
   - Find the secret created by the CloudFormation stack
   - Update the ServerCert, IntermediateCert, and RootCert values with the base64 encoded certificates

## Providing Certificates During Deployment

You can also provide certificates directly during deployment:

```bash
./deploy.sh --url example.com --port 443 --stack-name my-ssl-pinning \
  --server-cert "$(cat server.pem | base64)" \
  --intermediate-cert "$(cat intermediate.pem | base64)" \
  --root-cert "$(cat root.pem | base64)"
```

## CloudFormation Deployment Parameters

The CloudFormation template accepts the following parameters:

- **SecretName**: Name of the secret in AWS Secrets Manager for storing certificates
- **LoggerLevel**: Logging level for the Lambda function (DEBUG, INFO, WARNING, ERROR)
- **ServerURL**: URL of the server to perform SSL pinning against
- **ServerPort**: Port to connect to on the server (default: 443)
- **LambdaFunctionName**: Name for the deployed Lambda function
- **ServerCertificate**: Base64 encoded server certificate (optional)
- **IntermediateCertificate**: Base64 encoded intermediate certificate (optional)
- **RootCertificate**: Base64 encoded root certificate (optional)

## Using with API Gateway

To use this Lambda function as an API Gateway custom authorizer:

1. Create a new Custom Authorizer in API Gateway
2. Select the deployed Lambda function
3. Configure the Identity Source as desired
4. The Lambda will evaluate the certificate chain and return an appropriate IAM policy

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.