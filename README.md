# SvcWatchDogClientDemo

[**SvcWatchDogClientDemo**](https://github.com/matjazt/SvcWatchDogClientDemo) is a demonstration project showcasing the integration of a Python application with [SvcWatchDog](https://github.com/matjazt/SvcWatchDog). It doesn't have any other useful function.

## Challenge

The objective was the same as for the [**NotificationServer**](https://github.com/matjazt/NotificationServer) project.

## Result

A `time.sleep(9999999)` (for example) should be detected throughout the code.
This basically means that no matter where the code freezes, **SvcWatchDogClient** or **SvcWatchDog** will detect it and make sure the application is restarted, ensuring that the service is always available.


## How it works

The basics are exactly the same as for the [**NotificationServer**](https://github.com/matjazt/NotificationServer) project.

If your're interested, search for `TimeoutDetector` and `SvcWatchDogClient` in the code to see how the monitoring is implemented.

## How to install service

Preparation steps:
- Make sure the demo works if you start it from command line (`python svc_watch_dog_client_demo.py`). Install required Python modules if needed.
- Download [SvcWatchDog](https://github.com/matjazt/SvcWatchDog) - binary or source, it's up to you
- Customize `scripts\pack.bat` to match your SvcWatchDog folder
- Run `pack.bat` to prepare the distribution folder (**dist**)
- copy **dist** contents to your preffered location

Installation steps (**Admin credentials required**):
- install service: `service\SvcWatchDogClientDemoService -i`
- start service: `net start SvcWatchDogClientDemoService`
- stop service: `net stop SvcWatchDogClientDemoService`
- uninstall service: `service\SvcWatchDogClientDemoService -u`

## How to test

Once the service runs, you can experiment with the `PingEnabled` parameter in the `DummyThread` section of the configuration file (`etc/SvcWatchDogClientDemo.ini`).

Both this demo and **SvcWatchDog** generate detailed log files, which you are encouraged to review.

## Dependencies

This project relies on the following Python modules:
- **pywin32**: Needed for monitoring of SvcWatchDog's named win32 event.
- **pytest**: Only needed for testing.

## Contact

If you have any questions about the demo, I encourage you to [open an issue on GitHub](https://github.com/matjazt/SvcWatchDog/issues).
In case you would like to contact me directly, you can do so at: mt.dev[at]gmx.com .
