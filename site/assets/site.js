const languageButtons = document.querySelectorAll("[data-lang-switch]");
const translatableNodes = document.querySelectorAll("[data-en][data-es]");

function applyLanguage(language) {
  const safeLanguage = language === "es" ? "es" : "en";
  document.documentElement.lang = safeLanguage;
  translatableNodes.forEach((node) => {
    node.textContent = node.dataset[safeLanguage];
  });
  languageButtons.forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.langSwitch === safeLanguage ? "true" : "false");
  });
  window.localStorage.setItem("innerchispa-language", safeLanguage);
}

languageButtons.forEach((button) => {
  button.addEventListener("click", () => applyLanguage(button.dataset.langSwitch));
});

applyLanguage(window.localStorage.getItem("innerchispa-language") || "en");
