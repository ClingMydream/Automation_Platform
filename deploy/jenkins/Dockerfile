FROM jenkins/jenkins:lts-jdk21

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git nodejs npm \
    && rm -rf /var/lib/apt/lists/*

USER jenkins
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    git \
    credentials-binding \
    pipeline-stage-view \
    ws-cleanup
