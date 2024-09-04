import ctypes
import os

"""
Module avec une méthode permettant la création d'un fichier d'extension VCF à partir de fichier source de numéro de téléphone.
Un fichier VCF est un fichier permettant la création de contact en l'important dans un téléphone.
"""
def CreateVCFFile(sourceList):
    current_dir = os.getcwd()
    make_vcard = lambda number: f"BEGIN:VCARD TEL;TYPE=HOME:{number}\nEND:VCARD"
    # Lit le contenu du fichier VCARD
    numbers = ["+ " + x.strip().replace("'", "").replace("+", "") for x in sourceList if x and x.strip()]  # Supprimes les lignes vides et ajoute '+' si non présent
    # Supprime les doublons
    numbers = list(set(numbers))

    # Parcours les numéros et créer les fiches contacts
    vcard = []
    for number in numbers:
        vcard.append(make_vcard(number))

    path = f"{current_dir}/Export/VCF"
    if not os.path.exists(path):
        ctypes.windll.user32.MessageBoxW(0,
                                         "Le répertoire VCF n'est pas présent dans le répertoire de ODIM.\n"
                                         "Veuillez le recréer ou procéder à une nouvelle installation",
                                         "Erreur")
        return

    with open(f"{current_dir}/Export/VCF/contact.vcf", "w") as fos:
        fos.write("\n".join(vcard))

    ctypes.windll.user32.MessageBoxW(0, f"Script terminé : {len(numbers)} contacts uniques ont été exportés dans le fichier 'contact.vcf'", "Succès")


