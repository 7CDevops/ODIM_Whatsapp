import ctypes
import json
import logging
import os
import random
import shutil
import sys
import time
from os.path import exists
from subprocess import CREATE_NO_WINDOW
from zipfile import ZipFile, BadZipFile

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException, StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import ProtocolError

logger = logging.getLogger()


# Class contenant tous les composants de la page web de whatsapp nécessaire dans le code
class WhatsAppElements:
    # chemin vers le répertoire de stockage du fichier de configuration
    # Gestion d'une exécution sous cmd via la programmation
    if len(sys.argv) > 1:
        exeFilePath = sys.executable.split("\\ODIM.exe")[0]
        path = f'{exeFilePath}\\Configuration\\whatsappelements.txt'
    else:
        path = f'{os.getcwd()}\\Configuration\\whatsappelements.txt'
    if exists(path):
        try:
            # ouverture et lecture du fichier
            f = open(path, "r")
            values = list(f.read().split("\n"))
            # attribution des références
            # champs de recherche de destinataire
            search = (By.CSS_SELECTOR, values[0])
            # champs de résultat de la recherche de destinataire
            emptyResult = (By.CSS_SELECTOR, values[1])
            # Premier resultat pour la recherche de contact
            firstResultName = (By.CSS_SELECTOR, values[2])
            # composant pour commencer la discussion
            toDiscussionButton = (By.CSS_SELECTOR, values[3])
            # composant avec un url vers la création d'une conversation avec le contact inconnu dans le téléphone
            linkToWeb = (By.CSS_SELECTOR, values[4])
            # popup signalant que le numéro n'existe pas
            phoneNumberNotFound = (By.CSS_SELECTOR, values[5])
            # champs de saisi texte
            conversationInput = (By.CSS_SELECTOR, values[6])
            # composant pour ouvrir le menu d'envoi des pièces jointes
            attachementButton = (By.CSS_SELECTOR, values[7])
            # composant pour joindre une image
            attachementImageButton = (By.CSS_SELECTOR, values[8])
            # composant pour joindre un document
            attachementDocumentButton = (By.CSS_SELECTOR, values[9])
            # composant pour envoyer l'élément joint
            sendAttachementButton = (By.CSS_SELECTOR, values[10])
            # info du message (en cours, distribué, lu)
            messageTime = (By.CSS_SELECTOR, values[11])
            # composant message envoyé
            messageCheck = (By.CSS_SELECTOR, values[12])
            # composant message reçu
            messageDoubleCheck = (By.CSS_SELECTOR, values[13])
            # composant message en erreur
            messageError = (By.CSS_SELECTOR, values[14])
            # composant message
            lastMessage = (By.CSS_SELECTOR, values[15])
            # composant div conversation
            messageDiv = (By.CSS_SELECTOR, values[16])
        except Exception as error:
            logger.error("Erreur lors de la lecture de whatsappelements " + str(error))
    else:
        logger.info("Aucun fichier de whatsappelements")


def getChromedriverJsonVersion():
    driverURL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
    # nommage de l'output
    output = driverURL.split('/')[-1]
    # telechargement du zip
    response = requests.get(driverURL)
    if response.status_code == 200:
        with open(output, 'wb') as f:
            # ecriture du zip en local
            f.write(response.content)
            f.close()

        # ouverture du fichier json contenant la derniere version stable de chromedriver
        with open(output, 'r') as f:
            # lecture du fichier json et recherche du numero de version
            data = str(json.load(f)).split(",")[2].split()[1]
            # suppression du fichier json qui a ete telecharge
        os.remove(output)
        return data.replace("'", "")
    elif response.status_code == 404:
        logger.error("L'url de mise à jour de Chromedriver n'existe plus ou n'est pas disponible")


# Méthode de mise à jour du chromedriver avec en paramètre la version du navigateur chrome
def updateChromedriverVersion(chromeWantedVersion=None):
    # URL de telechargement de la version souhaité. Il n'est pas possible de download a la vole une version d'un chromedriver.
    # Une version doit etre specifie afin que le telechargement fonctionne
    driverURL = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{chromeWantedVersion}/win32/chromedriver-win32.zip"
    logger.info(driverURL)
    # nommage de l'output
    output = driverURL.split('/')[-1]
    # telechargement du zip
    r = requests.get(driverURL)
    with open(output, 'wb') as f:
        # ecriture du zip en local
        f.write(r.content)
        f.close()
    try:
        with ZipFile(output, 'r') as zObject:
            # dézip du fichier archive
            zObject.extractall(path=".\\")
            # replace du chromedriver afin d'en modifier le chemin et le deplacer vers le repertoire indique dans la variable environnement systeme dediee
            # rename ne fonctionne pas si un chromedriver existe deja car dépendant des droits utilisateurs windows pour pouvoir overwrite
            os.replace(f"./{zObject.namelist()[1]}", str(os.environ.get("Chromedriver")))
            zObject.close()
            logger.info(f"Mise à jour du chromedriver vers la version {chromeWantedVersion}")

        # suppression du zip
        os.remove(output)
        # suppression du fichier dezippé
        shutil.rmtree(f'./{output.split(".")[0]}')

    except BadZipFile:
        logger.error(f"La version du chromedriver {chromeWantedVersion} n'est pas disponible sur les repo de Google ")
        ctypes.windll.user32.MessageBoxW("Mise à jour du chromedriver impossible par l'application", 0x1000)
    except Exception as e:
        logger.error("Une erreur non identifiée est survenue lors du téléchargement de la mise à jour du chromedriver")
        logger.error(str(e))
        ctypes.windll.user32.MessageBoxW(
            "Une erreur non identifiée ne permet pas à l'application de mettre à jour le chromedriver", 0x1000)

class WhatsApp:
    """
    This class is used to interact with your whatsapp [UNOFFICIAL API]
    """

    browser = None
    timeout = 300  # seconds
    chrome_service = None

    # Constructeur
    def __init__(self, wait, screenshot=None, session=None):
        try:
            # mise à jour du chromedriver
            updateChromedriverVersion(chromeWantedVersion=getChromedriverJsonVersion())
            chromedriverPath = str(os.environ.get('Chromedriver'))
            if chromedriverPath is None:
                ctypes.windll.user32.MessageBoxW("Variable d\'environnement Chromedriver non défini", 0x1000)
            else:
                if os.path.exists(chromedriverPath):
                    chrome_service = Service(chromedriverPath)
                    chrome_service.creationflags = CREATE_NO_WINDOW

            # L'UTILISATION DU CHROMEDRIVERMANAGER N'EST PLUS POSSIBLE DEPUIS LA VERSION 115 DE CHROME CAR LES RELEASES DE CHROMEDRIVER
            # NE SONT PLUS DISPONIBLE POUR LE CHROMEDRIVERMANAGER
            # chrome_path = ChromeDriverManager().install()

            # Si une session est renseignée
            if session:
                # création de chrome_options pour passer le chemin vers la session en argument de connexion pour passer l'étape QR code
                chrome_options = Options()
                chrome_options.add_argument("--user-data-dir={}".format(session))
                self.browser = webdriver.Chrome(options=chrome_options,
                                                service=chrome_service)  # we are using chrome as our webbrowser

                logger.info("Lancement de la session WhatsApp avec la session renseignée")
            else:
                # Sinon création d'une connexion sans session
                self.browser = webdriver.Chrome(service=chrome_service)
                logger.info("Lancement de la session WhatsApp sans session")
        except Exception as e:
            if isinstance(e, WebDriverException):
                ctypes.windll.user32.MessageBoxW(0,
                                                 "Lancement de la nouvelle session impossible, une fenêtre Chrome lancé par ODIM semble être toujours active.",
                                                 "Erreur", 0x1000)
                logger.error(
                    "WhatsApp : Lancement de la nouvelle session impossible, une fenêtre Chrome lancé par ODIM est toujours active.")
                logger.error(e)
            else:
                ctypes.windll.user32.MessageBoxW(0,
                                                 "Lancement de la nouvelle session impossible suite à une erreur inconnu.",
                                                 "Erreur", 0x1000)
                logger.error("WhatsApp : Lancement de la nouvelle session impossible suite à une erreur inconnu.")

        # requête vers l'url de whatsapp
        if self.browser is not None:
            self.browser.get("https://web.whatsapp.com/")
            # Attente de la localisation du champ de recherche d'un contact pour s'assurer que la fenêtre soit chargée complètement.
            try:
                logger.info("Attente de la localisation du champs de recherche du destinataire")
                WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(WhatsAppElements.search))

            except ProtocolError as pe:
                logger.error(pe)
                ctypes.windll.user32.MessageBoxW(0,
                                                 "La connexion a été interrompu par une action utilisateur",
                                                 "Erreur", 0x1000)
            except TimeoutException as pe:
                logger.error(pe)
                ctypes.windll.user32.MessageBoxW(0,
                                                 "Le délai pour la connexion à WhatsApp est dépassé",
                                                 "Erreur", 0x1000)
        else:
            logger.info("Impossible d'ouvrir le navigateur chrome")
            ctypes.windll.user32.MessageBoxW(0,
                                             "L'application ne parvient pas à ouvrir une nouvelle fenêtre Chrome\n"
                                             "Une fenêtre Chrome ouverte par ODIM est peut être encore active, "
                                             "Si aucune fenêtre Chrome n'est active, il est possible que la session renseignée soit verrouillée suite à une précédente utilisation mal terminée",
                                             "Erreur")

    '''
    Méthode pour vérifier l'existence du contact dans la recherche de contact WhatsApp
    '''

    def checkResult(self, name, message, skipContact):
        try:
            # firstResult est le composant affichant le destinataire correspondant le plus à la recherche
            firstResult = None
            # resultFailed est le composant correspondant à l'absence de résultat pour le destinataire recherché
            resultFailed = None
            try:
                firstResult = self.browser.find_element(*WhatsAppElements.firstResultName)
            except NoSuchElementException:
                # Laissez ce try/except séparés pour ne pas sortir de la fonction
                pass
            try:
                if firstResult is None:
                    resultFailed = WebDriverWait(self.browser, self.timeout).until(
                        EC.element_to_be_clickable(WhatsAppElements.emptyResult))
            except Exception:
                return name, message, "Échec", "Erreur lors de la recherche du contact"

            # Contrôle si le résultat est vide ou si le premier résultat ne correspond pas complètement au numéro
            if resultFailed is not None:
                logger.info("recherche vide")
                # si l'utilisateur souhaite passer les contacts inconnus, return avec la réponse appropriée
                if skipContact:
                    return name, message, "Autre", "Contact inconnu dans le téléphone"
                else:
                    # si l'utilisateur souhaite tout de même contacter le contact, requête vers l'url ci-dessous.
                    self.browser.get("https://wa.me/" + name)
                    # attente du composant
                    if self.browser.current_url.__contains__("&not_found"):
                        self.goto_main()
                        return name, message, "Autre", "Contact inconnu dans WhatsApp"
                    button = WebDriverWait(self.browser, self.timeout).until(
                        EC.element_to_be_clickable(WhatsAppElements.toDiscussionButton))
                    button.click()
                    linkToWeb = WebDriverWait(self.browser, self.timeout).until(
                        EC.element_to_be_clickable(WhatsAppElements.linkToWeb))
                    linkToWeb.click()
                    # Attente chargement de WhatsApp
                    try:
                        # WebDriverWait(self.browser, 5).until(
                        # EC.element_to_be_clickable(WhatsAppElements.infoContainer))
                        WebDriverWait(self.browser, 10).until(
                            EC.element_to_be_clickable(WhatsAppElements.conversationInput))
                    except Exception as toe:
                        # Popup "Le numéro de téléphone partagé via URL n'est pas valide."
                        okButton = self.browser.find_element(*WhatsAppElements.phoneNumberNotFound)
                        okButton.click()
                        return name, message, "Échec", "Contact inconnu dans WhatsApp"
                    return name, message, "Succès", "Contact accepté"
            return name, message, "Succès", "Contact enregistré"

        except Exception as e:
            logger.error("WhatsApp : Erreur lors du contrôle du contact " + str(e))
            pass

    def contactSearch(self, search, name, message, skipContact):
        search.clear()
        search.send_keys(Keys.CONTROL, "a", Keys.DELETE)
        # Composant de recherche renseigné avec le numéro du contact recherché
        search.send_keys(name)
        time.sleep(0.5)
        # return du résultat du test sur l'existence du contact dans WhatsApp
        response = self.checkResult(name, message, skipContact)
        if response[3] == "Contact enregistré":
            search.send_keys(Keys.ENTER)
        return response

    # Méthode pour l'envoi de message texte au destinataire renseigne.
    def send_message(self, name, message, skipContact, randomStructure):
        search = self.browser.find_element(*WhatsAppElements.search)
        response = self.contactSearch(search, name, message, skipContact)
        if response[2] == "Autre" or response[2] == "Échec":
            return response
        try:
            # Contrôle si l'utilisateur souhaite envoyer des messages textes avec une structure aléatoire.
            # La structure aléatoire consiste à découper un message en plusieurs sous messages en se basant sur la présence de caractère espace " " dans le message.
            # Ces caractères sont remplacés ou non de manière aléatoire par un caractère de retour à la ligne "\n"
            if randomStructure:
                # split sur les espaces " "
                messageToArray = message.split(" ")
                message = ""
                # découpage du message en insérant des caractères "\n"
                for texte in messageToArray:
                    # retour à la ligne random
                    if bool(random.getrandbits(1)):
                        texte = texte + "\n"
                    message = message + " " + texte
            # sélection du champ de saisi dès qu'il est cliquable
            send_msg = self.browser.find_element(*WhatsAppElements.conversationInput)
            # cast en string pour éviter les erreurs et découpage du message à chaque retour à la ligne dans le message
            messages = str(message).split("\n")
            # Envoi du message
            for msg in messages:
                send_msg.send_keys(msg)
                send_msg.send_keys(Keys.ENTER)
                time.sleep(1)

            """
            un message a trois status possible correspondant au composant ci-dessous
            
            messageTime -> icone horloge pour le chargement dans la conversation
            messageCheck -> icone message envoyé
            messageDoubleCheck -> icone message reçu
            """

            try:
                time.sleep(2)
                WebDriverWait(self.browser, 300).until_not(EC.element_to_be_clickable(WhatsAppElements.messageTime))
            except TimeoutException:
                try:
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(WhatsAppElements.messageCheck))
                except TimeoutException:
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable(WhatsAppElements.messageDoubleCheck))
            return name, message, "Envoyé", ""
        except TimeoutException:
            return name, message, "Échec", "Pas de réponse de WhatsApp"
        except NoSuchElementException:
            logger.error("Message (NoSuchElementException) : Composant inexistant")
            return name, message, "Échec", "Le composant n'est pas localisé dans la page"
        except Exception as e:
            logger.error("Message (Exception) : Erreur non identifiée : " + str(e))
            return name, message, "Échec", "Erreur non gérée"

    # Méthode pour l'envoi de média image
    def send_picture(self, name, media_location, skipContact):
        search = self.browser.find_element(*WhatsAppElements.search)
        response = self.contactSearch(search, name, media_location, skipContact)
        if response[2] == "Autre" or response[2] == "Échec":
            return response
        try:

            # Par defaut un webdriverwait va gérer l'exception de type NoSuchElementException mais pas StaleElementReferenceException, on redefini alors
            # le comportement en ajoutant la StaleElementReferenceException.
            # Celle ci peut apparaitre pendant l'attente du composant recherche et faire planter le code si elle n'est pas geree.

            ignoresExceptions = StaleElementReferenceException, NoSuchElementException
            WebDriverWait(self.browser, self.timeout, ignored_exceptions=ignoresExceptions).until(
                EC.element_to_be_clickable(WhatsAppElements.attachementButton))
            # affectation du bouton de menu de fichier joint
            attach_btn = self.browser.find_element(*WhatsAppElements.attachementButton)
            attach_btn.click()
            time.sleep(1)
            # button pour joindre un fichier image
            attach_img_btn = self.browser.find_element(*WhatsAppElements.attachementImageButton)
            attach_img_btn.send_keys(media_location)
            time.sleep(1)
            # button d'envoi
            send_btn = WebDriverWait(self.browser, self.timeout, ignored_exceptions=ignoresExceptions).until(
                EC.element_to_be_clickable(WhatsAppElements.sendAttachementButton))
            send_btn.click()
            search.send_keys(Keys.CONTROL, "a", Keys.DELETE)
            # attente de la confirmation de l'envoi
            try:
                time.sleep(2)
                WebDriverWait(self.browser, 10).until(EC.presence_of_element_located(WhatsAppElements.messageDiv))
                lastMessage = \
                    self.browser.find_element(*WhatsAppElements.messageDiv).find_elements(
                        *WhatsAppElements.lastMessage)[-1]
                WebDriverWait(lastMessage, 2).until(EC.presence_of_element_located(WhatsAppElements.messageError))
                logger.error("Whatsapp n'a pas réussi à charger la pièce jointe")
                return name, media_location, "Échec", "Whatsapp n'a pas réussi a charger la pièce jointe dans la conversation"
            except TimeoutException:
                try:
                    WebDriverWait(self.browser, 300).until_not(EC.element_to_be_clickable(WhatsAppElements.messageTime))
                except TimeoutException:
                    try:
                        WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(WhatsAppElements.messageCheck))
                    except TimeoutException:
                        WebDriverWait(self.browser, 10).until(
                            EC.element_to_be_clickable(WhatsAppElements.messageDoubleCheck))
                return name, media_location, "Envoyé", ""
        except TimeoutException:
            logger.error("Média (TimeoutException) : La requête a expiré auprès de WhatsApp !")
            return name, media_location, "Échec", "Pas de réponse de WhatsApp"
        except NoSuchElementException:
            logger.error("Média (NoSuchElementException) : Composant inexistant")
            return name, media_location, "Échec", "Le composant n'est pas localisé dans la page"
        except StaleElementReferenceException:
            logger.error("Média (StaleElementReferenceException) : Erreur dans la référence du composant")
            return name, media_location, "Échec", "Le composant n'est pas référencé dans la page"
        except Exception as e:
            logger.error("Média (Exception) : Erreur non identifiée : " + str(e))
            return name, media_location, "Échec", "Erreur non gérée"

    # For sending documents
    def send_document(self, name, document_location, skipContact):
        search = self.browser.find_element(*WhatsAppElements.search)
        response = self.contactSearch(search, name, document_location, skipContact)
        if response[2] == "Autre" or response[2] == "Échec":
            return response
        try:
            # Par defaut un webdriverwait va ignorer l'exception de type NoSuchElementException, on redefini le comportement en ajoutant
            # la StaleElementReferenceException. Celle-ci peut apparaitre pendant l'attente du composant recherche et faire planter le code.

            ignoresExceptions = StaleElementReferenceException, NoSuchElementException
            WebDriverWait(self.browser, self.timeout, ignored_exceptions=ignoresExceptions).until(
                EC.element_to_be_clickable(WhatsAppElements.attachementButton))
            # affectation du bouton de menu de fichier joint
            attach_btn = self.browser.find_element(*WhatsAppElements.attachementButton)
            attach_btn.click()
            time.sleep(1)
            # button pour joindre un document
            attach_doc_btn = self.browser.find_element(*WhatsAppElements.attachementDocumentButton)
            attach_doc_btn.send_keys(document_location)
            # button d'envoi
            send_btn = WebDriverWait(self.browser, self.timeout, ignored_exceptions=ignoresExceptions).until(
                EC.element_to_be_clickable(WhatsAppElements.sendAttachementButton))
            send_btn.click()
            search.send_keys(Keys.CONTROL, "a", Keys.DELETE)
            # attente de la confirmation de l'envoi
            try:
                time.sleep(2)
                WebDriverWait(self.browser, 300).until_not(
                    EC.element_to_be_clickable(WhatsAppElements.messageTime))
            except TimeoutException:
                try:
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable(WhatsAppElements.messageCheck))
                except TimeoutException:
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable(WhatsAppElements.messageDoubleCheck))
            return name, document_location, "Envoyé", ""
        except TimeoutException:
            logger.error("Document (TimeoutException) : La requête a expiré auprès de WhatsApp !")
            return name, document_location, "Échec", "Pas de réponse de WhatsApp"
        except NoSuchElementException:
            logger.error("Document (NoSuchElementException) : Composant inexistant")
            return name, document_location, "Échec", "Le composant n'est pas localisé dans la page"
        except Exception as e:
            logger.error("Document (Exception) : Erreur non identifiée : " + str(e))
            return name, document_location, "Échec", "Erreur non gérée"

    # Extraction vers un fichier unique qui n'est pas horodaté dans son titre. Effacement par réécriture à chaque extraction
    def extract_contacts(self) -> iter:
        lst = []
        listDicussion = (By.CSS_SELECTOR, '[aria-label="Liste de discussions"]')
        discussionElement = (By.CSS_SELECTOR, '[role="listitem"]')
        for contact in self.browser.find_element(*listDicussion).find_elements(*discussionElement):
            lst.append(contact.text.split("\n")[0])
        return lst

    # override the timeout
    def override_timeout(self, new_timeout):
        self.timeout = new_timeout

    # Get the driver object
    def get_driver(self):
        return self.browser

    # This method is used to quit the browser
    def quit(self):
        self.browser.quit()

    # Retour à la page d'accueil de whatsapp ou de la session en cours
    def goto_main(self):
        try:
            self.browser.get("https://web.whatsapp.com/")
            Alert(self.browser).accept()
        except Exception as e:
            logger.error(e)
            pass
        WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(WhatsAppElements.search))
