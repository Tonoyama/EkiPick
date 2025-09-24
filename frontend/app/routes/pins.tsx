import type { Route } from "./+types/pins";
import { useState, useEffect } from "react";
import MapLeaflet from "../components/MapLeaflet";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router";
import { LocalPinManager, type LocalPin } from "~/utils/localPins";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "保存ピン | A2A Estate" },
    { name: "description", content: "保存した駅情報を管理" },
  ];
}

interface SavedPin {
  id: number;
  station_name: string;
  line_name?: string;
  coord_lat: number;
  coord_lon: number;
  nearby_places?: any;
  reachable_stations?: any[];
  average_rent?: number;
  conversation_context?: string;
  notes?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

export default function Pins() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [pins, setPins] = useState<SavedPin[]>([]);
  const [localPins, setLocalPins] = useState<LocalPin[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPin, setSelectedPin] = useState<SavedPin | LocalPin | null>(null);
  const [editingPin, setEditingPin] = useState<SavedPin | LocalPin | null>(null);
  const [filterTag, setFilterTag] = useState("");
  const [filterStation, setFilterStation] = useState("");

  const API_BASE_URL = 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';

  useEffect(() => {
    if (isAuthenticated) {
      loadPins();
    }
    // ローカルピンを常に読み込む
    loadLocalPins();
  }, [isAuthenticated]);

  const loadLocalPins = () => {
    const localPinData = LocalPinManager.getLocalPins();
    setLocalPins(localPinData);
  };

  const loadPins = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const params = new URLSearchParams();
      if (filterTag) params.append('tags', filterTag);
      if (filterStation) params.append('station_name', filterStation);

      const response = await fetch(`${API_BASE_URL}/api/v1/pins?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPins(data);
      }
    } catch (error) {
      console.error("Failed to load pins:", error);
    } finally {
      setLoading(false);
    }
  };

  const deletePin = async (pin: SavedPin | LocalPin) => {
    if (!confirm('このピンを削除しますか？')) return;

    if ('source' in pin && pin.source === 'local') {
      // ローカルピンの削除
      try {
        const success = LocalPinManager.deleteLocalPin(pin.id);
        if (success) {
          setLocalPins(localPins.filter(p => p.id !== pin.id));
          if (selectedPin?.id === pin.id) {
            setSelectedPin(null);
          }
        }
      } catch (error) {
        console.error("Failed to delete local pin:", error);
      }
    } else {
      // サーバーピンの削除
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        const response = await fetch(`${API_BASE_URL}/api/v1/pins/${pin.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          setPins(pins.filter(p => p.id !== pin.id));
          if (selectedPin?.id === pin.id) {
            setSelectedPin(null);
          }
        }
      } catch (error) {
        console.error("Failed to delete pin:", error);
      }
    }
  };

  const updatePin = async (pin: SavedPin | LocalPin) => {
    if ('source' in pin && pin.source === 'local') {
      // ローカルピンの更新
      try {
        const updatedPin = LocalPinManager.updateLocalPin(pin.id, {
          notes: pin.notes,
          tags: pin.tags
        });
        if (updatedPin) {
          setLocalPins(localPins.map(p => p.id === updatedPin.id ? updatedPin : p));
          setEditingPin(null);
        }
      } catch (error) {
        console.error("Failed to update local pin:", error);
      }
    } else {
      // サーバーピンの更新
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        const response = await fetch(`${API_BASE_URL}/api/v1/pins/${pin.id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            notes: pin.notes,
            tags: pin.tags
          })
        });

        if (response.ok) {
          const updatedPin = await response.json();
          setPins(pins.map(p => p.id === updatedPin.id ? updatedPin : p));
          setEditingPin(null);
        }
      } catch (error) {
        console.error("Failed to update pin:", error);
      }
    }
  };

  // サーバーピンとローカルピンを統合
  const allPins = [...pins, ...localPins];

  // フィルタリング適用
  const filteredPins = allPins.filter(pin => {
    const matchesStation = !filterStation || pin.station_name.toLowerCase().includes(filterStation.toLowerCase());
    const matchesTag = !filterTag || (pin.tags && pin.tags.includes(filterTag));
    return matchesStation && matchesTag;
  });

  // 全てのユニークなタグを取得
  const allTags = Array.from(new Set(allPins.flatMap(p => p.tags || [])));

  // マップマーカーを準備
  const mapMarkers = filteredPins.map(pin => ({
    position: { lat: pin.coord_lat, lng: pin.coord_lon },
    title: pin.station_name,
    info: `${pin.line_name || ''} ${pin.average_rent ? `¥${pin.average_rent.toFixed(1)}万` : ''} ${'source' in pin ? '(ローカル)' : ''}`
  }));

  if (!isAuthenticated && localPins.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            保存されたピンがありません
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            ピンを保存するには駅を探索するか、Googleアカウントでログインしてください
          </p>
          <button
            onClick={() => navigate('/explore')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition"
          >
            駅を探索する
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          保存したピン
        </h1>

        {/* フィルター */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            フィルター
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                駅名
              </label>
              <input
                type="text"
                value={filterStation}
                onChange={(e) => setFilterStation(e.target.value)}
                placeholder="駅名で検索"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                タグ
              </label>
              <select
                value={filterTag}
                onChange={(e) => setFilterTag(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">すべてのタグ</option>
                {allTags.map(tag => (
                  <option key={tag} value={tag}>{tag}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={loadPins}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition"
              >
                検索
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 地図 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                ピンマップ ({filteredPins.length}件)
              </h3>
              {!isAuthenticated && localPins.length > 0 && (
                <p className="text-sm text-orange-600 dark:text-orange-400 mt-1">
                  ローカル保存されたピンが含まれています。ログインして同期することをお勧めします。
                </p>
              )}
            </div>
            <div style={{ height: '600px' }}>
              <MapLeaflet
                center={
                  filteredPins.length > 0
                    ? { lat: filteredPins[0].coord_lat, lng: filteredPins[0].coord_lon }
                    : { lat: 35.689487, lng: 139.691706 }
                }
                zoom={11}
                markers={mapMarkers}
                height="600px"
                onMarkerClick={(marker) => {
                  const pin = filteredPins.find(p => p.station_name === marker.title);
                  if (pin) {
                    setSelectedPin(pin);
                  }
                }}
              />
            </div>
          </div>

          {/* ピンリスト */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                保存済みピン
              </h3>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {loading ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  読み込み中...
                </div>
              ) : filteredPins.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  <p className="mb-4">
                    {filterStation || filterTag
                      ? "条件に一致するピンがありません"
                      : "保存されたピンがありません"
                    }
                  </p>
                  {!filterStation && !filterTag && (
                    <button
                      onClick={() => navigate('/explore')}
                      className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition"
                    >
                      駅を探索する
                    </button>
                  )}
                </div>
              ) : (
                filteredPins.map(pin => (
                  <div
                    key={pin.id}
                    className={`p-4 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer ${
                      selectedPin?.id === pin.id ? 'bg-blue-50 dark:bg-blue-900' : ''
                    }`}
                    onClick={() => setSelectedPin(pin)}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-gray-900 dark:text-white">
                            {pin.station_name}
                          </h4>
                          {'source' in pin && pin.source === 'local' && (
                            <span className="inline-block px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-200 rounded">
                              ローカル
                            </span>
                          )}
                        </div>
                        {pin.line_name && (
                          <p className="text-sm text-gray-600 dark:text-gray-300">
                            {pin.line_name}
                          </p>
                        )}
                        {pin.average_rent && (
                          <p className="text-sm text-green-600 dark:text-green-400">
                            家賃相場: {pin.average_rent.toFixed(1)}万円
                          </p>
                        )}
                        {pin.tags && pin.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {pin.tags.map((tag, i) => (
                              <span
                                key={i}
                                className="inline-block px-2 py-1 text-xs bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                          保存日: {new Date(pin.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingPin(pin);
                          }}
                          className="text-blue-600 hover:text-blue-700 dark:text-blue-400"
                        >
                          編集
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deletePin(pin);
                          }}
                          className="text-red-600 hover:text-red-700 dark:text-red-400"
                        >
                          削除
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ピン詳細 */}
        {selectedPin && !editingPin && (
          <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedPin.station_name}駅の詳細
              </h3>
              <button
                onClick={() => setEditingPin(selectedPin)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition"
              >
                編集
              </button>
            </div>

            {selectedPin.notes && (
              <div className="mb-4">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">メモ</h4>
                <p className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                  {selectedPin.notes}
                </p>
              </div>
            )}

            {selectedPin.conversation_context && (
              <div className="mb-4">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">保存時のコンテキスト</h4>
                <p className="text-gray-600 dark:text-gray-300">
                  {selectedPin.conversation_context}
                </p>
              </div>
            )}

            {selectedPin.reachable_stations && selectedPin.reachable_stations.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">関連駅</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedPin.reachable_stations.map((station, i) => (
                    <span
                      key={i}
                      className="inline-block px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded"
                    >
                      {station}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 編集フォーム */}
        {editingPin && (
          <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ピンを編集
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  メモ
                </label>
                <textarea
                  value={editingPin.notes || ''}
                  onChange={(e) => setEditingPin({ ...editingPin, notes: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  タグ（カンマ区切り）
                </label>
                <input
                  type="text"
                  value={editingPin.tags?.join(', ') || ''}
                  onChange={(e) => setEditingPin({
                    ...editingPin,
                    tags: e.target.value.split(',').map(t => t.trim()).filter(t => t)
                  })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div className="flex gap-4">
                <button
                  onClick={() => updatePin(editingPin)}
                  className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition"
                >
                  保存
                </button>
                <button
                  onClick={() => setEditingPin(null)}
                  className="bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md transition"
                >
                  キャンセル
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}