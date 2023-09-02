import re
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

baseURL = 'http://127.0.0.1:5000/api/v1/iot-gate'
TELEGRAM_API_KEY = 'xxx'
bot = telebot.TeleBot(TELEGRAM_API_KEY)


# controlla se un utente è già registrato o no, se si aggiorna il suo username nel db e ritorna True, se no False
def registered_users_only(message):
    CHAT_ID = message.chat.id
    acl = requests.get(f'{baseURL}/gates/{CHAT_ID}') # cancelli a cui è registrato l'utente
    code = acl.status_code
    if code == 200:
        #PATCH: username utente
        return False
    return True

# ritorna un dizionario con le entità chiave (bold, italic...) e il loro testo come valore in un messaggio
def parse_entities(message):
    entities = message.json['entities'] 
    text = message.text
    parsed_values = {}
    for entity in entities:
        parsed_values[f"{entity['type']}"] = text[entity['offset'] : (entity['offset'] + entity['length'])]
    return parsed_values

# mostra i tasti di InlineKeyboard 'Si' e 'No' in coda ad un messaggio di scelta
def gen_markup(option):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2 
    markup.add(InlineKeyboardButton('Si', callback_data = f'{option}_yes'), InlineKeyboardButton('No', callback_data = f'{option}_no'))
    return markup

# mostra la ReplyKeyboard per far scegliere il cancello all'utente
def choose_gate_markup(gates):
    markup = ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard = True)
    for gate in gates:
        markup.add(KeyboardButton(gate['gate_name']))
    return markup


# risponde e gestisce le scelte 'Si' e 'No' dell'utente
@bot.callback_query_handler(func = lambda call: True)
def callback_query(call):
    CALL_ID = call.id
    CHAT_ID = call.message.chat.id
    bot.edit_message_reply_markup(chat_id = CHAT_ID, message_id = call.message.id, reply_markup = None) # rimuove i tasti di InlineKeyboard
    
    acl = requests.get(f'{baseURL}/gates/{CHAT_ID}') # cancelli a cui è registrato l'utente
    code = acl.status_code
    if code != 200: # errore generico o utente non ha cancelli
        return bot.answer_callback_query(CALL_ID, 'ERRORE. Riprovare')
    user_gates = acl.json()

    bot.send_message(CHAT_ID, 'Richiesta accolta.')
    entities = parse_entities(call.message)
    gate_name = entities['bold']
    gateID = user_gates[[i for i in range(len(user_gates)) if user_gates[i]['gate_name'] == gate_name][0]]['gate_id'] # ottengo il gateID dal gate_name
    
    # apri cancello
    if call.data == 'open_yes':
        #GET: apri cancello (non implementata)
        return bot.answer_callback_query(CALL_ID, 'Apro il cancello')
    elif call.data == 'open_no':
        return bot.answer_callback_query(CALL_ID, 'Il cancello rimane chiuso')
    # aggiungi targa
    elif call.data == 'plate_add_yes':
        bot.answer_callback_query(CALL_ID, 'Targa aggiunta correttamente')
        plate = entities['italic']
        sent = bot.send_message(call.message.chat.id, 'Per identificare questa targa inviami il nome del propietario secondo il seguente formato: *Nome Propietario* (a-z A-Z).', parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, get_plate_owner, gateID, plate)
    elif call.data == 'plate_add_no':
        return bot.answer_callback_query(CALL_ID, 'Targa non aggiunta')
    # rimuovi targa
    elif call.data == 'plate_remove_yes':
        plate = entities['italic']
        delete_plate = requests.delete(f'{baseURL}/accesses/{gateID}/{plate}') # rimuovere la registrazione di una targa da un cancello
        code = delete_plate.status_code
        if code == 200:
            return bot.answer_callback_query(CALL_ID, 'Targa rimossa correttamente')
        else:
            return bot.answer_callback_query(CALL_ID, 'Errore cercando di rimuovere la targa')
    elif call.data == 'plate_remove_no':
        return bot.answer_callback_query(CALL_ID, 'Targa non rimossa')
    # rimuovi utente
    elif call.data == 'username_remove_yes':
        user_CHAT_ID = entities['italic']
        delete_user = requests.delete(f'{baseURL}/users/{gateID}/{user_CHAT_ID}') # rimuovere la registrazione di un utente da un cancello
        code = delete_user.status_code
        if code == 200:
            return bot.answer_callback_query(CALL_ID, 'Utente rimosso correttamente')
        else:   
            return bot.answer_callback_query(CALL_ID, "Errore cercando di rimuovere l'utente")
    elif call.data == 'username_remove_no':
        return bot.answer_callback_query(CALL_ID, 'Utente non rimosso')


# controlla che un utente sia autorizzato ad utilizzare il bot    
@bot.message_handler(func = registered_users_only)
def handle_unwanted_users(message):
    CHAT_ID = message.chat.id
    bot.delete_message(CHAT_ID, message.message_id)
    sent = bot.send_message(CHAT_ID, 'Non sei autorizzato ad utilizzare questo bot.\nPer utilizzare questo bot inviami il *gateID* del tuo cancello secondo il seguente formato: *#token* (32 caratteri).', parse_mode = 'Markdown')
    return bot.register_next_step_handler(sent, get_gateID)

# invia messaggio di info del bot
@bot.message_handler(commands = ['start', 'help'])
def greet(message):
    CHAT_ID = message.chat.id
    bot.send_message(CHAT_ID, 
    '''
    Ti aiuto a controllare e monitorare quello che succede davanti al tuo cancello.
    
Puoi controllarmi inviando questi comandi:
    
/help - lista dei miei comandi
/nuovo_cancello - registrati per il tuo cancello
/nome_cancello - nomina il tuo cancello
/foto - ottieni un'istantanea dal cancello
/aggiungi_targa - aggiungi una targa a quelle note
/rimuovi_targa - rimuovi una targa da quelle note
/targhe - stampa la lista delle targhe note
/rimuovi_utente - rimuovi un utente da quelli privilegiati
/utenti - stampa la lista degli utenti privilegiati
/esci - interrompi istruzione, se attiva
    ''')

# registra l'utente ad un cancello
@bot.message_handler(commands = ['nuovo_cancello'])
def get_gateID(message):
    CHAT_ID = message.chat.id
    username = message.from_user.username
    txt = message.text
    
    if txt.startswith('/esci'): return

    match = re.findall(' +#[a-z0-9-]{36} *', ' ' + txt) # match per il gateID ('psw') del cancello
    if match:
        gateID = match[0].replace('#', '').replace(' ', '')
        gate_name = 'tmp_gate_name' # nome temporaneo del cancello dato dal bot
        
        register_gate = requests.post(f'{baseURL}/users/{gateID}/{CHAT_ID}', json = {'username': username, 'gate_name': gate_name}) # aggiungi la registrazione dell'utente al cancello
        code = register_gate.status_code
        if code == 201:
            bot.send_message(CHAT_ID, '*gateID CORRETTO*\nPuoi ora utilizzare questo bot per controllare il tuo cancello.', parse_mode = 'Markdown')
            sent = bot.send_message(CHAT_ID, 'Per identificare questo cancello inviami un nome a scelta secondo il seguente formato: *NomeCancello* (min 5 caratteri: a-z A-Z 0-9).\nPuoi cambiarlo in un secondo momento.', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gate_name, gateID)
        elif code == 400:
            sent = bot.send_message(CHAT_ID, '*ERRORE*\nRinviami il *gateID* del tuo cancello secondo il seguente formato: *#token* (32 caratteri).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gateID)
        elif code == 404:
            sent = bot.send_message(CHAT_ID, '*gateID NON VALIDO o ERRATO*\nPer utilizzare questo bot inserisci il *gateID* del tuo cancello secondo il seguente formato: *#token* (32 caratteri).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gateID)
        elif code == 409:
            sent = bot.send_message(CHAT_ID, '*gateID GIÀ REGISTRATO*\nPer utilizzare questo bot inserisci il *gateID* di un tuo altro cancello secondo il seguente formato: *#token* (32 caratteri).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gateID)
        # elif code == 412: ...
    else:
        if txt.startswith('/nuovo_cancello'):
            sent = bot.send_message(CHAT_ID, 'Inviami il *gateID* del tuo cancello secondo il seguente formato: *#token* (32 caratteri).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gateID)
        else:
            sent = bot.send_message(CHAT_ID, '*gateID NON VALIDO o ERRATO*\nPer utilizzare questo bot inserisci il *gateID* del tuo cancello secondo il seguente formato: *#token* (32 caratteri).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gateID)

# scelta del cancello da parte dell'utente su cui applicare i comandi richiesti
@bot.message_handler(commands = ['nome_cancello', 'foto', 'apri', 'utenti', 'targhe', 'aggiungi_targa', 'rimuovi_targa', 'rimuovi_utente'])
def handle_request(message):
    CHAT_ID = message.chat.id
    command = message.text.strip('/')
    
    acl = requests.get(f'{baseURL}/gates/{CHAT_ID}') # cancelli a cui è registrato l'utente
    code = acl.status_code
    if code != 200:  # errore generico o utente non ha cancelli
        return bot.send_message(CHAT_ID, '*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
    user_gates = acl.json()

    # se l'utente ha solo un cancello
    if len(user_gates) == 1:
        message.text = user_gates[0]['gate_name']
        return handle_answer(message, user_gates, command)
    else: # se l'utente ha più cancelli sceglie quale
        sent = bot.send_message(CHAT_ID, 'Scegli un cancello', reply_markup = choose_gate_markup(user_gates))
        return bot.register_next_step_handler(sent, handle_answer, user_gates, command)

# reindirizza alla funzione giusta in base al comando richiesto dall'utente
def handle_answer(message, user_gates, command):
    CHAT_ID = message.chat.id
    gate_name = message.text
    
    if gate_name not in [user_gates[i]['gate_name'] for i in range(len(user_gates))]: # controllo che il nome del cancello inviato dall'utente sia un suo cancello
        return bot.send_message(CHAT_ID, 'Cancello selezionato non valido.')
    
    gateID = user_gates[[i for i in range(len(user_gates)) if user_gates[i]['gate_name'] == gate_name][0]]['gate_id'] # ottengo il gateID dal gate_name

    if command == 'nome_cancello':
        sent = bot.send_message(CHAT_ID, f'Rinomina il tuo cancello *{gate_name}* con un altro nome secondo il seguente formato: *NomeCancello* (min 5 caratteri: a-z A-Z 0-9).', parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, get_gate_name, gateID)
    elif command == 'foto':
        return get_photo(message, gateID)
    elif command == 'apri':
        return open_gate(message) 
    elif command == 'utenti':
        return list_users(message, gateID)
    elif command == 'targhe':
        return list_plates(message, gateID) 
    elif command == 'aggiungi_targa': 
        sent = bot.send_message(CHAT_ID, f'Inviami il numero di targa da aggiungere al cancello *{gate_name}* secondo il seguente formato: *AZ 000 AZ* (2 caratteri A-Z, 3 numeri 0-9, 2 caratteri A-Z).', parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, manage_plate, gateID, gate_name, 'add')
    elif command == 'rimuovi_targa':
        gate_plates = requests.get(f'{baseURL}/accesses/{gateID}') # lista delle targhe registrate al cancello
        code = gate_plates.status_code 
        if code == 400:
            return bot.send_message(CHAT_ID, '*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
        elif code == 404:
            return bot.send_message(CHAT_ID, f'Nessuna targa può accedere al cancello *{gate_name}*.', parse_mode = 'Markdown')

        sent = bot.send_message(CHAT_ID, f'Inviami il numero di targa da rimuovere dal cancello *{gate_name}* secondo il seguente formato: *AZ 000 AZ* (2 caratteri A-Z, 3 numeri 0-9, 2 caratteri A-Z).', parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, manage_plate, gateID, gate_name, 'remove')
    elif command == 'rimuovi_utente':
        sent = bot.send_message(CHAT_ID, f"Inviami lo username dell'utente da rimuovere dal cancello *{gate_name}* secondo il seguente formato: @*username* (min 5 caratteri: a-z A-Z 0-9).", parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, remove_user, gateID, gate_name)

# rinomina il cancello dell'utente
def get_gate_name(message, gateID): 
    CHAT_ID = message.chat.id
    txt = message.text

    match = re.findall(' +[A-Za-z0-9]{5,} *', ' ' + txt) # match per il nome del cancello
    if match:
        new_gate_name = match[0].replace(' ', '') 

        patch_name = requests.patch(f'{baseURL}/users/{gateID}/{CHAT_ID}', json = {'gate_name': new_gate_name}) # aggiorna il nome del cancello per l'utente
        code = patch_name.status_code
        if code == 200:
            return bot.send_message(CHAT_ID, f'Nome *{new_gate_name}* assegnato correttamente.', parse_mode = 'Markdown')
        elif code == 400:
            sent = bot.send_message(CHAT_ID, '*ERRORE*\nRinviami un nome a scelta da dare al tuo cancello secondo il seguente formato: *NomeCancello* (min 5 caratteri: a-z A-Z 0-9).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gate_name, gateID)
        elif code == 404:
            sent = bot.send_message(CHAT_ID, '*ERRORE* non sei autorizzato.', parse_mode = 'Markdown')
            return
        elif code == 412:
            sent = bot.send_message(CHAT_ID, '*nome NON VALIDO*, esiste già un cancello con questo nome.\nInviami un nome a scelta da dare al tuo cancello secondo il seguente formato: *NomeCancello* (min 5 caratteri: a-z A-Z 0-9).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, get_gate_name, gateID)
    else:
        sent = bot.send_message(CHAT_ID, '*nome NON VALIDO*\nInviami un nome a scelta da dare al tuo cancello secondo il seguente formato: *NomeCancello* (min 5 caratteri: a-z A-Z 0-9).', parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, get_gate_name, gateID)

# manda una foto di uno degli ultimi movimenti avvertiti davanti al cancello
def get_photo(message, gateID):
    CHAT_ID = message.chat.id
    gate_name = message.text
    
    gate_photo = requests.get(f'{baseURL}/events/logs/{gateID}')
    code = gate_photo.status_code

    if code == 200:
        print(gate_photo.json())
        return bot.send_message(CHAT_ID, f'Ecco cosa succede di fronte al cancello *{gate_name}*.', parse_mode = 'Markdown') 
    elif code == 404:
        return bot.send_message(CHAT_ID, 'Nessuna immagine disponibile al momento.', parse_mode = 'Markdown')    
    else:
        return bot.send_message(CHAT_ID, '*ERRORE*\nRiprovare.', parse_mode = 'Markdown')

# apre il cancello (da implementare)
def open_gate(message):
    CHAT_ID = message.chat.id
    gate_name = message.text
    return bot.send_message(CHAT_ID, f'Vuoi davvero aprire il cancello *{gate_name}*?', parse_mode = 'Markdown', reply_markup = gen_markup('open'))

# mostra la lista degli utenti registrati al cancello
def list_users(message, gateID):
    CHAT_ID = message.chat.id
    gate_name = message.text
    
    gate_acl = requests.get(f'{baseURL}/users/{gateID}') # lista degli utenti regitrati al cancello
    code = gate_acl.status_code
    if code != 200:
        return bot.send_message(CHAT_ID, '*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
    group = gate_acl.json()

    names = [group[i]['username'] for i in range(len(group)) if group[i]['gate_id'] == gateID] # lista degli username degli utenti 
    names_str = ''
    for name in names:
        names_str += '@' + name.replace('_', '\\_') + '\n'
    return bot.send_message(CHAT_ID, f'Ecco la lista degli utenti che hanno accesso al cancello *{gate_name}*:\n{names_str}', parse_mode = 'Markdown')

# mostra la lista delle targhe e propietari registrate al cancello
def list_plates(message, gateID): 
    CHAT_ID = message.chat.id
    gate_name = message.text

    gate_plates = requests.get(f'{baseURL}/accesses/{gateID}') # lista delle targhe registrate al cancello
    code = gate_plates.status_code 
    if code == 400:
        return bot.send_message(CHAT_ID, '*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
    elif code == 404:
        return bot.send_message(CHAT_ID, f'Nessuna targa può accedere al cancello *{gate_name}*.', parse_mode = 'Markdown')

    group = gate_plates.json()
    plates = [(group[i]['plate'], group[i]['owner']) for i in range(len(group)) if group[i]['gate_id'] == gateID] # lista delle targhe, nome propietario
    plates_str = ''
    for plate in plates:
        plates_str += plate[0].upper() + '  ' + plate[1] + '\n'
    return bot.send_message(CHAT_ID, f'Ecco la lista delle targhe salvate che possono accedere al cancello *{gate_name}*:\n{plates_str}', parse_mode = 'Markdown')

# aggiunge/rimuove una targa a/da un cancello
def manage_plate(message, gateID, gate_name, option):
    CHAT_ID = message.chat.id
    txt = message.text
    
    if txt.startswith('/esci'): return

    match = re.findall(' +[A-Za-z]{2} ?[0-9]{3} ?[A-Za-z]{2} *', ' ' + txt) # match per il numero di targa
    if match:
        plate = match[0].replace(' ', '').upper()

        valid_plate = requests.get(f'{baseURL}/accesses/{gateID}/{plate}') # informazioni di una targa per un cancello
        code = valid_plate.status_code
        if code == 200: # se è già registrata
            if option == 'add':
                sent = bot.send_message(CHAT_ID, f'*Targa GIÀ REGISTRATA*\nInviami un altro numero di targa da aggiungere al cancello *{gate_name}* secondo il seguente formato: *AZ 000 AZ* (2 caratteri A-Z, 3 numeri 0-9, 2 caratteri A-Z).', parse_mode = 'Markdown')
                return bot.register_next_step_handler(sent, manage_plate, gateID, gate_name, 'add')
            if option == 'remove':
                return bot.send_message(CHAT_ID, f'Vuoi davvero rimuovere dal cancello *{gate_name}* questa targa: _{plate}_?', parse_mode = 'Markdown', reply_markup = gen_markup('plate_remove'))
        elif code == 400:
                return bot.send_message(CHAT_ID, f'*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
        elif code == 404: # se non è registrata
            if option == 'add':
                return bot.send_message(CHAT_ID, f'Vuoi davvero aggiungere al cancello *{gate_name}* questa targa: _{plate}_?', parse_mode = 'Markdown', reply_markup = gen_markup('plate_add'))
            if option == 'remove':
                sent = bot.send_message(CHAT_ID, f'*Targa NON REGISTRATA*\nInviami un altro numero di targa da rimuovere dal cancello *{gate_name}* secondo il seguente formato: *AZ 000 AZ* (2 caratteri A-Z, 3 numeri 0-9, 2 caratteri A-Z).', parse_mode = 'Markdown')
                return bot.register_next_step_handler(sent, manage_plate, gateID, gate_name, 'remove')
    else:
        if option == 'add':
            sent = bot.send_message(CHAT_ID, f'*Targa NON VALIDA*\nInviami il numero di targa da aggiungere al cancello *{gate_name}* secondo il seguente formato: *AZ 000 AZ* (2 caratteri A-Z, 3 numeri 0-9, 2 caratteri A-Z).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, manage_plate, gateID, gate_name, 'add')
        elif option == 'remove':
            sent = bot.send_message(CHAT_ID, f'*Targa NON VALIDA*\nInviami il numero di targa da rimuovere dal cancello *{gate_name}* secondo il seguente formato: *AZ 000 AZ* (2 caratteri A-Z, 3 numeri 0-9, 2 caratteri A-Z).', parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, manage_plate, gateID, gate_name, 'remove')

# assegna il nome del propietario alla targa 
def get_plate_owner(message, gateID, plate):
    CHAT_ID = message.chat.id
    txt = message.text
    
    match = re.findall('[A-Za-z]+ *[A-Za-z]+', txt) # match per il nome del propietario
    if match:
        owner = match[0]
        
        new_plate = requests.post(f'{baseURL}/accesses/{gateID}/{plate}', json = {'owner': owner}) # aggiungi la targa e il suo propietario al cancello
        code = new_plate.status_code
        if code == 201:
            return bot.send_message(CHAT_ID, f'Ho assegnato alla targa *{plate}* il propietario *{owner}*.', parse_mode = 'Markdown')
        else:
            print(f'code: {code}')
            return bot.send_message(CHAT_ID, f'*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
    else:
        sent = bot.send_message(CHAT_ID, '*nome proprietario NON VALIDO*\nPer identificare la targa inviami il nome del propietario secondo il seguente formato: *Nome Propietario* (a-z A-Z).', parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, get_plate_owner, gateID, plate)

# rimuove un utente dal cancello
def remove_user(message, gateID, gate_name):
    CHAT_ID = message.chat.id
    txt = message.text

    if txt.startswith('/esci'): return
    
    match = re.findall(' +@[A-Za-z0-9_]{5,} *', ' ' + txt) # match per il telegram username
    if match:
        username = match[0].replace('@','').replace(' ', '').lower()
        
        gate_acl = requests.get(f'{baseURL}/users/{gateID}') # lista degli utenti regitrati al cancello
        code = gate_acl.status_code
        if code != 200:
            return bot.send_message(CHAT_ID, '*ERRORE*\nRiprovare.', parse_mode = 'Markdown')
        group = gate_acl.json()

        user = [group[i]['chat_id'] for i in range(len(group)) if group[i]['username'].lower() == username] # CHAT_ID del utente che si vuole rimuovere (se presente) [FORSE NON NECESSARIO: SE SI METTE PATCH USERNAME ALL'INIZIO DEL PROGRAMMA FACCIO UNA DELETE CON LO USERNAME E NON IL CHATID]
        if user:
            user_CHAT_ID = user[0]
            return bot.send_message(CHAT_ID, f'Vuoi davvero rimuovere @{username}:_{user_CHAT_ID}_ dagli utenti che possono accedere al cancello *{gate_name}*?', parse_mode = 'Markdown', reply_markup = gen_markup('username_remove'))
        else:
            sent = bot.send_message(CHAT_ID, f"*username NON VALIDO*\nInviami lo username dell'utente registrato al cancello *{gate_name}* secondo il seguente formato: @*username* (min 5 caratteri: a-z A-Z 0-9)", parse_mode = 'Markdown')
            return bot.register_next_step_handler(sent, remove_user, gateID, gate_name)
    else:
        sent = bot.send_message(CHAT_ID, f"*username ERRATO*\nInviami lo username dell'utente registrato al cancello *{gate_name}* secondo il seguente formato: @*username* (min 5 caratteri: a-z A-Z 0-9)", parse_mode = 'Markdown')
        return bot.register_next_step_handler(sent, remove_user, gateID, gate_name)

# risponde a tutti i messaggi/comandi non gestiti
@bot.message_handler(func = lambda message: True)
def reply_message(message):
    CHAT_ID = message.chat.id
    print(f'Messaggio non gestito\n')
    return bot.send_message(CHAT_ID, 'Non posso rispondere ad altre richieste o messaggi oltre i quali sono stato istruito.')

bot.infinity_polling()
