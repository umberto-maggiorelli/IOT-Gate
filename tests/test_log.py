import requests

gate1 = 'ef6ae607-3e36-4878-ad00-22a2c148b12b'
gate2 = '18b31260-0db1-4433-8d37-f568540042f9'
IP_PORT = '127.0.0.1:5000'

url = f'http://{IP_PORT}/api/v1/iot-gate/events/{gate2}'
headers= {'Content-Type' : 'image/jpeg'}
img = open('test1.jpg', 'rb').read()

response = requests.post(url, data = img, headers=headers)
print(response.__dict__)
print(response)
print(response.text)
