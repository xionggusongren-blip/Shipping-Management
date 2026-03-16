/**
 * QRスキャン機能
 * CDN不要 - getUserMedia + BarcodeDetector (Android Chrome標準) で実装
 */
const Scanner = {
  _stream: null,
  _interval: null,
  _detecting: false,

  async start(elementId, onResult) {
    const container = document.getElementById(elementId);
    if (!container) {
      console.error("[Scanner] #" + elementId + " が見つかりません");
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
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }
      });
    } catch (e) {
      container.innerHTML =
        `<div style="padding:24px;text-align:center;color:#e53e3e;background:#1a202c;border-radius:8px">
          <div style="font-size:32px;margin-bottom:8px">🚫</div>
          <div style="font-weight:600">カメラへのアクセスを許可してください</div>
          <div style="font-size:12px;margin-top:8px;color:#a0aec0">${e.message}</div>
        </div>`;
      console.error("[Scanner] カメラ起動失敗:", e);
      return false;
    }

    video.srcObject = this._stream;
    try {
      await video.play();
    } catch (e) {
      console.error("[Scanner] video.play() 失敗:", e);
    }

    // BarcodeDetector 非対応端末の対応
    if (!("BarcodeDetector" in window)) {
      container.insertAdjacentHTML("beforeend",
        `<div style="padding:8px;text-align:center;color:#f6ad55;font-size:12px">
          ⚠ QR自動検出非対応。カメラは表示されています。手動入力をご利用ください。
        </div>`);
      console.warn("[Scanner] BarcodeDetector非対応");
      return true; // カメラ映像は表示する
    }

    const detector = new BarcodeDetector({ formats: ["qr_code"] });
    console.log("[Scanner] 検出開始");

    this._interval = setInterval(async () => {
      if (this._detecting || video.readyState < 2 || video.paused) return;
      this._detecting = true;
      try {
        const codes = await detector.detect(video);
        if (codes.length > 0) {
          const value = codes[0].rawValue;
          console.log("[Scanner] QR検出:", value);
          clearInterval(this._interval);
          this._interval = null;
          this.beep();
          await this.stop();
          onResult(value);
        }
      } catch (_) {}
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
