#!/usr/bin/env python3
import boto3
import subprocess
import os
import io
import time

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

while True:
    try:
        if len(bucket.meta.client.list_objects(Bucket=bucket.name, Delimiter='/')["CommonPrefixes"]) <= 1:
            print("Waiting")
            time.sleep(10)
            continue
        key = bucket.meta.client.list_objects(Bucket=bucket.name, Delimiter='/')["CommonPrefixes"][0]
        image = key["Prefix"]
        print(image)
        timestamp = 0
        imagebytestring = b''
        bytestringfile = io.BytesIO()
        # while len(bucket.objects.filter(Prefix=image)) < 80:
        #     print(len(bucket.objects.filter(Prefix=image)))
        #     time.sleep(10)
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

        with open(filename, "wb") as imagefile:
            imagefile.write(imagebytestring)

        cmd = "./darknet detect cfg/"+model+".cfg weights/"+model+".weights -thresh " + confidence_level + " " + filename
        process = subprocess.run(cmd.split(), capture_output=True, text=True)
        if process.returncode == 0 and "Cannot load image" not in process.stderr:
            # print("stderr:")
            # print(process.stderr)
            output = process.stdout
            numPeople = 0;
            for line in output.split("\n"):
                print(line)
                if line.split(":")[0] == "person":
                    numPeople += 1;
            print("NumPeople:", numPeople)

            if store_in_DB_flag:
                print("Uploading to AWS")
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table(TABLE_NAME)
                table.put_item(
                    Item={
                        'timestamp': timestamp,
                        'numpeople': numPeople,
                        'myid': 'mcavanag'
                    }
                )
        else:
            print(process.stderr)
        if delete_local_flag:
            os.remove(filename)
        if delete_aws_flag:
            bucket.delete_objects(Delete = {"Objects": [{"Key": image}]})
    except:
        pass
