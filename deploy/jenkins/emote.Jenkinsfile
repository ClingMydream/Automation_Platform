pipeline {
  agent any
  options { disableConcurrentBuilds(); buildDiscarder(logRotator(numToKeepStr: '10', artifactNumToKeepStr: '5')) }
  parameters {
    gitParameter(name: 'BRANCH', type: 'PT_BRANCH', defaultValue: 'origin/dev-20260811-1.9.1-test',
      branchFilter: 'origin/(.*)', sortMode: 'DESCENDING_SMART', selectedValue: 'DEFAULT',
      quickFilterEnabled: true, listSize: '15',
      useRepository: 'https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git',
      description: '选择需要打包的远程分支；可在输入框中搜索分支名称')
  }
  environment { REPOSITORY_URL = 'https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git' }
  stages {
    stage('只读拉取代码') {
      steps {
        script {
          if (!(params.BRANCH ==~ /^origin\/[A-Za-z0-9._\/-]+$/)) {
            error("远程分支格式不合法：${params.BRANCH}")
          }
          def branchName = params.BRANCH.replaceFirst(/^origin\//, '')
          currentBuild.description = "分支：${branchName}"
          echo "本次只读构建分支：${branchName}"
          checkout([$class: 'GitSCM', branches: [[name: branchName]],
            userRemoteConfigs: [[url: env.REPOSITORY_URL, credentialsId: 'codeup-readonly']]])
        }
      }
    }
    stage('安装前端依赖') { steps { sh 'pnpm install --frozen-lockfile' } }
    stage('同步 Android 工程') { steps { sh 'pnpm build -- --mode production && pnpm exec cap sync android' } }
    stage('构建 Debug APK') {
      steps { dir('android') { sh 'chmod +x gradlew && ./gradlew assembleDebug --no-daemon --max-workers=2' } }
    }
    stage('归档并发布') {
      steps {
        script {
          def apk = sh(script: "find android/app/build/outputs/apk/debug -name '*.apk' -type f | head -1", returnStdout: true).trim()
          if (!apk) error('没有找到构建后的 APK')
          sh "cp '${apk}' emote-${BUILD_NUMBER}.apk"
        }
        archiveArtifacts artifacts: 'emote-*.apk', fingerprint: true
        withCredentials([string(credentialsId: 'cling-publish-token', variable: 'PUBLISH_TOKEN')]) {
          sh '''curl --fail --show-error --silent --retry 3 \
            -H "X-Jenkins-Token: ${PUBLISH_TOKEN}" \
            -F "file=@emote-${BUILD_NUMBER}.apk;type=application/vnd.android.package-archive" \
            -F "version=1.9.1-build-${BUILD_NUMBER}" \
            -F "notes=Jenkins 自动构建，分支 ${BRANCH}，构建 #${BUILD_NUMBER}" \
            http://backend:8000/api/test-packages/internal/jenkins/latest'''
        }
      }
    }
  }
  post { always { cleanWs(deleteDirs: true, disableDeferredWipeout: true) } }
}
