projet développé sous python 3.9.x

génération du fichier éxécutable ODIM.exe : "pyinstaller.exe --onedir .\MyApp.spec"

IMPERATIF : 
- ne pas générer l'exe via la commande  "pyinstaller.exe --onedir .\MyApp.py" car overwrite le fichier .\MyApp.spec contenant les chemins vers ressources locales en configuration de l'exe
- mettre à jour le fichier .\MyApp.spec avant lancement de la commande
- ajouter le répertoire FFMPEG à la variable Path du host pour la gestion des médias dans WhatsApp


script innosetup pour la génération du setup d'installation sous "C:\Users\Utilisateur\Documents\Source\ODIM_WhatsApp\Setup\script"
