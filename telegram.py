import ctypes
import os
import logging
import random
import sys
import time
from _winapi import CREATE_NO_WINDOW
from os.path import exists

import keyboard as keyboard
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.alert import Alert
from urllib3.exceptions import ProtocolError
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
logger = logging.getLogger()


# Classe regroupant les composants HTML du DOM de la page Telegram
class TelegramElements:
    # chemin vers le répertoire de stockage du fichier de configuration
    # Gestion d'une exécution sous cmd via la programmation
    if len(sys.argv) > 1:
        exeFilePath = sys.executable.split("\\ODIM.exe")[0]
        path = f'{exeFilePath}\\Configuration\\telegramelements.txt'
    else:
        path = f'{os.getcwd()}\\Configuration\\telegramelements.txt'
    if exists(path):
        try:
            # ouverture et lecture du fichier
            f = open(path, "r")
            values = list(f.read().split("\n"))
            # attribution des références
            # bouton pour ouvrir une conversation web
            openInWeb = (By.CSS_SELECTOR, values[0])
            # champs de recherche d'un contact
            search = (By.CSS_SELECTOR, values[1])
            # les chats existants
            contactsList = (By.CSS_SELECTOR, values[2])
            # champs de saisi message
            inputMessageContainer = (By.CSS_SELECTOR, values[3])
            # info du message (en cours, distribué, lu)
            sendingCheck = (By.CSS_SELECTOR, values[4])
            sentCheck = (By.CSS_SELECTOR, values[5])
            readCheck = (By.CSS_SELECTOR, values[6])
            # bouton de menu pour joindre un élément dans le message
            attachButton = (By.CSS_SELECTOR, values[7])
            # bouton pour joindre un média
            attachMedia = (By.CSS_SELECTOR, values[8])
            # bouton pour joindre un document
            attachDocument = (By.CSS_SELECTOR, values[9])
            # composant pour envoyer l'élément joint
            sendAttach = (By.CSS_SELECTOR, values[10])

        except Exception as error:
            logger.error("Erreur lors de la lecture de telegramelements " + str(error))
    else:
        logger.info("Aucun fichier de telegramelements")

class Telegram:
    """
    This class is used to interact with your Telegram [UNOFFICIAL API]
    """
    browser = None
    timeout = 300  # The timeout is set for about ten seconds

    def __init__(self, wait, screenshot=None, session=None):
        chrome_path = ChromeDriverManager().install()
        chrome_service = Service(chrome_path)
        chrome_service.creationflags = CREATE_NO_WINDOW
        if session:
            chrome_options = Options()
            chrome_options.add_argument("--user-data-dir={}".format(session))
            self.browser = webdriver.Chrome(options=chrome_options,
                                            service=chrome_service)
        else:
            self.browser = webdriver.Chrome(service=chrome_service)
        """
        Il y a deux URL pour telegram :

        "https://web.telegram.org/z/" : Développée en React, tous les composants web ne sont pas disponibles à l'interaction via selenium.
        "https://web.telegram.org/k/" : Développée en Native js, action possible sur tous les composants.
        """
        # Requête vers l'URL de Telegram
        if self.browser is not None:
            self.browser.get("https://web.telegram.org/k/")
            # Attente de la localisation du champ de recherche d'un contact pour s'assurer que la fenêtre soit chargée complètement.
            try:
                logger.info("Attente de la localisation du champs de recherche du destinataire")
                WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(TelegramElements.search))
            except ProtocolError as pe:
                logger.error(pe)
                ctypes.windll.user32.MessageBoxW(0,
                                                 "La connexion a été interrompu par une action utilisateur",
                                                 "Erreur")
            except TimeoutException as pe:
                logger.error(pe)
                ctypes.windll.user32.MessageBoxW(0,
                                                 "Le délai pour la connexion à Telegram est dépassé",
                                                 "Erreur")
        else:
            logger.info("Impossible d'ouvrir le navigateur chrome")
            ctypes.windll.user32.MessageBoxW(0,
                                             "L'application ne parvient pas à ouvrir une nouvelle fenêtre Chrome\n"
                                             "Une fenêtre Chrome ouverte par ODIM est peut être encore active, "
                                             "Si aucune fenêtre Chrome n'est active, il est possible que la session renseignée soit verrouillée suite à une précédente utilisation mal terminée",
                                             "Erreur")

    # Méthode pour l'envoi de message texte au destinataire renseigné.
    def send_message(self, name, message, skipContact, randomStructure):
        identifer = str(name).replace("+", "").replace("@","")
        if identifer.isnumeric():
            self.browser.get("https://t.me/+"+str(identifer))
        else:
            self.browser.get("https://t.me/" + str(identifer))
        try:
            openInWeb = WebDriverWait(self.browser, self.timeout).until(EC.element_to_be_clickable(TelegramElements.openInWeb))
            openInWeb.click()
            # Contrôle si l'utilisateur souhaite envoyer des messages textes avec une structure aléatoire.
            # La structure aléatoire consiste à découper un message en plusieurs sous messages en se basant sur la présence de caractère espace " " dans le message.
            # Ces caractères sont remplacés ou non de manière aléatoire par un boolean par un caractère de retour à la ligne "\n"
            if randomStructure:
                # split sur les espaces " "
                messageToArray = message.split(" ")
                message = ""
                # découpage du message en insérant des caractères "\n"
                for texte in messageToArray:
                    if bool(random.getrandbits(1)):
                        texte = texte + "\n"
                    message = message + " " + texte
            # sélection du champ de saisi dès qu'il est cliquable
            send_msg = WebDriverWait(self.browser, self.timeout).until(EC.element_to_be_clickable(TelegramElements.inputMessageContainer))
            # cast en string pas défaut pour éviter les erreurs sur messages de type autre que string
            messages = str(message).split("\n")
            # Envoi du message
            for msg in messages:
                send_msg.send_keys(msg)
                send_msg.send_keys(Keys.ENTER)
                time.sleep(1)
            # attente de la confirmation de l'envoi
            try:
                time.sleep(2)
                WebDriverWait(self.browser, 300).until_not(EC.element_to_be_clickable(TelegramElements.sendingCheck))
            except TimeoutException:
                try:
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(TelegramElements.sentCheck))
                except TimeoutException:
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(TelegramElements.readCheck))
            return name, message, "Envoyé", ""
        except TimeoutException:
            logger.error("Message (TimeoutException) : La requête a expiré auprès de Telegram !")
            return name, message, "Échec", "Pas de réponse de Telegram"
        except NoSuchElementException:
            logger.error("Message (NoSuchElementException) : Composant inexistant")
            return name, message, "Échec", "Le composant n'est pas localisé dans la page"
        except Exception as e:
            logger.error("Message (Exception) : Erreur non identifiée : " + str(e))
            return name, message, "Échec", "Erreur non gérée"

    # Méthode pour l'envoi de média
    def send_picture(self, name, file, skipContact, caption=None):
        identifer = str(name).replace("+", "").replace("@", "")
        if identifer.isnumeric():
            self.browser.get("https://t.me/+" + str(identifer))
        else:
            self.browser.get("https://t.me/" + str(identifer))
        try:
            openInWeb = WebDriverWait(self.browser, self.timeout).until(EC.element_to_be_clickable(TelegramElements.openInWeb))
            openInWeb.click()
            attachButton = WebDriverWait(self.browser, self.timeout).until(EC.element_to_be_clickable(TelegramElements.attachButton))
            attachButton.click()
            attachMedia = WebDriverWait(self.browser, self.timeout).until(EC.element_to_be_clickable(TelegramElements.attachMedia))
            attachMedia.click()
            time.sleep(2)
            # saisie dans l'explorateur de fichiers Windows
            keyboard.write(file)
            keyboard.press('enter')
            send_btn = WebDriverWait(self.browser, self.timeout).until(EC.element_to_be_clickable(TelegramElements.sendAttach))
            send_btn.click()
            # attente de la confirmation de l'envoi
            try:
                time.sleep(2)
                WebDriverWait(self.browser, 300).until_not(EC.element_to_be_clickable(TelegramElements.sendingCheck))
            except TimeoutException:
                try:
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(TelegramElements.sentCheck))
                except TimeoutException:
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(TelegramElements.readCheck))
            return name, file, "Envoyé", ""
        except TimeoutException:
            logger.error("Média (TimeoutException) : La requête a expiré auprès de Telegram !")
            return name, file, "Échec", "Pas de réponse de Telegram"
        except NoSuchElementException:
            logger.error("Média (NoSuchElementException) : Composant inexistant")
            return name, file, "Échec", "Le composant n'est pas localisé dans la page"
        except Exception as e:
            logger.error("Média (Exception) : Erreur non identifiée : " + str(e))
            return name, file, "Échec", "Erreur non gérée"

    def send_document(self, name, document_location, skipContact):
        identifer = str(name).replace("+", "").replace("@", "")
        if identifer.isnumeric():
            self.browser.get("https://t.me/+" + str(identifer))
        else:
            self.browser.get("https://t.me/" + str(identifer))
        try:
            openInWeb = WebDriverWait(self.browser, self.timeout).until(
                EC.element_to_be_clickable(TelegramElements.openInWeb))
            openInWeb.click()
            attachButton = WebDriverWait(self.browser, self.timeout).until(
                EC.element_to_be_clickable(TelegramElements.attachButton))
            attachButton.click()
            attachDocument = WebDriverWait(self.browser, self.timeout).until(
                EC.element_to_be_clickable(TelegramElements.attachDocument))
            attachDocument.click()
            time.sleep(2)
            # saisie dans l'explorateur de fichiers Windows
            keyboard.write(document_location)
            keyboard.press('enter')
            send_btn = WebDriverWait(self.browser, self.timeout).until(
                EC.element_to_be_clickable(TelegramElements.sendAttach))
            send_btn.click()
            # attente de la confirmation de l'envoi
            try:
                time.sleep(2)
                WebDriverWait(self.browser, 300).until_not(
                    EC.element_to_be_clickable(TelegramElements.sendingCheck))
            except TimeoutException:
                try:
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable(TelegramElements.sentCheck))
                except TimeoutException:
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable(TelegramElements.readCheck))
            return name, document_location, "Envoyé", ""
        except TimeoutException:
            logger.error("Document (TimeoutException) : La requête a expiré auprès de Telegram !")
            return name, document_location, "Échec", "Pas de réponse de Telegram"
        except NoSuchElementException:
            logger.error("Document (NoSuchElementException) : Composant inexistant")
            return name, document_location, "Échec", "Le composant n'est pas localisé dans la page"
        except Exception as e:
            logger.error("Document (Exception) : Erreur non identifiée : " + str(e))
            return name, document_location, "Échec", "Erreur non gérée"

    def extract_contacts(self) -> iter:
        WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(TelegramElements.contactsList))
        discussions = self.browser.find_elements(By.CSS_SELECTOR, ".peer-title")
        lst = []
        for d in discussions:
            lst.append(d.text)
        return lst

    # override the timeout
    def override_timeout(self, new_timeout):
        self.timeout = new_timeout

    # This method is used to quit the browser
    def quit(self):
        self.browser.quit()

    # Retour à la page d'accueil de Telegram ou de la session en cours
    def goto_main(self):
        try:
            self.browser.refresh()
            Alert(self.browser).accept()
        except Exception as e:
            logger.error(e)
        WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(TelegramElements.search))


