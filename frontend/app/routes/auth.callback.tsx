import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useAuth } from "../contexts/AuthContext";
import type { Route } from "./+types/auth.callback";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "認証中... | A2A Estate" },
    { name: "description", content: "Googleアカウントで認証中" },
  ];
}

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleCallback } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const [hasProcessed, setHasProcessed] = useState(false);

  useEffect(() => {
    // Prevent duplicate processing (React Strict Mode or re-renders)
    if (hasProcessed) return;

    const processCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError(`認証エラー: ${errorParam}`);
        setIsProcessing(false);
        setTimeout(() => navigate("/"), 3000);
        return;
      }

      if (!code) {
        setError("認証コードが見つかりません");
        setIsProcessing(false);
        setTimeout(() => navigate("/"), 3000);
        return;
      }

      // Mark as processed immediately to prevent duplicate calls
      setHasProcessed(true);

      try {
        await handleCallback(code);
        // 成功したらホームページへリダイレクト
        navigate("/");
      } catch (err) {
        console.error("Authentication error:", err);
        setError("認証処理中にエラーが発生しました");
        setIsProcessing(false);
        setTimeout(() => navigate("/"), 3000);
      }
    };

    processCallback();
  }, [searchParams, navigate, handleCallback, hasProcessed]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 max-w-md w-full">
        {isProcessing ? (
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 mb-4">
              <svg
                className="animate-spin h-12 w-12 text-blue-600"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              認証処理中...
            </h2>
            <p className="text-gray-600 dark:text-gray-300">
              Googleアカウントで認証しています
            </p>
          </div>
        ) : error ? (
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 mb-4 bg-red-100 dark:bg-red-900 rounded-full">
              <svg
                className="h-8 w-8 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              認証エラー
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-4">{error}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              3秒後にホームページへ戻ります...
            </p>
          </div>
        ) : (
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 mb-4 bg-green-100 dark:bg-green-900 rounded-full">
              <svg
                className="h-8 w-8 text-green-600 dark:text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              認証成功！
            </h2>
            <p className="text-gray-600 dark:text-gray-300">
              リダイレクト中...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}