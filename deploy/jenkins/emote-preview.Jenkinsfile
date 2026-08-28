pipeline {
  agent any
  options { disableConcurrentBuilds(); buildDiscarder(logRotator(numToKeepStr: '10')) }
  parameters {
    gitParameter(name: 'BRANCH', type: 'PT_BRANCH', defaultValue: 'origin/dev-20260811-1.9.1',
      branchFilter: 'origin/(.*)', sortMode: 'DESCENDING_SMART', selectedValue: 'DEFAULT',
      quickFilterEnabled: true, listSize: '15',
      useRepository: 'https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git',
      description: '选择需要同步到在线预览的远程分支')
  }
  environment { REPOSITORY_URL = 'https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git' }
  stages {
    stage('只读拉取代码') {
      steps {
        script {
          def selectedBranch = params.BRANCH?.trim()
          if (!(selectedBranch ==~ /^(origin\/)?[A-Za-z0-9._\/-]+$/)) {
            error("远程分支格式不合法：${selectedBranch ?: '未选择'}")
          }
          def branchName = selectedBranch.replaceFirst(/^origin\//, '')
          currentBuild.description = "预览分支：${branchName}"
          checkout([$class: 'GitSCM', branches: [[name: branchName]],
            userRemoteConfigs: [[url: env.REPOSITORY_URL, credentialsId: 'codeup-readonly']]])
          def commitSha = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
          env.PREVIEW_BRANCH = branchName
          env.PREVIEW_SHA = commitSha
          currentBuild.description = "预览分支：${branchName} | SHA：${commitSha}"
        }
      }
    }
    stage('安装依赖') { steps { sh 'pnpm install --frozen-lockfile' } }
    stage('兼容 Linux 文件名') {
      steps { sh '''if [ ! -f assets/activitys/item/card-bg-full.jpg ] && [ -f assets/activitys/item/card-bg-full.JPG ]; then
        cp assets/activitys/item/card-bg-full.JPG assets/activitys/item/card-bg-full.jpg
      fi''' }
    }
    stage('构建预览页面') {
      steps {
        // The preview runs on this cloud server, so it must never inherit a
        // developer LAN address from a checked-out branch. This only injects
        // the test backend into the generated preview files; source code stays read-only.
        sh 'VITE_API_BASE=https://www.inxpiration.cn/emote-test/api pnpm build -- --mode production'
      }
    }
    stage('适配预览子路径') {
      steps {
        sh '''# emote 源码中的 Logo 使用站点根路径；在线预览部署在 /emote-preview/ 下。
          # 只修改本次构建产物，不修改、提交或推送 emote 仓库。
          for pattern in '*.js' '*.html' '*.css'; do
            find dist -type f -name "$pattern" -exec sed -i 's|/emote.png|/emote-preview/emote.png|g' {} +
          done'''
      }
    }
    stage('发布在线预览') {
      steps {
        sh '''set -eu
          # This manifest is deployed with the static site. It is the source of truth
          # for the revision actually being served, even if a later Jenkins build fails.
          printf '{"branch":"%s","sha":"%s","build_number":"%s","published_at":"%s"}\n' \\
            "$PREVIEW_BRANCH" "$PREVIEW_SHA" "$BUILD_NUMBER" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > dist/.cling-preview-revision.json
          rm -rf /srv/emote-preview/next
          mkdir -p /srv/emote-preview/next
          cp -a dist/. /srv/emote-preview/next/
          rm -rf /srv/emote-preview/previous
          if [ -d /srv/emote-preview/current ]; then mv /srv/emote-preview/current /srv/emote-preview/previous; fi
          mv /srv/emote-preview/next /srv/emote-preview/current'''
      }
    }
  }
  post { always { cleanWs(deleteDirs: true, disableDeferredWipeout: true) } }
}
