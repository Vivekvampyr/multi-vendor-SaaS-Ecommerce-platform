/**
 * ==========================================================================
 * NexusSaaS Frontend Interactivity, API Client, and Real-Time Chat Controller
 * ==========================================================================
 */

window.Nexus = {
  // Token & Cookie Helpers
  getToken: function () {
    const local = localStorage.getItem("nexus_token");
    if (local) return local;
    const match = document.cookie.match(new RegExp("(^| )access_token=([^;]+)"));
    return match ? match[2] : null;
  },

  setToken: function (token) {
    localStorage.setItem("nexus_token", token);
    document.cookie = `access_token=${token}; path=/; max-age=86400; SameSite=Lax`;
  },

  clearToken: function () {
    localStorage.removeItem("nexus_token");
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
  },

  getSessionToken: function () {
    let token = localStorage.getItem("guest_session_token");
    if (!token) {
      token = "gst_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
      localStorage.setItem("guest_session_token", token);
    }
    return token;
  },

  // Standardized API Fetch Wrapper
  apiFetch: async function (url, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    headers["X-Session-Token"] = this.getSessionToken();
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data?.error?.message || data?.message || "An unexpected error occurred.";
      throw new Error(errorMsg);
    }
    return data;
  },

  // Floating Toast Notifications
  showToast: function (message, type = "success") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "✓" : type === "error" ? "✕" : "ℹ";
    toast.innerHTML = `<span class="font-bold text-lg">${icon}</span><span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  // Cart Badge & Actions
  updateCartBadge: async function () {
    try {
      const resp = await this.apiFetch("/api/v1/cart");
      const count = resp?.data?.total_items || 0;
      const badges = document.querySelectorAll(".cart-count-badge");
      badges.forEach((b) => {
        b.textContent = count;
        b.classList.toggle("hidden", count === 0);
      });
    } catch (e) {
      console.warn("Could not sync cart badge:", e);
    }
  },

  addToCart: async function (productId, quantity = 1) {
    try {
      await this.apiFetch("/api/v1/cart/items", {
        method: "POST",
        body: JSON.stringify({ product_id: parseInt(productId), quantity: parseInt(quantity) }),
      });
      this.showToast("Product added to cart!", "success");
      this.updateCartBadge();
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  // Wishlist Actions
  addToWishlist: async function (productId) {
    try {
      await this.apiFetch("/api/v1/wishlist", {
        method: "POST",
        body: JSON.stringify({ product_id: parseInt(productId) }),
      });
      this.showToast("Saved to wishlist!", "success");
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  // Auth Logout
  logout: function () {
    this.clearToken();
    window.location.href = "/login";
  },

  // Theme Management (Light & Dark with Pitch Black & Lime palette)
  initTheme: function () {
    const saved = localStorage.getItem("nexus_theme") || "dark";
    if (saved === "dark") {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.add("light");
      document.documentElement.classList.remove("dark");
    }
    this.updateThemeIcons(saved);
  },

  toggleTheme: function (e) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    const isDark = document.documentElement.classList.contains("dark");
    const next = isDark ? "light" : "dark";
    if (next === "dark") {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.add("light");
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("nexus_theme", next);
    this.updateThemeIcons(next);
  },

  updateThemeIcons: function (theme) {
    const sunIcons = document.querySelectorAll(".theme-icon-sun");
    const moonIcons = document.querySelectorAll(".theme-icon-moon");
    const themeTextEls = document.querySelectorAll(".theme-text-indicator");

    if (theme === "dark") {
      sunIcons.forEach((el) => el.classList.remove("hidden"));
      moonIcons.forEach((el) => el.classList.add("hidden"));
      themeTextEls.forEach((el) => (el.textContent = "Switch to Light"));
    } else {
      sunIcons.forEach((el) => el.classList.add("hidden"));
      moonIcons.forEach((el) => el.classList.remove("hidden"));
      themeTextEls.forEach((el) => (el.textContent = "Switch to Dark"));
    }
  },

  // User Profile Dropdown Toggle
  toggleUserDropdown: function (e) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    const menu = document.getElementById("user-dropdown-menu");
    if (!menu) return;
    menu.classList.toggle("dropdown-open");
  },

  // Mobile Navigation Drawer Toggle
  toggleMobileDrawer: function (e) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    const drawer = document.getElementById("mobile-drawer");
    const backdrop = document.getElementById("mobile-drawer-backdrop");
    if (!drawer) return;
    const isOpen = drawer.classList.contains("drawer-open");
    if (isOpen) {
      drawer.classList.remove("drawer-open");
      drawer.classList.add("drawer-closed");
      if (backdrop) backdrop.classList.add("hidden");
      document.body.style.overflow = "";
    } else {
      drawer.classList.remove("drawer-closed");
      drawer.classList.add("drawer-open");
      if (backdrop) backdrop.classList.remove("hidden");
      document.body.style.overflow = "hidden";
    }
  },

  closeMobileDrawer: function () {
    const drawer = document.getElementById("mobile-drawer");
    const backdrop = document.getElementById("mobile-drawer-backdrop");
    if (drawer) {
      drawer.classList.remove("drawer-open");
      drawer.classList.add("drawer-closed");
    }
    if (backdrop) {
      backdrop.classList.add("hidden");
    }
    document.body.style.overflow = "";
  },
};

// Initialize Cart Badge & Dynamic Handlers on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  window.Nexus.initTheme();
  window.Nexus.updateCartBadge();

  // Close user profile dropdown when clicking outside
  document.addEventListener("click", (e) => {
    const container = document.getElementById("user-menu-container");
    if (container && !container.contains(e.target)) {
      window.Nexus.closeUserDropdown();
    }
  });

  // Global handler for Add to Cart buttons
  document.querySelectorAll("[data-add-to-cart]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const prodId = btn.getAttribute("data-add-to-cart");
      const qtyInput = document.getElementById(`qty-${prodId}`);
      const qty = qtyInput ? qtyInput.value : 1;
      window.Nexus.addToCart(prodId, qty);
    });
  });

  // Global handler for Add to Wishlist buttons
  document.querySelectorAll("[data-add-to-wishlist]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const prodId = btn.getAttribute("data-add-to-wishlist");
      window.Nexus.addToWishlist(prodId);
    });
  });
});
