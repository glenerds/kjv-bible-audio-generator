@echo off
setlocal
cd /d "%~dp0"
set "TMP=%CD%\portable\temp"
set "TEMP=%TMP%"
set "TMPDIR=%TMP%"
set "HOME=%CD%\portable\home"
set "USERPROFILE=%HOME%"
set "APPDATA=%CD%\portable\appdata\roaming"
set "LOCALAPPDATA=%CD%\portable\appdata\local"
set "PYTHONUSERBASE=%CD%\portable\python-userbase"
set "PIP_CACHE_DIR=%CD%\portable\cache\pip"
set "HF_HOME=%CD%\portable\cache\huggingface"
set "HF_HUB_CACHE=%HF_HOME%\hub"
set "TRANSFORMERS_CACHE=%HF_HOME%\transformers"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "HF_DATASETS_OFFLINE=1"
set "TORCH_HOME=%CD%\portable\cache\torch"
set "XDG_CACHE_HOME=%CD%\portable\xdg\cache"
set "NUMBA_CACHE_DIR=%CD%\portable\cache\numba"
set "MPLCONFIGDIR=%CD%\portable\config\matplotlib"
set "XDG_CONFIG_HOME=%CD%\portable\xdg\config"
set "XDG_DATA_HOME=%CD%\portable\xdg\data"
set "XDG_STATE_HOME=%CD%\portable\xdg\state"
for %%D in ("%TMP%" "%HOME%" "%APPDATA%" "%LOCALAPPDATA%" "%PYTHONUSERBASE%" "%PIP_CACHE_DIR%" "%HF_HOME%" "%HF_HUB_CACHE%" "%TRANSFORMERS_CACHE%" "%TORCH_HOME%" "%XDG_CONFIG_HOME%" "%XDG_DATA_HOME%" "%XDG_STATE_HOME%" "%XDG_CACHE_HOME%" "%NUMBA_CACHE_DIR%" "%MPLCONFIGDIR%") do if not exist %%D mkdir %%D
if not exist "KJV Bible Audio Generator.exe" (
  echo The compiled Windows application is not present. This is the developer source tree.
  pause
  exit /b 2
)
start "" "%~dp0KJV Bible Audio Generator.exe"
