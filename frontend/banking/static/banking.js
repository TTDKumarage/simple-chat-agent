function initTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  if (!buttons.length) return;
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(target).classList.add("active");
    });
  });

  const hash = window.location.hash.replace("#", "");
  if (hash) {
    const match = document.querySelector(`.tab-btn[data-tab="${hash}"]`);
    if (match) match.click();
  }
}

document.addEventListener("DOMContentLoaded", initTabs);
