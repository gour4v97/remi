@echo off
rem Build the remi-suite Java jar. Requires JDK 17+ on PATH.
cd /d "%~dp0"
if not exist lib\jna.jar curl -sSL -o lib\jna.jar https://repo1.maven.org/maven2/net/java/dev/jna/jna/5.14.0/jna-5.14.0.jar
if not exist lib\jna-platform.jar curl -sSL -o lib\jna-platform.jar https://repo1.maven.org/maven2/net/java/dev/jna/jna-platform/5.14.0/jna-platform-5.14.0.jar
if not exist out mkdir out
dir /s /b src\*.java > sources.txt
javac -encoding UTF-8 -cp "lib\jna.jar;lib\jna-platform.jar" -d out @sources.txt || exit /b 1
jar --create --file remi-suite.jar --main-class suite.Suite -C out .
echo built remi-suite.jar
