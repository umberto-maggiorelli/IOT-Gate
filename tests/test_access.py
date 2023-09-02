from requests import post, get, delete

gate1 = 'ef6ae607-3e36-4878-ad00-22a2c148b12b'
gate2 = '18b31260-0db1-4433-8d37-f568540042f9'
plate1 = "GA129KM"
plate2 = "CS000CJ"
url = f'http://127.0.0.1:5000/api/v1/iot-gate/accesses/{gate2}'

# """ POST """
# post_response = post(url+f'/{plate1}',json={'owner': 'Umberto'})
# print(post_response.__dict__)
# print(post_response)
# print(post_response.text)

# """ GET """
# get_response = get(url+f'/{plate1}')
# print(get_response.__dict__)
# print(get_response)
# print(get_response.text)

# """ DELETE """
# delete_response = delete(url+f'/{plate1}')
# print(delete_response.__dict__)
# print(delete_response)
# print(delete_response.text)

# """ ACCESS GROUPS """

# """ GET """
# get_group_response = get(url)
# print(get_group_response.__dict__)
# print(get_group_response)
# print(get_group_response.text)
