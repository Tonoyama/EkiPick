import { useEffect, useRef } from 'react';

interface MapProps {
  center?: { lat: number; lng: number };
  zoom?: number;
  markers?: Array<{
    position: { lat: number; lng: number };
    title: string;
    info?: string;
  }>;
  height?: string;
  onMarkerClick?: (marker: any) => void;
  onSavePin?: (marker: any) => void;
  isAuthenticated?: boolean;
}

declare global {
  interface Window {
    L: any;
  }
}

export default function MapLeaflet({
  center = { lat: 35.6762, lng: 139.6503 }, // 東京の座標
  zoom = 12,
  markers = [],
  height = '100%',
  onMarkerClick,
  onSavePin,
  isAuthenticated = false,
}: MapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  useEffect(() => {
    // グローバルハンドラーを設定
    if (onSavePin) {
      (window as any).savePinHandler = (title: string, lat: number, lng: number) => {
        onSavePin({
          position: { lat, lng },
          title,
          info: 'チャットからのピン'
        });
      };
    }

    // Leaflet CSS
    if (!document.querySelector('#leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

    // Leaflet JS
    if (!window.L && !document.querySelector('#leaflet-js')) {
      const script = document.createElement('script');
      script.id = 'leaflet-js';
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.async = true;
      script.onload = initMap;
      document.head.appendChild(script);
    } else if (window.L) {
      initMap();
    }

    function initMap() {
      if (!mapRef.current || mapInstanceRef.current) return;

      // マップを初期化
      const map = window.L.map(mapRef.current).setView([center.lat, center.lng], zoom);

      // OpenStreetMapタイルを追加
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;

      // マーカーを追加
      updateMarkers();
    }

    return () => {
      // クリーンアップ
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // マーカーの更新
  useEffect(() => {
    updateMarkers();
  }, [markers]);

  function updateMarkers() {
    if (!mapInstanceRef.current || !window.L) return;

    // 既存のマーカーをクリア
    markersRef.current.forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current = [];

    // 新しいマーカーを追加
    markers.forEach((markerData) => {
      const marker = window.L.marker([markerData.position.lat, markerData.position.lng])
        .addTo(mapInstanceRef.current);

      // ポップアップを追加
      if (markerData.info) {
        const saveButtonHtml = onSavePin && isAuthenticated
          ? `<button
               onclick="window.savePinHandler && window.savePinHandler('${markerData.title}', ${markerData.position.lat}, ${markerData.position.lng})"
               style="
                 background: #3b82f6;
                 color: white;
                 border: none;
                 padding: 4px 8px;
                 border-radius: 4px;
                 font-size: 11px;
                 cursor: pointer;
                 margin-top: 8px;
                 width: 100%;
               "
               onmouseover="this.style.background='#2563eb'"
               onmouseout="this.style.background='#3b82f6'"
             >
               ピンを保存
             </button>`
          : '';

        const popupContent = `
          <div style="min-width: 150px;">
            <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">
              ${markerData.title}
            </h3>
            <p style="margin: 0; font-size: 12px; color: #666;">
              ${markerData.info}
            </p>
            ${saveButtonHtml}
          </div>
        `;
        marker.bindPopup(popupContent);
      } else {
        const saveButtonHtml = onSavePin && isAuthenticated
          ? `<button
               onclick="window.savePinHandler && window.savePinHandler('${markerData.title}', ${markerData.position.lat}, ${markerData.position.lng})"
               style="
                 background: #3b82f6;
                 color: white;
                 border: none;
                 padding: 4px 8px;
                 border-radius: 4px;
                 font-size: 11px;
                 cursor: pointer;
                 margin-top: 8px;
                 width: 100%;
               "
               onmouseover="this.style.background='#2563eb'"
               onmouseout="this.style.background='#3b82f6'"
             >
               ピンを保存
             </button>`
          : '';

        const popupContent = `
          <div style="min-width: 150px;">
            <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">
              ${markerData.title}
            </h3>
            ${saveButtonHtml}
          </div>
        `;
        marker.bindPopup(popupContent);
      }

      // クリックイベント
      if (onMarkerClick) {
        marker.on('click', () => {
          onMarkerClick(markerData);
        });
      }

      markersRef.current.push(marker);
    });

    // マーカーが複数ある場合、全てが見えるように調整
    if (markers.length > 1 && markersRef.current.length > 0) {
      const group = window.L.featureGroup(markersRef.current);
      mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1));
    } else if (markers.length === 1) {
      mapInstanceRef.current.setView([markers[0].position.lat, markers[0].position.lng], 15);
    }
  }

  return (
    <div
      ref={mapRef}
      style={{
        width: '100%',
        height,
        backgroundColor: '#f0f0f0',
        position: 'relative'
      }}
    >
      {!window.L && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center'
        }}>
          <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
          <p>地図を読み込み中...</p>
        </div>
      )}
    </div>
  );
}