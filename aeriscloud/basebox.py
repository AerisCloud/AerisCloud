from .config import basebox_bucket
from .s3 import S3


def baseboxes():
    """
    Retrieve a list of base boxes from the remote S3 bucket, sorted by infra

    :return: dict[str,str]
    """
    if not basebox_bucket():
        return {}

    # retrieve our bucket
    bucket = S3(basebox_bucket())

    boxes = {}
    current_infra = None
    for obj in bucket.list_bucket():
        # ignore objects that are not boxes
        if not obj['Key'].endswith('.box'):
            continue

        infra, box = obj['Key'].split('/')

        if current_infra != infra:
            current_infra = infra
            boxes[current_infra] = []

        boxes[current_infra].append(box)

    return boxes
