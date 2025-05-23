@SET SVCWATCHDOGFOLDER=..\..\..\SysTools\SvcWatchDog\SvcWatchDogDist
@SET OUTPUTFOLDER=..\dist

@echo Folder %OUTPUTFOLDER% will be deleted and recreated. If you don't want this, press ctrl-c.

pause

if exist %OUTPUTFOLDER% rd /s /q %OUTPUTFOLDER%

mkdir %OUTPUTFOLDER%\src\tools
mkdir %OUTPUTFOLDER%\service
mkdir %OUTPUTFOLDER%\etc
mkdir %OUTPUTFOLDER%\doc\SvcWatchDog

copy /y %SVCWATCHDOGFOLDER%\SvcWatchDog\SvcWatchDog.exe %OUTPUTFOLDER%\Service\SvcWatchDogClientDemoService.exe
copy /y %SVCWATCHDOGFOLDER%\Doc\* %OUTPUTFOLDER%\Doc\SvcWatchDog

xcopy /y /s ..\src\*.py %OUTPUTFOLDER%\src

copy /y ..\Etc\SvcWatchDogClientDemo.ini %OUTPUTFOLDER%\Etc
copy /y ..\Etc\SvcWatchDogClientDemoService.json %OUTPUTFOLDER%\Service

pause