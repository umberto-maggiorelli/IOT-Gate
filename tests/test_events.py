from requests import post, get
import base64

gate = 'e46be3fd-4d79-41d9-8924-457b0d78d6b1'
url = f'http://127.0.0.1:5000/api/v1/iot-gate/events/logs/{gate}'

with open("test.jpg", "rb") as original_file:
    encoded_image = base64.b64encode(original_file.read())

""" POST """
post_response = post(url, data = {'image': encoded_image, "plate": "FX657JR"})
print(post_response.__dict__)
print(post_response)

""" GET """
get_response = get(url)
print(get_response.__dict__)
print(get_response)
print(get_response.text)
