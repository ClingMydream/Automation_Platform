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
        colorPrimary: '#0066cc',
        colorInfo: '#0066cc',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#f5f5f7',
        colorText: '#1d1d1f',
        colorTextSecondary: '#6e6e73',
        colorTextPlaceholder: '#6e6e73',
        borderRadius: 12,
        colorBorder: '#d2d2d7',
        colorBgContainer: '#ffffff',
        colorBgElevated: '#ffffff',
        colorBgSpotlight: '#29292c',
        fontSize: 15, controlHeight: 40, controlHeightSM: 32,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#f5f5f7', rowHoverBg: '#f0f5fc' },
        Menu: { itemBorderRadius: 12, itemHeight: 42 },
        Button: { fontWeight: 500, borderRadius: 10, controlHeight: 40, controlHeightSM: 32 },
      },
    }}
  >
    <AntApp><ModuleBoundary><Suspense fallback={<ModuleLoading />}><PlatformApp /></Suspense></ModuleBoundary></AntApp>
  </ConfigProvider>
);}
