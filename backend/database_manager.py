from google.cloud import firestore
import os
import datetime
import hashlib
import pytz
import base64


def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f'Deleting doc {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

class DBManager(object):
    def __init__(self):
        self.db = firestore.Client()
        self.events_collection_ref = self.db.collection('events')
        self.plates_collection_ref = self.db.collection('plates')
        self.users_collection_ref = self.db.collection('users')
        self.gates_collection_ref = self.db.collection('gates')
        self.path = 'local-database/images/'
        self._create_path()

    def _create_path(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            print("The path './local-database/images' has been created.\n")
    
    def _dump_events(self):
        delete_collection(self.events_collection_ref, 10)

    def _dump_plates(self):
        delete_collection(self.plates_collection_ref, 10)

    def _dump_users(self):
        delete_collection(self.users_collection_ref, 10)

    def _dump_gates(self):
        delete_collection(self.gates_collection_ref, 10)

    """" GATE """
    def get_gate_id(self, gate_id):
        try:
            ref = self.gates_collection_ref.where("id", "==", gate_id).get()
            if ref:
                doc = ref[0].to_dict()
                return doc['id']
        except ValueError:
            return None
    
    """ USER """
    def get_linked_gates_id(self, chat_id):
        try:
            ref = self.users_collection_ref.where("chat_id", "==", chat_id).get()
            if ref:
                return [ doc.to_dict() for doc in ref]
        except ValueError:
            return None

    def get_user(self, gate, chat):
        try:
            ref = self.users_collection_ref.where("gate_id", "==", gate) \
                    .where("chat_id", "==", chat).get()
            if ref:
                return ref[0].to_dict()
        except ValueError:
            return None

    def get_detail_user(self, chat, gate_name):
        try:
            ref = self.users_collection_ref.where("chat_id", "==", chat) \
                    .where("gate_name", "==", gate_name).get()
            if ref:
                return ref[0].to_dict()
        except ValueError:
            return None

    def insert_user(self, gate, chat, body):
        ref = self.users_collection_ref.document()
        ref.set({
            'chat_id': chat,
            'gate_name': body['gate_name'],
            # 'name': body['name'],
            # 'lastname': body['lastname'],
            'username': body['username'],
            'gate_id': gate
        })

        return {'chat_id': chat, 'username': body['username'], 'gate_id': gate}
    
    def get_users(self, gate):
        try:
            ref = self.users_collection_ref.where("gate_id", "==", gate).get()
            if ref:
                return [doc.to_dict() for doc in ref]
        except ValueError:
            return None
    
    def get_users_ids(self, gate):
        try:
            ref = self.users_collection_ref.where("gate_id", "==", gate).get()
            if ref:
                return [doc.to_dict()['chat_id'] for doc in ref]
        except ValueError:
            return None
    
    def delete_user(self, gate, chat):
        try:
            ref = self.users_collection_ref.where("gate_id", "==", gate) \
                .where("chat_id", "==", chat).get()
            if ref:
                for doc in ref:
                    self.users_collection_ref.document(doc.id).delete()
                return True
        except ValueError:
            return False
    
    def update_user(self, gate, chat, body):
        try:
            ref = self.users_collection_ref.where("gate_id", "==", gate) \
                .where("chat_id", "==", chat).get()
            if ref:
                doc = ref[0]
                self.users_collection_ref.document(doc.id).update({'gate_name': body['gate_name']})
                result = doc.to_dict()
                result['gate_name'] = body['gate_name']
                return result
        except ValueError:
            return False

    """ PLATE ACCESS """
    def get_plate(self, gate, plate):
        try:
            ref = self.plates_collection_ref.where("gate_id", "==", gate) \
                    .where("plate", "==", plate.lower()).get()
            if ref:
                return ref[0].to_dict()
        except ValueError:
            return None
    
    def get_plates(self, gate):
        try:
            ref = self.plates_collection_ref.where("gate_id", "==", gate).get()
            if ref:
                return [doc.to_dict() for doc in ref]
        except ValueError:
            return None

    def insert_plate(self, gate, plate, body):
        ref = self.plates_collection_ref.document()
        result = {
            'gate_id': gate,
            'plate': plate.lower(),
            'owner': body.get('owner', '')
        }
        ref.set(result)
        return result

    def delete_plate(self, gate, plate):
        try:
            ref = self.plates_collection_ref.where("gate_id", "==", gate) \
                    .where("plate", "==", plate.lower()).get()
            if ref:
                for doc in ref:
                    self.plates_collection_ref.document(doc.id).delete()
                return True
        except ValueError:
            return False

    """ EVENTS """
    def is_duplicate(self, image):
        encoded_string_image = str(image).encode()
        img_bytes = base64.decodebytes(encoded_string_image)
        img_hash = hashlib.md5(img_bytes).hexdigest()
        try:
            ref = self.events_collection_ref.where("hash", "==", img_hash).get()
            if ref:
                return True
        except ValueError:
            return False

    def get_recent_events(self, gate_id):
        try:
            last_minutes = datetime.datetime.now() - datetime.timedelta(minutes=20)
            timezone = pytz.timezone('Europe/Rome')
            last_minutes = datetime.datetime.fromtimestamp(last_minutes.timestamp(), timezone)
            ref = self.events_collection_ref.where("timestamp", ">=", last_minutes) \
                        .where("gate_id", "==", gate_id) \
                        .order_by("timestamp", direction=firestore.Query.DESCENDING).get()
            if ref:
                documents = [doc.to_dict() for doc in ref]
                for doc in documents:
                    doc['timestamp'] = str(datetime.datetime.fromtimestamp(doc['timestamp'].timestamp()))
                return documents
        except ValueError:
            return None

    def get_all_events(self):
        try:
            ref = self.events_collection_ref.stream()
            if ref:
                documents = [doc.to_dict() for doc in ref]
                for doc in documents:
                    doc['timestamp'] = str(datetime.datetime.fromtimestamp(doc['timestamp'].timestamp()))
                return documents
        except ValueError:
            return None
    
    def insert_event(self, gate, body):
        encoded_string_image = str(body['image']).encode()
        plate_string = body['plate']

        ref = self.events_collection_ref.document()
        timestamp = datetime.datetime.now().timestamp()
        timezone = pytz.timezone('Europe/Rome')
        img_bytes = base64.decodebytes(encoded_string_image)
        img_hash = hashlib.md5(img_bytes).hexdigest()

        with open(f'{self.path}/{timestamp}.jpg', "wb") as new_file:
            new_file.write(img_bytes)

        ref.set({
            'path': self.path,
            'plate_string': plate_string.lower(),
            'timestamp': datetime.datetime.fromtimestamp(timestamp, timezone),
            #'base64': encoded_string_image,
            'hash': img_hash,
            'gate_id': gate
        })

        # notifica utente nel bot con token 

        return {'path': self.path, 'plate_string': plate_string, 'timestamp': timestamp}
    
    def insert_log(self, gate, plate, data):
        ref = self.events_collection_ref.document()
        now = datetime.datetime.now()
        now_timestamp = now.timestamp()
        timezone = pytz.timezone('Europe/Rome')
        img_hash = hashlib.md5(data).hexdigest()

        with open(f'{self.path}/{now_timestamp}.jpg', "wb") as new_file:
            new_file.write(data)
        
        new_log = {
            'path': self.path,
            'plate_string': plate,
            'timestamp': now.astimezone(timezone),
            'hash': img_hash,
            'gate_id': gate
        }

        ref.set(new_log)
        new_log['timestamp'] = now.strftime("%b %d %Y %H:%M:%S")
        return new_log