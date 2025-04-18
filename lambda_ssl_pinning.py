import ssl
import socket
from typing import Any
import boto3
import json
import os
import logging
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.getenv("logger_level", "INFO")))

# Initialize AWS clients
secrets_client = boto3.client("secretsmanager")


@dataclass
class ServerConfig:
    URL: str
    Port: int
    ServerCert: str
    IntermediateCert: str
    RootCert: str

    def __post_init__(self):
        self.ServerCert = "".join(self.ServerCert.split())
        self.IntermediateCert = "".join(self.IntermediateCert.split())
        self.RootCert = "".join(self.RootCert.split())


def get_certificate_chain(hostname: str, port: int = 443) -> list[str]:
    """
    Retrieves the full certificate chain from a specified website.

    Args:
        hostname (str): The domain of the website.
        port (int): The port to connect to (default is 443).

    Returns:
        List[str]: A list of PEM-encoded certificates in the chain.
    """
    try:
        # Create an SSL context
        context = ssl.create_default_context()

        # Create a socket and wrap it in an SSL context
        with socket.create_connection((hostname, port)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Retrieve the full verified certificate chain
                cert_chain = ssock.get_verified_chain()

                # Convert each certificate from DER to PEM format
                pem_certificates = [
                    ssl.DER_cert_to_PEM_cert(cert) for cert in cert_chain
                ]

                return pem_certificates
    except Exception as e:
        logger.error(f"Failed to retrieve certificate chain for {hostname}:{port}: {e}")
        return []


def generate_policy(principal_id, effect, resource) -> dict[str, Any]:
    """
    Generate an IAM policy for API Gateway.

    Args:
        principal_id (str): The principal user identifier.
        effect (str): The effect of the policy, either 'Allow' or 'Deny'.
        resource (str): The resource ARN that the policy applies to.

    Returns:
        dict[str, Any]: The generated IAM policy document.
    """
    # Generate an IAM policy for API Gateway
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}
            ],
        },
    }


def extract_certificate(cert_chain: list[str], index: int) -> str | None:
    """
    Safely extract a certificate from the chain by index and remove all whitespaces.

    Args:
        cert_chain (list[str]): The list of PEM-encoded certificates.
        index (int): The index of the certificate to extract.

    Returns:
        str | None: The certificate with all whitespaces removed if present, otherwise None.
    """
    if len(cert_chain) > index:
        return "".join(cert_chain[index].split())
    return None


def lambda_handler(event, context) -> dict[str, Any]:
    logger.info(f"Received event: {event}")
    requester_ip = event["requestContext"]["identity"]["sourceIp"]

    # Retrieve the secret name from environment variables
    secret_name = os.getenv("secret_name")
    if not secret_name:
        logger.error("Environment variable is not set or is None.")
        return generate_policy(requester_ip, "Deny", event["methodArn"])

    # Retrieve server configuration from Secrets Manager
    try:
        secrets_dict = json.loads(
            secrets_client.get_secret_value(SecretId=secret_name)["SecretString"]
        )
        server_config = ServerConfig(**secrets_dict)
    except Exception as e:
        logger.error(f"Error retrieving server config: {e}")
        return generate_policy("user", "Deny", event["methodArn"])

    logger.info(
        f"Retrieving the verified certificate chain for {server_config.URL}:{server_config.Port}"
    )
    retrieved_cert_chain = get_certificate_chain(server_config.URL, server_config.Port)

    if not retrieved_cert_chain:
        logger.error("Failed to retrieve any certificates from the server.")
        return generate_policy(requester_ip, "Deny", event["methodArn"])

    # Extract certificates from the chain
    server_cert = extract_certificate(retrieved_cert_chain, 0)
    intermediate_cert = extract_certificate(retrieved_cert_chain, 1)
    root_cert = extract_certificate(retrieved_cert_chain, 2)

    logger.debug(f"Received server certificate: {server_cert}")
    logger.debug(f"Received intermediate certificate: {intermediate_cert}")
    logger.debug(f"Received root certificate: {root_cert}")

    # Compare the retrieved certificates with the stored certificates
    cert_results = {
        "Server Certificate": server_config.ServerCert == server_cert,
        "Intermediate Certificate": server_config.IntermediateCert == intermediate_cert,
        "Root Certificate": server_config.RootCert == root_cert,
    }

    for cert_type, match in cert_results.items():
        logger.info(f"{cert_type} match: {match}")

    # Determine access based on certificate matching
    if all(cert_results.values()):
        return generate_policy(requester_ip, "Allow", event["methodArn"])
    else:
        return generate_policy(requester_ip, "Deny", event["methodArn"])
