/**
 * QRスキャン機能
 * CDN不要 - getUserMedia + BarcodeDetector (Android Chrome標準) で実装
 */
const Scanner = {
  _stream: null,
  _interval: null,
  _detecting: false,
  _frameCount: 0,

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

    this._log("起動開始...");
    this._log("BarcodeDetector: " + ("BarcodeDetector" in window ? "✅ 対応" : "❌ 非対応"));
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

    // BarcodeDetector 非対応端末の対応
    if (!("BarcodeDetector" in window)) {
      this._log("❌ BarcodeDetector非対応 → 手動入力を使用してください");
      return true;
    }

    const detector = new BarcodeDetector({ formats: ["qr_code"] });
    this._log("✅ QR検出ループ開始 (300ms間隔)");

    this._interval = setInterval(async () => {
      if (this._detecting || video.readyState < 2 || video.paused) return;
      this._detecting = true;
      this._frameCount++;
      if (this._frameCount % 10 === 0) {
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
    }, 300);

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
