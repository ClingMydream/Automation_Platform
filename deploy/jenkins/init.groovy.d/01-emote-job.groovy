import hudson.model.ParametersDefinitionProperty
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.csrf.DefaultCrumbIssuer
import jenkins.model.Jenkins
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl
import org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl
import hudson.util.Secret
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def env = System.getenv()
def jenkins = Jenkins.get()
def adminUser = env['JENKINS_ADMIN_USER'] ?: 'cling'
def adminPassword = env['JENKINS_ADMIN_PASSWORD']

if (adminPassword) {
    def realm = jenkins.securityRealm instanceof HudsonPrivateSecurityRealm \
        ? jenkins.securityRealm : new HudsonPrivateSecurityRealm(false)
    if (!hudson.model.User.getById(adminUser, false)) realm.createAccount(adminUser, adminPassword)
    jenkins.setSecurityRealm(realm)
    def strategy = new hudson.security.FullControlOnceLoggedInAuthorizationStrategy()
    strategy.setAllowAnonymousRead(false)
    jenkins.setAuthorizationStrategy(strategy)
    jenkins.setCrumbIssuer(new DefaultCrumbIssuer(true))
}

def store = SystemCredentialsProvider.getInstance().getStore()
def domain = Domain.global()
def replaceCredential = { String id, credential ->
    def existing = store.getCredentials(domain).find { it.id == id }
    if (existing) store.updateCredentials(domain, existing, credential)
    else store.addCredentials(domain, credential)
}

if (env['CODEUP_USERNAME'] && env['CODEUP_PASSWORD']) {
    replaceCredential('codeup-readonly', new UsernamePasswordCredentialsImpl(
        CredentialsScope.GLOBAL, 'codeup-readonly', 'Emote Codeup 只读拉取凭证',
        env['CODEUP_USERNAME'], env['CODEUP_PASSWORD']))
}
if (env['JENKINS_PUBLISH_TOKEN']) {
    replaceCredential('cling-publish-token', new StringCredentialsImpl(
        CredentialsScope.GLOBAL, 'cling-publish-token', 'APK 发布到 cling 的内部令牌',
        Secret.fromString(env['JENKINS_PUBLISH_TOKEN'])))
}

def pipelineScript = new File('/usr/share/jenkins/ref/emote.Jenkinsfile').getText('UTF-8')

def job = jenkins.getItem('emote-apk') as WorkflowJob
if (!job) job = jenkins.createProject(WorkflowJob, 'emote-apk')
job.setDescription('Emote Android 测试包：选择远程分支，只读拉取，构建 Debug APK，并发布到 cling 固定二维码。')
job.setDefinition(new CpsFlowDefinition(pipelineScript, true))
job.save()

def previewPipelineScript = new File('/usr/share/jenkins/ref/emote-preview.Jenkinsfile').getText('UTF-8')
def previewJob = jenkins.getItem('emote-preview') as WorkflowJob
if (!previewJob) previewJob = jenkins.createProject(WorkflowJob, 'emote-preview')
previewJob.setDescription('Emote 在线预览：选择远程分支，只读拉取并同步最新网页代码。')
previewJob.setDefinition(new CpsFlowDefinition(previewPipelineScript, true))
previewJob.save()
jenkins.save()
