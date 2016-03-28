import math
import requests
import time
import xml.etree.ElementTree as ET

# from .config import config


class S3:
    def __init__(self, bucket, endpoint_url=None):
        """
        The S3 class provides methods to manage files from a bucket.

        :param bucket: The bucket to use
        :type bucket: String
        """
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        if not self._endpoint_url:
            self._endpoint_url = 'http://%s.s3.amazonaws.com' % bucket

    def put(self, data, key):
        """
        Upload a file to the S3 bucket

        :param data: The content of the file to upload
        :type data: any
        :param key: The name of the file to post
        :type key: String
        :return: The url of the uploaded file
        :rtype: String
        """
        url = self._endpoint_url + '/' + key
        r = requests.put(url, data=data)
        r.raise_for_status()
        return url

    def generate_key(self, seed, ext):
        """
        Generate a key supposed to be unique in the bucket

        :param self: The seed to use to generate the name
        :type self: String
        :param ext: The file extension
        :type ext: String
        :return: A key to upload a new file
        :rtype: String
        """
        return "{0}-{1}.{2}".format(
            seed,
            int(math.floor(time.time())),
            ext
        )

    def list_bucket(self):
        """
        Return the list of the files in the bucket

        :return: List of files
        :rtype: List
        """
        url = self._endpoint_url + '/'
        r = requests.get(url)
        r.raise_for_status()
        xml = ET.fromstring(r.text)

        files = []
        for child in xml:
            if child.tag.endswith('Contents'):
                file = {}

                # Convert the XML data to python object
                for file_data in child:
                    if file_data.tag.endswith('Key'):
                        file['Key'] = file_data.text
                    if file_data.tag.endswith('LastModified'):
                        file['LastModified'] = file_data.text
                    if file_data.tag.endswith('Size'):
                        file['Size'] = file_data.text

                files.append(file)

        return files
