/**
 * QRスキャン機能
 * BarcodeDetector (Chrome/Android) 対応 + jsQR フォールバック (iOS Safari/Firefox 対応)
 */
const Scanner = {
  _stream: null,
  _interval: null,
  _detecting: false,
  _frameCount: 0,
  _canvas: null,
  _ctx: null,

  _log(msg) {
    console.log("[Scanner]", msg);
    const el = document.getElementById("scan-debug");
    if (el) {
      const time = new Date().toLocaleTimeString("ja-JP");
      el.innerHTML += `<div>${time} ${msg}</div>`;
      el.scrollTop = el.scrollHeight;
    }
  },

  async start(elementId, onResult) {
    this._frameCount = 0;
    const dbg = document.getElementById("scan-debug");
    if (dbg) dbg.innerHTML = "";

    const hasNative = "BarcodeDetector" in window;
    const hasJsQR = typeof jsQR === "function";

    this._log("起動開始...");
    this._log("BarcodeDetector: " + (hasNative ? "✅ 対応" : "❌ 非対応"));
    this._log("jsQR フォールバック: " + (hasJsQR ? "✅ 利用可" : "❌ 未ロード"));
    this._log("getUserMedia: " + (navigator.mediaDevices ? "✅ 対応" : "❌ 非対応"));

    const container = document.getElementById(elementId);
    if (!container) {
      this._log("❌ #" + elementId + " が見つかりません");
      return false;
    }

    // ビデオ要素を挿入
    const video = document.createElement("video");
    video.playsInline = true;
    video.muted = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("autoplay", "");
    video.style.cssText = "width:100%;height:auto;display:block;border-radius:8px;background:#000";
    container.innerHTML = "";
    container.appendChild(video);

    // カメラ権限取得
    this._log("カメラ権限リクエスト中...");
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }
      });
      this._log("✅ カメラ権限OK");
    } catch (e) {
      this._log("❌ カメラエラー: " + e.name + " - " + e.message);
      container.innerHTML =
        `<div style="padding:24px;text-align:center;color:#e53e3e;background:#1a202c;border-radius:8px">
          <div style="font-size:32px;margin-bottom:8px">🚫</div>
          <div style="font-weight:600">カメラへのアクセスを許可してください</div>
          <div style="font-size:12px;margin-top:8px;color:#a0aec0">${e.name}: ${e.message}</div>
        </div>`;
      return false;
    }

    video.srcObject = this._stream;
    try {
      await video.play();
      this._log("✅ カメラ映像開始 " + video.videoWidth + "x" + video.videoHeight);
    } catch (e) {
      this._log("❌ video.play() 失敗: " + e.message);
    }

    // BarcodeDetector ネイティブ対応
    if (hasNative) {
      // サポートされているフォーマットを確認してから初期化
      let formats = ["qr_code"];
      try {
        const supported = await BarcodeDetector.getSupportedFormats();
        const extra = ["code_128", "code_39", "ean_13", "data_matrix"].filter(f => supported.includes(f));
        formats = ["qr_code", ...extra];
      } catch (_) {}
      const detector = new BarcodeDetector({ formats });
      this._log("✅ BarcodeDetector で QR検出ループ開始 (200ms間隔) formats:" + formats.join(","));

      this._interval = setInterval(async () => {
        if (this._detecting || video.readyState < 2 || video.paused) return;
        this._detecting = true;
        this._frameCount++;
        if (this._frameCount % 15 === 0) {
          this._log("スキャン中... " + this._frameCount + "フレーム処理済");
        }
        try {
          const codes = await detector.detect(video);
          if (codes.length > 0) {
            const value = codes[0].rawValue;
            this._log("🎉 QR検出! " + value);
            clearInterval(this._interval);
            this._interval = null;
            this.beep();
            await this.stop();
            onResult(value);
          }
        } catch (e) {
          this._log("detect()エラー: " + e.message);
        }
        this._detecting = false;
      }, 200);

      return true;
    }

    // jsQR フォールバック (iOS Safari / Firefox など)
    if (hasJsQR) {
      this._canvas = document.createElement("canvas");
      this._ctx = this._canvas.getContext("2d", { willReadFrequently: true });
      this._log("✅ jsQR フォールバックで QR検出ループ開始 (200ms間隔)");

      this._interval = setInterval(() => {
        if (this._detecting || video.readyState < 2 || video.paused) return;
        if (video.videoWidth === 0) return;
        this._detecting = true;
        this._frameCount++;
        if (this._frameCount % 15 === 0) {
          this._log("スキャン中(jsQR)... " + this._frameCount + "フレーム処理済");
        }
        try {
          // 640px 幅にリサイズして処理速度を上げる
          const scale = Math.min(1, 640 / video.videoWidth);
          const w = Math.floor(video.videoWidth * scale);
          const h = Math.floor(video.videoHeight * scale);
          this._canvas.width = w;
          this._canvas.height = h;
          this._ctx.drawImage(video, 0, 0, w, h);
          const imageData = this._ctx.getImageData(0, 0, w, h);
          const result = jsQR(imageData.data, w, h, { inversionAttempts: "attemptBoth" });
          if (result) {
            const value = result.data;
            this._log("🎉 QR検出(jsQR)! " + value);
            clearInterval(this._interval);
            this._interval = null;
            this.beep();
            this.stop();
            onResult(value);
          }
        } catch (e) {
          this._log("jsQR エラー: " + e.message);
        }
        this._detecting = false;
      }, 200);

      return true;
    }

    // どちらも非対応
    this._log("❌ QR検出非対応ブラウザ → 手動入力を使用してください");
    return true;
  },

  async stop() {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = null;
    }
    this._detecting = false;
    if (this._stream) {
      this._stream.getTracks().forEach(t => t.stop());
      this._stream = null;
    }
    this._canvas = null;
    this._ctx = null;
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
