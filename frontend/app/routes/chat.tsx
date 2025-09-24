import type { Route } from "./+types/chat";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useLocation, useNavigate, useBlocker } from "react-router";
import MapLeaflet from "../components/MapLeaflet";
import { useAuth } from "../contexts/AuthContext";
import { LocalPinManager } from "~/utils/localPins";

interface Message {
  id: string;
  agent: string;
  agent_name: string;
  content: string;
  timestamp: Date;
  type: 'conversation_start' | 'agent_response' | 'conversation_complete' | 'user_message';
  isStreaming?: boolean;
  displayedContent?: string;
  isVisible?: boolean;
}

export function meta({}: Route.MetaArgs) {
  return [
    { title: "エージェント会話 - 不動産検索" },
    { name: "description", content: "エージェント同士の会話" },
  ];
}

export default function Chat() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [additionalRequest, setAdditionalRequest] = useState("");
  const [showAdditionalRequest, setShowAdditionalRequest] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const hasInitializedRef = useRef(false);
  const typewriterTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const messageQueue = useRef<Array<{ id: string; text: string }>>([]);
  const isProcessingQueue = useRef(false);

  const initialRequest = location.state?.request;

  // ページ離脱の確認
  const shouldBlockNavigation = useCallback(() => {
    // 会話中またはメッセージがある場合はブロック
    return isStreaming || messages.length > 0;
  }, [isStreaming, messages.length]);

  // React Routerのナビゲーションをブロック
  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    return shouldBlockNavigation() && currentLocation.pathname !== nextLocation.pathname;
  });

  useEffect(() => {
    if (blocker.state === "blocked") {
      const confirmExit = window.confirm(
        "チャットを終了しますか？\n現在のセッションは保存されません。"
      );
      if (confirmExit) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker]);

  // ブラウザの戻るボタン、タブを閉じる、URL直接変更の検知
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (shouldBlockNavigation()) {
        e.preventDefault();
        e.returnValue = "チャットを終了しますか？現在のセッションは保存されません。";
        return e.returnValue;
      }
    };

    // popstateイベント（戻る/進むボタン）の処理
    const handlePopState = (e: PopStateEvent) => {
      if (shouldBlockNavigation()) {
        const confirmExit = window.confirm(
          "チャットを終了しますか？\n現在のセッションは保存されません。"
        );
        if (!confirmExit) {
          // 戻るをキャンセル
          window.history.pushState(null, "", window.location.href);
        }
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("popstate", handlePopState);

    // 履歴にエントリを追加（戻るボタン検知用）
    window.history.pushState(null, "", window.location.href);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("popstate", handlePopState);
    };
  }, [shouldBlockNavigation]);

  useEffect(() => {
    if (!initialRequest) {
      navigate("/");
      return;
    }
    // 初回のみ実行
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      startConversation(initialRequest);
    }
  }, [initialRequest, navigate]);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
    return () => clearTimeout(timeoutId);
  }, [messages.length]);

  const startTypewriter = (messageId: string, fullText: string) => {
    // タイプライター開始時にメッセージを表示状態にする
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, isVisible: true }
        : msg
    ));

    let currentIndex = 0;
    const typeSpeed = 50; // milliseconds per character

    const typeWriter = () => {
      if (currentIndex < fullText.length) {
        setMessages(prev => prev.map(msg =>
          msg.id === messageId
            ? { ...msg, displayedContent: fullText.slice(0, currentIndex + 1) }
            : msg
        ));
        currentIndex++;
        const timeout = setTimeout(typeWriter, typeSpeed);
        typewriterTimeouts.current.set(messageId, timeout);
      } else {
        // タイプライター完了時にisStreamingをfalseにする
        setMessages(prev => prev.map(msg =>
          msg.id === messageId
            ? { ...msg, isStreaming: false, displayedContent: fullText }
            : msg
        ));
        typewriterTimeouts.current.delete(messageId);
        // 次のメッセージを処理
        processNextMessage();
      }
    };

    typeWriter();
  };

  const processNextMessage = () => {
    if (messageQueue.current.length > 0) {
      const nextMessage = messageQueue.current.shift();
      if (nextMessage) {
        startTypewriter(nextMessage.id, nextMessage.text);
      } else {
        isProcessingQueue.current = false;
      }
    } else {
      isProcessingQueue.current = false;
    }
  };

  const queueTypewriterMessage = (messageId: string, fullText: string) => {
    messageQueue.current.push({ id: messageId, text: fullText });

    if (!isProcessingQueue.current) {
      isProcessingQueue.current = true;
      processNextMessage();
    }
  };

  const clearTypewriter = (messageId: string) => {
    const timeout = typewriterTimeouts.current.get(messageId);
    if (timeout) {
      clearTimeout(timeout);
      typewriterTimeouts.current.delete(messageId);
    }
  };

  useEffect(() => {
    return () => {
      // クリーンアップ
      typewriterTimeouts.current.forEach((timeout) => clearTimeout(timeout));
      typewriterTimeouts.current.clear();
      messageQueue.current = [];
      isProcessingQueue.current = false;
    };
  }, []);


  const startConversation = async (request: string) => {
    setIsStreaming(true);
    setShowAdditionalRequest(false);
    abortControllerRef.current = new AbortController();

    // ユーザーのメッセージを画面に表示
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      agent: 'user',
      agent_name: 'あなた',
      content: request,
      timestamp: new Date(),
      type: 'user_message',
      isVisible: true
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      // APIベースURLを取得
      const API_BASE_URL = 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';

      const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: request,
          session_id: sessionId
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              switch (data.type) {
                case 'conversation_start':
                  const startMessage: Message = {
                    id: `start_${Date.now()}`,
                    agent: 'system',
                    agent_name: 'システム',
                    content: data.message,
                    timestamp: new Date(),
                    type: data.type,
                    isStreaming: true,
                    displayedContent: '',
                    isVisible: false
                  };
                  setMessages(prev => [...prev, startMessage]);
                  queueTypewriterMessage(startMessage.id, data.message);
                  break;

                case 'agent_response':
                  // 各エージェントの完了した回答をタイプライター効果で表示
                  const agentMessage: Message = {
                    id: `${data.agent}_${Date.now()}_${Math.random()}`,
                    agent: data.agent,
                    agent_name: data.agent_name,
                    content: data.message,
                    timestamp: new Date(),
                    type: data.type,
                    isStreaming: true,
                    displayedContent: '',
                    isVisible: false
                  };
                  setMessages(prev => [...prev, agentMessage]);
                  queueTypewriterMessage(agentMessage.id, data.message);
                  break;

                case 'conversation_complete':
                  const endMessage: Message = {
                    id: `end_${Date.now()}`,
                    agent: 'system',
                    agent_name: 'システム',
                    content: data.message,
                    timestamp: new Date(),
                    type: data.type,
                    isStreaming: true,
                    displayedContent: '',
                    isVisible: false
                  };
                  setMessages(prev => [...prev, endMessage]);
                  queueTypewriterMessage(endMessage.id, data.message);
                  break;

                case 'pin':
                  // ピンデータを受信して地図に追加
                  const newPin = {
                    position: { lat: data.lat, lng: data.lon },
                    title: data.name,
                    info: 'チャットからのピン'
                  };
                  setRealtimePins(prev => [...prev, newPin]);
                  break;
              }
            } catch (e) {
              console.error('Error parsing message:', e);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Streaming error:', error);
      }
    } finally {
      setIsStreaming(false);
      setShowAdditionalRequest(true);
    }
  };

  const stopConversation = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    // 進行中のタイプライター効果をすべて停止
    typewriterTimeouts.current.forEach((timeout) => clearTimeout(timeout));
    typewriterTimeouts.current.clear();
    // キューとプロセシング状態をリセット
    messageQueue.current = [];
    isProcessingQueue.current = false;
    setIsStreaming(false);
    setShowAdditionalRequest(true);
  };

  const handleAdditionalRequest = (e: React.FormEvent) => {
    e.preventDefault();
    if (additionalRequest.trim()) {
      startConversation(additionalRequest);
      setAdditionalRequest("");
    }
  };

  const getAgentInfo = (agent: string) => {
    const agentMap: Record<string, {name: string, emoji: string, color: string}> = {
      'real_estate_agent': { name: '不動産エージェント', emoji: '🏢', color: 'bg-green-500' },
      'real_estate_response': { name: '不動産エージェント', emoji: '💁‍♀️', color: 'bg-green-500' },
      'concierge_agent': { name: 'コンシェルジュエージェント', emoji: '🤵', color: 'bg-blue-500' },
      'summary_agent': { name: 'まとめエージェント', emoji: '📋', color: 'bg-purple-500' },
      'system': { name: 'システム', emoji: '⚙️', color: 'bg-gray-500' },
      'user': { name: 'あなた', emoji: '👤', color: 'bg-indigo-500' },
    };

    return agentMap[agent] || { name: 'エージェント', emoji: '💁‍♀️', color: 'bg-orange-500' };
  };

  // 物件のサンプルマーカー（実際の物件に基づいて動的に更新可能）
  const [mapMarkers, setMapMarkers] = useState([
    {
      position: { lat: 35.689487, lng: 139.691706 }, // 新宿駅
      title: "新宿駅",
      info: "JR・私鉄・地下鉄 ターミナル駅"
    }
  ]);

  // リアルタイムピンの状態管理
  const [realtimePins, setRealtimePins] = useState<Array<{
    position: { lat: number; lng: number };
    title: string;
    info: string;
  }>>([]);


  // ピン保存処理
  const savePin = async (markerData: any) => {
    if (!markerData) return;

    if (isAuthenticated) {
      // ログイン済みの場合はサーバーに保存
      try {
        const API_BASE_URL = typeof window !== 'undefined'
          ? (window as any).__API_BASE_URL__ || 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app'
          : 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';

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
            station_name: markerData.title,
            coord_lat: markerData.position.lat,
            coord_lon: markerData.position.lng,
            conversation_context: 'チャットから保存',
            notes: `${markerData.info || ''}`
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
          station_name: markerData.title,
          coord_lat: markerData.position.lat,
          coord_lon: markerData.position.lng,
          conversation_context: 'チャットから保存',
          notes: `${markerData.info || ''}`
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

  // メッセージから物件情報を抽出してマーカーを更新する処理
  useEffect(() => {
    // AIの返答から物件情報や場所を抽出する処理を追加可能
    // 例: 「新宿駅周辺の物件」→ マーカーを追加
  }, [messages]);

  // モバイル表示用の状態管理
  const [showMap, setShowMap] = useState(false);

  return (
    <div className="h-screen flex flex-col lg:flex-row bg-gray-100 dark:bg-gray-900">
      {/* モバイル用タブ切り替え */}
      <div className="lg:hidden flex bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setShowMap(false)}
          className={`flex-1 py-3 px-4 text-sm font-medium ${
            !showMap
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 dark:text-gray-400'
          }`}
        >
          💬 チャット
        </button>
        <button
          onClick={() => setShowMap(true)}
          className={`flex-1 py-3 px-4 text-sm font-medium ${
            showMap
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 dark:text-gray-400'
          }`}
        >
          🗺️ マップ
        </button>
      </div>

      {/* 地図エリア */}
      <div className={`
        ${showMap ? 'flex' : 'hidden'}
        lg:flex lg:w-1/2 flex-1 lg:flex-initial
        bg-gray-200 dark:bg-gray-800 relative
      `}>
        <div className="absolute top-4 left-4 right-4 lg:right-auto bg-white dark:bg-gray-700 rounded-lg shadow-lg p-3 lg:p-4 z-10 max-w-xs">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1 lg:mb-2 text-sm lg:text-base">🗺️ 物件マップ</h3>
          <p className="text-xs lg:text-sm text-gray-600 dark:text-gray-300">検索条件に合った物件が表示されます</p>
        </div>
        <MapLeaflet
          center={{ lat: 35.689487, lng: 139.691706 }}
          zoom={13}
          markers={useMemo(() => [...mapMarkers, ...realtimePins], [mapMarkers, realtimePins])}
          height="100%"
          onMarkerClick={useMemo(() => (marker: any) => {
            console.log('Marker clicked:', marker);
          }, [])}
          onSavePin={savePin}
          isAuthenticated={true}
        />
      </div>

      {/* チャットエリア */}
      <div className={`
        ${!showMap ? 'flex' : 'hidden'}
        lg:flex lg:w-1/2 flex-1 flex-col
      `}>
        {/* ヘッダー */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3 lg:p-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h2 className="text-base lg:text-lg font-semibold text-gray-900 dark:text-white">エージェント会話</h2>
              <p className="text-xs lg:text-sm text-gray-600 dark:text-gray-300">
                {isStreaming ? "会話中..." : "会話待機中"}
              </p>
            </div>
            <button
              onClick={() => {
                if (shouldBlockNavigation()) {
                  const confirmExit = window.confirm(
                    "チャットを終了しますか？\n現在のセッションは保存されません。"
                  );
                  if (confirmExit) {
                    navigate("/");
                  }
                } else {
                  navigate("/");
                }
              }}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-sm lg:text-base"
            >
              ← 戻る
            </button>
          </div>
        </div>

        {/* メッセージエリア */}
        <div className="flex-1 overflow-y-auto p-3 lg:p-4 space-y-3 lg:space-y-4">
          {messages.filter(message => message.isVisible !== false).map((message) => {
            const agent = getAgentInfo(message.agent);
            const isUser = message.agent === 'user';

            return (
              <div key={message.id} className={`flex items-start space-x-2 lg:space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
                <div className={`${agent.color} text-white rounded-full w-7 h-7 lg:w-8 lg:h-8 flex items-center justify-center text-xs lg:text-sm flex-shrink-0`}>
                  {agent.emoji}
                </div>
                <div className="flex-1 max-w-[85%] lg:max-w-none">
                  <div className={`flex items-center space-x-1 lg:space-x-2 mb-1 ${isUser ? 'justify-end' : ''}`}>
                    <span className="font-medium text-gray-900 dark:text-white text-sm lg:text-base">{message.agent_name}</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <div className={`${isUser ? 'bg-indigo-100 dark:bg-indigo-900' : 'bg-white dark:bg-gray-700'} rounded-lg p-2 lg:p-3 shadow`}>
                    <p className="text-gray-900 dark:text-white whitespace-pre-wrap text-sm lg:text-base">
                      {message.isStreaming ? message.displayedContent : message.content}
                      {message.isStreaming && (
                        <span className="animate-pulse text-blue-500 ml-1">|</span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}

          {/* ストリーミング中のローディング表示 */}
          {isStreaming && (
            <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
              <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span>エージェントが考えています...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* コントロールエリア */}
        <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-3 lg:p-4">
          {isStreaming ? (
            <button
              onClick={stopConversation}
              className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
            >
              STOP - 会話を停止
            </button>
          ) : (
            showAdditionalRequest && (
              <form onSubmit={handleAdditionalRequest} className="space-y-2 lg:space-y-3">
                <textarea
                  value={additionalRequest}
                  onChange={(e) => setAdditionalRequest(e.target.value)}
                  className="w-full h-16 lg:h-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none text-sm lg:text-base"
                  placeholder="追加の要望があれば入力してください..."
                />
                <button
                  type="submit"
                  disabled={!additionalRequest.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition duration-200 text-sm lg:text-base"
                >
                  追加依頼を送信
                </button>
              </form>
            )
          )}
        </div>
      </div>

    </div>
  );
}