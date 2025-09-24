import { useEffect, useRef, useState } from 'react';

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
}

declare global {
  interface Window {
    google: any;
    initMap: () => void;
  }
}

export default function Map({
  center = { lat: 35.6762, lng: 139.6503 }, // 東京の座標
  zoom = 12,
  markers = [],
  height = '100%',
  onMarkerClick,
}: MapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<any>(null);
  const [mapMarkers, setMapMarkers] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Google Maps APIの読み込み
  useEffect(() => {
    if (!window.google && !document.querySelector('#google-maps-script')) {
      const script = document.createElement('script');
      script.id = 'google-maps-script';
      // APIキーなしで開発モードで使用（本番環境では適切なAPIキーを設定してください）
      script.src = `https://maps.googleapis.com/maps/api/js?libraries=places&callback=initMap`;
      script.async = true;
      script.defer = true;

      // グローバルコールバック関数を定義
      window.initMap = () => {
        setIsLoaded(true);
      };

      script.onerror = () => {
        console.error('Google Maps APIの読み込みに失敗しました');
        // フォールバックとして、OpenStreetMapを使用する場合はここに実装
      };

      document.head.appendChild(script);
    } else if (window.google) {
      setIsLoaded(true);
    }
  }, []);

  // マップの初期化
  useEffect(() => {
    if (!isLoaded || !mapRef.current || map) return;

    const newMap = new window.google.maps.Map(mapRef.current, {
      center,
      zoom,
      styles: [
        {
          featureType: "all",
          elementType: "geometry",
          stylers: [{ color: "#f5f5f5" }]
        },
        {
          featureType: "water",
          elementType: "geometry",
          stylers: [{ color: "#c9c9c9" }]
        },
        {
          featureType: "water",
          elementType: "labels.text.fill",
          stylers: [{ color: "#9e9e9e" }]
        }
      ]
    });

    setMap(newMap);
  }, [isLoaded, center, zoom]);

  // マーカーの更新
  useEffect(() => {
    if (!map) return;

    // 既存のマーカーをクリア
    mapMarkers.forEach(marker => marker.setMap(null));

    // 新しいマーカーを追加
    const newMarkers = markers.map((markerData) => {
      const marker = new window.google.maps.Marker({
        position: markerData.position,
        map,
        title: markerData.title,
        animation: window.google.maps.Animation.DROP,
      });

      // 情報ウィンドウを作成
      if (markerData.info) {
        const infoWindow = new window.google.maps.InfoWindow({
          content: `
            <div style="padding: 8px;">
              <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">
                ${markerData.title}
              </h3>
              <p style="margin: 0; font-size: 12px; color: #666;">
                ${markerData.info}
              </p>
            </div>
          `,
        });

        marker.addListener('click', () => {
          infoWindow.open(map, marker);
          if (onMarkerClick) {
            onMarkerClick(markerData);
          }
        });
      }

      return marker;
    });

    setMapMarkers(newMarkers);

    // マーカーが複数ある場合、全てが見えるように調整
    if (markers.length > 1) {
      const bounds = new window.google.maps.LatLngBounds();
      markers.forEach(marker => {
        bounds.extend(marker.position);
      });
      map.fitBounds(bounds);
    } else if (markers.length === 1) {
      map.setCenter(markers[0].position);
      map.setZoom(15);
    }
  }, [map, markers]);

  if (!isLoaded) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f0f0f0' }}>
        <div className="text-gray-500">
          <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
          <p>地図を読み込み中...</p>
        </div>
      </div>
    );
  }

  return <div ref={mapRef} style={{ width: '100%', height }} />;
}