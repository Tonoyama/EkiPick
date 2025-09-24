import { useEffect, useRef, useState } from 'react';

interface HazardLayer {
  id: string;
  name: string;
  url: string;
  attribution: string;
  visible: boolean;
}

interface HazardMapProps {
  center?: { lat: number; lng: number };
  zoom?: number;
  markers?: Array<{
    position: { lat: number; lng: number };
    title: string;
    info?: string;
    hazardRisks?: any;
  }>;
  height?: string;
  onLocationClick?: (lat: number, lng: number) => void;
  showHazardControls?: boolean;
}

declare global {
  interface Window {
    L: any;
  }
}

export default function HazardMapLeaflet({
  center = { lat: 35.6762, lng: 139.6503 },
  zoom = 12,
  markers = [],
  height = '100%',
  onLocationClick,
  showHazardControls = true,
}: HazardMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const hazardLayersRef = useRef<any>({});
  const clickMarkerRef = useRef<any>(null);

  const [hazardLayers, setHazardLayers] = useState<HazardLayer[]>([
    {
      id: 'flood_l2',
      name: '洪水浸水想定（想定最大規模）',
      url: 'https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png',
      attribution: 'ハザードマップポータル',
      visible: false,
    },
    {
      id: 'tsunami',
      name: '津波浸水想定',
      url: 'https://disaportaldata.gsi.go.jp/raster/04_tsunami_newlegend_data/{z}/{x}/{y}.png',
      attribution: 'ハザードマップポータル',
      visible: false,
    },
    {
      id: 'landslide_debris',
      name: '土石流警戒区域',
      url: 'https://disaportaldata.gsi.go.jp/raster/05_dosekiryukeikaikuiki/{z}/{x}/{y}.png',
      attribution: 'ハザードマップポータル',
      visible: false,
    },
    {
      id: 'landslide_slope',
      name: '急傾斜地崩壊警戒区域',
      url: 'https://disaportaldata.gsi.go.jp/raster/05_kyukeishakeikaikuiki/{z}/{x}/{y}.png',
      attribution: 'ハザードマップポータル',
      visible: false,
    },
  ]);

  const [selectedLocation, setSelectedLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [hazardInfo, setHazardInfo] = useState<any>(null);
  const [isLoadingHazard, setIsLoadingHazard] = useState(false);

  // Leafletの初期化
  useEffect(() => {
    if (!document.querySelector('#leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

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

      const map = window.L.map(mapRef.current).setView([center.lat, center.lng], zoom);

      // ベースマップ
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      // クリックイベント
      map.on('click', async (e: any) => {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;

        // 前のクリックマーカーを削除
        if (clickMarkerRef.current) {
          map.removeLayer(clickMarkerRef.current);
        }

        // 新しいマーカーを追加
        const marker = window.L.marker([lat, lng], {
          icon: window.L.icon({
            iconUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJDOC4xMyAyIDUgNS4xMyA1IDlDNSAxNC4yNSAxMiAyMiAxMiAyMlMxOSAxNC4yNSAxOSA5QzE5IDUuMTMgMTUuODcgMiAxMiAyWk0xMiAxMS41QzEwLjYyIDExLjUgOS41IDEwLjM4IDkuNSA5QzkuNSA3LjYyIDEwLjYyIDYuNSAxMiA2LjVDMTMuMzggNi41IDE0LjUgNy42MiAxNC41IDlDMTQuNSAxMC4zOCAxMy4zOCAxMS41IDEyIDExLjVaIiBmaWxsPSIjRUI0MDM0Ii8+Cjwvc3ZnPg==',
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32],
          }),
        }).addTo(map);

        // ローディング中のポップアップを表示
        marker.bindPopup('<div style="text-align: center; padding: 10px;">災害リスク情報を取得中...</div>', { maxWidth: 300 }).openPopup();

        clickMarkerRef.current = marker;
        setSelectedLocation({ lat, lng });

        // 災害リスク情報を取得
        fetchHazardInfo(lat, lng);

        if (onLocationClick) {
          onLocationClick(lat, lng);
        }
      });

      mapInstanceRef.current = map;
      updateMarkers();
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // 災害リスク情報を取得
  async function fetchHazardInfo(lat: number, lng: number) {
    setIsLoadingHazard(true);
    try {
      const apiUrl = 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';
      const response = await fetch(`${apiUrl}/api/v1/hazard/risks?lat=${lat}&lon=${lng}`);
      if (response.ok) {
        const data = await response.json();
        setHazardInfo(data);

        // ポップアップを更新
        if (clickMarkerRef.current && window.L) {
          const popupContent = createHazardPopupContent(data);
          clickMarkerRef.current.setPopupContent(popupContent);
          // ポップアップが閉じられていた場合は再度開く
          if (!clickMarkerRef.current.isPopupOpen()) {
            clickMarkerRef.current.openPopup();
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch hazard info:', error);
      // エラー時のポップアップを表示
      if (clickMarkerRef.current && window.L) {
        clickMarkerRef.current.setPopupContent('<div style="color: red; padding: 10px;">災害リスク情報の取得に失敗しました</div>');
        if (!clickMarkerRef.current.isPopupOpen()) {
          clickMarkerRef.current.openPopup();
        }
      }
    }
    setIsLoadingHazard(false);
  }

  // 災害情報のポップアップコンテンツを作成
  function createHazardPopupContent(data: any) {
    const risks = [];

    if (data.flood?.L2_depth && data.flood.L2_depth !== '対象外') {
      risks.push(`🌊 洪水: ${data.flood.L2_depth}`);
    }
    if (data.tsunami?.depth && data.tsunami.depth !== '対象外' && data.tsunami.depth !== 'データ取得失敗') {
      risks.push(`🌊 津波: ${data.tsunami.depth}`);
    }
    if (data.landslide && Array.isArray(data.landslide) && data.landslide[0] !== '対象外') {
      risks.push(`⛰️ 土砂災害: ${data.landslide.join(', ')}`);
    }

    const content = `
      <div style="padding: 8px;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">
          災害リスク情報
        </h3>
        <p style="margin: 0 0 4px 0; font-size: 11px; color: #666;">
          緯度: ${data.location.lat.toFixed(4)}, 経度: ${data.location.lon.toFixed(4)}
        </p>
        ${risks.length > 0 ?
          `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd;">
            ${risks.map(risk => `<p style="margin: 4px 0; font-size: 12px;">${risk}</p>`).join('')}
          </div>` :
          '<p style="margin: 8px 0 0 0; font-size: 12px; color: #4CAF50;">✓ 災害リスクなし</p>'
        }
      </div>
    `;
    return content;
  }

  // ハザードレイヤーの切り替え
  function toggleHazardLayer(layerId: string) {
    if (!mapInstanceRef.current || !window.L) return;

    setHazardLayers(prev => {
      const newLayers = prev.map(layer => {
        if (layer.id === layerId) {
          const newVisible = !layer.visible;

          if (newVisible) {
            // レイヤーを追加
            if (!hazardLayersRef.current[layerId]) {
              const tileLayer = window.L.tileLayer(layer.url, {
                attribution: layer.attribution,
                opacity: 0.6,
                maxZoom: 17,
              });
              hazardLayersRef.current[layerId] = tileLayer;
            }
            hazardLayersRef.current[layerId].addTo(mapInstanceRef.current);
          } else {
            // レイヤーを削除
            if (hazardLayersRef.current[layerId]) {
              mapInstanceRef.current.removeLayer(hazardLayersRef.current[layerId]);
            }
          }

          return { ...layer, visible: newVisible };
        }
        return layer;
      });
      return newLayers;
    });
  }

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

      // ポップアップコンテンツを作成
      let popupContent = `
        <div style="min-width: 150px;">
          <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">
            ${markerData.title}
          </h3>
      `;

      if (markerData.info) {
        popupContent += `
          <p style="margin: 0; font-size: 12px; color: #666;">
            ${markerData.info}
          </p>
        `;
      }

      // 災害リスク情報があれば追加
      if (markerData.hazardRisks) {
        const risks = [];
        if (markerData.hazardRisks.flood?.L2_depth !== '対象外') {
          risks.push(`洪水: ${markerData.hazardRisks.flood.L2_depth}`);
        }
        if (markerData.hazardRisks.tsunami?.depth !== '対象外') {
          risks.push(`津波: ${markerData.hazardRisks.tsunami.depth}`);
        }

        if (risks.length > 0) {
          popupContent += `
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd;">
              <p style="margin: 0 0 4px 0; font-size: 11px; font-weight: bold; color: #d32f2f;">
                ⚠️ 災害リスク
              </p>
              ${risks.map(risk => `<p style="margin: 2px 0; font-size: 11px; color: #666;">・${risk}</p>`).join('')}
            </div>
          `;
        }
      }

      popupContent += '</div>';
      marker.bindPopup(popupContent);
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
    <div style={{ position: 'relative', width: '100%', height }}>
      <div
        ref={mapRef}
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: '#f0f0f0',
        }}
      >
        {typeof window !== 'undefined' && !window.L && (
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

      {/* ハザードマップレイヤーコントロール */}
      {showHazardControls && (
        <div style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          backgroundColor: 'white',
          color: '#333',
          padding: '12px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          zIndex: 1000,
          maxWidth: '250px',
        }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 'bold', color: '#333' }}>
            ハザードマップ表示
          </h3>
          <div style={{ fontSize: '12px' }}>
            {hazardLayers.map(layer => (
              <label
                key={layer.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '6px',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={layer.visible}
                  onChange={() => toggleHazardLayer(layer.id)}
                  style={{ marginRight: '6px' }}
                />
                <span style={{ color: '#333' }}>{layer.name}</span>
              </label>
            ))}
          </div>
          <div style={{
            marginTop: '12px',
            paddingTop: '12px',
            borderTop: '1px solid #e0e0e0',
            fontSize: '11px',
            color: '#666',
          }}>
            <p style={{ margin: '0 0 4px 0' }}>地図上をクリックして</p>
            <p style={{ margin: '0' }}>災害リスクを確認</p>
          </div>
        </div>
      )}

      {/* 凡例 */}
      {hazardLayers.some(l => l.visible) && (
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '10px',
          backgroundColor: 'white',
          color: '#333',
          padding: '10px',
          borderRadius: '6px',
          boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
          zIndex: 1000,
          fontSize: '11px',
        }}>
          <h4 style={{ margin: '0 0 6px 0', fontSize: '12px', fontWeight: 'bold', color: '#333' }}>
            凡例
          </h4>
          {hazardLayers.find(l => l.id === 'flood_l2' && l.visible) && (
            <div style={{ marginBottom: '6px' }}>
              <p style={{ margin: '0 0 4px 0', fontWeight: 'bold', color: '#333' }}>洪水浸水深</p>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#F7F5A9', marginRight: '4px' }}></div>
                <span style={{ color: '#333' }}>0.5m未満</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#FFD8C0', marginRight: '4px' }}></div>
                <span style={{ color: '#333' }}>0.5-1.0m</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#FFB7B7', marginRight: '4px' }}></div>
                <span style={{ color: '#333' }}>1.0-2.0m</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#FF9191', marginRight: '4px' }}></div>
                <span style={{ color: '#333' }}>2.0-3.0m</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#F285C9', marginRight: '4px' }}></div>
                <span style={{ color: '#333' }}>3.0-5.0m</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#DC7ADC', marginRight: '4px' }}></div>
                <span style={{ color: '#333' }}>5.0m以上</span>
              </div>
            </div>
          )}
          {(hazardLayers.find(l => l.id === 'landslide_debris' && l.visible) ||
            hazardLayers.find(l => l.id === 'landslide_slope' && l.visible)) && (
            <div>
              <p style={{ margin: '6px 0 4px 0', fontWeight: 'bold' }}>土砂災害</p>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#FF0000', marginRight: '4px' }}></div>
                <span>特別警戒区域</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: '16px', height: '12px', backgroundColor: '#FFFF00', marginRight: '4px' }}></div>
                <span>警戒区域</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ローディング表示 */}
      {isLoadingHazard && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          padding: '16px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          zIndex: 2000,
        }}>
          <div className="animate-spin w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px' }}>災害リスク情報を取得中...</p>
        </div>
      )}
    </div>
  );
}