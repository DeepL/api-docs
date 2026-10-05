(() => {
  const STORAGE_KEY = 'deepl_api_roadmap_survey_banner_v1';
  const DISMISSED = 'dismissed';
  const CLICKED = 'clicked';
  const SURVEY_URL = 'https://deepl.qualtrics.com/jfe/form/SV_8fbjoZx1wQUkAC2';
  const LINK_SELECTOR = `a[href="${SURVEY_URL}"]`;

  function getBannerState() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }

  function setBannerState(state) {
    try {
      window.localStorage.setItem(STORAGE_KEY, state);
    } catch {
      // The native banner still dismisses when storage is unavailable.
    }
  }

  function findDismissButton(link) {
    let container = link.parentElement;

    while (container && container !== document.body) {
      const button = container.querySelector(
        'button[aria-label*="dismiss" i], button[aria-label*="close" i]'
      );
      if (button) return button;
      container = container.parentElement;
    }

    return null;
  }

  function setupBanner() {
    const link = document.querySelector(LINK_SELECTOR);
    if (!link || link.dataset.roadmapSurveyReady === 'true') return false;

    const dismissButton = findDismissButton(link);
    if (!dismissButton) return false;

    link.dataset.roadmapSurveyReady = 'true';

    link.addEventListener('click', () => {
      setBannerState(CLICKED);
      window.setTimeout(() => dismissButton.click(), 0);
    });

    dismissButton.addEventListener('click', () => {
      if (getBannerState() !== CLICKED) setBannerState(DISMISSED);
    });

    const state = getBannerState();
    if (state === DISMISSED || state === CLICKED) dismissButton.click();

    return true;
  }

  if (!setupBanner()) {
    const observer = new MutationObserver(() => {
      if (setupBanner()) observer.disconnect();
    });

    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
