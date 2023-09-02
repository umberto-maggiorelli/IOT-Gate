import requests
import os

# invia foto con caption
# invia testo
class TelegramBotManager():
    def __init__(self):
        self.TELEGRAM_API_KEY = 'xxx'
    def send_photo(self, chat_id, photo, event_informations):
        response = requests.post( 
                url = f'https://api.telegram.org/bot{self.TELEGRAM_API_KEY}/sendPhoto', 
                data = {'chat_id': chat_id, 'caption': f"Tentativo di Accesso Rilevato:\n{event_informations}"},
                files = {'photo': photo} 
            )
    
    def send_message(self, chat_id, text):
        response = requests.get( 
                url = f'https://api.telegram.org/bot{self.TELEGRAM_API_KEY}/sendMessage', 
                params = {'chat_id': chat_id, 'text': text}
            )
