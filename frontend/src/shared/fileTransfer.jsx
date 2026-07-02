import React from 'react';

// 文件快传前端辅助模块。
// 修改建议：文件类型识别、预览方式、下载行为都集中在这里，页面组件只负责列表和表单。

// Detect the file transfer type from MIME type and file name.
export function transferKind(item) {
  const contentType = (item?.content_type || '').toLowerCase();
  const name = (item?.original_name || '').toLowerCase();
  if (contentType.startsWith('image/') || /\.(apng|avif|bmp|gif|heic|heif|ico|jpe?g|png|svg|webp)$/.test(name)) return 'image';
  if (contentType.startsWith('video/') || /\.(3gp|avi|m4v|mkv|mov|mp4|mpeg|mpg|ogv|webm)$/.test(name)) return 'video';
  return 'file';
}

// Convert a transfer type into display text.
export function transferKindLabel(item) {
  return { image: '图片', video: '视频', file: '文件' }[transferKind(item)];
}

// Render image, video, or generic file preview for transfers.
export function TransferPreview({ item }) {
  if (!item) return null;
  const kind = transferKind(item);
  if (kind === 'image') {
    return (
      <div className="transfer-preview">
        <img src={item.preview_url || item.download_url} alt={item.original_name} />
      </div>
    );
  }
  if (kind === 'video') {
    return (
      <div className="transfer-preview transfer-preview-video">
        <video controls preload="metadata" src={item.preview_url || item.download_url}>
          <track kind="captions" />
        </video>
      </div>
    );
  }
  return null;
}

// Create a temporary object URL and trigger browser download.
export function downloadBlob(blob, fallbackName, onPreview) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  onPreview?.(objectUrl);
}
