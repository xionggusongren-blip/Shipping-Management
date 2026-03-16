/**
 * 荷物管理Webアプリ - メインアプリケーション
 */
const App = {
  currentTab: "list",
  currentDetail: null,
  scannerStarted: false,
  _cameraMode: false,
  listData: [],
  filterParams: {},

  // ---- 初期化 ----
  async init() {
    window.App = this;
    this._bindEvents();

    const user = Api.getUser();
    if (user && Api.getToken()) {
      await this.onLogin(user);
    } else {
      this.showLogin();
    }
  },

  async onLogin(user) {
    document.getElementById("login-screen").style.display = "none";
    document.getElementById("user-name").textContent = user.display_name;
    if (user.role === "admin") {
      document.getElementById("nav-admin").style.display = "flex";
    }
    await this.loadShipments();
  },

  showLogin() {
    document.getElementById("login-screen").style.display = "flex";
    document.getElementById("login-username").focus();
  },

  // ---- イベントバインド ----
  _bindEvents() {
    // ログイン
    document.getElementById("login-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const u = document.getElementById("login-username").value.trim();
      const p = document.getElementById("login-password").value;
      const err = document.getElementById("login-error");
      const btn = document.getElementById("login-btn");
      err.style.display = "none";
      btn.disabled = true;
      btn.textContent = "ログイン中...";
      try {
        const data = await Api.login(u, p);
        await this.onLogin(data.user);
        this.showToast(`${data.user.display_name}さん、ログインしました`, "success");
      } catch (e) {
        err.textContent = e.message;
        err.style.display = "block";
      } finally {
        btn.disabled = false;
        btn.textContent = "ログイン";
      }
    });

    // ナビゲーション
    document.querySelectorAll(".nav-item").forEach((el) => {
      el.addEventListener("click", () => this.switchTab(el.dataset.tab));
    });

    // 戻るボタン
    document.getElementById("detail-back").addEventListener("click", () => this.closeDetail());

    // 同期ボタン
    document.getElementById("sync-btn").addEventListener("click", () => this.doSync());

    // ユーザーチップ（ログアウト）
    document.getElementById("user-chip").addEventListener("click", () => {
      if (confirm("ログアウトしますか？")) {
        Api.clearToken();
        location.reload();
      }
    });

    // 検索
    document.getElementById("search-btn").addEventListener("click", () => this.loadShipments());
    document.getElementById("search-keyword").addEventListener("keyup", (e) => {
      if (e.key === "Enter") this.loadShipments();
    });
    document.getElementById("filter-status").addEventListener("change", () => this.loadShipments());
    document.getElementById("filter-tanto").addEventListener("change", () => this.loadShipments());

    // ステータス更新ボタン
    document.querySelectorAll(".status-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".status-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
      });
    });
    document.getElementById("save-status-btn").addEventListener("click", () => this.saveStatus());

    // 荷札印刷
    document.getElementById("print-label-btn").addEventListener("click", () => this.printLabel());

    // スキャン
    document.getElementById("start-scan-btn").addEventListener("click", () => this.startScanner());
    document.getElementById("stop-scan-btn").addEventListener("click", () => this.stopScanner());
    document.getElementById("manual-search-btn").addEventListener("click", () => this.manualSearch());
    document.getElementById("manual-barcode").addEventListener("keyup", (e) => {
      if (e.key === "Enter") this.manualSearch();
    });

    // ブラウザの戻る操作
    window.addEventListener("popstate", () => {
      if (this.currentDetail) this.closeDetail();
    });
  },

  // ---- タブ切り替え ----
  switchTab(tabName) {
    if (this.currentDetail && tabName !== this.currentTab) {
      this.closeDetail();
    }

    this.currentTab = tabName;
    document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));

    const pane = document.getElementById(`tab-${tabName}`);
    if (pane) pane.classList.add("active");
    const nav = document.querySelector(`[data-tab="${tabName}"]`);
    if (nav) nav.classList.add("active");

    if (tabName === "scan") {
      const dbg = document.getElementById("scan-debug");
      if (dbg) { dbg.innerHTML = ""; this._dbgLog("スキャンタブを開きました"); }
      if (!this.scannerStarted) this.startScanner();
    }
    if (tabName === "admin") {
      this.loadAdminData();
    }
    if (tabName !== "scan") {
      this.stopScanner();
    }
  },

  // ---- 荷物一覧 ----
  async loadShipments() {
    const keyword = document.getElementById("search-keyword").value.trim();
    const status = document.getElementById("filter-status").value;
    const tanto = document.getElementById("filter-tanto").value;
    const user = Api.getUser();

    const params = { keyword, status };
    // 担当者フィルター: 管理者以外は自分の担当のみ（初期値）
    if (tanto) params.tanto = tanto;

    this.showLoading(true);
    try {
      const data = await Api.getShipments(params);
      this.listData = data;
      this.renderList(data);
    } catch (e) {
      this.showToast("データ取得に失敗しました: " + e.message, "error");
    } finally {
      this.showLoading(false);
    }
  },

  renderList(items) {
    const ul = document.getElementById("shipment-list");
    const empty = document.getElementById("list-empty");

    if (!items || items.length === 0) {
      ul.innerHTML = "";
      empty.style.display = "block";
      document.getElementById("list-count").textContent = "0件";
      return;
    }

    empty.style.display = "none";
    document.getElementById("list-count").textContent = `${items.length}件`;
    ul.innerHTML = items.map((item) => this._shipmentItemHtml(item)).join("");

    ul.querySelectorAll(".shipment-item").forEach((el) => {
      el.addEventListener("click", () => this.openDetail(parseInt(el.dataset.denno)));
    });
  },

  _shipmentItemHtml(item) {
    const nodayu = item.nodayu_str || "-";
    const today = new Date();
    let dateClass = "";
    if (item.nodayu_str) {
      const d = new Date(item.nodayu_str.replace(/\//g, "-"));
      const diff = (d - today) / 86400000;
      if (diff < 0) dateClass = "overdue";
      else if (diff <= 3) dateClass = "soon";
    }

    return `<li class="shipment-item status-${item.status}" data-denno="${item.denno}">
      <div class="shipment-row1">
        <span class="denno">#${item.denno}</span>
        <span class="hname">${esc(item.hname || "-")}</span>
        <span class="badge badge-${item.status}">${item.status}</span>
      </div>
      <div class="shipment-row2">
        <span>📦 ${esc(item.synm1 || "-")}</span>
        <span>数量: ${item.suryo || 0}</span>
        <span class="${dateClass}">納期: ${nodayu}</span>
        ${item.haiso ? `<span>🚚 ${esc(item.haiso)}</span>` : ""}
      </div>
    </li>`;
  },

  // ---- 詳細画面 ----
  async openDetail(denno) {
    this.showLoading(true);
    try {
      const data = await Api.getShipment(denno);
      this.currentDetail = data;
      this._renderDetail(data);
      document.getElementById("detail-panel").classList.add("open");
      history.pushState({ detail: denno }, "");
    } catch (e) {
      this.showToast("詳細取得失敗: " + e.message, "error");
    } finally {
      this.showLoading(false);
    }
  },

  closeDetail() {
    document.getElementById("detail-panel").classList.remove("open");
    this.currentDetail = null;
    if (this.scannerStarted) this.stopScanner();
  },

  _renderDetail(d) {
    const HAISO = { YAMTO: "ヤマト運輸", SAGAWA: "佐川急便", FUKUTU: "福山通運", NIPPON: "日本郵便", SEINO: "西濃運輸" };
    document.getElementById("detail-title").textContent = `伝票 #${d.denno}`;

    const fields = [
      ["hname", "品名", d.hname],
      ["hnm2", "型式", d.hnm2],
      ["mnmm", "メーカー", d.mnmm],
      ["hcod", "品番", d.hcod],
      ["suryo", "数量", d.suryo],
      ["ucod", "得意先コード", d.ucod],
      ["synm1", "出荷先", d.synm1 + (d.synm2 ? ` ${d.synm2}` : "")],
      ["adr1t", "住所", [d.adr1t, d.adr2t].filter(Boolean).join(" ")],
      ["nodayu_str", "得意先納期", d.nodayu_str || "-"],
      ["nodays_str", "指定納期", d.nodays_str || "-"],
      ["sykdy_str", "出荷日", d.sykdy_str || "-"],
      ["haiso", "配送方法", HAISO[d.haiso] || d.haiso || "-"],
      ["denno", "伝票番号", d.denno ? String(d.denno) : "-"],
      ["utno1", "得意先注番", d.utno1 || "-"],
      ["tanto", "担当者", d.tanto || "-"],
      ["dtadd", "備考", d.dtadd || "-"],
    ];

    const body = document.getElementById("detail-info-body");
    body.innerHTML = fields.map(([id, label, val]) =>
      `<div class="detail-cell${id === "synm1" || id === "adr1t" ? " full" : ""}">
        <div class="detail-label">${label}</div>
        <div class="detail-value">${esc(String(val || "-"))}</div>
      </div>`
    ).join("");

    // ステータスセット
    const currentStatus = d.status || "未処理";
    document.querySelectorAll(".status-btn").forEach((btn) => {
      btn.classList.toggle("selected", btn.dataset.status === currentStatus);
    });
    document.getElementById("status-memo").value = d.memo || "";
    document.getElementById("status-badge").textContent = currentStatus;
    document.getElementById("status-badge").className = `badge badge-${currentStatus}`;
    if (d.updated_by) {
      document.getElementById("status-updated-info").textContent =
        `最終更新: ${d.updated_by} ${d.updated_at ? new Date(d.updated_at).toLocaleString("ja-JP") : ""}`;
    } else {
      document.getElementById("status-updated-info").textContent = "";
    }
  },

  async saveStatus() {
    if (!this.currentDetail) return;
    const selected = document.querySelector(".status-btn.selected");
    if (!selected) { this.showToast("ステータスを選択してください", "error"); return; }
    const status = selected.dataset.status;
    const memo = document.getElementById("status-memo").value;
    const btn = document.getElementById("save-status-btn");
    btn.disabled = true;
    try {
      await Api.updateStatus(this.currentDetail.denno, status, memo);
      this.currentDetail.status = status;
      document.getElementById("status-badge").textContent = status;
      document.getElementById("status-badge").className = `badge badge-${status}`;
      document.getElementById("status-updated-info").textContent =
        `最終更新: ${Api.getUser()?.display_name} ${new Date().toLocaleString("ja-JP")}`;
      this.showToast("ステータスを更新しました", "success");
      // 一覧も更新
      const item = this.listData.find((x) => x.denno === this.currentDetail.denno);
      if (item) item.status = status;
    } catch (e) {
      this.showToast("更新失敗: " + e.message, "error");
    } finally {
      btn.disabled = false;
    }
  },

  printLabel() {
    if (!this.currentDetail) return;
    const url = `${window.location.origin}/api/shipments/${this.currentDetail.denno}/label`;
    const token = Api.getToken();
    // トークン付きでPDFを開く
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error("PDF生成に失敗しました");
        return res.blob();
      })
      .then((blob) => {
        const blobUrl = URL.createObjectURL(blob);
        window.open(blobUrl, "_blank");
        setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      })
      .catch((e) => this.showToast(e.message, "error"));
  },

  // ---- スキャン ----
  _dbgLog(msg) {
    console.log("[App]", msg);
    const el = document.getElementById("scan-debug");
    if (el) {
      const time = new Date().toLocaleTimeString("ja-JP");
      el.innerHTML += `<div>${time} ${msg}</div>`;
      el.scrollTop = el.scrollHeight;
    }
  },

  async startScanner() {
    const btn = document.getElementById("start-scan-btn");
    const stopBtn = document.getElementById("stop-scan-btn");
    const dbg = document.getElementById("scan-debug");
    if (dbg) dbg.innerHTML = "";
    this._dbgLog("startScanner() 呼び出し");

    btn.disabled = true;
    btn.textContent = "起動中...";

    let started = false;
    try {
      if (typeof Scanner === "undefined") {
        this._dbgLog("❌ Scanner未定義 - scanner.jsの読み込み失敗");
        throw new Error("Scanner未定義");
      }
      this._dbgLog("Scanner.start() 呼び出し...");
      started = await Scanner.start("reader", async (code) => {
        await this.stopScanner();
        this._cameraMode = true; // stop後にセット（自動再起動フラグ）
        await this.handleScanResult(code);
      });
    } catch (e) {
      this._dbgLog("❌ エラー: " + e.message);
      btn.disabled = false;
      btn.textContent = "📷 カメラ起動";
      return;
    }

    if (started) {
      btn.style.display = "none";
      stopBtn.style.display = "inline-flex";
      this.scannerStarted = true;
    } else {
      btn.disabled = false;
      btn.textContent = "📷 カメラ起動";
      this.showToast("カメラを起動できませんでした。手動入力をお使いください", "error");
    }
  },

  async stopScanner() {
    await Scanner.stop();
    const btn = document.getElementById("start-scan-btn");
    const stopBtn = document.getElementById("stop-scan-btn");
    btn.style.display = "inline-flex";
    btn.disabled = false;
    btn.textContent = "📷 カメラ起動";
    stopBtn.style.display = "none";
    this.scannerStarted = false;
    this._cameraMode = false;
  },

  // カメラスキャン中だった場合のみ自動再起動
  _autoRestartScanner() {
    if (!this._cameraMode) return;
    this._cameraMode = false;
    if (this.currentTab !== "scan" || this.scannerStarted) return;
    setTimeout(() => {
      if (this.currentTab === "scan" && !this.scannerStarted) {
        this.startScanner();
      }
    }, 800);
  },

  async manualSearch() {
    const val = document.getElementById("manual-barcode").value.trim();
    if (!val) return;
    await this.handleScanResult(val);
  },

  // QRコードの生データから検索キーを抽出する
  _extractSearchCode(raw) {
    const s = raw.trim();
    // カンマ区切り形式（納品書QR）: 最後のフィールドが DENNO
    if (s.includes(",")) {
      const parts = s.split(",");
      const last = parts[parts.length - 1].trim();
      if (last) return last;
    }
    // URLの場合、クエリパラメータまたはパスの末尾からコードを抽出
    try {
      const url = new URL(s);
      for (const key of ["order", "no", "code", "id", "utno", "denno", "barcode"]) {
        const val = url.searchParams.get(key);
        if (val) return val.trim();
      }
      const parts = url.pathname.split("/").filter(Boolean);
      if (parts.length > 0) return parts[parts.length - 1];
    } catch (_) {
      // URL ではない → そのまま使う
    }
    return s;
  },

  async handleScanResult(code) {
    const searchCode = this._extractSearchCode(code);
    const rawInfo = searchCode !== code
      ? `<div style="font-size:11px;color:var(--text-light);margin-top:4px">生データ: ${esc(code)}</div>`
      : "";

    document.getElementById("scan-result-area").innerHTML =
      `<div class="card"><div class="card-body">🔍 検索中: <strong>${esc(searchCode)}</strong>${rawInfo}</div></div>`;
    try {
      const data = await Api.scanBarcode(searchCode);
      document.getElementById("manual-barcode").value = "";
      this._showShipConfirm(data);
    } catch (e) {
      document.getElementById("scan-result-area").innerHTML =
        `<div class="card"><div class="card-body">
          <div style="color:var(--danger)">❌ ${esc(e.message)}</div>
          <div style="font-size:12px;margin-top:8px;color:var(--text-light)">
            スキャン値: <code style="background:#f0f0f0;padding:2px 6px;border-radius:4px">${esc(searchCode)}</code>
          </div>
          ${rawInfo}
          <div style="font-size:11px;margin-top:8px;color:var(--text-light)">
            ※ QRコードの内容がUTNO1・品番・伝票番号と一致しない場合は手動入力をお試しください
          </div>
        </div></div>`;
      // カメラスキャン由来の場合は2秒後に自動再起動
      if (this._cameraMode) {
        setTimeout(() => {
          document.getElementById("scan-result-area").innerHTML = "";
          this._autoRestartScanner();
        }, 2000);
      }
    }
  },

  _showShipConfirm(data) {
    const alreadyShipped = data.status === "出荷済" || data.status === "納品完了";
    const statusHtml = alreadyShipped
      ? `<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:8px 12px;margin-bottom:12px;font-size:13px">
           ⚠️ この伝票はすでに「${esc(data.status)}」です
         </div>`
      : "";

    document.getElementById("scan-result-area").innerHTML =
      `<div class="card" style="border:2px solid var(--primary)">
        <div class="card-header" style="background:var(--primary);color:#fff">
          📦 出荷確認
        </div>
        <div class="card-body">
          ${statusHtml}
          <table style="width:100%;font-size:14px;border-collapse:collapse">
            <tr><td style="color:var(--text-light);padding:4px 0;width:6em">伝票番号</td><td style="padding:4px 0"><strong>#${esc(String(data.denno))}</strong></td></tr>
            <tr><td style="color:var(--text-light);padding:4px 0">品名</td><td style="padding:4px 0">${esc(data.hname || "-")}</td></tr>
            <tr><td style="color:var(--text-light);padding:4px 0">出荷先</td><td style="padding:4px 0">${esc(data.synm1 || "-")}</td></tr>
            <tr><td style="color:var(--text-light);padding:4px 0">数量</td><td style="padding:4px 0">${esc(String(data.suryo || 0))}</td></tr>
            <tr><td style="color:var(--text-light);padding:4px 0">納期</td><td style="padding:4px 0">${esc(data.nodayu_str || "-")}</td></tr>
          </table>
          <div style="display:flex;gap:8px;margin-top:16px">
            <button id="ship-confirm-btn" class="btn btn-primary" style="flex:1;font-size:16px;padding:12px">
              🚚 出荷する
            </button>
            <button id="ship-detail-btn" class="btn" style="font-size:13px;padding:12px">
              詳細
            </button>
            <button id="ship-cancel-btn" class="btn btn-danger" style="font-size:13px;padding:12px">
              ✕
            </button>
          </div>
        </div>
      </div>`;

    document.getElementById("ship-confirm-btn").addEventListener("click", () => this._doShip(data));
    document.getElementById("ship-detail-btn").addEventListener("click", () => {
      document.getElementById("scan-result-area").innerHTML = "";
      this.currentDetail = data;
      this._renderDetail(data);
      document.getElementById("detail-panel").classList.add("open");
      history.pushState({ detail: data.denno }, "");
    });
    document.getElementById("ship-cancel-btn").addEventListener("click", () => {
      document.getElementById("scan-result-area").innerHTML = "";
      this._autoRestartScanner();
    });
  },

  async _doShip(data) {
    const btn = document.getElementById("ship-confirm-btn");
    if (btn) { btn.disabled = true; btn.textContent = "処理中..."; }
    try {
      await Api.updateStatus(data.denno, "出荷済", data.memo || "");
      document.getElementById("scan-result-area").innerHTML =
        `<div class="card" style="border:2px solid var(--success,#28a745)">
          <div class="card-body" style="text-align:center;padding:20px">
            <div style="font-size:40px;margin-bottom:8px">✅</div>
            <div style="font-size:16px;font-weight:bold">出荷済みにしました</div>
            <div style="color:var(--text-light);margin-top:4px">伝票 #${esc(String(data.denno))} &nbsp;${esc(data.synm1 || "")}</div>
            <div style="color:var(--text-light);font-size:12px;margin-top:4px">${new Date().toLocaleString("ja-JP")}</div>
          </div>
        </div>`;
      this.showToast(`伝票 #${data.denno} を出荷済みにしました`, "success");
      // 一覧データも更新
      const item = this.listData.find((x) => x.denno === data.denno);
      if (item) item.status = "出荷済";
      // 3秒後に結果エリアをクリアして次のスキャン待機（カメラ自動再起動）
      setTimeout(() => {
        document.getElementById("scan-result-area").innerHTML = "";
        this._autoRestartScanner();
      }, 3000);
    } catch (e) {
      this.showToast("出荷更新失敗: " + e.message, "error");
      if (btn) { btn.disabled = false; btn.textContent = "🚚 出荷する"; }
    }
  },

  // ---- 同期 ----
  async doSync() {
    const btn = document.getElementById("sync-btn");
    btn.disabled = true;
    btn.innerHTML = "⏳ 同期中...";
    try {
      const result = await Api.sync();
      this.showToast(`同期完了: ${result.record_count}件`, "success");
      await this.loadShipments();
    } catch (e) {
      this.showToast("同期失敗: " + e.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "🔄 同期";
    }
  },

  // ---- 管理画面 ----
  async loadAdminData() {
    try {
      const [syncStatus, logs] = await Promise.all([
        Api.getSyncStatus(),
        Api.getSyncLogs(),
      ]);

      document.getElementById("admin-record-count").textContent = syncStatus.record_count;
      document.getElementById("admin-last-sync").textContent =
        syncStatus.last_sync ? new Date(syncStatus.last_sync).toLocaleString("ja-JP") : "未実行";

      // ステータス集計
      const counts = { 未処理: 0, 梱包中: 0, 出荷済: 0, 納品完了: 0 };
      this.listData.forEach((i) => { if (counts[i.status] !== undefined) counts[i.status]++; });
      document.getElementById("admin-status-未処理").textContent = counts["未処理"];
      document.getElementById("admin-status-梱包中").textContent = counts["梱包中"];
      document.getElementById("admin-status-出荷済").textContent = counts["出荷済"];

      // 同期ログ
      const logEl = document.getElementById("sync-log-list");
      if (logs.length === 0) {
        logEl.innerHTML = "<li style='color:var(--text-light);padding:8px;'>ログなし</li>";
      } else {
        logEl.innerHTML = logs
          .map(
            (l) =>
              `<li style="padding:8px 0;border-bottom:1px solid var(--border)">
                <span style="font-size:11px;color:var(--text-light)">${new Date(l.synced_at).toLocaleString("ja-JP")}</span>
                <span class="badge badge-${l.status === "success" ? "出荷済" : "未処理"}" style="margin-left:8px">${l.status}</span>
                <span style="margin-left:8px;font-size:13px">${esc(l.message)}</span>
              </li>`
          )
          .join("");
      }
    } catch (e) {
      console.error("管理データ取得失敗:", e);
    }
  },

  // ---- ユーティリティ ----
  showLoading(show) {
    document.getElementById("loading-overlay").style.display = show ? "flex" : "none";
  },

  showToast(msg, type = "") {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = `${type}`;
    el.classList.add("show");
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
  },
};

// HTML エスケープ
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", () => App.init());
