from requests import get

chat1 = "528243245"
chat2 = "382370960"
url = f'http://127.0.0.1:5000/api/v1/iot-gate/gates/{chat1}'

""" GET """
get_response = get(url)
print(get_response.__dict__)
print(get_response)
print(get_response.text)