; Inno Setup script for WH Pallet Printer.

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName       "WH Pallet Printer"
#define MyAppPublisher  "BGA"
#define MyAppExeName    "WHPalletPrinter.exe"
#define MyAppIcon       "..\assets\icon.ico"

[Setup]
SetupIconFile={#MyAppIcon}
AppId={{A4C8E2B1-7F3D-4A9C-B6E1-2D8F5C9A4E73}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
OutputDir=Output
OutputBaseFilename=WHPalletPrinter-Setup-{#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\MicrosoftEdgeWebView2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "vendor\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; \
    Parameters: "/install /quiet /norestart"; \
    StatusMsg: "Installing VC++ 2015-2022 Redistributable..."; \
    Check: NeedVCRedist; \
    Flags: waituntilterminated

Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; \
    Parameters: "/silent /install"; \
    StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; \
    Check: NeedWebView2; \
    Flags: waituntilterminated

Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName} now"; \
    Flags: nowait postinstall skipifsilent

[Code]
function NeedWebView2: Boolean;
var
  Version: string;
begin
  Result := True;
  if RegQueryStringValue(HKLM,
       'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
       'pv', Version) then
    if (Version <> '') and (Version <> '0.0.0.0') then
      Result := False;
  if Result and RegQueryStringValue(HKCU,
       'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
       'pv', Version) then
    if (Version <> '') and (Version <> '0.0.0.0') then
      Result := False;
end;

function NeedVCRedist: Boolean;
var
  Installed: Cardinal;
begin
  Result := True;
  if RegQueryDWordValue(HKLM,
       'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
       'Installed', Installed) then
    if Installed = 1 then
      Result := False;
end;
