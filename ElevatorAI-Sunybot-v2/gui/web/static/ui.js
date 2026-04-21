/* gui/web/static/ui.js
 * - Giữ nguyên UI index.html: chỉ "inject" topbar tối giản + toast
 * - renderTabbar mặc định KHÔNG render (tránh thay đổi layout hiện tại)
 */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);

  function ensureStyleOnce() {
    if ($("#__suny_ui_style")) return;
    const style = document.createElement("style");
    style.id = "__suny_ui_style";
    style.textContent = `
      .suny-topbar{
        position: sticky;
        top: 0;
        z-index: 50;
        margin: 0;
        padding: 14px 18px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        background: linear-gradient(180deg, rgba(18,28,40,.92), rgba(15,22,32,.72));
        border-bottom: 1px solid rgba(255,255,255,.08);
        backdrop-filter: blur(10px);
      }
      .suny-topbar .brand{
        display:flex; align-items:center; gap:10px;
        font-family: "Sora", system-ui, sans-serif;
        font-weight: 800;
        letter-spacing: .4px;
      }
      .suny-topbar .brand .dot{
        width:10px;height:10px;border-radius:50%;
        background: linear-gradient(135deg, #2bd2b6, #57c9ff);
        box-shadow: 0 0 18px rgba(87,201,255,.5);
      }
      .suny-topbar .right{
        display:flex; align-items:center; gap:10px; flex-wrap:wrap;
      }
      .suny-pill{
        display:flex; align-items:center; gap:8px;
        padding:8px 10px;
        border-radius:999px;
        background: rgba(255,255,255,.06);
        border: 1px solid rgba(255,255,255,.08);
        color: rgba(232,238,246,.92);
        font-size: 12px;
        font-family: "Sora", system-ui, sans-serif;
        white-space: nowrap;
      }
      .suny-pill .k{ color: rgba(232,238,246,.62); font-weight: 600; }
      .suny-pill .v{ font-weight: 800; }

      /* Toast */
      .suny-toast-wrap{
        position: fixed;
        right: 16px;
        bottom: 16px;
        z-index: 9999;
        display:flex;
        flex-direction: column;
        gap: 10px;
        pointer-events:none;
      }
      .suny-toast{
        pointer-events:none;
        min-width: 220px;
        max-width: 360px;
        padding: 10px 12px;
        border-radius: 12px;
        background: rgba(18,28,40,.95);
        border: 1px solid rgba(255,255,255,.10);
        box-shadow: 0 18px 50px rgba(0,0,0,.35);
        color: rgba(232,238,246,.95);
        font-family: "Sora", system-ui, sans-serif;
        font-size: 12px;
        line-height: 1.35;
        transform: translateY(8px);
        opacity: 0;
        transition: .18s ease;
      }
      .suny-toast.show{
        transform: translateY(0);
        opacity: 1;
      }
      .suny-toast .t{
        font-weight: 800;
        margin-bottom: 2px;
      }
      .suny-toast .d{
        color: rgba(232,238,246,.70);
      }
    `;
    document.head.appendChild(style);
  }

  function renderTopbar(opts = {}) {
    ensureStyleOnce();

    // Nếu đã có topbar thì thôi (tránh render trùng)
    if ($(".suny-topbar")) return;

    const title = opts.title || "Sunybot • Smart Elevator";

    const bar = document.createElement("div");
    bar.className = "suny-topbar";
    bar.innerHTML = `
      <div class="brand" aria-label="Sunybot">
        <span class="dot" aria-hidden="true"></span>
        <span>${escapeHtml(title)}</span>
      </div>
      <div class="right">
        <div class="suny-pill" title="Thời gian">
          <span class="k">Giờ</span>
          <span class="v" id="tb_time">--:--</span>
        </div>
        <div class="suny-pill" title="Số lượng người trong thang">
          <span class="k">Người</span>
          <span class="v" id="tb_people">--</span>
        </div>
        <div class="suny-pill" title="Thời tiết">
          <span class="k">Thời tiết</span>
          <span class="v" id="tb_weather">--</span>
        </div>
      </div>
    `;

    // chèn lên đầu body (không phá layout .wrap phía dưới)
    document.body.insertBefore(bar, document.body.firstChild);
  }

  /**
   * renderTabbar()
   * - Mặc định: KHÔNG render gì (để giữ nguyên UI index.html như bạn yêu cầu).
   * - Nếu bạn muốn bật: gọi renderTabbar("/", { enabled:true })
   */
  function renderTabbar(_activePath = "/", options = {}) {
    ensureStyleOnce();
    const enabled = !!options.enabled;
    if (!enabled) return; // giữ nguyên 100% giao diện hiện tại

    // Nếu sau này bạn muốn tabbar dưới, mình có thể bổ sung thêm ở đây.
  }

  function showToast(message, detail = "", ttlMs = 2200) {
    ensureStyleOnce();

    let wrap = $(".suny-toast-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "suny-toast-wrap";
      document.body.appendChild(wrap);
    }

    const toast = document.createElement("div");
    toast.className = "suny-toast";
    toast.innerHTML = `
      <div class="t">${escapeHtml(message || "")}</div>
      ${detail ? `<div class="d">${escapeHtml(detail)}</div>` : ""}
    `;
    wrap.appendChild(toast);

    // animate in
    requestAnimationFrame(() => toast.classList.add("show"));

    // remove
    window.setTimeout(() => {
      toast.classList.remove("show");
      window.setTimeout(() => toast.remove(), 220);
    }, Math.max(800, ttlMs));
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // Expose globally (index.html đang gọi trực tiếp)
  window.renderTopbar = renderTopbar;
  window.renderTabbar = renderTabbar;
  window.showToast = showToast;
})();
