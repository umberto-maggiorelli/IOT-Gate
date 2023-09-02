from flask import Flask
from flask_restful import Resource, Api, request
from uuid import UUID
from marshmallow import Schema, fields, ValidationError
from database_manager import *
from telegram_bot import *
import requests
from pprint import pprint


PLATE_RECOGNIZER_API_KEY = 'xxx'

app = Flask(__name__)
api = Api(app)
basePath = '/api/v1'

db_mng = DBManager()
bot_mng = TelegramBotManager()

class AccessSchema(Schema):
    owner = fields.Str(validate=lambda x: len(x) <= 25)

class GateNameSchema(Schema):
    gate_name = fields.Str(validate=lambda x: 4 <= len(x) <= 20)

class UserSchema(Schema):
    username = fields.Str(validate=lambda x: 5 <= len(x) <= 20)
    gate_name = fields.Str(validate=lambda x: 4 <= len(x) <= 20)

def validate_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj)==uuid_to_test

def validate_access_plate(json):
    try:
        ret = AccessSchema().load(json)
        return ret
    except ValidationError:
        return False

def validate_gate_name(json):
    try:
        ret = GateNameSchema().load(json)
        return ret
    except ValidationError:
        return False

def validate_user_informations(json):
    try:
        ret = UserSchema().load(json)
        return ret
    except ValidationError:
        return False

def validate_plate(plate):
    if len(plate) == 7:
        return True
    return False

def validate_chat(chat_id):
    try:
        if (len(chat_id) < 9):
            return False
        chat = int(chat_id)
        return chat
    except ValueError:
        return False

class CleanEventsDB(Resource):
    def get(self):
        db_mng._dump_events()

class CleanPlatesDB(Resource):
    def get(self):
        db_mng._dump_plates()

class CleanUsersDB(Resource):
    def get(self):
        db_mng._dump_users()

class CleanGatesDB(Resource):
    def get(self):
        db_mng._dump_gates()

class GateAccess(Resource):
    def get(self, gate, plate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        if not validate_plate(plate):
            print("Not a valid Plate")
            return None, 400
        
        return_value = db_mng.get_plate(gate, plate)

        if return_value is None:
            return None, 404

        return return_value, 200

    def post(self, gate, plate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        if not validate_plate(plate):
            print("Not a valid Plate")
            return None, 400

        if not request.is_json:
            print("Request not in JSON format")
            return None, 400
        
        json = request.get_json()
        body = validate_access_plate(json)

        if not body:
            print("Error in body validation")
            return None, 400
        
        if not db_mng.get_gate_id(gate):
            print("Gate not Found")
            return None, 404

        duplicate = db_mng.get_plate(gate, plate)
        if duplicate is not None:
            print("Access already inserted")
            return None, 409

        return_value = db_mng.insert_plate(gate, plate, body)
        return return_value, 201

    def delete(self, gate, plate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        if not validate_plate(plate):
            print("Not a valid Plate")
            return None, 400

        return_value = db_mng.delete_plate(gate, plate)
        if not return_value:
            print("Plate not Found")
            return None, 404
        return 'OK', 200

class GateAccessGroup(Resource):
    def get(self, gate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        return_value = db_mng.get_plates(gate)

        if return_value is None:
            return None, 404

        return return_value, 200

class GateInformation(Resource):
    def get(self, chat):
        if not validate_chat(chat):
            print("Chat ID not valid")
            return None, 400
        
        return_value = db_mng.get_linked_gates_id(chat)

        if return_value is None:
            return None, 404

        return return_value, 200

class UserInformation(Resource):
    def get(self, gate, chat):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400
        
        if not validate_chat(chat):
            print("Chat ID not valid")
            return None, 400

        return_value = db_mng.get_user(gate, chat)

        if return_value is None:
            return None, 404

        return return_value, 200
    
    def post(self, gate, chat):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400
        
        if not validate_chat(chat):
            print("Chat ID not valid")
            return None, 400

        if not request.is_json:
            print("Request not in JSON format")
            return None, 400
        
        json = request.get_json()
        body = validate_user_informations(json)

        if not body:
            print("Error in body validation")
            return None, 400

        if not db_mng.get_gate_id(gate):
            print("Gate not Found")
            return None, 404

        if db_mng.get_user(gate, chat) is not None:
            print('User already associated to the Gate')
            return None, 409
        
        if db_mng.get_detail_user(chat, body['gate_name']) is not None:
            print('Gate\'s name already associated to a Gate')
            return None, 412

        return_value = db_mng.insert_user(gate, chat, body)
        return return_value, 201

    def delete(self, gate, chat):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        if not validate_chat(chat):
            print("Chat ID not valid")
            return None, 400

        return_value = db_mng.delete_user(gate, chat)

        if not return_value:
            print("User not Found")
            return None, 404

        return 'OK', 200

    def patch(self, gate, chat):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400
            
        if not validate_chat(chat):
            print("Chat ID not valid")
            return None, 400

        json = request.get_json()
        body = validate_gate_name(json)

        if not body:
            print("Error in body validation")
            return None, 400
        
        if db_mng.get_detail_user(chat, body['gate_name']) is not None:
            print('Gate\'s name already associated to a Gate')
            return None, 412

        return_value = db_mng.update_user(gate, chat, body)

        if not return_value:
            print("User not Found")
            return None, 404

        return return_value, 200

class UserGroup(Resource):
    def get(self, gate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        return_value = db_mng.get_users(gate)

        if return_value is None:
            return None, 404

        return return_value, 200

class Logger(Resource):
    def get(self, gate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        return_value = db_mng.get_recent_events(gate)

        if return_value is None:
            return None, 404

        return return_value, 200

    def post(self, gate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        data = request.form
        if not data:
            print("Data not supported")
            return None, 400

        if not db_mng.get_gate_id(gate):
            print("Gate UUID not found")
            return None, 404
        
        return_value = db_mng.insert_event(gate, data)
        return return_value, 201

class PictureHandler(Resource):
    def post(self, gate):
        if not validate_uuid(gate):
            print("Gate ID not in UUID format")
            return None, 400

        data = request.data
        if not data:
            print("Data not supported")
            return None, 400

        if not db_mng.get_gate_id(gate):
            print("Gate not found")
            return None, 404
        
        plate_recognizer_response = requests.post(
            'https://api.platerecognizer.com/v1/plate-reader/',
            data=dict(regions=['it']),  # Optional
            files=dict(upload=data),
            headers={'Authorization': f'Token {PLATE_RECOGNIZER_API_KEY}'})
        response = plate_recognizer_response.json()['results']

        if not plate_recognizer_response.status_code == 201 or not response:
            print('Plate not recognized')
            return None, 409
        
        plate = response[0]['plate']
        
        if not validate_plate(plate):
            print("Not a valid Plate")
            return None, 400

        log = db_mng.insert_log(gate, plate, data)
        users_ids = db_mng.get_users_ids(gate)
        return_value = db_mng.get_plate(gate, plate)
        print(users_ids)

        for chat_id in users_ids:
            bot_mng.send_photo(chat_id, data, f'Targa: {plate.upper()}\nData e Ora: {log["timestamp"]}')
            if not return_value:
                bot_mng.send_message(chat_id, '🔴 Accesso Negato')
            else:
                bot_mng.send_message(chat_id, '🟢 Accesso Consentito')

        if return_value is None:
            print('Plate not allowed')
            return None, 404

        return return_value, 200

api.add_resource(CleanEventsDB, f'{basePath}/iot-gate/events/clean')
api.add_resource(CleanPlatesDB, f'{basePath}/iot-gate/accesses/clean')
api.add_resource(CleanUsersDB, f'{basePath}/iot-gate/users/clean')
api.add_resource(CleanGatesDB, f'{basePath}/iot-gate/gates/clean')
api.add_resource(PictureHandler, f'{basePath}/iot-gate/events/<string:gate>')
api.add_resource(Logger, f'{basePath}/iot-gate/events/logs/<string:gate>')
api.add_resource(GateAccess, f'{basePath}/iot-gate/accesses/<string:gate>/<string:plate>')
api.add_resource(GateAccessGroup, f'{basePath}/iot-gate/accesses/<string:gate>')
api.add_resource(GateInformation, f'{basePath}/iot-gate/gates/<string:chat>')
api.add_resource(UserGroup, f'{basePath}/iot-gate/users/<string:gate>')
api.add_resource(UserInformation, f'{basePath}/iot-gate/users/<string:gate>/<string:chat>')

if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)
