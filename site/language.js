/* I18N is supplied by the page's translations.js, loaded before this file. */
(() => {
  const buttons = [...document.querySelectorAll(".langs button")];
  const languages = buttons.map((button) => button.dataset.lang);
  const aliases = { br: "pt", bs: "hr", sr: "hr", mr: "hi" };

  function pickLanguage() {
    try {
      const saved = localStorage.getItem("lang");
      if (languages.includes(saved)) return saved;
    } catch {
      // Browser privacy settings can disable storage; translation still works.
    }
    for (const locale of navigator.languages || [navigator.language]) {
      const prefix = (locale || "").slice(0, 2).toLowerCase();
      const language = aliases[prefix] || prefix;
      // Keep the existing English fallback while checking other preferred locales.
      if (language !== "en" && languages.includes(language)) return language;
    }
    return "en";
  }

  function applyLanguage(language) {
    const translations = I18N[language];
    document.documentElement.lang = language;
    document.title = translations.title;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const value = translations[element.dataset.i18n];
      // Only repository-authored translations contain markup.
      if (value !== undefined) element.innerHTML = value;
    });
    document.querySelectorAll("img[data-fig], img[data-dfig]").forEach((image) => {
      const directory = image.dataset.dfig ? "img/details" : "img";
      const figure = image.dataset.dfig || image.dataset.fig;
      image.src = `${directory}/${language}/${figure}.png`;
      const alt = translations[image.dataset.alt];
      if (alt !== undefined) image.alt = alt;
    });
    buttons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.lang === language));
    });
    try {
      localStorage.setItem("lang", language);
    } catch {
      // The selection remains active for this page when storage is unavailable.
    }
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => applyLanguage(button.dataset.lang));
  });
  applyLanguage(pickLanguage());
})();
