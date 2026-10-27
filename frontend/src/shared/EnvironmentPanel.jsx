import React, { lazy, Suspense } from 'react';
import { Tabs } from 'antd';
import { ModuleBoundary, ModuleLoading } from './ModuleBoundary.jsx';
const Preview = lazy(()=>import('../modules/15-online-preview/OnlinePreviewPanel.jsx').then(m=>({default:m.OnlinePreviewPanel})));
const Builds = lazy(()=>import('../modules/14-jenkins/JenkinsPanel.jsx').then(m=>({default:m.JenkinsPanel})));
const Packages = lazy(()=>import('../modules/11-test-packages/TestPackagePanel.jsx').then(m=>({default:m.TestPackagePanel})));
export function EnvironmentPanel({client,activeKey,allowedKeys,onChange}) {
  const definitions = [['online_preview','网页预览',Preview],['jenkins','构建打包',Builds],['test_packages','安装包',Packages]];
  return <Tabs className="workspace-tool-tabs" activeKey={activeKey} onChange={onChange} destroyOnHidden items={definitions.filter(([key])=>allowedKeys.has(key)).map(([key,label,Component])=>({key,label,children:<ModuleBoundary><Suspense fallback={<ModuleLoading/>}><Component client={client}/></Suspense></ModuleBoundary>}))}/>;
}
