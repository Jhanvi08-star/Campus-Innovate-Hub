document.addEventListener("DOMContentLoaded", () => {
  // 1. Live Idea Search & Category Filter (ideas.html)
  const searchInput = document.getElementById("ideaSearch");
  const categoryFilter = document.getElementById("categoryFilter");
  const ideaCards = document.querySelectorAll(".idea-card[data-title]");

  function filterIdeas() {
    if (!searchInput || !categoryFilter) return;
    const query = searchInput.value.toLowerCase().trim();
    const selectedCategory = categoryFilter.value.toLowerCase();

    ideaCards.forEach((card) => {
      const title = card.dataset.title.toLowerCase();
      const skills = card.dataset.skills.toLowerCase();
      const category = card.dataset.category.toLowerCase();

      const matchesText = title.includes(query) || skills.includes(query);
      const matchesCategory =
        selectedCategory === "all" || category === selectedCategory;

      card.style.display = matchesText && matchesCategory ? "block" : "none";
    });
  }

  if (searchInput) searchInput.addEventListener("input", filterIdeas);
  if (categoryFilter) categoryFilter.addEventListener("change", filterIdeas);

  // 2. Auto-hide flash messages after 4 seconds
  const flashMessages = document.querySelectorAll(".flash-msg");
  flashMessages.forEach((msg) => {
    setTimeout(() => {
      msg.style.transition = "opacity 0.5s ease";
      msg.style.opacity = "0";
      setTimeout(() => msg.remove(), 500);
    }, 4000);
  });
});
