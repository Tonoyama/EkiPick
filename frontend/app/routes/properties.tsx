import type { Route } from "./+types/properties";
import { useState, useEffect } from "react";
import api from "../lib/api";
import MapLeaflet from "../components/MapLeaflet";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "物件検索 | A2A Estate" },
    { name: "description", content: "通勤時間を考慮した物件検索" },
  ];
}

interface Property {
  id: number;
  title: string;
  price: number;
  location: string;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  property_type: string;
  status: string;
}

interface CommuteTime {
  address: string;
  time_minutes: number;
  fare: number;
}

export default function Properties() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [savedProperties, setSavedProperties] = useState<any[]>([]);
  const [workplaceAddress, setWorkplaceAddress] = useState("");
  const [maxCommuteTime, setMaxCommuteTime] = useState(60);
  const [loading, setLoading] = useState(false);
  const [commuteResults, setCommuteResults] = useState<Map<number, CommuteTime>>(new Map());
  const [activeTab, setActiveTab] = useState<"search" | "saved">("search");

  // 物件一覧を取得
  useEffect(() => {
    // クライアントサイドでのみ実行
    if (typeof window !== 'undefined') {
      loadProperties();
      loadSavedProperties();
    }
  }, []);

  const loadProperties = async () => {
    if (typeof window === 'undefined') return;
    try {
      setLoading(true);
      const data = await api.property.getProperties({ limit: 50 });
      setProperties(data);
    } catch (error) {
      console.error("Failed to load properties:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadSavedProperties = async () => {
    if (typeof window === 'undefined') return;
    try {
      const data = await api.property.getSavedProperties();
      setSavedProperties(data);
    } catch (error) {
      console.error("Failed to load saved properties:", error);
    }
  };

  // 通勤時間を計算
  const calculateCommuteTimes = async () => {
    if (!workplaceAddress || properties.length === 0) return;

    setLoading(true);
    const results = new Map<number, CommuteTime>();

    try {
      // 各物件への通勤時間を計算
      for (const property of properties) {
        try {
          const commuteData = await api.commute.calculateCommuteTime({
            from_address: property.location,
            to_address: workplaceAddress,
            start_time: "2025-09-22T08:30:00",
          });

          if (commuteData?.routes?.best_route) {
            results.set(property.id, {
              address: property.location,
              time_minutes: commuteData.routes.best_route.time_minutes,
              fare: commuteData.routes.best_route.total_fare,
            });
          }
        } catch (error) {
          console.error(`Failed to calculate commute for property ${property.id}:`, error);
        }
      }

      setCommuteResults(results);

      // 検索履歴を保存
      await api.search.saveSearchHistory({
        search_type: "commute_search",
        search_params: {
          workplace: workplaceAddress,
          max_time: maxCommuteTime,
        },
        results_count: results.size,
      });
    } catch (error) {
      console.error("Failed to calculate commute times:", error);
    } finally {
      setLoading(false);
    }
  };

  // 物件を保存
  const saveProperty = async (property: Property) => {
    try {
      const commuteData = commuteResults.get(property.id);
      await api.property.saveProperty(
        property.id,
        `通勤時間: ${commuteData?.time_minutes || "未計算"}分`,
        commuteData
      );
      await loadSavedProperties();
      alert("物件を保存しました");
    } catch (error) {
      console.error("Failed to save property:", error);
      alert("物件の保存に失敗しました");
    }
  };

  // 保存した物件を削除
  const removeSavedProperty = async (propertyId: number) => {
    try {
      await api.property.removeSavedProperty(propertyId);
      await loadSavedProperties();
      alert("保存した物件を削除しました");
    } catch (error) {
      console.error("Failed to remove property:", error);
      alert("物件の削除に失敗しました");
    }
  };

  // フィルタリング
  const filteredProperties = properties.filter((property) => {
    const commuteTime = commuteResults.get(property.id);
    if (!commuteTime) return true; // 通勤時間未計算の物件も表示
    return commuteTime.time_minutes <= maxCommuteTime;
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          物件検索
        </h1>

        {/* タブ */}
        <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab("search")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "search"
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
              }`}
            >
              物件検索 ({filteredProperties.length})
            </button>
            <button
              onClick={() => setActiveTab("saved")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "saved"
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
              }`}
            >
              保存した物件 ({savedProperties.length})
            </button>
          </nav>
        </div>

        {activeTab === "search" && (
          <>
            {/* 地図表示 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6 overflow-hidden">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  物件マップ
                </h2>
              </div>
              <div style={{ height: '400px' }}>
                <MapLeaflet
                  center={{ lat: 35.6762, lng: 139.6503 }}
                  zoom={11}
                  markers={filteredProperties.map(property => ({
                    position: {
                      lat: 35.6762 + (Math.random() - 0.5) * 0.1,
                      lng: 139.6503 + (Math.random() - 0.5) * 0.1
                    },
                    title: property.title,
                    info: `${property.location} - ¥${property.price.toLocaleString()}/月`
                  }))}
                  height="400px"
                  onMarkerClick={(marker) => {
                    console.log('Property marker clicked:', marker);
                  }}
                />
              </div>
            </div>

            {/* 検索条件 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                通勤時間で絞り込み
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    勤務地の住所
                  </label>
                  <input
                    type="text"
                    value={workplaceAddress}
                    onChange={(e) => setWorkplaceAddress(e.target.value)}
                    placeholder="例: 東京駅"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    最大通勤時間（分）
                  </label>
                  <input
                    type="number"
                    value={maxCommuteTime}
                    onChange={(e) => setMaxCommuteTime(Number(e.target.value))}
                    min="10"
                    max="120"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={calculateCommuteTimes}
                    disabled={!workplaceAddress || loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition"
                  >
                    {loading ? "計算中..." : "通勤時間を計算"}
                  </button>
                </div>
              </div>
            </div>

            {/* 物件リスト */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProperties.map((property) => {
                const commuteTime = commuteResults.get(property.id);
                const isSaved = savedProperties.some(p => p.id === property.id);

                return (
                  <div
                    key={property.id}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition"
                  >
                    <div className="p-6">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        {property.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-300 text-sm mb-2">
                        📍 {property.location}
                      </p>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                          ¥{property.price.toLocaleString()}
                        </span>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          /月
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 dark:text-gray-300 mb-3">
                        <div>🛏 {property.bedrooms}部屋</div>
                        <div>🚿 {property.bathrooms}バス</div>
                        <div>📐 {property.area_sqft}㎡</div>
                        <div>🏠 {property.property_type}</div>
                      </div>

                      {commuteTime && (
                        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3 mb-3">
                          <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            通勤時間
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-lg font-bold text-green-600 dark:text-green-400">
                              {commuteTime.time_minutes}分
                            </span>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              運賃: ¥{commuteTime.fare.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => saveProperty(property)}
                        disabled={isSaved}
                        className={`w-full py-2 px-4 rounded-md font-medium transition ${
                          isSaved
                            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                            : "bg-green-600 hover:bg-green-700 text-white"
                        }`}
                      >
                        {isSaved ? "保存済み" : "物件を保存"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {activeTab === "saved" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {savedProperties.map((saved) => (
              <div
                key={saved.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition"
              >
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                    {saved.title}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300 text-sm mb-2">
                    📍 {saved.location}
                  </p>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      ¥{saved.price.toLocaleString()}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      /月
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 dark:text-gray-300 mb-3">
                    <div>🛏 {saved.bedrooms}部屋</div>
                    <div>🚿 {saved.bathrooms}バス</div>
                    <div>📐 {saved.area_sqft}㎡</div>
                    <div>🏠 {saved.property_type}</div>
                  </div>

                  {saved.commute_data && (
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-3 mb-3">
                      <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        通勤時間
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-lg font-bold text-green-600 dark:text-green-400">
                          {saved.commute_data.time_minutes}分
                        </span>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          運賃: ¥{saved.commute_data.fare.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  )}

                  {saved.notes && (
                    <div className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                      📝 {saved.notes}
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={() => removeSavedProperty(saved.id)}
                      className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-md font-medium transition"
                    >
                      削除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}