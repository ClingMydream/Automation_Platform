import React, { Suspense } from 'react';
import { App as AntApp, ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import PlatformApp from './PlatformApp.jsx';
import { ModuleBoundary, ModuleLoading } from './shared/ModuleBoundary.jsx';
export default function WorkspaceRoot(){return (
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.defaultAlgorithm,
      token: {
        colorPrimary: '#756092',
        colorInfo: '#756092',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#f8f7f4',
        colorText: '#302c35',
        colorTextSecondary: '#736d79',
        colorTextPlaceholder: '#7f678d',
        borderRadius: 12,
        colorBorder: '#9f89ad',
        colorBgContainer: '#fffefd',
        fontSize: 15, controlHeight: 40, controlHeightSM: 32,
        fontFamily: 'Inter, "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#f6f4f8', rowHoverBg: '#f4f0f7' },
        Menu: { itemBorderRadius: 12, itemHeight: 42 },
        Button: { fontWeight: 650, borderRadius: 10, controlHeight: 40, controlHeightSM: 32 },
      },
    }}
  >
    <AntApp><ModuleBoundary><Suspense fallback={<ModuleLoading />}><PlatformApp /></Suspense></ModuleBoundary></AntApp>
  </ConfigProvider>
);}
