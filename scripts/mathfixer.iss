#ifndef MyAppVersion
  #define MyAppVersion "2.0.7"
#endif

[Setup]
AppId={{B15E90A8-6EE3-4C9B-A4E6-5085D0C3A75E}
AppName=MathFixer
AppVersion={#MyAppVersion}
AppPublisher=MathFixer contributors
AppPublisherURL=https://github.com/MahdiMazinani/MathFixer
DefaultDirName={autopf}\MathFixer
DefaultGroupName=MathFixer
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=MathFixer-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MathFixer.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\MathFixer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README_FA.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\BEGINNER_GUIDE.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\BEGINNER_GUIDE_FA.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\guide-en.css"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\guide-fa.css"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\examples\*"; DestDir: "{app}\examples"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MathFixer"; Filename: "{app}\MathFixer.exe"
Name: "{autodesktop}\MathFixer"; Filename: "{app}\MathFixer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\MathFixer.exe"; Description: "Launch MathFixer"; Flags: nowait postinstall skipifsilent
