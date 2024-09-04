#define appName "ODIM"
#define appVersion "2.0.0"
#define exePath "..\source\ODIM.exe"
#define exeName "ODIM.exe"

[Setup]
AppName={#appName}
AppVersion={#appVersion}
WizardStyle=modern
DefaultDirName={autopf}\ODIM
DefaultGroupName=ODIM
;Désactivation de l'option pour ne demander qu'une fois le chemin d'installation de l'exécutable
DisableDirPage=no
;Nom du setup 
OutputBaseFilename="ODIM_2.0.0_Setup"
Compression=lzma2
SolidCompression=yes
;répertoire de génération du Setup
OutputDir=..\output
PrivilegesRequired = admin
SetupIconFile=C:\Users\Adm-7C\Desktop\Setup\source\bombSetup.ico

;Language de la fenêtre d'installation
[Languages]
Name:"french";MessagesFile:"compiler:Languages\French.isl"

[Tasks]
;Demande à l'utilisateur d'une création d'une icône sur le bureau 
Name:"desktopicon";Description:"{cm:CreateDesktopIcon}";GroupDescription: "{cm:AdditionalIcons}";Flags:unchecked

[Dirs]
Name:"{app}\Configuration"
Name:"{app}\Export\Rapports"
Name:"{app}\Export\Contacts"
Name:"{app}\Extraction"
Name:"{app}\LOG"
Name:"{app}\Programmation"
Name:"{app}\VCF"


[Files]
; copie de l'exe de python vers le sous répertoire pythonInstaller
Source: "..\source\python-3.9.13-amd64.exe"; DestDir: "{app}\pythonInstaller"
; copie de l'exe de Chrome vers le sous répertoire ChromeInstaller
Source: "..\source\ChromeSetup.exe"; DestDir: "{app}\ChromeInstaller"
; copie du fichier d'élément web de WhatsApp vers le sous répertoire Configuration
Source: "..\source\whatsappelements.txt"; DestDir: "{app}\Configuration"
; copie du fichier d'élément web de Twitter vers le sous répertoire ChromeInstaller
Source: "..\source\twitterelements.txt"; DestDir: "{app}\Configuration"
; copie du fichier d'élément web de Telegram vers le sous répertoire ChromeInstaller
Source: "..\source\telegramelements.txt"; DestDir: "{app}\Configuration"
; copie de l'exe de FFMPEG dans le répertoire de l'application
Source: "..\source\FFMPEG\*"; DestDir: "{app}\FFMPEG"; Flags:recursesubdirs
; copie de l'exe de chromedriver dans le répertoire de l'application
Source: "..\source\chromedriver.exe"; DestDir: "{app}\Chromedriver"; Flags:recursesubdirs
; copie de l'exe de ODIM dans le répertoire de l'application
Source: "{#exePath}"; DestDir: "{app}"; AfterInstall:InstallExe

[Icons]
Name: "{commondesktop}\{#appName}"; Filename: "{app}\{#exeName}"


[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\FFMPEG\bin"; \
    Check: NeedsAddPath('{app}\FFMPEG\bin')
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Chromedriver"; ValueData: "{app}\Chromedriver\chromedriver.exe"; \
    Check: NeedsAddPath('{app}\Chromedriver\chromedriver.exe')	

[Code]
{Méthode pour lancer l'installation de python et de Chrome}
procedure InstallExe();

var 
  ResultCode:Integer;
begin
     {Installation de python}
     ShellExec('runas',ExpandConstant('{app}\pythonInstaller\python-3.9.13-amd64.exe'),'','',SW_SHOW,ewWaitUntilTerminated, ResultCode);
     {Installation du navigateur Chrome}
     ShellExec('runas',ExpandConstant('{app}\ChromeInstaller\ChromeSetup.exe'),'','',SW_SHOW,ewWaitUntilTerminated, ResultCode);
end;


function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  { look for the path with leading and trailing semicolon }
  { Pos() returns 0 if not found }
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;


