#define MyAppName "MahilMart License Manager Web"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MahilTechLab"
#define MyAppExeName "MahilMartLicenseManagerWeb.exe"

[Setup]
AppId={{9D15C5F2-8092-4E9D-9164-DC36D6B59CF4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MahilMart License Manager Web
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist-installer
OutputBaseFilename=MahilMartLicenseManagerWebSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DbConfigPage: TInputQueryWizardPage;
  DbNameValue: string;
  DbPasswordValue: string;

function IsDbNameValid(const Value: string): Boolean;
var
  I: Integer;
  C: Char;
begin
  Result := False;
  if (Length(Value) < 1) or (Length(Value) > 63) then
    Exit;

  C := Value[1];
  if not (((C >= 'A') and (C <= 'Z')) or ((C >= 'a') and (C <= 'z')) or (C = '_')) then
    Exit;

  for I := 1 to Length(Value) do
  begin
    C := Value[I];
    if not (((C >= 'A') and (C <= 'Z')) or ((C >= 'a') and (C <= 'z')) or ((C >= '0') and (C <= '9')) or (C = '_')) then
      Exit;
  end;

  Result := True;
end;

function FindPsqlPath(): string;
begin
  Result := '';
  if FileExists(ExpandConstant('{pf}\PostgreSQL\17\bin\psql.exe')) then
    Result := ExpandConstant('{pf}\PostgreSQL\17\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf}\PostgreSQL\16\bin\psql.exe')) then
    Result := ExpandConstant('{pf}\PostgreSQL\16\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf}\PostgreSQL\15\bin\psql.exe')) then
    Result := ExpandConstant('{pf}\PostgreSQL\15\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf}\PostgreSQL\14\bin\psql.exe')) then
    Result := ExpandConstant('{pf}\PostgreSQL\14\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf32}\PostgreSQL\17\bin\psql.exe')) then
    Result := ExpandConstant('{pf32}\PostgreSQL\17\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf32}\PostgreSQL\16\bin\psql.exe')) then
    Result := ExpandConstant('{pf32}\PostgreSQL\16\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf32}\PostgreSQL\15\bin\psql.exe')) then
    Result := ExpandConstant('{pf32}\PostgreSQL\15\bin\psql.exe')
  else if FileExists(ExpandConstant('{pf32}\PostgreSQL\14\bin\psql.exe')) then
    Result := ExpandConstant('{pf32}\PostgreSQL\14\bin\psql.exe');
end;

function CreateDatabaseIfNeeded(const PsqlPath, DbName, DbPassword: string): Boolean;
var
  ScriptPath: string;
  ScriptText: string;
  Params: string;
  ResultCode: Integer;
begin
  Result := False;
  ScriptPath := ExpandConstant('{tmp}\create_license_db.ps1');
  ScriptText :=
    'param(' + #13#10 +
    '  [Parameter(Mandatory=$true)][string]$PsqlPath,' + #13#10 +
    '  [Parameter(Mandatory=$true)][string]$DbName,' + #13#10 +
    '  [Parameter(Mandatory=$true)][string]$DbPassword' + #13#10 +
    ')' + #13#10 +
    '$ErrorActionPreference = ''Stop''' + #13#10 +
    '$env:PGPASSWORD = $DbPassword' + #13#10 +
    '$exists = (& $PsqlPath -h localhost -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = ''$DbName'';" 2>$null).Trim()' + #13#10 +
    'if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }' + #13#10 +
    'if ($exists -ne ''1'') {' + #13#10 +
    '  & $PsqlPath -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DbName;"' + #13#10 +
    '  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }' + #13#10 +
    '}' + #13#10;

  if not SaveStringToFile(ScriptPath, ScriptText, False) then
  begin
    Log('Failed to write temp PowerShell script: ' + ScriptPath);
    Exit;
  end;

  Params :=
    '-NoProfile -ExecutionPolicy Bypass -File ' + AddQuotes(ScriptPath) +
    ' -PsqlPath ' + AddQuotes(PsqlPath) +
    ' -DbName ' + AddQuotes(DbName) +
    ' -DbPassword ' + AddQuotes(DbPassword);

  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Log('PowerShell execution failed while creating database.');
    Exit;
  end;

  if ResultCode <> 0 then
  begin
    Log(Format('Database creation returned non-zero exit code: %d', [ResultCode]));
    Exit;
  end;

  Result := True;
end;

function SaveDbConfigFile(const DbName, DbPassword: string): Boolean;
var
  ConfigPath: string;
  Content: string;
begin
  ConfigPath := ExpandConstant('{app}\db_config.env');
  Content :=
    'MAHILMART_LICENSE_DB_NAME=' + DbName + #13#10 +
    'MAHILMART_LICENSE_DB_USER=postgres' + #13#10 +
    'MAHILMART_LICENSE_DB_PASSWORD=' + DbPassword + #13#10 +
    'MAHILMART_LICENSE_DB_HOST=localhost' + #13#10 +
    'MAHILMART_LICENSE_DB_PORT=5432' + #13#10;
  Result := SaveStringToFile(ConfigPath, Content, False);
end;

procedure InitializeWizard;
begin
  DbConfigPage := CreateInputQueryPage(
    wpSelectDir,
    'Database Setup',
    'PostgreSQL configuration',
    'Enter database details. Installer will create the database if needed. No license key is required for this app.'
  );
  DbConfigPage.Add('Database Name:', False);
  DbConfigPage.Values[0] := 'license';
  DbConfigPage.Add('PostgreSQL Password (postgres user):', True);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = DbConfigPage.ID then
  begin
    DbNameValue := Trim(DbConfigPage.Values[0]);
    DbPasswordValue := DbConfigPage.Values[1];

    if not IsDbNameValid(DbNameValue) then
    begin
      MsgBox(
        'Database name is invalid. Use 1-63 characters with letters, numbers, and underscore only. ' +
        'First character must be a letter or underscore.',
        mbError,
        MB_OK
      );
      Result := False;
      Exit;
    end;

    if DbPasswordValue = '' then
    begin
      MsgBox('PostgreSQL password is required.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Pos('"', DbPasswordValue) > 0 then
    begin
      MsgBox('Double quote character (") is not supported in password for this installer.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  PsqlPath: string;
  DbReady: Boolean;
  ContinueWithoutDb: Integer;
begin
  if CurStep <> ssPostInstall then
    Exit;

  PsqlPath := FindPsqlPath();
  if PsqlPath = '' then
  begin
    ContinueWithoutDb := MsgBox(
      'PostgreSQL psql.exe was not found. Install PostgreSQL first, then create database "' + DbNameValue + '" manually.' + #13#10 + #13#10 +
      'Continue install without database setup?',
      mbError,
      MB_YESNO
    );
    if ContinueWithoutDb = IDNO then
      RaiseException('Installation cancelled because PostgreSQL was not found.');
  end
  else
  begin
    DbReady := CreateDatabaseIfNeeded(PsqlPath, DbNameValue, DbPasswordValue);
    if not DbReady then
    begin
      ContinueWithoutDb := MsgBox(
        'Database creation failed. Check PostgreSQL password/service and create database manually if needed.' + #13#10 + #13#10 +
        'Continue install anyway?',
        mbError,
        MB_YESNO
      );
      if ContinueWithoutDb = IDNO then
        RaiseException('Installation cancelled because database creation failed.');
    end;
  end;

  if not SaveDbConfigFile(DbNameValue, DbPasswordValue) then
  begin
    RaiseException('Failed to save database config file in app folder.');
  end;
end;
