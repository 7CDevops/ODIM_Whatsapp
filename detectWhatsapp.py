import logging
from BaseSocialApp import BaseSocialApp
import requests
import json
from PhoneNumber import AppUsageEnum

logger = logging.getLogger()

class DetectWhatsapp(BaseSocialApp):
    # identifiant et hash de Green API non-officielle pour WhatsApp
    def __init__(self, phone_numbers_to_detect, api_id, api_hash):
        self.api_ID = api_id
        self.api_hash = api_hash
        self.url = ""
        super().__init__(phone_numbers_to_detect)

    def authenticate(self):
        self.url = "https://api.green-api.com/waInstance" + self.api_ID + "/checkWhatsapp/" + self.api_hash

    def detect_single_number(self, phone_number):
        payload = json.dumps({"phoneNumber": phone_number.phone_number})
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", self.url, headers=headers, data=payload)
        # si besoin
        #print(str(response.text.encode('utf8'))
        if "true" in str(response.text.encode('utf8')):
            phone_number.set_app_state(self.get_name(), AppUsageEnum.USAGE)
        else:
            phone_number.set_app_state(self.get_name(), AppUsageEnum.NO_USAGE)
            logger.info(f"WhatsApp : {self.get_name()} n'utilise pas")

    def detect_numbers(self, phone_numbers):
        self.authenticate()
        for phone in phone_numbers:
            self.detect_single_number(phone)

    def process(self):
        self.detect_numbers(self.phone_numbers_to_detect)

    def get_name(self):
        return "Whatsapp"
