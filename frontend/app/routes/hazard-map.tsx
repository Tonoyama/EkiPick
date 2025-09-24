import { useState } from "react";
import type { Route } from "./+types/hazard-map";
import HazardMapLeaflet from "../components/HazardMapLeaflet";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "災害リスクマップ | A2A Estate" },
    { name: "description", content: "物件の災害リスクを地図上で確認" },
  ];
}

export default function HazardMapPage() {
  const [selectedLocation, setSelectedLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sampleProperties] = useState([
    {
      position: { lat: 35.6812, lng: 139.7671 },
      title: "東京駅前物件",
      info: "3LDK, 85㎡, 賃料 25万円",
    },
    {
      position: { lat: 35.6585, lng: 139.7454 },
      title: "渋谷駅前タワー",
      info: "2LDK, 65㎡, 賃料 20万円",
    },
    {
      position: { lat: 35.7102, lng: 139.8107 },
      title: "浅草観光エリア",
      info: "1LDK, 45㎡, 賃料 15万円",
    },
  ]);

  const handleLocationClick = (lat: number, lng: number) => {
    setSelectedLocation({ lat, lng });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement geocoding search
    console.log("Searching for:", searchQuery);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              災害リスクマップ
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              物件の災害リスクを地図上で確認できます
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="住所や駅名で検索..."
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            />
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              検索
            </button>
          </form>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col lg:flex-row" style={{ height: "calc(100vh - 200px)" }}>
        {/* Map Section */}
        <div className="flex-1">
          <HazardMapLeaflet
            markers={sampleProperties}
            height="100%"
            onLocationClick={handleLocationClick}
            showHazardControls={true}
          />
        </div>

        {/* Info Panel */}
        <div className="lg:w-96 bg-white dark:bg-gray-800 border-t lg:border-t-0 lg:border-l border-gray-200 dark:border-gray-700 overflow-y-auto">
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
              災害リスク情報
            </h2>

            {selectedLocation ? (
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <h3 className="font-medium text-blue-900 dark:text-blue-300 mb-2">
                    選択地点
                  </h3>
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    緯度: {selectedLocation.lat.toFixed(4)}
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    経度: {selectedLocation.lng.toFixed(4)}
                  </p>
                </div>

                <div className="text-sm text-gray-600 dark:text-gray-400">
                  ※ 地図上をクリックすると、その地点の災害リスク情報が表示されます
                </div>
              </div>
            ) : (
              <div className="text-gray-500 dark:text-gray-400">
                <p className="mb-4">地図上をクリックして災害リスクを確認してください</p>

                <div className="space-y-3">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                    使い方
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-start">
                      <span className="text-blue-600 mr-2">1.</span>
                      <span>右上のチェックボックスでハザードマップレイヤーを表示</span>
                    </div>
                    <div className="flex items-start">
                      <span className="text-blue-600 mr-2">2.</span>
                      <span>地図上の任意の地点をクリック</span>
                    </div>
                    <div className="flex items-start">
                      <span className="text-blue-600 mr-2">3.</span>
                      <span>ポップアップで災害リスク情報を確認</span>
                    </div>
                  </div>
                </div>

                <div className="mt-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <h4 className="font-medium text-yellow-900 dark:text-yellow-300 mb-2">
                    ⚠️ 注意事項
                  </h4>
                  <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                    <li>• 表示される情報は参考値です</li>
                    <li>• 最新の情報は自治体にご確認ください</li>
                    <li>• データは国土地理院提供のものです</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Property List */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              サンプル物件
            </h3>
            <div className="space-y-3">
              {sampleProperties.map((property, index) => (
                <div
                  key={index}
                  className="p-3 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                  onClick={() => setSelectedLocation(property.position)}
                >
                  <h4 className="font-medium text-gray-900 dark:text-white">
                    {property.title}
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {property.info}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}