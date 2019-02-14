#!/usr/bin/env python3
import boto3
import subprocess
import os
import io

os.chdir("/home/ec2-user/darknet")

BUCKET_TITLE = "nd-spectre-images"
TABLE_NAME = "nd-spectre-numpeople"

confidence_level = ".17"
model = "yolov3"

store_in_DB_flag = True
delete_local_flag = True
delete_aws_flag = True

# Let's use Amazon S3
s3 = boto3.resource('s3')
bucket = s3.Bucket(BUCKET_TITLE)

# for key in bucket.objects.filter(Delimiter='/'):
for key in bucket.meta.client.list_objects(Bucket=bucket.name, Delimiter='/')["CommonPrefixes"]:
    image = key["Prefix"]
    timestamp = 0
    imagebytestring = b''
    bytestringfile = io.BytesIO()
    for partObject in bucket.objects.filter(Prefix=image):
        if partObject.key == image:
            continue
        if timestamp == 0:
            timestamp = int(partObject.key.split("/")[1])
        bucket.download_fileobj(partObject.key, bytestringfile)
        imagebytestring += bytestringfile.getvalue()
        if (delete_aws_flag):
            bucket.delete_objects(Delete = {"Objects": [{"Key":partObject.key}]})

    filename = "spectredata/" + image[:-1] + ".jpg"

    try:
        with open(filename, "wb") as imagefile:
            imagefile.write(imagebytestring)

        cmd = "./darknet detect cfg/"+model+".cfg weights/"+model+".weights -thresh " + confidence_level + " " + filename + " 2>&1"
        output = subprocess.check_output(cmd.split())
        numPeople = 0;
        for line in output.decode("utf-8").split("\n"):
            print(line)
            if line.split(":")[0] == "person":
                numPeople += 1;
        print("NumPeople:", numPeople)

        if (store_in_DB_flag and "error" not in output.decode("utf-8")):
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(TABLE_NAME)
            table.put_item(
                Item={
                    'timestamp': timestamp,
                    'numpeople': numPeople,
                    'myid': 'mcavanag'
                }
            )
    

    if (delete_local_flag):
        os.remove(filename)
    if (delete_aws_flag):
        bucket.delete_objects(Delete = {"Objects": [{"Key": image}]})
