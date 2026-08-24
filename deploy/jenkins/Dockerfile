FROM jenkins/jenkins:lts-jdk21

USER root
RUN sed -i 's|deb.debian.org/debian|mirrors.cloud.tencent.com/debian|g; s|security.debian.org/debian-security|mirrors.cloud.tencent.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends git unzip curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

ARG NODE_VERSION=22.22.1
RUN curl -fsSL --retry 3 -o /tmp/node.tar.xz "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm -f /tmp/node.tar.xz \
    && npm install --global pnpm@10.15.1 \
    && node --version \
    && pnpm --version

ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV JENKINS_UC_DOWNLOAD=https://mirrors.tuna.tsinghua.edu.cn/jenkins
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
    git-parameter \
    localization-zh-cn

COPY --chown=jenkins:jenkins deploy/jenkins/init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
COPY --chown=jenkins:jenkins deploy/jenkins/emote.Jenkinsfile /usr/share/jenkins/ref/emote.Jenkinsfile
