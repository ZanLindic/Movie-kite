import boto3
from urllib.parse import urlparse
import requests
import uuid
import os

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("minio_endpoint"),
    aws_access_key_id=os.getenv("minio_access_key"),
    aws_secret_access_key=os.getenv("minio_secret_key"),
)


BUCKET = "user-05"


def _extract_bucket_and_key(poster_url):
    parsed_url = urlparse(poster_url)
    path_parts = parsed_url.path.lstrip("/").split("/", 1)
    if len(path_parts) != 2:
        raise Exception("Invalid poster URL format")
    return path_parts[0], path_parts[1]


def fetch_poster_bytes(poster_url):
    if not poster_url:
        raise ValueError("Missing poster URL")

    parsed_url = urlparse(poster_url)
    minio_endpoint = (os.getenv("minio_endpoint") or "").rstrip("/")
    minio_netloc = urlparse(minio_endpoint).netloc

    if minio_netloc and parsed_url.netloc == minio_netloc:
        bucket_name, object_key = _extract_bucket_and_key(poster_url)
        obj = s3.get_object(Bucket=bucket_name, Key=object_key)
        content = obj["Body"].read()
        content_type = obj.get("ContentType") or "image/jpeg"
        return content, content_type

    response = requests.get(poster_url, timeout=15)
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "image/jpeg")


def upload_poster_from_url(image_url):
    if not image_url or not isinstance(image_url, str):
        raise ValueError("Invalid image URL")

    if not image_url.lower().startswith(("http://", "https://")):
        raise ValueError("Image URL must start with http:// or https://")

    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.SSLError as ssl_err:
        try:
            print("SSL error when downloading image, retrying without verification:", ssl_err)
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(image_url, timeout=10, verify=False)
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Failed to download image after disabling SSL verification: {e}")
    except Exception as e:
        raise Exception(f"Failed to download image: {e}")

    filename = f"{uuid.uuid4()}.jpg"

    s3.put_object(
        Bucket=BUCKET,
        Key=filename,
        Body=response.content,
        ContentType="image/jpeg"
    )

    return f"{os.getenv('minio_endpoint')}/{BUCKET}/{filename}"


def delete_poster(poster_url):
    if not poster_url:
        return

    bucket_name, object_key = _extract_bucket_and_key(poster_url)

    s3.delete_object(
        Bucket=bucket_name,
        Key=object_key
    )