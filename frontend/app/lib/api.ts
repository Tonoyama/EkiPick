/**
 * API クライアント
 * バックエンドとの通信を管理
 */

// APIエンドポイントは常に本番環境を使用
// 開発環境でもlocalhostは使わない
const API_BASE_URL = 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';

// セッションIDをローカルストレージで管理
const SESSION_KEY = 'a2a_estate_session_id';

interface ApiError {
  detail: string;
  status?: number;
}

/**
 * APIリクエストのベース関数
 */
async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Request failed:', error);
    throw error;
  }
}

/**
 * セッション管理
 */
export const sessionApi = {
  /**
   * セッションIDを取得（なければ作成）
   */
  async getOrCreateSession(): Promise<string> {
    // ブラウザ環境でのみlocalStorageを使用
    if (typeof window === 'undefined') {
      throw new Error('Session management is only available in browser');
    }

    // ローカルストレージから取得
    let sessionId = localStorage.getItem(SESSION_KEY);

    if (!sessionId) {
      // 新しいセッションを作成
      const response = await apiRequest<{ id: string }>('/api/v1/sessions/', {
        method: 'POST',
        body: JSON.stringify({ data: {} }),
      });

      sessionId = response.id;
      localStorage.setItem(SESSION_KEY, sessionId);
    }

    return sessionId;
  },

  /**
   * セッション情報を取得
   */
  async getSession(sessionId: string) {
    return apiRequest(`/api/v1/sessions/${sessionId}`);
  },

  /**
   * セッションデータを更新
   */
  async updateSession(sessionId: string, data: any) {
    return apiRequest(`/api/v1/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
};

/**
 * 物件API
 */
export const propertyApi = {
  /**
   * 物件一覧を取得
   */
  async getProperties(params?: {
    skip?: number;
    limit?: number;
    property_type?: string;
    status?: string;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.property_type) queryParams.append('property_type', params.property_type);
    if (params?.status) queryParams.append('status', params.status);

    return apiRequest(`/api/v1/properties?${queryParams}`);
  },

  /**
   * 物件詳細を取得
   */
  async getProperty(id: number) {
    return apiRequest(`/api/v1/properties/${id}`);
  },

  /**
   * 物件を作成
   */
  async createProperty(property: any) {
    return apiRequest('/api/v1/properties', {
      method: 'POST',
      body: JSON.stringify(property),
    });
  },

  /**
   * 物件を保存（お気に入り）
   */
  async saveProperty(propertyId: number, notes?: string, commuteData?: any) {
    const sessionId = await sessionApi.getOrCreateSession();
    return apiRequest(`/api/v1/sessions/${sessionId}/saved-properties/${propertyId}`, {
      method: 'POST',
      body: JSON.stringify({ notes, commute_data: commuteData }),
    });
  },

  /**
   * 保存した物件一覧を取得
   */
  async getSavedProperties() {
    const sessionId = await sessionApi.getOrCreateSession();
    return apiRequest(`/api/v1/sessions/${sessionId}/saved-properties`);
  },

  /**
   * 保存した物件を削除
   */
  async removeSavedProperty(propertyId: number) {
    const sessionId = await sessionApi.getOrCreateSession();
    return apiRequest(`/api/v1/sessions/${sessionId}/saved-properties/${propertyId}`, {
      method: 'DELETE',
    });
  },
};

/**
 * 通勤時間API
 */
export const commuteApi = {
  /**
   * 住所から座標を取得
   */
  async geocode(address: string) {
    const params = new URLSearchParams({ address });
    return apiRequest(`/api/v1/commute/geocode?${params}`);
  },

  /**
   * 通勤時間を計算
   */
  async calculateCommuteTime(params: {
    from_address: string;
    to_address: string;
    start_time?: string;
    use_coordinates?: boolean;
  }) {
    const queryParams = new URLSearchParams();
    queryParams.append('from_address', params.from_address);
    queryParams.append('to_address', params.to_address);
    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.use_coordinates) queryParams.append('use_coordinates', 'true');

    const result = await apiRequest(`/api/v1/commute/time?${queryParams}`);

    // 履歴に保存
    if (result && result.routes?.best_route) {
      const sessionId = await sessionApi.getOrCreateSession();
      const bestRoute = result.routes.best_route;

      await apiRequest(`/api/v1/sessions/${sessionId}/commute-history`, {
        method: 'POST',
        body: JSON.stringify({
          from_address: params.from_address,
          to_address: params.to_address,
          from_coords: result.from_coordinates ?
            { lat: parseFloat(result.from_coordinates.split(',')[0]),
              lon: parseFloat(result.from_coordinates.split(',')[1]) } : {},
          to_coords: result.to_coordinates ?
            { lat: parseFloat(result.to_coordinates.split(',')[0]),
              lon: parseFloat(result.to_coordinates.split(',')[1]) } : {},
          commute_time: bestRoute.time_minutes,
          fare: bestRoute.total_fare,
          route_data: bestRoute,
        }),
      });
    }

    return result;
  },

  /**
   * 複数の目的地への通勤時間を一括計算
   */
  async batchCalculate(params: {
    from_address: string;
    to_addresses: string;
    start_time?: string;
  }) {
    const queryParams = new URLSearchParams();
    queryParams.append('from_address', params.from_address);
    queryParams.append('to_addresses', params.to_addresses);
    if (params.start_time) queryParams.append('start_time', params.start_time);

    return apiRequest(`/api/v1/commute/batch?${queryParams}`);
  },

  /**
   * 通勤時間でランキング
   */
  async ranking(params: {
    from_address: string;
    to_addresses: string;
    start_time?: string;
    sort_by?: 'time' | 'fare';
  }) {
    const queryParams = new URLSearchParams();
    queryParams.append('from_address', params.from_address);
    queryParams.append('to_addresses', params.to_addresses);
    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.sort_by) queryParams.append('sort_by', params.sort_by);

    return apiRequest(`/api/v1/commute/ranking?${queryParams}`);
  },

  /**
   * 通勤時間計算履歴を取得
   */
  async getHistory(limit: number = 10) {
    const sessionId = await sessionApi.getOrCreateSession();
    return apiRequest(`/api/v1/sessions/${sessionId}/commute-history?limit=${limit}`);
  },
};

/**
 * 検索履歴API
 */
export const searchApi = {
  /**
   * 検索履歴を保存
   */
  async saveSearchHistory(params: {
    search_type: string;
    search_params: any;
    results_count: number;
  }) {
    const sessionId = await sessionApi.getOrCreateSession();
    return apiRequest(`/api/v1/sessions/${sessionId}/search-history`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  /**
   * 検索履歴を取得
   */
  async getSearchHistory(limit: number = 10) {
    const sessionId = await sessionApi.getOrCreateSession();
    return apiRequest(`/api/v1/sessions/${sessionId}/search-history?limit=${limit}`);
  },
};

/**
 * 認証API
 */
export const authApi = {
  /**
   * 現在のユーザー情報を取得
   */
  async getMe() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    if (!token) {
      throw new Error('認証トークンが見つかりません');
    }

    return apiRequest('/api/v1/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
  },
};

// エクスポート
export default {
  session: sessionApi,
  property: propertyApi,
  commute: commuteApi,
  search: searchApi,
  auth: authApi,
};