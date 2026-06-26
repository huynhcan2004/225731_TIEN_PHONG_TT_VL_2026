/**
 * Phát hiện xem ứng dụng web có đang được hiển thị bên trong WebView của ứng dụng di động hay không.
 *
 * Kiểm tra kết hợp 3 điều kiện để đảm bảo tính chính xác:
 * 1. Cookie `viewappmobie=true` (do ứng dụng di động Flutter tự động thiết lập).
 * 2. User Agent chứa chuỗi nhận dạng của ứng dụng di động (`YhctApp`).
 * 3. Sự tồn tại của kênh giao tiếp JavaScript Bridge `window.FlutterBridge`.
 */
export const isMobileApp = (): boolean => {
  // 1. Kiểm tra Cookie
  const hasCookie = document.cookie
    .split(';')
    .some((item) => item.trim().startsWith('viewappmobie='));

  // 2. Kiểm tra User Agent
  const hasUserAgent = navigator.userAgent.includes('YhctApp');

  // 3. Kiểm tra Flutter JavaScript Bridge
  const hasBridge = typeof (window as any).FlutterBridge !== 'undefined';

  return hasCookie || hasUserAgent || hasBridge;
};
