/**
 * QRスキャン機能
 * BarcodeDetector (Chrome/Android) + jsQR (全ブラウザ) を並列で実行
 * 先に検出した方の結果を採用する
 */
const Scanner = {
  _stream: null,
  _intervals: [],   // BarcodeDetector と jsQR の両方を管理
  _detected: false, // 二重検出防止フラグ
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
    this._detected = false;
    this._intervals = [];
    const dbg = document.getElementById("scan-debug");
    if (dbg) dbg.innerHTML = "";

    const hasNative = "BarcodeDetector" in window;
    const hasJsQR = typeof jsQR === "function";

    this._log("起動開始...");
    this._log("BarcodeDetector: " + (hasNative ? "✅ 対応" : "❌ 非対応"));
    this._log("jsQR: " + (hasJsQR ? "✅ 利用可" : "❌ 未ロード"));
    this._log("getUserMedia: " + (navigator.mediaDevices ? "✅ 対応" : "❌ 非対応"));

    if (!navigator.mediaDevices) {
      this._log("❌ カメラ非対応環境です (HTTPS でアクセスしているか確認してください)");
      const container = document.getElementById(elementId);
      if (container) {
        container.innerHTML =
          `<div style="padding:24px;text-align:center;color:#e53e3e;background:#1a202c;border-radius:8px">
            <div style="font-size:32px;margin-bottom:8px">🚫</div>
            <div style="font-weight:600">カメラを使用できません</div>
            <div style="font-size:12px;margin-top:8px;color:#a0aec0">
              HTTPS でアクセスしてください<br>https://[PC-IP]:8443
            </div>
          </div>`;
      }
      return false;
    }

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
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        }
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

    // ビデオの準備を少し待つ
    await new Promise(resolve => setTimeout(resolve, 300));
    this._log("映像サイズ: " + video.videoWidth + "x" + video.videoHeight);

    const _onDetect = (value, engine) => {
      if (this._detected) return;
      this._detected = true;
      this._log("🎉 QR検出(" + engine + "): " + value);
      this._clearIntervals();
      this.beep();
      this.stop();
      onResult(value);
    };

    let started = false;

    // ── jsQR ループ（Canvas ベース・全ブラウザ対応）──
    if (hasJsQR) {
      this._canvas = document.createElement("canvas");
      this._ctx = this._canvas.getContext("2d", { willReadFrequently: true });
      let frameCount = 0;

      const jsqrInterval = setInterval(() => {
        if (this._detected) { clearInterval(jsqrInterval); return; }
        if (video.readyState < 2 || video.paused || video.videoWidth === 0) return;

        frameCount++;
        if (frameCount % 15 === 0) {
          this._log("jsQR スキャン中... " + frameCount + "フレーム");
        }
        try {
          const scale = Math.min(1, 640 / video.videoWidth);
          const w = Math.floor(video.videoWidth * scale);
          const h = Math.floor(video.videoHeight * scale);
          if (w === 0 || h === 0) return;
          this._canvas.width = w;
          this._canvas.height = h;
          this._ctx.drawImage(video, 0, 0, w, h);
          const imageData = this._ctx.getImageData(0, 0, w, h);
          const result = jsQR(imageData.data, w, h, { inversionAttempts: "attemptBoth" });
          if (result && result.data) {
            _onDetect(result.data, "jsQR");
          }
        } catch (e) {
          // エラーは無視して継続
        }
      }, 200);

      this._intervals.push(jsqrInterval);
      started = true;
      this._log("✅ jsQR ループ開始 (200ms)");
    }

    // ── BarcodeDetector ループ（Chrome/Android ネイティブ・より高速）──
    if (hasNative) {
      try {
        let formats = ["qr_code"];
        try {
          const supported = await BarcodeDetector.getSupportedFormats();
          const extra = ["code_128", "code_39", "ean_13", "data_matrix"].filter(f => supported.includes(f));
          formats = ["qr_code", ...extra];
        } catch (_) {}

        const detector = new BarcodeDetector({ formats });
        let frameCount = 0;

        const nativeInterval = setInterval(async () => {
          if (this._detected) { clearInterval(nativeInterval); return; }
          if (video.readyState < 2 || video.paused) return;

          frameCount++;
          if (frameCount % 15 === 0) {
            this._log("Native スキャン中... " + frameCount + "フレーム");
          }
          try {
            const codes = await detector.detect(video);
            if (codes.length > 0 && codes[0].rawValue) {
              _onDetect(codes[0].rawValue, "BarcodeDetector");
            }
          } catch (_) {}
        }, 200);

        this._intervals.push(nativeInterval);
        started = true;
        this._log("✅ BarcodeDetector ループ開始 formats:" + formats.join(","));
      } catch (e) {
        this._log("BarcodeDetector 初期化失敗: " + e.message);
      }
    }

    if (!started) {
      this._log("❌ QR検出エンジンが利用できません → 手動入力を使用してください");
    }

    return true;
  },

  _clearIntervals() {
    this._intervals.forEach(id => clearInterval(id));
    this._intervals = [];
  },

  async stop() {
    this._clearIntervals();
    this._detected = false;
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
