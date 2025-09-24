export interface LocalPin {
  id: string;
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
  source: 'local'; // ローカル保存であることを示すフラグ
}

const LOCAL_PINS_KEY = 'a2a_estate_local_pins';

export class LocalPinManager {
  // ローカルピンを全て取得
  static getLocalPins(): LocalPin[] {
    try {
      const stored = localStorage.getItem(LOCAL_PINS_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to load local pins:', error);
      return [];
    }
  }

  // ローカルピンを保存
  static saveLocalPin(pinData: {
    station_name: string;
    line_name?: string;
    coord_lat: number;
    coord_lon: number;
    conversation_context?: string;
    notes?: string;
    tags?: string[];
    nearby_places?: any;
    reachable_stations?: any[];
    average_rent?: number;
  }): LocalPin {
    const pins = this.getLocalPins();

    // 既に同じ駅が保存されているかチェック
    const existingPin = pins.find(pin =>
      pin.station_name === pinData.station_name &&
      Math.abs(pin.coord_lat - pinData.coord_lat) < 0.001 &&
      Math.abs(pin.coord_lon - pinData.coord_lon) < 0.001
    );

    if (existingPin) {
      throw new Error('この駅は既に保存されています');
    }

    const newPin: LocalPin = {
      id: `local_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`,
      ...pinData,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      source: 'local'
    };

    pins.push(newPin);

    try {
      localStorage.setItem(LOCAL_PINS_KEY, JSON.stringify(pins));
      return newPin;
    } catch (error) {
      console.error('Failed to save local pin:', error);
      throw new Error('ローカルストレージへの保存に失敗しました');
    }
  }

  // ローカルピンを更新
  static updateLocalPin(pinId: string, updates: Partial<Pick<LocalPin, 'notes' | 'tags'>>): LocalPin | null {
    const pins = this.getLocalPins();
    const pinIndex = pins.findIndex(pin => pin.id === pinId);

    if (pinIndex === -1) {
      return null;
    }

    pins[pinIndex] = {
      ...pins[pinIndex],
      ...updates,
      updated_at: new Date().toISOString()
    };

    try {
      localStorage.setItem(LOCAL_PINS_KEY, JSON.stringify(pins));
      return pins[pinIndex];
    } catch (error) {
      console.error('Failed to update local pin:', error);
      throw new Error('ローカルピンの更新に失敗しました');
    }
  }

  // ローカルピンを削除
  static deleteLocalPin(pinId: string): boolean {
    const pins = this.getLocalPins();
    const filteredPins = pins.filter(pin => pin.id !== pinId);

    if (filteredPins.length === pins.length) {
      return false; // ピンが見つからなかった
    }

    try {
      localStorage.setItem(LOCAL_PINS_KEY, JSON.stringify(filteredPins));
      return true;
    } catch (error) {
      console.error('Failed to delete local pin:', error);
      throw new Error('ローカルピンの削除に失敗しました');
    }
  }

  // 全てのローカルピンを削除
  static clearLocalPins(): void {
    try {
      localStorage.removeItem(LOCAL_PINS_KEY);
    } catch (error) {
      console.error('Failed to clear local pins:', error);
    }
  }

  // ローカルピンの数を取得
  static getLocalPinCount(): number {
    return this.getLocalPins().length;
  }

  // 特定の駅が既に保存されているかチェック
  static isPinSaved(stationName: string, lat: number, lng: number): boolean {
    const pins = this.getLocalPins();
    return pins.some(pin =>
      pin.station_name === stationName &&
      Math.abs(pin.coord_lat - lat) < 0.001 &&
      Math.abs(pin.coord_lon - lng) < 0.001
    );
  }

  // ローカルピンをサーバーに同期（ログイン時）
  static async syncLocalPinsToServer(accessToken: string, apiBaseUrl: string): Promise<{
    success: number;
    failed: number;
    errors: string[];
  }> {
    const localPins = this.getLocalPins();
    if (localPins.length === 0) {
      return { success: 0, failed: 0, errors: [] };
    }

    let success = 0;
    let failed = 0;
    const errors: string[] = [];

    for (const pin of localPins) {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/pins/`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            station_name: pin.station_name,
            line_name: pin.line_name,
            coord_lat: pin.coord_lat,
            coord_lon: pin.coord_lon,
            conversation_context: pin.conversation_context,
            notes: pin.notes,
            tags: pin.tags,
            nearby_places: pin.nearby_places,
            reachable_stations: pin.reachable_stations,
            average_rent: pin.average_rent
          })
        });

        if (response.ok) {
          success++;
        } else if (response.status === 400) {
          // 既に存在する場合は成功とみなす
          success++;
        } else {
          failed++;
          errors.push(`${pin.station_name}: サーバーエラー`);
        }
      } catch (error) {
        failed++;
        errors.push(`${pin.station_name}: ネットワークエラー`);
      }
    }

    return { success, failed, errors };
  }
}