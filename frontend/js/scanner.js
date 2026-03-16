/**
 * バーコード/QRスキャン機能
 * html5-qrcode ライブラリを使用
 */
const Scanner = {
  _instance: null,
  _scanning: false,
  _onResult: null,

  async start(elementId, onResult) {
    this._onResult = onResult;

    if (!window.Html5Qrcode) {
      console.warn("Html5Qrcode が読み込まれていません");
      return false;
    }

    try {
      if (this._instance) {
        await this.stop();
      }
      this._instance = new Html5Qrcode(elementId, { verbose: false });

      const config = {
        fps: 10,
        aspectRatio: 1.333,
      };

      await this._instance.start(
        { facingMode: "environment" },
        config,
        (decodedText) => {
          if (this._onResult) {
            this._scanning = true;
            this._onResult(decodedText);
          }
        },
        () => {} // エラーは無視（スキャン試行中のエラー）
      );
      return true;
    } catch (e) {
      console.error("スキャナー起動失敗:", e);
      return false;
    }
  },

  async stop() {
    if (this._instance) {
      try {
        await this._instance.stop();
        this._instance.clear();
      } catch (e) {
        // ignore
      }
      this._instance = null;
    }
    this._scanning = false;
  },

  beep() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.2);
    } catch (e) {}
  },
};
