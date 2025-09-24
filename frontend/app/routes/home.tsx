import type { Route } from "./+types/home";
import { useState } from "react";
import { useNavigate } from "react-router";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "不動産エージェント検索" },
    { name: "description", content: "AIエージェントが不動産を探します" },
  ];
}

export default function Home() {
  const [workStation, setWorkStation] = useState("");
  const [maxCommuteTime, setMaxCommuteTime] = useState(30);
  const [rentBudget, setRentBudget] = useState(100000);
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (workStation.trim()) {
      const request = `職場の最寄り駅: ${workStation}, 通勤希望時間: ${maxCommuteTime}分以内, 家賃予算: ${rentBudget.toLocaleString()}円以内の賃貸物件を探しています。`;
      navigate("/chat", { state: { request } });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            🏠 不動産エージェント検索
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-8">
            コンシェルジュエージェントと不動産業者エージェントが協力して、あなたの理想の物件を見つけます
          </p>

          {/* Quick Links */}
          <div className="mb-8 grid grid-cols-2 gap-4">
            <a
              href="/hazard-map"
              className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow hover:shadow-lg transition-shadow"
            >
              <div className="text-2xl mb-2">🗺️</div>
              <div className="font-semibold text-gray-900 dark:text-white">災害リスクマップ</div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                物件の災害リスクを確認
              </div>
            </a>
            <a
              href="/explore"
              className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow hover:shadow-lg transition-shadow"
            >
              <div className="text-2xl mb-2">🔍</div>
              <div className="font-semibold text-gray-900 dark:text-white">物件を探索</div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                条件を指定して検索
              </div>
            </a>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                物件検索条件を入力してください
              </h3>

              {/* 職場の最寄り駅 */}
              <div>
                <label htmlFor="workStation" className="block text-left text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  職場の最寄り駅 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="workStation"
                  value={workStation}
                  onChange={(e) => setWorkStation(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="例：新宿駅"
                  required
                />
              </div>

              {/* 通勤希望時間 */}
              <div>
                <label htmlFor="maxCommuteTime" className="block text-left text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  通勤希望時間（最大）
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="range"
                    id="maxCommuteTime"
                    min="5"
                    max="120"
                    step="5"
                    value={maxCommuteTime}
                    onChange={(e) => setMaxCommuteTime(Number(e.target.value))}
                    className="flex-1"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 min-w-[60px]">
                    {maxCommuteTime}分
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  5分 〜 120分（2時間）
                </div>
              </div>

              {/* 家賃予算 */}
              <div>
                <label htmlFor="rentBudget" className="block text-left text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  家賃予算（月額）
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="range"
                    id="rentBudget"
                    min="50000"
                    max="500000"
                    step="10000"
                    value={rentBudget}
                    onChange={(e) => setRentBudget(Number(e.target.value))}
                    className="flex-1"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 min-w-[100px]">
                    {rentBudget.toLocaleString()}円
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  5万円 〜 50万円
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={!workStation.trim()}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition duration-200 shadow-lg"
            >
              エージェントに依頼する
            </button>
          </form>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="font-semibold text-blue-600 dark:text-blue-400 mb-2">🤵 コンシェルジュエージェント</div>
              <p>お客様のご要望を詳しくお聞きし、最適な条件を整理します</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="font-semibold text-green-600 dark:text-green-400 mb-2">🏢 不動産業者エージェント</div>
              <p>豊富な物件データベースから条件に合う物件を提案します</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
