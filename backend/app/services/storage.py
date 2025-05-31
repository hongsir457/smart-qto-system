import boto3
import os
from typing import BinaryIO

print("S3_ENDPOINT:", os.getenv("S3_ENDPOINT"))

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)

def upload_fileobj_to_s3(file_obj: BinaryIO, object_name: str) -> str:
    """
    上传文件对象到 Sealos S3，对象名为 object_name。
    返回文件的 S3 访问 URL。
    """
    print(f"[S3] 开始上传: {object_name} -> {S3_BUCKET} @ {S3_ENDPOINT}")
    s3_client.upload_fileobj(file_obj, S3_BUCKET, object_name)
    print(f"[S3] 上传成功: {object_name}")
    return f"{S3_ENDPOINT}/{S3_BUCKET}/{object_name}" 