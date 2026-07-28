#!/bin/sh
#
# Gradle wrapper script
#
set -e

APP_HOME="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Gradle"
CLASSPATH="$APP_HOME/gradle/wrapper/gradle-wrapper.jar"

JAVA_EXE="$JAVA_HOME/bin/java"
if [ -z "$JAVA_HOME" ]; then
    JAVA_EXE="java"
fi

exec "$JAVA_EXE" \
    -classpath "$CLASSPATH" \
    org.gradle.wrapper.GradleWrapperMain "$@"
