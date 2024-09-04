import os
from os.path import exists
from datetime import datetime
import ctypes
from PhoneNumber import PhoneNumber, AppUsageEnum
from detectTelegram import DetectTelegram
import logging
from detectWhatsapp import DetectWhatsapp
logger = logging.getLogger()

# Fonction principal pour detecter les reseaux sociaux lies a chaque numero
def create_social_network_files(listFromFile):
    phone_number_list = list_to_phone_number(listFromFile)
    detector = SocialDetector()
    ids = loadConfiguration()
    # Ajout des reseaux sociaux a detecter
    detector.add_social_app(DetectTelegram(phone_number_list, ids[0], ids[1]))
    detector.add_social_app(DetectWhatsapp(phone_number_list, ids[3], ids[4]))
    detector.detect()
    socialNetworkCounts = [0, 0]
    whatsappList = []
    telegramList = []
    # Stock de chaque numero par reseau social
    for number in phone_number_list:
        if number.has_app("Whatsapp") == AppUsageEnum.USAGE:
            socialNetworkCounts[0] += 1
            whatsappList.append(number.phone_number)
        if number.has_app("Telegram") == AppUsageEnum.USAGE:
            socialNetworkCounts[1] += 1
            telegramList.append(number.phone_number)
    # si utilisateurs trouves, creation de fichiers csv par reseau social
    if socialNetworkCounts[0] > 0:
        exportDetectionToCSV("Whatsapp", whatsappList)
    if socialNetworkCounts[1] > 0:
        exportDetectionToCSV("Telegram", telegramList)
    # retour des stats pour alimenter le camembert
    return socialNetworkCounts

# Transformation de chaque numero en objet PhoneNumber
def list_to_phone_number(listFromFile):
    phone_number_list = []
    for line in listFromFile:
        phone_number_list.append(PhoneNumber(line))
    return phone_number_list


def loadConfiguration():
    # chemin vers le repertoire de stockage du fichier de configuration
    path = f'{os.getcwd()}\Configuration\socialnetworkID.txt'
    logger.info(path)
    if exists(path):
        try:
            # ouverture et lecture du fichier
            f = open(path, "r")
            values = list(f.read().split("\n"))
            return values
        except Exception as error:
            logger.error("Erreur lors de la lecture de la configuration " + str(error))
    else:
        logger.error("Aucun fichier de configuration")
        ctypes.windll.user32.MessageBoxW(0, "Aucune configuration n'est disponible", "Erreur")


class SocialDetector:
    apps_to_detect = []

    # This method takes an implementation of BaseSocialApp and add it to the list to be detected later
    def add_social_app(self, app):
        self.apps_to_detect.append(app)

    def detect(self):
        for app in self.apps_to_detect:
            app.process()


def exportDetectionToCSV(socialNetworkName, listPhoneNumbers):
    try:
        path = f'{os.getcwd()}\\Export\\Detections\\'
        # nommage du fichier de rapport avec le gdh de generation de l'export.
        fileName = ("%s_%s_%s.csv" % (socialNetworkName, datetime.now().date(), datetime.now().strftime("%H-%M-%S")))
        # creation du repertoire Export s'il n'existe pas
        if not exists(path):
            ctypes.windll.user32.MessageBoxW(0, "Le dossier Detections est absent dans le dossier ODIM.", "Erreur")
            return
        else:
            # sauvegarde de fichier avec les configurations
            with open(path + fileName, 'w') as file:
                for pn in listPhoneNumbers:
                    file.write(pn + "\n")
            ctypes.windll.user32.MessageBoxW(0, f"Le fichier csv {socialNetworkName} produit.", "Confirmation")
            logger.info(f"Export du fichier csv {socialNetworkName} " + str(file.name))
            file.close()
    except UnboundLocalError as error:
        logger.error(error)
    except NameError as error:
        logger.error(error)
