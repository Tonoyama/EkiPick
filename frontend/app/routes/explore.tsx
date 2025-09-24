import type { Route } from "./+types/explore";
import { useState, useEffect } from "react";
import MapLeaflet from "../components/MapLeaflet";
import { useAuth } from "../contexts/AuthContext";
import { LocalPinManager } from "~/utils/localPins";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "駅探索 | A2A Estate" },
    { name: "description", content: "到達可能な駅を探索して最適な住まいを見つける" },
  ];
}

interface ReachableStation {
  station_name: string;
  line_name?: string;
  travel_time: number;
  coord_lat: number;
  coord_lon: number;
  average_rent?: number;
  area_characteristics?: any;
  area_tags?: string[];
}

export default function Explore() {
  const { user, isAuthenticated } = useAuth();
  const [stationName, setStationName] = useState("");
  const [timeLimit, setTimeLimit] = useState(30);
  const [maxRent, setMaxRent] = useState<number | undefined>();
  const [minRent, setMinRent] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [reachableStations, setReachableStations] = useState<ReachableStation[]>([]);
  const [optimalStations, setOptimalStations] = useState<ReachableStation[]>([]);
  const [selectedStation, setSelectedStation] = useState<ReachableStation | null>(null);
  const [placeInfo, setPlaceInfo] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"reachable" | "optimal">("reachable");

  const API_BASE_URL = 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';

  // 駅をピンに保存
  const saveStationPin = async (station: ReachableStation | null) => {
    if (!station) return;

    if (isAuthenticated) {
      // ログイン済みの場合はサーバーに保存
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          alert('ログインが必要です');
          return;
        }

        const response = await fetch(`${API_BASE_URL}/api/v1/pins/`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            station_name: station.station_name,
            line_name: station.line_name,
            coord_lat: station.coord_lat,
            coord_lon: station.coord_lon,
            conversation_context: '探索ページから保存',
            notes: `到達時間: ${station.travel_time}分${station.average_rent ? `, 家賃相場: ${station.average_rent.toFixed(1)}万円` : ''}`,
            tags: station.area_tags,
            nearby_places: station.area_characteristics,
            reachable_stations: station.reachable_stations,
            average_rent: station.average_rent
          })
        });

        if (response.ok) {
          alert('ピンを保存しました！');
        } else if (response.status === 400) {
          const error = await response.json();
          alert(error.detail || 'この駅は既に保存されています');
        } else {
          throw new Error('保存に失敗しました');
        }
      } catch (error) {
        console.error('Pin save error:', error);
        alert('ピンの保存中にエラーが発生しました');
      }
    } else {
      // 未ログインの場合はローカルストレージに保存
      try {
        LocalPinManager.saveLocalPin({
          station_name: station.station_name,
          line_name: station.line_name,
          coord_lat: station.coord_lat,
          coord_lon: station.coord_lon,
          conversation_context: '探索ページから保存',
          notes: `到達時間: ${station.travel_time}分${station.average_rent ? `, 家賃相場: ${station.average_rent.toFixed(1)}万円` : ''}`,
          tags: station.area_tags,
          nearby_places: station.area_characteristics,
          reachable_stations: station.reachable_stations,
          average_rent: station.average_rent
        });
        alert('ピンをローカルに保存しました！ログイン後にサーバーに同期されます。');
      } catch (error) {
        if (error instanceof Error) {
          alert(error.message);
        } else {
          alert('ピンの保存中にエラーが発生しました');
        }
      }
    }
  };

  // 到達可能駅を探索
  const exploreReachableStations = async () => {
    if (!stationName) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/explore/reachable`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          station_name: stationName,
          time_limit: timeLimit,
          search_radius: 1500,
          analyze_places: true,
          save_pins: isAuthenticated
        })
      });

      if (response.ok) {
        const data = await response.json();
        setReachableStations(data.reachable_stations || []);
      }
    } catch (error) {
      console.error("Failed to explore stations:", error);
    } finally {
      setLoading(false);
    }
  };

  // 最適駅を検索
  const findOptimalStations = async () => {
    if (!stationName) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/explore/optimal`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          station_name: stationName,
          max_travel_time: timeLimit,
          max_rent: maxRent,
          min_rent: minRent,
          analyze_places: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        setOptimalStations(data.optimal_stations || []);
        setActiveTab("optimal");
      }
    } catch (error) {
      console.error("Failed to find optimal stations:", error);
    } finally {
      setLoading(false);
    }
  };

  // 駅周辺の施設情報を取得
  const getStationPlaces = async (station: ReachableStation) => {
    setSelectedStation(station);
    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/explore/station/${encodeURIComponent(station.station_name)}/places?radius=1000`
      );

      if (response.ok) {
        const data = await response.json();
        setPlaceInfo(data);
      }
    } catch (error) {
      console.error("Failed to get station places:", error);
    } finally {
      setLoading(false);
    }
  };

  // マーカーデータを準備
  const getMapMarkers = () => {
    const stations = activeTab === "reachable" ? reachableStations : optimalStations;
    return stations.map(station => ({
      position: { lat: station.coord_lat, lng: station.coord_lon },
      title: station.station_name,
      info: `${station.line_name || ''} - ${station.travel_time}分 ${station.average_rent ? `¥${station.average_rent.toFixed(1)}万` : ''}`
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          駅探索
        </h1>

        {/* 検索条件 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            検索条件
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                起点駅名
              </label>
              <input
                type="text"
                value={stationName}
                onChange={(e) => setStationName(e.target.value)}
                placeholder="例: 新宿"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                到達時間（分）
              </label>
              <input
                type="number"
                value={timeLimit}
                onChange={(e) => setTimeLimit(Number(e.target.value))}
                min="10"
                max="60"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最大家賃（万円）
              </label>
              <input
                type="number"
                value={maxRent || ''}
                onChange={(e) => setMaxRent(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="例: 15"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最小家賃（万円）
              </label>
              <input
                type="number"
                value={minRent || ''}
                onChange={(e) => setMinRent(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="例: 8"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
          <div className="flex gap-4 mt-4">
            <button
              onClick={exploreReachableStations}
              disabled={!stationName || loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-6 rounded-md transition"
            >
              {loading ? "探索中..." : "到達可能駅を探索"}
            </button>
            <button
              onClick={findOptimalStations}
              disabled={!stationName || loading}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-2 px-6 rounded-md transition"
            >
              {loading ? "検索中..." : "最適駅を検索"}
            </button>
          </div>
        </div>

        {/* タブ */}
        <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab("reachable")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "reachable"
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
              }`}
            >
              到達可能駅 ({reachableStations.length})
            </button>
            <button
              onClick={() => setActiveTab("optimal")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "optimal"
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
              }`}
            >
              最適駅 ({optimalStations.length})
            </button>
          </nav>
        </div>

        {/* 地図と結果 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 地図 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                駅マップ
              </h3>
            </div>
            <div style={{ height: '500px' }}>
              <MapLeaflet
                center={
                  reachableStations.length > 0
                    ? { lat: reachableStations[0].coord_lat, lng: reachableStations[0].coord_lon }
                    : { lat: 35.689487, lng: 139.691706 }
                }
                zoom={12}
                markers={getMapMarkers()}
                height="500px"
                onMarkerClick={(marker) => {
                  const station = (activeTab === "reachable" ? reachableStations : optimalStations).find(
                    s => s.station_name === marker.title
                  );
                  if (station) {
                    getStationPlaces(station);
                  }
                }}
              />
            </div>
          </div>

          {/* 駅リスト */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {activeTab === "reachable" ? "到達可能駅一覧" : "最適駅一覧"}
              </h3>
            </div>
            <div className="max-h-[500px] overflow-y-auto">
              {(activeTab === "reachable" ? reachableStations : optimalStations).map((station, index) => (
                <div
                  key={`${station.station_name}-${index}`}
                  className={`p-4 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer ${
                    selectedStation?.station_name === station.station_name ? 'bg-blue-50 dark:bg-blue-900' : ''
                  }`}
                  onClick={() => getStationPlaces(station)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {station.station_name}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {station.line_name}
                      </p>
                      <div className="flex gap-4 mt-1">
                        <span className="text-sm text-blue-600 dark:text-blue-400">
                          🚃 {station.travel_time}分
                        </span>
                        {station.average_rent && (
                          <span className="text-sm text-green-600 dark:text-green-400">
                            💴 {station.average_rent.toFixed(1)}万円
                          </span>
                        )}
                      </div>
                      {station.area_tags && station.area_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {station.area_tags.map((tag, i) => (
                            <span
                              key={i}
                              className="inline-block px-2 py-1 text-xs bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {(station as any).optimization_score && (
                      <div className="text-right">
                        <span className="text-sm text-gray-500 dark:text-gray-400">スコア</span>
                        <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                          {((station as any).optimization_score * 100).toFixed(0)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 駅詳細情報 */}
        {selectedStation && placeInfo && (
          <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {selectedStation.station_name}駅の周辺情報
            </h3>

            {placeInfo.area_analysis && (
              <div className="mb-6">
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">エリア特性</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                    <div className="text-sm text-gray-600 dark:text-gray-300">利便性</div>
                    <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                      {placeInfo.area_analysis.characteristics?.convenience || 0}点
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                    <div className="text-sm text-gray-600 dark:text-gray-300">ファミリー向け</div>
                    <div className="text-xl font-bold text-green-600 dark:text-green-400">
                      {placeInfo.area_analysis.characteristics?.family_friendly || 0}点
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                    <div className="text-sm text-gray-600 dark:text-gray-300">買い物便利度</div>
                    <div className="text-xl font-bold text-purple-600 dark:text-purple-400">
                      {placeInfo.area_analysis.characteristics?.shopping || 0}点
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                    <div className="text-sm text-gray-600 dark:text-gray-300">医療充実度</div>
                    <div className="text-xl font-bold text-red-600 dark:text-red-400">
                      {placeInfo.area_analysis.characteristics?.medical || 0}点
                    </div>
                  </div>
                </div>

                {placeInfo.area_analysis.characteristics?.tags && (
                  <div className="mt-3">
                    <div className="flex flex-wrap gap-2">
                      {placeInfo.area_analysis.characteristics.tags.map((tag: string, i: number) => (
                        <span
                          key={i}
                          className="inline-block px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {placeInfo.places?.categories && (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">周辺施設</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(placeInfo.places.categories).map(([category, places]: [string, any]) => (
                    <div key={category} className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                      <h5 className="font-medium text-gray-900 dark:text-white mb-2">
                        {category} ({places.length}件)
                      </h5>
                      <ul className="space-y-1">
                        {places.slice(0, 3).map((place: any, i: number) => (
                          <li key={i} className="text-sm text-gray-600 dark:text-gray-300">
                            • {place.name} ({Math.round(place.distance)}m)
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-4">
              <button
                onClick={() => saveStationPin(selectedStation)}
                className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition"
              >
                この駅をピンに保存
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}