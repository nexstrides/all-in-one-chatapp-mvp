#ifndef AppVersion
  #define AppVersion "0.1.2"
#endif

[Setup]
AppId={{7121AD0F-7AAC-472D-9D19-C77A360971E9}
AppName=All in One Chatapp
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\AllInOneChatapp
DefaultGroupName=All in One Chatapp
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=AllInOneChatapp-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Files]
Source: "..\dist\AllInOneChatapp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\All in One Chatapp"; Filename: "{app}\AllInOneChatapp.exe"
Name: "{autodesktop}\All in One Chatapp"; Filename: "{app}\AllInOneChatapp.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "AllInOneChatapp"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\AllInOneChatapp.exe"; Description: "Open All in One Chatapp"; Flags: nowait postinstall skipifsilent

