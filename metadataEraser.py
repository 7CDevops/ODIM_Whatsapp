import logging
import os
import random
import string
import ffmpeg
from pydub import AudioSegment
import exif_delete

logger = logging.getLogger()

repertoire_travail = "_testEraseMetadata"
longueur_nom_fichier = 20
imageExtensions = ['.jpeg', '.jpg', '.JPEG', '.JPG', '.png', '.PNG']
videoExtensions = [".mp4", ".MP4", ".wmv", ".WMV", ".avi", ".AVI", ".mov", ".MOV"]
audioExtensions = [".wav", ".WAV", ".mp3", ".MP3"]
angle_rotation_max = 0.5  # 1 → entre -1 et 1 degré
randomSilenceDuration = [1000, 2000,
                         3000]  # tableau pour définir la durée du silence ajouté à un fichier audio : 1s / 2s / 3s

"""
Vérification si la ressource existe bien sous le chemin renseigné, si OK effacement des métadonnées
"""


def CheckPathAndErase(path):
    # Si la ressource existe effacement des métadonnées, si la ressource est un dossier, pour tous les fichiers les métadonnées sont effacées.
    if os.path.isfile(path):
        return eraseMetadata(path)
    elif os.path.isdir(path):
        for file in os.listdir(path):
            return eraseMetadata(file)


"""
Méthode pour la génération d'un nom aléatoire pour un fichier en entré
"""


def getRandomName():
    return ''.join \
        (random.choice(string.ascii_letters + string.digits) for _ in range(longueur_nom_fichier))


"""
Méthode pour supprimer les métadonnées d'un fichier image afin de ne laisser fuiter aucune information sur WhatsApp ou Telegram
"""


def eraseMetadata(file):
    file_extension = os.path.splitext(file)[-1]

    #  GESTION DES FICHIERS IMAGE
    if file_extension in imageExtensions:  # Si l'extension du fichier figure parmis celles acceptées
        # Calcul un nouveau nom
        final_name = f'{os.path.dirname(file)}\{getRandomName()}{file_extension}'
        exif_delete.exif_delete(file, final_name)
        return os.path.join(os.path.dirname(file), final_name)

    #  GESTION DES FICHIERS VIDEO
    elif file_extension in videoExtensions:
        try:
            # Nouveau nom de fichier.
            fileName = f'{getRandomName()}{file_extension}'
            # Testé et fonctionne avec les extensions wmv / avi / mov / mp4
            (
                ffmpeg
                .input(file)
                .output(os.path.join(os.path.dirname(file), fileName), metadata="title=")
                .run(overwrite_output=True)
            )
            # return du chemin du nouveau fichier démarqué en donnée pour pouvoir l'envoyer
            return os.path.join(os.path.dirname(file), fileName)
        except Exception as e:
            logger.error(e)

    #  GESTION DES FICHIERS AUDIO
    elif file_extension in audioExtensions:
        try:
            # Nouveau nom
            fileName = f'{getRandomName()}{file_extension}'
            # Flux entrant
            soundData = AudioSegment.from_file(file)
            # Random bool afin de déterminer au hasard si l'ajout du silence se faire au début ou à la fin du fichier audio
            if bool(random.getrandbits(1)):
                # Concaténation du fichier audio d'origine avec un silence d'une durée aléatoire pioché parmis trois durées possible déterminée dans un tableau
                audio = soundData + AudioSegment.silent(randomSilenceDuration[random.randint(0, 2)])
            else:
                audio = AudioSegment.silent(randomSilenceDuration[random.randint(0, 2)]) + soundData
            audio.export(os.path.join(os.path.dirname(file), fileName), format=file_extension.replace(".", ""))
            # return du chemin du nouveau fichier démarqué en donnée pour pouvoir l'envoyer
            return os.path.join(os.path.dirname(file), fileName)
        except Exception as e:
            logger.error(e)
    else:
        logging.error("extension non prise en charge")
