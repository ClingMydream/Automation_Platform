// File purpose: Shared codec algorithms used by the codec tools page.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import { escapeHtml } from './html';

// 通用转码模块。
// 修改建议：新增一种转码时，只需要在 operations 中加一个 key，并在页面 options 中加展示文案。

// Encode UTF-8 text as Base64.
function utf8ToBase64(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

// Decode Base64 content into UTF-8 text.
function base64ToUtf8(text) {
  const binary = atob(text.trim());
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

// Encode text into a hex string.
function textToHex(text) {
  return [...new TextEncoder().encode(text)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

// Decode a hex string into text.
function hexToText(text) {
  const cleaned = text.replace(/[^0-9a-fA-F]/g, '');
  if (cleaned.length % 2 !== 0) throw new Error('Hex 长度必须是偶数');
  const bytes = new Uint8Array(cleaned.match(/.{2}/g)?.map((part) => parseInt(part, 16)) || []);
  return new TextDecoder().decode(bytes);
}

// Encode text into Unicode escape sequences.
function unicodeEscape(text) {
  return Array.from(text).map((char) => {
    const code = char.codePointAt(0);
    if (code <= 0x7f) return char;
    if (code <= 0xffff) return `\\u${code.toString(16).padStart(4, '0')}`;
    return `\\u{${code.toString(16)}}`;
  }).join('');
}

// Decode Unicode escape sequences into text.
function unicodeUnescape(text) {
  return text
    .replace(/\\u\{([0-9a-fA-F]+)\}/g, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/\\u([0-9a-fA-F]{4})/g, (_, code) => String.fromCharCode(parseInt(code, 16)));
}

// Encode text as HTML entities.
function htmlEntityEncode(text) {
  return escapeHtml(text).replaceAll('\n', '&#10;');
}

// Decode HTML entities into text.
function htmlEntityDecode(text) {
  const textarea = document.createElement('textarea');
  textarea.innerHTML = text;
  return textarea.value;
}

// Encode text as URL-safe Base64URL.
function base64UrlEncode(text) {
  return utf8ToBase64(text).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/g, '');
}

// Decode Base64URL content into text.
function base64UrlDecode(text) {
  const normalized = text.trim().replaceAll('-', '+').replaceAll('_', '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
  return base64ToUtf8(padded);
}

// Dispatch the selected encode or decode operation.
// Shared helper block: exported helpers below are reused by multiple modules.
export function runCodec(operation, input) {
  const operations = {
    url_encode: () => encodeURIComponent(input),
    url_decode: () => decodeURIComponent(input),
    base64_encode: () => utf8ToBase64(input),
    base64_decode: () => base64ToUtf8(input),
    base64url_encode: () => base64UrlEncode(input),
    base64url_decode: () => base64UrlDecode(input),
    unicode_escape: () => unicodeEscape(input),
    unicode_unescape: () => unicodeUnescape(input),
    html_encode: () => htmlEntityEncode(input),
    html_decode: () => htmlEntityDecode(input),
    hex_encode: () => textToHex(input),
    hex_decode: () => hexToText(input),
    json_escape: () => JSON.stringify(input),
    json_unescape: () => {
      const value = JSON.parse(input);
      return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    },
  };
  return operations[operation]?.() ?? input;
}
