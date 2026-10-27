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
        colorPrimary: '#0877c9',
        colorInfo: '#0877c9',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#f6fbff',
        colorText: '#20384b',
        colorTextSecondary: '#437ba3',
        colorTextPlaceholder: '#356c94',
        borderRadius: 12,
        colorBorder: '#5d94bb',
        colorBgContainer: '#ffffff',
        fontSize: 15, controlHeight: 40, controlHeightSM: 32,
        fontFamily: 'Inter, "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#f8fcfe', rowHoverBg: '#f6fafe' },
        Menu: { itemBorderRadius: 12, itemHeight: 42 },
        Button: { fontWeight: 650, borderRadius: 10, controlHeight: 40, controlHeightSM: 32 },
      },
    }}
  >
    <AntApp><ModuleBoundary><Suspense fallback={<ModuleLoading />}><PlatformApp /></Suspense></ModuleBoundary></AntApp>
  </ConfigProvider>
);}
