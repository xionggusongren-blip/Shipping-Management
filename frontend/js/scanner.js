/**
 * QRスキャン機能
 * jsQR (Canvas) + BarcodeDetector を並列で実行
 * 競合なし・全ブラウザ対応
 */
const Scanner = {
  _stream: null,
  _stopRequested: false,

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
    this._stopRequested = false;
    const dbg = document.getElementById("scan-debug");
    if (dbg) dbg.innerHTML = "";

    const hasNative = "BarcodeDetector" in window;
    const hasJsQR = typeof jsQR === "function";

    this._log("=== 起動開始 ===");
    this._log("BarcodeDetector: " + (hasNative ? "✅" : "❌"));
    this._log("jsQR: " + (hasJsQR ? "✅" : "❌"));
    this._log("getUserMedia: " + (navigator.mediaDevices ? "✅" : "❌ HTTPS必要"));

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this._log("❌ カメラ不可 → https://[PC-IP]:8443 でアクセスしてください");
      const container = document.getElementById(elementId);
      if (container) {
        container.innerHTML =
          `<div style="padding:20px;text-align:center;color:#e53e3e;background:#1a202c;border-radius:8px">
            <div style="font-size:32px">🚫</div>
            <div style="font-weight:600;margin-top:8px">カメラを使用できません</div>
            <div style="font-size:12px;margin-top:8px;color:#a0aec0">
              https://[PC-IP]:8443 でアクセスしてください
            </div>
          </div>`;
      }
      return false;
    }

    const container = document.getElementById(elementId);
    if (!container) return false;

    // ── ビデオ + ビューファインダー ──
    container.innerHTML = "";
    container.style.position = "relative";
    container.style.background = "#000";
    container.style.borderRadius = "8px";
    container.style.overflow = "hidden";

    const video = document.createElement("video");
    video.playsInline = true;
    video.muted = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("autoplay", "");
    video.style.cssText = "width:100%;height:auto;display:block;";
    container.appendChild(video);

    // スキャンガイド枠
    const overlay = document.createElement("div");
    overlay.style.cssText = `
      position:absolute;top:0;left:0;width:100%;height:100%;
      display:flex;align-items:center;justify-content:center;
      pointer-events:none;
    `;
    overlay.innerHTML = `
      <div style="
        width:65%;max-width:220px;aspect-ratio:1;
        border:3px solid rgba(255,255,255,0.9);
        border-radius:12px;
        box-shadow:0 0 0 2000px rgba(0,0,0,0.35);
        position:relative;
      ">
        <div style="position:absolute;top:-3px;left:-3px;width:24px;height:24px;border-top:4px solid #4fc3f7;border-left:4px solid #4fc3f7;border-radius:3px 0 0 0;"></div>
        <div style="position:absolute;top:-3px;right:-3px;width:24px;height:24px;border-top:4px solid #4fc3f7;border-right:4px solid #4fc3f7;border-radius:0 3px 0 0;"></div>
        <div style="position:absolute;bottom:-3px;left:-3px;width:24px;height:24px;border-bottom:4px solid #4fc3f7;border-left:4px solid #4fc3f7;border-radius:0 0 0 3px;"></div>
        <div style="position:absolute;bottom:-3px;right:-3px;width:24px;height:24px;border-bottom:4px solid #4fc3f7;border-right:4px solid #4fc3f7;border-radius:0 0 3px 0;"></div>
        <div id="scan-line" style="
          position:absolute;top:0;left:4px;right:4px;height:2px;
          background:linear-gradient(90deg,transparent,#4fc3f7,transparent);
          animation:scanline 2s linear infinite;
        "></div>
      </div>
    `;
    container.appendChild(overlay);

    // スキャンラインアニメーション
    if (!document.getElementById("scanline-style")) {
      const style = document.createElement("style");
      style.id = "scanline-style";
      style.textContent = `
        @keyframes scanline {
          0%   { top:4px; }
          50%  { top:calc(100% - 6px); }
          100% { top:4px; }
        }
      `;
      document.head.appendChild(style);
    }

    // ── カメラ起動 ──
    this._log("カメラ起動中...");
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }
      });
    } catch (e) {
      this._log("❌ カメラエラー: " + e.name + " " + e.message);
      container.innerHTML =
        `<div style="padding:20px;text-align:center;color:#e53e3e;background:#1a202c;border-radius:8px">
          <div style="font-size:32px">🚫</div>
          <div style="font-weight:600;margin-top:8px">カメラを許可してください</div>
          <div style="font-size:12px;margin-top:6px;color:#a0aec0">${e.name}: ${e.message}</div>
        </div>`;
      return false;
    }

    video.srcObject = this._stream;
    try { await video.play(); } catch (e) { this._log("play()失敗: " + e.message); }

    // 最初のフレームが来るまで待つ
    await new Promise(resolve => {
      if (video.videoWidth > 0) { resolve(); return; }
      const done = () => resolve();
      video.addEventListener("loadeddata", done, { once: true });
      video.addEventListener("canplay",     done, { once: true });
      setTimeout(done, 2000);
    });

    this._log("✅ 映像: " + video.videoWidth + "x" + video.videoHeight);
    if (video.videoWidth === 0) this._log("⚠️ 映像サイズが0 → カメラを確認");

    if (!hasJsQR && !hasNative) {
      this._log("❌ QRエンジンなし → 手動入力を使用してください");
      return true;
    }

    // ── 検出ループ ──
    // closure スコープの detected フラグ（stop()の影響を受けない）
    let detected = false;
    let frameCount = 0;

    const onDetect = (value, engine) => {
      if (detected) return;
      detected = true;
      this._stopRequested = true;
      this._log("🎉 検出(" + engine + "): " + value);
      this.beep();
      this.stop();
      onResult(value);
    };

    // 5秒後に診断ログ
    const diagTimer = setTimeout(() => {
      if (!detected) {
        this._log("⏱ 5秒経過・未検出");
        this._log("  ・QRコードを枠内に収めてください");
        this._log("  ・jsQR: " + (hasJsQR ? "動作中" : "未ロード"));
        this._log("  ・映像サイズ: " + video.videoWidth + "x" + video.videoHeight);
      }
    }, 5000);

    // ── jsQR ループ ──
    if (hasJsQR) {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      this._log("▶ jsQR ループ開始");

      const jsqrTick = () => {
        if (this._stopRequested || detected) return;

        frameCount++;
        if (frameCount % 20 === 0) this._log("jsQR " + frameCount + "f");

        if (video.readyState >= 2 && video.videoWidth > 0) {
          try {
            const scale = Math.min(1, 640 / video.videoWidth);
            const w = Math.max(1, Math.floor(video.videoWidth  * scale));
            const h = Math.max(1, Math.floor(video.videoHeight * scale));
            canvas.width  = w;
            canvas.height = h;
            ctx.drawImage(video, 0, 0, w, h);
            const imgData = ctx.getImageData(0, 0, w, h);
            const result = jsQR(imgData.data, w, h, { inversionAttempts: "attemptBoth" });
            if (result && result.data) {
              clearTimeout(diagTimer);
              onDetect(result.data, "jsQR");
              return;
            }
          } catch (e) {
            this._log("jsQR err: " + e.message);
          }
        }
        setTimeout(jsqrTick, 200);
      };
      setTimeout(jsqrTick, 200);
    }

    // ── BarcodeDetector ループ ──
    if (hasNative) {
      let detector;
      try {
        let formats = ["qr_code"];
        try {
          const sup = await BarcodeDetector.getSupportedFormats();
          formats = ["qr_code", ...["code_128","code_39","ean_13","data_matrix"].filter(f => sup.includes(f))];
        } catch (_) {}
        detector = new BarcodeDetector({ formats });
        this._log("▶ BarcodeDetector ループ開始 [" + formats.join(",") + "]");
      } catch (e) {
        this._log("BarcodeDetector 初期化失敗: " + e.message);
      }

      if (detector) {
        const nativeTick = async () => {
          if (this._stopRequested || detected) return;
          if (video.readyState >= 2 && !video.paused) {
            try {
              const codes = await detector.detect(video);
              if (codes.length > 0 && codes[0].rawValue) {
                clearTimeout(diagTimer);
                onDetect(codes[0].rawValue, "BarcodeDetector");
                return;
              }
            } catch (_) {}
          }
          setTimeout(nativeTick, 200);
        };
        setTimeout(nativeTick, 200);
      }
    }

    return true;
  },

  async stop() {
    this._stopRequested = true;
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
    } catch (_) {}
  },
};
