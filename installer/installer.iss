; 滴鱼简历助手 XG Resume Studio —— 安装包脚本（Inno Setup 6）
; 用法：ISCC.exe installer\installer.iss /DMyAppVersion=1.1.0 /O"dist-installer"
; 前提：已用 PyInstaller 生成 dist\滴鱼简历助手\

#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif

#define MyAppName "滴鱼简历助手"
#define MyAppFullName "滴鱼简历助手 XG Resume Studio"
#define MyAppExeName "滴鱼简历助手.exe"

[Setup]
; 脚本在 installer/ 下，源码路径基于仓库根目录
SourceDir=..
AppId={{8F3B0A2E-3D6C-4E9B-A5C1-2E7D9F0A1B3C}
AppName={#MyAppFullName}
AppVersion={#MyAppVersion}
AppPublisher=Wolfentsz
AppPublisherURL=https://github.com/MapleLloyd/xg-resume-studio
AppSupportURL=https://github.com/MapleLloyd/xg-resume-studio
AppUpdatesURL=https://github.com/MapleLloyd/xg-resume-studio
DefaultDirName={localappdata}\Programs\滴鱼简历助手
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=XG-Resume-Studio-{#MyAppVersion}-setup
OutputDir=dist-installer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
; 安装到用户目录，无需管理员权限，程序旁的 data 文件夹可正常读写

[Languages]
Name: "chinesesimp"; MessagesFile: "installer\languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "dist\滴鱼简历助手\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*"

[Icons]
Name: "{autoprograms}\滴鱼简历助手"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\滴鱼简历助手"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 滴鱼简历助手"; Flags: nowait postinstall skipifsilent



[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox('是否同时删除你的全部简历数据（程序目录下的 data 文件夹）？' + #13#10 + #13#10 +
              '选择「否」将保留数据，以后重装可继续使用。', mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{app}\data'), True, True, True);
    end;
  end;
end;