from requests import post, get, delete, patch

gate1 = '18b31260-0db1-4433-8d37-f568540042f9'
gate2 = 'ef6ae607-3e36-4878-ad00-22a2c148b12b'
chat1 = '528243245'
chat2 = '382370960'
plate = 'FT852OP'
url = f'http://127.0.0.1:5000/api/v1/iot-gate/users/{gate1}'

""" USER """

""" POST """
post_response = post(url+f'/{chat1}', json = {'username': 'User', 'gate_name': 'Cancello di Casa'})
print(post_response.__dict__)
print(post_response)

""" GET """
get_response = get(url+f'/{chat1}')
print(get_response.__dict__)
print(get_response)
print(get_response.text)

""" PATCH """
delete_response = patch(url+f'/{chat1}', json={'gate_name': 'Casa'})
print(delete_response.__dict__)
print(delete_response)
print(delete_response.text)

""" DELETE """
delete_response = delete(url+f'/{chat2}')
print(delete_response.__dict__)
print(delete_response)
print(delete_response.text)

""" USER GROUPS """

""" GET """
get_group_response = get(url)
print(get_group_response.__dict__)
print(get_group_response)
print(get_group_response.text)

