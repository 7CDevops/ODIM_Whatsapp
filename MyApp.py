import logging
import sys
import os
from datetime import date, timedelta, datetime

# Create and configure logger
exePath = sys.executable.split("\\ODIM.exe")[0]
try:
    os.makedirs(exePath + "/LOG/", exist_ok=True)
except FileNotFoundError:
    exePath = os.getcwd()
    os.makedirs(exePath + "/LOG/", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='w',
    filename=f'{exePath}/LOG/ODIM{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}.log')
logger = logging.getLogger()

os.environ["KIVY_NO_FILELOG"] = '1'
from kivy import LOG_LEVELS
import csv
import ctypes
import subprocess
import threading
import time
from matplotlib import pyplot
import detectSocialNetwork
import generateContact
import metadataEraser
from retweetLike import generate_retweet_like
from kivy.config import Config

Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
# Les configurations doivent être déclarées en premier avant tous les imports suivants
Config.set('graphics', 'resizable', '1')  # 0 being off 1 being on as in true/false
Config.set('graphics', 'width', '900')
Config.set('graphics', 'height', '700')
from kivy.uix.textinput import TextInput
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from random import randint
from kivy.uix.boxlayout import BoxLayout
from whatsapp import WhatsApp
from telegram import Telegram
from os.path import exists
from kivymd.app import MDApp
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from dateutil.relativedelta import relativedelta
from kivy.core.window import Window

logger.setLevel(LOG_LEVELS["info"])

# variable pour le status d'un message et l'indice de celui-ci
global statusDict

# Taille par défaut de la fenêtre de l'interface
normalSize = (1000, 900)
# Taille par défaut de la fenêtre de l'interface
maximizeSize = (1200, 900)
# Code couleur par défaut
validColor = 0, 0, 1, 0.3
# Code couleur d'erreur
errorColor = 237 / 255, 70 / 255, 70 / 255, 0.5


# Classe Configuration pour le stockage des variables pour toutes les configurations liées à l'envoi de message
class Configuration:
    delay = 1
    applyPacketSending = applyRandomDelay = skipUnknownContact = relativePath = sendByWhatsApp = sendByTelegram = randomTexteStructure = False
    volume = pause = minDelay = maxDelay = packetCurrentSize = 0
    savedSession = ""


# Mise à jour des labels pour afficher un résultat à l'utilisateur
def updateResult(self, Success, Other, Failed):
    self.ids.labelSuccessCount.text = "Succès : " + str(Success)
    self.ids.labelOtherCount.text = "Autre : " + str(Other)
    self.ids.labelFailedCount.text = "Échec : " + str(Failed)


# Reset à une valeur vide pour les labels pour afficher les résultats
def resetSuccessFailedCountLabel(self):
    self.ids.labelSuccessCount.text = " "
    self.ids.labelOtherCount.text = " "
    self.ids.labelFailedCount.text = " "


# Envoi de messages en fonction du type renseigné pour le message
def sendMessages(self=None, num=None, content=None, typeContent=None):
    global statusDict
    currentSession = LoginScreen.currentSession

    """
    Dans WhatsApp il est possible de créer une conversation avec un contact inconnu dans le téléphone.
    Cela nécessite de requêter un URL particulier de WhatsApp ajoutant des étapes pour le BOT.
    Si le contact n'existe pas dans WhatsApp cela ne permettra pas in fine de créer une conversation avec lui.
    Le boolean skipContact permet de laisser le choix à l'utilisateur de tenter de créer ou non une conversation avec un numéro inconnu dans le téléphone.
    """
    # self peut être à None en cas d'envoi programmé car le context graphique n'existe pas
    if self is None:
        skipContact = Configuration.skipUnknownContact
        randomStructure = Configuration.randomTexteStructure
        relativePath = Configuration.relativePath
    else:
        # Envoi normal
        skipContact = self.ids.cbSkipContact.active
        randomStructure = self.ids.cbRandomTextStructureCheckBox.active
        relativePath = self.ids.cbRelativeCheckBox.active

    # si type Text
    if typeContent.strip().upper().__eq__("TEXT"):
        # envoi du message avec stockage du retour de la commande.
        statusDict[LoginScreen.indice] = currentSession.send_message(num, content, skipContact, randomStructure)
        LoginScreen.indice += 1

    # si type Media
    elif typeContent.strip().upper().__eq__("MEDIA"):
        if relativePath:
            # si l'utilisateur fait le choix de chemin relatif, on ajoute le path du répertoire courant
            content = os.getcwd() + content
        if exists(content):
            # si le path existe bien on crée une image temporaire sans metadata.
            file = metadataEraser.CheckPathAndErase(content)
            # envoi du média avec stockage du retour de la commande.
            statusDict[LoginScreen.indice] = currentSession.send_picture(num, file, skipContact)
            os.remove(file)
        else:
            # si le chemin n'existe pas, le message est mis en échec.
            statusDict[LoginScreen.indice] = (
                num, content, "Échec", "Le chemin vers la ressource n'est pas reconnu")
        LoginScreen.indice += 1

    # si type Document
    elif typeContent.strip().upper().__eq__('DOCUMENT'):
        fullPath = os.path.join(os.getcwd(), "r", content)
        if exists(fullPath):
            # si le chemin existe, envoi du document avec stockage du retour de la commande.
            statusDict[LoginScreen.indice] = currentSession.send_document(num, (
                os.path.join(os.getcwd(), "r", content)), skipContact)
        else:
            # si le chemin n'existe pas, le message est mis en échec.
            statusDict[LoginScreen.indice] = (
                num, content, "Échec", "Le chemin vers la ressource n'est pas reconnu")
        LoginScreen.indice += 1

    # si type Session
    elif typeContent.strip().upper().__eq__('SESSION'):
        # changement de session avec la nouvelle session renseigné.
        changeSession(self, content)
    else:
        logger.error(f"Type : {typeContent} non pris en charge")

    # rafraichissement de la page pour éviter une saturation du cache chrome.
    if LoginScreen.indice == 300:
        currentSession.goto_main()


# Méthode pour appliquer les configurations déterminées par l'utilisateur
def applyConf(self):
    # nombre de messages dans le packet courent
    Configuration.packetCurrentSize += 1

    # En cas de programmation le contexte graphique n'existe pas donc les paramètres de l'envoi voulu par l'utilisateur sont ceux de la configuration.
    if self is None:
        sendByPacket = Configuration.applyPacketSending
        currentSendVolume = Configuration.volume
        sendPause = Configuration.pause

        randomDelay = Configuration.applyRandomDelay
        randomDelayMin = Configuration.minDelay
        randomDelayMax = Configuration.maxDelay
    else:
        sendByPacket = self.ids.cbByPacket.active
        currentSendVolume = self.ids.inputVolume.text
        sendPause = self.ids.inputPause.text

        randomDelay = self.ids.cbRandomDelay.active
        randomDelayMin = self.ids.inputDelaiMin.text
        randomDelayMax = self.ids.inputDelaiMax.text

    # parsing de l'input pour applique un temps de pause correspondant, si échec pause de 1s
    try:
        time.sleep(int(Configuration.delay))
    except ValueError:
        time.sleep(1)

    # si un délai aléatoire doit être appliqué, parsing de l'input de temps min et max, si échec pass
    try:
        if randomDelay:
            time.sleep(randint(int(randomDelayMin), int(randomDelayMax)))
    except NameError:
        pass

    # si un système de message par groupe/paquet est configuré, parsing de l'input du volume du groupe et du temps de pause, si échec pass
    try:
        if sendByPacket & (int(currentSendVolume) == Configuration.packetCurrentSize):
            time.sleep(int(sendPause))
            Configuration.packetCurrentSize = 0
            # remise à zéro de la taille du paquet une fois la pause effectuée.
    except NameError:
        pass


# Gestion d'un fichier d'envoi en extension .csv
def handleCSVFileMessages(self, file, progressBar):
    # ouverture du fichier et parsing dans un objet dédié au csv
    nbLine = None
    progressBar.value = 0
    self.ids.progressBarLabel.text = ""

    # ouverture du fichier une premiere fois pour determiner le nombre de ligne renseignee
    with open(file, "r") as readingFile:
        # nombre de ligne dans le fichier
        nbLine = sum(1 for _ in readingFile)
        readingFile.close()

    with open(file, "r") as readingFile:
        csvreader = csv.reader(readingFile)
        # enumerate est une fonction pour enumerer le nombre de ligne d'un objet iterable
        for index, row in enumerate(csvreader):
            try:
                # split dans chaque ligne sur le séparateur pour isoler le destinataire, le contenu et le type d'envoi
                num = row[0].split(";")[0]
                content = row[0].split(";")[1]
                typeContent = row[0].split(";")[2]
                # envoi du message de la ligne correspondante dans le csv
                sendMessages(self=self, num=num, content=content, typeContent=typeContent)
                # application des configurations à l'issue d'un envoi
                applyConf(self)
                progressBar.value = (index+1)/nbLine
                self.ids.progressBarLabel.text = f'{(index+1)} / {nbLine}'
            except Exception as error:
                logger.error(content)
                logger.error("Problème lors du parsing du fichier CSV à la ligne " + str(index))
                logger.error(str(error))
        readingFile.close()


# Chargement de la configuration enregistrée à la dernière utilisation
def loadConfiguration(self):
    # chemin vers le répertoire de stockage du fichier de configuration
    path = f'{os.getcwd()}\Configuration\config.txt'
    logger.info(path)
    if exists(path):
        try:
            # ouverture et lecture du fichier
            f = open(path, "r")
            values = list(f.read().split("\n"))
            # attribution des configurations dans l'ordre des composants dans le fichier .kv
            self.ids.manager.ids.login.ids.inputDelai.text = values[0]
            self.ids.manager.ids.login.ids.cbByPacket.active = (
                False if values[1].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.inputVolume.text = values[2]
            self.ids.manager.ids.login.ids.inputPause.text = values[3]
            self.ids.manager.ids.login.ids.cbRandomDelay.active = (
                False if values[4].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.inputDelaiMin.text = values[5]
            self.ids.manager.ids.login.ids.inputDelaiMax.text = values[6]
            self.ids.manager.ids.login.ids.cbStayConnected.active = (
                False if values[7].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.inputSession.text = values[8]
            self.ids.manager.ids.login.ids.cbSkipContact.active = (
                False if values[9].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.cbRelativeCheckBox.active = (
                False if values[10].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.cbRandomTextStructureCheckBox.active = (
                False if values[11].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.cbWhatsApp.active = (
                False if values[12].__eq__("False") else True
            )
            self.ids.manager.ids.login.ids.cbTelegram.active = (
                False if values[13].__eq__("False") else True
            )
        except Exception as error:
            logger.error("Erreur lors de la lecture de la configuration " + str(error))
    else:
        logger.info("Aucun fichier de configuration")
        ctypes.windll.user32.MessageBoxW(0, "Aucune configuration n'est disponible pour l'envoi", "Erreur", 0x1000)


def loadScheduledConfiguration():
    # chemin vers le répertoire de stockage du fichier de configuration
    # sys.executable -> C:\Users\user\PycharmProjects\pythonWhatsApp\dist
    exeFilePath = sys.executable.split("\\ODIM.exe")[0]
    path = f'{exeFilePath}\Configuration\config.txt'
    logger.info(path)
    if exists(path):
        # ouverture et lecture du fichier
        f = open(path, "r")
        values = list(f.read().split("\n"))
        # attribution des configurations dans l'ordre des composants dans le fichier .kv
        Configuration.delay = values[0]
        Configuration.applyPacketSending = False if values[1].__eq__("False") else True
        Configuration.volume = values[2]
        Configuration.pause = values[3]
        Configuration.applyRandomDelay = False if values[4].__eq__("False") else True
        Configuration.minDelay = values[5]
        Configuration.maxDelay = values[6]
        exeFilePath = sys.executable.split("\\ODIM.exe")[0]
        path = f'{exeFilePath}\\SauvegardesChromeUserData\\ChromeUserData'
        Configuration.savedSession = values[8] if not values[8].__eq__("") else path
        Configuration.skipUnknownContact = False if values[9].__eq__("False") else True
        Configuration.relativePath = False if values[10].__eq__("False") else True
        Configuration.randomTexteStructure = False if values[11].__eq__("False") else True
        Configuration.sendByWhatsApp = False if values[12].__eq__("False") else True
        Configuration.sendByTelegram = False if values[13].__eq__("False") else True
    else:
        ctypes.windll.user32.MessageBoxW(0, "Aucun fichier de configuration ou lecture impossible", "Erreur", 0x1000)
        logger.info("Aucun fichier de configuration ou lecture impossible")


# Contrôle de la configuration à sauvegarder
def checkFields(self):
    delay = self.ids.inputDelai.text
    volume = self.ids.inputVolume.text
    pause = self.ids.inputPause.text
    delayMin = self.ids.inputDelaiMin.text
    delayMax = self.ids.inputDelaiMax.text
    session = self.ids.inputSession.text
    if len(delay) == 0 or not delay.isnumeric() or int(delay) < 1:
        ctypes.windll.user32.MessageBoxW(0, "Le delai entre les messages doit être un entier supérieur ou égal à 1",
                                         "Erreur", 0x1000)
        return False
    if self.ids.cbByPacket.active:
        if len(volume) == 0 or not volume.isnumeric() or int(volume) < 1:
            ctypes.windll.user32.MessageBoxW(0, "Le volume de messages doit être un entier positif", "Erreur", 0x1000)
            return False
        if len(pause) == 0 or not pause.isnumeric() or int(pause) < 1:
            ctypes.windll.user32.MessageBoxW(0, "Le volume de messages doit être un entier positif ", "Erreur", 0x1000)
            return False
    if self.ids.cbRandomDelay.active:
        if len(delayMin) == 0 or not delayMin.isnumeric() or int(delayMin) < 1:
            ctypes.windll.user32.MessageBoxW(0, "Le delai minimum doit être un entier positif ", "Erreur", 0x1000)
            return False
        if len(delayMax) == 0 or not delayMax.isnumeric() or int(delayMax) < 1:
            ctypes.windll.user32.MessageBoxW(0, "Le delai maximum doit être un entier positif ", "Erreur", 0x1000)
            return False
    if len(session) > 0:
        if not os.path.exists(session):
            ctypes.windll.user32.MessageBoxW(0, "Le chemin de la session n'existe pas sous windows", "Erreur", 0x1000)
            return False
    return True


# Sauvegarde de la configuration courante pour pouvoir la charger lors d'un prochain lancement.
def saveConfiguration(self):
    # chemin vers le répertoire de stockage du fichier de configuration
    path = f'{os.getcwd()}\Configuration'
    # sauvegarde de fichier avec les configurations, s'il n'existe pas il est créé par la fonction open()
    if checkFields(self):
        if not os.path.exists(path):
            ctypes.windll.user32.MessageBoxW(0,
                                             "Le répertoire Configuration n'est pas présent dans le répertoire de ODIM.\n"
                                             "Veuillez le recréer ou procéder à une nouvelle installation",
                                             "Erreur", 0x1000)
            return
        try:
            with open(path + "\config.txt", 'w') as file:
                file.write(
                    self.ids.inputDelai.text + "\n" +
                    str(self.ids.cbByPacket.active) + "\n" +
                    self.ids.inputVolume.text + "\n" +
                    self.ids.inputPause.text + "\n" +
                    str(self.ids.cbRandomDelay.active) + "\n" +
                    self.ids.inputDelaiMin.text + "\n" +
                    self.ids.inputDelaiMax.text + "\n" +
                    str(self.ids.cbStayConnected.active) + "\n" +
                    self.ids.inputSession.text + "\n" +
                    str(self.ids.cbSkipContact.active) + "\n" +
                    str(self.ids.cbRelativeCheckBox.active) + "\n" +
                    str(self.ids.cbRandomTextStructureCheckBox.active) + "\n" +
                    str(self.ids.cbWhatsApp.active) + "\n" +
                    str(self.ids.cbTelegram.active) + "\n"
                )
                file.close()
        except Exception as error:
            logger.error("Problème lors de la sauvegarde de la configuration " + str(error))
            ctypes.windll.user32.MessageBoxW(0, "Erreur lors de la sauvegarde de la configuration", "Erreur", 0x1000)
    else:
        logger.error("Problème lors de la saisie de la configuration")


# Préparation de l'envoi de message en procédant au contrôle des inputs
def startSend(file, self):
    self.ids.buttonLaunch.disabled = True
    progressBar = self.ids.botProgressBar
    progressBar.value = 0
    global statusDict
    # dictionnaire qui va stocker le retour commande de chaque envoi
    statusDict = dict()
    # Reset à leurs valeurs initiales de toutes les variables de classe de la configuration de l'envoi et du suivi des messages en succès ou en échec.
    LoginScreen.indice = LoginScreen.SuccessCount = LoginScreen.FailedCount = LoginScreen.OtherCount = Configuration.packetCurrentSize = 0
    # Reset à false de tous les booleans servant à contrôler la saisie conforme de l'utilisateur
    delaiIsCorrect = volumeIsCorrect = pauseIsCorrect = delaiMinIsCorrect = delaiMaxIsCorrect = extensionIsCorrect = False
    try:
        # Affectation du choix de délai à la variable de classe.
        Configuration.delay = int(self.ids.inputDelai.text)
        delaiIsCorrect = True
    except ValueError:
        ctypes.windll.user32.MessageBoxW(0, "Le délai doit être un entier positif", "Erreur", 0x1000)

    # contrôle des inputs si l'envoi se fait par paquet
    if self.ids.cbByPacket.active:
        try:
            # Affectation du choix du volume d'envoi à la variable de classe.
            Configuration.volume = int(self.ids.inputVolume.text)
            volumeIsCorrect = True
        except ValueError:
            ctypes.windll.user32.MessageBoxW(0, "Le volume doit être un entier positif", "Erreur", 0x1000)
        try:
            # Affectation du choix du temps de pause à la variable de classe.
            Configuration.pause = int(self.ids.inputPause.text)
            pauseIsCorrect = True
        except ValueError:
            ctypes.windll.user32.MessageBoxW(0, "Le temps de pause doit être un entier positif", "Erreur", 0x1000)
    else:
        volumeIsCorrect = True
        pauseIsCorrect = True

    # contrôle des inputs si l'envoi se fait en ajoutant un délai aléatoire
    if self.ids.cbRandomDelay.active:
        try:
            # Affectation du choix de délai minimale à la variable de classe.
            Configuration.minDelay = int(self.ids.inputDelaiMin.text)
            delaiMinIsCorrect = True
        except ValueError:
            ctypes.windll.user32.MessageBoxW(0, "Le délai minimum doit être un entier positif", "Erreur", 0x1000)
        try:
            # Affectation du choix de délai maximale à la variable de classe.
            Configuration.maxDelay = int(self.ids.inputDelaiMax.text)
            delaiMaxIsCorrect = True
        except ValueError:
            ctypes.windll.user32.MessageBoxW(0, "Le délai maximum doit être un entier positif", "Erreur", 0x1000)
    else:
        delaiMinIsCorrect = True
        delaiMaxIsCorrect = True

    # stockage de l'extension du fichier
    fileExtension = os.path.splitext(file)[-1]

    # contrôle sur l'extension du fichier avant de procéder à l'envoi de messages.
    if not fileExtension == ".csv":
        logger.info(f"Extension de fichier {fileExtension} non pris en charge")
        ctypes.windll.user32.MessageBoxW(0, f"Extension de fichier {fileExtension} non pris en charge", "Erreur", 0x1000)
    else:
        extensionIsCorrect = True

    # Contrôle de tout les boolean pour pouvoir continuer l'envoi de messages.
    if delaiIsCorrect and pauseIsCorrect and volumeIsCorrect and delaiMinIsCorrect and delaiMaxIsCorrect and extensionIsCorrect:
        # instanciation de la session whatsapp/telegram qui va servir à envoyer les messages
        LoginScreen.currentSession = getSession(self)

        # gestion de l'envoi en fonction de l'extension du fichier chargé
        if fileExtension == ".csv":
            handleCSVFileMessages(self, file, progressBar)
        # calcul du nombre de messages en succès et en échec ou autre
        for value in statusDict.values():
            if str(value).__contains__("Envoyé"):
                LoginScreen.SuccessCount += 1
            elif str(value).__contains__("Échec"):
                LoginScreen.FailedCount += 1
            else:
                LoginScreen.OtherCount += 1
        # Mise à jour des labels pour afficher les résultats
        updateResult(self, LoginScreen.SuccessCount, LoginScreen.OtherCount, LoginScreen.FailedCount)
        time.sleep(1)
        # Fermeture de la session en cours.
        LoginScreen.currentSession.quit()
        logger.info("Fin de l'envoi WhatsApp")
        # Envoi effectué donc Boolean pour un nouveau rapport disponible à True
        LoginScreen.newRapportAvailable = True
        self.ids.buttonLaunch.disabled = False
    else:
        pass


# Méthode pour le changement de session en utilisant le chemin renseigné par l'utilisateur dans le fichier d'envoi
# le paramètre newSession est le chemin vers la nouvelle session.
def changeSession(self, newSession):
    # fermeture de la session en cours pour permettre la création d'une nouvelle
    LoginScreen.currentSession.quit()
    try:
        # contrôle pour instancier la session sur la plateforme correspondante
        if self.ids.cbWhatsApp.active:
            LoginScreen.currentSession = WhatsApp(60, session=newSession)
        elif self.ids.cbTelegram.active:
            LoginScreen.currentSession = Telegram(60, session=newSession)
    except Exception as error:
        # si problème, notification à l'utilisation et l'envoi ne reprend pas, car la session précédente a été fermée.
        ctypes.windll.user32.MessageBoxW(0, error.__str__(), "Problème lors du changement de session", 0x1000)
        logger.error("Impossible de se connecter au vecteur sélectionné avec la session renseignée")


# Méthode pour retourner une session utilisateur sur WhatsApp ou Télégram
def getSession(self):
    """
     Création de la session en fonction du choix de la plateforme et du chemin vers le répertoire ChromeUserData si il est renseigné.

     Trois possibilitées :

        1 : Pas de session renseignée et pas de sauvegarde de la connexion → Instanciation d'une connexion vers la plateforme correspondante et authentification par QR Code
           Session non sauvegardée à la fin de l'envoi.

        2 : Session non renseignée et sauvegardée → Authentification nécessaire de l'utilisateur par QR code, session sauvegardee a cote du projet / exe  et réutilisable sans QR code ultérieurement

        3 : Session renseignée et sauvegardée → Instanciation de la session sur la plateforme correpondante sans QR code et sauvegarde à la fin de l'envoi vers le chemin de la session qui
                                                a ete renseignee

     """
    session = None
    sessionPath = r"%s\ChromeUserData" % self.ids.inputSession.text
    # si la cb pour WhatsApp est sélectionnée
    if self.ids.cbWhatsApp.active:
        # si l'utilisateur fait le choix de rester connecté
        if self.ids.cbStayConnected.active:
            # Contrôle si la session renseignée existe, sinon création
            if not exists(sessionPath):
                try:
                    os.mkdir(sessionPath)
                except FileNotFoundError:
                    os.makedirs(os.getcwd() + "\\SauvegardesChromeUserData\\ChromeUserData", exist_ok=True)
                    sessionPath = os.getcwd() + "\\SauvegardesChromeUserData\\ChromeUserData"
            # Instanciation de la session WhatsApp
            session = WhatsApp(60, session=sessionPath)
        else:
            session = WhatsApp(60)
    # si la cb pour Telegram est sélectionnée
    elif self.ids.cbTelegram.active:
        # si l'utilisateur fait le choix de rester connecté
        if self.ids.cbStayConnected.active:
            # Contrôle si la session renseignée existe, sinon création
            if not exists(sessionPath):
                try:
                    os.mkdir(sessionPath)
                except FileNotFoundError:
                    os.makedirs(os.getcwd() + "\\SauvegardesChromeUserData\\ChromeUserData", exist_ok=True)
                    sessionPath = os.getcwd() + "\\SauvegardesChromeUserData\\ChromeUserData"
            # Instanciation de la session Telegram
            session = Telegram(60, session=sessionPath)
        else:
            session = Telegram(60)
    # return de la session instanciée
    return session


# Gestionnaire de vue dans l'application dans le fichier .kv
class ScreenManagement(ScreenManager):
    pass


# Class custom redéfinissant les TextInput
class RoundedInput(TextInput):
    text_width = NumericProperty()

    def update_padding(self):
        self.text_width = self._get_text_width(
            self.text,
            self.tab_width,
            self._label_cached
        )


# Méthode pour récupérer le chemin d'une ressource notamment lors de l'exécution depuis un exécutable.
# Si exécution en environnement de dev, renvoi du chemin de stockage.
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception as error:
        base_path = os.path.abspath("")
        logger.error(str(error))
    return os.path.join(base_path, relative_path)


# Classe de l'écran permettant de créer une programmation afin de pouvoir déclencher un envoi à un GDH sur fichier
class ProgrammationScreen(Screen):
    # image d'arrière-plan de l'interface
    sourceFile = ""
    image_source = StringProperty()
    dateIsValid = timeIsValid = nameProgIsValid = sourceFileIsValid = False

    def __init__(self, **kwargs):
        super(ProgrammationScreen, self).__init__(**kwargs)
        self.image_source = resource_path(r'Images/4882066.jpg')
        # à l'instanciation de l'écran, set des variables de stockage de la date et du temps sélectionné par l'utilisateur depuis l'interface à une valeur vide.
        self.selectedDate = self.selectedTime = ''

    # Sauvegarde du temps sélectionné dans l'horloge par l'utilisateur
    def on_saveTime(self, instance, value):
        self.selectedTime = value
        # Affichage du temps sélectionné dans l'interface avec le composant dédié
        self.ids.inputTime.text = str(value)

    # Gestion d'annulation de la sélection par l'utilisateur
    def on_cancelTime(self, instance, value):
        self.ids.inputTime.text = ""

    # Création et affichage du composant timePicker
    def show_time_picker(self):
        # Instanciation du TimePicker
        time_dialog = MDTimePicker()
        # binding des méthodes on_save et on_cancel sur les méthodes déclarées au-dessus.
        time_dialog.bind(on_save=self.on_saveTime, on_cancel=self.on_cancelTime)
        # Application thème Dark
        time_dialog.theme_cls.theme_style = "Dark"
        time_dialog.open()

    # Sauvegarde de la date sélectionnée dans le calendrier par l'utilisateur
    def on_saveDate(self, instance, value, date_range):
        self.selectedDate = value
        self.ids.inputDate.text = str(value)

    # Gestion d'annulation de la sélection par l'utilisateur
    def on_cancelDate(self, instance, value):
        self.ids.inputDate.text = ""

    # Création et affichage du composant datePicker
    def show_date_picker(self):
        # instanciation des variables de temps minimale et maximale
        # min date → date aujourd'hui
        min_date = datetime.strptime(f'{date.today()}', '%Y-%m-%d').date()
        # max date → aujourd'hui + 1 mois
        max_date = date.today() + relativedelta(months=1)
        # Instanciation du datePicker avec la date minimale et maximale déterminée.
        # Un datePicker implémenté avec une limite de temps doit obligatoirement implémenter min et max date
        date_dialog = MDDatePicker(min_date=min_date, max_date=max_date)
        # Application thème Dark
        date_dialog.theme_cls.theme_style = "Dark"
        # Binding des méthodes de sauvegarde et d'annulation du datePicker avec les méthodes déclarées ci-dessus
        date_dialog.bind(on_save=self.on_saveDate, on_cancel=self.on_cancelDate)
        date_dialog.open()

    # explorateur de fichier pour importer le fichier devant faire l'objet d'une programmation
    def open_explorer(self):
        # Explorateur windows pour importer le fichier d'envoi de message
        try:
            Tk().withdraw()  # Suppression de l'interface principale qui s'affiche par default dès l'exécution d'un composant Tkinter
            self.sourceFile = askopenfilename(title="Sélectionner le fichier csv à importer :",
                                              filetypes=[("Fichier csv", "*.csv")])
            if self.sourceFile != "":
                self.ids.inputFile.text = self.sourceFile
                logger.info(f"Import fichier pour programmation  : {self.ids.inputFile.text} ")
        except IndexError:
            logger.warning("Import fichier WhatsApp : Sélection vide")

    # Lancement de la programmation avec le contrôle des inputs. Si tout est OK, inscription du script dans le planificateur de tâches.
    def triggerProgrammation(self):
        try:
            # Instanciation d'un dateTime en combinant la date et le temps sélectionnée par l'utilisateur.
            selectedDateTime = datetime.combine(self.selectedDate, self.selectedTime)
            # contrôle si le dateTime est antérieur à la date d'aujourd'hui
            if selectedDateTime < datetime.today():
                # code couleur rouge pour indiquer une erreur
                # c'est en théorie impossible car une date minimale est implémentée à la création du composant
                self.ids.DateTimeGrid.color = errorColor
                self.dateIsValid = self.timeIsValid = False
            else:
                # code couleur initiale
                self.dateIsValid = self.timeIsValid = True
                self.ids.DateTimeGrid.color = validColor
        except NameError:
            # Si champs vide, application du code couleur erreur et notification à l'utilisateur
            self.ids.DateTimeGrid.color = errorColor
            self.dateIsValid = self.timeIsValid = False
            ctypes.windll.user32.MessageBoxW(0, "GDH non conforme", "Erreur de GDH", 0x1000)
        except TypeError:
            # Si champs vide, application du code couleur erreur et notification à l'utilisateur
            self.ids.DateTimeGrid.color = errorColor
            self.dateIsValid = self.timeIsValid = False
            ctypes.windll.user32.MessageBoxW(0, "GDH non conforme", "Erreur de GDH", 0x1000)
        # Un nom de programmation doit obligatoirement être renseigné pour pouvoir nommer le fichier script.
        if self.ids.inputProgName.text == '':
            # Si champs vide, application du code couleur erreur et notification à l'utilisateur
            self.ids.scriptGrid.color = errorColor
            self.nameProgIsValid = False
            ctypes.windll.user32.MessageBoxW(0, "Nom de programmation manquant", "Erreur de nommage", 0x1000)
        else:
            self.ids.scriptGrid.color = validColor
            self.nameProgIsValid = True
        # Contrôle si le fichier devant faire l'objet d'une programmation a bien été renseigné
        if self.ids.inputFile.text == '':
            # Si champs vide, application du code couleur erreur et notification à l'utilisateur
            self.ids.scriptGrid.color = errorColor
            self.sourceFileIsValid = False
            ctypes.windll.user32.MessageBoxW(0, "Aucun fichier CSV renseigné", "Erreur de fichier", 0x1000)
        else:
            # instanciation d'une variable pour le stockage du fichier sélectionné
            path = self.ids.inputFile.text
            # Contrôle de l'extension du fichier sélectionné même si l'explorateur de fichier utilisé à des filtres sur les extensions sélectionnables.
            fileExtension = os.path.splitext(path)[-1]
            if not fileExtension == ".csv" and not fileExtension == ".xls" and not fileExtension == ".xlsx" and not fileExtension == ".xlsm":
                # Si extension non conforme, application du code couleur erreur et notification à l'utilisateur
                self.ids.scriptGrid.color = errorColor
                ctypes.windll.user32.MessageBoxW(0, "Extension de fichier %s non pris en charge" % fileExtension,
                                                 "Erreur d'extension", 0x1000)
                self.sourceFileIsValid = False
            # Contrôle si le path du fichier renseigné existe bien
            if not exists(path):
                # Si inexistant, application du code couleur erreur et notification à l'utilisateur
                self.ids.scriptGrid.color = errorColor
                ctypes.windll.user32.MessageBoxW(0, "Le chemin de la ressource est incorrect", "Erreur", 0x1000)
                self.sourceFileIsValid = False
            else:
                self.ids.scriptGrid.color = validColor
                self.sourceFileIsValid = True
        # Contrôle de tous les boolean pour la validation des inputs de l'utilisateur
        if self.dateIsValid and self.timeIsValid and self.nameProgIsValid and self.sourceFileIsValid:
            # chemin pour la création du fichier script de la programmation
            path = f'{os.getcwd()}\\Planification\\'
            if not exists(path):
                ctypes.windll.user32.MessageBoxW(0,
                                                 "Le répertoire Planification n'est pas présent dans le répertoire de ODIM.\n"
                                                 "Veuillez le recréer ou procéder à une nouvelle installation",
                                                 "Erreur", 0x1000)
                return
            try:
                path = f'{os.getcwd()}\\Planification\\' + self.ids.inputProgName.text + '.bat'

                with open(path, "w") as file:
                    file.write(os.getcwd() + "\ODIM.exe " + self.ids.inputFile.text)
                    file.close()
                # Création d'une date d'expiration pour le déclencheur de la tâche windows pour l'exécution du fichier script.
                # 1m est ajouté
                deltaDate = selectedDateTime + timedelta(minutes=1)
                dateExpire = deltaDate.strftime("%Y-%m-%dT%H:%M:%S")
                # commande powershell pour la création d'une tâche dans le planificateur de tâche windows.
                STR_CMD2 = f'''
                    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "{path}"
                    $settings = New-ScheduledTaskSettingsSet -DeleteExpiredTaskAfter (New-TimeSpan -Seconds 2)
                    $taskName = "{self.ids.inputProgName.text}"
                    $description = "Nouvelle tâche programmé par ODIM"
                    $trigger = New-ScheduledTaskTrigger -Once -At "{self.selectedDate.strftime("%m/%d/%Y")} {str(self.selectedTime)}"
                    $trigger.EndBoundary = "{dateExpire}"
                    Register-ScheduledTask -TaskName $taskName -Description $description -Action $action -Settings $settings -Trigger $trigger | Out-Null
                    '''
                # liste pour concaténer les arguments de la commande à exécuter
                listProcess = [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    STR_CMD2
                ]
                # execution de la commande
                subprocess.run(listProcess, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Log de l'inscription au planificateur de tâche et notification utilisateur
                logger.info("Inscription au planificateur de tâches du script " + self.ids.inputProgName.text + ".bat")
                ctypes.windll.user32.MessageBoxW(0,
                                                 "Inscription au planificateur de tâches du script " + self.ids.inputProgName.text + ".bat",
                                                 "Information", 0x1000)
                # Reset des champs d'input à vide.
                self.ids.inputFile.text = self.ids.inputTime.text = self.ids.inputDate.text = self.ids.inputProgName.text = ''
                # Reset des booleans de contrôle à False
                self.dateIsValid = self.timeIsValid = self.nameProgIsValid = self.sourceFileIsValid = False
            except Exception as error:
                if isinstance(error, TypeError):
                    logger.error("Erreur dans la syntaxe de la commande pour la création d'une programmation")
                    ctypes.windll.user32.MessageBoxW(0, "La syntaxe des éléments renseignés n'est pas conforme",
                                                     "Erreur", 0x1000)
                if isinstance(error, subprocess.CalledProcessError):
                    logger.error(
                        "Les éléments renseignés ne permettent pas la création d'une programmation dans le "
                        "planificateur de tâches.")
                    ctypes.windll.user32.MessageBoxW(0,
                                                     "Les éléments renseignés ne permettent pas la création d'une programmation dans le planificateur de tâches.\n"
                                                     "Vérifiez notamment qu'une tâche n'existe pas déjà sous le nom renseigné.",
                                                     "Erreur", 0x1000)
                else:
                    logger.error(str(error.__class__) + " : " + str(error))


# Classe de l'écran principal contenu tous les composants graphiques pour l'utilisateur
class LoginScreen(Screen):
    # image d'arrière plan UI
    image_source = StringProperty()
    # variable de classe pour stocker la session WP/Telegram courante ainsi que le fichier d'envoi de message
    currentSession = fileToSend = ''
    # variable de classe pour stocker le nombre de messages en succès et en échec ainsi qu'une variable indice pour suivre le nombre de messages envoyés.
    indice = FailedCount = OtherCount = SuccessCount = 0
    # Boolean pour indiquer si un nouveau rapport est générable afin de ne générer de rapport identique à la suite si aucun envoi n'a été effectué depuis le dernier rapport.
    newRapportAvailable = False

    # Constructeur
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.image_source = resource_path(r'Images/4882066.jpg')

    # Méthode de déclenchement du BOT pour lancer le processus d'envoi de message
    def runBOT(self):
        saveConfiguration(self)
        # Reset des champs d'affichage du nombre de messages en succès ou échec à l'issue d'un envoi
        resetSuccessFailedCountLabel(self)
        # Contrôle si la sélection est vide
        if self.fileToSend == '':
            ctypes.windll.user32.MessageBoxW(0, "Aucun fichier sélectionné", "Erreur", 0x1000)
        # contrôle de l'extension du fichier importé.
        elif os.path.splitext(self.fileToSend)[-1] == ".csv":
            # déclenchement de l'envoi
            threading.Thread(target=startSend, args=(self.fileToSend, self)).start()
        else:
            logger.error("Fichier importé ou extension non conforme ")
            ctypes.windll.user32.MessageBoxW(0, "Extension du fichier non conforme", "Erreur", 0x1000)

    # appel vers la méthode de sauvegarde de la configuration utilisateur
    def saveConfiguration(self):
        saveConfiguration(self)

    # Explorateur windows pour importer le fichier d'envoi de message
    def openExplorer(self):
        try:
            Tk().withdraw()  # Suppression de l'interface principale qui s'affiche par default dès l'exécution d'un composant Tkinter
            LoginScreen.fileToSend = self.fileToSend = askopenfilename(title="Sélectionner le fichier csv à importer :",
                                                                       filetypes=[("Fichier csv", "*.csv")])
            # Affectation du fichier importé au composant dédié dans l'interface afin d'afficher le nom du fichier à l'utilisateur.
            self.ids.fileImportedLabel.text = self.fileToSend
            logger.info("Import fichier Destinataire / Fichier importé  : %s " % self.fileToSend)
        except IndexError:
            # Fermeture par l'utilisateur de la fenêtre de sélection du fichier source
            # Reset de la variable de classe et de la variable d'instance à un champ vide
            LoginScreen.fileToSend = self.fileToSend = ""
            # Reset du champ d'affichage du fichier importé à un champ vide
            self.ids.fileImportedLabel.text = ""

    # Extraction du nom des contacts de toutes les conversations existantes dans une session WhatsApp
    def extractContacts(self):
        # instanciation de la session dans laquelle exporter les contacts
        sessionToExtract = getSession(self)
        contacts = dict()
        # dictionnaire contenant les contacts ayant pu être exportés
        contacts["contacts"] = sessionToExtract.extract_contacts()
        # chemin vers le répertoire de stockage de l'extraction
        extractToPath = './Export/Contacts/'
        # si le chemin n'existe pas, création du répertoire
        if not os.path.exists(extractToPath):
            ctypes.windll.user32.MessageBoxW(0,
                                             "Le répertoire Contacts n'est pas présent dans le répertoire de ODIM.\n"
                                             "Veuillez le recréer ou procéder à une nouvelle installation",
                                             "Erreur", 0x1000)
            return
        try:
            with open(f'{extractToPath}/contacts.csv', 'w') as file:
                # écriture du contenu du fichier
                for num in contacts["contacts"]:
                    file.write(num+"\n")
                # file.write("\n".join([",".join([str(item) if item else "" for item in t]) for t in
                #                       zip_longest(*[[group] + contacts[group] for group in contacts.keys()])]))
                file.close()
                ctypes.windll.user32.MessageBoxW(0, f"Extraction des contacts vers le fichier contact.csv", "Confirmation", 0x1000)

                logger.info("L'extraction de contacts est terminée")
        except Exception as error:
            ctypes.windll.user32.MessageBoxW(0, "une erreur s'est produite lors de l'extraction des conversations.\n"
                                                "Pour plus de détail consultez les fichiers de log.", "Erreur", 0x1000)

            logger.error("Extraction de contacts : " + str(error))


# Ecran pour la gestion de l'affichage du rapport suite à un envoi.
def exportRapportToCSV(isScheduled=None):
    global statusDict
    try:
        # chemin vers le repertoire d'export du rapport
        if isScheduled is None:
            path = f'{os.getcwd()}\\Export\\Rapports\\'
        else:
            exeFilePath = sys.executable.split("\\ODIM.exe")[0]
            path = f'{exeFilePath}\\Export\\Rapports\\'
        # nommage du fichier de rapport avec le gdh de génération de l'export.
        fileName = ("rapport_%s_%s.csv" % (datetime.now().date(), datetime.now().strftime("%H-%M-%S")))
        # création du répertoire Rapports s'il n'existe pas
        if not exists(path):
            ctypes.windll.user32.MessageBoxW(0,
                                             "Le répertoire Rapports n'est pas présent dans le répertoire de ODIM.\n"
                                             "Veuillez le recréer ou procéder à une nouvelle installation",
                                             "Erreur", 0x1000)
            return
        # sauvegarde de fichier avec les configurations
        with open(path + fileName, 'w') as file:
            # Pour chaque statut de message dans le dictionnaire écriture d'une ligne dans le fichier csv
            for value in statusDict.values():
                valueToCSV = ""
                for text in value:
                    # statusDict est sous le format : numero, contenu, status, information
                    # ajout de ces quatres valeurs dans le tableau pour créer une ligne au format csv.
                    valueToCSV += text + ";"
                # fin du parcours des valeurs, écriture du fichier de rapport
                file.write(valueToCSV + "\n")
        ctypes.windll.user32.MessageBoxW(0, "Le fichier csv de rapport a été créé.", "Confirmation", 0x1000)
        logger.info("Export du fichier csv de rapport " + str(file.name))
        file.close()
    except UnboundLocalError as error:
        logger.error(error)
    except NameError as error:
        logger.error(error)


class RapportScreen(Screen):
    # image d'arrière plan de l'interface
    image_source = StringProperty()

    def __init__(self, **kwargs):
        super(RapportScreen, self).__init__(**kwargs)
        self.image_source = resource_path(r'Images/4882066.jpg')

    # Export du contenu de la table du rapport vers un fichier CSV
    def exportRapportToCSV(self):
        exportRapportToCSV()


# Méthode qui renvoie une liste de numéro de téléphone à partir d'un fichier en entré csv/xls/txt contenant un numéro par ligne.
def extractListFromFile(sourceFile):
    contactsList = list()
    if sourceFile == '':
        ctypes.windll.user32.MessageBoxW(0, "Aucun fichier importé", "Erreur", 0x1000)
    else:
        # gestion d'un fichier en entré CSV
        if (os.path.splitext(sourceFile)[-1]) == ".csv":
            file = open(sourceFile)
            # Lecture du fichier CSV
            csvreader = csv.reader(file)
            for row in csvreader:
                contactsList.append(row[0])
        else:
            ctypes.windll.user32.MessageBoxW(0, "Fichier ou extension de fichier non pris en charge", "Erreur", 0x1000)
    if len(contactsList) > 0:
        return contactsList


# Class pour l'écran de génération d'un fichier VCF
# Un fichier VCF est un fichier de contact parsable nativement par un téléphone android. Possible également sur IOS
class GenerateContactScreen(Screen):
    image_source = StringProperty()

    # Constructeur
    def __init__(self, **kwargs):
        super(GenerateContactScreen, self).__init__(**kwargs)
        self.generationList = None
        self.sourceFile = ''
        self.image_source = resource_path(r'Images/4882066.jpg')

    # Méthode de génération d'un fichier VCF suite à l'import de fichier de numéro source
    def generateFile(self):
        # Gestion de l'extension du fichier importé pour pouvoir le parser par la suite
        self.generationList = extractListFromFile(self.sourceFile)
        # Nouveau contrôle si le fichier est null ou si la taille de la list permet une génération de fichier CSV
        if self.generationList is not None and len(self.generationList) > 0:
            # Création du fichier VCF
            generateContact.CreateVCFFile(self.generationList)

    # Méthode pour l'affichage d'une fenêtre Windows explorer pour la sélection d'un fichier de numéro source
    def open_explorer(self):
        try:
            Tk().withdraw()  # Suppression de l'interface principale qui s'affiche par default dès l'exécution d'un composant Tkinter
            self.sourceFile = askopenfilename(title="Sélectionner le fichier csv à importer :",
                                              filetypes=[("Fichier csv",
                                                          "*.csv")])  # show an "Open" dialog box and return the path to the selected file

            if self.sourceFile != "":
                self.ids.inputSourceFile.text = self.sourceFile
        except IndexError:
            self.ids.inputSourceFile.text = self.sourceFile = ""


# Class pour l'écran de détection des réseaux sociaux pour chaque numéro
class DetectionScreen(Screen):
    image_source = StringProperty()

    # Constructeur
    def __init__(self, **kwargs):
        super(DetectionScreen, self).__init__(**kwargs)
        self.detectionList = None
        self.sourceFile = ''
        self.image_source = resource_path(r'Images/4882066.jpg')

    # Méthode de détection
    def detectFile(self):
        # Gestion de l'extension du fichier importé pour pouvoir le parser par la suite
        self.detectionList = extractListFromFile(self.sourceFile)
        # Nouveau contrôle si le fichier est null ou si la taille de la list permet une génération de fichier CSV
        if self.detectionList is not None and len(self.detectionList) > 0:
            # Création des fichiers csv
            socialNetworkCounts = detectSocialNetwork.create_social_network_files(self.detectionList)

        # Définition des labels pour les données et des couleurs associés aux labels
        labels = ['WhatsApp : %s' % str(socialNetworkCounts[0]), 'Telegram : %s' % str(socialNetworkCounts[1])]
        colors = ["#99ff99", "#7fefbd"]
        # Création des variables pour le graphique
        x = [socialNetworkCounts[0], socialNetworkCounts[1]]
        fig = pyplot.figure()
        fig.patch.set_facecolor((0, 0, 1, 0))
        # instanciation du graphique avec les variables définies
        pyplot.pie(x=x,
                   colors=colors,
                   labels=labels,
                   textprops={'color': "w"})
        # affectation du camembert dans son container
        graphSocialNetwork = self.ids.graphSocialNetwork
        # récupération de tous les composants enfant du conteneur
        rows = [i for i in graphSocialNetwork.children]
        for row1 in rows:
            # suppression des enfants
            graphSocialNetwork.remove_widget(row1)
        # ajout du nouveau graphique
        graphSocialNetwork.add_widget(FigureCanvasKivyAgg(pyplot.gcf()))

    # Méthode pour l'affichage d'une fenêtre Windows explorer pour la sélection d'un fichier de numéro source
    def open_explorer(self):
        try:
            Tk().withdraw()  # Suppression de l'interface principale qui s'affiche par default dès l'exécution d'un composant Tkinter
            self.sourceFile = askopenfilename(title="Sélectionner le fichier csv à importer :",
                                              filetypes=[("Fichier csv",
                                                          "*.csv")])  # show an "Open" dialog box and return the path to the selected file
            if self.sourceFile != "":
                self.ids.inputFile.text = self.sourceFile
        except IndexError:
            self.ids.inputFile.text = self.sourceFile = ""


# Class pour l'écran de retweet et like
class RetweetScreen(Screen):
    image_source = StringProperty()
    selectedDate = None

    # Constructeur
    def __init__(self, **kwargs):
        super(RetweetScreen, self).__init__(**kwargs)
        self.usersList = []
        self.sourceFileTweet = ''
        self.sourceFileRetweet = ''
        self.image_source = resource_path(r'Images/4882066.jpg')

    # Méthode pour l'affichage d'une fenêtre Windows explorer pour la sélection d'un fichier de numéro source
    def open_explorer_tweet(self):
        try:
            Tk().withdraw()  # Suppression de l'interface principale qui s'affiche par default dès l'exécution d'un composant Tkinter
            self.sourceFileTweet = askopenfilename(title="Sélectionner le fichier csv à importer :",
                                                   filetypes=[("Fichier csv",
                                                               "*.csv")])  # show an "Open" dialog box and return the path to the selected file
            if self.sourceFileTweet != "":
                self.ids.inputFileTweet.text = self.sourceFileTweet
        except IndexError:
            self.ids.inputFileTweet.text = self.sourceFileTweet = ""

        # Méthode pour l'affichage d'une fenêtre Windows explorer pour la sélection d'un fichier de numéro source

    def open_explorer_retweet(self):
        try:
            Tk().withdraw()  # Suppression de l'interface principale qui s'affiche par default dès l'exécution d'un composant Tkinter
            self.sourceFileRetweet = askopenfilename(title="Sélectionner le fichier csv à importer :",
                                                     filetypes=[("Fichier csv",
                                                                 "*.csv")])  # show an "Open" dialog box and return the path to the selected file
            if self.sourceFileRetweet != "":
                self.ids.inputFileRetweet.text = self.sourceFileRetweet
        except IndexError:
            self.ids.inputFile.text = self.sourceFileRetweet = ""

    # Méthode de retweet et like
    def retweetAndLike(self):
        # Retweet, like et récupération des utilisateurs
        self.usersList = generate_retweet_like(self.sourceFileTweet, self.sourceFileRetweet, self.selectedDate)
        if (len(self.usersList) != 0):
            tweetsFoundCount = 0
            tweetsNotFoundCount = 0
            for user in self.usersList:
                if (len(user.tweetsList) == 0):
                    tweetsNotFoundCount += 1
                else:
                    tweetsFoundCount += 1

            # Définition des labels pour les données et des couleurs associés aux labels
            labels = ['Tweeters trouvés : %s' % str(tweetsFoundCount),
                      'Tweeters non trouvés : %s' % str(tweetsNotFoundCount)]
            colors = ["#99ff99", "#d2042d"]
            # Création des variables pour le graphique
            x = [tweetsFoundCount, tweetsNotFoundCount]
            fig = pyplot.figure()
            fig.patch.set_facecolor((0, 0, 1, 0))
            # instanciation du graphique avec les variables définies
            pyplot.pie(x=x,
                       colors=colors,
                       labels=labels,
                       textprops={'color': "w"})
            # affectation du camembert dans son container
            graphRetweetLike = self.ids.graphRetweetLike
            # récupération de tous les composants enfant du conteneur
            rows = [i for i in graphRetweetLike.children]
            for row1 in rows:
                # suppression des enfants
                graphRetweetLike.remove_widget(row1)
            # ajout du nouveau graphique
            graphRetweetLike.add_widget(FigureCanvasKivyAgg(pyplot.gcf()))

    # Création et affichage du composant datePicker
    def show_date_picker(self):
        # Instanciation du DatePicker
        date_dialog = MDDatePicker()
        # Application thème Dark
        date_dialog.theme_cls.theme_style = "Dark"
        # Binding des méthodes de sauvegarde et d'annulation du datePicker avec les méthodes déclarées ci-dessus
        date_dialog.bind(on_save=self.on_saveDate, on_cancel=self.on_cancelDate)
        date_dialog.open()

    # Sauvegarde de la date sélectionnée dans le calendrier par l'utilisateur
    def on_saveDate(self, instance, value, date_range):
        self.selectedDate = value
        self.ids.inputDateRetweet.text = str(value)

    # Gestion d'annulation de la sélection par l'utilisateur
    def on_cancelDate(self, instance, value):
        self.ids.inputDateRetweet.text = ""

    # Méthode pour fermer l'application au clique sur la croix rouge native à la fenêtre windows.


def end_func(self):
    MyApp.stop(MyApp.get_running_app())
    Window.close()
    logger.info("Fermeture de ODIM par l'utilisateur")


# Méthode pour focus la fenêtre principale quand le curseur passe dessus afin d'éviter d'avoir un clique obligatoire pour focus la fenêtre.
def window_callback(self):
    if not Window.focus:
        Window.raise_window()


# Class principal du fichier MyApp.kv
class MainScreen(BoxLayout):
    # Constructeur
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        # binding pour capter l'évènement de fermeture de la fenêtre principale par l'utilisateur
        Window.bind(on_request_close=end_func)
        Window.bind(on_cursor_enter=window_callback)
        # chargement de la configuration sauvegardée par l'utilisateur
        loadConfiguration(self)
        # si le composant délai est vide, forçage à 1 obligatoirement car c'est le délai minimum
        if self.ids.manager.ids.login.ids.inputDelai.text == "":
            self.ids.manager.ids.login.ids.inputDelai.text = "1"

    # Création du graphic pour présenter les résultats de l'envoi
    def updateGraphic(self):
        try:
            # si le boolean est à faux, soit aucun envoi n'a été fait, soit aucun envoi n'a été fait depuis le dernier rapport.
            if LoginScreen.newRapportAvailable:
                # Définition des labels pour les données et des couleurs associés aux labels
                labels = ['Succès : %s' % str(LoginScreen.SuccessCount), 'Échec : %s' % str(LoginScreen.FailedCount),
                          'Autre : %s' % str(LoginScreen.OtherCount)]
                colors = ["#99ff99", "#ff6666", "#ffa85a"]
                # Création des variables pour le graphique
                x = [LoginScreen.SuccessCount, LoginScreen.FailedCount, LoginScreen.OtherCount]
                fig = pyplot.figure()
                fig.patch.set_facecolor((0, 0, 1, 0))
                # instanciation du graphique avec les variables définies
                pyplot.pie(x=x,
                           colors=colors,
                           labels=labels,
                           textprops={'color': "w"})
                # affectation du camembert dans son container
                chartbox = self.ids.manager.ids.rapport.ids.chartBox
                # récupération de tous les composants enfant du conteneur
                rows = [i for i in chartbox.children]
                for row1 in rows:
                    # suppression des enfants
                    chartbox.remove_widget(row1)
                # ajout du nouveau graphique
                chartbox.add_widget(FigureCanvasKivyAgg(pyplot.gcf()))
                # Boolean pour nouveau rapport à False
                LoginScreen.newRapportAvailable = False
            else:
                pass
        except NameError:
            pass
        except FileNotFoundError:
            pass


# Méthode de déclenchement de l'envoi de message via une programmation dans le planificateur de tâches.
def startSendScheduled(scheduledFile=None):
    global statusDict
    # Chargement de la configuration que l'utilisateur a sauvegardé.
    loadScheduledConfiguration()
    # Dictionnaire qui va stocker le retour commande de chaque envoi
    statusDict = dict()
    # Remise à zéro des entiers pour le suivant du nombre de messages envoyé et pour le suivi du nombre de succès ou d'échec.
    LoginScreen.indice = LoginScreen.SuccessCount = LoginScreen.FailedCount = LoginScreen.OtherCount = Configuration.packetCurrentSize = 0
    fileExtension = os.path.splitext(scheduledFile)[-1]

    # instanciation de la session whatsapp/telegram pour qui va servir à envoyer les messages
    if Configuration.sendByWhatsApp:
        LoginScreen.currentSession = WhatsApp(60, session=Configuration.savedSession)
    else:
        LoginScreen.currentSession = Telegram(60, session=Configuration.savedSession)

    # gestion de l'envoi en fonction de l'extension du fichier chargé
    if fileExtension == ".csv":
        handleCSVFileMessages(None, scheduledFile)

    # calcul du nombre de messages en succès et en échec
    for value in statusDict.values():
        if str(value).__contains__("Envoyé"):
            LoginScreen.SuccessCount += 1
        elif str(value).__contains__("Autre"):
            LoginScreen.OtherCount += 1
        else:
            LoginScreen.FailedCount += 1

    # fermeture de la session en cours.
    try:
        LoginScreen.currentSession.quit()
    except AttributeError as a:
        pass
    # export automatique suite à la fin de l'envoi afin de fournir un élément de retex à l'utilisateur
    exportRapportToCSV(isScheduled=True)
    logger.info("Fermeture de l'application")


class MyApp(MDApp):
    def build(self):
        self.title = "ODIM - 2.0.0"
        self.icon = resource_path(r'Images/bomb.png')
        return MainScreen()


# Main
if __name__ == '__main__':
    LoginScreen.fileToSend = ""
    # Gestion d'une exécution sous cmd via la programmation
    if len(sys.argv) > 1:
        # Lancement du bot de programmation
        startSendScheduled(scheduledFile=sys.argv[1])
    else:
        # gestion du chromedriver dans le module service.py
        # le chromedriver est à placer à côté du script
        logger.info("Lancement de ODIM")
        MyApp().run()
