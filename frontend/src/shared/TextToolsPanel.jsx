import React, { lazy, Suspense } from 'react';
import { Tabs } from 'antd';
import { ModuleBoundary, ModuleLoading } from './ModuleBoundary.jsx';
const Json = lazy(()=>import('../modules/06-json-tools/JsonToolsPanel.jsx').then(m=>({default:m.JsonToolsPanel})));
const Codec = lazy(()=>import('../modules/07-codec-tools/CodecPanel.jsx').then(m=>({default:m.CodecPanel})));
export function TextToolsPanel({activeKey,allowedKeys,onChange}) {
  return <Tabs className="workspace-tool-tabs" activeKey={activeKey} onChange={onChange} destroyOnHidden items={[
    ['json_tools','JSON 格式化与对比',Json],['codec','编码与解码',Codec],
  ].filter(([key])=>allowedKeys.has(key)).map(([key,label,Component])=>({key,label,children:<ModuleBoundary><Suspense fallback={<ModuleLoading/>}><Component/></Suspense></ModuleBoundary>}))}/>;
}
