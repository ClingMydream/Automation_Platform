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
        colorPrimary: '#526b56',
        colorInfo: '#526b56',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#eeeee6',
        colorText: '#303a32',
        colorTextSecondary: '#606c61',
        colorTextPlaceholder: '#606c61',
        borderRadius: 12,
        colorBorder: '#7c897b',
        colorBgContainer: '#f7f7f1',
        colorBgElevated: '#f7f7f1',
        colorBgSpotlight: '#3c483f',
        fontSize: 15, controlHeight: 40, controlHeightSM: 32,
        fontFamily: 'Inter, "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#ecefe6', rowHoverBg: '#e8ede2' },
        Menu: { itemBorderRadius: 12, itemHeight: 42 },
        Button: { fontWeight: 650, borderRadius: 10, controlHeight: 40, controlHeightSM: 32 },
      },
    }}
  >
    <AntApp><ModuleBoundary><Suspense fallback={<ModuleLoading />}><PlatformApp /></Suspense></ModuleBoundary></AntApp>
  </ConfigProvider>
);}
