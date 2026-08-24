FROM jenkins/jenkins:lts-jdk21

USER root
RUN sed -i 's|deb.debian.org/debian|mirrors.cloud.tencent.com/debian|g; s|security.debian.org/debian-security|mirrors.cloud.tencent.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends git nodejs npm unzip curl \
    && rm -rf /var/lib/apt/lists/*

ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools"
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools \
    && curl -fsSL --retry 3 -o /tmp/android-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip \
    && unzip -q /tmp/android-tools.zip -d /tmp/android-tools \
    && mv /tmp/android-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest \
    && rm -rf /tmp/android-tools /tmp/android-tools.zip \
    && yes | sdkmanager --licenses >/dev/null \
    && sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0" \
    && chown -R jenkins:jenkins ${ANDROID_HOME}

USER jenkins
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    git \
    credentials-binding \
    pipeline-stage-view \
    ws-cleanup \
    git-parameter

COPY --chown=jenkins:jenkins deploy/jenkins/init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
COPY --chown=jenkins:jenkins deploy/jenkins/emote.Jenkinsfile /usr/share/jenkins/ref/emote.Jenkinsfile
